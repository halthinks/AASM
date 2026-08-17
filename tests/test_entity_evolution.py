from __future__ import annotations

import hashlib
import json

import pytest

from aasm import AASMEngine as ActiveEngine
from aasm.artifact_backends import MemoryArtifactBackend
from aasm.artifact_lineage import ArtifactRevision
from aasm.artifact_lineage_runtime import ARTIFACT_LINEAGE_CAPABILITIES
from aasm.entity_evolution import (
    ENTITY_EVOLUTION_RELATIONS,
    EntityEvolution,
    EntityRepresentationRef,
    entity_evolution_contract,
)
from aasm.entity_evolution_runtime import (
    ENTITY_EVOLUTION_CAPABILITIES,
    EntityEvolutionRuntimeMixin,
    entity_evolution_runtime_contract,
    project_entity_evolution_evidence,
)
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.semantic_evolution import ProblemRevision


WORKSPACE = "workspace-entity-evolution"
SCOPE = "root"
ROOT = "root"
RECORDER = "entity-recorder"


class EntityEvolutionEngine(EntityEvolutionRuntimeMixin, ActiveEngine):
    pass


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None):
    engine = EntityEvolutionEngine(ProblemSpec("S3 entity evolution"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "entity evolution fixture root", source="fixture.root-of-trust"),
        reason="entity evolution trust anchor",
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
    _grant(
        engine,
        RECORDER,
        *ARTIFACT_LINEAGE_CAPABILITIES.values(),
        *ENTITY_EVOLUTION_CAPABILITIES.values(),
    )
    problem_revision = ProblemRevision(
        "problem-entity",
        _digest("problem-r1"),
        _digest("problem-semantic-r1"),
        created_by="policy",
    )
    engine.register_initial_problem_revision(
        problem_revision,
        authority_id="policy",
        authority_class="POLICY",
        evidence_ids=(trust.evidence_id,),
    )
    return engine, problem_revision, trust


def source_evidence(engine, statement: str = "entity evolution source evidence"):
    return engine.add_evidence(
        EvidenceRecord("observation", statement, source="fixture.entity-source"),
        reason="entity evolution source evidence recorded",
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
):
    parent_items = tuple(parents)
    if relation is None:
        relation = "CREATED" if not parent_items else ("MERGES" if len(parent_items) > 1 else "MODIFIES")
    ref = backend.put_text("entity-evolution", logical_artifact_id, payload)
    return ArtifactRevision(
        logical_artifact_id=logical_artifact_id,
        content_sha256=_digest(payload),
        semantic_projection_sha256=_digest(semantic_projection),
        artifact_ref=ref,
        artifact_kind="ENGINEERING_DOCUMENT",
        parent_revision_ids=tuple(row.revision_id for row in parent_items),
        parent_revision_fingerprints={row.revision_id: row.fingerprint for row in parent_items},
        revision_relation=relation,
        producer_id="tool:entity-fixture",
        producer_kind="TOOL",
        source_problem_revision_id=source_problem.revision_id,
        source_problem_revision_fingerprint=source_problem.fingerprint,
        format_id="text/plain",
        schema_id="entity.fixture.v1",
        tool_id="entity-fixture",
        tool_version="1.0.0",
        evidence_ids=(evidence_id,),
    )


def record_revision(engine, item, *, backend, semantic_projection: str):
    return engine.record_artifact_revision(
        item,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=RECORDER,
        artifact_backend=backend,
        semantic_projection=semantic_projection,
    )


def representation(entity_id: str, revision: ArtifactRevision, label: str):
    return EntityRepresentationRef(
        entity_id=entity_id,
        artifact_revision_id=revision.revision_id,
        artifact_revision_fingerprint=revision.fingerprint,
        representation_id=label,
        representation_fingerprint=_digest(f"{revision.revision_id}:{label}"),
        entity_kind="PCB_COMPONENT",
    )


def record_evolution(engine, item: EntityEvolution):
    return engine.record_entity_evolution(
        item,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=RECORDER,
    )


def two_revision_fixture(engine, problem_revision, evidence):
    backend = MemoryArtifactBackend()
    root = make_revision(
        backend=backend,
        payload="root",
        semantic_projection="semantic-root",
        source_problem=problem_revision,
        evidence_id=evidence.evidence_id,
    )
    record_revision(engine, root, backend=backend, semantic_projection="semantic-root")
    child = make_revision(
        backend=backend,
        payload="child",
        semantic_projection="semantic-child",
        source_problem=problem_revision,
        evidence_id=evidence.evidence_id,
        parents=(root,),
        relation="MODIFIES",
    )
    record_revision(engine, child, backend=backend, semantic_projection="semantic-child")
    return backend, root, child


def test_entity_evolution_semantic_contract_covers_required_relations_and_firewalls():
    contract = entity_evolution_contract()
    assert tuple(contract["relations"]) == ENTITY_EVOLUTION_RELATIONS
    assert contract["ambiguous_mapping"] == "FAIL_CLOSED_FOR_HARD_REUSE_OR_AUTOMATIC_IDENTITY_TRANSFER"
    assert contract["fact_authority_creation"] == "NONE"
    assert contract["effect_authorization"] == "NONE"
    assert contract["current_entity_state_pointer"] == "NONE"
    runtime = entity_evolution_runtime_contract()
    assert runtime["parallel_entity_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert runtime["parallel_current_state_store"] == "NONE"
    assert runtime["hidden_wall_clock"] == "NONE"


def test_relation_cardinality_and_identity_rules_fail_closed():
    artifact_fp = _digest("artifact")
    a = EntityRepresentationRef("entity:A", "artifact-revision-" + "a" * 24, artifact_fp, "A", _digest("A"))
    b = EntityRepresentationRef("entity:B", "artifact-revision-" + "b" * 24, _digest("artifact-b"), "B", _digest("B"))
    with pytest.raises(ValueError, match="SPLIT"):
        EntityEvolution("SPLIT", predecessors=(a,), successors=(b,))
    with pytest.raises(ValueError, match="REPLACED"):
        EntityEvolution("REPLACED", predecessors=(a,), successors=(a,))
    with pytest.raises(ValueError, match="MODIFIED"):
        EntityEvolution("MODIFIED", predecessors=(a,), successors=(b,))
    ambiguous = EntityEvolution("AMBIGUOUS", predecessors=(a,), successors=(b,), evidence_ids=("e1",))
    assert ambiguous.is_ambiguous is True
    assert EntityEvolution.from_dict(ambiguous.to_dict()).fingerprint == ambiguous.fingerprint


def test_runtime_records_modified_entity_without_minting_authority():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    _, root, child = two_revision_fixture(engine, problem_revision, evidence)
    item = EntityEvolution(
        "MODIFIED",
        predecessors=(representation("component:R1", root, "R1"),),
        successors=(representation("component:R1", child, "R1"),),
        evidence_ids=(evidence.evidence_id,),
        reason="resistor moved while identity persisted",
    )
    result = record_evolution(engine, item)
    assert result["already_recorded"] is False
    assert result["hard_reuse_allowed"] is True
    assert result["fact_authority_created"] is False
    assert result["effect_authorized"] is False
    assert result["effect_dispatched"] is False
    assert result["current_entity_state_selected"] is False
    report = engine.entity_evolution_report("component:R1", workspace_id=WORKSPACE, scope_id=SCOPE)
    assert report["ambiguous"] is False
    assert report["hard_reuse_allowed"] is True
    assert report["head_semantics"] == "QUERY_PROJECTION_ONLY_NEVER_CURRENT_STATE_OR_AUTHORITY"
    assert report["authoritative"] is False


def test_runtime_supports_explicit_split_and_merge_without_identity_collapse():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    root = make_revision(backend=backend, payload="root", semantic_projection="s0", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    record_revision(engine, root, backend=backend, semantic_projection="s0")
    split_revision = make_revision(backend=backend, payload="split", semantic_projection="s1", source_problem=problem_revision, evidence_id=evidence.evidence_id, parents=(root,))
    record_revision(engine, split_revision, backend=backend, semantic_projection="s1")
    split = EntityEvolution(
        "SPLIT",
        predecessors=(representation("net:bus", root, "bus"),),
        successors=(
            representation("net:bus-a", split_revision, "bus-a"),
            representation("net:bus-b", split_revision, "bus-b"),
        ),
        evidence_ids=(evidence.evidence_id,),
    )
    record_evolution(engine, split)
    merge_revision = make_revision(backend=backend, payload="merge", semantic_projection="s2", source_problem=problem_revision, evidence_id=evidence.evidence_id, parents=(split_revision,))
    record_revision(engine, merge_revision, backend=backend, semantic_projection="s2")
    merged = EntityEvolution(
        "MERGED",
        predecessors=(
            representation("net:bus-a", split_revision, "bus-a"),
            representation("net:bus-b", split_revision, "bus-b"),
        ),
        successors=(representation("net:bus-recombined", merge_revision, "bus"),),
        evidence_ids=(evidence.evidence_id,),
    )
    record_evolution(engine, merged)
    report = engine.entity_evolutions_report()
    assert report["valid"] is True
    assert len(report["events"]) == 2
    assert "net:bus-a" in report["entity_history"]
    assert "net:bus-b" in report["entity_history"]
    assert "net:bus-recombined" in report["entity_history"]


def test_ambiguous_mapping_is_durable_and_blocks_hard_reuse():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    _, root, child = two_revision_fixture(engine, problem_revision, evidence)
    item = EntityEvolution(
        "AMBIGUOUS",
        predecessors=(representation("feature:old", root, "feature"),),
        successors=(
            representation("feature:new-a", child, "feature-a"),
            representation("feature:new-b", child, "feature-b"),
        ),
        evidence_ids=(evidence.evidence_id,),
        reason="tool could not prove correspondence",
    )
    result = record_evolution(engine, item)
    assert result["hard_reuse_allowed"] is False
    report = engine.entity_evolution_report("feature:new-a", workspace_id=WORKSPACE, scope_id=SCOPE)
    assert report["ambiguous"] is True
    assert report["hard_reuse_allowed"] is False
    all_report = engine.entity_evolutions_report()
    assert {"feature:old", "feature:new-a", "feature:new-b"}.issubset(set(all_report["hard_reuse_blocked_entities"]))


def test_runtime_rejects_forged_artifact_revision_fingerprint():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    _, root, child = two_revision_fixture(engine, problem_revision, evidence)
    forged = EntityRepresentationRef(
        "component:R1",
        child.revision_id,
        "0" * 64,
        "R1",
        _digest("forged-representation"),
    )
    item = EntityEvolution(
        "MODIFIED",
        predecessors=(representation("component:R1", root, "R1"),),
        successors=(forged,),
        evidence_ids=(evidence.evidence_id,),
    )
    with pytest.raises(ValueError, match="artifact revision fingerprint mismatch"):
        record_evolution(engine, item)


def test_runtime_rejects_unrelated_artifact_lineages():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    board = make_revision(backend=backend, payload="board", semantic_projection="board", source_problem=problem_revision, evidence_id=evidence.evidence_id, logical_artifact_id="board")
    enclosure = make_revision(backend=backend, payload="enclosure", semantic_projection="enclosure", source_problem=problem_revision, evidence_id=evidence.evidence_id, logical_artifact_id="enclosure")
    record_revision(engine, board, backend=backend, semantic_projection="board")
    record_revision(engine, enclosure, backend=backend, semantic_projection="enclosure")
    item = EntityEvolution(
        "REPLACED",
        predecessors=(representation("board:feature", board, "f"),),
        successors=(representation("enclosure:feature", enclosure, "f"),),
        evidence_ids=(evidence.evidence_id,),
    )
    with pytest.raises(ValueError, match="unrelated logical artifact lineages"):
        record_evolution(engine, item)


def test_runtime_rejects_non_descendant_successor_revision():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    backend = MemoryArtifactBackend()
    root = make_revision(backend=backend, payload="root", semantic_projection="root", source_problem=problem_revision, evidence_id=evidence.evidence_id)
    record_revision(engine, root, backend=backend, semantic_projection="root")
    left = make_revision(backend=backend, payload="left", semantic_projection="left", source_problem=problem_revision, evidence_id=evidence.evidence_id, parents=(root,))
    right = make_revision(backend=backend, payload="right", semantic_projection="right", source_problem=problem_revision, evidence_id=evidence.evidence_id, parents=(root,))
    record_revision(engine, left, backend=backend, semantic_projection="left")
    record_revision(engine, right, backend=backend, semantic_projection="right")
    item = EntityEvolution(
        "MODIFIED",
        predecessors=(representation("entity:x", left, "x"),),
        successors=(representation("entity:x", right, "x"),),
        evidence_ids=(evidence.evidence_id,),
    )
    with pytest.raises(ValueError, match="not descended"):
        record_evolution(engine, item)


def test_runtime_rejects_invalidated_source_evidence():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    _, root, child = two_revision_fixture(engine, problem_revision, evidence)
    engine.invalidate_evidence(evidence.evidence_id, "disputed")
    item = EntityEvolution(
        "MODIFIED",
        predecessors=(representation("entity:x", root, "x"),),
        successors=(representation("entity:x", child, "x"),),
        evidence_ids=(evidence.evidence_id,),
    )
    with pytest.raises(ValueError, match="source Evidence is not active"):
        record_evolution(engine, item)


def test_projection_rejects_forged_entity_evolution_envelope():
    engine, problem_revision, _ = bootstrapped_engine()
    evidence = source_evidence(engine)
    _, root, child = two_revision_fixture(engine, problem_revision, evidence)
    item = EntityEvolution(
        "MODIFIED",
        predecessors=(representation("entity:x", root, "x"),),
        successors=(representation("entity:x", child, "x"),),
        evidence_ids=(evidence.evidence_id,),
    )
    result = record_evolution(engine, item)
    records = list(engine.snapshot.evidence["records"])
    forged = dict(result["evolution"])
    forged["reason"] = "tampered"
    records.append({
        "kind": "entity_evolution",
        "statement": json.dumps(forged),
        "source": "forged",
        "confidence": None,
        "supports": [],
        "contradicts": [],
        "derived_from": [result["evidence_id"]],
        "metadata": {
            "aasm_entity_evolution_record_type": "ENTITY_EVOLUTION",
            "document": forged,
            "object_id": item.evolution_id,
            "object_fingerprint": item.fingerprint,
        },
        "status": "active",
        "evidence_id": "forged-entity-evolution",
        "created_at": 0.0,
        "invalidated_at": None,
        "invalidated_reason": None,
    })
    projection = project_entity_evolution_evidence(records)
    assert projection["valid"] is False
    assert projection["issues"]


def test_sqlite_restart_reconstructs_identical_entity_evolution_projection(tmp_path):
    db = tmp_path / "entity-evolution.db"
    store = SQLiteStore(db)
    engine, problem_revision, _ = bootstrapped_engine(store=store)
    evidence = source_evidence(engine)
    _, root, child = two_revision_fixture(engine, problem_revision, evidence)
    item = EntityEvolution(
        "MODIFIED",
        predecessors=(representation("component:R1", root, "R1"),),
        successors=(representation("component:R1", child, "R1"),),
        evidence_ids=(evidence.evidence_id,),
    )
    record_evolution(engine, item)
    before = engine.entity_evolutions_report()
    machine_id = engine.snapshot.machine_id
    store.close()
    reopened = SQLiteStore(db)
    resumed = EntityEvolutionEngine.resume(machine_id, reopened)
    after = resumed.entity_evolutions_report()
    assert after == before
    assert resumed.entity_evolution_event_report(item.evolution_id)["evolution"] == item.to_dict()
    reopened.close()
