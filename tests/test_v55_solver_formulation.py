from __future__ import annotations

from dataclasses import replace

import pytest

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
    OptimizationVariable,
)
from aasm.runtime_v54 import translate_model_for_solver
from aasm.semantic_evolution import ExternalReference
from aasm.solver_formulation import (
    SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID,
    SOLVER_FORMULATION_CONTRACT_ID,
    FormulationExternalReferenceBinding,
    FormulationObjectMapping,
    SolverFormulation,
    formulation_from_v54_translation,
    identity_object_mappings,
    solver_formulation_contract,
    verify_solver_formulation_identity,
)


def source_model() -> OptimizationModel:
    return OptimizationModel(
        "formulation-fixture",
        (
            OptimizationVariable("x", "BOOL"),
            OptimizationVariable("y", "BOOL"),
        ),
        (
            OptimizationConstraint(
                "LINEAR",
                coefficients={"x": 1, "y": 1},
                sense="<=",
                rhs=1,
                constraint_id="req-power-budget",
            ),
        ),
        objective=OptimizationObjective("MINIMIZE", {"x": 1, "y": 2}),
    )


def exact_admission(model: OptimizationModel, provider_id: str = "highs-formulation"):
    features = ModelFeatureSet(
        model.fingerprint,
        (ModelFeatureRequirement("BOOLEAN", "EXACT_ONLY"),),
        problem_revision_id="board-r1",
        problem_revision_fingerprint="board-r1-fingerprint",
    )
    manifest = ProviderCapabilityManifest(
        provider_id,
        "1.0",
        "aasm.highs",
        "0.1.0",
        (ProviderFeatureSupport("BOOLEAN", "EXACT_NATIVE"),),
        solver_families=("MILP",),
    )
    admission = evaluate_model_admission(features, manifest)
    assert admission.admitted and admission.exact
    return features, manifest, admission


def test_v54_exact_translation_becomes_certified_formulation_with_external_lineage():
    model = source_model()
    translation, translation_certificate = translate_model_for_solver(
        model,
        target_family="MILP",
        target_provider_id="highs-formulation",
    )
    features, manifest, admission = exact_admission(model)
    reference = ExternalReference(
        namespace="textpcb.requirement",
        external_id="REQ-PWR-7",
        role="HARD_REQUIREMENT",
        revision="4",
        semantic_entity_id="requirement.power.7",
    )
    binding = FormulationExternalReferenceBinding(
        reference,
        "CONSTRAINT",
        "req-power-budget",
        "CONSTRAINT",
        ("req-power-budget",),
    )
    formulation, certificate = formulation_from_v54_translation(
        model,
        translation,
        translation_certificate,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        external_reference_bindings=(binding,),
        problem_revision_id="board-r1",
        problem_revision_fingerprint="board-r1-fingerprint",
    )
    assert certificate.status == "PASS"
    assert certificate.verified_fidelity == "EXACT"
    assert certificate.mapping_complete is True
    assert certificate.external_references_resolved is True
    assert formulation.predecessor_translation_id == translation.translation_id
    assert formulation.external_reference_bindings[0].reference.key == "textpcb.requirement:REQ-PWR-7@4"
    assert SolverFormulation.from_dict(formulation.to_dict()).fingerprint == formulation.fingerprint


def test_dropped_source_and_unaccounted_target_objects_fail_certificate():
    model = source_model()
    features, manifest, admission = exact_admission(model)
    mappings = tuple(row for row in identity_object_mappings(model) if not (row.object_kind == "VARIABLE" and row.source_id == "y"))
    formulation = SolverFormulation(
        model,
        OptimizationModel.from_dict({**model.to_dict(), "family": "MILP"}),
        manifest.provider_id,
        manifest.manifest_id,
        manifest.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        admission.report_id,
        admission.fingerprint,
        "EXACT",
        mappings,
        problem_revision_id="board-r1",
        problem_revision_fingerprint="board-r1-fingerprint",
    )
    certificate = verify_solver_formulation_identity(formulation)
    assert certificate.status == "FAIL"
    assert any(row.startswith("UNMAPPED_SOURCE_VARIABLE:y") for row in certificate.diagnostics)
    assert any(row.startswith("UNACCOUNTED_TARGET_VARIABLE:y") for row in certificate.diagnostics)


