from __future__ import annotations

import hashlib

import pytest

from aasm import AASMEngine as ActiveEngine
from aasm.artifact_backends import LocalDirectoryArtifactBackend, MemoryArtifactBackend
from aasm.artifact_lineage import ArtifactRevision
from aasm.artifact_lineage_runtime import (
    ARTIFACT_LINEAGE_CAPABILITIES,
    artifact_lineage_runtime_contract,
    project_artifact_lineage_evidence,
)
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.semantic_evolution import ProblemRevision


WORKSPACE = "workspace-artifact"
SCOPE = "root"
ROOT = "root"
RECORDER = "artifact-recorder"
ArtifactLineageEngine = ActiveEngine


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None):
    engine = ArtifactLineageEngine(ProblemSpec("S3 artifact lineage"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "artifact lineage fixture root", source="fixture.root-of-trust"),
        reason="artifact lineage trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    _grant(engine, ROOT, "identity.register")
    engine.register_scoped_principal(
        Principal(RECORDER, "SERVICE"),
        workspace_id=WORKSPACE,
        actor_principal_id=ROOT,
    )
    _grant(engine, RECORDER, *ARTIFACT_LINEAGE_CAPABILITIES.values())
    problem_revision = ProblemRevision(
        "problem-artifact",
        _digest("problem-r1"),
        _digest("problem-semantic-r1"),
        created_by="policy",
    )
    problem_row = engine.register_initial_problem_revision(
        problem_revision,
        authority_id="policy",
        authority_class="POLICY",
        evidence_ids=(trust.evidence_id,),
    )
    return engine, problem_revision, problem_row


def source_evidence(engine, statement="artifact source evidence"):
    return engine.add_evidence(
        EvidenceRecord("observation", statement, source="fixture.source"),
        reason="artifact source evidence recorded",
    )


def make_revision(
    *,
    backend,
    payload: str,
    semantic_projection: str,
    source_problem: ProblemRevision,
    evidence_id: str,
    logical_artifact_id: str = "board-main",
    parents=(),
    relation: str | None = None,
    producer_id: str = "tool:reference",
):
    parent_items = tuple(parents)
    parent_ids = tuple(row.revision_id for row in parent_items)
    parent_fingerprints = {row.revision_id: row.fingerprint for row in parent_items}
    if relation is None:
        relation = "CREATED" if not parent_items else ("MERGES" if len(parent_items) > 1 else "MODIFIES")
    ref = backend.put_text("artifact-lineage", logical_artifact_id, payload)
    return ArtifactRevision(
        logical_artifact_id=logical_artifact_id,
        content_sha256=_digest(payload),
        semantic_projection_sha256=_digest(semantic_projection),
        artifact_ref=ref,
        artifact_kind="ENGINEERING_DOCUMENT",
        parent_revision_ids=parent_ids,
        parent_revision_fingerprints=parent_fingerprints,
        revision_relation=relation,
        producer_id=producer_id,
        producer_kind="TOOL",
        source_problem_revision_id=source_problem.revision_id,
        source_problem_revision_fingerprint=source_problem.fingerprint,
        format_id="text/plain",
        schema_id="example.schema.v1",
        tool_id="reference-tool",
        tool_version="1.0.0",
        evidence_ids=(evidence_id,),
    )


def record(engine, item, *, backend, semantic_projection):
    return engine.record_artifact_revision(
        item,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=RECORDER,
        artifact_backend=backend,
        semantic_projection=semantic_projection,
    )


def test_real_active_engine_exposes_candidate_runtime_without_public_adoption_claim():
    assert ArtifactLineageEngine is ActiveEngine
    assert callable(getattr(ActiveEngine, "record_artifact_revision", None))
    assert callable(getattr(ActiveEngine, "artifact_revision_report", None))
    assert callable(getattr(ActiveEngine, "artifact_lineage_report", None))
    assert artifact_lineage_runtime_contract()["runtime_admission"] == "ACTIVE_ENGINE_CANDIDATE_QUALIFICATION"


def test_runtime_records_explicit_branch_and_merge_without_selecting_authority():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    root = make_revision(backend=backend, payload="root", semantic_projection="semantic-root", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    root_result = record(engine, root, backend=backend, semantic_projection="semantic-root")
    assert root_result["already_recorded"] is False
    assert root_result["artifact_accepted"] is False
    assert root_result["fact_authority_created"] is False
    assert root_result["effect_authorized"] is False
    assert root_result["effect_dispatched"] is False

    left = make_revision(backend=backend, payload="left", semantic_projection="semantic-left", source_problem=problem_revision, evidence_id=evidence.evidence_id, parents=(root,), relation="MODIFIES")
    right = make_revision(backend=backend, payload="right", semantic_projection="semantic-right", source_problem=problem_revision, evidence_id=evidence.evidence_id, parents=(root,), relation="DERIVED_FROM")
    record(engine, left, backend=backend, semantic_projection="semantic-left")
    record(engine, right, backend=backend, semantic_projection="semantic-right")
    branch_report = engine.artifact_lineage_report(root.logical_artifact_id, workspace_id=WORKSPACE, scope_id=SCOPE)
    assert sorted(branch_report["heads"]) == sorted([left.revision_id, right.revision_id])
    assert branch_report["head_semantics"] == "QUERY_PROJECTION_ONLY_NOT_ACCEPTANCE_OR_AUTHORITY"
    assert branch_report["newest_revision_authority"] == "NONE"

    merged = make_revision(backend=backend, payload="merged", semantic_projection="semantic-merged", source_problem=problem_revision, evidence_id=evidence.evidence_id, parents=(left, right), relation="MERGES")
    record(engine, merged, backend=backend, semantic_projection="semantic-merged")
    report = engine.artifact_lineage_report(root.logical_artifact_id, workspace_id=WORKSPACE, scope_id=SCOPE)
    assert report["valid"] is True
    assert report["heads"] == [merged.revision_id]
    assert len(report["revisions"]) == 4


def test_runtime_rejects_forged_parent_fingerprint_and_second_created_root():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    root = make_revision(backend=backend, payload="root", semantic_projection="semantic-root", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    record(engine, root, backend=backend, semantic_projection="semantic-root")

    forged_ref = backend.put_text("artifact-lineage", "board-main", "forged")
    forged = ArtifactRevision(
        logical_artifact_id="board-main",
        content_sha256=_digest("forged"),
        semantic_projection_sha256=_digest("semantic-forged"),
        artifact_ref=forged_ref,
        artifact_kind="ENGINEERING_DOCUMENT",
        parent_revision_ids=(root.revision_id,),
        parent_revision_fingerprints={root.revision_id: "0" * 64},
        revision_relation="MODIFIES",
        producer_id="tool:reference",
        producer_kind="TOOL",
        source_problem_revision_id=problem_revision.revision_id,
        source_problem_revision_fingerprint=problem_revision.fingerprint,
        format_id="text/plain",
        evidence_ids=(evidence.evidence_id,),
    )
    with pytest.raises(ValueError, match="parent revision fingerprint mismatch"):
        record(engine, forged, backend=backend, semantic_projection="semantic-forged")

    second_root = make_revision(backend=backend, payload="second-root", semantic_projection="semantic-second-root", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    with pytest.raises(ValueError, match="already has a durable CREATED root"):
        record(engine, second_root, backend=backend, semantic_projection="semantic-second-root")


def test_runtime_rejects_stale_problem_revision_missing_or_invalidated_source_evidence():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    stale = make_revision(backend=backend, payload="stale", semantic_projection="semantic-stale", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    stale_payload = stale.to_dict()
    stale_payload.pop("revision_id")
    stale_payload.pop("fingerprint")
    stale_payload.pop("storage_binding_fingerprint")
    stale_payload["source_problem_revision_fingerprint"] = "0" * 64
    stale = ArtifactRevision.from_dict(stale_payload)
    with pytest.raises(ValueError, match="source problem revision fingerprint mismatch"):
        record(engine, stale, backend=backend, semantic_projection="semantic-stale")

    missing = make_revision(backend=backend, payload="missing", semantic_projection="semantic-missing", source_problem=problem_revision, evidence_id="evidence-does-not-exist", logical_artifact_id="missing-artifact")
    with pytest.raises(KeyError):
        record(engine, missing, backend=backend, semantic_projection="semantic-missing")

    engine.invalidate_evidence(evidence.evidence_id, "source disputed")
    invalidated = make_revision(backend=backend, payload="invalidated", semantic_projection="semantic-invalidated", source_problem=problem_revision, evidence_id=evidence.evidence_id, logical_artifact_id="invalidated-artifact")
    with pytest.raises(ValueError, match="source Evidence is not active"):
        record(engine, invalidated, backend=backend, semantic_projection="semantic-invalidated")


def test_runtime_verifies_content_and_semantic_projection_hashes():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    item = make_revision(backend=backend, payload="payload", semantic_projection="semantic-payload", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    with pytest.raises(ValueError, match="semantic projection SHA-256 mismatch"):
        record(engine, item, backend=backend, semantic_projection="wrong-semantic")

    payload = item.to_dict()
    payload.pop("revision_id")
    payload.pop("fingerprint")
    payload.pop("storage_binding_fingerprint")
    payload["content_sha256"] = _digest("other-payload")
    mismatched = ArtifactRevision.from_dict(payload)
    with pytest.raises(ValueError, match="artifact content SHA-256 mismatch"):
        record(engine, mismatched, backend=backend, semantic_projection="semantic-payload")


def test_storage_rebinding_appends_binding_without_mutating_revision(tmp_path):
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    memory = MemoryArtifactBackend()
    local = LocalDirectoryArtifactBackend(tmp_path / "artifact-files")
    payload = "portable bytes"
    semantic = "portable semantics"
    first = make_revision(backend=memory, payload=payload, semantic_projection=semantic, source_problem=problem_revision, evidence_id=evidence.evidence_id)
    first_result = record(engine, first, backend=memory, semantic_projection=semantic)
    second = make_revision(backend=local, payload=payload, semantic_projection=semantic, source_problem=problem_revision, evidence_id=evidence.evidence_id)
    assert first.revision_id == second.revision_id
    assert first.fingerprint == second.fingerprint
    assert first.storage_binding_fingerprint != second.storage_binding_fingerprint
    second_result = record(engine, second, backend=local, semantic_projection=semantic)
    assert second_result["already_recorded"] is True
    assert second_result["evidence_id"] == first_result["evidence_id"]
    assert second_result["storage_binding_evidence_id"] != first_result["evidence_id"]
    report = engine.artifact_revision_report(first.revision_id)
    assert report["revision"]["artifact_ref"] == first.artifact_ref
    assert len(report["storage_bindings"]) == 2
    assert {row["binding"]["artifact_ref"] for row in report["storage_bindings"]} == {first.artifact_ref, second.artifact_ref}
    assert report["artifact_accepted"] is False
    assert report["authoritative"] is False


def test_storage_rebinding_and_parent_lineage_cannot_cross_scope():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    root = make_revision(backend=backend, payload="root", semantic_projection="semantic-root", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    record(engine, root, backend=backend, semantic_projection="semantic-root")
    with pytest.raises(PermissionError, match="cannot cross workspace/scope"):
        engine.record_artifact_revision(
            root,
            workspace_id=WORKSPACE,
            scope_id="other-scope",
            actor_principal_id=RECORDER,
            artifact_backend=backend,
            semantic_projection="semantic-root",
        )


def test_duplicate_content_with_different_provenance_remains_distinguishable():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    root = make_revision(backend=backend, payload="same-bytes", semantic_projection="same-semantic", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    record(engine, root, backend=backend, semantic_projection="same-semantic")
    child = make_revision(backend=backend, payload="same-bytes", semantic_projection="same-semantic", source_problem=problem_revision, evidence_id=evidence.evidence_id, parents=(root,), relation="DERIVED_FROM", producer_id="tool:different")
    record(engine, child, backend=backend, semantic_projection="same-semantic")
    assert child.content_sha256 == root.content_sha256
    assert child.revision_id != root.revision_id
    assert child.fingerprint != root.fingerprint


def test_projection_rejects_mutated_revision_record_and_source_firewall_claims_remain_false():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    root = make_revision(backend=backend, payload="root", semantic_projection="semantic-root", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    result = record(engine, root, backend=backend, semantic_projection="semantic-root")
    contract = artifact_lineage_runtime_contract()
    assert contract["fact_authority_creation"] == "NONE"
    assert contract["source_trust_creation"] == "NONE"
    assert contract["effect_authorization"] == "NONE"
    assert contract["effect_dispatch"] == "NONE"
    assert contract["current_artifact_pointer"] == "NONE"
    assert contract["parallel_artifact_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY"

    forged = root.to_dict()
    forged["artifact_ref"] = "artifact+memory://forged/location"
    forged["storage_binding_fingerprint"] = "0" * 64
    records = list(engine.snapshot.evidence["records"])
    records.append(
        {
            "kind": "artifact_lineage",
            "statement": "{}",
            "source": "forged",
            "confidence": None,
            "supports": [],
            "contradicts": [],
            "derived_from": [result["evidence_id"]],
            "metadata": {
                "aasm_artifact_lineage_record_type": "ARTIFACT_REVISION",
                "document": forged,
                "object_id": root.revision_id,
                "object_fingerprint": root.fingerprint,
            },
            "status": "active",
            "evidence_id": "forged-artifact-lineage-evidence",
            "created_at": 0.0,
            "invalidated_at": None,
            "invalidated_reason": None,
        }
    )
    projection = project_artifact_lineage_evidence(records)
    assert projection["valid"] is False
    assert projection["issues"]


def test_sqlite_restart_reconstructs_identical_lineage_projection(tmp_path):
    db = tmp_path / "artifact-lineage.db"
    store = SQLiteStore(db)
    engine, problem_revision, _ = bootstrapped_engine(store=store)
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    root = make_revision(backend=backend, payload="root", semantic_projection="semantic-root", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    record(engine, root, backend=backend, semantic_projection="semantic-root")
    before = engine.artifact_lineage_report()
    machine_id = engine.snapshot.machine_id
    store.close()
    reopened = SQLiteStore(db)
    resumed = ArtifactLineageEngine.resume(machine_id, reopened)
    after = resumed.artifact_lineage_report()
    assert after == before
    assert resumed.artifact_revision_report(root.revision_id)["revision"] == root.to_dict()
    reopened.close()
