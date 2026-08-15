from __future__ import annotations

from dataclasses import replace

import pytest

from aasm.formulation_execution import (
    FORMULATION_EXECUTION_BINDING_CONTRACT_ID,
    bind_formulation_execution_request,
    formulation_execution_contract,
    validate_formulation_governance_chain,
)
from aasm.model_features import (
    ModelFeatureRequirement,
    ModelFeatureSet,
    ProviderCapabilityManifest,
    ProviderFeatureSupport,
    evaluate_model_admission,
)
from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationRequest,
    OptimizationVariable,
)
from aasm.runtime_v54 import translate_model_for_solver
from aasm.solver_formulation import formulation_from_v54_translation


def _chain(environment_fingerprint: str = ""):
    source = OptimizationModel(
        "execution-binding-fixture",
        (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
        (
            OptimizationConstraint(
                "LINEAR",
                coefficients={"x": 1, "y": 1},
                sense="<=",
                rhs=1,
                constraint_id="capacity",
            ),
        ),
        objective=OptimizationObjective("MINIMIZE", {"x": 1, "y": 2}),
    )
    translation, translation_certificate = translate_model_for_solver(
        source,
        target_family="MILP",
        target_provider_id="highs-governed",
    )
    features = ModelFeatureSet(source.fingerprint, (ModelFeatureRequirement("BOOLEAN", "EXACT_ONLY"),))
    manifest = ProviderCapabilityManifest(
        "highs-governed",
        "1.0",
        "aasm.highs",
        "0.1.0",
        (ProviderFeatureSupport("BOOLEAN", "EXACT_NATIVE"),),
        solver_families=("MILP",),
        environment_fingerprint=environment_fingerprint,
    )
    admission = evaluate_model_admission(features, manifest)
    formulation, certificate = formulation_from_v54_translation(
        source,
        translation,
        translation_certificate,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
    )
    return source, features, manifest, admission, formulation, certificate


def _request(formulation, *, provider="highs-governed", environment_fingerprint=""):
    return OptimizationRequest(
        formulation.target_model,
        capability_id="solver.milp",
        capability_version="0.1.0",
        obligation_id="solve-board",
        required_provider=provider,
        environment_fingerprint=environment_fingerprint,
    )


def test_exact_governance_chain_binds_to_existing_optimization_request():
    _, features, manifest, admission, formulation, certificate = _chain()
    request = _request(formulation)
    report = validate_formulation_governance_chain(
        formulation,
        certificate,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
    )
    assert report["valid"] is True
    binding = bind_formulation_execution_request(
        request,
        formulation,
        certificate,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
    )
    assert binding.request_fingerprint == request.fingerprint
    assert binding.target_model_fingerprint == formulation.target_model.fingerprint
    assert binding.target_provider_id == "highs-governed"
    assert binding.formulation_certificate_fingerprint == certificate.fingerprint


def test_execution_binding_rejects_provider_substitution():
    _, features, manifest, admission, formulation, certificate = _chain()
    request = _request(formulation, provider="different-provider")
    with pytest.raises(ValueError, match="required_provider"):
        bind_formulation_execution_request(
            request,
            formulation,
            certificate,
            feature_set=features,
            provider_manifest=manifest,
            admission_report=admission,
        )


def test_execution_binding_requires_explicit_provider():
    _, features, manifest, admission, formulation, certificate = _chain()
    request = _request(formulation, provider="")
    with pytest.raises(ValueError, match="must require the exact target provider"):
        bind_formulation_execution_request(
            request,
            formulation,
            certificate,
            feature_set=features,
            provider_manifest=manifest,
            admission_report=admission,
        )


def test_environment_bound_manifest_requires_exact_request_environment():
    _, features, manifest, admission, formulation, certificate = _chain("env-locked")
    missing = _request(formulation)
    with pytest.raises(ValueError, match="has no environment fingerprint"):
        bind_formulation_execution_request(
            missing,
            formulation,
            certificate,
            feature_set=features,
            provider_manifest=manifest,
            admission_report=admission,
        )
    wrong = _request(formulation, environment_fingerprint="env-wrong")
    with pytest.raises(ValueError, match="does not match"):
        bind_formulation_execution_request(
            wrong,
            formulation,
            certificate,
            feature_set=features,
            provider_manifest=manifest,
            admission_report=admission,
        )
    exact = _request(formulation, environment_fingerprint="env-locked")
    assert bind_formulation_execution_request(
        exact,
        formulation,
        certificate,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
    ).environment_fingerprint == "env-locked"


def test_governance_chain_rejects_manifest_or_admission_substitution():
    _, features, manifest, admission, formulation, certificate = _chain()
    other_manifest = ProviderCapabilityManifest(
        manifest.provider_id,
        "2.0",
        manifest.adapter_id,
        manifest.adapter_version,
        manifest.feature_support,
        solver_families=manifest.solver_families,
    )
    report = validate_formulation_governance_chain(
        formulation,
        certificate,
        feature_set=features,
        provider_manifest=other_manifest,
        admission_report=admission,
    )
    assert report["valid"] is False
    assert "PROVIDER_MANIFEST_BINDING_MISMATCH" in report["errors"]


def test_execution_binding_rejects_nonpassing_formulation_certificate():
    _, features, manifest, admission, formulation, certificate = _chain()
    failing = replace(
        certificate,
        status="FAIL",
        verified_fidelity="NONE",
        diagnostics=("test failure",),
        certificate_id="",
    )
    request = _request(formulation)
    with pytest.raises(ValueError, match="FORMULATION_CERTIFICATE_NOT_EXACT_PASS"):
        bind_formulation_execution_request(
            request,
            formulation,
            failing,
            feature_set=features,
            provider_manifest=manifest,
            admission_report=admission,
        )


def test_execution_contract_grants_no_execution_or_truth_authority():
    contract = formulation_execution_contract()
    assert contract["contract_id"] == FORMULATION_EXECUTION_BINDING_CONTRACT_ID
    assert contract["required_certificate"] == "PASS_EXACT"
    assert contract["provider_execution"] == "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY"
    assert contract["execution_authority"] == "NONE_GRANTED_BY_BINDING"
    assert contract["truth_authority"] == "NONE"
