from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from itertools import product
import math
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


class FiniteDomainDecisionBackend:
    backend_id = "aasm.finite-domain"
    backend_version = "1.0.0"
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
    def _domains(request: DecisionRequest) -> list[tuple[str, list[dict[str, Any]]]]:
        by_subject: dict[str, list[dict[str, Any]]] = {}
        for decision in request.available_decisions:
            subject = str(decision.get("subject", ""))
            decision_id = str(decision.get("decision_id", ""))
            if not subject or not decision_id:
                continue
            if decision.get("status") in {"INVALIDATED", "REJECTED", "HISTORICAL"}:
                continue
            by_subject.setdefault(subject, []).append(decision)
        return [
            (subject, sorted(values, key=lambda item: str(item.get("decision_id"))))
            for subject, values in sorted(by_subject.items())
        ]

    def propose_batch(
        self,
        request: DecisionRequest,
        *,
        budget: BackendBudget | None = None,
        continuation: str | None = None,
    ) -> CandidateBatch:
        budget = budget or BackendBudget()
        request_id = canonical_hash(request.to_dict())[:24]
        domains = self._domains(request)
        start = 0
        if continuation:
            prefix, _, raw = continuation.partition(":")
            if prefix != request_id or not raw.isdigit():
                raise ValueError("invalid finite-domain continuation token")
            start = int(raw)
        combinations = 1
        for _, choices in domains:
            combinations *= max(1, len(choices))
        if combinations > budget.max_combinations:
            return CandidateBatch(
                request_id=request_id,
                backend_id=self.backend_id,
                backend_version=self.backend_version,
                candidates=[],
                exhausted=False,
                continuation=continuation or f"{request_id}:0",
                usage=BackendUsage(combinations_considered=0),
                diagnostics=[BackendDiagnostic(
                    "COMBINATION_LIMIT",
                    f"finite search space {combinations} exceeds limit {budget.max_combinations}",
                    "WARN",
                )],
            )

        rows: list[tuple[dict[str, str], dict[str, Any]]] = []
        choice_lists = [values for _, values in domains]
        iterable: Iterable[tuple[dict[str, Any], ...]]
        iterable = product(*choice_lists) if choice_lists else [tuple()]
        for index, selected in enumerate(iterable):
            if index < start:
                continue
            assignments = {
                subject: str(decision.get("decision_id"))
                for (subject, _), decision in zip(domains, selected)
            }
            rows.append((assignments, {"ordinal": index}))
            if len(rows) >= budget.max_candidates:
                break

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

        consumed = start + len(candidates)
        exhausted = consumed >= combinations
        next_token = None if exhausted else f"{request_id}:{consumed}"
        return CandidateBatch(
            request_id=request_id,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            candidates=candidates,
            exhausted=exhausted,
            continuation=next_token,
            usage=BackendUsage(
                combinations_considered=len(candidates),
                candidates_returned=len(candidates),
            ),
            certificate={
                "kind": "FINITE_ENUMERATION",
                "request_fingerprint": canonical_hash(request.to_dict()),
                "search_space_size": combinations,
                "start": start,
                "end": consumed,
            },
        )

    def propose(self, request: DecisionRequest) -> CandidateModel | dict[str, Any]:
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
    """Provider-neutral model/heuristic proposal backend.

    The callback returns either one candidate dictionary or a list of candidate
    dictionaries. AASM still validates every candidate independently.
    """

    backend_id = "aasm.callback"
    backend_version = "1.0.0"
    capabilities = BackendCapabilities(model_interaction=True)

    def __init__(self, callback: Callable[[dict[str, Any]], Any], *, backend_id: str | None = None):
        self.callback = callback
        if backend_id:
            self.backend_id = backend_id

    def propose_batch(self, request: DecisionRequest) -> CandidateBatch:
        raw = self.callback(request.to_dict())
        rows = raw if isinstance(raw, list) else [raw]
        candidates: list[CandidateModel] = []
        for index, row in enumerate(rows):
            if isinstance(row, CandidateModel):
                candidate = row
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
        request_id = canonical_hash(request.to_dict())[:24]
        return CandidateBatch(
            request_id=request_id,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            candidates=candidates,
            exhausted=True,
            usage=BackendUsage(candidates_returned=len(candidates)),
        )

    def propose(self, request: DecisionRequest) -> CandidateModel:
        batch = self.propose_batch(request)
        if not batch.candidates:
            raise RuntimeError("callback backend produced no candidate")
        return batch.candidates[0]


class PortfolioDecisionBackend:
    backend_id = "aasm.portfolio"
    backend_version = "1.0.0"
    capabilities = BackendCapabilities()

    def __init__(self, backends: Iterable[Any]):
        self.backends = list(backends)
        if not self.backends:
            raise ValueError("portfolio backend requires at least one backend")

    def propose_batch(self, request: DecisionRequest) -> CandidateBatch:
        merged: dict[tuple[tuple[str, str], ...], CandidateModel] = {}
        diagnostics: list[BackendDiagnostic] = []
        for backend in self.backends:
            try:
                if hasattr(backend, "propose_batch"):
                    batch = backend.propose_batch(request)
                    rows = batch.candidates
                else:
                    raw = backend.propose(request)
                    rows = [raw if isinstance(raw, CandidateModel) else CandidateModel.from_dict(raw)]
            except Exception as exc:
                diagnostics.append(BackendDiagnostic(
                    "BACKEND_ERROR",
                    f"{getattr(backend, 'backend_id', type(backend).__name__)}: {exc}",
                    "WARN",
                ))
                continue
            for candidate in rows:
                key = tuple(sorted(candidate.assignments.items()))
                merged.setdefault(key, candidate)
        request_id = canonical_hash(request.to_dict())[:24]
        candidates = [merged[key] for key in sorted(merged)]
        return CandidateBatch(
            request_id=request_id,
            backend_id=self.backend_id,
            backend_version=self.backend_version,
            candidates=candidates,
            exhausted=True,
            usage=BackendUsage(candidates_returned=len(candidates)),
            diagnostics=diagnostics,
        )

    def propose(self, request: DecisionRequest) -> CandidateModel:
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
