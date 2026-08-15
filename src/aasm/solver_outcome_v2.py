from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .optimization import OptimizationResult
from .semantic_result import semantic_fingerprint


SOLVER_OUTCOME_V2_CONTRACT_ID = "aasm.solver.outcome.v2"
SOLVER_OUTCOME_V2_CONTRACT_VERSION = "0.1.0"
SOLVER_TERMINATION_V2_CONTRACT_ID = "aasm.solver.termination.v2"
SOLVER_TERMINATION_V2_CONTRACT_VERSION = "0.1.0"
SOLVER_EVIDENCE_GRADE_CONTRACT_ID = "aasm.solver.evidence-grade.v1"
SOLVER_EVIDENCE_GRADE_CONTRACT_VERSION = "0.1.0"
SOLVER_OUTCOME_V2_STABILITY = "FOUNDATION_EXPERIMENTAL"

TERMINATION_REASONS = (
    "COMPLETED",
    "TIME_LIMIT",
    "NODE_LIMIT",
    "ITERATION_LIMIT",
    "SOLUTION_LIMIT",
    "MEMORY_LIMIT",
    "USER_INTERRUPT",
    "NUMERICAL_FAILURE",
    "MODEL_INVALID",
    "PROVIDER_UNAVAILABLE",
    "UNSUPPORTED_FEATURE",
    "INTERNAL_ERROR",
    "UNKNOWN",
)
SOLUTION_STATUSES = ("FEASIBLE", "INFEASIBLE", "UNKNOWN")
INCUMBENT_STATUSES = ("PRESENT", "ABSENT", "UNKNOWN")
OPTIMALITY_CLAIMS = ("CLAIMED_OPTIMAL", "NOT_CLAIMED", "NOT_APPLICABLE", "UNKNOWN")
PROOF_STATUSES = (
    "CHECKED_CERTIFICATE",
    "UNCHECKED_CERTIFICATE",
    "NO_CERTIFICATE",
    "NOT_APPLICABLE",
    "UNKNOWN",
)
EVIDENCE_GRADES = (
    "CHECKED_CERTIFICATE",
    "INDEPENDENTLY_VALIDATED",
    "PROVIDER_ASSERTED",
    "UNVERIFIED",
    "INCONCLUSIVE",
)
LEGACY_STATUSES = ("SAT", "UNSAT", "OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "TIMEOUT", "ERROR")


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"solver outcome v2 value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class ProviderTermination:
    reason: str
    raw_status: str = ""
    raw_status_code: str = ""
    raw_message: str = ""
    limit_value: float | int | None = None
    limit_unit: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    contract_id: str = SOLVER_TERMINATION_V2_CONTRACT_ID
    contract_version: str = SOLVER_TERMINATION_V2_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != SOLVER_TERMINATION_V2_CONTRACT_ID or self.contract_version != SOLVER_TERMINATION_V2_CONTRACT_VERSION:
            raise ValueError("unsupported solver termination v2 contract")
        if self.reason not in TERMINATION_REASONS:
            raise ValueError(f"invalid termination reason: {self.reason}")
        object.__setattr__(self, "raw_status", str(self.raw_status))
        object.__setattr__(self, "raw_status_code", str(self.raw_status_code))
        object.__setattr__(self, "raw_message", str(self.raw_message))
        object.__setattr__(self, "limit_unit", str(self.limit_unit))
        if self.limit_value is not None:
            if isinstance(self.limit_value, bool):
                raise ValueError("termination limit_value must be numeric")
            object.__setattr__(self, "limit_value", float(self.limit_value))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "reason": self.reason,
            "raw_status": self.raw_status,
            "raw_status_code": self.raw_status_code,
            "raw_message": self.raw_message,
            "limit_value": self.limit_value,
            "limit_unit": self.limit_unit,
            "metadata": _jsonable(self.metadata),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProviderTermination":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class SolverEvidenceGrade:
    grade: str
    proof_status: str
    certificate_ids: tuple[str, ...] = ()
    checker_ids: tuple[str, ...] = ()
    validation_evidence_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    contract_id: str = SOLVER_EVIDENCE_GRADE_CONTRACT_ID
    contract_version: str = SOLVER_EVIDENCE_GRADE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != SOLVER_EVIDENCE_GRADE_CONTRACT_ID or self.contract_version != SOLVER_EVIDENCE_GRADE_CONTRACT_VERSION:
            raise ValueError("unsupported solver evidence-grade contract")
        if self.grade not in EVIDENCE_GRADES:
            raise ValueError(f"invalid solver evidence grade: {self.grade}")
        if self.proof_status not in PROOF_STATUSES:
            raise ValueError(f"invalid solver proof status: {self.proof_status}")
        object.__setattr__(self, "certificate_ids", _uniq(self.certificate_ids))
        object.__setattr__(self, "checker_ids", _uniq(self.checker_ids))
        object.__setattr__(self, "validation_evidence_ids", _uniq(self.validation_evidence_ids))
        object.__setattr__(self, "diagnostics", _uniq(self.diagnostics))
        if self.grade == "CHECKED_CERTIFICATE":
            if self.proof_status != "CHECKED_CERTIFICATE" or not self.certificate_ids or not self.checker_ids:
                raise ValueError("checked-certificate evidence grade requires checked proof, certificate, and checker identity")
        if self.proof_status == "CHECKED_CERTIFICATE" and self.grade != "CHECKED_CERTIFICATE":
            raise ValueError("checked proof status requires checked-certificate evidence grade")
        if self.proof_status == "UNCHECKED_CERTIFICATE" and not self.certificate_ids:
            raise ValueError("unchecked certificate status requires certificate identity")
        if self.grade == "INDEPENDENTLY_VALIDATED" and not self.validation_evidence_ids:
            raise ValueError("independently validated evidence grade requires validation Evidence")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "grade": self.grade,
            "proof_status": self.proof_status,
            "certificate_ids": list(self.certificate_ids),
            "checker_ids": list(self.checker_ids),
            "validation_evidence_ids": list(self.validation_evidence_ids),
            "diagnostics": list(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverEvidenceGrade":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        for name in ("certificate_ids", "checker_ids", "validation_evidence_ids", "diagnostics"):
            payload[name] = tuple(payload.get(name) or ())
        return cls(**payload)


@dataclass(frozen=True)
class SolverOutcomeV2:
    source_result_id: str
    source_result_fingerprint: str
    request_id: str
    request_fingerprint: str
    model_fingerprint: str
    provider_id: str
    provider_implementation: str
    provider_version: str
    legacy_status: str
    termination: ProviderTermination | Mapping[str, Any]
    solution_status: str
    incumbent_status: str
    optimality_claim: str
    evidence: SolverEvidenceGrade | Mapping[str, Any]
    objective_value: float | None = None
    best_bound: float | None = None
    relative_gap: float | None = None
    wall_time_ms: int = 0
    statistics: Mapping[str, Any] = field(default_factory=dict)
    source_diagnostics: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    outcome_id: str = ""
    contract_id: str = SOLVER_OUTCOME_V2_CONTRACT_ID
    contract_version: str = SOLVER_OUTCOME_V2_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "source_result_id",
            "source_result_fingerprint",
            "request_id",
            "request_fingerprint",
            "model_fingerprint",
            "provider_id",
            "provider_implementation",
            "provider_version",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SOLVER_OUTCOME_V2_CONTRACT_ID or self.contract_version != SOLVER_OUTCOME_V2_CONTRACT_VERSION:
            raise ValueError("unsupported solver outcome v2 contract")
        if self.legacy_status not in LEGACY_STATUSES:
            raise ValueError(f"invalid legacy solver status: {self.legacy_status}")
        termination = self.termination if isinstance(self.termination, ProviderTermination) else ProviderTermination.from_dict(self.termination)
        evidence = self.evidence if isinstance(self.evidence, SolverEvidenceGrade) else SolverEvidenceGrade.from_dict(self.evidence)
        if self.solution_status not in SOLUTION_STATUSES:
            raise ValueError(f"invalid solution status: {self.solution_status}")
        if self.incumbent_status not in INCUMBENT_STATUSES:
            raise ValueError(f"invalid incumbent status: {self.incumbent_status}")
        if self.optimality_claim not in OPTIMALITY_CLAIMS:
            raise ValueError(f"invalid optimality claim: {self.optimality_claim}")
        if self.solution_status == "FEASIBLE" and self.incumbent_status != "PRESENT":
            raise ValueError("feasible outcome requires a present incumbent")
        if self.solution_status == "INFEASIBLE" and self.incumbent_status == "PRESENT":
            raise ValueError("infeasible outcome cannot carry an incumbent")
        if self.optimality_claim == "CLAIMED_OPTIMAL" and self.solution_status != "FEASIBLE":
            raise ValueError("optimality claim requires a feasible incumbent")
        if int(self.wall_time_ms) < 0:
            raise ValueError("solver outcome wall_time_ms must be non-negative")
        object.__setattr__(self, "termination", termination)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "wall_time_ms", int(self.wall_time_ms))
        object.__setattr__(self, "statistics", _jsonable(dict(self.statistics)))
        object.__setattr__(self, "source_diagnostics", _uniq(self.source_diagnostics))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.outcome_id:
            object.__setattr__(self, "outcome_id", f"solver-outcome-v2-{semantic_fingerprint(self.identity_payload())[:24]}")

    @property
    def has_decisive_negative_proof(self) -> bool:
        return self.solution_status == "INFEASIBLE" and self.evidence.proof_status == "CHECKED_CERTIFICATE"

    @property
    def has_proven_optimality(self) -> bool:
        return self.optimality_claim == "CLAIMED_OPTIMAL" and self.evidence.proof_status == "CHECKED_CERTIFICATE"

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "source_result_id": self.source_result_id,
            "source_result_fingerprint": self.source_result_fingerprint,
            "request_id": self.request_id,
            "request_fingerprint": self.request_fingerprint,
            "model_fingerprint": self.model_fingerprint,
            "provider_id": self.provider_id,
            "provider_implementation": self.provider_implementation,
            "provider_version": self.provider_version,
            "legacy_status": self.legacy_status,
            "termination": self.termination.to_dict(),
            "solution_status": self.solution_status,
            "incumbent_status": self.incumbent_status,
            "optimality_claim": self.optimality_claim,
            "evidence": self.evidence.to_dict(),
            "objective_value": self.objective_value,
            "best_bound": self.best_bound,
            "relative_gap": self.relative_gap,
            "wall_time_ms": self.wall_time_ms,
            "statistics": _jsonable(self.statistics),
            "source_diagnostics": list(self.source_diagnostics),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"outcome_id": self.outcome_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            **self.identity_payload(),
            "has_decisive_negative_proof": self.has_decisive_negative_proof,
            "has_proven_optimality": self.has_proven_optimality,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverOutcomeV2":
        payload = deepcopy(dict(value))
        for key in ("fingerprint", "has_decisive_negative_proof", "has_proven_optimality"):
            payload.pop(key, None)
        payload["source_diagnostics"] = tuple(payload.get("source_diagnostics") or ())
        return cls(**payload)


def legacy_termination(status: str) -> ProviderTermination:
    if status == "TIMEOUT":
        return ProviderTermination("TIME_LIMIT", raw_status=status)
    if status == "ERROR":
        return ProviderTermination("INTERNAL_ERROR", raw_status=status)
    if status == "UNKNOWN":
        return ProviderTermination("UNKNOWN", raw_status=status)
    return ProviderTermination("COMPLETED", raw_status=status)


def _legacy_solution_axes(result: OptimizationResult) -> tuple[str, str, str]:
    has_assignment = bool(result.assignment)
    if result.status in {"SAT", "FEASIBLE", "OPTIMAL"}:
        if not has_assignment:
            raise ValueError(f"legacy status {result.status} requires assignment before v2 normalization")
        optimality = "CLAIMED_OPTIMAL" if result.status == "OPTIMAL" else ("NOT_APPLICABLE" if result.status == "SAT" else "NOT_CLAIMED")
        return "FEASIBLE", "PRESENT", optimality
    if result.status in {"UNSAT", "INFEASIBLE"}:
        return "INFEASIBLE", "ABSENT", "NOT_APPLICABLE" if result.status == "UNSAT" else "NOT_CLAIMED"
    if result.status in {"TIMEOUT", "UNKNOWN", "ERROR"}:
        if has_assignment:
            return "FEASIBLE", "PRESENT", "NOT_CLAIMED"
        return "UNKNOWN", "ABSENT", "UNKNOWN"
    raise ValueError(f"unsupported legacy optimization status: {result.status}")


def normalize_optimization_result_v2(
    result: OptimizationResult | Mapping[str, Any],
    *,
    termination: ProviderTermination | Mapping[str, Any] | None = None,
    evidence: SolverEvidenceGrade | Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> SolverOutcomeV2:
    source = result if isinstance(result, OptimizationResult) else OptimizationResult.from_dict(result)
    solution_status, incumbent_status, optimality_claim = _legacy_solution_axes(source)
    effective_termination = legacy_termination(source.status) if termination is None else (
        termination if isinstance(termination, ProviderTermination) else ProviderTermination.from_dict(termination)
    )
    effective_evidence = SolverEvidenceGrade("PROVIDER_ASSERTED", "NO_CERTIFICATE") if evidence is None else (
        evidence if isinstance(evidence, SolverEvidenceGrade) else SolverEvidenceGrade.from_dict(evidence)
    )
    return SolverOutcomeV2(
        source.result_id,
        source.fingerprint,
        source.request_id,
        source.request_fingerprint,
        source.model_fingerprint,
        source.solver.provider_id,
        source.solver.implementation,
        source.solver.version,
        source.status,
        effective_termination,
        solution_status,
        incumbent_status,
        optimality_claim,
        effective_evidence,
        source.objective_value,
        source.best_bound,
        source.relative_gap,
        source.wall_time_ms,
        deepcopy(source.statistics),
        tuple(source.diagnostics),
        {"legacy_metadata": deepcopy(source.metadata), **dict(metadata or {})},
    )


def solver_outcome_v2_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_OUTCOME_V2_CONTRACT_ID,
        "contract_version": SOLVER_OUTCOME_V2_CONTRACT_VERSION,
        "termination_contract_id": SOLVER_TERMINATION_V2_CONTRACT_ID,
        "evidence_grade_contract_id": SOLVER_EVIDENCE_GRADE_CONTRACT_ID,
        "stability": SOLVER_OUTCOME_V2_STABILITY,
        "legacy_result": "PRESERVED_AND_FINGERPRINT_BOUND",
        "axes": ["termination", "solution_status", "incumbent_status", "optimality_claim", "proof_status", "evidence_grade"],
        "timeout_with_incumbent": "FEASIBLE_INCUMBENT_PRESERVED_SEPARATELY_FROM_TIME_LIMIT",
        "provider_optimal_status": "CLAIMED_OPTIMAL_NOT_PROVEN_OPTIMAL_WITHOUT_CHECKED_CERTIFICATE",
        "negative_status": "INFEASIBLE_NOT_DECISIVE_WITHOUT_CHECKED_CERTIFICATE_WHERE_PROOF_IS_REQUIRED",
        "raw_provider_status": "PRESERVED_VERBATIM_IN_TERMINATION_RECORD",
        "bounds_and_gap": "PRESERVED_WITHOUT_REINTERPRETATION",
        "status_mapping": "EXPLICIT_PROVIDER_MAPPING_OR_CONSERVATIVE_LEGACY_MAPPING_ONLY",
        "truth_authority": "NONE",
    }


__all__ = [
    "SOLVER_OUTCOME_V2_CONTRACT_ID",
    "SOLVER_OUTCOME_V2_CONTRACT_VERSION",
    "SOLVER_TERMINATION_V2_CONTRACT_ID",
    "SOLVER_EVIDENCE_GRADE_CONTRACT_ID",
    "TERMINATION_REASONS",
    "SOLUTION_STATUSES",
    "INCUMBENT_STATUSES",
    "OPTIMALITY_CLAIMS",
    "PROOF_STATUSES",
    "EVIDENCE_GRADES",
    "ProviderTermination",
    "SolverEvidenceGrade",
    "SolverOutcomeV2",
    "legacy_termination",
    "normalize_optimization_result_v2",
    "solver_outcome_v2_contract",
]
