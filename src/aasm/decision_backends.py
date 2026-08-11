from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from inspect import signature
from itertools import islice, product
import math
import time
from typing import Any, Callable, Iterable

from .domain_adapters import CandidateModel, DecisionRequest
from .profile_packages import canonical_hash


CANDIDATE_STATUSES = {
    "PROPOSED",
    "VALIDATING",
    "ADMISSIBLE",
    "REJECTED",
    "SELECTED",
    "ACTIVATED",
    "SUPERSEDED",
    "EXPIRED",
}


@dataclass(frozen=True)
class BackendCapabilities:
    finite_domains: bool = False
    partial_models: bool = False
    hard_constraints: bool = False
    soft_constraints: bool = False
    multi_objective: bool = False
    incremental: bool = False
    continuations: bool = False
    certificates: bool = False
    deterministic: bool = False
    human_interaction: bool = False
    model_interaction: bool = False

    def to_dict(self) -> dict[str, bool]:
        return asdict(self)


@dataclass
class BackendBudget:
    max_candidates: int = 32
    max_combinations: int = 100_000
    max_cost: float | None = None
    max_latency_ms: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.max_candidates <= 0 or self.max_combinations <= 0:
            raise ValueError("backend candidate and combination limits must be positive")
        if self.max_cost is not None and self.max_cost < 0:
            raise ValueError("max_cost cannot be negative")
        if self.max_latency_ms is not None and self.max_latency_ms < 0:
            raise ValueError("max_latency_ms cannot be negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BackendUsage:
    combinations_considered: int = 0
    candidates_returned: int = 0
    estimated_cost: float = 0.0
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class BackendDiagnostic:
    code: str
    message: str
    severity: str = "INFO"
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateExplanation:
    assumptions: list[str] = field(default_factory=list)
    expected_obligation_ids: list[str] = field(default_factory=list)
    rationale: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateBatch:
    request_id: str
    backend_id: str
    backend_version: str
    candidates: list[CandidateModel]
    exhausted: bool
    continuation: str | None = None
    usage: BackendUsage = field(default_factory=BackendUsage)
    diagnostics: list[BackendDiagnostic] = field(default_factory=list)
    certificate: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.request_id or not self.backend_id or not self.backend_version:
            raise ValueError("candidate batches require request and backend identity")
        seen: set[str] = set()
        for candidate in self.candidates:
            if candidate.candidate_id in seen:
                raise ValueError(f"duplicate candidate ID: {candidate.candidate_id}")
            seen.add(candidate.candidate_id)
        self.usage.candidates_returned = len(self.candidates)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "exhausted": self.exhausted,
            "continuation": self.continuation,
            "usage": self.usage.to_dict(),
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "certificate": deepcopy(self.certificate),
        }


@dataclass
class CandidateLifecycleRecord:
    candidate: dict[str, Any]
    status: str = "PROPOSED"
    rejection_reasons: list[str] = field(default_factory=list)
    validation: dict[str, Any] = field(default_factory=dict)
    proposed_sequence: int = 0
    selected_sequence: int | None = None
    activated_sequence: int | None = None
    superseded_sequence: int | None = None

    def __post_init__(self):
        if self.status not in CANDIDATE_STATUSES:
            raise ValueError(f"invalid candidate lifecycle status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_candidate_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "requests": {},
        "batches": {},
        "candidates": {},
        "selected_candidate_id": None,
        "activated_candidate_id": None,
        "backend_history": [],
    }


def _request_payload(request: DecisionRequest | dict[str, Any]) -> dict[str, Any]:
    if isinstance(request, DecisionRequest):
        return request.to_dict()
    if not isinstance(request, dict):
        raise TypeError("decision backend request must be DecisionRequest or dict")
    return deepcopy(request)


def _request_id(request: DecisionRequest | dict[str, Any]) -> str:
    payload = _request_payload(request)
    explicit = str(payload.get("request_id") or "")
    return explicit or canonical_hash(payload)[:24]


