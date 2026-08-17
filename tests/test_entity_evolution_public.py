from __future__ import annotations

import aasm
from aasm import public_active as parent
from aasm import public_active_entity_evolution as candidate
from aasm.entity_evolution import ENTITY_EVOLUTION_RELATIONS


def test_entity_public_candidate_is_additive_over_active_parent():
    parent_report = parent.validate_public_api_contract()
    candidate_report = candidate.validate_public_api_contract()
    assert parent_report["valid"], parent_report
    assert candidate_report["valid"], candidate_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.14"
    assert candidate.PUBLIC_API_CONTRACT["contract_version"] == "0.32.15"
    assert candidate.AASMEngine is parent.AASMEngine
    assert candidate.AASMEngine is aasm.AASMEngine
    assert set(parent.SUPPORTED_ENGINE_METHODS).issubset(candidate.SUPPORTED_ENGINE_METHODS)
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(candidate.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(candidate.SUPPORTED_INSPECTION_SURFACES)


def test_entity_public_candidate_exports_exact_semantic_and_runtime_contracts():
    contract = candidate.public_api_contract()
    entity = contract["entity_evolution"]
    runtime = entity["runtime"]
    assert entity["contract_id"] == candidate.ENTITY_EVOLUTION_CONTRACT_ID
    assert tuple(entity["relations"]) == ENTITY_EVOLUTION_RELATIONS
    assert entity["ambiguous_mapping"] == "FAIL_CLOSED_FOR_HARD_REUSE_OR_AUTOMATIC_IDENTITY_TRANSFER"
    assert entity["parallel_entity_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert entity["current_entity_state_pointer"] == "NONE"
    assert runtime["contract_id"] == candidate.ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID
    assert runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"
    assert runtime["recording_authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert runtime["artifact_revision_source"] == "EXISTING_ARTIFACT_LINEAGE_PROJECTION_ONLY"
    assert runtime["artifact_revision_binding"] == "EXACT_ID_AND_FINGERPRINT_REQUIRED"
    assert runtime["ambiguity"] == "RECORDED_EXPLICITLY_AND_FAIL_CLOSED_FOR_HARD_AUTOMATIC_REUSE"
    assert runtime["parallel_entity_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert runtime["parallel_current_state_store"] == "NONE"
    assert runtime["runtime_admission"] == "ACTIVE_ENGINE_QUALIFIED"


def test_entity_public_candidate_exposes_no_authority_or_current_state_shortcut():
    entity = candidate.PUBLIC_API_CONTRACT["entity_evolution"]
    runtime = entity["runtime"]
    for key in (
        "artifact_authority",
        "physical_state_authority",
        "external_state_authority",
        "fact_authority_creation",
        "source_trust_creation",
        "effect_authorization",
        "effect_dispatch",
        "current_entity_state_pointer",
    ):
        assert entity[key] == "NONE"
    for key in (
        "artifact_authority",
        "physical_state_authority",
        "external_state_authority",
        "fact_authority_creation",
        "source_trust_creation",
        "effect_authorization",
        "effect_dispatch",
        "state_claim_creation",
        "current_entity_state_pointer",
    ):
        assert runtime[key] == "NONE"
    assert runtime["heads"] == "QUERY_PROJECTION_ONLY_NEVER_CURRENT_STATE_OR_AUTHORITY"
    assert "entity-evolution" in candidate.SUPPORTED_INSPECTION_SURFACES


def test_entity_public_candidate_engine_methods_are_real_active_engine_methods():
    for name in (
        "entity_evolution_runtime_contract_report",
        "record_entity_evolution",
        "entity_evolution_event_report",
        "entity_evolution_report",
        "entity_evolutions_report",
    ):
        assert name in candidate.SUPPORTED_ENGINE_METHODS
        assert callable(getattr(candidate.AASMEngine, name, None))


def test_entity_public_adoption_is_top_level_after_qualification():
    report = aasm.validate_public_api_contract()
    assert report["valid"], report
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.15"
    assert aasm.AASMEngine is candidate.AASMEngine
    assert aasm.ENTITY_EVOLUTION_CONTRACT_ID == candidate.ENTITY_EVOLUTION_CONTRACT_ID
    assert aasm.ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID == candidate.ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID
