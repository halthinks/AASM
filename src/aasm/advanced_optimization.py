from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from importlib import metadata as importlib_metadata
from math import isclose, sqrt
from threading import RLock
from typing import Any, Mapping, Sequence
import time

from .optimization import (
    BooleanLiteral,
    OptimizationModel,
    OptimizationResult,
    OptimizationSolverIdentity,
    objective_value,
    validate_optimization_solution,
)
from .semantic_result import semantic_fingerprint
from .typed_protocol import CapabilityContract, CapabilityProvider

ADVANCED_OPTIMIZATION_CONTRACT_ID = "aasm.optimization.advanced.v1"
ADVANCED_OPTIMIZATION_CONTRACT_VERSION = "0.1.0"
ADVANCED_CAPABILITY_VERSION = "0.1.0"
ADVANCED_KINDS = (
    "FAST_SAT",
    "INCREMENTAL_SAT",
    "CP_SAT_SCHEDULING",
    "MILP_ADVANCED",
    "CONVEX_ADVANCED",
)
ADVANCED_CAPABILITIES = {
    "FAST_SAT": "solver.sat.fast",
    "INCREMENTAL_SAT": "solver.sat.incremental",
    "CP_SAT_SCHEDULING": "solver.cp_sat.scheduling",
    "MILP_ADVANCED": "solver.milp.advanced",
    "CONVEX_ADVANCED": "solver.convex.advanced",
}
ADVANCED_PROVIDERS = {
    "FAST_SAT": "kissat",
    "INCREMENTAL_SAT": "cadical-incremental",
    "CP_SAT_SCHEDULING": "ortools-cp-sat-scheduling",
    "MILP_ADVANCED": "highs-advanced",
    "CONVEX_ADVANCED": "cvxpy-advanced",
}
ADVANCED_STATUSES = (
    "SAT", "UNSAT", "OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNBOUNDED", "UNKNOWN", "TIMEOUT", "ERROR"
)


def _package_version(name: str) -> str:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _int(value: float | int, *, name: str = "value") -> int:
    if not isclose(float(value), round(float(value)), abs_tol=1e-9):
        raise ValueError(f"{name} must be integral")
    return int(round(float(value)))


def _base_model(value: OptimizationModel | Mapping[str, Any]) -> OptimizationModel:
    return value if isinstance(value, OptimizationModel) else OptimizationModel.from_dict(value)


@dataclass(frozen=True)
class FastSATProblem:
    model: OptimizationModel | Mapping[str, Any]

    def __post_init__(self):
        model = _base_model(self.model)
        if model.solver_family != "SAT":
            raise ValueError("FAST_SAT requires a SAT-compatible OptimizationModel")
        object.__setattr__(self, "model", model)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "FAST_SAT", "model": self.model.to_dict()}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FastSATProblem":
        return cls(dict(value)["model"])


@dataclass(frozen=True)
class IncrementalSATProblem:
    model: OptimizationModel | Mapping[str, Any]
    assumptions: tuple[BooleanLiteral | Mapping[str, Any], ...] = ()
    conflict_budget: int | None = None
    decision_budget: int | None = None

    def __post_init__(self):
        model = _base_model(self.model)
        if model.solver_family != "SAT":
            raise ValueError("INCREMENTAL_SAT requires a SAT-compatible OptimizationModel")
        assumptions = tuple(row if isinstance(row, BooleanLiteral) else BooleanLiteral.from_dict(row) for row in self.assumptions)
        known = {row.variable_id for row in model.variables}
        missing = sorted({row.variable_id for row in assumptions} - known)
        if missing:
            raise ValueError(f"SAT assumptions reference unknown variables: {missing}")
        if self.conflict_budget is not None and int(self.conflict_budget) <= 0:
            raise ValueError("conflict_budget must be positive")
        if self.decision_budget is not None and int(self.decision_budget) <= 0:
            raise ValueError("decision_budget must be positive")
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "assumptions", tuple(sorted(assumptions, key=lambda row: (row.variable_id, not row.positive))))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "INCREMENTAL_SAT",
            "model": self.model.to_dict(),
            "assumptions": [row.to_dict() for row in self.assumptions],
            "conflict_budget": self.conflict_budget,
            "decision_budget": self.decision_budget,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IncrementalSATProblem":
        payload = dict(value)
        return cls(payload["model"], tuple(payload.get("assumptions") or ()), payload.get("conflict_budget"), payload.get("decision_budget"))


@dataclass(frozen=True)
class SchedulingInterval:
    interval_id: str
    start_variable_id: str
    size: int
    end_variable_id: str
    presence_variable_id: str = ""

    def __post_init__(self):
        if not self.interval_id.strip() or not self.start_variable_id.strip() or not self.end_variable_id.strip():
            raise ValueError("scheduling interval IDs are required")
        if int(self.size) <= 0:
            raise ValueError("scheduling interval size must be positive")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SchedulingInterval":
        return cls(**dict(value))


@dataclass(frozen=True)
class NoOverlapConstraint:
    interval_ids: tuple[str, ...]
    constraint_id: str = ""

    def __post_init__(self):
        ids = _uniq(self.interval_ids)
        if len(ids) < 2:
            raise ValueError("NO_OVERLAP requires at least two intervals")
        object.__setattr__(self, "interval_ids", ids)
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"no-overlap-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self):
        return {"interval_ids": list(self.interval_ids)}

    def to_dict(self):
        return {"constraint_id": self.constraint_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, value):
        return cls(tuple(value["interval_ids"]), str(value.get("constraint_id") or ""))


@dataclass(frozen=True)
class CumulativeConstraint:
    interval_ids: tuple[str, ...]
    demands: tuple[int, ...]
    capacity: int
    constraint_id: str = ""

    def __post_init__(self):
        ids = tuple(map(str, self.interval_ids))
        demands = tuple(int(v) for v in self.demands)
        if not ids or len(ids) != len(demands):
            raise ValueError("CUMULATIVE requires one demand per interval")
        if any(v < 0 for v in demands) or int(self.capacity) < 0:
            raise ValueError("CUMULATIVE demands/capacity must be non-negative")
        object.__setattr__(self, "interval_ids", ids)
        object.__setattr__(self, "demands", demands)
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"cumulative-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self):
        return {"interval_ids": list(self.interval_ids), "demands": list(self.demands), "capacity": int(self.capacity)}

    def to_dict(self):
        return {"constraint_id": self.constraint_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, value):
        return cls(tuple(value["interval_ids"]), tuple(value["demands"]), int(value["capacity"]), str(value.get("constraint_id") or ""))


