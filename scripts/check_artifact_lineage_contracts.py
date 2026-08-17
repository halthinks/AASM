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
    schema_path = root / "schemas/artifact-revision.schema.json"
    tests = root / "tests/test_artifact_lineage_foundation.py"
    active_runtime = root / "src/aasm/runtime_v56_foundation.py"

    require(model, [
        'ARTIFACT_REVISION_CONTRACT_ID = "aasm.artifact.revision.v1"',
        'ARTIFACT_REVISION_CONTRACT_VERSION = "0.3.0"',
        '"revision_identity": "BACKEND_INDEPENDENT_CONTENT_HASH_SEMANTIC_HASH_AND_PROVENANCE_BOUND"',
        '"parent_identity": "EXACT_PARENT_REVISION_ID_AND_FINGERPRINT_BINDINGS"',
        '"revision_relation": "EXPLICIT_NOT_INFERRED_FROM_RECENCY"',
        '"storage_binding_identity": "SEPARATE_FROM_REVISION_IDENTITY_AND_INTEGRITY_FINGERPRINTED"',
        '"content_storage": "EXISTING_AASM_ARTIFACT_BACKENDS_OR_EXTERNAL_REFERENCE"',
        '"artifact_ref": "NON_SEMANTIC_OPAQUE_STORAGE_BINDING_WITH_DIGEST_CHECK_WHEN_DECODABLE"',
        '"execution_environment": "EXACT_ID_AND_FINGERPRINT_WHEN_PRESENT"',
        '"authority": "NONE_GRANTED_BY_ARTIFACT_REVISION"',
        '"truth_authority": "EXISTING_AASM_ADMISSION_PATH_ONLY"',
        '"artifact_acceptance": "NOT_DEFINED_BY_FOUNDATION_CONTRACT"',
        '"generated_artifact_authority": "NONE"',
        '"successful_generation_authority": "NONE"',
        '"current_artifact_pointer": "NONE"',
        '"parallel_artifact_registry": "NONE"',
        '"parallel_truth_table": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        "parent_revision_fingerprints",
        "revision_relation",
        "environment_id",
        "environment_fingerprint",
        "refinement_run_id",
        "storage_binding_fingerprint",
        "ExternalReference",
        "semantic_fingerprint",
        "source_problem_revision_fingerprint",
        "source_external_references",
        "evidence_ids",
    ])
    require(tests, [
        "revision_identity_is_backend_independent_but_storage_binding_is_not",
        "rejects_content_ref_digest_mismatch",
        "rejects_forged_revision_semantic_and_storage_fingerprints",
        "require_exact_pairs",
        "requires_exact_parent_id_fingerprint_and_stable_logical_identity",
        "revision_relation_is_explicit_and_merge_requires_complete_multiple_parent_set",
        "competing_children_are_distinct_legal_branches_not_implicit_authority",
        "duplicate_content_with_different_provenance_produces_distinct_revision_identity",
        "denies_truth_acceptance_and_parallel_registry",
    ])

    forbid(model, [
        "AASMEngine",
        "EvidenceRecord",
        "EvidenceLedger",
        "add_evidence",
        "authorize_effect(",
        "execute_effect(",
        "register_fact_authority(",
        "record_state_claim(",
        "TextPCB",
        "TEXTPCB",
        "time.time(",
        "time_ns(",
        "datetime.now(",
        "pickle",
        "MemoryArtifactBackend(",
        "LocalDirectoryArtifactBackend(",
        "ArtifactBackendRegistry(",
    ])
    forbid(active_runtime, [
        "artifact_lineage",
        "ArtifactRevision",
        "ArtifactLineage",
    ])

    model_text = model.read_text(encoding="utf-8")
    identity_start = model_text.index("def identity_payload")
    storage_start = model_text.index("def storage_binding_payload")
    identity_body = model_text[identity_start:storage_start]
    if '"artifact_ref"' in identity_body:
        fail("portable artifact revision identity must not contain artifact_ref", model)

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        fail("artifact revision schema must use JSON Schema 2020-12", schema_path)
    if schema.get("additionalProperties") is not False:
        fail("artifact revision schema must fail closed on unknown fields", schema_path)
    required = set(schema.get("required") or ())
    for name in (
        "revision_id",
        "logical_artifact_id",
        "content_sha256",
        "semantic_projection_sha256",
        "parent_revision_ids",
        "parent_revision_fingerprints",
        "revision_relation",
        "producer_id",
        "format_id",
        "environment_id",
        "environment_fingerprint",
        "evidence_ids",
        "fingerprint",
        "storage_binding_fingerprint",
    ):
        if name not in required:
            fail(f"artifact revision schema is missing required field: {name}", schema_path)

    sys.path.insert(0, str(root / "src"))
    from aasm.artifact_lineage import artifact_lineage_contract

    contract = artifact_lineage_contract()
    if not contract["revision_identity"].startswith("BACKEND_INDEPENDENT"):
        fail("artifact revision identity remains backend-dependent", model)
    if contract["parent_identity"] != "EXACT_PARENT_REVISION_ID_AND_FINGERPRINT_BINDINGS":
        fail("artifact revision does not bind exact predecessor fingerprints", model)
    if contract["revision_relation"] != "EXPLICIT_NOT_INFERRED_FROM_RECENCY":
        fail("artifact revision relation remains implicit", model)
    if contract["authority"] != "NONE_GRANTED_BY_ARTIFACT_REVISION":
        fail("artifact revision acquired authority semantics", model)
    if contract["truth_authority"] != "EXISTING_AASM_ADMISSION_PATH_ONLY":
        fail("artifact revision introduced a new truth path", model)
    if contract["artifact_acceptance"] != "NOT_DEFINED_BY_FOUNDATION_CONTRACT":
        fail("pre-admission artifact revision contract acquired acceptance semantics", model)
    if contract["parallel_artifact_registry"] != "NONE":
        fail("artifact revision introduced a parallel artifact registry", model)
    if contract["runtime_admission"] != "PRE_ADMISSION_ONLY":
        fail("artifact revision was promoted before qualification", model)

    print("S3 artifact revision portable pre-admission source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