def _finite_domains(
    request: DecisionRequest | dict[str, Any],
) -> list[tuple[str, list[dict[str, Any]]]]:
    payload = _request_payload(request)
    by_subject: dict[str, list[dict[str, Any]]] = {}
    raw_domains = payload.get("domains")
    if isinstance(raw_domains, dict):
        for subject, choices in raw_domains.items():
            rows: list[dict[str, Any]] = []
            for choice in list(choices or []):
                if isinstance(choice, dict):
                    row = deepcopy(choice)
                    row.setdefault("subject", str(subject))
                    row.setdefault("decision_id", str(row.get("value", "")))
                    row.setdefault("status", "PROPOSED")
                else:
                    row = {
                        "decision_id": str(choice),
                        "subject": str(subject),
                        "value": deepcopy(choice),
                        "status": "PROPOSED",
                    }
                if row.get("decision_id"):
                    rows.append(row)
            by_subject[str(subject)] = rows
    else:
        for decision in payload.get("available_decisions", []):
            subject = str(decision.get("subject", ""))
            decision_id = str(decision.get("decision_id", ""))
            if not subject or not decision_id:
                continue
            if decision.get("status") in {"INVALIDATED", "REJECTED", "HISTORICAL"}:
                continue
            by_subject.setdefault(subject, []).append(deepcopy(decision))
    return [
        (subject, sorted(values, key=lambda item: str(item.get("decision_id"))))
        for subject, values in sorted(by_subject.items())
    ]


def _remaining_latency_ms(started: float, budget: BackendBudget) -> float | None:
    if budget.max_latency_ms is None:
        return None
    return max(0.0, float(budget.max_latency_ms) - (time.monotonic() - started) * 1000.0)


