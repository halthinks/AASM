from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationResult,
    OptimizationSolverIdentity,
    OptimizationVariable,
)
from aasm.proof_claims import certify_optimization_result


def result(model, assignment, objective):
    return OptimizationResult(
        "req", "req-fp", model.fingerprint, "OPTIMAL",
        OptimizationSolverIdentity("fixture-solver", "fixture", "1.0"),
        assignment, objective,
    )


def test_continuous_optimality_is_unsupported_not_failed():
    model = OptimizationModel(
        "continuous-proof-limit",
        (OptimizationVariable("x", "CONTINUOUS", 0, 1),),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1}, sense=">=", rhs=0),),
        OptimizationObjective("MINIMIZE", {"x": 1}),
        family="MILP",
    )
    report = certify_optimization_result(model, result(model, {"x": 0}, 0.0))
    assert report["status"] == "UNSUPPORTED"
    assert report["verification_level"] == "SOLVER_VALIDATED"
    assert report["certificate"] is None


def test_proof_budget_exhaustion_is_unsupported_not_failed():
    variables = tuple(OptimizationVariable(f"x{i}", "BOOL") for i in range(10))
    coefficients = {f"x{i}": 1 for i in range(10)}
    model = OptimizationModel(
        "proof-budget-limit",
        variables,
        (OptimizationConstraint("LINEAR", coefficients=coefficients, sense=">=", rhs=0),),
        OptimizationObjective("MINIMIZE", coefficients),
        family="CP_SAT",
    )
    assignment = {f"x{i}": 0 for i in range(10)}
    report = certify_optimization_result(model, result(model, assignment, 0.0), max_states=100)
    assert report["status"] == "UNSUPPORTED"
    assert "budget exceeded" in report["reason"]
    assert report["certificate"] is None
