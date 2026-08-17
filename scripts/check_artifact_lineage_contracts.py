from __future__ import annotations

from pathlib import Path
import json
import sys


def fail(message: str, path: Path | None = None) -> None:
    location = f" file={path}" if path is not None else ""
    safe = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error{location}::{safe}", file=sys.stderr)
    raise SystemExit(message)


def require(path: Path, tokens) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        fail(f"missing required artifact-lineage contract tokens: {missing}", path)


def forbid(path: Path, tokens) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    if present:
        fail(f"forbidden artifact-lineage implementation tokens: {present}", path)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    model = root / "src/aasm/artifact_lineage.py"
    runtime = root / "src/aasm/artifact_lineage_runtime.py"
    schema_path = root / "schemas/artifact-revision.schema.json"
    foundation_tests = root / "tests/test_artifact_lineage_foundation.py"
    runtime_tests = root / "tests/test_artifact_lineage_runtime.py"
    envelope_tests = root / "tests/test_artifact_lineage_envelope.py"
    active_runtime = root / "src/aasm/runtime_v56_foundation.py"
    public_active = root / "src/aasm/public_active.py"

    require(model, [
        'ARTIFACT_REVISION_CONTRACT_ID = "aasm.artifact.revision.v1"',
        'ARTIFACT_REVISION_CONTRACT_VERSION = "0.3.0"',
        '"revision_identity": "BACKEND_INDEPENDENT_CONTENT_HASH_SEMANTIC_HASH_AND_PROVENANCE_BOUND"',
        '"parent_identity": "EXACT_PARENT_REVISION_ID_AND_FINGERPRINT_BINDINGS"',
        '"revision_relation": "EXPLICIT_NOT_INFERRED_FROM_RECENCY"',
        '"authority": "NONE_GRANTED_BY_ARTIFACT_REVISION"',
        '"truth_authority": "EXISTING_AASM_ADMISSION_PATH_ONLY"',
        '"current_artifact_pointer": "NONE"',
        '"parallel_artifact_registry": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        "parent_revision_fingerprints",
        "environment_fingerprint",
        "storage_binding_fingerprint",
    ])
    require(runtime, [
        'ARTIFACT_LINEAGE_RUNTIME_CONTRACT_ID = "aasm.artifact-lineage.runtime.v1"',
        '"durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"',
        '"recording_authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"',
        '"evidence_envelope": "DETERMINISTIC_ID_OBJECT_ID_OBJECT_FINGERPRINT_AND_CANONICAL_STATEMENT"',
        '"scope_binding": "WORKSPACE_AND_SCOPE_BOUND_TO_DURABLE_REVISION_RECORD"',
        '"storage_rebinding": "APPEND_ONLY_EVIDENCE_BINDING_NOT_REVISION_MUTATION"',
        '"heads": "QUERY_PROJECTION_ONLY_NOT_ACCEPTANCE_OR_AUTHORITY"',
        '"newest_revision_authority": "NONE"',
        '"artifact_acceptance": "NONE_DEFINED_BY_RUNTIME"',
        '"fact_authority_creation": "NONE"',
        '"source_trust_creation": "NONE"',
        '"effect_authorization": "NONE"',
        '"effect_dispatch": "NONE"',
        '"current_artifact_pointer": "NONE"',
        '"parallel_artifact_registry": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"hidden_wall_clock": "NONE"',
        '"runtime_admission": "ACTIVE_ENGINE_CANDIDATE_QUALIFICATION"',
        "_expected_evidence_id",
        "_require_evidence_envelope",
        "authorize_scoped_request",
        "add_evidence_guarded",
        "semantic_evolution_report",
        "execution_environment_report",
        "project_artifact_lineage_evidence",
    ])
    require(active_runtime, [
        "from .artifact_lineage_runtime import ArtifactLineageRuntimeMixin",
        "ArtifactLineageRuntimeMixin,",
    ])
    require(runtime_tests, [
        "ArtifactLineageEngine = ActiveEngine",
        "test_real_active_engine_exposes_candidate_runtime_without_public_adoption_claim",
        "test_runtime_records_explicit_branch_and_merge_without_selecting_authority",
        "test_runtime_rejects_forged_parent_fingerprint_and_second_created_root",
        "test_runtime_rejects_stale_problem_revision_missing_or_invalidated_source_evidence",
        "test_runtime_verifies_content_and_semantic_projection_hashes",
        "test_storage_rebinding_appends_binding_without_mutating_revision",
        "test_storage_rebinding_and_parent_lineage_cannot_cross_scope",
        "test_duplicate_content_with_different_provenance_remains_distinguishable",
        "test_sqlite_restart_reconstructs_identical_lineage_projection",
    ])
    require(envelope_tests, [
        "test_storage_binding_rejects_forged_metadata_object_fingerprint",
        "test_storage_binding_rejects_forged_deterministic_evidence_id",
        "test_storage_binding_requires_derivation_from_canonical_revision_evidence",
        "test_artifact_lineage_rejects_noncanonical_statement_and_firewall_metadata",
    ])
    require(foundation_tests, [
        "requires_exact_parent_id_fingerprint_and_stable_logical_identity",
        "revision_relation_is_explicit_and_merge_requires_complete_multiple_parent_set",
        "competing_children_are_distinct_legal_branches_not_implicit_authority",
    ])

    forbid(model, [
        "AASMEngine", "EvidenceRecord", "EvidenceLedger", "add_evidence", "authorize_effect(",
        "execute_effect(", "register_fact_authority(", "record_state_claim(", "TextPCB", "TEXTPCB",
        "time.time(", "time_ns(", "datetime.now(", "pickle", "MemoryArtifactBackend(",
        "LocalDirectoryArtifactBackend(", "ArtifactBackendRegistry(",
    ])
    forbid(runtime, [
        "register_fact_authority(", "record_source_trust(", "authorize_effect(", "execute_effect(",
        "dispatch_effect(", "record_state_claim(", "patch_snapshot(", "snapshot.resources",
        "external_artifacts", "current_artifact =", "current_entity_state =", "time.time(",
        "time_ns(", "datetime.now(", "datetime.utcnow(", "TextPCB", "TEXTPCB", "pickle",
    ])
    forbid(runtime_tests, ["class PreAdmissionArtifactLineageEngine"])
    forbid(public_active, [
        "from .artifact_lineage import",
        "from .artifact_lineage_runtime import",
        '"record_artifact_revision"',
        '"artifact_lineage_report"',
        '"artifact_revision_report"',
    ])

    model_text = model.read_text(encoding="utf-8")
    identity_body = model_text[model_text.index("def identity_payload"):model_text.index("def storage_binding_payload")]
    if '"artifact_ref"' in identity_body:
        fail("portable artifact revision identity must not contain artifact_ref", model)

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("artifact revision schema must use JSON Schema 2020-12", schema_path)
    if schema.get("additionalProperties") is not False:
        fail("artifact revision schema must fail closed on unknown fields", schema_path)
    required = set(schema.get("required") or ())
    for name in (
        "revision_id", "logical_artifact_id", "content_sha256", "semantic_projection_sha256",
        "parent_revision_ids", "parent_revision_fingerprints", "revision_relation", "producer_id",
        "format_id", "environment_id", "environment_fingerprint", "evidence_ids", "fingerprint",
        "storage_binding_fingerprint",
    ):
        if name not in required:
            fail(f"artifact revision schema is missing required field: {name}", schema_path)

    sys.path.insert(0, str(root / "src"))
    from aasm import AASMEngine
    from aasm.artifact_lineage import artifact_lineage_contract
    from aasm.artifact_lineage_runtime import artifact_lineage_runtime_contract
    from aasm.public_active import PUBLIC_API_CONTRACT

    model_contract = artifact_lineage_contract()
    runtime_contract = artifact_lineage_runtime_contract()
    if model_contract["authority"] != "NONE_GRANTED_BY_ARTIFACT_REVISION":
        fail("artifact revision acquired authority semantics", model)
    if model_contract["parallel_artifact_registry"] != "NONE":
        fail("artifact revision introduced a parallel artifact registry", model)
    if runtime_contract["durability"] != "EXISTING_AASM_EVIDENCE_EVENT_REPLAY":
        fail("artifact lineage bypassed existing durable Evidence/replay", runtime)
    if runtime_contract["runtime_admission"] != "ACTIVE_ENGINE_CANDIDATE_QUALIFICATION":
        fail("artifact lineage is not at the active-engine candidate boundary", runtime)
    if runtime_contract["newest_revision_authority"] != "NONE" or runtime_contract["artifact_acceptance"] != "NONE_DEFINED_BY_RUNTIME":
        fail("artifact lineage acquired recency or acceptance authority", runtime)
    for name in ("record_artifact_revision", "artifact_revision_report", "artifact_lineage_report"):
        if not callable(getattr(AASMEngine, name, None)):
            fail(f"real imported AASMEngine is missing candidate artifact-lineage method: {name}", active_runtime)
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.13":
        fail("candidate composition must not advance public adoption before qualification", public_active)

    print("S3 artifact revision active-engine candidate source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
