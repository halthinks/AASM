from __future__ import annotations

import aasm
import aasm.public_active_engineering_rule as parent
import aasm.public_active_semantic_projection as active


def test_semantic_projection_public_adoption_is_additive_over_qualified_rule_parent():
    parent_report = parent.validate_public_api_contract()
    active_report = active.validate_public_api_contract()
    assert parent_report["valid"] is True, parent_report
    assert active_report["valid"] is True, active_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.17"
    assert active.PUBLIC_API_CONTRACT["contract_version"] == "0.32.18"
    assert active.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.17"
    assert active.AASMEngine is parent.AASMEngine
    assert active.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert active_report["active_root_status"] == "ACTIVE_QUALIFIED_PUBLIC_ROOT"


def test_semantic_projection_remains_qualified_03218_parent_beneath_active_03219():
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.18"
    assert aasm.AASMEngine is parent.AASMEngine
    assert active.PUBLIC_API_CONTRACT["contract_version"] == "0.32.18"
    assert active.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.17"
    assert active.public_api_contract()["semantic_projection"]["active_root_status"] == "ACTIVE_QUALIFIED_PUBLIC_ROOT"
    assert aasm.public_api_contract()["semantic_projection"] == active.public_api_contract()["semantic_projection"]
    assert aasm.validate_public_api_contract()["valid"] is True
    assert hasattr(aasm, "SemanticProjectionDefinition")
    assert hasattr(aasm, "SemanticEquivalenceAssessment")
    assert hasattr(aasm, "InvariantRef")


def test_semantic_projection_public_adoption_preserves_full_parent_import_surface():
    for name in parent.SUPPORTED_PUBLIC_IMPORTS:
        assert name in active.SUPPORTED_PUBLIC_IMPORTS, name
        assert hasattr(active, name), name
        assert hasattr(aasm, name), name
    assert active.PUBLIC_API_CONTRACT["supported_imports"] == active.SUPPORTED_PUBLIC_IMPORTS
    assert set(active.SUPPORTED_PUBLIC_IMPORTS).issubset(aasm.SUPPORTED_PUBLIC_IMPORTS)


def test_semantic_projection_public_adoption_adds_ir_without_engine_methods():
    required = (
        "SEMANTIC_PROJECTION_CONTRACT_ID",
        "SEMANTIC_EQUIVALENCE_CONTRACT_ID",
        "INVARIANT_CONTRACT_ID",
        "InvariantRef",
        "SemanticSubjectRef",
        "SemanticProjectionDefinition",
        "SemanticProjectionResult",
        "SemanticEquivalenceAssessment",
        "assess_semantic_equivalence",
        "invariant_contract",
        "semantic_projection_contract",
    )
    for name in required:
        assert name in active.SUPPORTED_PUBLIC_IMPORTS, name
        assert hasattr(active, name), name
        assert hasattr(aasm, name), name
    assert "semantic-projection" in active.SUPPORTED_INSPECTION_SURFACES
    assert active.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert aasm.SUPPORTED_ENGINE_METHODS == active.SUPPORTED_ENGINE_METHODS
    assert not any(name.startswith("semantic_projection_") for name in active.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("semantic_equivalence_") for name in active.SUPPORTED_ENGINE_METHODS)


def test_semantic_projection_public_claim_ceiling_and_invariant_classes_remain_strict():
    semantic = active.public_api_contract()["semantic_projection"]
    assert semantic["contract_id"] == "aasm.semantic.projection.v1"
    assert semantic["equivalence_contract_id"] == "aasm.semantic.equivalence.v1"
    assert semantic["invariant_contract_id"] == "aasm.invariant.v1"
    assert semantic["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert semantic["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert semantic["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert semantic["active_root_status"] == "ACTIVE_QUALIFIED_PUBLIC_ROOT"
    assert semantic["parallel_projection_registry"] == "NONE"
    assert semantic["current_projection_pointer"] == "NONE"
    assert semantic["existing_reuse_certified_equivalent"] == "NOT_REINTERPRETED_OR_ADMITTED_BY_FOUNDATION"
    assert semantic["invariant_contract"]["classifications"] == [
        "REPRESENTATIONAL",
        "STATIC_PROTOCOL",
        "DYNAMIC_KERNEL",
        "EMPIRICAL",
    ]
    assert semantic["invariant_contract"]["projection_preservation_is_proof"] is False
    assert semantic["invariant_contract"]["representational_equivalence_proves_dynamic_kernel"] is False
    assert semantic["invariant_contract"]["representational_equivalence_proves_empirical"] is False
    assert all(value == "NONE" for value in semantic["public_claim_ceiling"].values())
    assert aasm.public_api_contract()["semantic_projection"] == semantic


def test_semantic_projection_public_types_are_deterministic_and_projection_relative():
    definition = aasm.SemanticProjectionDefinition(
        projection_name="active-logical-board",
        source_type_ids=("textpcb.board.alternative.v1",),
        target_type_id="textpcb.logical-board.v1",
        purpose="active public semantic comparison",
        fidelity="LOSSLESS",
        invariants=(
            aasm.InvariantRef("board.connectivity", "REPRESENTATIONAL"),
            aasm.InvariantRef("board.constraint-shape", "STATIC_PROTOCOL"),
        ),
    )
    left_subject = aasm.SemanticSubjectRef(
        "textpcb.board.alternative.v1", "left", "a" * 64, "revision-1", "1" * 64
    )
    right_subject = aasm.SemanticSubjectRef(
        "textpcb.board.alternative.v1", "right", "b" * 64, "revision-1", "1" * 64
    )
    left = aasm.SemanticProjectionResult(
        definition.projection_id, definition.fingerprint, left_subject, "PROJECTED", "f" * 64
    )
    right = aasm.SemanticProjectionResult(
        definition.projection_id, definition.fingerprint, right_subject, "PROJECTED", "f" * 64
    )
    assessment = aasm.assess_semantic_equivalence(definition, left, right)
    assert assessment.relation == "PROJECTION_EQUIVALENT"
    assert assessment.relation != "EXACT_IDENTITY"
    assert aasm.SemanticEquivalenceAssessment.from_dict(assessment.to_dict()) == assessment
