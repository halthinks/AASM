from __future__ import annotations

import pytest

from aasm.model_features import (
    MODEL_ADMISSION_CONTRACT_ID,
    MODEL_FEATURE_SET_CONTRACT_ID,
    PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID,
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
    model_feature_contract,
)


def _features(*rows: ModelFeatureRequirement) -> ModelFeatureSet:
    return ModelFeatureSet(
        model_fingerprint="model-fp",
        problem_revision_id="revision-1",
        problem_revision_fingerprint="revision-fp-1",
        features=rows,
    )


def _manifest(*rows: ProviderFeatureSupport) -> ProviderCapabilityManifest:
    return ProviderCapabilityManifest(
        provider_id="provider-1",
        provider_version="1.2.3",
        adapter_id="adapter-1",
        adapter_version="0.5.0",
        feature_support=rows,
        solver_families=("MILP",),
        environment_fingerprint="env-fp",
    )


def test_exact_native_and_exact_translated_features_are_admitted_exactly():
    feature_set = _features(
        ModelFeatureRequirement("BOOLEAN"),
        ModelFeatureRequirement("PSEUDO_BOOLEAN"),
    )
    manifest = _manifest(
        ProviderFeatureSupport("BOOLEAN", "EXACT_NATIVE"),
        ProviderFeatureSupport("PSEUDO_BOOLEAN", "EXACT_TRANSLATED", transformation_id="pb-to-linear-v1"),
    )
    report = evaluate_model_admission(feature_set, manifest)
    assert report.admitted is True
    assert report.exact is True
    assert report.exact_features == ("BOOLEAN", "PSEUDO_BOOLEAN")
    assert report.unsupported_features == ()


def test_approximate_translation_fails_closed_when_exact_is_required():
    feature_set = _features(ModelFeatureRequirement("NONLINEAR_CONTINUOUS", "EXACT_ONLY"))
    manifest = _manifest(
        ProviderFeatureSupport(
            "NONLINEAR_CONTINUOUS",
            "APPROXIMATE_TRANSLATED",
            transformation_id="piecewise-linear-v2",
            tolerance_policy_id="approx-tolerance-1",
        )
    )
    report = evaluate_model_admission(feature_set, manifest)
    assert report.admitted is False
    assert report.exact is False
    assert report.unsupported_features == ("NONLINEAR_CONTINUOUS",)
    assert "NONLINEAR_CONTINUOUS:APPROXIMATION_FORBIDDEN" in report.reasons


def test_approximate_translation_is_explicit_and_never_called_exact():
    feature_set = _features(ModelFeatureRequirement("NONLINEAR_CONTINUOUS", "EXACT_OR_APPROXIMATE"))
    manifest = _manifest(
        ProviderFeatureSupport(
            "NONLINEAR_CONTINUOUS",
            "APPROXIMATE_TRANSLATED",
            transformation_id="piecewise-linear-v2",
            tolerance_policy_id="approx-tolerance-1",
        )
    )
    report = evaluate_model_admission(feature_set, manifest)
    assert report.admitted is True
    assert report.exact is False
    assert report.approximate_features == ("NONLINEAR_CONTINUOUS",)


def test_verifier_only_support_requires_explicit_model_permission():
    manifest = _manifest(ProviderFeatureSupport("GEOMETRIC_PREDICATE", "VERIFIER_ONLY"))
    rejected = evaluate_model_admission(
        _features(ModelFeatureRequirement("GEOMETRIC_PREDICATE", "EXACT_ONLY")),
        manifest,
    )
    accepted = evaluate_model_admission(
        _features(ModelFeatureRequirement("GEOMETRIC_PREDICATE", "VERIFIER_ONLY_ALLOWED")),
        manifest,
    )
    assert rejected.admitted is False
    assert "GEOMETRIC_PREDICATE:VERIFIER_ONLY_NOT_ALLOWED" in rejected.reasons
    assert accepted.admitted is True
    assert accepted.exact is False
    assert accepted.verifier_only_features == ("GEOMETRIC_PREDICATE",)


def test_missing_provider_feature_is_unsupported():
    report = evaluate_model_admission(
        _features(ModelFeatureRequirement("ROBUST_OR_SCENARIO_CONSTRAINT")),
        _manifest(ProviderFeatureSupport("BOOLEAN", "EXACT_NATIVE")),
    )
    assert report.admitted is False
    assert report.unsupported_features == ("ROBUST_OR_SCENARIO_CONSTRAINT",)


def test_translated_support_requires_transformation_and_approximation_policy():
    with pytest.raises(ValueError):
        ProviderFeatureSupport("PSEUDO_BOOLEAN", "EXACT_TRANSLATED")
    with pytest.raises(ValueError):
        ProviderFeatureSupport("NONLINEAR_CONTINUOUS", "APPROXIMATE_TRANSLATED", transformation_id="xform")


def test_feature_set_requires_revision_identity_as_a_pair():
    with pytest.raises(ValueError):
        ModelFeatureSet(
            model_fingerprint="model-fp",
            problem_revision_id="revision-only",
            features=(ModelFeatureRequirement("BOOLEAN"),),
        )


def test_contract_is_fail_closed_and_grants_no_truth():
    contract = model_feature_contract()
    assert contract["feature_set_contract_id"] == MODEL_FEATURE_SET_CONTRACT_ID
    assert contract["provider_manifest_contract_id"] == PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID
    assert contract["admission_contract_id"] == MODEL_ADMISSION_CONTRACT_ID
    assert contract["unsupported_feature_policy"] == "FAIL_CLOSED_BEFORE_PROVIDER_EXECUTION"
    assert contract["truth_authority"] == "NONE"
