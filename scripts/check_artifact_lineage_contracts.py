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
        '"content_storage": "EXISTING_AASM_ARTIFACT_BACKENDS_OR_EXTERNAL_REFERENCE"',
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
        "ExternalReference",
        "semantic_fingerprint",
        "source_problem_revision_fingerprint",
        "source_external_references",
        "evidence_ids",
    ])
    require(tests, [
        "reuses_existing_file_and_sql_blob_content_ids",
        "rejects_content_ref_digest_mismatch",
        "rejects_forged_revision_id_and_fingerprint",
        "requires_exact_id_and_fingerprint_pair",
        "requires_exact_parent_set_and_stable_logical_identity",
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
        "FileArtifactBackend(",
        "SqlBlobArtifactBackend(",
    ])
    forbid(active_runtime, [
        "artifact_lineage",
        "ArtifactRevision",
        "ArtifactLineage",
    ])

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
        "producer_id",
        "format_id",
        "evidence_ids",
        "fingerprint",
    ):
        if name not in required:
            fail(f"artifact revision schema is missing required field: {name}", schema_path)

    sys.path.insert(0, str(root / "src"))
    from aasm.artifact_lineage import artifact_lineage_contract

    contract = artifact_lineage_contract()
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

    print("S3 artifact revision pre-admission source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
