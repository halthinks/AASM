from __future__ import annotations

from copy import deepcopy

import pytest

from aasm.discrete_ir import (
    CARDINALITY_LINEARIZATION_ID,
    PSEUDO_BOOLEAN_LINEARIZATION_ID,
    CardinalityConstraint,
    DiscreteBooleanModel,
    DiscreteLinearization,
    PseudoBooleanConstraint,
    WeightedBooleanLiteral,
    discrete_ir_contract,
    lower_discrete_boolean_model,
    verify_discrete_boolean_linearization,
)
from aasm.model_features import (
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
)
from aasm.optimization import BooleanLiteral, validate_optimization_solution


def _model() -> DiscreteBooleanModel:
    return DiscreteBooleanModel(
        "board discrete constraints",
        ("x", "y", "z"),
        pseudo_boolean_constraints=(
            PseudoBooleanConstraint(
                (
                    WeightedBooleanLiteral("x", True, 3),
                    WeightedBooleanLiteral("y", False, 2),
                    WeightedBooleanLiteral("z", True, -1),
                ),
                "<=",
                4,
                source_reference_fingerprints=("req-pb",),
                constraint_id="pb-power-budget",
            ),
        ),
        cardinality_constraints=(
            CardinalityConstraint(
                (
                    BooleanLiteral("x", True),
                    BooleanLiteral("y", False),
                    BooleanLiteral("z", True),
                ),
                min_count=1,
                max_count=2,
                source_reference_fingerprints=("req-card",),
                constraint_id="card-route-choice",
            ),
        ),
    )


def _governance(model: DiscreteBooleanModel, provider: str = "provider-milp"):
    features = ModelFeatureSet(
        model.fingerprint,
        (
            ModelFeatureRequirement("PSEUDO_BOOLEAN", "EXACT_ONLY", source_reference_fingerprints=("req-pb",)),
            ModelFeatureRequirement("CARDINALITY", "EXACT_ONLY", source_reference_fingerprints=("req-card",)),
        ),
    )
    manifest = ProviderCapabilityManifest(
        provider,
        "1",
        "aasm.test-discrete",
        "1",
        (
            ProviderFeatureSupport("PSEUDO_BOOLEAN", "EXACT_TRANSLATED", transformation_id=PSEUDO_BOOLEAN_LINEARIZATION_ID),
            ProviderFeatureSupport("CARDINALITY", "EXACT_TRANSLATED", transformation_id=CARDINALITY_LINEARIZATION_ID),
        ),
        solver_families=("MILP", "CP_SAT"),
    )
    admission = evaluate_model_admission(features, manifest)
    assert admission.admitted and admission.exact
    return features, manifest, admission


def test_discrete_ir_contract_is_exact_and_non_authoritative():
    contract = discrete_ir_contract()
    assert contract["source_semantics"] == ["PSEUDO_BOOLEAN", "CARDINALITY"]
    assert contract["approximation"] == "NOT_SUPPORTED_BY_THIS_CONTRACT"
    assert contract["checker_method"] == "INDEPENDENT_ALGEBRAIC_RECONSTRUCTION_OF_EXPECTED_LINEAR_TARGET"
    assert contract["truth_authority"] == "NONE"


def test_pseudo_boolean_negative_literal_linearizes_exactly():
    model = _model()
    features, manifest, admission = _governance(model)
    lowering, certificate = lower_discrete_boolean_model(
        model,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        target_family="MILP",
    )
    assert certificate.status == "PASS"
    assert certificate.exact is True
    target = {row.constraint_id: row for row in lowering.target_model.constraints}
    pb = target["pb-power-budget__pb_linear"]
    # 3*x + 2*(1-y) - z <= 4  =>  3*x - 2*y - z <= 2
    assert pb.coefficients == {"x": 3.0, "y": -2.0, "z": -1.0}
    assert pb.sense == "<="
    assert pb.rhs == 2.0
    mapping = next(row for row in lowering.mappings if row.source_constraint_id == "pb-power-budget")
    assert mapping.transformation_id == PSEUDO_BOOLEAN_LINEARIZATION_ID
    assert mapping.source_reference_fingerprints == ("req-pb",)