@dataclass(frozen=True)
class CPSATSchedulingProblem:
    model: OptimizationModel | Mapping[str, Any]
    intervals: tuple[SchedulingInterval | Mapping[str, Any], ...]
    no_overlap: tuple[NoOverlapConstraint | Mapping[str, Any], ...] = ()
    cumulative: tuple[CumulativeConstraint | Mapping[str, Any], ...] = ()
    search_workers: int = 1
    deterministic_time_limit: float | None = None

    def __post_init__(self):
        model = _base_model(self.model)
        if model.solver_family != "CP_SAT":
            raise ValueError("CP_SAT_SCHEDULING requires a CP-SAT-compatible OptimizationModel")
        intervals = tuple(row if isinstance(row, SchedulingInterval) else SchedulingInterval.from_dict(row) for row in self.intervals)
        no_overlap = tuple(row if isinstance(row, NoOverlapConstraint) else NoOverlapConstraint.from_dict(row) for row in self.no_overlap)
        cumulative = tuple(row if isinstance(row, CumulativeConstraint) else CumulativeConstraint.from_dict(row) for row in self.cumulative)
        ids = [row.interval_id for row in intervals]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("scheduling interval IDs must be non-empty and unique")
        variables = {row.variable_id: row for row in model.variables}
        for row in intervals:
            for variable_id in (row.start_variable_id, row.end_variable_id):
                if variable_id not in variables or variables[variable_id].domain == "CONTINUOUS":
                    raise ValueError("scheduling start/end variables must be integer CP-SAT variables")
            if row.presence_variable_id:
                if row.presence_variable_id not in variables or variables[row.presence_variable_id].domain != "BOOL":
                    raise ValueError("optional interval presence variable must be BOOL")
        known_intervals = set(ids)
        for row in (*no_overlap, *cumulative):
            missing = sorted(set(row.interval_ids) - known_intervals)
            if missing:
                raise ValueError(f"scheduling constraint references unknown intervals: {missing}")
        if int(self.search_workers) <= 0:
            raise ValueError("search_workers must be positive")
        if self.deterministic_time_limit is not None and float(self.deterministic_time_limit) <= 0:
            raise ValueError("deterministic_time_limit must be positive")
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "intervals", tuple(sorted(intervals, key=lambda row: row.interval_id)))
        object.__setattr__(self, "no_overlap", tuple(sorted(no_overlap, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "cumulative", tuple(sorted(cumulative, key=lambda row: row.constraint_id)))

    @property
    def fingerprint(self):
        return semantic_fingerprint(self.to_dict())

    def to_dict(self):
        return {
            "kind": "CP_SAT_SCHEDULING",
            "model": self.model.to_dict(),
            "intervals": [row.to_dict() for row in self.intervals],
            "no_overlap": [row.to_dict() for row in self.no_overlap],
            "cumulative": [row.to_dict() for row in self.cumulative],
            "search_workers": int(self.search_workers),
            "deterministic_time_limit": self.deterministic_time_limit,
        }

    @classmethod
    def from_dict(cls, value):
        return cls(value["model"], tuple(value.get("intervals") or ()), tuple(value.get("no_overlap") or ()), tuple(value.get("cumulative") or ()), int(value.get("search_workers", 1)), value.get("deterministic_time_limit"))


@dataclass(frozen=True)
class AdvancedMILPProblem:
    model: OptimizationModel | Mapping[str, Any]
    warm_start: dict[str, float] = field(default_factory=dict)
    mip_relative_gap: float | None = None
    node_limit: int | None = None

    def __post_init__(self):
        model = _base_model(self.model)
        if model.solver_family != "MILP":
            raise ValueError("MILP_ADVANCED requires a MILP-compatible OptimizationModel")
        known = {row.variable_id for row in model.variables}
        missing = sorted(set(self.warm_start) - known)
        if missing:
            raise ValueError(f"MILP warm start references unknown variables: {missing}")
        if self.mip_relative_gap is not None and float(self.mip_relative_gap) < 0:
            raise ValueError("mip_relative_gap must be non-negative")
        if self.node_limit is not None and int(self.node_limit) < 0:
            raise ValueError("node_limit must be non-negative")
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "warm_start", {str(k): float(v) for k, v in sorted(self.warm_start.items())})

    @property
    def fingerprint(self):
        return semantic_fingerprint(self.to_dict())

    def to_dict(self):
        return {"kind": "MILP_ADVANCED", "model": self.model.to_dict(), "warm_start": dict(self.warm_start), "mip_relative_gap": self.mip_relative_gap, "node_limit": self.node_limit}

    @classmethod
    def from_dict(cls, value):
        return cls(value["model"], dict(value.get("warm_start") or {}), value.get("mip_relative_gap"), value.get("node_limit"))


@dataclass(frozen=True)
class AffineExpression:
    coefficients: dict[str, float] = field(default_factory=dict)
    offset: float = 0.0

    def __post_init__(self):
        object.__setattr__(self, "coefficients", {str(k): float(v) for k, v in sorted(self.coefficients.items()) if float(v) != 0.0})

    def to_dict(self):
        return {"coefficients": dict(self.coefficients), "offset": float(self.offset)}

    @classmethod
    def from_dict(cls, value):
        return cls(dict(value.get("coefficients") or {}), float(value.get("offset", 0.0)))

    def evaluate(self, assignment: Mapping[str, float]) -> float:
        return float(self.offset) + sum(coef * float(assignment[var]) for var, coef in self.coefficients.items())


@dataclass(frozen=True)
class QuadraticFactor:
    expression: AffineExpression | Mapping[str, Any]
    weight: float = 1.0

    def __post_init__(self):
        expression = self.expression if isinstance(self.expression, AffineExpression) else AffineExpression.from_dict(self.expression)
        if float(self.weight) < 0:
            raise ValueError("quadratic factor weight must be non-negative")
        if expression.offset != 0.0:
            raise ValueError("quadratic factors use homogeneous affine expressions; put offsets in linear/constant objective terms")
        object.__setattr__(self, "expression", expression)

    def to_dict(self):
        return {"expression": self.expression.to_dict(), "weight": float(self.weight)}

    @classmethod
    def from_dict(cls, value):
        return cls(value["expression"], float(value.get("weight", 1.0)))


@dataclass(frozen=True)
class AffineSOCConstraint:
    lhs_rows: tuple[AffineExpression | Mapping[str, Any], ...]
    rhs: AffineExpression | Mapping[str, Any]
    constraint_id: str = ""

    def __post_init__(self):
        lhs = tuple(row if isinstance(row, AffineExpression) else AffineExpression.from_dict(row) for row in self.lhs_rows)
        rhs = self.rhs if isinstance(self.rhs, AffineExpression) else AffineExpression.from_dict(self.rhs)
        if not lhs:
            raise ValueError("affine SOC requires at least one left-hand row")
        object.__setattr__(self, "lhs_rows", lhs)
        object.__setattr__(self, "rhs", rhs)
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"affine-soc-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self):
        return {"lhs_rows": [row.to_dict() for row in self.lhs_rows], "rhs": self.rhs.to_dict()}

    def to_dict(self):
        return {"constraint_id": self.constraint_id, **self.identity_payload()}

    @classmethod
    def from_dict(cls, value):
        return cls(tuple(value["lhs_rows"]), value["rhs"], str(value.get("constraint_id") or ""))


@dataclass(frozen=True)
class AdvancedConvexObjective:
    sense: str
    linear: AffineExpression | Mapping[str, Any] = field(default_factory=AffineExpression)
    quadratic_factors: tuple[QuadraticFactor | Mapping[str, Any], ...] = ()

    def __post_init__(self):
        if self.sense not in {"MINIMIZE", "MAXIMIZE"}:
            raise ValueError("advanced convex objective sense must be MINIMIZE or MAXIMIZE")
        linear = self.linear if isinstance(self.linear, AffineExpression) else AffineExpression.from_dict(self.linear)
        factors = tuple(row if isinstance(row, QuadraticFactor) else QuadraticFactor.from_dict(row) for row in self.quadratic_factors)
        if not linear.coefficients and linear.offset == 0.0 and not factors:
            raise ValueError("advanced convex objective requires linear or quadratic terms")
        object.__setattr__(self, "linear", linear)
        object.__setattr__(self, "quadratic_factors", factors)

    def to_dict(self):
        return {"sense": self.sense, "linear": self.linear.to_dict(), "quadratic_factors": [row.to_dict() for row in self.quadratic_factors]}

    @classmethod
    def from_dict(cls, value):
        return cls(value["sense"], value.get("linear") or {}, tuple(value.get("quadratic_factors") or ()))


@dataclass(frozen=True)
class AdvancedConvexProblem:
    variables: tuple[Mapping[str, Any], ...]
    linear_constraints: tuple[Mapping[str, Any], ...] = ()
    affine_soc_constraints: tuple[AffineSOCConstraint | Mapping[str, Any], ...] = ()
    objective: AdvancedConvexObjective | Mapping[str, Any] | None = None
    name: str = "advanced-convex"

    def __post_init__(self):
        variables = tuple({"variable_id": str(row["variable_id"]), "lower_bound": row.get("lower_bound"), "upper_bound": row.get("upper_bound")} for row in self.variables)
        ids = [row["variable_id"] for row in variables]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("advanced convex variable IDs must be non-empty and unique")
        linear = tuple({"coefficients": {str(k): float(v) for k, v in sorted((row.get("coefficients") or {}).items()) if float(v) != 0.0}, "sense": str(row["sense"]), "rhs": float(row["rhs"]), "constraint_id": str(row.get("constraint_id") or "")} for row in self.linear_constraints)
        for row in linear:
            if row["sense"] not in {"<=", ">=", "=="} or not row["coefficients"]:
                raise ValueError("advanced convex linear constraints require coefficients and valid sense")
        soc = tuple(row if isinstance(row, AffineSOCConstraint) else AffineSOCConstraint.from_dict(row) for row in self.affine_soc_constraints)
        objective = self.objective
        if objective is not None and not isinstance(objective, AdvancedConvexObjective):
            objective = AdvancedConvexObjective.from_dict(objective)
        known = set(ids)
        refs = set()
        for row in linear: refs.update(row["coefficients"])
        for row in soc:
            for expr in (*row.lhs_rows, row.rhs): refs.update(expr.coefficients)
        if objective:
            refs.update(objective.linear.coefficients)
            for factor in objective.quadratic_factors: refs.update(factor.expression.coefficients)
        missing = sorted(refs - known)
        if missing:
            raise ValueError(f"advanced convex problem references unknown variables: {missing}")
        object.__setattr__(self, "variables", tuple(sorted(variables, key=lambda row: row["variable_id"])))
        object.__setattr__(self, "linear_constraints", tuple(sorted(linear, key=lambda row: (row["constraint_id"], str(row["coefficients"])))))
        object.__setattr__(self, "affine_soc_constraints", tuple(sorted(soc, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "objective", objective)

    @property
    def fingerprint(self):
        return semantic_fingerprint(self.to_dict())

    def to_dict(self):
        return {
            "kind": "CONVEX_ADVANCED",
            "name": self.name,
            "variables": [dict(row) for row in self.variables],
            "linear_constraints": [dict(row) for row in self.linear_constraints],
            "affine_soc_constraints": [row.to_dict() for row in self.affine_soc_constraints],
            "objective": self.objective.to_dict() if self.objective else None,
        }

    @classmethod
    def from_dict(cls, value):
        return cls(tuple(value["variables"]), tuple(value.get("linear_constraints") or ()), tuple(value.get("affine_soc_constraints") or ()), value.get("objective"), str(value.get("name") or "advanced-convex"))


ProblemType = FastSATProblem | IncrementalSATProblem | CPSATSchedulingProblem | AdvancedMILPProblem | AdvancedConvexProblem


def advanced_problem_from_dict(value: Mapping[str, Any]) -> ProblemType:
    kind = str(value.get("kind") or "")
    return {
        "FAST_SAT": FastSATProblem,
        "INCREMENTAL_SAT": IncrementalSATProblem,
        "CP_SAT_SCHEDULING": CPSATSchedulingProblem,
        "MILP_ADVANCED": AdvancedMILPProblem,
        "CONVEX_ADVANCED": AdvancedConvexProblem,
    }[kind].from_dict(value)


@dataclass(frozen=True)
class AdvancedSolverRequest:
    problem: ProblemType | Mapping[str, Any]
    capability_id: str
    capability_version: str
    obligation_id: str
    required_provider: str
    timeout_ms: int = 30_000
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""

    def __post_init__(self):
        problem = self.problem if not isinstance(self.problem, Mapping) else advanced_problem_from_dict(self.problem)
        kind = problem.to_dict()["kind"]
        if kind not in ADVANCED_KINDS:
            raise ValueError("unknown advanced optimization kind")
        if self.capability_id != ADVANCED_CAPABILITIES[kind] or self.capability_version != ADVANCED_CAPABILITY_VERSION:
            raise ValueError("advanced optimization capability mismatch")
        if self.required_provider != ADVANCED_PROVIDERS[kind]:
            raise ValueError("advanced optimization provider mismatch")
        if not self.obligation_id.strip() or int(self.timeout_ms) <= 0:
            raise ValueError("advanced optimization request requires obligation and positive timeout")
        object.__setattr__(self, "problem", problem)
        object.__setattr__(self, "dependency_fingerprints", _uniq(self.dependency_fingerprints))
        if not self.request_id:
            object.__setattr__(self, "request_id", f"advanced-request-{semantic_fingerprint(self.identity_payload())[:20]}")

    @property
    def kind(self):
        return self.problem.to_dict()["kind"]

    @property
    def fingerprint(self):
        return semantic_fingerprint({"request_id": self.request_id, **self.identity_payload()})

    @property
    def capability_token(self):
        return f"aasm.capability:{self.capability_id}@{self.capability_version}"

    def identity_payload(self):
        return {
            "problem": self.problem.to_dict(), "capability_id": self.capability_id, "capability_version": self.capability_version,
            "obligation_id": self.obligation_id, "required_provider": self.required_provider, "timeout_ms": int(self.timeout_ms),
            "environment_fingerprint": self.environment_fingerprint, "dependency_fingerprints": list(self.dependency_fingerprints), "metadata": deepcopy(self.metadata),
        }

    def to_dict(self):
        return {"request_id": self.request_id, **self.identity_payload(), "kind": self.kind, "capability_token": self.capability_token, "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value):
        payload = deepcopy(dict(value)); payload.pop("kind", None); payload.pop("capability_token", None); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class AdvancedSolverIdentity:
    provider_id: str
    implementation: str
    version: str
    backend: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class AdvancedSolverResult:
    request_id: str
    request_fingerprint: str
    problem_fingerprint: str
    status: str
    solver: AdvancedSolverIdentity | Mapping[str, Any]
    assignment: dict[str, float] = field(default_factory=dict)
    objective_value: float | None = None
    best_bound: float | None = None
    relative_gap: float | None = None
    unsat_core: tuple[BooleanLiteral | Mapping[str, Any], ...] = ()
    telemetry: dict[str, Any] = field(default_factory=dict)
    wall_time_ms: int = 0
    diagnostics: tuple[str, ...] = ()
    result_id: str = ""

    def __post_init__(self):
        solver = self.solver if isinstance(self.solver, AdvancedSolverIdentity) else AdvancedSolverIdentity(**dict(self.solver))
        core = tuple(row if isinstance(row, BooleanLiteral) else BooleanLiteral.from_dict(row) for row in self.unsat_core)
        if self.status not in ADVANCED_STATUSES:
            raise ValueError(f"invalid advanced result status: {self.status}")
        object.__setattr__(self, "solver", solver)
        object.__setattr__(self, "assignment", {str(k): float(v) for k, v in sorted(self.assignment.items())})
        object.__setattr__(self, "unsat_core", tuple(sorted(core, key=lambda row: (row.variable_id, not row.positive))))
        object.__setattr__(self, "diagnostics", tuple(map(str, self.diagnostics)))
        if not self.result_id:
            object.__setattr__(self, "result_id", f"advanced-result-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self):
        return {
            "request_id": self.request_id, "request_fingerprint": self.request_fingerprint, "problem_fingerprint": self.problem_fingerprint,
            "status": self.status, "solver": self.solver.to_dict(), "assignment": dict(self.assignment), "objective_value": self.objective_value,
            "best_bound": self.best_bound, "relative_gap": self.relative_gap, "unsat_core": [row.to_dict() for row in self.unsat_core],
            "telemetry": deepcopy(self.telemetry), "wall_time_ms": int(self.wall_time_ms), "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self):
        return semantic_fingerprint({"result_id": self.result_id, **self.identity_payload()})

    def to_dict(self):
        return {"result_id": self.result_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value):
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


def advanced_optimization_contract() -> dict[str, Any]:
    return {
        "contract_id": ADVANCED_OPTIMIZATION_CONTRACT_ID,
        "contract_version": ADVANCED_OPTIMIZATION_CONTRACT_VERSION,
        "canonical_ir": "AASM_OWNED_EXPLICIT_SEARCH_ARTIFACTS",
        "scheduler": "EXISTING_AASM_RESOURCE_WORKER_LEASE",
        "result_authority": "EVIDENCE_ONLY",
        "fast_sat": {"provider": "kissat", "mode": "NON_INCREMENTAL_HIGH_PERFORMANCE"},
        "incremental_sat": {"provider": "cadical-incremental", "assumptions": True, "unsat_core": True, "learned_state": "EPHEMERAL_PERFORMANCE_ONLY"},
        "cp_sat_scheduling": {"interval": True, "no_overlap": True, "cumulative": True, "deterministic_time_budget": True},
        "milp_advanced": {"warm_start": True, "node_limit": True, "relative_gap_target": True, "bound_gap_telemetry": True},
        "convex_advanced": {"factorized_general_psd_quadratic": True, "affine_soc": True},
        "truth_rule": "SEARCH_STATE_NEVER_PROMOTES_TRUTH",
    }


def default_advanced_capability_contracts() -> tuple[CapabilityContract, ...]:
    return tuple(
        CapabilityContract(
            capability_id, "OPERATOR", ADVANCED_CAPABILITY_VERSION,
            input_schema={"type": "object"}, output_schema={"type": "object"}, evidence_types=("advanced_optimization_result",),
            deterministic=False, metadata={"advanced_kind": kind, "result_authority": "EVIDENCE_ONLY"},
        )
        for kind, capability_id in ADVANCED_CAPABILITIES.items()
    )


def default_advanced_providers() -> tuple[CapabilityProvider, ...]:
    definitions = {
        "FAST_SAT": ("kissat", "solver-kissat", "pysat:kissat404", "python-sat"),
        "INCREMENTAL_SAT": ("cadical-incremental", "solver-cadical-incremental", "pysat:cadical195", "python-sat"),
        "CP_SAT_SCHEDULING": ("ortools-cp-sat-scheduling", "solver-ortools-cp-sat-scheduling", "ortools.cp-sat", "ortools"),
        "MILP_ADVANCED": ("highs-advanced", "solver-highs-advanced", "highspy", "highspy"),
        "CONVEX_ADVANCED": ("cvxpy-advanced", "solver-cvxpy-advanced", "cvxpy", "cvxpy"),
    }
    rows = []
    for kind in ADVANCED_KINDS:
        provider_id, resource_id, implementation, package = definitions[kind]
        rows.append(CapabilityProvider(provider_id, ADVANCED_CAPABILITIES[kind], ADVANCED_CAPABILITY_VERSION, resource_id, implementation, metadata={"advanced_kind": kind, "python_package": package}))
    return tuple(rows)


def advanced_optimization_blueprint():
    return {"contract": advanced_optimization_contract(), "capabilities": [row.to_dict() for row in default_advanced_capability_contracts()], "providers": [row.to_dict() for row in default_advanced_providers()]}


def _assumption_literal(problem: IncrementalSATProblem, row: BooleanLiteral, mapping: Mapping[str, int]) -> int:
    index = mapping[row.variable_id]
    return index if row.positive else -index


class _CadicalSessionPool:
    def __init__(self, max_sessions: int = 8):
        self.max_sessions = max_sessions
        self._lock = RLock()
        self._sessions: OrderedDict[str, dict[str, Any]] = OrderedDict()

    def clear(self):
        with self._lock:
            for row in self._sessions.values():
                try: row["solver"].delete()
                except Exception: pass
            self._sessions.clear()

    def solve(self, problem: IncrementalSATProblem):
        from pysat.solvers import Solver
        key = problem.model.fingerprint
        with self._lock:
            reused = key in self._sessions
            if not reused:
                mapping = {row.variable_id: index + 1 for index, row in enumerate(problem.model.variables)}
                clauses = [[mapping[lit.variable_id] if lit.positive else -mapping[lit.variable_id] for lit in row.literals] for row in problem.model.constraints]
                solver = Solver(name="cadical195", bootstrap_with=clauses, use_timer=True)
                self._sessions[key] = {"solver": solver, "mapping": mapping, "uses": 0}
                while len(self._sessions) > self.max_sessions:
                    _, evicted = self._sessions.popitem(last=False)
                    try: evicted["solver"].delete()
                    except Exception: pass
            row = self._sessions[key]
            self._sessions.move_to_end(key)
            solver, mapping = row["solver"], row["mapping"]
            assumptions = [_assumption_literal(problem, assumption, mapping) for assumption in problem.assumptions]
            if problem.conflict_budget is not None: solver.conf_budget(int(problem.conflict_budget))
            if problem.decision_budget is not None: solver.dec_budget(int(problem.decision_budget))
            limited = problem.conflict_budget is not None or problem.decision_budget is not None
            solved = solver.solve_limited(assumptions=assumptions) if limited else solver.solve(assumptions=assumptions)
            row["uses"] += 1
            stats = dict(solver.accum_stats() or {})
            stats.update({"session_reused": reused, "session_use_count": row["uses"], "ephemeral_learned_state": True})
            assignment = {}
            core: tuple[BooleanLiteral, ...] = ()
            if solved is True:
                model_values = set(solver.get_model() or [])
                assignment = {variable_id: 1.0 if index in model_values else 0.0 for variable_id, index in mapping.items()}
                status = "SAT"
            elif solved is False:
                reverse = {abs(index): variable_id for variable_id, index in mapping.items()}
                core_rows = []
                for literal in solver.get_core() or []:
                    core_rows.append(BooleanLiteral(reverse[abs(literal)], literal > 0))
                core = tuple(core_rows)
                status = "UNSAT"
            else:
                status = "UNKNOWN"
            return status, assignment, core, stats


_CADICAL_POOL = _CadicalSessionPool()


def clear_incremental_sat_sessions():
    _CADICAL_POOL.clear()


def _build_cp_base(cp_model, base: OptimizationModel):
    model = cp_model.CpModel()
    variables: dict[str, Any] = {}
    for row in base.variables:
        lb, ub = _int(row.lower_bound), _int(row.upper_bound)
        variables[row.variable_id] = model.new_bool_var(row.variable_id) if row.domain == "BOOL" and lb == 0 and ub == 1 else model.new_int_var(lb, ub, row.variable_id)
    for constraint in base.constraints:
        if constraint.kind == "CLAUSE":
            model.add_bool_or([variables[lit.variable_id] if lit.positive else variables[lit.variable_id].Not() for lit in constraint.literals])
        elif constraint.kind == "ALL_DIFFERENT":
            model.add_all_different([variables[vid] for vid in constraint.variable_ids])
        else:
            expr = sum(_int(coef) * variables[vid] for vid, coef in constraint.coefficients.items())
            rhs = _int(constraint.rhs)
            model.add(expr <= rhs if constraint.sense == "<=" else expr >= rhs if constraint.sense == ">=" else expr == rhs)
    if base.objective:
        expr = sum(_int(coef) * variables[vid] for vid, coef in base.objective.coefficients.items()) + _int(base.objective.offset)
        model.minimize(expr) if base.objective.sense == "MINIMIZE" else model.maximize(expr)
    return model, variables


def _scheduling_validate(problem: CPSATSchedulingProblem, assignment: Mapping[str, float], tolerance: float = 1e-7):
    validate_optimization_solution(problem.model, assignment, tolerance=tolerance)
    interval_map = {row.interval_id: row for row in problem.intervals}
    active: dict[str, tuple[int, int]] = {}
    for row in problem.intervals:
        present = True if not row.presence_variable_id else bool(round(float(assignment[row.presence_variable_id])))
        if not present: continue
        start, end = _int(assignment[row.start_variable_id]), _int(assignment[row.end_variable_id])
        if end != start + int(row.size):
            raise ValueError(f"scheduling interval equation violated: {row.interval_id}")
        active[row.interval_id] = (start, end)
    for constraint in problem.no_overlap:
        ids = [interval_id for interval_id in constraint.interval_ids if interval_id in active]
        for i, left_id in enumerate(ids):
            for right_id in ids[i + 1:]:
                left, right = active[left_id], active[right_id]
                if not (left[1] <= right[0] or right[1] <= left[0]):
                    raise ValueError(f"NO_OVERLAP violated: {constraint.constraint_id}")
    for constraint in problem.cumulative:
        if not active: continue
        starts = [active[i][0] for i in constraint.interval_ids if i in active]
        ends = [active[i][1] for i in constraint.interval_ids if i in active]
        if not starts: continue
        demand_map = dict(zip(constraint.interval_ids, constraint.demands))
        for tick in range(min(starts), max(ends)):
            load = sum(demand_map[i] for i in constraint.interval_ids if i in active and active[i][0] <= tick < active[i][1])
            if load > constraint.capacity:
                raise ValueError(f"CUMULATIVE violated: {constraint.constraint_id}")


def _advanced_convex_objective(problem: AdvancedConvexProblem, assignment: Mapping[str, float]) -> float | None:
    if problem.objective is None: return None
    value = problem.objective.linear.evaluate(assignment)
    sign = 1.0 if problem.objective.sense == "MINIMIZE" else -1.0
    for factor in problem.objective.quadratic_factors:
        v = factor.expression.evaluate(assignment)
        value += sign * float(factor.weight) * v * v
    return value


def _advanced_convex_validate(problem: AdvancedConvexProblem, assignment: Mapping[str, float], tolerance=1e-5):
    known = {row["variable_id"] for row in problem.variables}
    missing = sorted(known - set(assignment))
    if missing: raise ValueError(f"advanced convex assignment missing variables: {missing}")
    for row in problem.variables:
        value = float(assignment[row["variable_id"]])
        if row["lower_bound"] is not None and value < float(row["lower_bound"]) - tolerance: raise ValueError("advanced convex lower bound violated")
        if row["upper_bound"] is not None and value > float(row["upper_bound"]) + tolerance: raise ValueError("advanced convex upper bound violated")
    for row in problem.linear_constraints:
        lhs = sum(float(coef) * float(assignment[var]) for var, coef in row["coefficients"].items())
        rhs = row["rhs"]
        if row["sense"] == "<=" and lhs > rhs + tolerance: raise ValueError("advanced convex linear <= violated")
        if row["sense"] == ">=" and lhs < rhs - tolerance: raise ValueError("advanced convex linear >= violated")
        if row["sense"] == "==" and abs(lhs - rhs) > tolerance: raise ValueError("advanced convex equality violated")
    for row in problem.affine_soc_constraints:
        lhs = sqrt(sum(expr.evaluate(assignment) ** 2 for expr in row.lhs_rows))
        rhs = row.rhs.evaluate(assignment)
        if lhs > rhs + tolerance: raise ValueError(f"affine SOC violated: {row.constraint_id}")


def validate_advanced_result(request: AdvancedSolverRequest, result: AdvancedSolverResult):
    if result.request_id != request.request_id or result.request_fingerprint != request.fingerprint:
        raise ValueError("advanced result request identity mismatch")
    if result.problem_fingerprint != request.problem.fingerprint:
        raise ValueError("advanced result problem fingerprint mismatch")
    if result.solver.provider_id != request.required_provider:
        raise ValueError("advanced result provider mismatch")
    problem = request.problem
    if isinstance(problem, (FastSATProblem, IncrementalSATProblem)):
        if result.status == "SAT": validate_optimization_solution(problem.model, result.assignment)
        if isinstance(problem, IncrementalSATProblem) and result.unsat_core:
            assumptions = {(row.variable_id, row.positive) for row in problem.assumptions}
            if any((row.variable_id, row.positive) not in assumptions for row in result.unsat_core):
                raise ValueError("UNSAT core contains a literal outside request assumptions")
    elif isinstance(problem, CPSATSchedulingProblem):
        if result.status in {"SAT", "OPTIMAL", "FEASIBLE"}:
            _scheduling_validate(problem, result.assignment)
            expected = objective_value(problem.model, result.assignment)
            if expected is not None and result.objective_value is not None and not isclose(expected, result.objective_value, rel_tol=1e-7, abs_tol=1e-7):
                raise ValueError("scheduling objective mismatch")
    elif isinstance(problem, AdvancedMILPProblem):
        if result.status in {"SAT", "OPTIMAL", "FEASIBLE"}:
            validate_optimization_solution(problem.model, result.assignment)
            expected = objective_value(problem.model, result.assignment)
            if expected is not None and result.objective_value is not None and not isclose(expected, result.objective_value, rel_tol=1e-7, abs_tol=1e-7):
                raise ValueError("advanced MILP objective mismatch")
    elif isinstance(problem, AdvancedConvexProblem):
        if result.status in {"OPTIMAL", "FEASIBLE"}:
            _advanced_convex_validate(problem, result.assignment)
            expected = _advanced_convex_objective(problem, result.assignment)
            if expected is not None and result.objective_value is not None:
                scale = max(1.0, abs(expected), abs(result.objective_value))
                if abs(expected - result.objective_value) > 1e-5 * scale: raise ValueError("advanced convex objective mismatch")


def advanced_result_satisfies_request(request: AdvancedSolverRequest, result: AdvancedSolverResult) -> bool:
    if request.kind in {"FAST_SAT", "INCREMENTAL_SAT"}: return result.status in {"SAT", "UNSAT"}
    return result.status in {"OPTIMAL", "INFEASIBLE"}


def _run_fast_sat(request: AdvancedSolverRequest) -> AdvancedSolverResult:
    from pysat.solvers import Solver
    problem: FastSATProblem = request.problem  # type: ignore[assignment]
    mapping = {row.variable_id: index + 1 for index, row in enumerate(problem.model.variables)}
    clauses = [[mapping[lit.variable_id] if lit.positive else -mapping[lit.variable_id] for lit in row.literals] for row in problem.model.constraints]
    start = time.monotonic()
    try:
        with Solver(name="kissat404", bootstrap_with=clauses, use_timer=True) as solver:
            solved = solver.solve()
            assignment = {}
            if solved:
                values = set(solver.get_model() or [])
                assignment = {vid: 1.0 if idx in values else 0.0 for vid, idx in mapping.items()}
            result = AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, "SAT" if solved else "UNSAT", AdvancedSolverIdentity("kissat", "pysat:kissat404", _package_version("python-sat"), "kissat404"), assignment=assignment, telemetry=dict(solver.accum_stats() or {}), wall_time_ms=int((time.monotonic() - start) * 1000))
            validate_advanced_result(request, result); return result
    except Exception as exc:
        return AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, "ERROR", AdvancedSolverIdentity("kissat", "pysat:kissat404", _package_version("python-sat"), "kissat404"), wall_time_ms=int((time.monotonic() - start) * 1000), diagnostics=(f"{type(exc).__name__}: {exc}",))


def _run_incremental_sat(request: AdvancedSolverRequest) -> AdvancedSolverResult:
    problem: IncrementalSATProblem = request.problem  # type: ignore[assignment]
    start = time.monotonic()
    try:
        status, assignment, core, stats = _CADICAL_POOL.solve(problem)
        result = AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, status, AdvancedSolverIdentity("cadical-incremental", "pysat:cadical195", _package_version("python-sat"), "cadical195"), assignment=assignment, unsat_core=core, telemetry=stats, wall_time_ms=int((time.monotonic() - start) * 1000))
        validate_advanced_result(request, result); return result
    except Exception as exc:
        return AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, "ERROR", AdvancedSolverIdentity("cadical-incremental", "pysat:cadical195", _package_version("python-sat"), "cadical195"), wall_time_ms=int((time.monotonic() - start) * 1000), diagnostics=(f"{type(exc).__name__}: {exc}",))


def _run_scheduling(request: AdvancedSolverRequest) -> AdvancedSolverResult:
    from ortools.sat.python import cp_model
    problem: CPSATSchedulingProblem = request.problem  # type: ignore[assignment]
    start = time.monotonic()
    try:
        model, variables = _build_cp_base(cp_model, problem.model)
        intervals = {}
        for row in problem.intervals:
            start_var, end_var = variables[row.start_variable_id], variables[row.end_variable_id]
            if row.presence_variable_id:
                intervals[row.interval_id] = model.new_optional_interval_var(start_var, int(row.size), end_var, variables[row.presence_variable_id], row.interval_id)
            else:
                intervals[row.interval_id] = model.new_interval_var(start_var, int(row.size), end_var, row.interval_id)
        for row in problem.no_overlap: model.add_no_overlap([intervals[i] for i in row.interval_ids])
        for row in problem.cumulative: model.add_cumulative([intervals[i] for i in row.interval_ids], list(row.demands), int(row.capacity))
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = request.timeout_ms / 1000.0
        solver.parameters.num_search_workers = int(problem.search_workers)
        solver.parameters.random_seed = 0
        if problem.deterministic_time_limit is not None: solver.parameters.max_deterministic_time = float(problem.deterministic_time_limit)
        raw = solver.solve(model)
        if raw == cp_model.INFEASIBLE: status = "INFEASIBLE"
        elif raw == cp_model.OPTIMAL: status = "OPTIMAL" if problem.model.objective else "SAT"
        elif raw == cp_model.FEASIBLE: status = "FEASIBLE" if problem.model.objective else "SAT"
        else: status = "UNKNOWN"
        assignment = {vid: float(solver.value(var)) for vid, var in variables.items()} if status in {"SAT", "OPTIMAL", "FEASIBLE"} else {}
        objective = objective_value(problem.model, assignment) if assignment else None
        best_bound = float(solver.best_objective_bound) if problem.model.objective else None
        gap = None
        if objective is not None and best_bound is not None: gap = abs(objective - best_bound) / max(1.0, abs(objective))
        response = solver.response_proto
        result = AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, status, AdvancedSolverIdentity("ortools-cp-sat-scheduling", "ortools.cp-sat", _package_version("ortools"), "cp-sat"), assignment=assignment, objective_value=objective, best_bound=best_bound, relative_gap=gap, telemetry={"conflicts": int(solver.num_conflicts), "branches": int(solver.num_branches), "deterministic_time": float(getattr(response, "deterministic_time", 0.0)), "wall_time_seconds": float(solver.wall_time)}, wall_time_ms=int((time.monotonic() - start) * 1000))
        validate_advanced_result(request, result); return result
    except Exception as exc:
        return AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, "ERROR", AdvancedSolverIdentity("ortools-cp-sat-scheduling", "ortools.cp-sat", _package_version("ortools"), "cp-sat"), wall_time_ms=int((time.monotonic() - start) * 1000), diagnostics=(f"{type(exc).__name__}: {exc}",))


