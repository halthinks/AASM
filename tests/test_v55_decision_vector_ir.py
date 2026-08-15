from __future__ import annotations

import pytest

from aasm.decision_vector_ir import (
    DecisionHardFloor,
    DecisionObjective,
    GovernedDecisionVector,
    compile_linear_decision_vector,
    decision_vector_contract,
    evaluate_hard_floors,
)
from aasm.multi_objective import solve_lexicographic_finite
from aasm.optimization import OptimizationModel, OptimizationVariable


def _base_model() -> OptimizationModel:
    return OptimizationModel(
        "governed choices",
        (
            OptimizationVariable("quality", "BOOL"),
            OptimizationVariable("cheap", "BOOL"),
        ),
        (),
        family="CP_SAT",
    )


def test_decision_vector_contract_forbids_scalarizing_hard_floors():
    contract = decision_vector_contract()
    assert contract["hard_floors"] == "SEPARATE_CONSTRAINT_CLASS_NEVER_WEIGHTED_OR_TRADED"
    assert contract["resource_objectives"] == "PREFERENCES_ONLY_AFTER_ALL_HARD_FLOORS_PASS"
    assert contract["scalarization"] == "NONE"
    assert contract["resource_policy_can_weaken_hard_semantics"] is False
    assert contract["truth_authority"] == "NONE"


def test_linear_hard_floor_filters_cheaper_invalid_candidate_before_lexicographic_optimization():
    vector = GovernedDecisionVector(
        _base_model(),
        (
            DecisionHardFloor(
                "floor-quality",
                "quality-threshold",
                ">=",
                1,
                coefficients={"quality": 1},
                source_reference_fingerprints=("req-quality",),
            ),
        ),
        (
            DecisionObjective(
                "objective-cost",
                "cost",
                0,
                "MINIMIZE",
                category="RESOURCE",
                coefficients={"quality": 10, "cheap": -5},
                source_reference_fingerprints=("policy-cost",),
            ),
            DecisionObjective(
                "objective-complexity",
                "complexity",
                1,
                "MINIMIZE",
                category="ENGINEERING",
                coefficients={"cheap": 1},
            ),
        ),
    )
    failed = evaluate_hard_floors(vector, {"quality": 0, "cheap": 1})
    assert failed["passes"] is False
    assert failed["resource_policy_can_override"] is False

    problem, compilation = compile_linear_decision_vector(vector)
    assert problem is not None
    assert compilation.status == "PASS"
    result = solve_lexicographic_finite(problem)
    selected = result["result"].selected.assignment
    assert selected["quality"] == 1.0
    assert selected["cheap"] == 1.0
    assert compilation.floor_constraint_map["floor-quality"] == "hard-floor::floor-quality"


def test_higher_priority_engineering_objective_cannot_be_traded_for_lower_priority_resource_savings():
    model = OptimizationModel(
        "priority fixture",
        (OptimizationVariable("safe", "BOOL"), OptimizationVariable("cheap", "BOOL")),
        (),
        family="CP_SAT",
    )
    vector = GovernedDecisionVector(
        model,
        (DecisionHardFloor("floor-any", "admissible", ">=", 0, coefficients={"safe": 1}),),
        (
            DecisionObjective("maximize-safety", "safety", 0, "MAXIMIZE", category="ENGINEERING", coefficients={"safe": 1}),
            DecisionObjective("minimize-cost", "cost", 1, "MINIMIZE", category="RESOURCE", coefficients={"safe": 100, "cheap": -1}),
        ),
    )
    problem, _ = compile_linear_decision_vector(vector)
    result = solve_lexicographic_finite(problem)["result"]
    assert result.selected.assignment["safe"] == 1.0
    assert result.stages[0].objective_id == "maximize-safety"
    assert result.stages[1].objective_id == "minimize-cost"


def test_named_metrics_are_representable_but_not_silently_compiled():
    vector = GovernedDecisionVector(
        _base_model(),
        (DecisionHardFloor("floor-quality", "external-drc-pass", ">=", 1, metric_kind="NAMED_EVALUATION"),),
        (DecisionObjective("resource-cost", "cost", 0, "MINIMIZE", category="RESOURCE", coefficients={"cheap": -1}),),
    )
    assert evaluate_hard_floors(vector, {"quality": 0, "cheap": 1}, named_metrics={"external-drc-pass": 1})["passes"] is True
    problem, compilation = compile_linear_decision_vector(vector)
    assert problem is None
    assert compilation.status == "INCONCLUSIVE"
    assert any("NAMED_METRIC" in row for row in compilation.diagnostics)


def test_duplicate_objective_priority_is_rejected_for_determinism():
    with pytest.raises(ValueError, match="priorities"):
        GovernedDecisionVector(
            _base_model(),
            (DecisionHardFloor("floor", "floor", ">=", 0, coefficients={"quality": 1}),),
            (
                DecisionObjective("a", "a", 0, "MINIMIZE", coefficients={"quality": 1}),
                DecisionObjective("b", "b", 0, "MINIMIZE", coefficients={"cheap": 1}),
            ),
        )


def test_hard_floor_equality_tolerance_refuses_unsafe_single_constraint_compilation():
    vector = GovernedDecisionVector(
        _base_model(),
        (DecisionHardFloor("eq-floor", "eq", "==", 1, coefficients={"quality": 1}, tolerance=0.1),),
        (DecisionObjective("cost", "cost", 0, "MINIMIZE", coefficients={"cheap": 1}),),
    )
    problem, compilation = compile_linear_decision_vector(vector)
    assert problem is None
    assert compilation.status == "INCONCLUSIVE"
    assert "EQUALITY_HARD_FLOOR_WITH_TOLERANCE_REQUIRES_TWO_CONSTRAINTS:eq-floor" in compilation.diagnostics
