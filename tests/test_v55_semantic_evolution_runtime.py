from __future__ import annotations

from pathlib import Path

import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence import SQLiteStore
from aasm.reasoning import Claim, ReasoningProducer
from aasm.runtime_v55_foundation import AASMEngine
from aasm.semantic_dependencies import SemanticNodeRef
from aasm.semantic_evolution import ProblemDelta, ProblemRevision


def initial_revision(problem_id: str = "board-alpha", revision_id: str = "board-alpha-r1") -> ProblemRevision:
    return ProblemRevision(
        problem_id=problem_id,
        problem_fingerprint=f"{problem_id}-problem-fp-1",
        semantic_projection_fingerprint=f"{problem_id}-semantic-fp-1",
        created_by="controller",
        revision_id=revision_id,
    )


def transition_from(
    base: ProblemRevision,
    *,
    suffix: str,
    truth_change_roots=(),
    evidence_ids=(),
) -> tuple[ProblemDelta, ProblemRevision]:
    problem_fp = f"{base.problem_id}-problem-fp-{suffix}"
    semantic_fp = f"{base.problem_id}-semantic-fp-{suffix}"
    delta = ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint=problem_fp,
        target_semantic_projection_fingerprint=semantic_fp,
        truth_change_roots=tuple(truth_change_roots),
        changed_semantic_ids=(f"semantic-change-{suffix}",),
        evidence_ids=tuple(evidence_ids),
    )
    target = ProblemRevision(
        problem_id=base.problem_id,
        problem_fingerprint=problem_fp,
        semantic_projection_fingerprint=semantic_fp,
        parent_revision_ids=(base.revision_id,),
        created_by="controller",
        created_from_delta_id=delta.delta_id,
        revision_id=f"{base.problem_id}-r{suffix}",
    )
    return delta, target


def test_runtime_contract_reuses_existing_evidence_and_truth_maintenance_paths():
    engine = AASMEngine(ProblemSpec("v55 runtime contract"))
    contract = engine.semantic_evolution_runtime_contract_report()
    assert contract["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"
    assert contract["truth_maintenance"] == "EXISTING_AASM_SEMANTIC_DEPENDENCY_RUNTIME"
    assert contract["parallel_revision_table"] == "NONE"
    assert contract["parallel_change_impact_graph"] == "NONE"
    assert contract["revision_record_grants_truth"] is False


def test_initial_revision_is_durable_projection_and_replay_safe():
    engine = AASMEngine(ProblemSpec("v55 initial revision"))
    revision = initial_revision()
    result = engine.register_initial_problem_revision(
        revision,
        authority_id="policy-v55",
        authority_class="POLICY",
    )
    assert result["already_registered"] is False
    report = engine.semantic_evolution_report(revision.problem_id)
    assert report["valid"] is True
    assert report["heads"] == [revision.revision_id]
    assert engine.require_usable_problem_revision(revision.problem_id)["fingerprint"] == revision.fingerprint
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_revision_commit_rejects_non_policy_authority():
    engine = AASMEngine(ProblemSpec("v55 authority"))
    with pytest.raises(PermissionError, match="POLICY or CONTROLLER"):
        engine.register_initial_problem_revision(
            initial_revision(),
            authority_id="agent",
            authority_class="PROPOSER",
        )


def test_revision_transition_advances_single_head_without_mutating_historical_evidence():
    engine = AASMEngine(ProblemSpec("v55 transition"))
    observation = engine.add_evidence(EvidenceRecord("observation", "source evidence remains historical", source="test"))
    base = initial_revision()
    engine.register_initial_problem_revision(base, authority_id="policy", authority_class="POLICY")
    delta, target = transition_from(base, suffix="2", evidence_ids=(observation.evidence_id,))
    committed = engine.commit_problem_revision_transition(
        delta,
        target,
        authority_id="policy",
        authority_class="POLICY",
    )
    assert committed["already_committed"] is False
    report = engine.semantic_evolution_report(base.problem_id)
    assert report["heads"] == [target.revision_id]
    assert report["pending_impact_delta_ids"] == []
    assert engine.require_usable_problem_revision(base.problem_id)["revision_id"] == target.revision_id
    source = next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == observation.evidence_id)
    assert source["status"] == "active"