def _run_milp(request: AdvancedSolverRequest) -> AdvancedSolverResult:
    import highspy
    import numpy as np
    problem: AdvancedMILPProblem = request.problem  # type: ignore[assignment]
    start = time.monotonic(); h = highspy.Highs(); h.setOptionValue("output_flag", False); h.setOptionValue("time_limit", request.timeout_ms / 1000.0)
    try:
        if problem.mip_relative_gap is not None: h.setOptionValue("mip_rel_gap", float(problem.mip_relative_gap))
        if problem.node_limit is not None: h.setOptionValue("mip_max_nodes", int(problem.node_limit))
        variables = {}; order = []
        for row in problem.model.variables:
            var_type = highspy.HighsVarType.kInteger if row.domain in {"BOOL", "INTEGER"} else highspy.HighsVarType.kContinuous
            variables[row.variable_id] = h.addVariable(lb=float(row.lower_bound), ub=float(row.upper_bound), type=var_type, name=row.variable_id); order.append(row.variable_id)
        for constraint in problem.model.constraints:
            expr = sum(coeff * variables[vid] for vid, coeff in constraint.coefficients.items())
            h.addConstr(expr <= constraint.rhs if constraint.sense == "<=" else expr >= constraint.rhs if constraint.sense == ">=" else expr == constraint.rhs, name=constraint.constraint_id)
        if problem.model.objective:
            expr = sum(coeff * variables[vid] for vid, coeff in problem.model.objective.coefficients.items()) + float(problem.model.objective.offset)
            h.minimize(expr) if problem.model.objective.sense == "MINIMIZE" else h.maximize(expr)
        if problem.warm_start:
            index = np.array([order.index(name) for name in problem.warm_start], dtype=np.int32)
            value = np.array([problem.warm_start[name] for name in problem.warm_start], dtype=np.double)
            h.setSolution(len(index), index, value)
        h.run()
        raw_name = h.modelStatusToString(h.getModelStatus()); lower = raw_name.lower()
        if "optimal" in lower: status = "OPTIMAL" if problem.model.objective else "SAT"
        elif "infeasible" in lower: status = "INFEASIBLE"
        elif "time" in lower: status = "TIMEOUT"
        elif "unbounded" in lower: status = "UNBOUNDED"
        elif "feasible" in lower: status = "FEASIBLE"
        else: status = "UNKNOWN"
        assignment = {vid: float(h.val(var)) for vid, var in variables.items()} if status in {"SAT", "OPTIMAL", "FEASIBLE", "TIMEOUT"} and bool(getattr(h.getSolution(), "value_valid", True)) else {}
        objective = objective_value(problem.model, assignment) if assignment else None
        info = h.getInfo(); best_bound = getattr(info, "mip_dual_bound", None); gap = getattr(info, "mip_gap", None)
        best_bound = float(best_bound) if best_bound is not None else None; gap = float(gap) if gap is not None else None
        result = AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, status, AdvancedSolverIdentity("highs-advanced", "highspy", _package_version("highspy"), "highs"), assignment=assignment, objective_value=objective, best_bound=best_bound, relative_gap=gap, telemetry={"warm_start_supplied": bool(problem.warm_start), "mip_nodes": int(getattr(info, "mip_node_count", 0)), "simplex_iterations": int(getattr(info, "simplex_iteration_count", 0)), "mip_primal_bound": float(getattr(info, "mip_primal_bound", objective or 0.0)), "mip_dual_bound": best_bound, "mip_gap": gap, "raw_status": raw_name}, wall_time_ms=int((time.monotonic() - start) * 1000))
        validate_advanced_result(request, result); return result
    except Exception as exc:
        return AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, "ERROR", AdvancedSolverIdentity("highs-advanced", "highspy", _package_version("highspy"), "highs"), wall_time_ms=int((time.monotonic() - start) * 1000), diagnostics=(f"{type(exc).__name__}: {exc}",))


