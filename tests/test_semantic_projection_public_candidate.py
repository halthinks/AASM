from __future__ import annotations

import aasm
import aasm.public_active_engineering_rule as parent
import aasm.public_active_semantic_projection as candidate


def test_semantic_projection_public_candidate_advances_only_candidate_overlay():
    parent_report = parent.validate_public_api_contract()
    candidate_report = candidate.validate_public_api_contract()
    assert parent_report["valid"] is True, parent_report
    assert candidate_report["valid"] is True, candidate_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.17"
    assert candidate.PUBLIC_API_CONTRACT["contract_version"] == "0.32.18"
    assert candidate.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.17"
    assert candidate.AASMEngine is parent.AASMEngine
    assert candidate.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert candidate_report["active_root_status"] == "CANDIDATE_UNTIL_PACKAGE_ROOT_SWITCH"


def test_active_package_root_remains_03217_until_candidate_is_qualified():
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.17"
    assert aasm.AASMEngine is parent.AASMEngine
    assert not hasattr(aasm, "SemanticProjectionDefinition")


def test_semantic_projection_candidate_exposes_semantic_ir_without_runtime_methods():
    required = (
        "SEMANTIC_PROJECTION_CONTRACT_ID", "SEMANTIC_EQUIVALENCE_CONTRACT_ID", "INVARIANT_CONTRACT_ID",
        "InvariantRef", "SemanticSubjectRef", "SemanticProjectionDefinition", "SemanticProjectionResult",
        "SemanticEquivalenceAssessment", "assess_semantic_equivalence", "invariant_contract", "semantic_projection_contract",
    )
    for name in required:
        assert name in candidate.SUPPORTED_PUBLIC_IMPORTS, name
        assert hasattr(candidate, name), name
    assert "semantic-projection" in candidate.SUPPORTED_INSPECTION_SURFACES
    assert not any(name.startswith("semantic_projection_") for name in candidate.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("semantic_equivalence_") for name in candidate.SUPPORTED_ENGINE_METHODS)


def test_semantic_projection_candidate_contract_preserves_claim_ceiling_and_invariant_classes():
    semantic = candidate.public_api_contract()["semantic_projection"]
    assert semantic["contract_id"] == "aasm.semantic.projection.v1"
    assert semantic["equivalence_contract_id"] == "aasm.semantic.equivalence.v1"
    assert semantic["invariant_contract_id"] == "aasm.invariant.v1"
    assert semantic["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert semantic["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert semantic["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert semantic["parallel_projection_registry"] == "NONE"
    assert semantic["current_projection_pointer"] == "NONE"
    assert semantic["existing_reuse_certified_equivalent"] == "NOT_REINTERPRETED_OR_ADMITTED_BY_FOUNDATION"
    assert semantic["invariant_contract"]["classifications"] == ["REPRESENTATIONAL", "STATIC_PROTOCOL", "DYNAMIC_KERNEL", "EMPIRICAL"]
    assert semantic["invariant_contract"]["projection_preservation_is_proof"] is False
    assert semantic["invariant_contract"]["representational_equivalence_proves_dynamic_kernel"] is False
    assert semantic["invariant_contract"]["representational_equivalence_proves_empirical"] is False
    assert all(value == "NONE" for value in semantic["public_claim_ceiling"].values())


def test_semantic_projection_candidate_public_types_are_deterministic_and_relative_to_projection():
    definition = candidate.SemanticProjectionDefinition(
        projection_name="candidate-logical-board",
        source_type_ids=("textpcb.board.alternative.v1",),
        target_type_id="textpcb.logical-board.v1",
        purpose="candidate public semantic comparison",
        fidelity="LOSSLESS",
        invariants=(candidate.InvariantRef("board.connectivity", "REPRESENTATIONAL"), candidate.InvariantRef("board.constraint-shape", "STATIC_PROTOCOL")),
    )
    left_subject = candidate.SemanticSubjectRef("textpcb.board.alternative.v1", "left", "a" * 64, "revision-1", "1" * 64)
    right_subject = candidate.SemanticSubjectRef("textpcb.board.alternative.v1", "right", "b" * 64, "revision-1", "1" * 64)
    left = candidate.SemanticProjectionResult(definition.projection_id, definition.fingerprint, left_subject, "PROJECTED", "f" * 64)
    right = candidate.SemanticProjectionResult(definition.projection_id, definition.fingerprint, right_subject, "PROJECTED", "f" * 64)
    assessment = candidate.assess_semantic_equivalence(definition, left, right)
    assert assessment.relation == "PROJECTION_EQUIVALENT"
    assert assessment.relation != "EXACT_IDENTITY"
    assert candidate.SemanticEquivalenceAssessment.from_dict(assessment.to_dict()) == assessment
