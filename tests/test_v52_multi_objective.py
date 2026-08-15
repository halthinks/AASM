from aasm.multi_objective import (
    MultiObjectiveProblem,
    ObjectivePoint,
    OrderedObjective,
    ParetoFrontier,
    solve_exact_finite_pareto_frontier,
    solve_lexicographic_finite,
    verify_exact_finite_pareto_frontier,
)
from aasm.optimization import OptimizationConstraint, OptimizationModel, OptimizationVariable


def reference_problem(*, x_priority=0, y_priority=1, x_tolerance=0.0):
    model = OptimizationModel(
        "v52-two-objective",
        (
            OptimizationVariable("x", "BOOL"),
            OptimizationVariable("y", "BOOL"),
        ),
        (
            OptimizationConstraint(
                "LINEAR",
                coefficients={"x": 1, "y": 1},
                sense=">=",
                rhs=1,
            ),
        ),
        family="CP_SAT",
    )
    return MultiObjectiveProblem(
        model,
        (
            OrderedObjective("min_x", x_priority, "MINIMIZE", {"x": 1}, tolerance=x_tolerance),
            OrderedObjective("min_y", y_priority, "MINIMIZE", {"y": 1}),
        ),
    )


def assignment_tuple(point):
    return (int(point.assignment["x"]), int(point.assignment["y"]))


def test_exact_lexicographic_solving_preserves_priority_and_is_independently_verified():
    solved = solve_lexicographic_finite(reference_problem())
    result = solved["result"]
    assert result.verification_status == "PASS"
    assert solved["enumeration_certificate"].status == "PASS"
    assert assignment_tuple(result.selected) == (0, 1)
    assert [stage.objective_id for stage in result.stages] == ["min_x", "min_y"]
    assert [stage.optimum for stage in result.stages] == [0.0, 1.0]
    assert solved["verification"]["status"] == "PASS"


def test_priority_inversion_changes_lexicographic_answer_deterministically():
    solved = solve_lexicographic_finite(reference_problem(x_priority=1, y_priority=0))
    assert assignment_tuple(solved["result"].selected) == (1, 0)
    assert [stage.objective_id for stage in solved["result"].stages] == ["min_y", "min_x"]


def test_declared_tolerance_is_the_only_allowed_higher_priority_degradation():
    solved = solve_lexicographic_finite(reference_problem(x_tolerance=1.0))
    result = solved["result"]
    assert result.verification_status == "PASS"
    assert assignment_tuple(result.selected) == (1, 0)
    assert result.stages[0].optimum == 0.0
    assert result.selected.values["min_x"] <= result.stages[0].optimum + result.stages[0].tolerance


def test_exact_finite_pareto_frontier_is_complete_and_contains_only_nondominated_points():
    solved = solve_exact_finite_pareto_frontier(reference_problem())
    frontier = solved["frontier"]
    assert frontier.completeness_status == "COMPLETE"
    assert frontier.certificate is not None
    assert frontier.certificate.status == "PASS"
    assert frontier.certificate.pairwise_nondominant is True
    assert frontier.certificate.exact_solution_set_match is True
    assert {assignment_tuple(point) for point in frontier.points} == {(0, 1), (1, 0)}
    assert frontier.certificate.feasible_count == 3
    assert frontier.certificate.frontier_count == 2
    assert frontier.certificate.dominated_count == 1


def test_dominated_frontier_member_fails_independent_certificate():
    problem = reference_problem()
    solved = solve_exact_finite_pareto_frontier(problem)
    dominated_solution = next(row for row in solved["pool"].solutions if (int(row.assignment["x"]), int(row.assignment["y"])) == (1, 1))
    dominated = ObjectivePoint(
        dominated_solution.solution_id,
        dominated_solution.assignment,
        {objective.objective_id: objective.value(dominated_solution.assignment) for objective in problem.objectives},
    )
    forged = ParetoFrontier(problem.fingerprint, "EXACT_FINITE_PARETO_FRONTIER", tuple(solved["frontier"].points) + (dominated,), "EXHAUSTED_PENDING_CERTIFICATION")
    certificate = verify_exact_finite_pareto_frontier(problem, forged, solved["enumeration_certificate"])
    assert certificate.status == "FAIL"
    assert certificate.pairwise_nondominant is False


def test_missing_frontier_member_fails_exactness_certificate():
    problem = reference_problem()
    solved = solve_exact_finite_pareto_frontier(problem)
    forged = ParetoFrontier(problem.fingerprint, "EXACT_FINITE_PARETO_FRONTIER", (solved["frontier"].points[0],), "EXHAUSTED_PENDING_CERTIFICATION")
    certificate = verify_exact_finite_pareto_frontier(problem, forged, solved["enumeration_certificate"])
    assert certificate.status == "FAIL"
    assert certificate.exact_solution_set_match is False


def test_reusing_valid_solution_ids_with_falsified_point_content_fails_exactness():
    problem = reference_problem()
    solved = solve_exact_finite_pareto_frontier(problem)
    first, second = solved["frontier"].points
    forged_first = ObjectivePoint(
        first.solution_id,
        {"x": 1.0, "y": 1.0},
        dict(first.values),
    )
    forged = ParetoFrontier(problem.fingerprint, "EXACT_FINITE_PARETO_FRONTIER", (forged_first, second), "EXHAUSTED_PENDING_CERTIFICATION")
    certificate = verify_exact_finite_pareto_frontier(problem, forged, solved["enumeration_certificate"])
    assert certificate.status == "FAIL"
    assert certificate.exact_solution_set_match is False
