from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from math import isclose
from typing import Any, Mapping, Sequence

from .optimization import (
    OptimizationRequest,
    OptimizationResult,
    objective_value,
    validate_optimization_solution,
)
from .semantic_result import semantic_fingerprint


SOLVER_OUTCOME_V2_CONTRACT_ID = "aasm.solver.outcome.v2"
SOLVER_OUTCOME_V2_CONTRACT_VERSION = "0.1.0"
SOLVER_STATUS_V2_CONTRACT_ID = "aasm.solver.status.v2"
SOLVER_STATUS_V2_CONTRACT_VERSION = "0.1.0"
SOLVER_TERMINATION_V2_CONTRACT_ID = "aasm.solver.termination.v2"
SOLVER_TERMINATION_V2_CONTRACT_VERSION = "0.1.0"
SOLVER_EVIDENCE_GRADE_CONTRACT_ID = "aasm.solver.evidence-grade.v1"
SOLVER_EVIDENCE_GRADE_CONTRACT_VERSION = "0.1.0"
SOLVER_LEGACY_PROJECTION_CONTRACT_ID = "aasm.solver.status-v1-projection.v1"
SOLVER_LEGACY_PROJECTION_CONTRACT_VERSION = "0.1.0"
SOLVER_OUTCOME_V2_STABILITY = "QUALIFICATION_CANDIDATE"

TERMINATION_REASONS = (
    "COMPLETED",
    "TIME_LIMIT",
    "NODE_LIMIT",
    "ITERATION_LIMIT",
    "SOLUTION_LIMIT",
    "MEMORY_LIMIT",
    "OBJECTIVE_BOUND",
    "OBJECTIVE_TARGET",
    "USER_INTERRUPT",
    "NUMERICAL_FAILURE",
    "MODEL_INVALID",
    "PROVIDER_UNAVAILABLE",
    "UNSUPPORTED_FEATURE",
    "STALE_RESULT",
    "INTERNAL_ERROR",
    "UNKNOWN",
)

NORMALIZED_STATUSES = (
    "SAT",
    "UNSAT",
    "OPTIMAL",
    "FEASIBLE_NOT_PROVEN_OPTIMAL",
    "INFEASIBLE",
    "UNBOUNDED",
    "INFEASIBLE_OR_UNBOUNDED",
    "TIME_LIMIT_WITH_INCUMBENT",
    "TIME_LIMIT_NO_SOLUTION",
    "NODE_LIMIT_WITH_INCUMBENT",
    "NODE_LIMIT_NO_SOLUTION",
    "ITERATION_LIMIT_WITH_INCUMBENT",
    "ITERATION_LIMIT_NO_SOLUTION",
    "SOLUTION_LIMIT_WITH_INCUMBENT",
    "SOLUTION_LIMIT_NO_SOLUTION",
    "MEMORY_LIMIT_WITH_INCUMBENT",
    "MEMORY_LIMIT_NO_SOLUTION",
    "OBJECTIVE_BOUND_WITH_INCUMBENT",
    "OBJECTIVE_BOUND_NO_SOLUTION",
    "OBJECTIVE_TARGET_WITH_INCUMBENT",
    "OBJECTIVE_TARGET_NO_SOLUTION",
    "USER_INTERRUPT_WITH_INCUMBENT",
    "USER_INTERRUPT_NO_SOLUTION",
    "UNKNOWN_WITH_INCUMBENT",
    "UNKNOWN_NO_SOLUTION",
    "NUMERICAL_FAILURE",
    "MODEL_INVALID",
    "PROVIDER_UNAVAILABLE",
    "UNSUPPORTED_FEATURE",
    "STALE_RESULT",
    "INTERNAL_ERROR",
    "UNKNOWN",
)

SOLUTION_STATUSES = ("FEASIBLE", "INFEASIBLE", "UNBOUNDED", "INFEASIBLE_OR_UNBOUNDED", "UNKNOWN")
INCUMBENT_STATUSES = ("PRESENT", "ABSENT", "UNKNOWN")
INCUMBENT_VALIDATION_STATUSES = ("VALIDATED", "REJECTED", "NOT_PRESENT", "NOT_CHECKED")
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

