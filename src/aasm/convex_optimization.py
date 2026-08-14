from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from importlib import metadata as importlib_metadata
from math import sqrt
from typing import Any, Mapping, Sequence
import time

from .semantic_result import semantic_fingerprint
from .typed_protocol import CapabilityContract, CapabilityProvider

CONVEX_OPTIMIZATION_CONTRACT_ID = "aasm.optimization.convex.v1"
CONVEX_OPTIMIZATION_CONTRACT_VERSION = "0.1.0"
CONVEX_CAPABILITY_ID = "solver.convex"
CONVEX_CAPABILITY_VERSION = "0.1.0"
CONVEX_STATUSES = ("OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNBOUNDED", "UNKNOWN", "TIMEOUT", "ERROR")


def _package_version(name: str) -> str:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


@dataclass(frozen=True)
class ConvexVariable:
    variable_id: str
    lower_bound: float | None = None
    upper_bound: float | None = None

    def __post_init__(self):
        if not self.variable_id.strip():
            raise ValueError("convex variable_id is required")
        if self.lower_bound is not None and self.upper_bound is not None and float(self.lower_bound) > float(self.upper_bound):
            raise ValueError("convex variable lower_bound exceeds upper_bound")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConvexVariable":
        return cls(**dict(value))


@dataclass(frozen=True)
class ConvexLinearConstraint:
    coefficients: dict[str, float]
    sense: str
    rhs: float
    constraint_id: str = ""

    def __post_init__(self):
        coeffs = {str(k): float(v) for k, v in sorted(self.coefficients.items()) if float(v) != 0.0}
        if not coeffs:
            raise ValueError("convex linear constraint requires coefficients")
        if self.sense not in {"<=", ">=", "=="}:
            raise ValueError("convex linear sense must be <=, >=, or ==")
        object.__setattr__(self, "coefficients", coeffs)
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"convex-linear-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {"coefficients": dict(self.coefficients), "sense": self.sense, "rhs": float(self.rhs)}

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConvexLinearConstraint":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class SecondOrderConeConstraint:
    variable_ids: tuple[str, ...]
    radius: float
    constraint_id: str = ""

    def __post_init__(self):
        variables = _uniq(self.variable_ids)
        if not variables:
            raise ValueError("SOC constraint requires variables")
        if float(self.radius) < 0:
            raise ValueError("SOC radius must be non-negative")
        object.__setattr__(self, "variable_ids", variables)
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"convex-soc-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {"variable_ids": list(self.variable_ids), "radius": float(self.radius)}

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SecondOrderConeConstraint":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class ConvexObjective:
    sense: str
    linear_coefficients: dict[str, float] = field(default_factory=dict)
    quadratic_diagonal: dict[str, float] = field(default_factory=dict)
    offset: float = 0.0

    def __post_init__(self):
        if self.sense not in {"MINIMIZE", "MAXIMIZE"}:
            raise ValueError("convex objective sense must be MINIMIZE or MAXIMIZE")
        linear = {str(k): float(v) for k, v in sorted(self.linear_coefficients.items()) if float(v) != 0.0}
        quad = {str(k): float(v) for k, v in sorted(self.quadratic_diagonal.items()) if float(v) != 0.0}
        if self.sense == "MINIMIZE" and any(value < 0 for value in quad.values()):
            raise ValueError("MINIMIZE quadratic diagonal must be positive semidefinite")
        if self.sense == "MAXIMIZE" and any(value > 0 for value in quad.values()):
            raise ValueError("MAXIMIZE quadratic diagonal must be negative semidefinite")
        if not linear and not quad:
            raise ValueError("convex objective requires linear or quadratic terms")
        object.__setattr__(self, "linear_coefficients", linear)
        object.__setattr__(self, "quadratic_diagonal", quad)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConvexObjective":
        return cls(**dict(value))


