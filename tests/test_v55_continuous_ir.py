from __future__ import annotations

from decimal import Decimal

import pytest

from aasm.continuous_ir import (
    ContinuousAssignment,
    ContinuousModel,
    ContinuousVariable,
    LinearExpression,
    NumericTolerancePolicy,
    QuadraticConstraint,
    QuadraticExpression,
    QuadraticObjective,
    QuadraticTerm,
    SecondOrderConeConstraint,
    bind_continuous_provider,
    canonical_decimal,
    continuous_ir_contract,
    validate_continuous_assignment,
)
from aasm.model_features import (
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
)


def _model() -> ContinuousModel:
    return ContinuousModel(
        "electrical continuous envelope",
        (
            ContinuousVariable("x", "-2", "2", source_reference_fingerprints=("req-x",)),
            ContinuousVariable("y", "-2", "2", source_reference_fingerprints=("req-y",)),
            ContinuousVariable("t", "0", "3", source_reference_fingerprints=("req-t",)),
        ),
        quadratic_constraints=(
            QuadraticConstraint(
                QuadraticExpression(
                    terms=(QuadraticTerm("x", "x", "1"), QuadraticTerm("y", "y", "1")),
                ),
                "<=",
                "1",
                source_reference_fingerprints=("req-circle",),
                constraint_id="unit-circle",
            ),
        ),
        conic_constraints=(
            SecondOrderConeConstraint(
                (
                    LinearExpression({"x": "1"}),
                    LinearExpression({"y": "1"}),
                ),
                LinearExpression({"t": "1"}),
                source_reference_fingerprints=("req-soc",),
                constraint_id="soc-envelope",
            ),
        ),
        objective=QuadraticObjective(
            "MINIMIZE",
            QuadraticExpression(
                LinearExpression({"t": "1"}),
                (QuadraticTerm("x", "x", "0.5"),),
            ),
            source_reference_fingerprints=("goal-cost",),
        ),
    )


def _governance(model: ContinuousModel):
    features = ModelFeatureSet(
        model.fingerprint,
        tuple(ModelFeatureRequirement(feature_id, "EXACT_ONLY") for feature_id in model.required_feature_ids),
    )
    manifest = ProviderCapabilityManifest(
        "conic-provider",
        "1",
        "aasm.conic",
        "1",
        tuple(ProviderFeatureSupport(feature_id, "EXACT_NATIVE") for feature_id in model.required_feature_ids),
        environment_fingerprint="conic-env-1",
    )
    admission = evaluate_model_admission(features, manifest)
    assert admission.admitted and admission.exact
    return features, manifest, admission


def test_continuous_contract_separates_structural_and_numerical_claims():
    contract = continuous_ir_contract()
    assert contract["number_encoding"] == "CANONICAL_FINITE_DECIMAL_STRINGS"
    assert contract["execution_adapter"] == "NOT_CLAIMED_BY_THIS_FOUNDATION"
    assert contract["optimality_proof"] == "NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION"
    assert contract["global_optimality"] == "NOT_INFERRED_FROM_FEASIBILITY_OR_OBJECTIVE_VALUE"
    assert contract["truth_authority"] == "NONE"


def test_decimal_canonicalization_is_stable_and_rejects_non_finite():
    assert canonical_decimal("1.2300") == "1.23"
    assert canonical_decimal(Decimal("-0.000")) == "0"
    assert canonical_decimal("1E+3") == "1000"
    with pytest.raises(ValueError, match="finite"):
        canonical_decimal("NaN")
    with pytest.raises(ValueError, match="finite"):
        canonical_decimal("Infinity")


def test_quadratic_and_soc_assignment_validates_with_decimal_math():
    model = _model()
    policy = NumericTolerancePolicy("0", "0", precision=60)
    assignment = ContinuousAssignment(model.model_id, model.fingerprint, {"x": "0.6", "y": "0.8", "t": "1"})
    report = validate_continuous_assignment(model, assignment, policy)
    assert report.valid is True
    assert report.violations == ()
    assert report.objective_value == "1.18"


