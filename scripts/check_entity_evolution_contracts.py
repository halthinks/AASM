from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing required entity-evolution file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    model = text("src/aasm/entity_evolution.py")
    runtime = text("src/aasm/entity_evolution_runtime.py")
    schema_text = text("schemas/entity-evolution.schema.json")
    tests = text("tests/test_entity_evolution.py")
    active_tests = text("tests/test_entity_evolution_active_engine.py")
    public_tests = text("tests/test_entity_evolution_public.py")
    foundation = text("src/aasm/runtime_v56_foundation.py")
    parent_public = text("src/aasm/public_active.py")
    candidate_public = text("src/aasm/public_active_entity_evolution.py")
    package_init = text("src/aasm/__init__.py")

    schema = json.loads(schema_text)
    require(schema["properties"]["contract_id"]["const"] == "aasm.entity.evolution.v1", "entity evolution schema contract ID drift")
    require(schema["properties"]["contract_version"]["const"] == "0.1.0", "entity evolution schema version drift")

    required_model_tokens = [
        'ENTITY_EVOLUTION_CONTRACT_ID = "aasm.entity.evolution.v1"',
        'ENTITY_EVOLUTION_CONTRACT_VERSION = "0.1.0"',
        '"UNCHANGED"',
        '"MODIFIED"',
        '"GENERATED"',
        '"SPLIT"',
        '"MERGED"',
        '"REPLACED"',
        '"DELETED"',
        '"AMBIGUOUS"',
        '"FAIL_CLOSED_FOR_HARD_REUSE_OR_AUTOMATIC_IDENTITY_TRANSFER"',
        '"current_entity_state_pointer": "NONE"',
        '"parallel_entity_registry": "NONE_EVIDENCE_PROJECTION_ONLY"',
    ]
    for token in required_model_tokens:
        require(token in model, f"entity evolution model contract missing token: {token}")

    required_runtime_tokens = [
        'ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID = "aasm.entity-evolution.runtime.v1"',
        'ENTITY_EVOLUTION_CAPABILITIES = {"evolution_record": "entity.evolution.record"}',
        '"artifact_revision_source": "EXISTING_ARTIFACT_LINEAGE_PROJECTION_ONLY"',
        '"artifact_revision_binding": "EXACT_ID_AND_FINGERPRINT_REQUIRED"',
        '"ambiguity": "RECORDED_EXPLICITLY_AND_FAIL_CLOSED_FOR_HARD_AUTOMATIC_REUSE"',
        '"parallel_entity_registry": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"parallel_current_state_store": "NONE"',
        '"hidden_wall_clock": "NONE"',
        '"runtime_admission": "ACTIVE_ENGINE_QUALIFIED"',
        "project_artifact_lineage_evidence",
        "add_evidence_guarded",
        "authorize_scoped_request",
    ]
    for token in required_runtime_tokens:
        require(token in runtime, f"entity evolution runtime contract missing token: {token}")

    banned_runtime_tokens = [
        "FactAuthority(",
        "StateClaim(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "datetime.now(",
        "time.time(",
        "current_entity_store",
        "current_entity_state =",
        "latest_is_authoritative",
    ]
    for token in banned_runtime_tokens:
        require(token not in runtime, f"entity evolution runtime violates source firewall with token: {token}")

    required_test_tokens = [
        "test_runtime_records_modified_entity_without_minting_authority",
        "test_runtime_supports_explicit_split_and_merge_without_identity_collapse",
        "test_ambiguous_mapping_is_durable_and_blocks_hard_reuse",
        "test_runtime_rejects_forged_artifact_revision_fingerprint",
        "test_runtime_rejects_unrelated_artifact_lineages",
        "test_runtime_rejects_non_descendant_successor_revision",
        "test_runtime_rejects_invalidated_source_evidence",
        "test_projection_rejects_forged_entity_evolution_envelope",
        "test_sqlite_restart_reconstructs_identical_entity_evolution_projection",
    ]
    for token in required_test_tokens:
        require(token in tests, f"entity evolution adversarial corpus missing test: {token}")

    require("from .entity_evolution_runtime import EntityEvolutionRuntimeMixin" in foundation, "entity evolution runtime is not imported by active foundation")
    require("EntityEvolutionRuntimeMixin," in foundation, "entity evolution runtime is not composed into active AASMEngine")
    require("from aasm import AASMEngine as ActiveEngine" in active_tests, "active-engine corpus does not import exported AASMEngine")
    require("corpus.EntityEvolutionEngine = ActiveEngine" in active_tests, "active-engine corpus does not rebind the full adversarial corpus")
    require("test_active_engine_composes_entity_evolution_runtime" in active_tests, "active-engine composition assertion is missing")

    # The parent public surface remains immutable while 0.32.15 is qualified.
    require('"contract_version": "0.32.14"' in parent_public, "entity public candidate parent adoption drift")
    require("ENTITY_EVOLUTION_CONTRACT_ID" not in parent_public, "entity evolution leaked into the 0.32.14 parent surface")
    require('"record_entity_evolution"' not in parent_public, "entity evolution method leaked into the 0.32.14 parent surface")
    require("public_active_entity_evolution" in package_init, "qualified entity evolution overlay is not the package root")

    required_candidate_tokens = [
        '"contract_version": "0.32.15"',
        "ENTITY_EVOLUTION_CONTRACT_ID",
        "ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID",
        "EntityRepresentationRef",
        "EntityEvolution",
        "entity_evolution_contract",
        "entity_evolution_runtime_contract",
        "project_entity_evolution_evidence",
        '"entity-evolution"',
        '"entity_evolution_runtime_contract_report"',
        '"record_entity_evolution"',
        '"entity_evolution_event_report"',
        '"entity_evolution_report"',
        '"entity_evolutions_report"',
        '"FAIL_CLOSED_FOR_HARD_REUSE_OR_AUTOMATIC_IDENTITY_TRANSFER"',
        '"NONE_EVIDENCE_PROJECTION_ONLY"',
        '"QUERY_PROJECTION_ONLY_NEVER_CURRENT_STATE_OR_AUTHORITY"',
    ]
    for token in required_candidate_tokens:
        require(token in candidate_public, f"entity evolution public candidate missing token: {token}")

    required_public_test_tokens = [
        "test_entity_public_candidate_is_additive_over_active_parent",
        "test_entity_public_candidate_exports_exact_semantic_and_runtime_contracts",
        "test_entity_public_candidate_exposes_no_authority_or_current_state_shortcut",
        "test_entity_public_candidate_engine_methods_are_real_active_engine_methods",
        "test_entity_public_adoption_is_top_level_after_qualification",
    ]
    for token in required_public_test_tokens:
        require(token in public_tests, f"entity evolution public candidate corpus missing test: {token}")

    print("entity evolution active-engine + active-public source contracts: PASS")


if __name__ == "__main__":
    main()
