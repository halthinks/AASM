from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .optimization import OptimizationModel
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


MULTI_OBJECTIVE_CONTRACT_ID = "aasm.optimization.multi-objective.v1"
MULTI_OBJECTIVE_CONTRACT_VERSION = "0.1.0"
FRONTIER_CONTRACT_ID = "aasm.optimization.frontier.v1"
FRONTIER_CONTRACT_VERSION = "0.1.0"
MULTI_OBJECTIVE_STABILITY = "FOUNDATION_EXPERIMENTAL"
FRONTIER_MODES = (
    "EXACT_FINITE_PARETO_FRONTIER",
    "BOUNDED_PARTIAL_FRONTIER",
    "EPSILON_APPROXIMATE_FRONTIER",
)


@dataclass(frozen=True)
class OrderedObjective:
    objective_id: str
    priority: int
    sense: str
    coefficients: Mapping[str, float]
    offset: float = 0.0
    tolerance: float = 0.0

    def __post_init__(self) -> None:
        if not self.objective_id.strip():
            raise ValueError("objective_id is required")
        if int(self.priority) < 0:
            raise ValueError("objective priority must be non-negative")
        if self.sense not in {"MINIMIZE", "MAXIMIZE"}:
            raise ValueError("objective sense must be MINIMIZE or MAXIMIZE")
        coefficients = {str(key): float(value) for key, value in sorted(self.coefficients.items()) if float(value) != 0.0}
        if not coefficients:
            raise ValueError("objective requires at least one non-zero coefficient")
        if float(self.tolerance) < 0:
            raise ValueError("objective tolerance must be non-negative")
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "priority", int(self.priority))
        object.__setattr__(self, "offset", float(self.offset))
        object.__setattr__(self, "tolerance", float(self.tolerance))

    def value(self, assignment: Mapping[str, float]) -> float:
        return float(self.offset) + sum(float(coefficient) * float(assignment[variable_id]) for variable_id, coefficient in self.coefficients.items())

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "priority": self.priority,
            "sense": self.sense,
            "coefficients": dict(self.coefficients),
            "offset": self.offset,
            "tolerance": self.tolerance,
        }


