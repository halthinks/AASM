from __future__ import annotations

import json
from pathlib import Path

import aasm
from aasm.model import ProblemSpec
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
from aasm.optimization import OptimizationConstraint, OptimizationModel, OptimizationObjective, OptimizationVariable
from aasm.runtime_v54 import translate_model_for_solver
from aasm.runtime_v55_foundation import AASMEngine
from aasm.semantic_evolution import (
    EXTERNAL_REFERENCE_CONTRACT_ID,
    PROBLEM_DELTA_CONTRACT_ID,
    PROBLEM_REVISION_CONTRACT_ID,
    ExternalReference,
    ProblemDelta,
    ProblemRevision,
    semantic_evolution_contract,
    validate_revision_transition,
)
from aasm.solver_formulation import (
    SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID,
    SOLVER_FORMULATION_CONTRACT_ID,
    FormulationExternalReferenceBinding,
    formulation_from_v54_translation,
    solver_formulation_contract,
)
from aasm._runtime_v55_semantic_evolution import (
    SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_ID,
    semantic_evolution_runtime_contract,
)


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load_schema(name: str) -> dict:
    path = ROOT / "schemas" / name
    require(path.is_file(), f"missing v0.55 schema: {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_source_doctrine() -> None:
    for rel in (
        "docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md",
        "docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md",
        "docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md",
        "docs/source_material/SOURCE_LOCK_MANIFEST.md",
    ):
        require((ROOT / rel).is_file(), f"missing canonical governed-semantic-evolution source: {rel}")
    lock = (ROOT / "docs/source_material/SOURCE_LOCK_MANIFEST.md").read_text(encoding="utf-8")
    require("59340a1620bc4be7b20c981fb6fb023c79e44862a35e84d7564ff86375efd560" in lock, "TextPCB requirements source hash missing from source lock")
    require("7e58621fcba1b90c70bf9da4f64913845cc6648b343095429f4d2992a3c1531c" in lock, "TextPCB builder-gap source hash missing from source lock")
    require("No-drift rules" in lock, "source lock must preserve explicit no-drift rules")


def check_active_release_boundary() -> None:
    require(aasm.__version__ == "0.54.0", "development v0.55 foundation must not silently replace the released v0.54 package surface")
    init_text = (ROOT / "src/aasm/__init__.py").read_text(encoding="utf-8")
    require("from .public_v54 import *" in init_text, "active public package must remain frozen on public_v54 until v0.55 release gating")


def check_contracts_and_schemas() -> None:
    semantic = semantic_evolution_contract()
    runtime = semantic_evolution_runtime_contract()
    features = model_feature_contract()
    formulation = solver_formulation_contract()
    require(semantic["external_reference_contract_id"] == EXTERNAL_REFERENCE_CONTRACT_ID, "external reference contract drift")
    require(semantic["problem_revision_contract_id"] == PROBLEM_REVISION_CONTRACT_ID, "problem revision contract drift")
    require(semantic["problem_delta_contract_id"] == PROBLEM_DELTA_CONTRACT_ID, "problem delta contract drift")
    require(semantic["truth_authority"] == "EXISTING_AASM_ADMISSION_PATH_ONLY", "semantic evolution may not create truth authority")
    require(runtime["contract_id"] == SEMANTIC_EVOLUTION_RUNTIME_CONTRACT_ID, "semantic evolution runtime contract drift")
    require(runtime["parallel_revision_table"] == "NONE", "v0.55 must not add a parallel revision truth table")
    require(runtime["parallel_change_impact_graph"] == "NONE", "v0.55 must reuse semantic dependency truth maintenance")
    require(runtime["revision_record_grants_truth"] is False, "problem revision Evidence cannot self-grant truth")
    require(features["feature_set_contract_id"] == MODEL_FEATURE_SET_CONTRACT_ID, "model feature-set contract drift")
    require(features["provider_manifest_contract_id"] == PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID, "provider manifest contract drift")
    require(features["admission_contract_id"] == MODEL_ADMISSION_CONTRACT_ID, "model admission contract drift")
    require(features["unsupported_feature_policy"] == "FAIL_CLOSED_BEFORE_PROVIDER_EXECUTION", "unsupported features must fail before provider execution")
    require(features["truth_authority"] == "NONE", "provider capability evidence may not create truth authority")
    require(formulation["formulation_contract_id"] == SOLVER_FORMULATION_CONTRACT_ID, "solver formulation contract drift")
    require(formulation["certificate_contract_id"] == SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID, "solver formulation certificate drift")
    require(formulation["builtin_checker_scope"] == "EXACT_IDENTITY_ONLY", "built-in formulation checker must not overclaim nontrivial translations")
    require(formulation["nontrivial_translation_policy"] == "NO_PASS_WITHOUT_AN_INDEPENDENT_CHECKER_FOR_THE_REQUESTED_FIDELITY", "nontrivial formulation checking must fail closed")
    require(formulation["truth_authority"] == "NONE", "solver formulation evidence may not create truth authority")

    schema_contracts = {
        "external-reference.schema.json": EXTERNAL_REFERENCE_CONTRACT_ID,
        "problem-revision.schema.json": PROBLEM_REVISION_CONTRACT_ID,
        "problem-delta.schema.json": PROBLEM_DELTA_CONTRACT_ID,
        "model-feature-set.schema.json": MODEL_FEATURE_SET_CONTRACT_ID,
        "provider-capability-manifest.schema.json": PROVIDER_CAPABILITY_MANIFEST_CONTRACT_ID,
        "model-admission-report.schema.json": MODEL_ADMISSION_CONTRACT_ID,
        "solver-formulation.schema.json": SOLVER_FORMULATION_CONTRACT_ID,
        "solver-formulation-certificate.schema.json": SOLVER_FORMULATION_CERTIFICATE_CONTRACT_ID,
    }
    for schema_name, contract_id in schema_contracts.items():
        schema = load_schema(schema_name)
        require(schema["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {schema_name}")


def check_reference_transition() -> None:
    base = ProblemRevision(
        problem_id="v55-contract-fixture",
        problem_fingerprint="problem-1",
        semantic_projection_fingerprint="semantic-1",
        revision_id="v55-r1",
    )
    delta = ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint="problem-2",
        target_semantic_projection_fingerprint="semantic-2",
    )
    target = ProblemRevision(
        problem_id=base.problem_id,
        problem_fingerprint="problem-2",
        semantic_projection_fingerprint="semantic-2",
        parent_revision_ids=(base.revision_id,),
        created_from_delta_id=delta.delta_id,
        revision_id="v55-r2",
    )
    require(validate_revision_transition(base, delta, target)["valid"], "reference problem revision transition must validate")
    engine = AASMEngine(ProblemSpec("v0.55 contract fixture"))
    engine.register_initial_problem_revision(base, authority_id="v55-policy", authority_class="POLICY")
    engine.commit_problem_revision_transition(delta, target, authority_id="v55-policy", authority_class="POLICY")
    require(engine.require_usable_problem_revision(base.problem_id)["revision_id"] == target.revision_id, "durable v0.55 runtime failed to advance the canonical revision head")
    require(engine.replay().canonical_hash() == engine.snapshot.canonical_hash(), "v0.55 revision history must replay to the persisted canonical state")


def check_model_admission() -> None:
    feature_set = ModelFeatureSet(
        model_fingerprint="v55-model",
        features=(
            ModelFeatureRequirement("BOOLEAN", "EXACT_ONLY"),
            ModelFeatureRequirement("PSEUDO_BOOLEAN", "EXACT_ONLY"),
        ),
    )
    manifest = ProviderCapabilityManifest(
        provider_id="v55-provider",
        provider_version="1",
        adapter_id="v55-adapter",
        adapter_version="1",
        feature_support=(
            ProviderFeatureSupport("BOOLEAN", "EXACT_NATIVE"),
            ProviderFeatureSupport("PSEUDO_BOOLEAN", "EXACT_TRANSLATED", transformation_id="pb-exact-v1"),
        ),
    )
    report = evaluate_model_admission(feature_set, manifest)
    require(report.admitted and report.exact, "exact reference feature set should be admitted exactly")

    approximate_manifest = ProviderCapabilityManifest(
        provider_id="v55-approx-provider",
        provider_version="1",
        adapter_id="v55-approx-adapter",
        adapter_version="1",
        feature_support=(
            ProviderFeatureSupport(
                "PSEUDO_BOOLEAN",
                "APPROXIMATE_TRANSLATED",
                transformation_id="pb-approx-v1",
                tolerance_policy_id="tol-v1",
            ),
        ),
    )
    rejected = evaluate_model_admission(
        ModelFeatureSet(model_fingerprint="v55-model-2", features=(ModelFeatureRequirement("PSEUDO_BOOLEAN", "EXACT_ONLY"),)),
        approximate_manifest,
    )
    require(not rejected.admitted, "approximate provider support must fail closed when exact semantics are required")


def check_formulation_bridge() -> None:
    model = OptimizationModel(
        "v55-formulation-fixture",
        (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
        (
            OptimizationConstraint(
                "LINEAR",
                coefficients={"x": 1, "y": 1},
                sense="<=",
                rhs=1,
                constraint_id="requirement-capacity",
            ),
        ),
        objective=OptimizationObjective("MINIMIZE", {"x": 1, "y": 2}),
    )
    translation, translation_certificate = translate_model_for_solver(
        model,
        target_family="MILP",
        target_provider_id="v55-highs",
    )
    features = ModelFeatureSet(model.fingerprint, (ModelFeatureRequirement("BOOLEAN", "EXACT_ONLY"),))
    manifest = ProviderCapabilityManifest(
        "v55-highs",
        "1",
        "aasm.highs",
        "1",
        (ProviderFeatureSupport("BOOLEAN", "EXACT_NATIVE"),),
        solver_families=("MILP",),
    )
    admission = evaluate_model_admission(features, manifest)
    reference = ExternalReference("textpcb.requirement", "REQ-CAP-1", "HARD_REQUIREMENT", revision="1")
    binding = FormulationExternalReferenceBinding(
        reference,
        "CONSTRAINT",
        "requirement-capacity",
        "CONSTRAINT",
        ("requirement-capacity",),
    )
    formulation, certificate = formulation_from_v54_translation(
        model,
        translation,
        translation_certificate,
        feature_set=features,
        provider_manifest=manifest,
        admission_report=admission,
        external_reference_bindings=(binding,),
    )
    require(certificate.status == "PASS" and certificate.verified_fidelity == "EXACT", "v0.54 exact translation must bridge to an independently checked exact formulation")
    require(certificate.mapping_complete and certificate.external_references_resolved, "formulation bridge must preserve complete object and external-reference lineage")
    require(formulation.predecessor_translation_id == translation.translation_id, "formulation must preserve v0.54 translation ancestry")


def main() -> None:
    check_source_doctrine()
    check_active_release_boundary()
    check_contracts_and_schemas()
    check_reference_transition()
    check_model_admission()
    check_formulation_bridge()
    print("v0.55 governed semantic evolution foundation contracts: PASS")


if __name__ == "__main__":
    main()
