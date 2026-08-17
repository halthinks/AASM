from __future__ import annotations

import hashlib
from copy import deepcopy

from aasm.artifact_lineage import ARTIFACT_REVISION_CONTRACT_ID, ArtifactRevision
from aasm.artifact_lineage_runtime import project_artifact_lineage_evidence
from aasm.semantic_result import canonical_semantic_json, semantic_fingerprint


WORKSPACE = "workspace-envelope"
SCOPE = "root"
ACTOR = "recorder"
FIREWALL = {
    "fact_authority_creation": "NONE",
    "source_trust_creation": "NONE",
    "effect_authorization": "NONE",
    "effect_dispatch": "NONE",
    "state_claim_creation": "NONE",
    "artifact_acceptance": "NONE",
    "current_artifact_pointer": "NONE",
}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _revision(artifact_ref: str) -> ArtifactRevision:
    return ArtifactRevision(
        logical_artifact_id="portable-artifact",
        content_sha256=_digest("same bytes"),
        semantic_projection_sha256=_digest("same semantics"),
        producer_id="tool:envelope-test",
        format_id="text/plain",
        artifact_ref=artifact_ref,
        artifact_kind="ENGINEERING_DOCUMENT",
    )


def _evidence_id(record_type: str, object_id: str, document: dict) -> str:
    identity = {"record_type": record_type, "object_id": object_id, "document": document}
    return f"artifact-lineage-evidence-{semantic_fingerprint(identity)[:24]}"


def _row(record_type: str, object_id: str, object_fingerprint: str, document: dict, *, derived_from=()):
    evidence_id = _evidence_id(record_type, object_id, document)
    return {
        "kind": "artifact_lineage",
        "statement": canonical_semantic_json(document),
        "source": ARTIFACT_REVISION_CONTRACT_ID,
        "confidence": None,
        "supports": [],
        "contradicts": [],
        "derived_from": list(derived_from),
        "metadata": {
            "aasm_artifact_lineage_record_type": record_type,
            "document": deepcopy(document),
            "object_id": object_id,
            "object_fingerprint": object_fingerprint,
            "workspace_id": WORKSPACE,
            "scope_id": SCOPE,
            "actor_principal_id": ACTOR,
            **FIREWALL,
        },
        "status": "active",
        "evidence_id": evidence_id,
        "created_at": 0.0,
        "invalidated_at": None,
        "invalidated_reason": None,
    }


def _valid_revision_and_binding_rows():
    original = _revision("artifact+memory://artifact-lineage/original")
    rebound = _revision("artifact+file://local/artifact-lineage/rebound.txt")
    assert original.revision_id == rebound.revision_id
    assert original.fingerprint == rebound.fingerprint
    assert original.storage_binding_fingerprint != rebound.storage_binding_fingerprint

    revision_document = original.to_dict()
    revision_row = _row(
        "ARTIFACT_REVISION",
        original.revision_id,
        original.fingerprint,
        revision_document,
    )
    binding_document = {
        "revision_id": rebound.revision_id,
        "revision_fingerprint": rebound.fingerprint,
        "content_sha256": rebound.content_sha256,
        "artifact_ref": rebound.artifact_ref,
        "storage_binding_fingerprint": rebound.storage_binding_fingerprint,
    }
    binding_object_id = f"{rebound.revision_id}:{rebound.storage_binding_fingerprint}"
    binding_row = _row(
        "ARTIFACT_STORAGE_BINDING",
        binding_object_id,
        rebound.storage_binding_fingerprint,
        binding_document,
        derived_from=(revision_row["evidence_id"],),
    )
    return original, rebound, revision_row, binding_row


def test_valid_storage_rebinding_envelope_projects_without_mutating_revision():
    original, rebound, revision_row, binding_row = _valid_revision_and_binding_rows()
    projection = project_artifact_lineage_evidence([revision_row, binding_row])
    assert projection["valid"] is True
    assert projection["revisions"][original.revision_id]["revision"]["artifact_ref"] == original.artifact_ref
    bindings = projection["storage_bindings_by_revision"][original.revision_id]
    assert {row["binding"]["artifact_ref"] for row in bindings} == {original.artifact_ref, rebound.artifact_ref}


def test_storage_binding_rejects_forged_metadata_object_fingerprint():
    _, _, revision_row, binding_row = _valid_revision_and_binding_rows()
    forged = deepcopy(binding_row)
    forged["metadata"]["object_fingerprint"] = "0" * 64
    projection = project_artifact_lineage_evidence([revision_row, forged])
    assert projection["valid"] is False
    assert any("metadata fingerprint mismatch" in row["error"] for row in projection["issues"])


def test_storage_binding_rejects_forged_deterministic_evidence_id():
    _, _, revision_row, binding_row = _valid_revision_and_binding_rows()
    forged = deepcopy(binding_row)
    forged["evidence_id"] = "artifact-lineage-evidence-" + ("0" * 24)
    projection = project_artifact_lineage_evidence([revision_row, forged])
    assert projection["valid"] is False
    assert any("deterministic Evidence ID mismatch" in row["error"] for row in projection["issues"])


def test_storage_binding_requires_derivation_from_canonical_revision_evidence():
    _, _, revision_row, binding_row = _valid_revision_and_binding_rows()
    forged = deepcopy(binding_row)
    forged["derived_from"] = []
    projection = project_artifact_lineage_evidence([revision_row, forged])
    assert projection["valid"] is False
    assert any("must derive from canonical revision Evidence" in row["error"] for row in projection["issues"])


def test_artifact_lineage_rejects_noncanonical_statement_and_firewall_metadata():
    _, _, revision_row, _ = _valid_revision_and_binding_rows()
    forged_statement = deepcopy(revision_row)
    forged_statement["statement"] = "{}"
    projection = project_artifact_lineage_evidence([forged_statement])
    assert projection["valid"] is False
    assert any("canonical statement mismatch" in row["error"] for row in projection["issues"])

    forged_firewall = deepcopy(revision_row)
    forged_firewall["metadata"]["fact_authority_creation"] = "GRANTED"
    projection = project_artifact_lineage_evidence([forged_firewall])
    assert projection["valid"] is False
    assert any("source firewall metadata mismatch" in row["error"] for row in projection["issues"])