_WITH_INCUMBENT = {status for status in NORMALIZED_STATUSES if status.endswith("_WITH_INCUMBENT")}
_NO_SOLUTION = {status for status in NORMALIZED_STATUSES if status.endswith("_NO_SOLUTION")}
_FEASIBLE_STATUSES = {"SAT", "OPTIMAL", "FEASIBLE_NOT_PROVEN_OPTIMAL", *_WITH_INCUMBENT, "UNKNOWN_WITH_INCUMBENT"}
_NEGATIVE_STATUSES = {"UNSAT", "INFEASIBLE"}


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
class LegacyStatusProjection:
    status: str
    lossy: bool
    reason: str
    contract_id: str = SOLVER_LEGACY_PROJECTION_CONTRACT_ID
    contract_version: str = SOLVER_LEGACY_PROJECTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.status not in LEGACY_STATUSES:
            raise ValueError(f"invalid legacy projection status: {self.status}")
        if self.contract_id != SOLVER_LEGACY_PROJECTION_CONTRACT_ID or self.contract_version != SOLVER_LEGACY_PROJECTION_CONTRACT_VERSION:
            raise ValueError("unsupported solver legacy projection contract")
        object.__setattr__(self, "reason", _required(self.reason, "legacy projection reason"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "status": self.status,
            "lossy": bool(self.lossy),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LegacyStatusProjection":
        return cls(**dict(value))


def project_v2_to_legacy_status(normalized_status: str) -> LegacyStatusProjection:
    if normalized_status not in NORMALIZED_STATUSES:
        raise ValueError(f"invalid normalized solver status: {normalized_status}")
    exact = {
        "SAT": "SAT",
        "UNSAT": "UNSAT",
        "OPTIMAL": "OPTIMAL",
        "INFEASIBLE": "INFEASIBLE",
    }
    if normalized_status in exact:
        return LegacyStatusProjection(exact[normalized_status], False, "exact v2/v1 status correspondence")
    if normalized_status == "FEASIBLE_NOT_PROVEN_OPTIMAL":
        return LegacyStatusProjection("FEASIBLE", True, "v1 cannot preserve explicit not-proven-optimal semantics")
    if normalized_status.startswith("TIME_LIMIT_"):
        return LegacyStatusProjection("TIMEOUT", True, "v1 timeout collapses incumbent distinction")
    if normalized_status in _WITH_INCUMBENT or normalized_status == "UNKNOWN_WITH_INCUMBENT":
        return LegacyStatusProjection("FEASIBLE", True, "v1 feasible collapses non-time termination cause and incumbent validation detail")
    if normalized_status in _NO_SOLUTION or normalized_status in {"UNKNOWN_NO_SOLUTION", "UNBOUNDED", "INFEASIBLE_OR_UNBOUNDED", "STALE_RESULT", "UNKNOWN"}:
        return LegacyStatusProjection("UNKNOWN", True, "v1 unknown cannot preserve the detailed v2 termination/solution state")
    if normalized_status in {"NUMERICAL_FAILURE", "MODEL_INVALID", "PROVIDER_UNAVAILABLE", "UNSUPPORTED_FEATURE", "INTERNAL_ERROR"}:
        return LegacyStatusProjection("ERROR", True, "v1 error collapses distinct v2 failure classes")
    raise ValueError(f"no legacy projection rule for normalized status: {normalized_status}")


def _limit_status(reason: str, has_incumbent: bool) -> str | None:
    prefixes = {
        "TIME_LIMIT": "TIME_LIMIT",
        "NODE_LIMIT": "NODE_LIMIT",
        "ITERATION_LIMIT": "ITERATION_LIMIT",
        "SOLUTION_LIMIT": "SOLUTION_LIMIT",
        "MEMORY_LIMIT": "MEMORY_LIMIT",
        "OBJECTIVE_BOUND": "OBJECTIVE_BOUND",
        "OBJECTIVE_TARGET": "OBJECTIVE_TARGET",
        "USER_INTERRUPT": "USER_INTERRUPT",
    }
    prefix = prefixes.get(reason)
    if prefix is None:
        return None
    return f"{prefix}_{'WITH_INCUMBENT' if has_incumbent else 'NO_SOLUTION'}"


def legacy_termination(status: str) -> ProviderTermination:
    if status == "TIMEOUT":
        return ProviderTermination("TIME_LIMIT", raw_status=status, metadata={"projection": "LEGACY_V1_LOSSY"})
    if status == "ERROR":
        return ProviderTermination("INTERNAL_ERROR", raw_status=status, metadata={"projection": "LEGACY_V1_LOSSY"})
    if status == "UNKNOWN":
        return ProviderTermination("UNKNOWN", raw_status=status, metadata={"projection": "LEGACY_V1_LOSSY"})
    return ProviderTermination("COMPLETED", raw_status=status, metadata={"projection": "LEGACY_V1_LOSSY"})


def _validate_incumbent(source: OptimizationResult, request: OptimizationRequest | None) -> tuple[str, str]:
    if not source.assignment:
        return "ABSENT", "NOT_PRESENT"
    if request is None:
        raise ValueError("solver outcome with incumbent requires the exact OptimizationRequest for independent validation")
    if source.request_id != request.request_id or source.request_fingerprint != request.fingerprint:
        raise ValueError("solver outcome request binding mismatch")
    if source.model_fingerprint != request.model.fingerprint:
        raise ValueError("solver outcome model binding mismatch")
    validate_optimization_solution(request.model, source.assignment)
    expected = objective_value(request.model, source.assignment)
    if expected is not None:
        if source.objective_value is None or not isclose(float(source.objective_value), float(expected), rel_tol=1e-7, abs_tol=1e-7):
            raise ValueError("solver incumbent objective value does not match independently evaluated assignment")
    return "PRESENT", "VALIDATED"


def _derive_status(source: OptimizationResult, termination: ProviderTermination, has_incumbent: bool, request: OptimizationRequest | None) -> str:
    limit = _limit_status(termination.reason, has_incumbent)
    if limit is not None:
        return limit
    explicit_failures = {
        "NUMERICAL_FAILURE": "NUMERICAL_FAILURE",
        "MODEL_INVALID": "MODEL_INVALID",
        "PROVIDER_UNAVAILABLE": "PROVIDER_UNAVAILABLE",
        "UNSUPPORTED_FEATURE": "UNSUPPORTED_FEATURE",
        "STALE_RESULT": "STALE_RESULT",
        "INTERNAL_ERROR": "INTERNAL_ERROR",
    }
    if termination.reason in explicit_failures:
        return explicit_failures[termination.reason]
    if source.status == "SAT":
        return "SAT"
    if source.status == "UNSAT":
        return "UNSAT"
    if source.status == "OPTIMAL":
        return "OPTIMAL"
    if source.status == "FEASIBLE":
        return "FEASIBLE_NOT_PROVEN_OPTIMAL"
    if source.status == "INFEASIBLE":
        return "INFEASIBLE"
    if source.status == "TIMEOUT":
        return "TIME_LIMIT_WITH_INCUMBENT" if has_incumbent else "TIME_LIMIT_NO_SOLUTION"
    if source.status == "UNKNOWN":
        return "UNKNOWN_WITH_INCUMBENT" if has_incumbent else "UNKNOWN_NO_SOLUTION"
    if source.status == "ERROR":
        if termination.reason == "UNKNOWN":
            raise ValueError("legacy ERROR requires an explicit v2 failure classification; ERROR is not a v2 catch-all")
        return "INTERNAL_ERROR"
    raise ValueError(f"unsupported legacy optimization status: {source.status}")


def _axes_for_status(normalized_status: str, has_incumbent: bool) -> tuple[str, str]:
    if normalized_status in _FEASIBLE_STATUSES:
        return "FEASIBLE", "CLAIMED_OPTIMAL" if normalized_status == "OPTIMAL" else ("NOT_APPLICABLE" if normalized_status == "SAT" else "NOT_CLAIMED")
    if normalized_status in _NEGATIVE_STATUSES:
        return "INFEASIBLE", "NOT_APPLICABLE" if normalized_status == "UNSAT" else "NOT_CLAIMED"
    if normalized_status == "UNBOUNDED":
        return "UNBOUNDED", "NOT_APPLICABLE"
    if normalized_status == "INFEASIBLE_OR_UNBOUNDED":
        return "INFEASIBLE_OR_UNBOUNDED", "NOT_APPLICABLE"
    return "UNKNOWN", "UNKNOWN"


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
    normalized_status: str
    legacy_projection: LegacyStatusProjection | Mapping[str, Any]
    termination: ProviderTermination | Mapping[str, Any]
    solution_status: str
    incumbent_status: str
    incumbent_validation: str
    optimality_claim: str
    evidence: SolverEvidenceGrade | Mapping[str, Any]
    provider_status_rule_id: str = ""
    provider_status_map_version: str = ""
    assignment_fingerprint: str = ""
    objective_value: float | None = None
    best_bound: float | None = None
    relative_gap: float | None = None
    primal_ray_present: bool = False
    primal_ray_checked: bool = False
    wall_time_ms: int = 0
    statistics: Mapping[str, Any] = field(default_factory=dict)
    source_diagnostics: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    outcome_id: str = ""
    contract_id: str = SOLVER_OUTCOME_V2_CONTRACT_ID
    contract_version: str = SOLVER_OUTCOME_V2_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "source_result_id", "source_result_fingerprint", "request_id", "request_fingerprint",
            "model_fingerprint", "provider_id", "provider_implementation", "provider_version",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SOLVER_OUTCOME_V2_CONTRACT_ID or self.contract_version != SOLVER_OUTCOME_V2_CONTRACT_VERSION:
            raise ValueError("unsupported solver outcome v2 contract")
        if self.normalized_status not in NORMALIZED_STATUSES:
            raise ValueError(f"invalid normalized solver status: {self.normalized_status}")
        termination = self.termination if isinstance(self.termination, ProviderTermination) else ProviderTermination.from_dict(self.termination)
        evidence = self.evidence if isinstance(self.evidence, SolverEvidenceGrade) else SolverEvidenceGrade.from_dict(self.evidence)
        projection = self.legacy_projection if isinstance(self.legacy_projection, LegacyStatusProjection) else LegacyStatusProjection.from_dict(self.legacy_projection)
        expected_projection = project_v2_to_legacy_status(self.normalized_status)
        if projection.status != expected_projection.status or projection.lossy != expected_projection.lossy:
            raise ValueError("legacy status projection is inconsistent with normalized v2 status")
        if self.solution_status not in SOLUTION_STATUSES:
            raise ValueError(f"invalid solution status: {self.solution_status}")
        if self.incumbent_status not in INCUMBENT_STATUSES:
            raise ValueError(f"invalid incumbent status: {self.incumbent_status}")
        if self.incumbent_validation not in INCUMBENT_VALIDATION_STATUSES:
            raise ValueError(f"invalid incumbent validation status: {self.incumbent_validation}")
        if self.optimality_claim not in OPTIMALITY_CLAIMS:
            raise ValueError(f"invalid optimality claim: {self.optimality_claim}")
        if self.normalized_status in _FEASIBLE_STATUSES:
            if self.incumbent_status != "PRESENT" or self.incumbent_validation != "VALIDATED" or not self.assignment_fingerprint:
                raise ValueError(f"{self.normalized_status} requires a nonempty independently validated incumbent")
        if self.normalized_status in _NO_SOLUTION or self.normalized_status in _NEGATIVE_STATUSES:
            if self.incumbent_status != "ABSENT" or self.incumbent_validation != "NOT_PRESENT":
                raise ValueError(f"{self.normalized_status} cannot carry an accepted incumbent")
        if self.normalized_status == "OPTIMAL":
            if self.optimality_claim != "CLAIMED_OPTIMAL" or termination.reason != "COMPLETED":
                raise ValueError("OPTIMAL requires a validated incumbent and provider optimal completion claim")
        if self.normalized_status in {"UNSAT", "INFEASIBLE"} and self.assignment_fingerprint:
            raise ValueError("UNSAT/INFEASIBLE cannot carry an assignment fingerprint")
        if self.primal_ray_checked and not self.primal_ray_present:
            raise ValueError("a checked primal ray must be present")
        if int(self.wall_time_ms) < 0:
            raise ValueError("solver outcome wall_time_ms must be non-negative")
        object.__setattr__(self, "termination", termination)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "legacy_projection", projection)
        object.__setattr__(self, "provider_status_rule_id", str(self.provider_status_rule_id))
        object.__setattr__(self, "provider_status_map_version", str(self.provider_status_map_version))
        object.__setattr__(self, "assignment_fingerprint", str(self.assignment_fingerprint))
        object.__setattr__(self, "wall_time_ms", int(self.wall_time_ms))
        object.__setattr__(self, "statistics", _jsonable(dict(self.statistics)))
        object.__setattr__(self, "source_diagnostics", _uniq(self.source_diagnostics))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.outcome_id:
            object.__setattr__(self, "outcome_id", f"solver-outcome-v2-{semantic_fingerprint(self.identity_payload())[:24]}")

    @property
    def has_decisive_negative_proof(self) -> bool:
        return self.normalized_status in {"UNSAT", "INFEASIBLE"} and self.evidence.proof_status == "CHECKED_CERTIFICATE"

    @property
    def has_proven_optimality(self) -> bool:
        return self.normalized_status == "OPTIMAL" and self.evidence.proof_status == "CHECKED_CERTIFICATE"

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
            "normalized_status": self.normalized_status,
            "legacy_projection": self.legacy_projection.to_dict(),
            "termination": self.termination.to_dict(),
            "solution_status": self.solution_status,
            "incumbent_status": self.incumbent_status,
            "incumbent_validation": self.incumbent_validation,
            "optimality_claim": self.optimality_claim,
            "evidence": self.evidence.to_dict(),
            "provider_status_rule_id": self.provider_status_rule_id,
            "provider_status_map_version": self.provider_status_map_version,
            "assignment_fingerprint": self.assignment_fingerprint,
            "objective_value": self.objective_value,
            "best_bound": self.best_bound,
            "relative_gap": self.relative_gap,
            "primal_ray_present": bool(self.primal_ray_present),
            "primal_ray_checked": bool(self.primal_ray_checked),
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


def normalize_optimization_result_v2(
    result: OptimizationResult | Mapping[str, Any],
    *,
    request: OptimizationRequest | Mapping[str, Any] | None = None,
    termination: ProviderTermination | Mapping[str, Any] | None = None,
    normalized_status: str | None = None,
    evidence: SolverEvidenceGrade | Mapping[str, Any] | None = None,
    provider_status_rule_id: str = "",
    provider_status_map_version: str = "",
    primal_ray_present: bool = False,
    primal_ray_checked: bool = False,
    metadata: Mapping[str, Any] | None = None,
) -> SolverOutcomeV2:
    source = result if isinstance(result, OptimizationResult) else OptimizationResult.from_dict(result)
    parsed_request = None if request is None else (request if isinstance(request, OptimizationRequest) else OptimizationRequest.from_dict(request))
    incumbent_status, incumbent_validation = _validate_incumbent(source, parsed_request)
    has_incumbent = incumbent_status == "PRESENT" and incumbent_validation == "VALIDATED"
    effective_termination = legacy_termination(source.status) if termination is None else (
        termination if isinstance(termination, ProviderTermination) else ProviderTermination.from_dict(termination)
    )
    status = normalized_status or _derive_status(source, effective_termination, has_incumbent, parsed_request)
    if status not in NORMALIZED_STATUSES:
        raise ValueError(f"invalid normalized solver status: {status}")
    solution_status, optimality_claim = _axes_for_status(status, has_incumbent)
    effective_evidence = SolverEvidenceGrade("PROVIDER_ASSERTED", "NO_CERTIFICATE") if evidence is None else (
        evidence if isinstance(evidence, SolverEvidenceGrade) else SolverEvidenceGrade.from_dict(evidence)
    )
    assignment_fp = semantic_fingerprint({"assignment": source.assignment}) if has_incumbent else ""
    if status in _FEASIBLE_STATUSES and not has_incumbent:
        raise ValueError(f"{status} requires an independently validated incumbent")
    if status in _NO_SOLUTION and has_incumbent:
        raise ValueError(f"{status} forbids an incumbent")
    if status == "OPTIMAL" and parsed_request is not None and parsed_request.model.objective is None:
        status = "SAT"
        solution_status, optimality_claim = _axes_for_status(status, has_incumbent)
    if status == "INFEASIBLE" and parsed_request is not None and parsed_request.model.objective is None:
        status = "UNSAT"
        solution_status, optimality_claim = _axes_for_status(status, has_incumbent)
    return SolverOutcomeV2(
        source.result_id,
        source.fingerprint,
        source.request_id,
        source.request_fingerprint,
        source.model_fingerprint,
        source.solver.provider_id,
        source.solver.implementation,
        source.solver.version,
        status,
        project_v2_to_legacy_status(status),
        effective_termination,
        solution_status,
        incumbent_status,
        incumbent_validation,
        optimality_claim,
        effective_evidence,
        provider_status_rule_id=provider_status_rule_id,
        provider_status_map_version=provider_status_map_version,
        assignment_fingerprint=assignment_fp,
        objective_value=source.objective_value,
        best_bound=source.best_bound,
        relative_gap=source.relative_gap,
        primal_ray_present=bool(primal_ray_present),
        primal_ray_checked=bool(primal_ray_checked),
        wall_time_ms=source.wall_time_ms,
        statistics=deepcopy(source.statistics),
        source_diagnostics=tuple(source.diagnostics),
        metadata={
            "source_legacy_status": source.status,
            "legacy_to_v2_projection": "LOSSY_UNLESS_EXACT_PROVIDER_STATUS_MAPPING_SUPPLIED",
            "legacy_metadata": deepcopy(source.metadata),
            **dict(metadata or {}),
        },
    )


def solver_outcome_v2_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_OUTCOME_V2_CONTRACT_ID,
        "contract_version": SOLVER_OUTCOME_V2_CONTRACT_VERSION,
        "status_contract_id": SOLVER_STATUS_V2_CONTRACT_ID,
        "status_contract_version": SOLVER_STATUS_V2_CONTRACT_VERSION,
        "termination_contract_id": SOLVER_TERMINATION_V2_CONTRACT_ID,
        "evidence_grade_contract_id": SOLVER_EVIDENCE_GRADE_CONTRACT_ID,
        "legacy_projection_contract_id": SOLVER_LEGACY_PROJECTION_CONTRACT_ID,
        "stability": SOLVER_OUTCOME_V2_STABILITY,
        "authoritative_detailed_status": "normalized_status",
        "legacy_result": "PRESERVED_AND_FINGERPRINT_BOUND",
        "legacy_projection": "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED",
        "axes": [
            "normalized_status", "termination", "solution_status", "incumbent_status",
            "incumbent_validation", "optimality_claim", "proof_status", "evidence_grade",
        ],
        "incumbent_admission": "NONEMPTY_ASSIGNMENT_MUST_PASS_AASM_INDEPENDENT_MODEL_VALIDATION",
        "provider_optimal_status": "PROVIDER_OPTIMAL_COMPLETION_PLUS_VALIDATED_INCUMBENT_NOT_INDEPENDENT_PROOF",
        "proof_certification": "STRICTLY_STRONGER_THAN_PROVIDER_OPTIMAL_STATUS",
        "raw_provider_status": "PRESERVED_VERBATIM_IN_TERMINATION_RECORD",
        "bounds_and_gap": "PRESERVED_WITHOUT_REINTERPRETATION",
        "model_invalid": "DISTINCT_FROM_INFEASIBLE",
        "numerical_failure": "DISTINCT_FROM_UNKNOWN",
        "stale_result": "DISTINCT_FAIL_CLOSED_STATUS",
        "status_mapping": "EXPLICIT_PROVIDER_MAPPING_OR_MARKED_LOSSY_LEGACY_PROJECTION_ONLY",
        "truth_authority": "NONE",
    }


__all__ = [
    "SOLVER_OUTCOME_V2_CONTRACT_ID", "SOLVER_OUTCOME_V2_CONTRACT_VERSION",
    "SOLVER_STATUS_V2_CONTRACT_ID", "SOLVER_STATUS_V2_CONTRACT_VERSION",
    "SOLVER_TERMINATION_V2_CONTRACT_ID", "SOLVER_EVIDENCE_GRADE_CONTRACT_ID",
    "SOLVER_LEGACY_PROJECTION_CONTRACT_ID", "TERMINATION_REASONS", "NORMALIZED_STATUSES",
    "SOLUTION_STATUSES", "INCUMBENT_STATUSES", "INCUMBENT_VALIDATION_STATUSES",
    "OPTIMALITY_CLAIMS", "PROOF_STATUSES", "EVIDENCE_GRADES", "ProviderTermination",
    "SolverEvidenceGrade", "LegacyStatusProjection", "SolverOutcomeV2", "legacy_termination",
    "project_v2_to_legacy_status", "normalize_optimization_result_v2", "solver_outcome_v2_contract",
]