def test_tampered_target_semantics_fail_even_when_mapping_ids_are_complete():
    model = source_model()
    features, manifest, admission = exact_admission(model)
    target = OptimizationModel(
        model.name,
        model.variables,
        (
            OptimizationConstraint(
                "LINEAR",
                coefficients={"x": 1, "y": 1},
                sense="<=",
                rhs=2,
                constraint_id="req-power-budget",
            ),
        ),
        objective=model.objective,
        family="MILP",
    )
    formulation = SolverFormulation(
        model,
        target,
        manifest.provider_id,
        manifest.manifest_id,
        manifest.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        admission.report_id,
        admission.fingerprint,
        "EXACT",
        identity_object_mappings(model),
        problem_revision_id="board-r1",
        problem_revision_fingerprint="board-r1-fingerprint",
    )
    certificate = verify_solver_formulation_identity(formulation)
    assert certificate.status == "FAIL"
    assert "SEMANTIC_PROJECTION_MISMATCH" in certificate.diagnostics


def test_unresolved_external_reference_target_fails_certificate():
    model = source_model()
    features, manifest, admission = exact_admission(model)
    reference = ExternalReference("textpcb.requirement", "REQ-X", "HARD_REQUIREMENT")
    bad_binding = FormulationExternalReferenceBinding(
        reference,
        "CONSTRAINT",
        "req-power-budget",
        "CONSTRAINT",
        ("missing-target-constraint",),
    )
    target = OptimizationModel.from_dict({**model.to_dict(), "family": "MILP"})
    formulation = SolverFormulation(
        model,
        target,
        manifest.provider_id,
        manifest.manifest_id,
        manifest.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        admission.report_id,
        admission.fingerprint,
        "EXACT",
        identity_object_mappings(model),
        external_reference_bindings=(bad_binding,),
        problem_revision_id="board-r1",
        problem_revision_fingerprint="board-r1-fingerprint",
    )
    certificate = verify_solver_formulation_identity(formulation)
    assert certificate.status == "FAIL"
    assert certificate.external_references_resolved is False
    assert any(row.startswith("REFERENCE_UNKNOWN_TARGET") for row in certificate.diagnostics)


def test_nontrivial_transform_is_representable_but_builtin_checker_refuses_to_certify_it():
    model = source_model()
    features, manifest, admission = exact_admission(model)
    mappings = list(identity_object_mappings(model))
    mappings[0] = FormulationObjectMapping(
        mappings[0].object_kind,
        mappings[0].source_id,
        mappings[0].target_ids,
        mapping_kind="EXACT_TRANSFORM",
        transformation_id="explicit-exact-rewrite-v1",
    )
    target = OptimizationModel.from_dict({**model.to_dict(), "family": "MILP"})
    formulation = SolverFormulation(
        model,
        target,
        manifest.provider_id,
        manifest.manifest_id,
        manifest.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        admission.report_id,
        admission.fingerprint,
        "EXACT",
        tuple(mappings),
        problem_revision_id="board-r1",
        problem_revision_fingerprint="board-r1-fingerprint",
    )
    certificate = verify_solver_formulation_identity(formulation)
    assert certificate.status == "INCONCLUSIVE"
    assert certificate.verified_fidelity == "NONE"
    assert "BUILTIN_CHECKER_SUPPORTS_IDENTITY_ONLY" in certificate.diagnostics


def test_v54_bridge_rejects_approximate_provider_admission():
    model = source_model()
    translation, translation_certificate = translate_model_for_solver(
        model,
        target_family="MILP",
        target_provider_id="highs-formulation",
    )
    features = ModelFeatureSet(model.fingerprint, (ModelFeatureRequirement("BOOLEAN", "EXACT_OR_APPROXIMATE"),))
    manifest = ProviderCapabilityManifest(
        "highs-formulation",
        "1.0",
        "aasm.highs",
        "0.1.0",
        (
            ProviderFeatureSupport(
                "BOOLEAN",
                "APPROXIMATE_TRANSLATED",
                transformation_id="bool-approx",
                tolerance_policy_id="tol-1",
            ),
        ),
        solver_families=("MILP",),
    )
    admission = evaluate_model_admission(features, manifest)
    assert admission.admitted is True and admission.exact is False
    with pytest.raises(ValueError, match="requires exact provider admission"):
        formulation_from_v54_translation(
            model,
            translation,
            translation_certificate,
            feature_set=features,
            provider_manifest=manifest,
            admission_report=admission,
        )


def test_formulation_contract_never_grants_truth_and_requires_independent_nontrivial_checking():
    contract = solver_formulation_contract()
    assert contract["formulation_contract_id"] == SOLVER_FORMULATION_CONTRACT_ID
    assert contract["certificate_contract_id"] == SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID
    assert contract["v54_translation"] == "REUSED_AS_FIRST_EXACT_IDENTITY_FORMULATION"
    assert contract["nontrivial_translation_policy"] == "NO_PASS_WITHOUT_AN_INDEPENDENT_CHECKER_FOR_THE_REQUESTED_FIDELITY"
    assert contract["truth_authority"] == "NONE"
