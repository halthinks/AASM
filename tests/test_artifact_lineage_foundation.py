from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aasm.artifact_backends import FileArtifactBackend, SqlBlobArtifactBackend
from aasm.artifact_lineage import (
    ARTIFACT_REVISION_CONTRACT_ID,
    ArtifactRevision,
    artifact_lineage_contract,
    validate_artifact_revision_transition,
)
from aasm.semantic_evolution import ExternalReference


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _external(revision: str = "7") -> ExternalReference:
    return ExternalReference(
        namespace="engineering.requirement",
        external_id="REQ-USB-02",
        role="SOURCE_REVISION",
        revision=revision,
        source_fingerprint="sha256:abc123",
        source_location={"contract_path": "/requirements/usb/1"},
        semantic_entity_id="requirement.usb.02",
    )


def _revision(
    *,
    payload: str = "board artifact",
    logical_artifact_id: str = "board-main",
    parents=(),
    artifact_ref: str | None = None,
) -> ArtifactRevision:
    digest = _digest(payload)
    return ArtifactRevision(
        logical_artifact_id=logical_artifact_id,
        content_sha256=digest,
        semantic_projection_sha256=_digest("semantic:" + payload),
        artifact_ref=digest if artifact_ref is None else artifact_ref,
        artifact_kind="ENGINEERING_DOCUMENT",
        parent_revision_ids=tuple(parents),
        producer_id="tool:reference",
        producer_kind="TOOL",
        machine_id="machine-1",
        effect_id="effect-1",
        source_problem_revision_id="board-r7",
        source_problem_revision_fingerprint=_digest("board-r7"),
        source_external_references=(_external(),),
        format_id="text/plain",
        schema_id="example.schema.v1",
        tool_id="reference-tool",
        tool_version="1.0.0",
        external_references=(_external(),),
        evidence_ids=("evidence-source-1",),
        metadata={"purpose": "foundation-test"},
    )


def test_artifact_revision_is_deterministic_content_and_provenance_bound():
    first = _revision()
    second = ArtifactRevision.from_dict(first.to_dict())
    assert first.revision_id.startswith("artifact-revision-")
    assert first.revision_id == second.revision_id
    assert first.fingerprint == second.fingerprint
    assert second.to_dict() == first.to_dict()


def test_artifact_revision_reuses_existing_file_and_sql_blob_content_ids(tmp_path):
    payload = "same content through existing backends"
    file_ref = FileArtifactBackend(tmp_path / "files").put_text(payload)
    sql_ref = SqlBlobArtifactBackend(tmp_path / "artifacts.sqlite").put_text(payload)
    assert file_ref == sql_ref == _digest(payload)
    item = _revision(payload=payload, artifact_ref=file_ref)
    assert item.artifact_ref == item.content_sha256
    assert FileArtifactBackend(tmp_path / "files").get_text(item.artifact_ref) == payload
    assert SqlBlobArtifactBackend(tmp_path / "artifacts.sqlite").get_text(item.artifact_ref) == payload


def test_artifact_revision_rejects_content_ref_digest_mismatch():
    with pytest.raises(ValueError, match="artifact_ref content digest"):
        _revision(artifact_ref="0" * 64)


def test_artifact_revision_rejects_forged_revision_id_and_fingerprint():
    item = _revision()
    forged_id = item.to_dict()
    forged_id["revision_id"] = "artifact-revision-" + ("0" * 24)
    with pytest.raises(ValueError, match="revision_id"):
        ArtifactRevision.from_dict(forged_id)

    forged_fingerprint = item.to_dict()
    forged_fingerprint["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint"):
        ArtifactRevision.from_dict(forged_fingerprint)


def test_source_problem_revision_requires_exact_id_and_fingerprint_pair():
    item = _revision()
    payload = item.to_dict()
    payload["source_problem_revision_fingerprint"] = ""
    payload.pop("fingerprint")
    payload.pop("revision_id")
    with pytest.raises(ValueError, match="must either both be present"):
        ArtifactRevision.from_dict(payload)


def test_lineage_transition_requires_exact_parent_set_and_stable_logical_identity():
    base = _revision(payload="r1")
    child = _revision(payload="r2", parents=(base.revision_id,))
    report = validate_artifact_revision_transition((base,), child)
    assert report["valid"] is True

    wrong_identity = _revision(
        payload="r3",
        logical_artifact_id="other-artifact",
        parents=(base.revision_id,),
    )
    report = validate_artifact_revision_transition((base,), wrong_identity)
    assert report["valid"] is False
    assert "LOGICAL_ARTIFACT_ID_CHANGED" in report["errors"]

    missing_parent = _revision(payload="r4")
    report = validate_artifact_revision_transition((base,), missing_parent)
    assert report["valid"] is False
    assert "PARENT_REVISION_SET_MISMATCH" in report["errors"]


def test_contract_explicitly_denies_truth_acceptance_and_parallel_registry():
    contract = artifact_lineage_contract()
    assert contract["artifact_revision_contract_id"] == ARTIFACT_REVISION_CONTRACT_ID
    assert contract["content_storage"] == "EXISTING_AASM_ARTIFACT_BACKENDS_OR_EXTERNAL_REFERENCE"
    assert contract["authority"] == "NONE_GRANTED_BY_ARTIFACT_REVISION"
    assert contract["truth_authority"] == "EXISTING_AASM_ADMISSION_PATH_ONLY"
    assert contract["artifact_acceptance"] == "NOT_DEFINED_BY_FOUNDATION_CONTRACT"
    assert contract["generated_artifact_authority"] == "NONE"
    assert contract["successful_generation_authority"] == "NONE"
    assert contract["current_artifact_pointer"] == "NONE"
    assert contract["parallel_artifact_registry"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"


def test_schema_is_strict_2020_12_and_matches_contract_surface():
    path = Path(__file__).resolve().parents[1] / "schemas" / "artifact-revision.schema.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert schema["additionalProperties"] is False
    assert schema["properties"]["contract_id"]["const"] == ARTIFACT_REVISION_CONTRACT_ID
    assert schema["properties"]["content_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert schema["properties"]["semantic_projection_sha256"]["pattern"] == "^[0-9a-f]{64}$"
