from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from importlib import metadata as importlib_metadata
from math import isclose
from typing import Any, Mapping, Sequence
import time

from .semantic_result import semantic_fingerprint
from .typed_protocol import CapabilityContract, CapabilityProvider

OPTIMIZATION_CONTRACT_ID = "aasm.optimization.v1"
OPTIMIZATION_CONTRACT_VERSION = "0.1.0"
OPTIMIZATION_FAMILIES = ("SAT", "CP_SAT", "MILP")
OPTIMIZATION_VARIABLE_DOMAINS = ("BOOL", "INTEGER", "CONTINUOUS")
OPTIMIZATION_CONSTRAINT_KINDS = ("CLAUSE", "LINEAR", "ALL_DIFFERENT")
OPTIMIZATION_SENSES = ("MINIMIZE", "MAXIMIZE")
OPTIMIZATION_STATUSES = (
    "SAT", "UNSAT", "OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN", "TIMEOUT", "ERROR"
)
OPTIMIZATION_CAPABILITIES = {
    "SAT": "solver.sat",
    "CP_SAT": "solver.cp_sat",
    "MILP": "solver.milp",
}


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _is_intlike(value: float | int) -> bool:
    return isclose(float(value), round(float(value)), abs_tol=1e-9)


def _package_version(name: str) -> str:
    try:
        return importlib_metadata.version(name)
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


