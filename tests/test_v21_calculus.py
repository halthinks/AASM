from __future__ import annotations

from pathlib import Path

import pytest

from aasm import (
    AASMEngine,
    ConflictRecord,
    DecisionRecord,
    ExplanationRecord,
    FairnessPolicy,
    LockRecord,
    MachineDefinition,
    ObligationRecord,
    PlanNode,
    ProblemSpec,
    RecoveryDecision,
    SQLiteStore,
)
from aasm.calculus import (
    LearnedConstraint,
    condition_holds,
    constraint_violated,
    default_calculus_state,
    project_constraint,
)
from aasm.persistence.serde import snapshot_from_dict


def test_legacy_snapshot_deserializes_with_empty_calculus():
    raw = {
        "machine_id": "m",
        "version": 0,
        "state": "INGEST",
        "problem": {"goal": "x", "objective": {}, "constraints": [], "invariants": [], "acceptance_tests": [], "features": {}},
        "graph": {"nodes": [], "edges": []},
        "frontier": [],
        "visited": [],
        "pruned": [],
        "memory": {},
        "resources": {},
        "evidence": {"claims": [], "observations": [], "contradictions": [], "assumptions": [], "records": []},
        "metadata": {},
    }
    assert snapshot_from_dict(raw).calculus == default_calculus_state()


def test_guarded_no_good_condition_semantics():
    values = {"database": "postgres", "mode": "isolated"}
    assert condition_holds(
        {
            "all": [
                {"decision": {"subject": "database", "op": "EQ", "value": "postgres"}},
                {"not": {"decision": {"subject": "mode", "op": "EQ", "value": "networked"}}},
            ]
        },
        values,
    )
    constraint = LearnedConstraint(
        "LC",
        [
            {"subject": "database", "op": "EQ", "value": "postgres"},
            {"subject": "mode", "op": "EQ", "value": "isolated"},
        ],
        "C",
        "X",
        ["E"],
        status="ACTIVE",
        validation="VALIDATED",
    ).to_dict()
    assert constraint_violated(constraint, values)


def test_lock_break_restores_obligation_after_model_change():
    engine = AASMEngine(ProblemSpec("locking"))
    engine.register_decision(DecisionRecord("D-pg", "database", "postgres"))
    engine.activate_decision("D-pg")
    engine.register_obligation(ObligationRecord(
        "O-sqlite",
        "Implement SQLite migration",
        activation_condition={"decision": {"subject": "database", "op": "EQ", "value": "sqlite"}},
    ))
    engine.lock_obligation(LockRecord(
        "L-sqlite",
        "O-sqlite",
        {"decision": {"subject": "database", "op": "EQ", "value": "postgres"}},
        "SQLite work is inactive under PostgreSQL",
        "D-pg",
    ))
    engine.register_decision(DecisionRecord("D-sqlite", "database", "sqlite"))
    result = engine.activate_decision("D-sqlite", supersede_decision_id="D-pg")
    report = engine.calculus_report()
    assert result["broken_lock_ids"] == ["L-sqlite"]
    assert report["locks"]["L-sqlite"]["status"] == "BROKEN"
    assert report["obligations"]["O-sqlite"]["status"] == "AVAILABLE"
    engine.enable_obligation("O-sqlite")
    assert engine.calculus_report()["obligations"]["O-sqlite"]["status"] == "ENABLED"


