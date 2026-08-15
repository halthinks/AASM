from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationVariable,
)
from aasm.solver_learning import (
    SolverLearningArtifact,
    revalidate_finite_solver_learning,
    solver_learning_contract,
    validate_native_accelerator_hint,
)


def model():
    return OptimizationModel(
        "solver-learning-fixture",
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
        objective=OptimizationObjective("MINIMIZE", {"x": 1, "y": 1}),
        family="CP_SAT",
    )


def artifact(kind, payload, **kwargs):
    fixture = model()
    return SolverLearningArtifact(
        kind,
        fixture.fingerprint,
        fixture.solver_family,
        payload,
        source_result_fingerprint="result-fixture",
        source_evidence_ids=("evidence-b", "evidence-a"),
        **kwargs,
    )


def test_contract_separates_pruning_knowledge_from_performance_hints():
    contract = solver_learning_contract()
    assert contract["contract_id"] == "aasm.solver.learning.v1"
    assert contract["cross_run_transport"] == "EXISTING_AASM_V48_REUSE_RESULT_ENVELOPE"
    assert contract["cross_run_authority_transfer"] == "NEVER"
    assert contract["cross_run_admission_implies_truth"] is False
    assert contract["pruning_application"] == "LOCAL_REVALIDATION_REQUIRED"
    assert contract["performance_hint_authority"] == "NEVER_TRUTH_OR_POLICY"


def test_learning_artifact_is_canonical_and_round_trips_exactly():
    first = artifact(
        "NO_GOOD",
        {"literals": [{"variable_id": "y", "positive": False}, {"variable_id": "x", "positive": False}]},
    )
    second = artifact(
        "NO_GOOD",
        {"literals": [{"variable_id": "x", "positive": False}, {"variable_id": "y", "positive": False}]},
    )
    assert first.fingerprint == second.fingerprint
    assert first.source_evidence_ids == ("evidence-a", "evidence-b")
    assert SolverLearningArtifact.from_dict(first.to_dict()).to_dict() == first.to_dict()


def test_exact_finite_no_good_revalidation_accepts_only_truly_infeasible_conjunction():
    fixture = model()
    valid = artifact(
        "NO_GOOD",
        {"literals": [{"variable_id": "x", "positive": False}, {"variable_id": "y", "positive": False}]},
    )
    result = revalidate_finite_solver_learning(valid, fixture)
    assert result.status == "PASS"
    assert result.application_authority == "PRUNING_CERTIFIED_FOR_EXACT_MODEL"
    assert result.enumeration_certificate_id

    forged = artifact(
        "NO_GOOD",
        {"literals": [{"variable_id": "x", "positive": True}, {"variable_id": "y", "positive": False}]},
    )
    failed = revalidate_finite_solver_learning(forged, fixture)
    assert failed.status == "FAIL"
    assert failed.application_authority == "NONE"
    assert "LEARNED_PRUNING_WOULD_EXCLUDE_FEASIBLE_SOLUTIONS" in failed.diagnostics
    assert failed.details["violating_solution_ids"]


def test_unsat_core_uses_same_complete_finite_revalidation_boundary():
    fixture = model()
    core = artifact(
        "UNSAT_CORE",
        {"literals": [{"variable_id": "x", "positive": False}, {"variable_id": "y", "positive": False}]},
    )
    checked = revalidate_finite_solver_learning(core, fixture)
    assert checked.status == "PASS"
    assert checked.application_authority == "PRUNING_CERTIFIED_FOR_EXACT_MODEL"


def test_exact_finite_bound_revalidation_rejects_false_bound():
    fixture = model()
    lower = artifact("BOUND", {"bound_type": "LOWER", "value": 1.0})
    assert revalidate_finite_solver_learning(lower, fixture).status == "PASS"

    false_lower = artifact("BOUND", {"bound_type": "LOWER", "value": 1.5})
    failed = revalidate_finite_solver_learning(false_lower, fixture)
    assert failed.status == "FAIL"
    assert "LEARNED_BOUND_FALSE_FOR_EXACT_MODEL" in failed.diagnostics
    assert failed.details["minimum"] == 1.0
    assert failed.details["maximum"] == 2.0

    upper = artifact("BOUND", {"bound_type": "UPPER", "value": 2.0})
    assert revalidate_finite_solver_learning(upper, fixture).status == "PASS"


def test_incumbent_and_warm_start_are_validated_as_performance_hints_only():
    fixture = model()
    incumbent = artifact("INCUMBENT", {"assignment": {"x": 1, "y": 0}, "objective": 1})
    checked = revalidate_finite_solver_learning(incumbent, fixture)
    assert checked.status == "PASS"
    assert checked.application_authority == "PERFORMANCE_HINT_ONLY"
    assert checked.details["truth_authority"] == "NONE"

    invalid = artifact("WARM_START", {"assignment": {"x": 0, "y": 0}})
    failed = revalidate_finite_solver_learning(invalid, fixture)
    assert failed.status == "FAIL"
    assert failed.application_authority == "NONE"


def test_model_fingerprint_mismatch_fails_before_any_learning_use():
    learned = artifact("BOUND", {"bound_type": "LOWER", "value": 1})
    other = OptimizationModel(
        "other",
        (OptimizationVariable("x", "BOOL"),),
        (),
        objective=OptimizationObjective("MINIMIZE", {"x": 1}),
        family="CP_SAT",
    )
    result = revalidate_finite_solver_learning(learned, other)
    assert result.status == "FAIL"
    assert result.diagnostics == ("MODEL_FINGERPRINT_MISMATCH",)


def test_native_accelerator_requires_exact_backend_version_and_environment_and_stays_performance_only():
    fixture = model()
    native = SolverLearningArtifact(
        "NATIVE_ACCELERATOR",
        fixture.fingerprint,
        fixture.solver_family,
        {
            "backend_id": "ortools-cp-sat",
            "backend_version": "fixture-1",
            "state_fingerprint": "state-abc",
        },
        provider_id="ortools-cp-sat",
        provider_version="fixture-1",
        environment_fingerprint="env-a",
    )
    passed = validate_native_accelerator_hint(
        native,
        fixture,
        provider_id="ortools-cp-sat",
        provider_version="fixture-1",
        environment_fingerprint="env-a",
    )
    assert passed.status == "PASS"
    assert passed.application_authority == "PERFORMANCE_HINT_ONLY"
    assert passed.details["truth_authority"] == "NONE"

    mismatched = validate_native_accelerator_hint(
        native,
        fixture,
        provider_id="ortools-cp-sat",
        provider_version="fixture-2",
        environment_fingerprint="env-a",
    )
    assert mismatched.status == "FAIL"
    assert "BACKEND_IDENTITY_MISMATCH" in mismatched.diagnostics