def _run_convex(request: AdvancedSolverRequest) -> AdvancedSolverResult:
    import cvxpy as cp
    problem: AdvancedConvexProblem = request.problem  # type: ignore[assignment]
    start = time.monotonic()
    try:
        variables = {row["variable_id"]: cp.Variable(name=row["variable_id"]) for row in problem.variables}; constraints = []
        for row in problem.variables:
            if row["lower_bound"] is not None: constraints.append(variables[row["variable_id"]] >= float(row["lower_bound"]))
            if row["upper_bound"] is not None: constraints.append(variables[row["variable_id"]] <= float(row["upper_bound"]))
        def expr(affine: AffineExpression):
            return float(affine.offset) + sum(float(coef) * variables[var] for var, coef in affine.coefficients.items())
        for row in problem.linear_constraints:
            lhs = sum(float(coef) * variables[var] for var, coef in row["coefficients"].items()); rhs = float(row["rhs"])
            constraints.append(lhs <= rhs if row["sense"] == "<=" else lhs >= rhs if row["sense"] == ">=" else lhs == rhs)
        for row in problem.affine_soc_constraints:
            constraints.append(cp.norm(cp.hstack([expr(item) for item in row.lhs_rows]), 2) <= expr(row.rhs))
        value_expr = 0.0
        if problem.objective:
            value_expr = expr(problem.objective.linear)
            sign = 1.0 if problem.objective.sense == "MINIMIZE" else -1.0
            value_expr += sum(sign * float(f.weight) * cp.square(expr(f.expression)) for f in problem.objective.quadratic_factors)
            objective = cp.Minimize(value_expr) if problem.objective.sense == "MINIMIZE" else cp.Maximize(value_expr)
        else: objective = cp.Minimize(0.0)
        cp_problem = cp.Problem(objective, constraints); installed = set(cp.installed_solvers())
        order = ("CLARABEL", "SCS") if problem.affine_soc_constraints else ("OSQP", "CLARABEL", "SCS")
        backend = next((name for name in order if name in installed), None)
        if not backend: raise RuntimeError(f"no supported CVXPY backend installed; found {sorted(installed)}")
        value = cp_problem.solve(solver=backend, verbose=False, warm_start=False)
        raw = str(cp_problem.status or "").lower()
        status = "OPTIMAL" if raw in {"optimal", "optimal_inaccurate"} else "INFEASIBLE" if raw in {"infeasible", "infeasible_inaccurate"} else "UNBOUNDED" if raw in {"unbounded", "unbounded_inaccurate"} else "UNKNOWN"
        assignment = {name: float(var.value) for name, var in variables.items()} if status == "OPTIMAL" else {}
        result = AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, status, AdvancedSolverIdentity("cvxpy-advanced", "cvxpy", _package_version("cvxpy"), backend), assignment=assignment, objective_value=float(value) if value is not None and assignment else None, telemetry={"backend": backend, "raw_status": raw, "num_iters": getattr(cp_problem.solver_stats, "num_iters", None)}, wall_time_ms=int((time.monotonic() - start) * 1000))
        validate_advanced_result(request, result); return result
    except Exception as exc:
        return AdvancedSolverResult(request.request_id, request.fingerprint, problem.fingerprint, "ERROR", AdvancedSolverIdentity("cvxpy-advanced", "cvxpy", _package_version("cvxpy"), "unknown"), wall_time_ms=int((time.monotonic() - start) * 1000), diagnostics=(f"{type(exc).__name__}: {exc}",))