def _conflicted_engine(store=None):
    engine = AASMEngine(ProblemSpec("conflict learning"), store=store)
    engine.plan_add_node(PlanNode("schema-node", "task"))
    engine.plan_add_node(PlanNode("cache-node", "task"))
    engine.register_decision(DecisionRecord("D-db", "database", "postgres"))
    engine.activate_decision("D-db")
    engine.register_decision(DecisionRecord("D-schema", "schema", "v2", kind="DERIVED", parent_ids=["D-db"], plan_node_ids=["schema-node"]))
    engine.activate_decision("D-schema")
    engine.register_decision(DecisionRecord("D-cache", "cache", "memory", plan_node_ids=["cache-node"]))
    engine.activate_decision("D-cache")
    engine.register_decision(DecisionRecord("D-api", "api", "new", kind="DERIVED", parent_ids=["D-schema"], plan_node_ids=["schema-node"]))
    engine.activate_decision("D-api")
    engine.register_obligation(ObligationRecord(
        "O-schema",
        "Implement schema v2",
        decision_dependencies=["D-schema"],
        plan_node_ids=["schema-node"],
    ))
    engine.register_obligation(ObligationRecord(
        "O-cache",
        "Implement cache",
        decision_dependencies=["D-cache"],
        plan_node_ids=["cache-node"],
    ))
    evidence = engine.add_observation(
        "schema v2 violates the compatibility contract",
        source="integration-test",
        confidence=1.0,
        metadata={"evidence_type": "integration_test"},
    )
    engine.raise_conflict(ConflictRecord(
        "C-schema",
        "ASSUMPTION_CONFLICT",
        [evidence.evidence_id],
        implicated_decision_ids=["D-schema"],
        observed_at_obligation_id="O-schema",
    ))
    engine.register_explanation(ExplanationRecord(
        "X-schema",
        "C-schema",
        [{"subject": "schema", "op": "EQ", "value": "v2", "decision_id": "D-schema"}],
        [evidence.evidence_id],
        status="VALIDATED",
        minimality="IRREDUCIBLE",
        certificate={"type": "reproduction", "test": "integration"},
    ))
    learned = engine.learn_constraint("X-schema", "LC-schema")
    assert learned["strength"] == "SOFT"
    assert learned["assurance_status"] == "CERTIFICATE_REQUIRED"
    engine.register_projection_certificate("LC-schema", certificate_id="CERT-schema")
    verification = engine.verify_projection_certificate("CERT-schema")
    assert verification["valid"] is True
    promoted = engine.promote_constraint_hard("LC-schema", "CERT-schema")
    assert promoted["strength"] == "HARD"
    return engine


def test_strict_assurance_rejects_any_uncertified_hard_commit():
    engine = _conflicted_engine()
    state = engine.calculus_report()
    state["constraints"]["LC-schema"].pop("certificate_id")
    with pytest.raises(ValueError, match="UNCERTIFIED_HARD_CONSTRAINT"):
        engine._commit_calculus(state, "attempted assurance bypass")
    assert engine.calculus_report()["constraints"]["LC-schema"]["certificate_id"] == "CERT-schema"


def test_conflict_learning_and_graph_backjump_preserve_unrelated_later_work():
    engine = _conflicted_engine()
    result = engine.backjump_conflict("C-schema")
    report = engine.calculus_report()
    assert result["backjump"]["pivot_decision_id"] == "D-db"
    assert result["backjump"]["invalidated_decision_ids"] == ["D-api", "D-db", "D-schema"]
    assert report["decisions"]["D-cache"]["status"] == "ACTIVE"
    assert report["active_model"] == {"cache": "D-cache"}
    assert report["obligations"]["O-schema"]["status"] == "NEEDS_REVALIDATION"
    assert report["obligations"]["O-cache"]["status"] == "AVAILABLE"
    nodes = {node["node_id"]: node for node in engine.snapshot.graph["nodes"]}
    assert nodes["schema-node"]["status"] == "needs_revalidation"
    assert nodes["cache-node"]["status"] == "pending"
    assert engine.paused_tasks() == ["schema-node"]


def test_learned_constraint_survives_sqlite_resume_and_search_restart(tmp_path: Path):
    store = SQLiteStore(tmp_path / "calculus.db")
    engine = _conflicted_engine(store)
    engine.backjump_conflict("C-schema")
    machine_id = engine.snapshot.machine_id
    engine.restart_search(reason="diversify planning")
    store.close()

    store = SQLiteStore(tmp_path / "calculus.db")
    resumed = AASMEngine.resume(machine_id, store)
    report = resumed.calculus_report()
    assert report["constraints"]["LC-schema"]["status"] == "ACTIVE"
    assert report["conflicts"]["C-schema"]["status"] == "RESOLVED"
    assert report["active_model"] == {}
    store.close()


def test_hard_constraint_blocks_reconstruction_of_failed_model():
    engine = _conflicted_engine()
    engine.backjump_conflict("C-schema")
    engine.register_decision(DecisionRecord("D-schema-2", "schema", "v2"))
    with pytest.raises(ValueError, match="violates learned hard constraints"):
        engine.activate_decision("D-schema-2")