def test_cardinality_range_becomes_two_exact_linear_constraints():
    model = _model()
    features, manifest, admission = _governance(model)
    lowering, certificate = lower_discrete_boolean_model(
        model,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        target_family="CP_SAT",
    )
    assert certificate.status == "PASS"
    target = {row.constraint_id: row for row in lowering.target_model.constraints}
    lower = target["card-route-choice__card_min"]
    upper = target["card-route-choice__card_max"]
    # x + (1-y) + z in [1,2] => x - y + z in [0,1]
    assert lower.coefficients == {"x": 1.0, "y": -1.0, "z": 1.0}
    assert lower.sense == ">=" and lower.rhs == 0.0
    assert upper.coefficients == {"x": 1.0, "y": -1.0, "z": 1.0}
    assert upper.sense == "<=" and upper.rhs == 1.0
    mapping = next(row for row in lowering.mappings if row.source_constraint_id == "card-route-choice")
    assert mapping.target_constraint_ids == ("card-route-choice__card_max", "card-route-choice__card_min")
    assert mapping.source_reference_fingerprints == ("req-card",)


def test_linearized_target_accepts_exactly_the_same_sampled_assignments():
    model = _model()
    features, manifest, admission = _governance(model)
    lowering, _ = lower_discrete_boolean_model(
        model,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        target_family="MILP",
    )
    for x in (0, 1):
        for y in (0, 1):
            for z in (0, 1):
                assignment = {"x": float(x), "y": float(y), "z": float(z)}
                pb_value = 3 * x + 2 * (1 - y) - z
                card_value = x + (1 - y) + z
                source_valid = pb_value <= 4 and 1 <= card_value <= 2
                try:
                    validate_optimization_solution(lowering.target_model, assignment)
                    target_valid = True
                except ValueError:
                    target_valid = False
                assert target_valid is source_valid


def test_independent_checker_rejects_tampered_target_constraint():
    model = _model()
    features, manifest, admission = _governance(model)
    lowering, certificate = lower_discrete_boolean_model(
        model,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        target_family="MILP",
    )
    assert certificate.status == "PASS"
    payload = lowering.to_dict()
    payload["target_model"]["constraints"][0]["rhs"] = float(payload["target_model"]["constraints"][0]["rhs"]) + 1.0
    payload["target_model"].pop("fingerprint", None)
    payload["target_model"].pop("solver_family", None)
    payload.pop("fingerprint", None)
    tampered = DiscreteLinearization.from_dict(payload)
    rejected = verify_discrete_boolean_linearization(tampered)
    assert rejected.status == "FAIL"
    assert "TARGET_LINEARIZATION_MISMATCH" in rejected.diagnostics


def test_lowering_rejects_unapproved_or_wrong_translation_identity():
    model = _model()
    features, manifest, admission = _governance(model)
    wrong_manifest = ProviderCapabilityManifest(
        "provider-wrong",
        "1",
        "aasm.test-discrete",
        "1",
        (
            ProviderFeatureSupport("PSEUDO_BOOLEAN", "EXACT_TRANSLATED", transformation_id="wrong-pb-transform"),
            ProviderFeatureSupport("CARDINALITY", "EXACT_TRANSLATED", transformation_id=CARDINALITY_LINEARIZATION_ID),
        ),
        solver_families=("MILP",),
    )
    wrong_admission = evaluate_model_admission(features, wrong_manifest)
    assert wrong_admission.exact
    with pytest.raises(ValueError, match="transformation_id"):
        lower_discrete_boolean_model(
            model,
            feature_set=features,
            provider_manifest=wrong_manifest,
            admission_report=wrong_admission,
            target_family="MILP",
        )


def test_constant_false_normalization_is_encoded_as_explicit_infeasibility():
    model = DiscreteBooleanModel(
        "constant contradiction",
        ("x",),
        pseudo_boolean_constraints=(
            PseudoBooleanConstraint(
                (
                    WeightedBooleanLiteral("x", True, 1),
                    WeightedBooleanLiteral("x", False, 1),
                ),
                "==",
                0,
                constraint_id="always-one-equals-zero",
            ),
        ),
    )
    features = ModelFeatureSet(model.fingerprint, (ModelFeatureRequirement("PSEUDO_BOOLEAN", "EXACT_ONLY"),))
    manifest = ProviderCapabilityManifest(
        "provider-constant",
        "1",
        "aasm.test-discrete",
        "1",
        (ProviderFeatureSupport("PSEUDO_BOOLEAN", "EXACT_TRANSLATED", transformation_id=PSEUDO_BOOLEAN_LINEARIZATION_ID),),
        solver_families=("MILP",),
    )
    admission = evaluate_model_admission(features, manifest)
    lowering, certificate = lower_discrete_boolean_model(
        model,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        target_family="MILP",
    )
    assert certificate.status == "PASS"
    assert "__aasm_discrete_false" in {row.variable_id for row in lowering.target_model.variables}
    with pytest.raises(ValueError):
        validate_optimization_solution(lowering.target_model, {"x": 0.0, "__aasm_discrete_false": 0.0})