def test_problem_delta_truth_roots_use_existing_dependency_truth_maintenance():
    engine = AASMEngine(ProblemSpec("v55 truth maintenance"))
    root = Claim("revision-sensitive root", ReasoningProducer("agent", "PROPOSER"))
    dependent = Claim(
        "revision-sensitive dependent",
        ReasoningProducer("agent", "PROPOSER"),
        premise_artifact_ids=(root.artifact_id,),
    )
    engine.propose_artifact(root)
    engine.propose_artifact(dependent)
    base = initial_revision()
    engine.register_initial_problem_revision(base, authority_id="policy", authority_class="POLICY")
    delta, target = transition_from(
        base,
        suffix="2",
        truth_change_roots=(SemanticNodeRef("ARTIFACT", root.artifact_id),),
    )
    committed = engine.commit_problem_revision_transition(
        delta,
        target,
        authority_id="policy",
        authority_class="POLICY",
    )
    assert committed["truth_maintenance"]["already_applied"] is False
    reasoning = engine.reasoning_report()
    assert reasoning["artifacts"][root.artifact_id]["state"] == "STALE"
    assert reasoning["artifacts"][dependent.artifact_id]["state"] == "STALE"
    report = engine.semantic_evolution_report(base.problem_id)
    assert report["pending_impact_delta_ids"] == []
    repeated = engine.resume_problem_revision_impacts(delta.delta_id)
    assert repeated["already_applied"] is True


def test_pending_revision_impact_survives_sqlite_restart_and_blocks_use_until_resumed(tmp_path: Path):
    path = tmp_path / "v55-semantic-evolution.db"
    store = SQLiteStore(str(path))
    engine = AASMEngine(ProblemSpec("v55 restart"), store=store)
    machine_id = engine.snapshot.machine_id
    root = Claim("restart-sensitive root", ReasoningProducer("agent", "PROPOSER"))
    engine.propose_artifact(root)
    base = initial_revision()
    engine.register_initial_problem_revision(base, authority_id="policy", authority_class="POLICY")
    delta, target = transition_from(
        base,
        suffix="2",
        truth_change_roots=(SemanticNodeRef("ARTIFACT", root.artifact_id),),
    )
    engine.commit_problem_revision_transition(
        delta,
        target,
        authority_id="policy",
        authority_class="POLICY",
        apply_truth_maintenance=False,
    )
    assert engine.semantic_evolution_report(base.problem_id)["pending_impact_delta_ids"] == [delta.delta_id]
    with pytest.raises(RuntimeError, match="pending truth-maintenance"):
        engine.require_usable_problem_revision(base.problem_id)
    store.close()

    resumed_store = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, resumed_store)
    assert resumed.semantic_evolution_report(base.problem_id)["pending_impact_delta_ids"] == [delta.delta_id]
    applied = resumed.resume_problem_revision_impacts(delta.delta_id)
    assert applied["already_applied"] is False
    assert resumed.reasoning_report(root.artifact_id)["state"] == "STALE"
    assert resumed.semantic_evolution_report(base.problem_id)["pending_impact_delta_ids"] == []
    assert resumed.require_usable_problem_revision(base.problem_id)["revision_id"] == target.revision_id
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    resumed_store.close()


def test_two_hosts_cannot_commit_from_same_stale_revision_head(tmp_path: Path):
    path = tmp_path / "v55-stale-writer.db"
    store_a = SQLiteStore(str(path))
    host_a = AASMEngine(ProblemSpec("v55 stale writer"), store=store_a)
    machine_id = host_a.snapshot.machine_id
    base = initial_revision()
    host_a.register_initial_problem_revision(base, authority_id="policy", authority_class="POLICY")

    store_b = SQLiteStore(str(path))
    host_b = AASMEngine.resume(machine_id, store_b)
    delta_a, target_a = transition_from(base, suffix="2a")
    delta_b, target_b = transition_from(base, suffix="2b")

    host_a.commit_problem_revision_transition(
        delta_a,
        target_a,
        authority_id="policy",
        authority_class="POLICY",
    )
    with pytest.raises(ValueError, match="Stale machine version"):
        host_b.commit_problem_revision_transition(
            delta_b,
            target_b,
            authority_id="policy",
            authority_class="POLICY",
        )

    canonical = store_a.load_snapshot(machine_id)
    assert host_b.snapshot.canonical_hash() == canonical.canonical_hash()
    report = host_b.semantic_evolution_report(base.problem_id)
    assert report["heads"] == [target_a.revision_id]
    assert target_b.revision_id not in report["revisions"]
    assert host_b.replay().canonical_hash() == canonical.canonical_hash()
    store_a.close()
    store_b.close()