def solve_advanced_request(request: AdvancedSolverRequest | Mapping[str, Any]) -> AdvancedSolverResult:
    request = request if isinstance(request, AdvancedSolverRequest) else AdvancedSolverRequest.from_dict(request)
    return {
        "FAST_SAT": _run_fast_sat,
        "INCREMENTAL_SAT": _run_incremental_sat,
        "CP_SAT_SCHEDULING": _run_scheduling,
        "MILP_ADVANCED": _run_milp,
        "CONVEX_ADVANCED": _run_convex,
    }[request.kind](request)


def reference_advanced_problems() -> dict[str, ProblemType]:
    from .optimization import OptimizationConstraint, OptimizationObjective, OptimizationVariable
    sat = OptimizationModel("advanced-sat", (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")), (OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x"), BooleanLiteral("y"))),), family="SAT")
    incremental = IncrementalSATProblem(sat, (BooleanLiteral("x", False), BooleanLiteral("y", False)))
    scheduling_base = OptimizationModel(
        "advanced-scheduling",
        (OptimizationVariable("s1", "INTEGER", 0, 8), OptimizationVariable("e1", "INTEGER", 0, 10), OptimizationVariable("s2", "INTEGER", 0, 8), OptimizationVariable("e2", "INTEGER", 0, 10)),
        (OptimizationConstraint("LINEAR", coefficients={"s2": 1, "e1": -1}, sense=">=", rhs=0),),
        OptimizationObjective("MINIMIZE", {"e2": 1}), family="CP_SAT",
    )
    scheduling = CPSATSchedulingProblem(scheduling_base, (SchedulingInterval("i1", "s1", 2, "e1"), SchedulingInterval("i2", "s2", 2, "e2")), (NoOverlapConstraint(("i1", "i2")),), (CumulativeConstraint(("i1", "i2"), (2, 2), 2),))
    milp_base = OptimizationModel("advanced-milp", (OptimizationVariable("x", "INTEGER", 0, 4), OptimizationVariable("y", "INTEGER", 0, 4)), (OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1}, sense="<=", rhs=4),), OptimizationObjective("MAXIMIZE", {"x": 2, "y": 1}), family="MILP")
    milp = AdvancedMILPProblem(milp_base, {"x": 1, "y": 1}, 0.0, 100)
    convex = AdvancedConvexProblem(
        variables=({"variable_id": "x", "lower_bound": -2, "upper_bound": 2}, {"variable_id": "y", "lower_bound": -2, "upper_bound": 2}),
        linear_constraints=({"coefficients": {"x": 1, "y": 1}, "sense": ">=", "rhs": 0.5, "constraint_id": "sum-floor"},),
        affine_soc_constraints=(AffineSOCConstraint((AffineExpression({"x": 1, "y": 1}), AffineExpression({"x": 1, "y": -1})), AffineExpression({}, 2.0)),),
        objective=AdvancedConvexObjective("MINIMIZE", AffineExpression({"x": -2, "y": -1}, 2.0), (QuadraticFactor(AffineExpression({"x": 1, "y": 1}), 1.0), QuadraticFactor(AffineExpression({"x": 1, "y": -1}), 0.5))),
        name="advanced-factorized-psd-affine-soc",
    )
    return {"FAST_SAT": FastSATProblem(sat), "INCREMENTAL_SAT": incremental, "CP_SAT_SCHEDULING": scheduling, "MILP_ADVANCED": milp, "CONVEX_ADVANCED": convex}


__all__ = [
    "ADVANCED_OPTIMIZATION_CONTRACT_ID", "ADVANCED_OPTIMIZATION_CONTRACT_VERSION", "ADVANCED_KINDS", "ADVANCED_CAPABILITIES", "ADVANCED_PROVIDERS",
    "FastSATProblem", "IncrementalSATProblem", "SchedulingInterval", "NoOverlapConstraint", "CumulativeConstraint", "CPSATSchedulingProblem",
    "AdvancedMILPProblem", "AffineExpression", "QuadraticFactor", "AffineSOCConstraint", "AdvancedConvexObjective", "AdvancedConvexProblem",
    "AdvancedSolverRequest", "AdvancedSolverIdentity", "AdvancedSolverResult", "advanced_problem_from_dict", "advanced_optimization_contract",
    "default_advanced_capability_contracts", "default_advanced_providers", "advanced_optimization_blueprint", "validate_advanced_result",
    "advanced_result_satisfies_request", "solve_advanced_request", "clear_incremental_sat_sessions", "reference_advanced_problems",
]
