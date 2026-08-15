from __future__ import annotations

import pytest

from aasm.model_features import (
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
)
from aasm.scheduling_ir import (
    CumulativeResourceConstraint,
    NoOverlapConstraint,
    PrecedenceConstraint,
    SchedulingAssignment,
    SchedulingModel,
    SchedulingTask,
    bind_scheduling_provider,
    scheduling_ir_contract,
    validate_scheduling_assignment,
)


def _model() -> SchedulingModel:
    return SchedulingModel(
        "board operation schedule",
        20,
        (
            SchedulingTask("place", 4, source_reference_fingerprints=("req-place",)),
            SchedulingTask("route", 5, source_reference_fingerprints=("req-route",)),
            SchedulingTask("verify", 3, source_reference_fingerprints=("req-verify",)),
            SchedulingTask("thermal", 4, source_reference_fingerprints=("req-thermal",)),
        ),
        precedences=(
            PrecedenceConstraint("place", "route", min_lag=1, source_reference_fingerprints=("req-order",), constraint_id="precedence-place-route"),
            PrecedenceConstraint("route", "verify", source_reference_fingerprints=("req-order",), constraint_id="precedence-route-verify"),
        ),
        no_overlaps=(
            NoOverlapConstraint(("verify", "thermal"), source_reference_fingerprints=("req-lab",), constraint_id="no-overlap-lab"),
        ),
        cumulative_resources=(
            CumulativeResourceConstraint("expert", 2, {"route": 2, "verify": 1, "thermal": 1}, source_reference_fingerprints=("req-expert",), constraint_id="cumulative-expert"),
        ),
    )


def test_scheduling_contract_claim_ceiling_is_truthful():
    contract = scheduling_ir_contract()
    assert contract["global_constraints"] == ["PRECEDENCE", "NO_OVERLAP", "CUMULATIVE_RESOURCE"]
    assert contract["execution_adapter"] == "NOT_CLAIMED_BY_THIS_FOUNDATION"
    assert contract["approximation"] == "NOT_SUPPORTED_BY_THIS_CONTRACT"
    assert contract["truth_authority"] == "NONE"


def test_valid_schedule_passes_independent_validator():
    model = _model()
    assignment = SchedulingAssignment(model.model_id, model.fingerprint, {"place": 0, "route": 5, "verify": 10, "thermal": 13})
    report = validate_scheduling_assignment(model, assignment)
    assert report.valid is True
    assert report.violations == ()


def test_precedence_violation_is_explicit():
    model = _model()
    assignment = SchedulingAssignment(model.model_id, model.fingerprint, {"place": 0, "route": 4, "verify": 10, "thermal": 13})
    report = validate_scheduling_assignment(model, assignment)
    assert report.valid is False
    assert "PRECEDENCE_VIOLATION" in {row["code"] for row in report.violations}


def test_no_overlap_violation_is_explicit():
    model = _model()
    assignment = SchedulingAssignment(model.model_id, model.fingerprint, {"place": 0, "route": 5, "verify": 10, "thermal": 11})
    report = validate_scheduling_assignment(model, assignment)
    assert report.valid is False
    assert "NO_OVERLAP_VIOLATION" in {row["code"] for row in report.violations}


def test_cumulative_resource_violation_uses_half_open_intervals():
    model = SchedulingModel(
        "capacity schedule",
        12,
        (
            SchedulingTask("a", 5),
            SchedulingTask("b", 5),
            SchedulingTask("c", 2),
        ),
        cumulative_resources=(
            CumulativeResourceConstraint("gpu", 3, {"a": 2, "b": 2, "c": 1}, constraint_id="gpu-capacity"),
        ),
    )
    violating = SchedulingAssignment(model.model_id, model.fingerprint, {"a": 0, "b": 3, "c": 8})
    report = validate_scheduling_assignment(model, violating)
    assert report.valid is False
    violation = next(row for row in report.violations if row["code"] == "CUMULATIVE_CAPACITY_VIOLATION")
    assert violation["interval"] == [3, 5]
    assert violation["load"] == 4

    boundary_safe = SchedulingAssignment(model.model_id, model.fingerprint, {"a": 0, "b": 5, "c": 10})
    assert validate_scheduling_assignment(model, boundary_safe).valid is True


def test_assignment_must_bind_exact_model_and_complete_task_set():
    model = _model()
    wrong = SchedulingAssignment(model.model_id, "wrong-fingerprint", {"place": 0, "route": 5, "verify": 10, "thermal": 13})
    report = validate_scheduling_assignment(model, wrong)
    assert report.valid is False
    assert report.violations[0]["code"] == "MODEL_BINDING_MISMATCH"

    incomplete = SchedulingAssignment(model.model_id, model.fingerprint, {"place": 0})
    report2 = validate_scheduling_assignment(model, incomplete)
    assert report2.valid is False
    assert report2.violations[0]["code"] == "ASSIGNMENT_TASK_SET_MISMATCH"


def test_provider_binding_requires_exact_native_global_scheduling():
    model = _model()
    features = ModelFeatureSet(model.fingerprint, (ModelFeatureRequirement("GLOBAL_SCHEDULING", "EXACT_ONLY"),))
    exact_manifest = ProviderCapabilityManifest(
        "ortools-cpsat",
        "1",
        "aasm.ortools",
        "1",
        (ProviderFeatureSupport("GLOBAL_SCHEDULING", "EXACT_NATIVE"),),
        solver_families=("CP_SAT",),
        environment_fingerprint="env-1",
    )
    admission = evaluate_model_admission(features, exact_manifest)
    binding = bind_scheduling_provider(model, feature_set=features, provider_manifest=exact_manifest, admission_report=admission)
    assert binding.model_fingerprint == model.fingerprint
    assert binding.provider_id == "ortools-cpsat"
    assert binding.environment_fingerprint == "env-1"

    approximate_manifest = ProviderCapabilityManifest(
        "approx-scheduler",
        "1",
        "aasm.approx",
        "1",
        (ProviderFeatureSupport("GLOBAL_SCHEDULING", "APPROXIMATE_TRANSLATED", transformation_id="approx-schedule", tolerance_policy_id="tol"),),
        solver_families=("CP_SAT",),
    )
    approximate_admission = evaluate_model_admission(features, approximate_manifest)
    assert approximate_admission.admitted is False
    with pytest.raises(ValueError, match="EXACT_NATIVE"):
        bind_scheduling_provider(model, feature_set=features, provider_manifest=approximate_manifest, admission_report=approximate_admission)
