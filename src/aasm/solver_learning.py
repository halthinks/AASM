from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .optimization import (
    BooleanLiteral,
    OptimizationModel,
    objective_value,
    validate_optimization_solution,
)
from .semantic_result import semantic_fingerprint
from .solution_pools import (
    EnumerationCompletenessCertificate,
    EnumerationCursor,
    SolutionPool,
    SolutionRecord,
    certify_complete_finite_enumeration,
    enumerate_finite_step,
    initial_enumeration_cursor,
)


SOLVER_LEARNING_CONTRACT_ID = "aasm.solver.learning.v1"
SOLVER_LEARNING_CONTRACT_VERSION = "0.1.0"
SOLVER_LEARNING_STABILITY = "FOUNDATION_EXPERIMENTAL"
SOLVER_LEARNING_CHECKER_ID = "aasm.checker.solver-learning-finite.v1"
SOLVER_LEARNING_CHECKER_VERSION = "0.1.0"

SOLVER_LEARNING_KINDS = (
    "NO_GOOD",
    "UNSAT_CORE",
    "BOUND",
    "INCUMBENT",
    "WARM_START",
    "NATIVE_ACCELERATOR",
)
CORRECTNESS_SENSITIVE_KINDS = ("NO_GOOD", "UNSAT_CORE", "BOUND")
PERFORMANCE_HINT_KINDS = ("INCUMBENT", "WARM_START", "NATIVE_ACCELERATOR")
VALIDATION_STATUSES = ("PASS", "FAIL", "INCONCLUSIVE", "UNSUPPORTED")


def solver_learning_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_LEARNING_CONTRACT_ID,
        "contract_version": SOLVER_LEARNING_CONTRACT_VERSION,
        "stability": SOLVER_LEARNING_STABILITY,
        "kinds": list(SOLVER_LEARNING_KINDS),
        "correctness_sensitive": list(CORRECTNESS_SENSITIVE_KINDS),
        "performance_hints": list(PERFORMANCE_HINT_KINDS),
        "cross_run_transport": "EXISTING_AASM_V48_REUSE_RESULT_ENVELOPE",
        "cross_run_authority_transfer": "NEVER",
        "cross_run_admission_implies_truth": False,
        "pruning_application": "LOCAL_REVALIDATION_REQUIRED",
        "performance_hint_authority": "NEVER_TRUTH_OR_POLICY",
        "model_compatibility": "EXACT_MODEL_FINGERPRINT",
        "native_accelerator_compatibility": "EXACT_BACKEND_VERSION_AND_ENVIRONMENT",
    }


def _canonical_literals(payload: Mapping[str, Any]) -> dict[str, Any]:
    raw = payload.get("literals")
    if not isinstance(raw, (list, tuple)) or not raw:
        raise ValueError("NO_GOOD/UNSAT_CORE solver learning requires literals")
    literals = tuple(
        row if isinstance(row, BooleanLiteral) else BooleanLiteral.from_dict(row)
        for row in raw
    )
    ids = [row.variable_id for row in literals]
    if len(ids) != len(set(ids)):
        raise ValueError("solver learning literals must reference each variable at most once")
    ordered = tuple(sorted(literals, key=lambda row: (row.variable_id, not row.positive)))
    return {"literals": [row.to_dict() for row in ordered]}