@dataclass(frozen=True)
class ConvexOptimizationModel:
    name: str
    variables: tuple[ConvexVariable | Mapping[str, Any], ...]
    linear_constraints: tuple[ConvexLinearConstraint | Mapping[str, Any], ...] = ()
    soc_constraints: tuple[SecondOrderConeConstraint | Mapping[str, Any], ...] = ()
    objective: ConvexObjective | Mapping[str, Any] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    model_id: str = ""

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("convex optimization model name is required")
        variables = tuple(row if isinstance(row, ConvexVariable) else ConvexVariable.from_dict(row) for row in self.variables)
        linear = tuple(row if isinstance(row, ConvexLinearConstraint) else ConvexLinearConstraint.from_dict(row) for row in self.linear_constraints)
        soc = tuple(row if isinstance(row, SecondOrderConeConstraint) else SecondOrderConeConstraint.from_dict(row) for row in self.soc_constraints)
        objective = self.objective
        if objective is not None and not isinstance(objective, ConvexObjective):
            objective = ConvexObjective.from_dict(objective)
        ids = [row.variable_id for row in variables]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("convex variable IDs must be non-empty and unique")
        known = set(ids)
        for constraint in linear:
            missing = sorted(set(constraint.coefficients) - known)
            if missing:
                raise ValueError(f"convex linear constraint references unknown variables: {missing}")
        for constraint in soc:
            missing = sorted(set(constraint.variable_ids) - known)
            if missing:
                raise ValueError(f"SOC constraint references unknown variables: {missing}")
        if objective is not None:
            missing = sorted((set(objective.linear_coefficients) | set(objective.quadratic_diagonal)) - known)
            if missing:
                raise ValueError(f"convex objective references unknown variables: {missing}")
        object.__setattr__(self, "variables", tuple(sorted(variables, key=lambda row: row.variable_id)))
        object.__setattr__(self, "linear_constraints", tuple(sorted(linear, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "soc_constraints", tuple(sorted(soc, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "objective", objective)
        if not self.model_id:
            object.__setattr__(self, "model_id", f"convex-model-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "variables": [row.to_dict() for row in self.variables],
            "linear_constraints": [row.to_dict() for row in self.linear_constraints],
            "soc_constraints": [row.to_dict() for row in self.soc_constraints],
            "objective": self.objective.to_dict() if self.objective else None,
            "metadata": deepcopy(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"model_id": self.model_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"model_id": self.model_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConvexOptimizationModel":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class ConvexOptimizationRequest:
    model: ConvexOptimizationModel | Mapping[str, Any]
    capability_id: str
    capability_version: str
    obligation_id: str
    timeout_ms: int = 30_000
    required_provider: str = "cvxpy"
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""

    def __post_init__(self):
        model = self.model if isinstance(self.model, ConvexOptimizationModel) else ConvexOptimizationModel.from_dict(self.model)
        object.__setattr__(self, "model", model)
        if self.capability_id != CONVEX_CAPABILITY_ID or self.capability_version != CONVEX_CAPABILITY_VERSION:
            raise ValueError("convex request capability mismatch")
        if not self.obligation_id.strip() or int(self.timeout_ms) <= 0:
            raise ValueError("convex request requires obligation and positive timeout")
        if self.required_provider != "cvxpy":
            raise ValueError("v0.45 reference convex provider is cvxpy")
        object.__setattr__(self, "dependency_fingerprints", _uniq(self.dependency_fingerprints))
        if not self.request_id:
            object.__setattr__(self, "request_id", f"convex-request-{semantic_fingerprint(self.identity_payload())[:20]}")

    @property
    def capability_token(self) -> str:
        return f"aasm.capability:{self.capability_id}@{self.capability_version}"

    def identity_payload(self) -> dict[str, Any]:
        return {
            "model": self.model.to_dict(),
            "capability_id": self.capability_id,
            "capability_version": self.capability_version,
            "obligation_id": self.obligation_id,
            "timeout_ms": int(self.timeout_ms),
            "required_provider": self.required_provider,
            "environment_fingerprint": self.environment_fingerprint,
            "dependency_fingerprints": list(self.dependency_fingerprints),
            "metadata": deepcopy(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"request_id": self.request_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"request_id": self.request_id, **self.identity_payload(), "capability_token": self.capability_token, "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConvexOptimizationRequest":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); payload.pop("capability_token", None); return cls(**payload)


@dataclass(frozen=True)
class ConvexSolverIdentity:
    provider_id: str
    implementation: str
    version: str
    backend_solver: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())


@dataclass(frozen=True)
class ConvexOptimizationResult:
    request_id: str
    request_fingerprint: str
    model_fingerprint: str
    status: str
    solver: ConvexSolverIdentity | Mapping[str, Any]
    assignment: dict[str, float] = field(default_factory=dict)
    objective_value: float | None = None
    wall_time_ms: int = 0
    statistics: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()
    result_id: str = ""

    def __post_init__(self):
        solver = self.solver if isinstance(self.solver, ConvexSolverIdentity) else ConvexSolverIdentity(**dict(self.solver))
        object.__setattr__(self, "solver", solver)
        if self.status not in CONVEX_STATUSES:
            raise ValueError(f"invalid convex result status: {self.status}")
        object.__setattr__(self, "assignment", {str(k): float(v) for k, v in sorted(self.assignment.items())})
        object.__setattr__(self, "diagnostics", tuple(map(str, self.diagnostics)))
        if not self.result_id:
            object.__setattr__(self, "result_id", f"convex-result-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_fingerprint": self.request_fingerprint,
            "model_fingerprint": self.model_fingerprint,
            "status": self.status,
            "solver": self.solver.to_dict(),
            "assignment": dict(self.assignment),
            "objective_value": self.objective_value,
            "wall_time_ms": int(self.wall_time_ms),
            "statistics": deepcopy(self.statistics),
            "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"result_id": self.result_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"result_id": self.result_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ConvexOptimizationResult":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


def convex_optimization_contract() -> dict[str, Any]:
    return {
        "contract_id": CONVEX_OPTIMIZATION_CONTRACT_ID,
        "contract_version": CONVEX_OPTIMIZATION_CONTRACT_VERSION,
        "canonical_ir": "AASM_OWNED",
        "capability_id": CONVEX_CAPABILITY_ID,
        "provider": "cvxpy",
        "supported_problem_classes": ["LP", "CONVEX_QP", "CONCAVE_QP_MAX", "SOC"],
        "quadratic_form": "DIAGONAL_ONLY_V0_45",
        "soc_form": "NORM2_VARIABLE_VECTOR_LE_CONSTANT_RADIUS",
        "scheduler": "EXISTING_AASM_RESOURCE_WORKER_LEASE",
        "result_authority": "EVIDENCE_ONLY",
        "optimality_semantics": "PROVIDER_VERDICT_FEASIBILITY_RECHECKED_BY_AASM",
        "direct_native_v44_paths_preserved": ["cadical", "ortools-cp-sat", "highs"],
    }


def default_convex_capability_contract() -> CapabilityContract:
    return CapabilityContract(
        CONVEX_CAPABILITY_ID,
        "OPERATOR",
        CONVEX_CAPABILITY_VERSION,
        input_schema={"type": "object"},
        output_schema={"type": "object"},
        evidence_types=("convex_optimization_result",),
        deterministic=False,
        metadata={"solver_family": "CONVEX", "canonical_ir": "AASM_OWNED", "result_authority": "EVIDENCE_ONLY"},
    )


def default_cvxpy_provider() -> CapabilityProvider:
    return CapabilityProvider(
        "cvxpy",
        CONVEX_CAPABILITY_ID,
        CONVEX_CAPABILITY_VERSION,
        "solver-resource-cvxpy",
        "cvxpy",
        metadata={"solver_version": _package_version("cvxpy"), "solver_family": "CONVEX", "provider_role": "NATIVE_MODELING_SOLVER"},
    )


def _objective_value(model: ConvexOptimizationModel, assignment: Mapping[str, float]) -> float | None:
    if model.objective is None:
        return None
    value = float(model.objective.offset)
    value += sum(float(coef) * float(assignment[var]) for var, coef in model.objective.linear_coefficients.items())
    value += sum(float(coef) * float(assignment[var]) ** 2 for var, coef in model.objective.quadratic_diagonal.items())
    return value


def validate_convex_solution(model: ConvexOptimizationModel, assignment: Mapping[str, float], *, tolerance: float = 1e-5) -> None:
    known = {row.variable_id for row in model.variables}
    missing = sorted(known - set(assignment))
    if missing:
        raise ValueError(f"convex assignment missing variables: {missing}")
    for variable in model.variables:
        value = float(assignment[variable.variable_id])
        if variable.lower_bound is not None and value < float(variable.lower_bound) - tolerance:
            raise ValueError(f"convex assignment violates lower bound: {variable.variable_id}")
        if variable.upper_bound is not None and value > float(variable.upper_bound) + tolerance:
            raise ValueError(f"convex assignment violates upper bound: {variable.variable_id}")
    for constraint in model.linear_constraints:
        lhs = sum(float(coef) * float(assignment[var]) for var, coef in constraint.coefficients.items())
        if constraint.sense == "<=" and lhs > float(constraint.rhs) + tolerance:
            raise ValueError(f"convex assignment violates linear constraint: {constraint.constraint_id}")
        if constraint.sense == ">=" and lhs < float(constraint.rhs) - tolerance:
            raise ValueError(f"convex assignment violates linear constraint: {constraint.constraint_id}")
        if constraint.sense == "==" and abs(lhs - float(constraint.rhs)) > tolerance:
            raise ValueError(f"convex assignment violates linear equality: {constraint.constraint_id}")
    for constraint in model.soc_constraints:
        norm = sqrt(sum(float(assignment[var]) ** 2 for var in constraint.variable_ids))
        if norm > float(constraint.radius) + tolerance:
            raise ValueError(f"convex assignment violates SOC constraint: {constraint.constraint_id}")


def validate_convex_result(request: ConvexOptimizationRequest, result: ConvexOptimizationResult) -> None:
    if result.request_id != request.request_id or result.request_fingerprint != request.fingerprint:
        raise ValueError("convex result request identity mismatch")
    if result.model_fingerprint != request.model.fingerprint:
        raise ValueError("convex result model fingerprint mismatch")
    if result.solver.provider_id != request.required_provider:
        raise ValueError("convex result provider mismatch")
    if result.status in {"OPTIMAL", "FEASIBLE"}:
        validate_convex_solution(request.model, result.assignment)
        expected = _objective_value(request.model, result.assignment)
        if expected is not None and result.objective_value is not None:
            scale = max(1.0, abs(expected), abs(float(result.objective_value)))
            if abs(expected - float(result.objective_value)) > 1e-5 * scale:
                raise ValueError("convex result objective does not match canonical model")


def _choose_cvxpy_solver(model: ConvexOptimizationModel, installed: set[str]) -> str:
    if model.soc_constraints:
        order = ("CLARABEL", "SCS")
    elif model.objective and model.objective.quadratic_diagonal:
        order = ("OSQP", "CLARABEL", "SCS")
    else:
        order = ("CLARABEL", "SCS", "SCIPY")
    for name in order:
        if name in installed:
            return name
    raise RuntimeError(f"no supported CVXPY backend installed; found {sorted(installed)}")


def solve_convex_request(request: ConvexOptimizationRequest) -> ConvexOptimizationResult:
    started = time.perf_counter()
    try:
        import cvxpy as cp
        model = request.model
        variables = {row.variable_id: cp.Variable(name=row.variable_id) for row in model.variables}
        constraints = []
        for row in model.variables:
            if row.lower_bound is not None:
                constraints.append(variables[row.variable_id] >= float(row.lower_bound))
            if row.upper_bound is not None:
                constraints.append(variables[row.variable_id] <= float(row.upper_bound))
        for row in model.linear_constraints:
            expression = sum(float(coef) * variables[var] for var, coef in row.coefficients.items())
            if row.sense == "<=": constraints.append(expression <= float(row.rhs))
            elif row.sense == ">=": constraints.append(expression >= float(row.rhs))
            else: constraints.append(expression == float(row.rhs))
        for row in model.soc_constraints:
            constraints.append(cp.norm(cp.hstack([variables[var] for var in row.variable_ids]), 2) <= float(row.radius))
        expression = 0.0
        if model.objective is not None:
            expression += float(model.objective.offset)
            expression += sum(float(coef) * variables[var] for var, coef in model.objective.linear_coefficients.items())
            expression += sum(float(coef) * cp.square(variables[var]) for var, coef in model.objective.quadratic_diagonal.items())
            objective = cp.Minimize(expression) if model.objective.sense == "MINIMIZE" else cp.Maximize(expression)
        else:
            objective = cp.Minimize(0.0)
        problem = cp.Problem(objective, constraints)
        backend = _choose_cvxpy_solver(model, set(cp.installed_solvers()))
        value = problem.solve(solver=backend, verbose=False, warm_start=False)
        raw = str(problem.status or "").lower()
        if raw in {"optimal", "optimal_inaccurate"}: status = "OPTIMAL"
        elif raw in {"infeasible", "infeasible_inaccurate"}: status = "INFEASIBLE"
        elif raw in {"unbounded", "unbounded_inaccurate"}: status = "UNBOUNDED"
        elif raw in {"user_limit"}: status = "TIMEOUT"
        else: status = "UNKNOWN"
        assignment = {}
        if status in {"OPTIMAL", "FEASIBLE"}:
            for name, variable in variables.items():
                if variable.value is None:
                    raise RuntimeError(f"CVXPY returned no value for {name}")
                assignment[name] = float(variable.value)
        stats = problem.solver_stats
        result = ConvexOptimizationResult(
            request.request_id,
            request.fingerprint,
            model.fingerprint,
            status,
            ConvexSolverIdentity("cvxpy", "cvxpy", _package_version("cvxpy"), backend),
            assignment=assignment,
            objective_value=float(value) if value is not None and status in {"OPTIMAL", "FEASIBLE"} else None,
            wall_time_ms=int((time.perf_counter() - started) * 1000),
            statistics={
                "solver_name": getattr(stats, "solver_name", backend),
                "solve_time": getattr(stats, "solve_time", None),
                "num_iters": getattr(stats, "num_iters", None),
                "raw_status": raw,
            },
        )
        validate_convex_result(request, result)
        return result
    except Exception as exc:
        return ConvexOptimizationResult(
            request.request_id,
            request.fingerprint,
            request.model.fingerprint,
            "ERROR",
            ConvexSolverIdentity("cvxpy", "cvxpy", _package_version("cvxpy"), "unknown"),
            wall_time_ms=int((time.perf_counter() - started) * 1000),
            diagnostics=(f"{type(exc).__name__}: {exc}",),
        )


def reference_convex_models() -> dict[str, ConvexOptimizationModel]:
    qp = ConvexOptimizationModel(
        "reference-convex-qp",
        variables=(ConvexVariable("x", -5, 5), ConvexVariable("y", -5, 5)),
        linear_constraints=(ConvexLinearConstraint({"x": 1, "y": 1}, ">=", 1),),
        objective=ConvexObjective("MINIMIZE", {"x": -2, "y": -4}, {"x": 1, "y": 1}, 5),
    )
    soc = ConvexOptimizationModel(
        "reference-soc",
        variables=(ConvexVariable("x", -1, 1), ConvexVariable("y", -1, 1)),
        soc_constraints=(SecondOrderConeConstraint(("x", "y"), 1.0),),
        objective=ConvexObjective("MAXIMIZE", {"x": 1.0}),
    )
    return {"QP": qp, "SOC": soc}


__all__ = [
    "CONVEX_OPTIMIZATION_CONTRACT_ID", "CONVEX_OPTIMIZATION_CONTRACT_VERSION", "CONVEX_CAPABILITY_ID",
    "ConvexVariable", "ConvexLinearConstraint", "SecondOrderConeConstraint", "ConvexObjective",
    "ConvexOptimizationModel", "ConvexOptimizationRequest", "ConvexSolverIdentity", "ConvexOptimizationResult",
    "convex_optimization_contract", "default_convex_capability_contract", "default_cvxpy_provider",
    "validate_convex_solution", "validate_convex_result", "solve_convex_request", "reference_convex_models",
]