class FiniteDomainDecisionBackend:
    backend_id = "aasm.finite-domain"
    backend_version = "1.1.0"
    capabilities = BackendCapabilities(
        finite_domains=True,
        partial_models=True,
        hard_constraints=True,
        soft_constraints=True,
        incremental=True,
        continuations=True,
        certificates=True,
        deterministic=True,
    )

    @staticmethod
    def _domains(
        request: DecisionRequest | dict[str, Any],
    ) -> list[tuple[str, list[dict[str, Any]]]]:
        return _finite_domains(request)

    def propose_batch(
        self,
        request: DecisionRequest | dict[str, Any],
        *,
        budget: BackendBudget | None = None,
        continuation: str | None = None,
    ) -> CandidateBatch:
        budget = budget or BackendBudget()
        started = time.monotonic()
        request_id = _request_id(request)
        payload = _request_payload(request)
        domains = self._domains(request)
        start = 0
        if continuation:
            prefix, _, raw = continuation.partition(":")
            if prefix != request_id or not raw.isdigit():
                raise ValueError("invalid finite-domain continuation token")
            start = int(raw)

        if domains and any(not choices for _, choices in domains):
            combinations = 0
        else:
            combinations = 1
            for _, choices in domains:
                combinations *= len(choices)
        if start < 0 or start > combinations:
            raise ValueError("finite-domain continuation is outside the search space")

        diagnostics: list[BackendDiagnostic] = []
        per_combination_cost = float(
            budget.metadata.get(
                "cost_per_combination",
                1.0 if budget.max_cost is not None else 0.0,
            )
        )
        if per_combination_cost < 0:
            raise ValueError("cost_per_combination cannot be negative")

        call_limit = min(budget.max_candidates, budget.max_combinations)
        if budget.max_cost is not None and per_combination_cost > 0:
            cost_limit = max(0, int(float(budget.max_cost) // per_combination_cost))
            call_limit = min(call_limit, cost_limit)
        if call_limit <= 0 and start < combinations:
            diagnostics.append(BackendDiagnostic(
                "COST_LIMIT",
                "finite-domain budget does not permit another combination",
                "WARN",
                {"max_cost": budget.max_cost, "cost_per_combination": per_combination_cost},
            ))

        rows: list[tuple[dict[str, str], dict[str, Any]]] = []
        choice_lists = [values for _, values in domains]
        iterable: Iterable[tuple[dict[str, Any], ...]]
        iterable = product(*choice_lists) if choice_lists else [tuple()]
        considered = 0
        latency_limited = False
        for index, selected in enumerate(islice(iterable, start, start + call_limit), start=start):
            remaining = _remaining_latency_ms(started, budget)
            if remaining is not None and remaining <= 0:
                latency_limited = True
                break
            assignments = {
                subject: str(decision.get("decision_id"))
                for (subject, _), decision in zip(domains, selected)
            }
            rows.append((assignments, {"ordinal": index}))
            considered += 1

        candidates: list[CandidateModel] = []
        for assignments, meta in rows:
            candidate_id = "candidate_" + canonical_hash(
                {"request_id": request_id, "assignments": assignments}
            )[:16]
            candidates.append(CandidateModel(
                candidate_id=candidate_id,
                assignments=assignments,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                rationale={"kind": "finite-domain-enumeration", **meta},
                metadata={"deterministic": True},
            ))

        consumed = start + considered
        exhausted = consumed >= combinations
        if latency_limited:
            diagnostics.append(BackendDiagnostic(
                "LATENCY_LIMIT",
                "finite-domain enumeration stopped at its latency budget",
                "WARN",
                {"max_latency_ms": budget.max_latency_ms},
            ))
        elif not exhausted and considered >= budget.max_combinations:
            diagnostics.append(BackendDiagnostic(
                "COMBINATION_LIMIT",
                "finite-domain enumeration reached the per-call combination limit",
                "INFO",
                {"max_combinations": budget.max_combinations},
            ))
        elif not exhausted and considered >= budget.max_candidates:
            diagnostics.append(BackendDiagnostic(
                "CANDIDATE_LIMIT",
                "finite-domain enumeration reached the per-call candidate limit",
                "INFO",
                {"max_candidates": budget.max_candidates},
            ))
        elif not exhausted and budget.max_cost is not None:
            diagnostics.append(BackendDiagnostic(
                "COST_LIMIT",
                "finite-domain enumeration stopped at its cost budget",
                "WARN",
                {"max_cost": budget.max_cost, "cost_per_combination": per_combination_cost},
            ))

        next_token = None if exhausted else f"{request_id}:{consumed}"
        latency_ms = (time.monotonic() - started) * 1000.0
        return CandidateBatch(
            request_id=request_id,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            candidates=candidates,
            exhausted=exhausted,
            continuation=next_token,
            usage=BackendUsage(
                combinations_considered=considered,
                candidates_returned=len(candidates),
                estimated_cost=considered * per_combination_cost,
                latency_ms=latency_ms,
            ),
            diagnostics=diagnostics,
            certificate={
                "kind": "FINITE_ENUMERATION",
                "request_fingerprint": canonical_hash(payload),
                "search_space_size": combinations,
                "start": start,
                "end": consumed,
                "per_call_combination_limit": budget.max_combinations,
            },
        )

    def generate(
        self,
        request: DecisionRequest | dict[str, Any],
        *,
        budget: BackendBudget | None = None,
        continuation: str | None = None,
    ) -> CandidateBatch:
        return self.propose_batch(request, budget=budget, continuation=continuation)

    def propose(self, request: DecisionRequest | dict[str, Any]) -> CandidateModel | dict[str, Any]:
        batch = self.propose_batch(request, budget=BackendBudget(max_candidates=1))
        if not batch.candidates:
            raise RuntimeError("finite-domain backend produced no candidate")
        return batch.candidates[0]


class HumanDecisionBackend:
    backend_id = "aasm.human"
    backend_version = "1.0.0"
    capabilities = BackendCapabilities(human_interaction=True)

    def decision_packet(self, request: DecisionRequest) -> dict[str, Any]:
        return {
            "request": request.to_dict(),
            "response_contract": {
                "assignments": "object mapping decision subjects to decision IDs",
                "rationale": "optional structured rationale",
            },
        }

    def accept_response(self, request: DecisionRequest, response: dict[str, Any]) -> CandidateModel:
        assignments = deepcopy(response.get("assignments") or {})
        candidate_id = "candidate_" + canonical_hash(
            {"request": request.machine_id, "assignments": assignments, "source": "human"}
        )[:16]
        return CandidateModel(
            candidate_id=candidate_id,
            assignments=assignments,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            rationale=deepcopy(response.get("rationale") or {}),
            metadata={"human": True},
        )

    def propose(self, request: DecisionRequest) -> dict[str, Any]:
        return self.decision_packet(request)


class CallbackDecisionBackend:
    """Provider-neutral callback backend with explicit resource budgets.

    The callback is run in a worker thread so the caller can stop waiting when
    the declared latency budget expires. This is a timeout boundary, not a
    security sandbox; untrusted callbacks still belong in a separate process.
    """

    backend_id = "aasm.callback"
    backend_version = "1.1.0"
    capabilities = BackendCapabilities(model_interaction=True)

    def __init__(self, callback: Callable[[dict[str, Any]], Any], *, backend_id: str | None = None):
        self.callback = callback
        if backend_id:
            self.backend_id = backend_id

    def propose_batch(
        self,
        request: DecisionRequest | dict[str, Any],
        *,
        budget: BackendBudget | None = None,
        continuation: str | None = None,
    ) -> CandidateBatch:
        if continuation is not None:
            raise ValueError("callback backend does not support continuations")
        budget = budget or BackendBudget()
        payload = _request_payload(request)
        request_id = _request_id(request)
        started = time.monotonic()
        callback_cost = float(budget.metadata.get("callback_cost", 0.0))
        if callback_cost < 0:
            raise ValueError("callback_cost cannot be negative")
        if budget.max_cost is not None and callback_cost > float(budget.max_cost):
            return CandidateBatch(
                request_id=request_id,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                candidates=[],
                exhausted=False,
                usage=BackendUsage(estimated_cost=0.0),
                diagnostics=[BackendDiagnostic(
                    "COST_LIMIT",
                    "callback was not invoked because its declared cost exceeds the budget",
                    "WARN",
                    {"callback_cost": callback_cost, "max_cost": budget.max_cost},
                )],
            )

        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aasm-backend")
        future = executor.submit(self.callback, deepcopy(payload))
        try:
            timeout = None if budget.max_latency_ms is None else float(budget.max_latency_ms) / 1000.0
            raw = future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            latency_ms = (time.monotonic() - started) * 1000.0
            return CandidateBatch(
                request_id=request_id,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                candidates=[],
                exhausted=False,
                usage=BackendUsage(estimated_cost=callback_cost, latency_ms=latency_ms),
                diagnostics=[BackendDiagnostic(
                    "CALLBACK_TIMEOUT",
                    "callback exceeded the declared latency budget",
                    "WARN",
                    {"max_latency_ms": budget.max_latency_ms},
                )],
            )
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        rows = raw if isinstance(raw, list) else [raw]
        diagnostics: list[BackendDiagnostic] = []
        if len(rows) > budget.max_candidates:
            diagnostics.append(BackendDiagnostic(
                "CANDIDATE_LIMIT",
                "callback output was truncated to the candidate budget",
                "WARN",
                {"returned": len(rows), "max_candidates": budget.max_candidates},
            ))
            rows = rows[: budget.max_candidates]

        candidates: list[CandidateModel] = []
        for index, row in enumerate(rows):
            if isinstance(row, CandidateModel):
                candidate = CandidateModel.from_dict(row.to_dict())
            elif isinstance(row, dict):
                assignments = deepcopy(row.get("assignments") or {})
                candidate = CandidateModel(
                    candidate_id=row.get("candidate_id") or "candidate_" + canonical_hash(
                        {"backend": self.backend_id, "index": index, "assignments": assignments}
                    )[:16],
                    assignments=assignments,
                    backend_id=self.backend_id,
                    backend_version=self.backend_version,
                    rationale=deepcopy(row.get("rationale") or {}),
                    score=row.get("score"),
                    metadata=deepcopy(row.get("metadata") or {}),
                )
            else:
                raise TypeError("callback backend must return candidate dictionaries")
            if candidate.score is not None and not math.isfinite(float(candidate.score)):
                raise ValueError("candidate score must be finite")
            candidates.append(candidate)

        latency_ms = (time.monotonic() - started) * 1000.0
        return CandidateBatch(
            request_id=request_id,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            candidates=candidates,
            exhausted=True,
            usage=BackendUsage(
                combinations_considered=len(rows),
                candidates_returned=len(candidates),
                estimated_cost=callback_cost,
                latency_ms=latency_ms,
            ),
            diagnostics=diagnostics,
        )

    def generate(
        self,
        request: DecisionRequest | dict[str, Any],
        *,
        budget: BackendBudget | None = None,
        continuation: str | None = None,
    ) -> CandidateBatch:
        return self.propose_batch(request, budget=budget, continuation=continuation)

    def propose(self, request: DecisionRequest | dict[str, Any]) -> CandidateModel:
        batch = self.propose_batch(request)
        if not batch.candidates:
            raise RuntimeError("callback backend produced no candidate")
        return batch.candidates[0]


class PortfolioDecisionBackend:
    backend_id = "aasm.portfolio"
    backend_version = "1.1.0"
    capabilities = BackendCapabilities()

    def __init__(self, backends: Iterable[Any]):
        self.backends = list(backends)
        if not self.backends:
            raise ValueError("portfolio backend requires at least one backend")

    @staticmethod
    def _invoke_backend(
        backend: Any,
        request: DecisionRequest | dict[str, Any],
        budget: BackendBudget,
    ) -> CandidateBatch:
        if hasattr(backend, "propose_batch"):
            method = backend.propose_batch
            parameters = signature(method).parameters
            kwargs: dict[str, Any] = {}
            if "budget" in parameters:
                kwargs["budget"] = budget
            return method(request, **kwargs)
        raw = backend.propose(request)
        rows = [raw if isinstance(raw, CandidateModel) else CandidateModel.from_dict(raw)]
        return CandidateBatch(
            request_id=_request_id(request),
            backend_id=str(getattr(backend, "backend_id", type(backend).__name__)),
            backend_version=str(getattr(backend, "backend_version", "0")),
            candidates=rows,
            exhausted=True,
        )

    def propose_batch(
        self,
        request: DecisionRequest | dict[str, Any],
        *,
        budget: BackendBudget | None = None,
        continuation: str | None = None,
    ) -> CandidateBatch:
        if continuation is not None:
            raise ValueError("portfolio backend does not support continuations")
        budget = budget or BackendBudget()
        started = time.monotonic()
        merged: dict[tuple[tuple[str, str], ...], CandidateModel] = {}
        diagnostics: list[BackendDiagnostic] = []
        total_combinations = 0
        total_cost = 0.0
        all_exhausted = True

        for backend in self.backends:
            remaining_candidates = budget.max_candidates - len(merged)
            remaining_cost = None if budget.max_cost is None else max(0.0, budget.max_cost - total_cost)
            remaining_latency = _remaining_latency_ms(started, budget)
            if remaining_candidates <= 0:
                all_exhausted = False
                diagnostics.append(BackendDiagnostic(
                    "CANDIDATE_LIMIT",
                    "portfolio stopped before all backends ran because its candidate budget was full",
                    "INFO",
                ))
                break
            if remaining_latency is not None and remaining_latency <= 0:
                all_exhausted = False
                diagnostics.append(BackendDiagnostic(
                    "LATENCY_LIMIT",
                    "portfolio stopped before all backends ran because its latency budget expired",
                    "WARN",
                ))
                break
            sub_budget = BackendBudget(
                max_candidates=remaining_candidates,
                max_combinations=budget.max_combinations,
                max_cost=remaining_cost,
                max_latency_ms=remaining_latency,
                metadata=deepcopy(budget.metadata),
            )
            backend_id = str(getattr(backend, "backend_id", type(backend).__name__))
            backend_version = str(getattr(backend, "backend_version", "0"))
            try:
                batch = self._invoke_backend(backend, request, sub_budget)
            except Exception as exc:
                diagnostics.append(BackendDiagnostic(
                    "BACKEND_ERROR",
                    f"{backend_id}: {type(exc).__name__}: {exc}",
                    "WARN",
                    {"backend_id": backend_id, "error_type": type(exc).__name__},
                ))
                all_exhausted = False
                continue
            total_combinations += int(batch.usage.combinations_considered)
            total_cost += float(batch.usage.estimated_cost)
            all_exhausted = all_exhausted and bool(batch.exhausted)
            diagnostics.extend(deepcopy(batch.diagnostics))
            for candidate in batch.candidates:
                key = tuple(sorted((str(k), str(v)) for k, v in candidate.assignments.items()))
                source = {
                    "backend_id": backend_id,
                    "backend_version": backend_version,
                    "candidate_id": candidate.candidate_id,
                }
                if key not in merged:
                    clone = CandidateModel.from_dict(candidate.to_dict())
                    clone.metadata = deepcopy(clone.metadata)
                    clone.metadata["portfolio_sources"] = [source]
                    merged[key] = clone
                else:
                    sources = merged[key].metadata.setdefault("portfolio_sources", [])
                    if source not in sources:
                        sources.append(source)

        request_id = _request_id(request)
        candidates = [merged[key] for key in sorted(merged)][: budget.max_candidates]
        latency_ms = (time.monotonic() - started) * 1000.0
        return CandidateBatch(
            request_id=request_id,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            candidates=candidates,
            exhausted=all_exhausted,
            usage=BackendUsage(
                combinations_considered=total_combinations,
                candidates_returned=len(candidates),
                estimated_cost=total_cost,
                latency_ms=latency_ms,
            ),
            diagnostics=diagnostics,
        )

    def generate(
        self,
        request: DecisionRequest | dict[str, Any],
        *,
        budget: BackendBudget | None = None,
        continuation: str | None = None,
    ) -> CandidateBatch:
        return self.propose_batch(request, budget=budget, continuation=continuation)

    def propose(self, request: DecisionRequest | dict[str, Any]) -> CandidateModel:
        batch = self.propose_batch(request)
        if not batch.candidates:
            raise RuntimeError("portfolio produced no candidate")
        return batch.candidates[0]


class DecisionBackendRegistry:
    def __init__(self):
        self._backends: dict[str, Any] = {}

    def register(self, backend: Any) -> None:
        backend_id = str(getattr(backend, "backend_id", ""))
        if not backend_id:
            raise ValueError("backend_id is required")
        if backend_id in self._backends:
            raise ValueError(f"backend already registered: {backend_id}")
        self._backends[backend_id] = backend

    def get(self, backend_id: str) -> Any:
        try:
            return self._backends[backend_id]
        except KeyError as exc:
            raise KeyError(f"unknown decision backend: {backend_id}") from exc

    def list(self) -> list[dict[str, Any]]:
        rows = []
        for backend_id, backend in sorted(self._backends.items()):
            capabilities = getattr(backend, "capabilities", BackendCapabilities())
            rows.append({
                "backend_id": backend_id,
                "backend_version": str(getattr(backend, "backend_version", "0")),
                "capabilities": capabilities.to_dict(),
            })
        return rows


def default_backend_registry() -> DecisionBackendRegistry:
    registry = DecisionBackendRegistry()
    registry.register(FiniteDomainDecisionBackend())
    registry.register(HumanDecisionBackend())
    return registry


def route_backend(
    registry: DecisionBackendRegistry,
    *,
    required_capabilities: Iterable[str] = (),
    deterministic: bool | None = None,
) -> str:
    required = set(required_capabilities)
    for row in registry.list():
        capabilities = row["capabilities"]
        if any(not capabilities.get(name, False) for name in required):
            continue
        if deterministic is not None and bool(capabilities.get("deterministic")) != deterministic:
            continue
        return str(row["backend_id"])
    raise LookupError("no registered decision backend satisfies the requested capabilities")
