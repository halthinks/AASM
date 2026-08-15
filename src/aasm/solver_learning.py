from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .optimization import (
    BooleanLiteral,
    OptimizationConstraint,
    OptimizationModel,
    OptimizationRequest,
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
SOLVER_LEARNING_APPLICATION_CONTRACT_ID = "aasm.solver.learning.application.v1"
SOLVER_LEARNING_APPLICATION_CONTRACT_VERSION = "0.1.0"

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
SOLVER_LEARNING_APPLICATION_CLASSES = ("PRUNING_CONSTRAINTS", "PERFORMANCE_HINT")


def solver_learning_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_LEARNING_CONTRACT_ID,
        "contract_version": SOLVER_LEARNING_CONTRACT_VERSION,
        "stability": SOLVER_LEARNING_STABILITY,
        "application_contract_id": SOLVER_LEARNING_APPLICATION_CONTRACT_ID,
        "application_contract_version": SOLVER_LEARNING_APPLICATION_CONTRACT_VERSION,
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
        "application": "EXPLICIT_VALIDATED_ADAPTER_APPLICATION_ONLY",
        "application_truth_authority": "NONE",
        "application_policy_authority": "NONE",
        "solver_execution": "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY",
    }


def solver_learning_application_contract() -> dict[str, Any]:
    return {
        "contract_id": SOLVER_LEARNING_APPLICATION_CONTRACT_ID,
        "contract_version": SOLVER_LEARNING_APPLICATION_CONTRACT_VERSION,
        "application_classes": list(SOLVER_LEARNING_APPLICATION_CLASSES),
        "validation_required": "PASS_EXACT_ARTIFACT_AND_MODEL",
        "pruning_authority_required": "PRUNING_CERTIFIED_FOR_EXACT_MODEL",
        "performance_authority_required": "PERFORMANCE_HINT_ONLY",
        "truth_authority": "NONE",
        "policy_authority": "NONE",
        "pruning_lowering": "NEW_OPTIMIZATION_MODEL_EXISTING_PROVIDER_PATH",
        "performance_lowering": "EXPLICIT_PROVIDER_CONSUMED_HINT_ONLY",
        "current_assignment_hint_provider": "ortools-cp-sat",
        "native_accelerator_application": "UNSUPPORTED_UNTIL_EXPLICIT_PUBLIC_ADAPTER",
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

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverLearningValidation":
        payload = dict(value)
        payload.pop("fingerprint", None)
        payload["diagnostics"] = tuple(payload.get("diagnostics") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SolverLearningApplication:
    learning_id: str
    learning_fingerprint: str
    validation_id: str
    validation_fingerprint: str
    original_model_fingerprint: str
    application_class: str
    application_payload: Mapping[str, Any]
    transformed_model_fingerprint: str = ""
    provider_id: str = ""
    truth_authority: str = "NONE"
    policy_authority: str = "NONE"
    application_id: str = ""

    def __post_init__(self) -> None:
        if self.application_class not in SOLVER_LEARNING_APPLICATION_CLASSES:
            raise ValueError(f"unsupported solver learning application class: {self.application_class}")
        if not all((self.learning_id, self.learning_fingerprint, self.validation_id, self.validation_fingerprint, self.original_model_fingerprint)):
            raise ValueError("solver learning application requires artifact, validation, and model identity")
        if self.truth_authority != "NONE" or self.policy_authority != "NONE":
            raise ValueError("solver learning application never carries truth or policy authority")
        object.__setattr__(self, "application_payload", deepcopy(dict(self.application_payload)))
        if not self.application_id:
            object.__setattr__(self, "application_id", f"solver-learning-application-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": SOLVER_LEARNING_APPLICATION_CONTRACT_ID,
            "contract_version": SOLVER_LEARNING_APPLICATION_CONTRACT_VERSION,
            "learning_id": self.learning_id,
            "learning_fingerprint": self.learning_fingerprint,
            "validation_id": self.validation_id,
            "validation_fingerprint": self.validation_fingerprint,
            "original_model_fingerprint": self.original_model_fingerprint,
            "application_class": self.application_class,
            "application_payload": deepcopy(dict(self.application_payload)),
            "transformed_model_fingerprint": self.transformed_model_fingerprint,
            "provider_id": self.provider_id,
            "truth_authority": self.truth_authority,
            "policy_authority": self.policy_authority,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"application_id": self.application_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"application_id": self.application_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverLearningApplication":
        payload = dict(value)
        payload.pop("fingerprint", None)
        payload.pop("contract_id", None)
        payload.pop("contract_version", None)
        return cls(**payload)


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


def _validate_learning_literal_domain(artifact: SolverLearningArtifact, model: OptimizationModel) -> tuple[str, ...]:
    if artifact.learning_kind not in {"NO_GOOD", "UNSAT_CORE"}:
        return ()
    variables = {row.variable_id: row for row in model.variables}
    diagnostics: list[str] = []
    for literal in artifact.payload["literals"]:
        variable_id = str(literal["variable_id"])
        variable = variables.get(variable_id)
        if variable is None:
            diagnostics.append(f"UNKNOWN_LITERAL_VARIABLE:{variable_id}")
        elif variable.domain != "BOOL":
            diagnostics.append(f"NON_BOOLEAN_LITERAL_VARIABLE:{variable_id}")
    return tuple(sorted(set(diagnostics)))


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

    literal_diagnostics = _validate_learning_literal_domain(artifact, model)
    if literal_diagnostics:
        return SolverLearningValidation(
            artifact.learning_id,
            model.fingerprint,
            "FAIL",
            "NONE",
            diagnostics=literal_diagnostics,
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


def _require_application_validation(
    artifact: SolverLearningArtifact,
    validation: SolverLearningValidation,
    model: OptimizationModel,
) -> None:
    if artifact.model_fingerprint != model.fingerprint or validation.model_fingerprint != model.fingerprint:
        raise ValueError("solver learning application requires exact original model fingerprint")
    if artifact.solver_family != model.solver_family:
        raise ValueError("solver learning application solver family mismatch")
    if validation.learning_id != artifact.learning_id:
        raise ValueError("solver learning validation does not bind the artifact")
    if validation.status != "PASS":
        raise ValueError("solver learning application requires PASS local validation")
    required = (
        "PRUNING_CERTIFIED_FOR_EXACT_MODEL"
        if artifact.learning_kind in CORRECTNESS_SENSITIVE_KINDS
        else "PERFORMANCE_HINT_ONLY"
    )
    if validation.application_authority != required:
        raise ValueError(f"solver learning application requires validation authority {required}")


def _no_good_constraint(artifact: SolverLearningArtifact, model: OptimizationModel) -> OptimizationConstraint:
    diagnostics = _validate_learning_literal_domain(artifact, model)
    if diagnostics:
        raise ValueError(f"invalid learned Boolean conjunction: {list(diagnostics)}")
    literals = [BooleanLiteral.from_dict(row) for row in artifact.payload["literals"]]
    metadata = {
        "solver_learning_id": artifact.learning_id,
        "solver_learning_kind": artifact.learning_kind,
        "truth_authority": "NONE",
    }
    if model.solver_family == "SAT":
        return OptimizationConstraint(
            "CLAUSE",
            literals=tuple(BooleanLiteral(row.variable_id, not row.positive) for row in literals),
            metadata=metadata,
        )
    coefficients: dict[str, float] = {}
    positive_count = 0
    for literal in literals:
        if literal.positive:
            coefficients[literal.variable_id] = coefficients.get(literal.variable_id, 0.0) - 1.0
            positive_count += 1
        else:
            coefficients[literal.variable_id] = coefficients.get(literal.variable_id, 0.0) + 1.0
    return OptimizationConstraint(
        "LINEAR",
        coefficients=coefficients,
        sense=">=",
        rhs=float(1 - positive_count),
        metadata=metadata,
    )


def _bound_constraint(artifact: SolverLearningArtifact, model: OptimizationModel) -> OptimizationConstraint:
    if model.objective is None:
        raise ValueError("BOUND application requires model objective")
    bound = float(artifact.payload["value"])
    tolerance = float(artifact.payload.get("tolerance", 0.0))
    lower = artifact.payload["bound_type"] == "LOWER"
    effective = bound - tolerance if lower else bound + tolerance
    return OptimizationConstraint(
        "LINEAR",
        coefficients=dict(model.objective.coefficients),
        sense=">=" if lower else "<=",
        rhs=float(effective - model.objective.offset),
        metadata={
            "solver_learning_id": artifact.learning_id,
            "solver_learning_kind": "BOUND",
            "bound_type": artifact.payload["bound_type"],
            "validated_tolerance": tolerance,
            "truth_authority": "NONE",
        },
    )


def build_solver_learning_application(
    artifact: SolverLearningArtifact,
    validation: SolverLearningValidation,
    model: OptimizationModel,
    *,
    provider_id: str = "",
) -> tuple[SolverLearningApplication, OptimizationModel | None]:
    _require_application_validation(artifact, validation, model)
    if artifact.learning_kind in CORRECTNESS_SENSITIVE_KINDS:
        constraint = (
            _no_good_constraint(artifact, model)
            if artifact.learning_kind in {"NO_GOOD", "UNSAT_CORE"}
            else _bound_constraint(artifact, model)
        )
        transformed = OptimizationModel(
            f"{model.name}-validated-learning",
            model.variables,
            tuple((*model.constraints, constraint)),
            objective=model.objective,
            family=model.family,
            metadata={
                **deepcopy(model.metadata),
                "solver_learning_original_model_fingerprint": model.fingerprint,
                "solver_learning_id": artifact.learning_id,
                "solver_learning_validation_id": validation.validation_id,
                "truth_authority": "NONE",
            },
        )
        application = SolverLearningApplication(
            artifact.learning_id,
            artifact.fingerprint,
            validation.validation_id,
            validation.fingerprint,
            model.fingerprint,
            "PRUNING_CONSTRAINTS",
            {"constraint": constraint.to_dict()},
            transformed_model_fingerprint=transformed.fingerprint,
        )
        return application, transformed

    if artifact.learning_kind in {"INCUMBENT", "WARM_START"}:
        if model.solver_family != "CP_SAT" or provider_id != "ortools-cp-sat":
            raise ValueError(
                "validated assignment hints currently require the explicit ortools-cp-sat adapter"
            )
        application = SolverLearningApplication(
            artifact.learning_id,
            artifact.fingerprint,
            validation.validation_id,
            validation.fingerprint,
            model.fingerprint,
            "PERFORMANCE_HINT",
            {
                "hint_kind": "ASSIGNMENT",
                "source_kind": artifact.learning_kind,
                "assignment": deepcopy(dict(artifact.payload["assignment"])),
            },
            transformed_model_fingerprint=model.fingerprint,
            provider_id=provider_id,
        )
        return application, None

    raise ValueError(
        "validated native accelerator state has no explicit public adapter application in v0.53"
    )


def apply_solver_learning_to_optimization_request(
    artifact: SolverLearningArtifact,
    validation: SolverLearningValidation,
    request: OptimizationRequest,
) -> tuple[SolverLearningApplication, OptimizationRequest]:
    application, transformed = build_solver_learning_application(
        artifact,
        validation,
        request.model,
        provider_id=request.required_provider,
    )
    metadata = deepcopy(request.metadata)
    application_ids = list(metadata.get("solver_learning_application_ids") or [])
    if application.application_id not in application_ids:
        application_ids.append(application.application_id)
    metadata["solver_learning_application_ids"] = sorted(set(map(str, application_ids)))
    metadata["solver_learning_original_model_fingerprint"] = request.model.fingerprint
    metadata["solver_learning_truth_authority"] = "NONE"
    if application.application_class == "PERFORMANCE_HINT":
        hints = list(metadata.get("solver_learning_hints") or [])
        hints.append({
            "application_id": application.application_id,
            "provider_id": application.provider_id,
            **deepcopy(dict(application.application_payload)),
        })
        metadata["solver_learning_hints"] = hints
    updated = OptimizationRequest(
        transformed or request.model,
        request.capability_id,
        request.capability_version,
        request.obligation_id,
        timeout_ms=request.timeout_ms,
        required_provider=request.required_provider,
        accept_feasible=request.accept_feasible,
        environment_fingerprint=request.environment_fingerprint,
        dependency_fingerprints=request.dependency_fingerprints,
        metadata=metadata,
    )
    return application, updated


__all__ = [
    "SOLVER_LEARNING_CONTRACT_ID",
    "SOLVER_LEARNING_CONTRACT_VERSION",
    "SOLVER_LEARNING_STABILITY",
    "SOLVER_LEARNING_CHECKER_ID",
    "SOLVER_LEARNING_CHECKER_VERSION",
    "SOLVER_LEARNING_APPLICATION_CONTRACT_ID",
    "SOLVER_LEARNING_APPLICATION_CONTRACT_VERSION",
    "SOLVER_LEARNING_KINDS",
    "CORRECTNESS_SENSITIVE_KINDS",
    "PERFORMANCE_HINT_KINDS",
    "SOLVER_LEARNING_APPLICATION_CLASSES",
    "SolverLearningArtifact",
    "SolverLearningValidation",
    "SolverLearningApplication",
    "solver_learning_contract",
    "solver_learning_application_contract",
    "revalidate_finite_solver_learning",
    "validate_native_accelerator_hint",
    "build_solver_learning_application",
    "apply_solver_learning_to_optimization_request",
]