@dataclass(frozen=True)
class MultiObjectiveProblem:
    model: OptimizationModel | Mapping[str, Any]
    objectives: tuple[OrderedObjective | Mapping[str, Any], ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    problem_id: str = ""

    def __post_init__(self) -> None:
        model = self.model if isinstance(self.model, OptimizationModel) else OptimizationModel.from_dict(self.model)
        objectives = tuple(row if isinstance(row, OrderedObjective) else OrderedObjective(**dict(row)) for row in self.objectives)
        if not objectives:
            raise ValueError("multi-objective problem requires objectives")
        priorities = [row.priority for row in objectives]
        if len(priorities) != len(set(priorities)):
            raise ValueError("objective priorities must be unique for deterministic lexicographic ordering")
        ids = [row.objective_id for row in objectives]
        if len(ids) != len(set(ids)):
            raise ValueError("objective IDs must be unique")
        known = {row.variable_id for row in model.variables}
        for objective in objectives:
            missing = sorted(set(objective.coefficients) - known)
            if missing:
                raise ValueError(f"objective references unknown variables: {missing}")
        object.__setattr__(self, "model", model)
        object.__setattr__(self, "objectives", tuple(sorted(objectives, key=lambda row: (row.priority, row.objective_id))))
        identity = {
            "model_fingerprint": model.fingerprint,
            "objectives": [row.to_dict() for row in sorted(objectives, key=lambda row: (row.priority, row.objective_id))],
            "metadata": dict(self.metadata),
        }
        object.__setattr__(self, "problem_id", self.problem_id or f"multi-objective-{semantic_fingerprint(identity)[:24]}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "problem_id": self.problem_id,
            "model": self.model.to_dict(),
            "objectives": [row.to_dict() for row in self.objectives],
            "metadata": dict(self.metadata),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


@dataclass(frozen=True)
class ObjectivePoint:
    solution_id: str
    assignment: Mapping[str, float]
    values: Mapping[str, float]

    def __post_init__(self) -> None:
        object.__setattr__(self, "assignment", {str(key): float(value) for key, value in sorted(self.assignment.items())})
        object.__setattr__(self, "values", {str(key): float(value) for key, value in sorted(self.values.items())})

    def to_dict(self) -> dict[str, Any]:
        return {"solution_id": self.solution_id, "assignment": dict(self.assignment), "values": dict(self.values)}


@dataclass(frozen=True)
class LexicographicStage:
    objective_id: str
    priority: int
    sense: str
    tolerance: float
    optimum: float
    candidates_before: int
    candidates_after: int
    surviving_solution_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "priority": self.priority,
            "sense": self.sense,
            "tolerance": self.tolerance,
            "optimum": self.optimum,
            "candidates_before": self.candidates_before,
            "candidates_after": self.candidates_after,
            "surviving_solution_ids": list(self.surviving_solution_ids),
        }


@dataclass(frozen=True)
class LexicographicResult:
    problem_fingerprint: str
    selected: ObjectivePoint
    stages: tuple[LexicographicStage, ...]
    enumeration_certificate_id: str
    verification_status: str
    result_id: str = ""

    def __post_init__(self) -> None:
        if self.verification_status not in {"PASS", "FAIL"}:
            raise ValueError("verification_status must be PASS or FAIL")
        identity = self.to_dict(include_fingerprint=False, include_id=False)
        object.__setattr__(self, "result_id", self.result_id or f"lexicographic-result-{semantic_fingerprint(identity)[:24]}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True, include_id: bool = True) -> dict[str, Any]:
        out = {
            "problem_fingerprint": self.problem_fingerprint,
            "selected": self.selected.to_dict(),
            "stages": [row.to_dict() for row in self.stages],
            "enumeration_certificate_id": self.enumeration_certificate_id,
            "verification_status": self.verification_status,
        }
        if include_id:
            out["result_id"] = self.result_id
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


@dataclass(frozen=True)
class ParetoFrontierCertificate:
    problem_fingerprint: str
    frontier_fingerprint: str
    enumeration_certificate_id: str
    feasible_count: int
    frontier_count: int
    dominated_count: int
    pairwise_nondominant: bool
    exact_solution_set_match: bool
    status: str
    diagnostics: tuple[str, ...] = ()
    certificate_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in {"PASS", "FAIL"}:
            raise ValueError("frontier certificate status must be PASS or FAIL")
        identity = self.to_dict(include_fingerprint=False, include_id=False)
        object.__setattr__(self, "certificate_id", self.certificate_id or f"pareto-certificate-{semantic_fingerprint(identity)[:24]}")

    def to_dict(self, *, include_fingerprint: bool = True, include_id: bool = True) -> dict[str, Any]:
        out = {
            "problem_fingerprint": self.problem_fingerprint,
            "frontier_fingerprint": self.frontier_fingerprint,
            "enumeration_certificate_id": self.enumeration_certificate_id,
            "feasible_count": self.feasible_count,
            "frontier_count": self.frontier_count,
            "dominated_count": self.dominated_count,
            "pairwise_nondominant": self.pairwise_nondominant,
            "exact_solution_set_match": self.exact_solution_set_match,
            "status": self.status,
            "diagnostics": list(self.diagnostics),
        }
        if include_id:
            out["certificate_id"] = self.certificate_id
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


@dataclass(frozen=True)
class ParetoFrontier:
    problem_fingerprint: str
    mode: str
    points: tuple[ObjectivePoint, ...]
    completeness_status: str
    certificate: ParetoFrontierCertificate | None = None
    frontier_id: str = ""

    def __post_init__(self) -> None:
        if self.mode not in FRONTIER_MODES:
            raise ValueError(f"unsupported frontier mode: {self.mode}")
        points = tuple(sorted(self.points, key=lambda row: row.solution_id))
        if len({row.solution_id for row in points}) != len(points):
            raise ValueError("Pareto frontier cannot contain duplicate solutions")
        if self.completeness_status == "COMPLETE" and (self.certificate is None or self.certificate.status != "PASS"):
            raise ValueError("COMPLETE Pareto frontier requires a passing certificate")
        object.__setattr__(self, "points", points)
        identity = {
            "problem_fingerprint": self.problem_fingerprint,
            "mode": self.mode,
            "points": [row.to_dict() for row in points],
            "completeness_status": self.completeness_status,
        }
        object.__setattr__(self, "frontier_id", self.frontier_id or f"pareto-frontier-{semantic_fingerprint(identity)[:24]}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "frontier_id": self.frontier_id,
            "problem_fingerprint": self.problem_fingerprint,
            "mode": self.mode,
            "points": [row.to_dict() for row in self.points],
            "solution_ids": [row.solution_id for row in self.points],
            "completeness_status": self.completeness_status,
            "certificate": self.certificate.to_dict() if self.certificate else None,
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


def multi_objective_contract() -> dict[str, Any]:
    return {
        "contract_id": MULTI_OBJECTIVE_CONTRACT_ID,
        "contract_version": MULTI_OBJECTIVE_CONTRACT_VERSION,
        "stability": MULTI_OBJECTIVE_STABILITY,
        "lexicographic_order": "EXPLICIT_UNIQUE_PRIORITY",
        "higher_priority_degradation": "FORBIDDEN_OUTSIDE_DECLARED_TOLERANCE",
        "exact_finite_basis": "V0.51_COMPLETE_FINITE_ENUMERATION_CERTIFICATE_REQUIRED",
        "result_authority": "EVIDENCE_ONLY",
        "truth_authority": "EXISTING_AASM_POLICY_ONLY",
    }


def frontier_contract() -> dict[str, Any]:
    return {
        "contract_id": FRONTIER_CONTRACT_ID,
        "contract_version": FRONTIER_CONTRACT_VERSION,
        "stability": MULTI_OBJECTIVE_STABILITY,
        "modes": list(FRONTIER_MODES),
        "exact_mode": "EXACT_FINITE_PARETO_FRONTIER",
        "complete_requires": "V0.51_ENUMERATION_EXHAUSTION_PLUS_INDEPENDENT_FRONTIER_RECHECK",
        "dominated_point_admission": "REJECTED",
        "false_exactness": "FAIL_CLOSED",
        "result_authority": "EVIDENCE_ONLY",
        "truth_authority": "EXISTING_AASM_POLICY_ONLY",
    }


def _complete_pool(problem: MultiObjectiveProblem, *, max_total_states: int = 100_000, max_states_per_step: int = 1_000) -> tuple[SolutionPool, EnumerationCursor, EnumerationCompletenessCertificate]:
    pool = SolutionPool(problem.model.fingerprint, "COMPLETE_FINITE_ENUMERATION", lineage={"multi_objective_problem_fingerprint": problem.fingerprint})
    cursor = initial_enumeration_cursor(problem.model, pool.pool_id, pool.mode, max_total_states=max_total_states)
    solutions: list[SolutionRecord] = []
    exclusion_ids: set[str] = set()
    while not cursor.exhausted:
        step = enumerate_finite_step(
            problem.model,
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
        problem.model.fingerprint,
        pool.mode,
        tuple(solutions),
        tuple(sorted(exclusion_ids)),
        "EXHAUSTED_PENDING_CERTIFICATION",
        cursor.fingerprint,
        lineage=pool.lineage,
        pool_id=pool.pool_id,
    )
    certificate = certify_complete_finite_enumeration(problem.model, pending, cursor=cursor, max_total_states=max_total_states)
    if certificate.status != "PASS":
        raise ValueError(f"finite enumeration completeness failed: {certificate.diagnostics}")
    complete = SolutionPool(
        problem.model.fingerprint,
        pool.mode,
        tuple(solutions),
        tuple(sorted(exclusion_ids)),
        "COMPLETE",
        cursor.fingerprint,
        certificate.certificate_id,
        pool.lineage,
        pool.pool_id,
    )
    return complete, cursor, certificate


def _point(problem: MultiObjectiveProblem, solution: SolutionRecord) -> ObjectivePoint:
    return ObjectivePoint(
        solution.solution_id,
        solution.assignment,
        {objective.objective_id: objective.value(solution.assignment) for objective in problem.objectives},
    )


def _best_value(objective: OrderedObjective, points: Sequence[ObjectivePoint]) -> float:
    values = [row.values[objective.objective_id] for row in points]
    return min(values) if objective.sense == "MINIMIZE" else max(values)


def _within_optimum(objective: OrderedObjective, value: float, optimum: float) -> bool:
    if objective.sense == "MINIMIZE":
        return value <= optimum + objective.tolerance
    return value >= optimum - objective.tolerance


def solve_lexicographic_finite(problem: MultiObjectiveProblem, *, max_total_states: int = 100_000, max_states_per_step: int = 1_000) -> dict[str, Any]:
    pool, cursor, enumeration_certificate = _complete_pool(problem, max_total_states=max_total_states, max_states_per_step=max_states_per_step)
    if not pool.solutions:
        raise ValueError("multi-objective model has no feasible solutions")
    survivors = [_point(problem, row) for row in pool.solutions]
    stages: list[LexicographicStage] = []
    for objective in problem.objectives:
        before = len(survivors)
        optimum = _best_value(objective, survivors)
        survivors = [row for row in survivors if _within_optimum(objective, row.values[objective.objective_id], optimum)]
        stages.append(LexicographicStage(
            objective.objective_id,
            objective.priority,
            objective.sense,
            objective.tolerance,
            optimum,
            before,
            len(survivors),
            tuple(sorted(row.solution_id for row in survivors)),
        ))
    selected = min(survivors, key=lambda row: row.solution_id)
    provisional = LexicographicResult(problem.fingerprint, selected, tuple(stages), enumeration_certificate.certificate_id, "PASS")
    verification = verify_lexicographic_result(problem, provisional, max_total_states=max_total_states, max_states_per_step=max_states_per_step)
    result = LexicographicResult(problem.fingerprint, selected, tuple(stages), enumeration_certificate.certificate_id, verification["status"])
    return {
        "result": result,
        "pool": pool,
        "cursor": cursor,
        "enumeration_certificate": enumeration_certificate,
        "verification": verification,
    }


def verify_lexicographic_result(problem: MultiObjectiveProblem, result: LexicographicResult, *, max_total_states: int = 100_000, max_states_per_step: int = 1_000) -> dict[str, Any]:
    pool, _, certificate = _complete_pool(problem, max_total_states=max_total_states, max_states_per_step=max_states_per_step)
    points = [_point(problem, row) for row in pool.solutions]
    diagnostics: list[str] = []
    survivors = points
    expected_stages: list[LexicographicStage] = []
    for objective in problem.objectives:
        before = len(survivors)
        optimum = _best_value(objective, survivors)
        survivors = [row for row in survivors if _within_optimum(objective, row.values[objective.objective_id], optimum)]
        expected_stages.append(LexicographicStage(objective.objective_id, objective.priority, objective.sense, objective.tolerance, optimum, before, len(survivors), tuple(sorted(row.solution_id for row in survivors))))
    expected_selected = min(survivors, key=lambda row: row.solution_id)
    if result.problem_fingerprint != problem.fingerprint:
        diagnostics.append("problem fingerprint mismatch")
    if result.selected.to_dict() != expected_selected.to_dict():
        diagnostics.append("selected lexicographic solution is not exact")
    if [row.to_dict() for row in result.stages] != [row.to_dict() for row in expected_stages]:
        diagnostics.append("lexicographic stage optimum/survivor trace mismatch")
    return {
        "status": "PASS" if not diagnostics and certificate.status == "PASS" else "FAIL",
        "diagnostics": diagnostics,
        "independent_enumeration_certificate_id": certificate.certificate_id,
        "selected_solution_id": expected_selected.solution_id,
        "stage_optima": {row.objective_id: row.optimum for row in expected_stages},
    }


def _no_worse(objective: OrderedObjective, left: float, right: float) -> bool:
    if objective.sense == "MINIMIZE":
        return left <= right + objective.tolerance
    return left >= right - objective.tolerance


def _strictly_better(objective: OrderedObjective, left: float, right: float) -> bool:
    if objective.sense == "MINIMIZE":
        return left < right - objective.tolerance
    return left > right + objective.tolerance


def dominates(problem: MultiObjectiveProblem, left: ObjectivePoint, right: ObjectivePoint) -> bool:
    return all(_no_worse(objective, left.values[objective.objective_id], right.values[objective.objective_id]) for objective in problem.objectives) and any(
        _strictly_better(objective, left.values[objective.objective_id], right.values[objective.objective_id]) for objective in problem.objectives
    )


def _nondominated(problem: MultiObjectiveProblem, points: Sequence[ObjectivePoint]) -> tuple[ObjectivePoint, ...]:
    return tuple(sorted(
        (candidate for candidate in points if not any(other.solution_id != candidate.solution_id and dominates(problem, other, candidate) for other in points)),
        key=lambda row: row.solution_id,
    ))


def solve_exact_finite_pareto_frontier(problem: MultiObjectiveProblem, *, max_total_states: int = 100_000, max_states_per_step: int = 1_000) -> dict[str, Any]:
    pool, cursor, enumeration_certificate = _complete_pool(problem, max_total_states=max_total_states, max_states_per_step=max_states_per_step)
    points = [_point(problem, row) for row in pool.solutions]
    frontier_points = _nondominated(problem, points)
    provisional = ParetoFrontier(problem.fingerprint, "EXACT_FINITE_PARETO_FRONTIER", frontier_points, "EXHAUSTED_PENDING_CERTIFICATION")
    certificate = verify_exact_finite_pareto_frontier(problem, provisional, enumeration_certificate, max_total_states=max_total_states, max_states_per_step=max_states_per_step)
    frontier = ParetoFrontier(problem.fingerprint, "EXACT_FINITE_PARETO_FRONTIER", frontier_points, "COMPLETE" if certificate.status == "PASS" else "FAILED_COMPLETENESS", certificate)
    return {
        "frontier": frontier,
        "pool": pool,
        "cursor": cursor,
        "enumeration_certificate": enumeration_certificate,
        "certificate": certificate,
    }


def verify_exact_finite_pareto_frontier(problem: MultiObjectiveProblem, frontier: ParetoFrontier, enumeration_certificate: EnumerationCompletenessCertificate, *, max_total_states: int = 100_000, max_states_per_step: int = 1_000) -> ParetoFrontierCertificate:
    pool, _, independent_certificate = _complete_pool(problem, max_total_states=max_total_states, max_states_per_step=max_states_per_step)
    all_points = [_point(problem, row) for row in pool.solutions]
    expected = _nondominated(problem, all_points)
    expected_ids = {row.solution_id for row in expected}
    actual_ids = {row.solution_id for row in frontier.points}
    pairwise_nondominant = all(not dominates(problem, left, right) and not dominates(problem, right, left) for index, left in enumerate(frontier.points) for right in frontier.points[index + 1:])
    diagnostics: list[str] = []
    if frontier.mode != "EXACT_FINITE_PARETO_FRONTIER":
        diagnostics.append("frontier mode is not exact finite")
    if enumeration_certificate.status != "PASS" or independent_certificate.status != "PASS":
        diagnostics.append("finite feasible-space exhaustion is not certified")
    if not pairwise_nondominant:
        diagnostics.append("frontier contains a dominated pair")
    if actual_ids != expected_ids:
        diagnostics.append("frontier solution set does not equal independently reconstructed nondominated set")
    frontier_fingerprint = semantic_fingerprint({"problem_fingerprint": problem.fingerprint, "solution_ids": sorted(actual_ids), "points": [row.to_dict() for row in sorted(frontier.points, key=lambda row: row.solution_id)]})
    return ParetoFrontierCertificate(
        problem.fingerprint,
        frontier_fingerprint,
        enumeration_certificate.certificate_id,
        len(all_points),
        len(frontier.points),
        len(all_points) - len(expected),
        pairwise_nondominant,
        actual_ids == expected_ids,
        "PASS" if not diagnostics else "FAIL",
        tuple(diagnostics),
    )


__all__ = [
    "MULTI_OBJECTIVE_CONTRACT_ID",
    "MULTI_OBJECTIVE_CONTRACT_VERSION",
    "FRONTIER_CONTRACT_ID",
    "FRONTIER_CONTRACT_VERSION",
    "MULTI_OBJECTIVE_STABILITY",
    "FRONTIER_MODES",
    "OrderedObjective",
    "MultiObjectiveProblem",
    "ObjectivePoint",
    "LexicographicStage",
    "LexicographicResult",
    "ParetoFrontierCertificate",
    "ParetoFrontier",
    "multi_objective_contract",
    "frontier_contract",
    "solve_lexicographic_finite",
    "verify_lexicographic_result",
    "dominates",
    "solve_exact_finite_pareto_frontier",
    "verify_exact_finite_pareto_frontier",
]