@dataclass(frozen=True)
class BooleanLiteral:
    variable_id: str
    positive: bool = True

    def __post_init__(self):
        if not self.variable_id.strip():
            raise ValueError("literal variable_id is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BooleanLiteral":
        return cls(**dict(value))


@dataclass(frozen=True)
class OptimizationVariable:
    variable_id: str
    domain: str
    lower_bound: float = 0.0
    upper_bound: float = 1.0

    def __post_init__(self):
        if not self.variable_id.strip():
            raise ValueError("optimization variable_id is required")
        if self.domain not in OPTIMIZATION_VARIABLE_DOMAINS:
            raise ValueError(f"invalid optimization variable domain: {self.domain}")
        if float(self.lower_bound) > float(self.upper_bound):
            raise ValueError("optimization variable lower_bound exceeds upper_bound")
        if self.domain == "BOOL" and (float(self.lower_bound) < 0 or float(self.upper_bound) > 1):
            raise ValueError("BOOL variable bounds must lie within [0,1]")
        if self.domain in {"BOOL", "INTEGER"} and not (
            _is_intlike(self.lower_bound) and _is_intlike(self.upper_bound)
        ):
            raise ValueError("integer variable bounds must be integral")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OptimizationVariable":
        return cls(**dict(value))


@dataclass(frozen=True)
class OptimizationConstraint:
    kind: str
    literals: tuple[BooleanLiteral | Mapping[str, Any], ...] = ()
    coefficients: dict[str, float] = field(default_factory=dict)
    sense: str = ""
    rhs: float = 0.0
    variable_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    constraint_id: str = ""

    def __post_init__(self):
        if self.kind not in OPTIMIZATION_CONSTRAINT_KINDS:
            raise ValueError(f"invalid optimization constraint kind: {self.kind}")
        literals = tuple(
            row if isinstance(row, BooleanLiteral) else BooleanLiteral.from_dict(row)
            for row in self.literals
        )
        object.__setattr__(self, "literals", tuple(sorted(literals, key=lambda row: (row.variable_id, not row.positive))))
        object.__setattr__(self, "coefficients", {str(k): float(v) for k, v in sorted(self.coefficients.items()) if float(v) != 0.0})
        object.__setattr__(self, "variable_ids", _uniq(self.variable_ids))
        if self.kind == "CLAUSE":
            if not self.literals:
                raise ValueError("CLAUSE requires at least one literal")
            if self.coefficients or self.variable_ids or self.sense:
                raise ValueError("CLAUSE may only define literals")
        elif self.kind == "LINEAR":
            if not self.coefficients:
                raise ValueError("LINEAR constraint requires coefficients")
            if self.sense not in {"<=", ">=", "=="}:
                raise ValueError("LINEAR sense must be <=, >=, or ==")
            if self.literals or self.variable_ids:
                raise ValueError("LINEAR may only define coefficients/sense/rhs")
        elif self.kind == "ALL_DIFFERENT":
            if len(self.variable_ids) < 2:
                raise ValueError("ALL_DIFFERENT requires at least two variables")
            if self.literals or self.coefficients or self.sense:
                raise ValueError("ALL_DIFFERENT may only define variable_ids")
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"constraint-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "literals": [row.to_dict() for row in self.literals],
            "coefficients": dict(self.coefficients),
            "sense": self.sense,
            "rhs": float(self.rhs),
            "variable_ids": list(self.variable_ids),
            "metadata": deepcopy(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OptimizationConstraint":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class OptimizationObjective:
    sense: str
    coefficients: dict[str, float]
    offset: float = 0.0

    def __post_init__(self):
        if self.sense not in OPTIMIZATION_SENSES:
            raise ValueError(f"invalid optimization objective sense: {self.sense}")
        coeffs = {str(k): float(v) for k, v in sorted(self.coefficients.items()) if float(v) != 0.0}
        if not coeffs:
            raise ValueError("optimization objective requires coefficients")
        object.__setattr__(self, "coefficients", coeffs)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OptimizationObjective":
        return cls(**dict(value))


@dataclass(frozen=True)
class OptimizationModel:
    name: str
    variables: tuple[OptimizationVariable | Mapping[str, Any], ...]
    constraints: tuple[OptimizationConstraint | Mapping[str, Any], ...]
    objective: OptimizationObjective | Mapping[str, Any] | None = None
    family: str = "AUTO"
    metadata: dict[str, Any] = field(default_factory=dict)
    model_id: str = ""

    def __post_init__(self):
        if not self.name.strip():
            raise ValueError("optimization model name is required")
        variables = tuple(row if isinstance(row, OptimizationVariable) else OptimizationVariable.from_dict(row) for row in self.variables)
        constraints = tuple(row if isinstance(row, OptimizationConstraint) else OptimizationConstraint.from_dict(row) for row in self.constraints)
        objective = self.objective
        if objective is not None and not isinstance(objective, OptimizationObjective):
            objective = OptimizationObjective.from_dict(objective)
        ids = [row.variable_id for row in variables]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("optimization variable IDs must be non-empty and unique")
        known = set(ids)
        for constraint in constraints:
            refs = {row.variable_id for row in constraint.literals} | set(constraint.coefficients) | set(constraint.variable_ids)
            missing = sorted(refs - known)
            if missing:
                raise ValueError(f"optimization constraint references unknown variables: {missing}")
            for literal in constraint.literals:
                variable = next(row for row in variables if row.variable_id == literal.variable_id)
                if variable.domain != "BOOL":
                    raise ValueError("CLAUSE literals require BOOL variables")
        if objective is not None:
            missing = sorted(set(objective.coefficients) - known)
            if missing:
                raise ValueError(f"optimization objective references unknown variables: {missing}")
        object.__setattr__(self, "variables", tuple(sorted(variables, key=lambda row: row.variable_id)))
        object.__setattr__(self, "constraints", tuple(sorted(constraints, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "objective", objective)
        inferred = infer_solver_family_parts(self.variables, self.constraints, objective)
        if self.family not in {"AUTO", *OPTIMIZATION_FAMILIES}:
            raise ValueError(f"invalid optimization family: {self.family}")
        if self.family != "AUTO" and self.family != inferred and not _family_can_accept(self.family, self.variables, self.constraints, objective):
            raise ValueError(f"declared optimization family {self.family} cannot represent this model")
        if not self.model_id:
            object.__setattr__(self, "model_id", f"optimization-model-{semantic_fingerprint(self.identity_payload())[:20]}")

    @property
    def solver_family(self) -> str:
        return self.family if self.family != "AUTO" else infer_solver_family_parts(self.variables, self.constraints, self.objective)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "variables": [row.to_dict() for row in self.variables],
            "constraints": [row.to_dict() for row in self.constraints],
            "objective": self.objective.to_dict() if self.objective else None,
            "family": self.family,
            "metadata": deepcopy(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"model_id": self.model_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"model_id": self.model_id, **self.identity_payload(), "solver_family": self.solver_family, "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OptimizationModel":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); payload.pop("solver_family", None); return cls(**payload)


def _family_can_accept(family: str, variables, constraints, objective) -> bool:
    if family == "SAT":
        return objective is None and all(row.domain == "BOOL" for row in variables) and all(row.kind == "CLAUSE" for row in constraints)
    if family == "CP_SAT":
        if any(row.domain == "CONTINUOUS" for row in variables):
            return False
        for row in constraints:
            if row.kind == "LINEAR" and (not all(_is_intlike(v) for v in row.coefficients.values()) or not _is_intlike(row.rhs)):
                return False
        return objective is None or all(_is_intlike(v) for v in objective.coefficients.values()) and _is_intlike(objective.offset)
    if family == "MILP":
        return all(row.kind == "LINEAR" for row in constraints)
    return False


def infer_solver_family_parts(variables, constraints, objective) -> str:
    if _family_can_accept("SAT", variables, constraints, objective):
        return "SAT"
    if _family_can_accept("CP_SAT", variables, constraints, objective):
        return "CP_SAT"
    if _family_can_accept("MILP", variables, constraints, objective):
        return "MILP"
    raise ValueError("model cannot be represented by SAT, CP-SAT, or MILP reference lowering")


def infer_solver_family(model: OptimizationModel | Mapping[str, Any]) -> str:
    parsed = model if isinstance(model, OptimizationModel) else OptimizationModel.from_dict(model)
    return parsed.solver_family


@dataclass(frozen=True)
class OptimizationRequest:
    model: OptimizationModel | Mapping[str, Any]
    capability_id: str
    capability_version: str
    obligation_id: str
    timeout_ms: int = 30_000
    required_provider: str = ""
    accept_feasible: bool = False
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    request_id: str = ""

    def __post_init__(self):
        model = self.model if isinstance(self.model, OptimizationModel) else OptimizationModel.from_dict(self.model)
        object.__setattr__(self, "model", model)
        if self.capability_id != OPTIMIZATION_CAPABILITIES[model.solver_family]:
            raise ValueError("optimization request capability does not match model solver family")
        if not self.capability_version.strip() or not self.obligation_id.strip():
            raise ValueError("optimization request capability_version and obligation_id are required")
        if int(self.timeout_ms) <= 0:
            raise ValueError("optimization timeout_ms must be positive")
        object.__setattr__(self, "dependency_fingerprints", _uniq(self.dependency_fingerprints))
        if not self.request_id:
            object.__setattr__(self, "request_id", f"optimization-request-{semantic_fingerprint(self.identity_payload())[:20]}")

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
            "accept_feasible": bool(self.accept_feasible),
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
    def from_dict(cls, value: Mapping[str, Any]) -> "OptimizationRequest":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); payload.pop("capability_token", None); return cls(**payload)


@dataclass(frozen=True)
class OptimizationSolverIdentity:
    provider_id: str
    implementation: str
    version: str
    invocation: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "invocation": list(self.invocation)}

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())


@dataclass(frozen=True)
class OptimizationResult:
    request_id: str
    request_fingerprint: str
    model_fingerprint: str
    status: str
    solver: OptimizationSolverIdentity | Mapping[str, Any]
    assignment: dict[str, float] = field(default_factory=dict)
    objective_value: float | None = None
    best_bound: float | None = None
    relative_gap: float | None = None
    wall_time_ms: int = 0
    statistics: dict[str, Any] = field(default_factory=dict)
    diagnostics: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    result_id: str = ""

    def __post_init__(self):
        solver = self.solver if isinstance(self.solver, OptimizationSolverIdentity) else OptimizationSolverIdentity(**dict(self.solver))
        object.__setattr__(self, "solver", solver)
        if self.status not in OPTIMIZATION_STATUSES:
            raise ValueError(f"invalid optimization status: {self.status}")
        if int(self.wall_time_ms) < 0:
            raise ValueError("optimization wall_time_ms must be non-negative")
        object.__setattr__(self, "assignment", {str(k): float(v) for k, v in sorted(self.assignment.items())})
        object.__setattr__(self, "diagnostics", tuple(map(str, self.diagnostics)))
        if not self.result_id:
            object.__setattr__(self, "result_id", f"optimization-result-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "request_fingerprint": self.request_fingerprint,
            "model_fingerprint": self.model_fingerprint,
            "status": self.status,
            "solver": self.solver.to_dict(),
            "assignment": dict(self.assignment),
            "objective_value": self.objective_value,
            "best_bound": self.best_bound,
            "relative_gap": self.relative_gap,
            "wall_time_ms": int(self.wall_time_ms),
            "statistics": deepcopy(self.statistics),
            "diagnostics": list(self.diagnostics),
            "metadata": deepcopy(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"result_id": self.result_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"result_id": self.result_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "OptimizationResult":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


def optimization_contract() -> dict[str, Any]:
    return {
        "contract_id": OPTIMIZATION_CONTRACT_ID,
        "contract_version": OPTIMIZATION_CONTRACT_VERSION,
        "families": list(OPTIMIZATION_FAMILIES),
        "capabilities": dict(OPTIMIZATION_CAPABILITIES),
        "canonical_ir": "AASM_OWNED",
        "inner_loop_ownership": "NATIVE_SOLVER_PROVIDER",
        "scheduler": "EXISTING_AASM_RESOURCE_WORKER_LEASE",
        "result_authority": "EVIDENCE_ONLY",
        "reuse": "V0.41_EXACT_VALIDATED_REUSE",
        "provider_admission": "EXISTING_CAPABILITY_ABI_POLICY_OR_CONTROLLER",
        "default_providers": ["cadical", "ortools-cp-sat", "highs"],
        "formal_providers_preserved": ["z3", "cvc5", "vampire", "lean4"],
    }


def default_optimization_capability_contracts() -> tuple[CapabilityContract, ...]:
    generic_in = {"type": "object"}
    generic_out = {"type": "object"}
    return (
        CapabilityContract("solver.sat", "OPERATOR", "0.1.0", generic_in, generic_out, evidence_types=("optimization_result",), metadata={"solver_family": "SAT"}),
        CapabilityContract("solver.cp_sat", "OPERATOR", "0.1.0", generic_in, generic_out, evidence_types=("optimization_result",), metadata={"solver_family": "CP_SAT"}),
        CapabilityContract("solver.milp", "OPERATOR", "0.1.0", generic_in, generic_out, evidence_types=("optimization_result",), metadata={"solver_family": "MILP"}),
    )


def default_optimization_providers() -> tuple[CapabilityProvider, ...]:
    return (
        CapabilityProvider("cadical", "solver.sat", "0.1.0", "solver-cadical", "pysat:cadical195", metadata={"python_package": "python-sat", "solver_family": "SAT"}),
        CapabilityProvider("ortools-cp-sat", "solver.cp_sat", "0.1.0", "solver-ortools-cp-sat", "ortools.cp-sat", metadata={"python_package": "ortools", "solver_family": "CP_SAT"}),
        CapabilityProvider("highs", "solver.milp", "0.1.0", "solver-highs", "highspy", metadata={"python_package": "highspy", "solver_family": "MILP"}),
    )


def optimization_blueprint() -> dict[str, Any]:
    return {
        "contract": optimization_contract(),
        "capabilities": [row.to_dict() for row in default_optimization_capability_contracts()],
        "providers": [row.to_dict() for row in default_optimization_providers()],
        "execution": "EXISTING_RESOURCE_WORKER_LEASE_BOUNDARY",
        "registration": "EXPLICIT_POLICY_ADMISSION_REQUIRED",
    }


def _value(model: OptimizationModel, assignment: Mapping[str, float], variable_id: str) -> float:
    if variable_id not in assignment:
        raise ValueError(f"solution assignment missing variable: {variable_id}")
    return float(assignment[variable_id])


def objective_value(model: OptimizationModel, assignment: Mapping[str, float]) -> float | None:
    if model.objective is None:
        return None
    return float(model.objective.offset + sum(coeff * _value(model, assignment, vid) for vid, coeff in model.objective.coefficients.items()))


def validate_optimization_solution(model: OptimizationModel, assignment: Mapping[str, float], *, tolerance: float = 1e-7) -> None:
    variables = {row.variable_id: row for row in model.variables}
    for variable_id, variable in variables.items():
        value = _value(model, assignment, variable_id)
        if value < float(variable.lower_bound) - tolerance or value > float(variable.upper_bound) + tolerance:
            raise ValueError(f"solution violates bounds for {variable_id}")
        if variable.domain in {"BOOL", "INTEGER"} and not isclose(value, round(value), abs_tol=tolerance):
            raise ValueError(f"solution violates integrality for {variable_id}")
    for constraint in model.constraints:
        if constraint.kind == "CLAUSE":
            if not any((bool(round(_value(model, assignment, lit.variable_id))) is lit.positive) for lit in constraint.literals):
                raise ValueError(f"solution violates clause {constraint.constraint_id}")
        elif constraint.kind == "ALL_DIFFERENT":
            values = [_value(model, assignment, vid) for vid in constraint.variable_ids]
            if len({round(value, 9) for value in values}) != len(values):
                raise ValueError(f"solution violates all-different {constraint.constraint_id}")
        else:
            lhs = sum(coeff * _value(model, assignment, vid) for vid, coeff in constraint.coefficients.items())
            if constraint.sense == "<=" and lhs > constraint.rhs + tolerance:
                raise ValueError(f"solution violates linear <= {constraint.constraint_id}")
            if constraint.sense == ">=" and lhs < constraint.rhs - tolerance:
                raise ValueError(f"solution violates linear >= {constraint.constraint_id}")
            if constraint.sense == "==" and not isclose(lhs, constraint.rhs, abs_tol=tolerance):
                raise ValueError(f"solution violates linear == {constraint.constraint_id}")


def validate_optimization_result(request: OptimizationRequest, result: OptimizationResult) -> None:
    if result.request_id != request.request_id or result.request_fingerprint != request.fingerprint:
        raise ValueError("optimization result request fingerprint mismatch")
    if result.model_fingerprint != request.model.fingerprint:
        raise ValueError("optimization result model fingerprint mismatch")
    if result.status in {"SAT", "OPTIMAL", "FEASIBLE"}:
        validate_optimization_solution(request.model, result.assignment)
        expected = objective_value(request.model, result.assignment)
        if expected is not None:
            if result.objective_value is None or not isclose(float(result.objective_value), expected, rel_tol=1e-7, abs_tol=1e-7):
                raise ValueError("optimization result objective value does not match assignment")


def optimization_result_satisfies_request(request: OptimizationRequest, result: OptimizationResult) -> bool:
    if result.status in {"SAT", "UNSAT", "OPTIMAL", "INFEASIBLE"}:
        return True
    return result.status == "FEASIBLE" and request.accept_feasible


class PySATCadicalWorker:
    provider_id = "cadical"

    def __init__(self, solver_name: str = "cadical195"):
        self.solver_name = solver_name

    def run(self, request: OptimizationRequest) -> OptimizationResult:
        if request.model.solver_family != "SAT":
            raise ValueError("CaDiCaL worker requires SAT-compatible model")
        from pysat.solvers import Solver
        mapping = {row.variable_id: index + 1 for index, row in enumerate(request.model.variables)}
        clauses = [[mapping[lit.variable_id] if lit.positive else -mapping[lit.variable_id] for lit in row.literals] for row in request.model.constraints]
        start = time.monotonic()
        try:
            with Solver(name=self.solver_name, bootstrap_with=clauses, use_timer=True) as solver:
                solved = solver.solve()
                assignment: dict[str, float] = {}
                if solved:
                    model_values = set(solver.get_model() or [])
                    for variable_id, index in mapping.items():
                        assignment[variable_id] = 1.0 if index in model_values else 0.0
                stats = dict(solver.accum_stats() or {})
                status = "SAT" if solved else "UNSAT"
        except Exception as exc:
            return OptimizationResult(request.request_id, request.fingerprint, request.model.fingerprint, "ERROR", OptimizationSolverIdentity(self.provider_id, f"pysat:{self.solver_name}", _package_version("python-sat"), metadata={"solver_name": self.solver_name}), wall_time_ms=int((time.monotonic() - start) * 1000), diagnostics=(f"{type(exc).__name__}: {exc}",))
        return OptimizationResult(request.request_id, request.fingerprint, request.model.fingerprint, status, OptimizationSolverIdentity(self.provider_id, f"pysat:{self.solver_name}", _package_version("python-sat"), metadata={"solver_name": self.solver_name}), assignment=assignment, wall_time_ms=int((time.monotonic() - start) * 1000), statistics=stats)


class ORToolsCPSATWorker:
    provider_id = "ortools-cp-sat"

    @staticmethod
    def _integer(value: float) -> int:
        if not _is_intlike(value):
            raise ValueError("CP-SAT lowering requires integral coefficients, bounds, rhs, and objective")
        return int(round(float(value)))

    def run(self, request: OptimizationRequest) -> OptimizationResult:
        if request.model.solver_family != "CP_SAT":
            raise ValueError("OR-Tools worker requires CP_SAT-compatible model")
        from ortools.sat.python import cp_model
        start = time.monotonic()
        model = cp_model.CpModel()
        variables: dict[str, Any] = {}
        for row in request.model.variables:
            lb, ub = self._integer(row.lower_bound), self._integer(row.upper_bound)
            variables[row.variable_id] = model.new_bool_var(row.variable_id) if row.domain == "BOOL" and lb == 0 and ub == 1 else model.new_int_var(lb, ub, row.variable_id)
        for constraint in request.model.constraints:
            if constraint.kind == "CLAUSE":
                model.add_bool_or([variables[lit.variable_id] if lit.positive else variables[lit.variable_id].Not() for lit in constraint.literals])
            elif constraint.kind == "ALL_DIFFERENT":
                model.add_all_different([variables[vid] for vid in constraint.variable_ids])
            else:
                expr = sum(self._integer(coeff) * variables[vid] for vid, coeff in constraint.coefficients.items())
                rhs = self._integer(constraint.rhs)
                model.add(expr <= rhs if constraint.sense == "<=" else expr >= rhs if constraint.sense == ">=" else expr == rhs)
        if request.model.objective:
            expr = sum(self._integer(coeff) * variables[vid] for vid, coeff in request.model.objective.coefficients.items()) + self._integer(request.model.objective.offset)
            model.minimize(expr) if request.model.objective.sense == "MINIMIZE" else model.maximize(expr)
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = request.timeout_ms / 1000.0
        solver.parameters.num_search_workers = 1
        solver.parameters.random_seed = 0
        try:
            raw = solver.solve(model)
            raw_name = solver.status_name(raw)
            if raw == cp_model.INFEASIBLE:
                status = "UNSAT" if request.model.objective is None else "INFEASIBLE"
            elif raw == cp_model.OPTIMAL:
                status = "SAT" if request.model.objective is None else "OPTIMAL"
            elif raw == cp_model.FEASIBLE:
                status = "SAT" if request.model.objective is None else "FEASIBLE"
            elif raw == cp_model.UNKNOWN:
                status = "UNKNOWN"
            else:
                status = "ERROR"
            assignment = {vid: float(solver.value(var)) for vid, var in variables.items()} if status in {"SAT", "OPTIMAL", "FEASIBLE"} else {}
            objective = float(solver.objective_value) if request.model.objective and assignment else None
            best_bound = float(solver.best_objective_bound) if request.model.objective else None
            stats = {"conflicts": int(solver.num_conflicts), "branches": int(solver.num_branches), "wall_time_seconds": float(solver.wall_time), "raw_status": raw_name}
            return OptimizationResult(request.request_id, request.fingerprint, request.model.fingerprint, status, OptimizationSolverIdentity(self.provider_id, "ortools.cp-sat", _package_version("ortools")), assignment=assignment, objective_value=objective, best_bound=best_bound, wall_time_ms=int((time.monotonic() - start) * 1000), statistics=stats)
        except Exception as exc:
            return OptimizationResult(request.request_id, request.fingerprint, request.model.fingerprint, "ERROR", OptimizationSolverIdentity(self.provider_id, "ortools.cp-sat", _package_version("ortools")), wall_time_ms=int((time.monotonic() - start) * 1000), diagnostics=(f"{type(exc).__name__}: {exc}",))


class HighsMILPWorker:
    provider_id = "highs"

    def run(self, request: OptimizationRequest) -> OptimizationResult:
        if request.model.solver_family != "MILP":
            raise ValueError("HiGHS worker requires MILP-compatible model")
        import highspy
        start = time.monotonic()
        h = highspy.Highs()
        h.setOptionValue("output_flag", False)
        h.setOptionValue("time_limit", request.timeout_ms / 1000.0)
        variables: dict[str, Any] = {}
        try:
            for row in request.model.variables:
                var_type = highspy.HighsVarType.kInteger if row.domain in {"BOOL", "INTEGER"} else highspy.HighsVarType.kContinuous
                variables[row.variable_id] = h.addVariable(lb=float(row.lower_bound), ub=float(row.upper_bound), type=var_type, name=row.variable_id)
            for constraint in request.model.constraints:
                expr = sum(coeff * variables[vid] for vid, coeff in constraint.coefficients.items())
                h.addConstr(expr <= constraint.rhs if constraint.sense == "<=" else expr >= constraint.rhs if constraint.sense == ">=" else expr == constraint.rhs, name=constraint.constraint_id)
            if request.model.objective:
                expr = sum(coeff * variables[vid] for vid, coeff in request.model.objective.coefficients.items()) + float(request.model.objective.offset)
                h.minimize(expr) if request.model.objective.sense == "MINIMIZE" else h.maximize(expr)
            else:
                h.run()
            raw_name = h.modelStatusToString(h.getModelStatus())
            lower = raw_name.lower()
            if "optimal" in lower:
                status = "OPTIMAL" if request.model.objective else "SAT"
            elif "infeasible" in lower:
                status = "INFEASIBLE" if request.model.objective else "UNSAT"
            elif "time" in lower:
                status = "TIMEOUT"
            elif "feasible" in lower:
                status = "FEASIBLE" if request.model.objective else "SAT"
            else:
                status = "UNKNOWN"
            assignment = {vid: float(h.val(var)) for vid, var in variables.items()} if status in {"SAT", "OPTIMAL", "FEASIBLE"} else {}
            objective = objective_value(request.model, assignment) if assignment else None
            info = h.getInfo()
            stats = {"raw_status": raw_name, "simplex_iterations": int(getattr(info, "simplex_iteration_count", 0)), "mip_nodes": int(getattr(info, "mip_node_count", 0))}
            return OptimizationResult(request.request_id, request.fingerprint, request.model.fingerprint, status, OptimizationSolverIdentity(self.provider_id, "highspy", _package_version("highspy")), assignment=assignment, objective_value=objective, wall_time_ms=int((time.monotonic() - start) * 1000), statistics=stats)
        except Exception as exc:
            return OptimizationResult(request.request_id, request.fingerprint, request.model.fingerprint, "ERROR", OptimizationSolverIdentity(self.provider_id, "highspy", _package_version("highspy")), wall_time_ms=int((time.monotonic() - start) * 1000), diagnostics=(f"{type(exc).__name__}: {exc}",))


def solve_optimization_request(request: OptimizationRequest | Mapping[str, Any]) -> OptimizationResult:
    parsed = request if isinstance(request, OptimizationRequest) else OptimizationRequest.from_dict(request)
    provider = parsed.required_provider
    if provider == "cadical":
        return PySATCadicalWorker().run(parsed)
    if provider == "ortools-cp-sat":
        return ORToolsCPSATWorker().run(parsed)
    if provider == "highs":
        return HighsMILPWorker().run(parsed)
    raise ValueError(f"unsupported optimization provider: {provider or '<none>'}")


def reference_optimization_models() -> dict[str, OptimizationModel]:
    sat = OptimizationModel(
        "reference-sat",
        (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
        (
            OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x"), BooleanLiteral("y"))),
            OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x", False), BooleanLiteral("y"))),
        ),
        family="SAT",
    )
    cp = OptimizationModel(
        "reference-cp-sat",
        (OptimizationVariable("x", "INTEGER", 0, 5), OptimizationVariable("y", "INTEGER", 0, 5)),
        (
            OptimizationConstraint("ALL_DIFFERENT", variable_ids=("x", "y")),
            OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1}, sense="<=", rhs=6),
        ),
        OptimizationObjective("MAXIMIZE", {"x": 2, "y": 1}),
        family="CP_SAT",
    )
    milp = OptimizationModel(
        "reference-milp",
        (OptimizationVariable("x", "CONTINUOUS", 0, 10), OptimizationVariable("y", "INTEGER", 0, 10)),
        (
            OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 2}, sense="<=", rhs=8),
        ),
        OptimizationObjective("MAXIMIZE", {"x": 1, "y": 3}),
        family="MILP",
    )
    return {"SAT": sat, "CP_SAT": cp, "MILP": milp}


__all__ = [
    "OPTIMIZATION_CONTRACT_ID", "OPTIMIZATION_CONTRACT_VERSION", "OPTIMIZATION_FAMILIES",
    "OPTIMIZATION_STATUSES", "OPTIMIZATION_CAPABILITIES", "BooleanLiteral", "OptimizationVariable",
    "OptimizationConstraint", "OptimizationObjective", "OptimizationModel", "OptimizationRequest",
    "OptimizationSolverIdentity", "OptimizationResult", "optimization_contract", "optimization_blueprint",
    "default_optimization_capability_contracts", "default_optimization_providers", "infer_solver_family",
    "objective_value", "validate_optimization_solution", "validate_optimization_result",
    "optimization_result_satisfies_request", "PySATCadicalWorker", "ORToolsCPSATWorker", "HighsMILPWorker",
    "solve_optimization_request", "reference_optimization_models",
]