def _canonical_payload(kind: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    if kind in {"NO_GOOD", "UNSAT_CORE"}:
        return _canonical_literals(data)
    if kind == "BOUND":
        bound_type = str(data.get("bound_type", "")).upper()
        if bound_type not in {"LOWER", "UPPER"}:
            raise ValueError("BOUND solver learning requires bound_type LOWER or UPPER")
        if "value" not in data:
            raise ValueError("BOUND solver learning requires value")
        tolerance = float(data.get("tolerance", 0.0))
        if tolerance < 0:
            raise ValueError("BOUND tolerance must be non-negative")
        return {"bound_type": bound_type, "value": float(data["value"]), "tolerance": tolerance}
    if kind in {"INCUMBENT", "WARM_START"}:
        assignment = data.get("assignment")
        if not isinstance(assignment, Mapping) or not assignment:
            raise ValueError(f"{kind} solver learning requires assignment")
        canonical = {str(key): float(value) for key, value in sorted(assignment.items())}
        out: dict[str, Any] = {"assignment": canonical}
        if data.get("objective") is not None:
            out["objective"] = float(data["objective"])
        return out
    if kind == "NATIVE_ACCELERATOR":
        required = ("backend_id", "backend_version", "state_fingerprint")
        missing = [name for name in required if not str(data.get(name, "")).strip()]
        if missing:
            raise ValueError(f"NATIVE_ACCELERATOR solver learning missing {missing}")
        return {
            "backend_id": str(data["backend_id"]),
            "backend_version": str(data["backend_version"]),
            "state_fingerprint": str(data["state_fingerprint"]),
            "state_ref": str(data.get("state_ref", "")),
        }
    raise ValueError(f"unsupported solver learning kind: {kind}")


@dataclass(frozen=True)
class SolverLearningArtifact:
    learning_kind: str
    model_fingerprint: str
    solver_family: str
    payload: Mapping[str, Any]
    source_result_fingerprint: str = ""
    source_evidence_ids: tuple[str, ...] = ()
    source_validation: str = "SOLVER_OBSERVED"
    provider_id: str = ""
    provider_version: str = ""
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    learning_id: str = ""

    def __post_init__(self) -> None:
        if self.learning_kind not in SOLVER_LEARNING_KINDS:
            raise ValueError(f"unsupported solver learning kind: {self.learning_kind}")
        if not self.model_fingerprint.strip():
            raise ValueError("solver learning requires model_fingerprint")
        if not self.solver_family.strip():
            raise ValueError("solver learning requires solver_family")
        payload = _canonical_payload(self.learning_kind, self.payload)
        object.__setattr__(self, "payload", payload)
        object.__setattr__(self, "source_evidence_ids", tuple(sorted(set(map(str, self.source_evidence_ids)))))
        object.__setattr__(self, "dependency_fingerprints", tuple(sorted(set(map(str, self.dependency_fingerprints)))))
        if self.learning_kind == "NATIVE_ACCELERATOR":
            provider_id = self.provider_id or str(payload["backend_id"])
            provider_version = self.provider_version or str(payload["backend_version"])
            if provider_id != payload["backend_id"] or provider_version != payload["backend_version"]:
                raise ValueError("native accelerator provider identity must match payload backend identity")
            object.__setattr__(self, "provider_id", provider_id)
            object.__setattr__(self, "provider_version", provider_version)
        if not self.learning_id:
            object.__setattr__(self, "learning_id", f"solver-learning-{semantic_fingerprint(self.identity_payload())[:24]}")

    @property
    def learning_class(self) -> str:
        return "CORRECTNESS_SENSITIVE" if self.learning_kind in CORRECTNESS_SENSITIVE_KINDS else "PERFORMANCE_HINT"

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": SOLVER_LEARNING_CONTRACT_ID,
            "contract_version": SOLVER_LEARNING_CONTRACT_VERSION,
            "learning_kind": self.learning_kind,
            "learning_class": self.learning_class,
            "model_fingerprint": self.model_fingerprint,
            "solver_family": self.solver_family,
            "payload": dict(self.payload),
            "source_result_fingerprint": self.source_result_fingerprint,
            "source_evidence_ids": list(self.source_evidence_ids),
            "source_validation": self.source_validation,
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "environment_fingerprint": self.environment_fingerprint,
            "dependency_fingerprints": list(self.dependency_fingerprints),
            "metadata": dict(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"learning_id": self.learning_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"learning_id": self.learning_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverLearningArtifact":
        payload = dict(value)
        payload.pop("fingerprint", None)
        payload.pop("contract_id", None)
        payload.pop("contract_version", None)
        payload.pop("learning_class", None)
        payload["source_evidence_ids"] = tuple(payload.get("source_evidence_ids") or ())
        payload["dependency_fingerprints"] = tuple(payload.get("dependency_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SolverLearningValidation:
    learning_id: str
    model_fingerprint: str
    status: str
    application_authority: str
    checker_id: str = SOLVER_LEARNING_CHECKER_ID
    checker_version: str = SOLVER_LEARNING_CHECKER_VERSION
    enumeration_certificate_id: str = ""
    diagnostics: tuple[str, ...] = ()
    details: Mapping[str, Any] = field(default_factory=dict)
    validation_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in VALIDATION_STATUSES:
            raise ValueError(f"unsupported solver learning validation status: {self.status}")
        object.__setattr__(self, "diagnostics", tuple(map(str, self.diagnostics)))
        if not self.validation_id:
            object.__setattr__(self, "validation_id", f"solver-learning-validation-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "learning_id": self.learning_id,
            "model_fingerprint": self.model_fingerprint,
            "status": self.status,
            "application_authority": self.application_authority,
            "checker_id": self.checker_id,
            "checker_version": self.checker_version,
            "enumeration_certificate_id": self.enumeration_certificate_id,
            "diagnostics": list(self.diagnostics),
            "details": dict(self.details),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"validation_id": self.validation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"validation_id": self.validation_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def _complete_finite_pool(
    model: OptimizationModel,
    *,
    learning_id: str,
    max_total_states: int,
    max_states_per_step: int,
) -> tuple[SolutionPool, EnumerationCursor, EnumerationCompletenessCertificate]:
    pool = SolutionPool(
        model.fingerprint,
        "COMPLETE_FINITE_ENUMERATION",
        lineage={"solver_learning_validation": learning_id},
    )
    cursor = initial_enumeration_cursor(
        model,
        pool.pool_id,
        pool.mode,
        max_total_states=max_total_states,
    )
    solutions: list[SolutionRecord] = []
    exclusion_ids: set[str] = set()
    while not cursor.exhausted:
        step = enumerate_finite_step(
            model,
            pool.pool_id,
            cursor=cursor,
            existing_solutions=solutions,
            max_states_per_step=max_states_per_step,
            max_total_states=max_total_states,
        )
        solutions.extend(step["accepted"])
        exclusion_ids.update(row.exclusion_id for row in step["exclusions"])
        cursor = step["cursor"]
    pending = SolutionPool(
        model.fingerprint,
        pool.mode,
        tuple(solutions),
        tuple(sorted(exclusion_ids)),
        "EXHAUSTED_PENDING_CERTIFICATION",
        cursor.fingerprint,
        lineage=pool.lineage,
        pool_id=pool.pool_id,
    )
    certificate = certify_complete_finite_enumeration(
        model,
        pending,
        cursor=cursor,
        max_total_states=max_total_states,
    )
    complete = SolutionPool(
        model.fingerprint,
        pool.mode,
        tuple(solutions),
        tuple(sorted(exclusion_ids)),
        "COMPLETE" if certificate.status == "PASS" else "FAILED_COMPLETENESS",
        cursor.fingerprint,
        certificate.certificate_id if certificate.status == "PASS" else "",
        pool.lineage,
        pool.pool_id,
    )
    return complete, cursor, certificate


def _assignment_matches_literals(assignment: Mapping[str, float], literals: list[Mapping[str, Any]]) -> bool:
    for row in literals:
        variable_id = str(row["variable_id"])
        if variable_id not in assignment:
            return False
        bit = bool(round(float(assignment[variable_id])))
        if bit != bool(row.get("positive", True)):
            return False
    return True


def revalidate_finite_solver_learning(
    artifact: SolverLearningArtifact,
    model: OptimizationModel,
    *,
    max_total_states: int = 100_000,
    max_states_per_step: int = 1_000,
) -> SolverLearningValidation:
    if artifact.model_fingerprint != model.fingerprint:
        return SolverLearningValidation(
            artifact.learning_id,
            model.fingerprint,
            "FAIL",
            "NONE",
            diagnostics=("MODEL_FINGERPRINT_MISMATCH",),
        )
    if artifact.solver_family != model.solver_family:
        return SolverLearningValidation(
            artifact.learning_id,
            model.fingerprint,
            "FAIL",
            "NONE",
            diagnostics=("SOLVER_FAMILY_MISMATCH",),
        )

    if artifact.learning_kind in {"INCUMBENT", "WARM_START"}:
        assignment = artifact.payload["assignment"]
        try:
            validate_optimization_solution(model, assignment)
        except ValueError as exc:
            return SolverLearningValidation(
                artifact.learning_id,
                model.fingerprint,
                "FAIL",
                "NONE",
                diagnostics=(f"INFEASIBLE_HINT:{exc}",),
            )
        value = objective_value(model, assignment)
        expected = artifact.payload.get("objective")
        if expected is not None and (value is None or abs(float(value) - float(expected)) > 1e-9):
            return SolverLearningValidation(
                artifact.learning_id,
                model.fingerprint,
                "FAIL",
                "NONE",
                diagnostics=("OBJECTIVE_VALUE_MISMATCH",),
            )
        return SolverLearningValidation(
            artifact.learning_id,
            model.fingerprint,
            "PASS",
            "PERFORMANCE_HINT_ONLY",
            details={"objective": value, "truth_authority": "NONE"},
        )

    if artifact.learning_kind == "NATIVE_ACCELERATOR":
        return SolverLearningValidation(
            artifact.learning_id,
            model.fingerprint,
            "UNSUPPORTED",
            "NONE",
            diagnostics=("NATIVE_ACCELERATOR_REQUIRES_EXACT_BACKEND_VALIDATION",),
        )

    pool, _, certificate = _complete_finite_pool(
        model,
        learning_id=artifact.learning_id,
        max_total_states=max_total_states,
        max_states_per_step=max_states_per_step,
    )
    if certificate.status != "PASS":
        return SolverLearningValidation(
            artifact.learning_id,
            model.fingerprint,
            "INCONCLUSIVE",
            "NONE",
            enumeration_certificate_id=certificate.certificate_id,
            diagnostics=tuple(certificate.diagnostics),
        )

    if artifact.learning_kind in {"NO_GOOD", "UNSAT_CORE"}:
        literals = list(artifact.payload["literals"])
        violating = [
            row.solution_id
            for row in pool.solutions
            if _assignment_matches_literals(row.assignment, literals)
        ]
        if violating:
            return SolverLearningValidation(
                artifact.learning_id,
                model.fingerprint,
                "FAIL",
                "NONE",
                enumeration_certificate_id=certificate.certificate_id,
                diagnostics=("LEARNED_PRUNING_WOULD_EXCLUDE_FEASIBLE_SOLUTIONS",),
                details={"violating_solution_ids": violating},
            )
        return SolverLearningValidation(
            artifact.learning_id,
            model.fingerprint,
            "PASS",
            "PRUNING_CERTIFIED_FOR_EXACT_MODEL",
            enumeration_certificate_id=certificate.certificate_id,
            details={"feasible_solution_count": len(pool.solutions)},
        )

    if artifact.learning_kind == "BOUND":
        if model.objective is None:
            return SolverLearningValidation(
                artifact.learning_id,
                model.fingerprint,
                "FAIL",
                "NONE",
                enumeration_certificate_id=certificate.certificate_id,
                diagnostics=("BOUND_REQUIRES_MODEL_OBJECTIVE",),
            )
        if not pool.solutions:
            return SolverLearningValidation(
                artifact.learning_id,
                model.fingerprint,
                "INCONCLUSIVE",
                "NONE",
                enumeration_certificate_id=certificate.certificate_id,
                diagnostics=("BOUND_ON_INFEASIBLE_MODEL_NOT_ACTIVATED",),
            )
        values = [float(row.objective) for row in pool.solutions if row.objective is not None]
        bound = float(artifact.payload["value"])
        tolerance = float(artifact.payload.get("tolerance", 0.0))
        if artifact.payload["bound_type"] == "LOWER":
            valid = min(values) >= bound - tolerance
        else:
            valid = max(values) <= bound + tolerance
        if not valid:
            return SolverLearningValidation(
                artifact.learning_id,
                model.fingerprint,
                "FAIL",
                "NONE",
                enumeration_certificate_id=certificate.certificate_id,
                diagnostics=("LEARNED_BOUND_FALSE_FOR_EXACT_MODEL",),
                details={"minimum": min(values), "maximum": max(values)},
            )
        return SolverLearningValidation(
            artifact.learning_id,
            model.fingerprint,
            "PASS",
            "PRUNING_CERTIFIED_FOR_EXACT_MODEL",
            enumeration_certificate_id=certificate.certificate_id,
            details={"minimum": min(values), "maximum": max(values)},
        )

    raise AssertionError(f"unhandled solver learning kind: {artifact.learning_kind}")


def validate_native_accelerator_hint(
    artifact: SolverLearningArtifact,
    model: OptimizationModel,
    *,
    provider_id: str,
    provider_version: str,
    environment_fingerprint: str = "",
) -> SolverLearningValidation:
    diagnostics: list[str] = []
    if artifact.learning_kind != "NATIVE_ACCELERATOR":
        diagnostics.append("NOT_NATIVE_ACCELERATOR")
    if artifact.model_fingerprint != model.fingerprint:
        diagnostics.append("MODEL_FINGERPRINT_MISMATCH")
    if artifact.solver_family != model.solver_family:
        diagnostics.append("SOLVER_FAMILY_MISMATCH")
    if artifact.provider_id != provider_id or artifact.provider_version != provider_version:
        diagnostics.append("BACKEND_IDENTITY_MISMATCH")
    if artifact.environment_fingerprint and artifact.environment_fingerprint != environment_fingerprint:
        diagnostics.append("ENVIRONMENT_FINGERPRINT_MISMATCH")
    return SolverLearningValidation(
        artifact.learning_id,
        model.fingerprint,
        "PASS" if not diagnostics else "FAIL",
        "PERFORMANCE_HINT_ONLY" if not diagnostics else "NONE",
        diagnostics=tuple(diagnostics),
        details={"truth_authority": "NONE", "state_fingerprint": artifact.payload.get("state_fingerprint", "")},
    )


__all__ = [
    "SOLVER_LEARNING_CONTRACT_ID",
    "SOLVER_LEARNING_CONTRACT_VERSION",
    "SOLVER_LEARNING_STABILITY",
    "SOLVER_LEARNING_CHECKER_ID",
    "SOLVER_LEARNING_CHECKER_VERSION",
    "SOLVER_LEARNING_KINDS",
    "CORRECTNESS_SENSITIVE_KINDS",
    "PERFORMANCE_HINT_KINDS",
    "SolverLearningArtifact",
    "SolverLearningValidation",
    "solver_learning_contract",
    "revalidate_finite_solver_learning",
    "validate_native_accelerator_hint",
]
