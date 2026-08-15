import pytest

from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationRequest,
    OptimizationVariable,
)
from aasm.solver_learning import (
    SolverLearningApplication,
    SolverLearningArtifact,
    apply_solver_learning_to_optimization_request,
    build_solver_learning_application,
    revalidate_finite_solver_learning,
    solver_learning_application_contract,
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
    assert contract["application"] == "EXPLICIT_VALIDATED_ADAPTER_APPLICATION_ONLY"
    assert contract["application_truth_authority"] == "NONE"
    assert contract["application_policy_authority"] == "NONE"
    assert contract["solver_execution"] == "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY"

    application = solver_learning_application_contract()
    assert application["contract_id"] == "aasm.solver.learning.application.v1"
    assert application["truth_authority"] == "NONE"
    assert application["policy_authority"] == "NONE"
    assert application["current_assignment_hint_provider"] == "ortools-cp-sat"


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


def test_no_good_revalidation_rejects_unknown_and_non_boolean_literal_variables_before_enumeration():
    fixture = model()
    unknown = SolverLearningArtifact(
        "NO_GOOD",
        fixture.fingerprint,
        fixture.solver_family,
        {"literals": [{"variable_id": "ghost", "positive": True}]},
    )
    checked = revalidate_finite_solver_learning(unknown, fixture)
    assert checked.status == "FAIL"
    assert checked.application_authority == "NONE"
    assert checked.diagnostics == ("UNKNOWN_LITERAL_VARIABLE:ghost",)

    integer_model = OptimizationModel(
        "integer-learning-fixture",
        (OptimizationVariable("n", "INTEGER", 0, 1),),
        (OptimizationConstraint("LINEAR", coefficients={"n": 1}, sense=">=", rhs=0),),
        family="CP_SAT",
    )
    non_boolean = SolverLearningArtifact(
        "NO_GOOD",
        integer_model.fingerprint,
        integer_model.solver_family,
        {"literals": [{"variable_id": "n", "positive": True}]},
    )
    checked = revalidate_finite_solver_learning(non_boolean, integer_model)
    assert checked.status == "FAIL"
    assert checked.diagnostics == ("NON_BOOLEAN_LITERAL_VARIABLE:n",)


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


def test_certified_boolean_no_good_lowers_to_existing_cp_sat_model_ir():
    fixture = model()
    learned = artifact(
        "NO_GOOD",
        {"literals": [{"variable_id": "x", "positive": False}, {"variable_id": "y", "positive": False}]},
    )
    validation = revalidate_finite_solver_learning(learned, fixture)
    application, transformed = build_solver_learning_application(learned, validation, fixture)
    assert application.application_class == "PRUNING_CONSTRAINTS"
    assert application.truth_authority == "NONE"
    assert application.policy_authority == "NONE"
    assert transformed is not None
    assert transformed.fingerprint == application.transformed_model_fingerprint
    assert transformed.metadata["solver_learning_original_model_fingerprint"] == fixture.fingerprint
    constraint = transformed.constraints[-1]
    assert constraint.kind == "LINEAR"
    assert constraint.coefficients == {"x": 1.0, "y": 1.0}
    assert constraint.sense == ">="
    assert constraint.rhs == 1.0
    assert constraint.metadata["truth_authority"] == "NONE"
    assert SolverLearningApplication.from_dict(application.to_dict()).to_dict() == application.to_dict()


def test_certified_sat_no_good_lowers_to_complement_clause():
    sat = OptimizationModel(
        "sat-learning-fixture",
        (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
        (OptimizationConstraint("CLAUSE", literals=({"variable_id": "x", "positive": True}, {"variable_id": "y", "positive": True})),),
        family="SAT",
    )
    learned = SolverLearningArtifact(
        "NO_GOOD",
        sat.fingerprint,
        sat.solver_family,
        {"literals": [{"variable_id": "x", "positive": False}, {"variable_id": "y", "positive": False}]},
    )
    validation = revalidate_finite_solver_learning(learned, sat)
    assert validation.status == "PASS"
    application, transformed = build_solver_learning_application(learned, validation, sat)
    learned_clause = transformed.constraints[-1]
    assert learned_clause.kind == "CLAUSE"
    assert [(row.variable_id, row.positive) for row in learned_clause.literals] == [("x", True), ("y", True)]
    assert application.application_class == "PRUNING_CONSTRAINTS"


def test_certified_bound_application_preserves_validation_tolerance():
    fixture = model()
    learned = artifact("BOUND", {"bound_type": "LOWER", "value": 1.25, "tolerance": 0.25})
    validation = revalidate_finite_solver_learning(learned, fixture)
    assert validation.status == "PASS"
    application, transformed = build_solver_learning_application(learned, validation, fixture)
    constraint = transformed.constraints[-1]
    assert constraint.coefficients == {"x": 1.0, "y": 1.0}
    assert constraint.sense == ">="
    assert constraint.rhs == 1.0
    assert constraint.metadata["validated_tolerance"] == 0.25
    assert application.truth_authority == "NONE"


def test_failed_validation_cannot_be_turned_into_application():
    fixture = model()
    forged = artifact(
        "NO_GOOD",
        {"literals": [{"variable_id": "x", "positive": True}, {"variable_id": "y", "positive": False}]},
    )
    failed = revalidate_finite_solver_learning(forged, fixture)
    assert failed.status == "FAIL"
    with pytest.raises(ValueError, match="PASS local validation"):
        build_solver_learning_application(forged, failed, fixture)


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


def test_validated_assignment_hint_is_packaged_only_for_explicit_ortools_adapter():
    fixture = model()
    learned = artifact("INCUMBENT", {"assignment": {"x": 1, "y": 0}, "objective": 1})
    validation = revalidate_finite_solver_learning(learned, fixture)
    request = OptimizationRequest(
        fixture,
        "solver.cp_sat",
        "0.1.0",
        "learning-hint-obligation",
        required_provider="ortools-cp-sat",
    )
    application, updated = apply_solver_learning_to_optimization_request(learned, validation, request)
    assert application.application_class == "PERFORMANCE_HINT"
    assert application.provider_id == "ortools-cp-sat"
    assert updated.model.fingerprint == fixture.fingerprint
    assert updated.metadata["solver_learning_truth_authority"] == "NONE"
    hints = updated.metadata["solver_learning_hints"]
    assert hints == [{
        "application_id": application.application_id,
        "provider_id": "ortools-cp-sat",
        "hint_kind": "ASSIGNMENT",
        "source_kind": "INCUMBENT",
        "assignment": {"x": 1.0, "y": 0.0},
    }]

    unsupported = OptimizationRequest(
        fixture,
        "solver.cp_sat",
        "0.1.0",
        "unsupported-hint-obligation",
        required_provider="",
    )
    with pytest.raises(ValueError, match="explicit ortools-cp-sat adapter"):
        apply_solver_learning_to_optimization_request(learned, validation, unsupported)


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

    with pytest.raises(ValueError, match="no explicit public adapter application"):
        build_solver_learning_application(native, passed, fixture, provider_id="ortools-cp-sat")

    mismatched = validate_native_accelerator_hint(
        native,
        fixture,
        provider_id="ortools-cp-sat",
        provider_version="fixture-2",
        environment_fingerprint="env-a",
    )
    assert mismatched.status == "FAIL"
    assert "BACKEND_IDENTITY_MISMATCH" in mismatched.diagnostics
