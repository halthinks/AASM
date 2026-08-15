from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .multi_objective import MultiObjectiveProblem, OrderedObjective
from .optimization import OptimizationConstraint, OptimizationModel
from .semantic_result import semantic_fingerprint


DECISION_VECTOR_CONTRACT_ID = "aasm.decision-vector.v1"
DECISION_VECTOR_CONTRACT_VERSION = "0.1.0"
DECISION_VECTOR_COMPILATION_CONTRACT_ID = "aasm.decision-vector.compilation.v1"
DECISION_VECTOR_COMPILATION_CONTRACT_VERSION = "0.1.0"
DECISION_VECTOR_STABILITY = "FOUNDATION_EXPERIMENTAL"

HARD_FLOOR_SENSES = ("<=", ">=", "==")
OBJECTIVE_SENSES = ("MINIMIZE", "MAXIMIZE")
OBJECTIVE_CATEGORIES = ("ENGINEERING", "EVIDENCE", "PROGRESS", "RESOURCE", "OTHER")
METRIC_KINDS = ("LINEAR_ASSIGNMENT", "NAMED_EVALUATION")


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _linear_coefficients(values: Mapping[str, float]) -> dict[str, float]:
    return {str(key): float(value) for key, value in sorted(values.items()) if float(value) != 0.0}


