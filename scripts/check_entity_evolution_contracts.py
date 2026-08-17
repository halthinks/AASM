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
    foundation = text("src/aasm/runtime_v56_foundation.py")
    public = text("src/aasm/public_active.py")

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
        '"ambiguity": "RECORDED_EXPLICITLY_AND_FAIL_CLOSED_FOR_HARD_AUTOMATIC_REUSE"',
        '"parallel_entity_registry": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"parallel_current_state_store": "NONE"',
        '"hidden_wall_clock": "NONE"',
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

    # This checker is the pre-admission firewall. Promotion deliberately flips
    # these expectations only after this gate is green and the real-engine corpus
    # is rerun against from aasm import AASMEngine.
    require("EntityEvolutionRuntimeMixin" not in foundation, "entity evolution runtime was composed before pre-admission qualification")
    require("ENTITY_EVOLUTION_CONTRACT_ID" not in public, "entity evolution public surface was exposed before pre-admission qualification")
    require("record_entity_evolution" not in public, "entity evolution public method was exposed before pre-admission qualification")

    print("entity evolution pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
