from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from aasm.artifact_backends import LocalDirectoryArtifactBackend, MemoryArtifactBackend
from aasm.artifact_lineage import (
    ARTIFACT_REVISION_CONTRACT_ID,
    ARTIFACT_REVISION_CONTRACT_VERSION,
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
    relation: str | None = None,
    artifact_ref: str | None = None,
    parent_fingerprints: dict[str, str] | None = None,
) -> ArtifactRevision:
    digest = _digest(payload)
    parent_items = tuple(parents)
    parent_ids = tuple(
        row.revision_id if isinstance(row, ArtifactRevision) else str(row)
        for row in parent_items
    )
    if parent_fingerprints is None:
        parent_fingerprints = {
            row.revision_id: row.fingerprint
            for row in parent_items
            if isinstance(row, ArtifactRevision)
        }
    if relation is None:
        relation = "CREATED" if not parent_ids else ("MERGES" if len(parent_ids) > 1 else "MODIFIES")
    return ArtifactRevision(
        logical_artifact_id=logical_artifact_id,
        content_sha256=digest,
        semantic_projection_sha256=_digest("semantic:" + payload),
        artifact_ref=digest if artifact_ref is None else artifact_ref,
        artifact_kind="ENGINEERING_DOCUMENT",
        parent_revision_ids=parent_ids,
        parent_revision_fingerprints=parent_fingerprints,
        revision_relation=relation,
        producer_id="tool:reference",
        producer_kind="TOOL",
        machine_id="machine-1",
        effect_id="effect-1",
        source_problem_revision_id="board-r7",
        source_problem_revision_fingerprint=_digest("board-r7"),
        environment_id="env-r1",
        environment_fingerprint=_digest("env-r1"),
        refinement_run_id="refinement-run-r4",
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
    assert first.storage_binding_fingerprint == second.storage_binding_fingerprint
    assert second.to_dict() == first.to_dict()


def test_revision_identity_is_backend_independent_but_storage_binding_is_not(tmp_path):
    payload = "same content through existing backends"
    memory = MemoryArtifactBackend()
    local = LocalDirectoryArtifactBackend(tmp_path / "files")

    memory_ref = memory.put_text("artifact-lineage", "board", payload)
    local_ref = local.put_text("artifact-lineage", "board", payload)

    memory_item = _revision(payload=payload, artifact_ref=memory_ref)
    local_item = _revision(payload=payload, artifact_ref=local_ref)
    expected_digest = _digest(payload)

    assert memory_item.content_sha256 == expected_digest
    assert local_item.content_sha256 == expected_digest
    assert memory.get_text(memory_ref) == payload
    assert local.get_text(local_ref) == payload
    assert memory_ref.startswith("artifact+memory://")
    assert local_ref.startswith("artifact+file://")

    assert memory_item.revision_id == local_item.revision_id
    assert memory_item.fingerprint == local_item.fingerprint
    assert memory_item.storage_binding_fingerprint != local_item.storage_binding_fingerprint


def test_artifact_revision_rejects_content_ref_digest_mismatch():
    with pytest.raises(ValueError, match="artifact_ref content digest"):
        _revision(artifact_ref="0" * 64)


def test_artifact_revision_rejects_forged_revision_semantic_and_storage_fingerprints():
    item = _revision()

    forged_id = item.to_dict()
    forged_id["revision_id"] = "artifact-revision-" + ("0" * 24)
    with pytest.raises(ValueError, match="revision_id"):
        ArtifactRevision.from_dict(forged_id)

    forged_semantic_fingerprint = item.to_dict()
    forged_semantic_fingerprint["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="canonical semantic content"):
        ArtifactRevision.from_dict(forged_semantic_fingerprint)

    forged_storage_fingerprint = item.to_dict()
    forged_storage_fingerprint["storage_binding_fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="storage binding fingerprint"):
        ArtifactRevision.from_dict(forged_storage_fingerprint)

    rebound_storage = item.to_dict()
    rebound_storage["artifact_ref"] = "artifact+file://elsewhere/board.txt"
    with pytest.raises(ValueError, match="storage binding fingerprint"):
        ArtifactRevision.from_dict(rebound_storage)


def test_source_problem_revision_and_environment_require_exact_pairs():
    item = _revision()

    payload = item.to_dict()
    payload["source_problem_revision_fingerprint"] = ""
    payload.pop("fingerprint")
    payload.pop("storage_binding_fingerprint")
    payload.pop("revision_id")
    with pytest.raises(ValueError, match="source problem revision ID and fingerprint"):
        ArtifactRevision.from_dict(payload)

    payload = item.to_dict()
    payload["environment_fingerprint"] = ""
    payload.pop("fingerprint")
    payload.pop("storage_binding_fingerprint")
    payload.pop("revision_id")
    with pytest.raises(ValueError, match="environment ID and fingerprint"):
        ArtifactRevision.from_dict(payload)


def test_lineage_transition_requires_exact_parent_id_fingerprint_and_stable_logical_identity():
    base = _revision(payload="r1")
    child = _revision(payload="r2", parents=(base,))
    report = validate_artifact_revision_transition((base,), child)
    assert report["valid"] is True

    wrong_identity = _revision(
        payload="r3",
        logical_artifact_id="other-artifact",
        parents=(base,),
    )
    report = validate_artifact_revision_transition((base,), wrong_identity)
    assert report["valid"] is False
    assert "LOGICAL_ARTIFACT_ID_CHANGED" in report["errors"]

    missing_parent = _revision(payload="r4")
    report = validate_artifact_revision_transition((base,), missing_parent)
    assert report["valid"] is False
    assert "PARENT_REVISION_SET_MISMATCH" in report["errors"]

    forged_parent_fingerprint = _revision(
        payload="r5",
        parents=(base.revision_id,),
        parent_fingerprints={base.revision_id: "0" * 64},
    )
    report = validate_artifact_revision_transition((base,), forged_parent_fingerprint)
    assert report["valid"] is False
    assert "PARENT_REVISION_FINGERPRINT_MISMATCH" in report["errors"]


def test_revision_relation_is_explicit_and_merge_requires_complete_multiple_parent_set():
    left = _revision(payload="left")
    right = _revision(payload="right")
    merged = _revision(payload="merged", parents=(left, right), relation="MERGES")
    report = validate_artifact_revision_transition((left, right), merged)
    assert report["valid"] is True
    assert report["revision_relation"] == "MERGES"

    with pytest.raises(ValueError, match="MERGES artifact revision requires at least two parents"):
        _revision(payload="bad-merge", parents=(left,), relation="MERGES")

    with pytest.raises(ValueError, match="parentless artifact revision must use CREATED"):
        _revision(payload="bad-derived", relation="DERIVED_FROM")


def test_competing_children_are_distinct_legal_branches_not_implicit_authority():
    base = _revision(payload="root")
    branch_a = _revision(payload="branch-a", parents=(base,), relation="MODIFIES")
    branch_b = _revision(payload="branch-b", parents=(base,), relation="DERIVED_FROM")
    assert validate_artifact_revision_transition((base,), branch_a)["valid"] is True
    assert validate_artifact_revision_transition((base,), branch_b)["valid"] is True
    assert branch_a.revision_id != branch_b.revision_id
    assert branch_a.revision_relation != branch_b.revision_relation


def test_duplicate_content_with_different_provenance_produces_distinct_revision_identity():
    first = _revision(payload="same bytes")
    payload = first.to_dict()
    payload.pop("revision_id")
    payload.pop("fingerprint")
    payload.pop("storage_binding_fingerprint")
    payload["producer_id"] = "tool:other"
    second = ArtifactRevision.from_dict(payload)
    assert second.content_sha256 == first.content_sha256
    assert second.revision_id != first.revision_id
    assert second.fingerprint != first.fingerprint


def test_contract_explicitly_denies_truth_acceptance_and_parallel_registry():
    contract = artifact_lineage_contract()
    assert contract["artifact_revision_contract_id"] == ARTIFACT_REVISION_CONTRACT_ID
    assert contract["artifact_revision_contract_version"] == ARTIFACT_REVISION_CONTRACT_VERSION
    assert contract["revision_identity"].startswith("BACKEND_INDEPENDENT")
    assert contract["parent_identity"] == "EXACT_PARENT_REVISION_ID_AND_FINGERPRINT_BINDINGS"
    assert contract["revision_relation"] == "EXPLICIT_NOT_INFERRED_FROM_RECENCY"
    assert contract["storage_binding_identity"] == (
        "SEPARATE_FROM_REVISION_IDENTITY_AND_INTEGRITY_FINGERPRINTED"
    )
    assert contract["content_storage"] == "EXISTING_AASM_ARTIFACT_BACKENDS_OR_EXTERNAL_REFERENCE"
    assert contract["artifact_ref"].startswith("NON_SEMANTIC_OPAQUE_STORAGE_BINDING")
    assert contract["execution_environment"] == "EXACT_ID_AND_FINGERPRINT_WHEN_PRESENT"
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
    assert schema["properties"]["contract_version"]["const"] == ARTIFACT_REVISION_CONTRACT_VERSION
    assert schema["properties"]["content_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert schema["properties"]["semantic_projection_sha256"]["pattern"] == "^[0-9a-f]{64}$"
    assert schema["properties"]["revision_relation"]["enum"] == [
        "CREATED",
        "CREATED_FROM",
        "MODIFIES",
        "DERIVED_FROM",
        "MERGES",
        "REPLACES",
    ]
    assert "parent_revision_fingerprints" in schema["required"]
    assert "environment_fingerprint" in schema["required"]
    assert "storage_binding_fingerprint" in schema["required"]