@dataclass(frozen=True)
class DecisionHardFloor:
    floor_id: str
    metric_id: str
    sense: str
    threshold: float
    metric_kind: str = "LINEAR_ASSIGNMENT"
    coefficients: Mapping[str, float] = field(default_factory=dict)
    offset: float = 0.0
    tolerance: float = 0.0
    source_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "floor_id", _required(self.floor_id, "floor_id"))
        object.__setattr__(self, "metric_id", _required(self.metric_id, "metric_id"))
        if self.sense not in HARD_FLOOR_SENSES:
            raise ValueError("hard-floor sense must be <=, >=, or ==")
        if self.metric_kind not in METRIC_KINDS:
            raise ValueError("invalid hard-floor metric_kind")
        coefficients = _linear_coefficients(self.coefficients)
        if self.metric_kind == "LINEAR_ASSIGNMENT" and not coefficients:
            raise ValueError("linear hard floor requires coefficients")
        if self.metric_kind == "NAMED_EVALUATION" and coefficients:
            raise ValueError("named hard floor cannot carry linear coefficients")
        if float(self.tolerance) < 0:
            raise ValueError("hard-floor tolerance must be non-negative")
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "threshold", float(self.threshold))
        object.__setattr__(self, "offset", float(self.offset))
        object.__setattr__(self, "tolerance", float(self.tolerance))
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        object.__setattr__(self, "metadata", deepcopy(dict(self.metadata)))

    def value(self, assignment: Mapping[str, float], named_metrics: Mapping[str, float] | None = None) -> float:
        if self.metric_kind == "NAMED_EVALUATION":
            if named_metrics is None or self.metric_id not in named_metrics:
                raise KeyError(f"missing named hard-floor metric: {self.metric_id}")
            return float(named_metrics[self.metric_id])
        return self.offset + sum(coefficient * float(assignment[variable_id]) for variable_id, coefficient in self.coefficients.items())

    def passes(self, value: float) -> bool:
        if self.sense == "<=":
            return float(value) <= self.threshold + self.tolerance
        if self.sense == ">=":
            return float(value) >= self.threshold - self.tolerance
        return abs(float(value) - self.threshold) <= self.tolerance

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "floor_id": self.floor_id,
            "metric_id": self.metric_id,
            "metric_kind": self.metric_kind,
            "sense": self.sense,
            "threshold": self.threshold,
            "coefficients": dict(self.coefficients),
            "offset": self.offset,
            "tolerance": self.tolerance,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
            "metadata": deepcopy(dict(self.metadata)),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DecisionHardFloor":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class DecisionObjective:
    objective_id: str
    metric_id: str
    priority: int
    sense: str
    category: str = "ENGINEERING"
    metric_kind: str = "LINEAR_ASSIGNMENT"
    coefficients: Mapping[str, float] = field(default_factory=dict)
    offset: float = 0.0
    tolerance: float = 0.0
    source_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "objective_id", _required(self.objective_id, "objective_id"))
        object.__setattr__(self, "metric_id", _required(self.metric_id, "metric_id"))
        if int(self.priority) < 0:
            raise ValueError("objective priority must be non-negative")
        if self.sense not in OBJECTIVE_SENSES:
            raise ValueError("objective sense must be MINIMIZE or MAXIMIZE")
        if self.category not in OBJECTIVE_CATEGORIES:
            raise ValueError("invalid decision objective category")
        if self.metric_kind not in METRIC_KINDS:
            raise ValueError("invalid decision objective metric_kind")
        coefficients = _linear_coefficients(self.coefficients)
        if self.metric_kind == "LINEAR_ASSIGNMENT" and not coefficients:
            raise ValueError("linear objective requires coefficients")
        if self.metric_kind == "NAMED_EVALUATION" and coefficients:
            raise ValueError("named objective cannot carry linear coefficients")
        if float(self.tolerance) < 0:
            raise ValueError("objective tolerance must be non-negative")
        object.__setattr__(self, "priority", int(self.priority))
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "offset", float(self.offset))
        object.__setattr__(self, "tolerance", float(self.tolerance))
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        object.__setattr__(self, "metadata", deepcopy(dict(self.metadata)))

    def value(self, assignment: Mapping[str, float], named_metrics: Mapping[str, float] | None = None) -> float:
        if self.metric_kind == "NAMED_EVALUATION":
            if named_metrics is None or self.metric_id not in named_metrics:
                raise KeyError(f"missing named decision metric: {self.metric_id}")
            return float(named_metrics[self.metric_id])
        return self.offset + sum(coefficient * float(assignment[variable_id]) for variable_id, coefficient in self.coefficients.items())

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "metric_id": self.metric_id,
            "metric_kind": self.metric_kind,
            "priority": self.priority,
            "sense": self.sense,
            "category": self.category,
            "coefficients": dict(self.coefficients),
            "offset": self.offset,
            "tolerance": self.tolerance,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
            "metadata": deepcopy(dict(self.metadata)),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DecisionObjective":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class GovernedDecisionVector:
    model: OptimizationModel | Mapping[str, Any]
    hard_floors: tuple[DecisionHardFloor | Mapping[str, Any], ...]
    objectives: tuple[DecisionObjective | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    vector_id: str = ""
    contract_id: str = DECISION_VECTOR_CONTRACT_ID
    contract_version: str = DECISION_VECTOR_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != DECISION_VECTOR_CONTRACT_ID or self.contract_version != DECISION_VECTOR_CONTRACT_VERSION:
            raise ValueError("unsupported decision-vector contract")
        model = self.model if isinstance(self.model, OptimizationModel) else OptimizationModel.from_dict(self.model)
        floors = tuple(row if isinstance(row, DecisionHardFloor) else DecisionHardFloor.from_dict(row) for row in self.hard_floors)
        objectives = tuple(row if isinstance(row, DecisionObjective) else DecisionObjective.from_dict(row) for row in self.objectives)
        if not floors:
            raise ValueError("governed decision vector requires at least one hard floor")
        if not objectives:
            raise ValueError("governed decision vector requires at least one objective")
        floor_ids = [row.floor_id for row in floors]
        objective_ids = [row.objective_id for row in objectives]
        priorities = [row.priority for row in objectives]
        if len(floor_ids) != len(set(floor_ids)):
            raise ValueError("hard-floor IDs must be unique")
        if len(objective_ids) != len(set(objective_ids)):
            raise ValueError("decision objective IDs must be unique")
        if len(priorities) != len(set(priorities)):
            raise ValueError("decision objective priorities must be unique")
        known = {row.variable_id for row in model.variables}
        for row in (*floors, *objectives):
            missing = sorted(set(row.coefficients) - known)
            if missing:
                raise ValueError(f"decision metric references unknown variables: {missing}")
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "hard_floors", tuple(sorted(floors, key=lambda row: row.floor_id)))
        object.__setattr__(self, "objectives", tuple(sorted(objectives, key=lambda row: (row.priority, row.objective_id))))
        object.__setattr__(self, "metadata", deepcopy(dict(self.metadata)))
        if not self.vector_id:
            object.__setattr__(self, "vector_id", f"decision-vector-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "model": self.model.to_dict(),
            "hard_floors": [row.to_dict() for row in self.hard_floors],
            "objectives": [row.to_dict() for row in self.objectives],
            "metadata": deepcopy(dict(self.metadata)),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"vector_id": self.vector_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"vector_id": self.vector_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernedDecisionVector":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["hard_floors"] = tuple(payload.get("hard_floors") or ())
        payload["objectives"] = tuple(payload.get("objectives") or ())
        return cls(**payload)


@dataclass(frozen=True)
class DecisionVectorCompilation:
    vector_id: str
    vector_fingerprint: str
    multi_objective_problem_id: str
    multi_objective_problem_fingerprint: str
    floor_constraint_map: Mapping[str, str]
    objective_map: Mapping[str, str]
    status: str
    diagnostics: tuple[str, ...] = ()
    compilation_id: str = ""
    contract_id: str = DECISION_VECTOR_COMPILATION_CONTRACT_ID
    contract_version: str = DECISION_VECTOR_COMPILATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "INCONCLUSIVE", "FAIL"}:
            raise ValueError("invalid decision-vector compilation status")
        object.__setattr__(self, "floor_constraint_map", {str(key): str(value) for key, value in sorted(self.floor_constraint_map.items())})
        object.__setattr__(self, "objective_map", {str(key): str(value) for key, value in sorted(self.objective_map.items())})
        object.__setattr__(self, "diagnostics", _uniq(self.diagnostics))
        if self.status == "PASS" and (not self.floor_constraint_map or not self.objective_map):
            raise ValueError("passing decision-vector compilation requires floor and objective mappings")
        if not self.compilation_id:
            object.__setattr__(self, "compilation_id", f"decision-vector-compilation-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "vector_id": self.vector_id,
            "vector_fingerprint": self.vector_fingerprint,
            "multi_objective_problem_id": self.multi_objective_problem_id,
            "multi_objective_problem_fingerprint": self.multi_objective_problem_fingerprint,
            "floor_constraint_map": dict(self.floor_constraint_map),
            "objective_map": dict(self.objective_map),
            "status": self.status,
            "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"compilation_id": self.compilation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"compilation_id": self.compilation_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def compile_linear_decision_vector(vector: GovernedDecisionVector | Mapping[str, Any]) -> tuple[MultiObjectiveProblem | None, DecisionVectorCompilation]:
    source = vector if isinstance(vector, GovernedDecisionVector) else GovernedDecisionVector.from_dict(vector)
    non_linear = [
        row.metric_id
        for row in (*source.hard_floors, *source.objectives)
        if row.metric_kind != "LINEAR_ASSIGNMENT"
    ]
    if non_linear:
        placeholder = semantic_fingerprint({"vector_fingerprint": source.fingerprint, "non_linear": sorted(non_linear)})
        return None, DecisionVectorCompilation(
            source.vector_id,
            source.fingerprint,
            "",
            placeholder,
            {},
            {},
            "INCONCLUSIVE",
            tuple(f"NAMED_METRIC_NOT_LINEarly_COMPILABLE:{metric_id}" for metric_id in sorted(non_linear)),
        )

    constraints = list(source.model.constraints)
    floor_map: dict[str, str] = {}
    for floor in source.hard_floors:
        constraint_id = f"hard-floor::{floor.floor_id}"
        adjusted_rhs = floor.threshold - floor.offset
        if floor.sense == "<=":
            adjusted_rhs += floor.tolerance
        elif floor.sense == ">=":
            adjusted_rhs -= floor.tolerance
        else:
            if floor.tolerance != 0:
                return None, DecisionVectorCompilation(
                    source.vector_id,
                    source.fingerprint,
                    "",
                    semantic_fingerprint({"vector_fingerprint": source.fingerprint, "floor_id": floor.floor_id}),
                    {},
                    {},
                    "INCONCLUSIVE",
                    (f"EQUALITY_HARD_FLOOR_WITH_TOLERANCE_REQUIRES_TWO_CONSTRAINTS:{floor.floor_id}",),
                )
        constraints.append(OptimizationConstraint(
            "LINEAR",
            coefficients=floor.coefficients,
            sense=floor.sense,
            rhs=adjusted_rhs,
            constraint_id=constraint_id,
        ))
        floor_map[floor.floor_id] = constraint_id
    compiled_model = OptimizationModel(
        f"{source.model.name} + governed hard floors",
        source.model.variables,
        tuple(constraints),
        objective=None,
        family=source.model.family,
        metadata={**deepcopy(source.model.metadata), "decision_vector_id": source.vector_id, "decision_vector_fingerprint": source.fingerprint},
    )
    ordered = tuple(
        OrderedObjective(
            objective.objective_id,
            objective.priority,
            objective.sense,
            objective.coefficients,
            objective.offset,
            objective.tolerance,
        )
        for objective in source.objectives
    )
    problem = MultiObjectiveProblem(
        compiled_model,
        ordered,
        metadata={"decision_vector_id": source.vector_id, "decision_vector_fingerprint": source.fingerprint},
    )
    objective_map = {row.objective_id: row.objective_id for row in source.objectives}
    compilation = DecisionVectorCompilation(
        source.vector_id,
        source.fingerprint,
        problem.problem_id,
        problem.fingerprint,
        floor_map,
        objective_map,
        "PASS",
    )
    return problem, compilation


def evaluate_hard_floors(
    vector: GovernedDecisionVector | Mapping[str, Any],
    assignment: Mapping[str, float],
    *,
    named_metrics: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    source = vector if isinstance(vector, GovernedDecisionVector) else GovernedDecisionVector.from_dict(vector)
    rows = []
    for floor in source.hard_floors:
        value = floor.value(assignment, named_metrics)
        rows.append({
            "floor_id": floor.floor_id,
            "metric_id": floor.metric_id,
            "value": value,
            "sense": floor.sense,
            "threshold": floor.threshold,
            "tolerance": floor.tolerance,
            "passes": floor.passes(value),
            "source_reference_fingerprints": list(floor.source_reference_fingerprints),
        })
    return {
        "vector_id": source.vector_id,
        "vector_fingerprint": source.fingerprint,
        "passes": all(row["passes"] for row in rows),
        "floors": rows,
        "resource_policy_can_override": False,
    }


def decision_vector_contract() -> dict[str, Any]:
    return {
        "contract_id": DECISION_VECTOR_CONTRACT_ID,
        "contract_version": DECISION_VECTOR_CONTRACT_VERSION,
        "compilation_contract_id": DECISION_VECTOR_COMPILATION_CONTRACT_ID,
        "compilation_contract_version": DECISION_VECTOR_COMPILATION_CONTRACT_VERSION,
        "stability": DECISION_VECTOR_STABILITY,
        "hard_floors": "SEPARATE_CONSTRAINT_CLASS_NEVER_WEIGHTED_OR_TRADED",
        "objective_order": "UNIQUE_EXPLICIT_LEXICOGRAPHIC_PRIORITY",
        "categories": list(OBJECTIVE_CATEGORIES),
        "resource_objectives": "PREFERENCES_ONLY_AFTER_ALL_HARD_FLOORS_PASS",
        "scalarization": "NONE",
        "linear_compilation": "EXISTING_V052_MULTI_OBJECTIVE_ENGINE",
        "named_metric_compilation": "INCONCLUSIVE_UNTIL_EXPLICIT_EVALUATOR_OR_LOWERING_EXISTS",
        "resource_policy_can_weaken_hard_semantics": False,
        "truth_authority": "NONE",
    }


__all__ = [
    "DECISION_VECTOR_CONTRACT_ID",
    "DECISION_VECTOR_CONTRACT_VERSION",
    "DECISION_VECTOR_COMPILATION_CONTRACT_ID",
    "DECISION_VECTOR_COMPILATION_CONTRACT_VERSION",
    "DecisionHardFloor",
    "DecisionObjective",
    "GovernedDecisionVector",
    "DecisionVectorCompilation",
    "compile_linear_decision_vector",
    "evaluate_hard_floors",
    "decision_vector_contract",
]