def test_quadratic_violation_is_distinct_from_conic_violation():
    model = _model()
    policy = NumericTolerancePolicy("0", "0")
    assignment = ContinuousAssignment(model.model_id, model.fingerprint, {"x": "1", "y": "1", "t": "2"})
    report = validate_continuous_assignment(model, assignment, policy)
    assert report.valid is False
    codes = {row["code"] for row in report.violations}
    assert "QUADRATIC_CONSTRAINT_VIOLATION" in codes
    assert "SECOND_ORDER_CONE_VIOLATION" not in codes

    conic_bad = ContinuousAssignment(model.model_id, model.fingerprint, {"x": "0.6", "y": "0.8", "t": "0.5"})
    report2 = validate_continuous_assignment(model, conic_bad, policy)
    codes2 = {row["code"] for row in report2.violations}
    assert "SECOND_ORDER_CONE_VIOLATION" in codes2


def test_explicit_tolerance_can_accept_small_numeric_overrun_without_changing_structure():
    model = ContinuousModel(
        "tolerance fixture",
        (ContinuousVariable("x"),),
        quadratic_constraints=(
            QuadraticConstraint(
                QuadraticExpression(terms=(QuadraticTerm("x", "x", "1"),)),
                "<=",
                "1",
                constraint_id="x2-limit",
            ),
        ),
    )
    assignment = ContinuousAssignment(model.model_id, model.fingerprint, {"x": "1.0000001"})
    strict = validate_continuous_assignment(model, assignment, NumericTolerancePolicy("0", "0", precision=60))
    assert strict.valid is False
    tolerant_policy = NumericTolerancePolicy("0.000001", "0", precision=60)
    tolerant = validate_continuous_assignment(model, assignment, tolerant_policy)
    assert tolerant.valid is True
    assert tolerant.tolerance_policy_fingerprint == tolerant_policy.fingerprint


def test_bounds_and_assignment_identity_fail_closed():
    model = _model()
    policy = NumericTolerancePolicy("0", "0")
    out_of_bounds = ContinuousAssignment(model.model_id, model.fingerprint, {"x": "3", "y": "0", "t": "3"})
    report = validate_continuous_assignment(model, out_of_bounds, policy)
    assert "UPPER_BOUND_VIOLATION" in {row["code"] for row in report.violations}

    wrong = ContinuousAssignment(model.model_id, "wrong", {"x": "0", "y": "0", "t": "0"})
    report2 = validate_continuous_assignment(model, wrong, policy)
    assert report2.valid is False
    assert report2.violations[0]["code"] == "MODEL_BINDING_MISMATCH"


def test_provider_binding_requires_exact_native_declared_features_and_pins_tolerance():
    model = _model()
    features, manifest, admission = _governance(model)
    policy = NumericTolerancePolicy("1e-8", "1e-8", precision=60)
    binding = bind_continuous_provider(
        model,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        tolerance_policy=policy,
    )
    assert binding.model_fingerprint == model.fingerprint
    assert binding.provider_manifest_fingerprint == manifest.fingerprint
    assert binding.tolerance_policy_fingerprint == policy.fingerprint
    assert binding.environment_fingerprint == "conic-env-1"

    approximate_manifest = ProviderCapabilityManifest(
        "approx-conic",
        "1",
        "aasm.approx-conic",
        "1",
        tuple(
            ProviderFeatureSupport(
                feature_id,
                "APPROXIMATE_TRANSLATED",
                transformation_id=f"approx-{feature_id.lower()}",
                tolerance_policy_id="provider-tol",
            )
            for feature_id in model.required_feature_ids
        ),
    )
    approximate_admission = evaluate_model_admission(features, approximate_manifest)
    assert approximate_admission.admitted is False
    with pytest.raises(ValueError, match="exact feature admission"):
        bind_continuous_provider(
            model,
            feature_set=features,
            provider_manifest=approximate_manifest,
            admission_report=approximate_admission,
            tolerance_policy=policy,
        )


def test_quadratic_pairs_are_canonical_and_duplicates_are_rejected():
    term = QuadraticTerm("z", "a", "2.00")
    assert term.left_variable_id == "a"
    assert term.right_variable_id == "z"
    assert term.coefficient == "2"
    with pytest.raises(ValueError, match="repeat"):
        QuadraticExpression(
            terms=(
                QuadraticTerm("x", "y", "1"),
                QuadraticTerm("y", "x", "2"),
            )
        )