def test_fairness_blocks_unrelated_model_growth_until_review():
    engine = AASMEngine(ProblemSpec("fairness"))
    engine.configure_calculus_fairness(FairnessPolicy(
        max_hidden_epochs=1,
        max_lock_age_epochs=10,
        max_lock_count=10,
        max_deferral_epochs=2,
    ))
    engine.register_obligation(ObligationRecord(
        "O-needed",
        "Eventually select the needed branch",
        activation_condition={"decision": {"subject": "needed", "op": "EQ", "value": True}},
    ))
    engine.register_decision(DecisionRecord("D-a", "a", 1))
    engine.activate_decision("D-a")
    engine.register_decision(DecisionRecord("D-b", "b", 1))
    engine.activate_decision("D-b")
    assert engine.audit_calculus_fairness()["overdue"] == ["O-needed"]
    engine.register_decision(DecisionRecord("D-c", "c", 1))
    with pytest.raises(ValueError, match="fairness blocks model selection"):
        engine.activate_decision("D-c")
    engine.review_calculus_fairness(
        "O-needed",
        disposition_status="IMPOSSIBLE",
        disposition_reason="required capability is unavailable in this run",
    )
    engine.activate_decision("D-c")


def test_only_authoritative_planner_can_recover_when_pbv_is_configured():
    from aasm import TeamMember

    engine = _conflicted_engine()
    engine.initialize_team([
        TeamMember("planner", "PLANNER"),
        TeamMember("builder", "BUILDER"),
        TeamMember("verifier", "VERIFIER"),
    ])
    with pytest.raises(PermissionError):
        engine.planner_recover(RecoveryDecision("builder", "BACKJUMP", "C-schema", reason="not authorized"))
    result = engine.planner_recover(RecoveryDecision("planner", "BACKJUMP", "C-schema", reason="validated contradiction"))
    assert result["backjump"]["pivot_decision_id"] == "D-db"


def test_superseding_parent_suspends_active_dependent_decisions():
    engine = AASMEngine(ProblemSpec("supersession closure"))
    engine.register_decision(DecisionRecord("D-parent", "backend", "old"))
    engine.activate_decision("D-parent")
    engine.register_decision(DecisionRecord(
        "D-child", "adapter", "old-adapter", kind="DERIVED", parent_ids=["D-parent"]
    ))
    engine.activate_decision("D-child")
    engine.register_decision(DecisionRecord("D-new", "backend", "new"))
    result = engine.activate_decision("D-new", supersede_decision_id="D-parent")
    report = engine.calculus_report()
    assert result["suspended_dependent_decision_ids"] == ["D-child"]
    assert report["decisions"]["D-child"]["status"] == "SUSPENDED"
    assert report["active_model"] == {"backend": "D-new"}


def test_obligation_lifecycle_rejects_illegal_jump_to_commit():
    engine = AASMEngine(ProblemSpec("obligation lifecycle"))
    engine.register_obligation(ObligationRecord("O", "verified before commit"))
    with pytest.raises(ValueError, match="illegal obligation transition"):
        engine.set_obligation_status("O", "COMMITTED")


def test_invalidated_evidence_expires_learned_constraint():
    engine = _conflicted_engine()
    evidence_id = engine.calculus_report()["conflicts"]["C-schema"]["evidence_ids"][0]
    engine.invalidate_evidence(evidence_id, "test result was produced by an invalid fixture")
    report = engine.calculus_report()
    assert report["constraints"]["LC-schema"]["status"] == "EXPIRED"
    assert report["explanations"]["X-schema"]["status"] == "REJECTED"
    assert report["conflicts"]["C-schema"]["status"] == "REJECTED"


def test_complete_rejects_unresolved_mandatory_obligation():
    definition = MachineDefinition.from_dict({
        "name": "completion-gate",
        "start_state": "INGEST",
        "terminal_states": ["COMPLETE", "FAIL"],
        "transitions": {"INGEST": ["COMPLETE", "FAIL"], "COMPLETE": [], "FAIL": []},
    })
    engine = AASMEngine(ProblemSpec("complete only with disposition"), definition=definition)
    engine.register_obligation(ObligationRecord("O", "mandatory"))
    with pytest.raises(ValueError, match="unresolved mandatory obligations"):
        engine.transition("COMPLETE", "premature")
    engine.set_obligation_status("O", "IMPOSSIBLE", disposition_reason="proven unavailable")
    engine.transition("COMPLETE", "explicitly dispositioned")
    assert engine.state == "COMPLETE"
