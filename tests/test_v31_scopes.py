from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, RefResolver

from aasm import (
    AASMEngine,
    CandidateModel,
    ConflictRecord,
    DecisionRecord,
    DecisionScope,
    EvidenceRecord,
    ExplanationRecord,
    LockRecord,
    ObligationRecord,
    ProblemSpec,
    ScopeDependency,
    SQLiteStore,
    build_scope_report,
    validate_public_api_contract,
)
from aasm.decision_backends import CandidateLifecycleRecord

ROOT = Path(__file__).resolve().parents[1]


def hierarchy() -> tuple[AASMEngine, dict[str, str]]:
    engine = AASMEngine(ProblemSpec("hierarchical delivery"))
    for scope in [
        DecisionScope("strategy", "Strategy", kind="STRATEGY"),
        DecisionScope("architecture-a", "Architecture A", kind="ARCHITECTURE", parent_scope_id="strategy"),
        DecisionScope("implementation-a", "Implementation A", kind="IMPLEMENTATION", parent_scope_id="architecture-a"),
        DecisionScope("architecture-b", "Architecture B", kind="ARCHITECTURE", parent_scope_id="strategy"),
        DecisionScope("implementation-b", "Implementation B", kind="IMPLEMENTATION", parent_scope_id="architecture-b"),
    ]:
        engine.register_scope(scope)
    decisions = {
        "strategy": "D-strategy",
        "architecture-a": "D-architecture-a",
        "implementation-a": "D-implementation-a",
        "architecture-b": "D-architecture-b",
        "implementation-b": "D-implementation-b",
    }
    parent = None
    for scope_id in ["strategy", "architecture-a", "implementation-a"]:
        decision_id = decisions[scope_id]
        engine.register_decision(
            DecisionRecord(
                decision_id,
                scope_id.replace("-", "_"),
                "active",
                parent_ids=[] if parent is None else [parent],
                scope={"scope_id": scope_id},
            )
        )
        engine.activate_decision(decision_id)
        parent = decision_id
    parent = decisions["strategy"]
    for scope_id in ["architecture-b", "implementation-b"]:
        decision_id = decisions[scope_id]
        engine.register_decision(
            DecisionRecord(
                decision_id,
                scope_id.replace("-", "_"),
                "active",
                parent_ids=[parent],
                scope={"scope_id": scope_id},
            )
        )
        engine.activate_decision(decision_id)
        parent = decision_id
    return engine, decisions


def add_candidate(engine: AASMEngine, candidate: CandidateModel) -> None:
    report = engine.validate_candidate_model(candidate)
    state = engine._candidate_state()
    state["candidates"][candidate.candidate_id] = CandidateLifecycleRecord(
        candidate=candidate.to_dict(),
        status="ADMISSIBLE" if report.valid else "REJECTED",
        validation=report.to_dict(),
        rejection_reasons=list(report.errors),
        proposed_sequence=engine._sequence() + 1,
    ).to_dict()
    engine.patch_snapshot({"candidate_state": state}, "test candidate registered")


def test_default_root_scope_preserves_flat_active_model() -> None:
    engine = AASMEngine(ProblemSpec("flat"))
    engine.register_decision(DecisionRecord("D-root", "database", "postgres"))
    engine.activate_decision("D-root")
    calculus = engine.calculus_report()
    assert calculus["active_model"] == {"database": "D-root"}
    report = engine.scope_report()
    assert report["root_scope_id"] == "root"
    assert report["scopes"][0]["local_active_model"] == {"database": "D-root"}


def test_register_hierarchy_and_effective_inheritance() -> None:
    engine, _ = hierarchy()
    report = engine.scope_report()
    by_id = {row["scope_id"]: row for row in report["scopes"]}
    assert report["scope_count"] == 6
    assert by_id["strategy"]["descendant_scope_ids"] == [
        "architecture-a", "architecture-b", "implementation-a", "implementation-b"
    ]
    assert by_id["implementation-a"]["ancestor_scope_ids"] == [
        "root", "strategy", "architecture-a"
    ]


def test_hierarchy_cycle_is_rejected() -> None:
    engine = AASMEngine(ProblemSpec("cycles"))
    engine.register_scope(DecisionScope("a", "A"))
    engine.register_scope(DecisionScope("b", "B", parent_scope_id="a"))
    with pytest.raises(ValueError, match="cycle"):
        engine.register_scope_dependency(
            ScopeDependency("SD-cycle", "b", "a", relation="DEPENDS_ON")
        )


def test_dependency_cycle_is_rejected() -> None:
    engine = AASMEngine(ProblemSpec("dependency cycles"))
    engine.register_scope(DecisionScope("a", "A"))
    engine.register_scope(DecisionScope("b", "B"))
    engine.register_scope_dependency(ScopeDependency("SD-ab", "a", "b"))
    with pytest.raises(ValueError, match="cycle"):
        engine.register_scope_dependency(ScopeDependency("SD-ba", "b", "a"))


def test_effective_context_inherits_parent_decisions() -> None:
    engine, decisions = hierarchy()
    context = engine.effective_scope_context("implementation-a")
    assert context["effective_active_model"] == {
        "strategy": decisions["strategy"],
        "architecture_a": decisions["architecture-a"],
        "implementation_a": decisions["implementation-a"],
    }


def test_explicit_override_is_required() -> None:
    engine = AASMEngine(ProblemSpec("override"))
    engine.register_scope(DecisionScope("strategy", "Strategy", kind="STRATEGY"))
    engine.register_scope(DecisionScope("implementation", "Implementation", kind="IMPLEMENTATION", parent_scope_id="strategy"))
    engine.register_decision(DecisionRecord("D-parent", "database", "postgres", scope={"scope_id": "strategy"}))
    engine.activate_decision("D-parent")
    engine.register_decision(DecisionRecord("D-child", "database", "sqlite", scope={"scope_id": "implementation"}))
    with pytest.raises(ValueError, match="explicit scope override"):
        engine.activate_decision("D-child")


def test_deny_override_policy_is_enforced() -> None:
    engine = AASMEngine(ProblemSpec("deny override"))
    engine.register_scope(DecisionScope("strategy", "Strategy", kind="STRATEGY"))
    engine.register_scope(DecisionScope("implementation", "Implementation", kind="IMPLEMENTATION", parent_scope_id="strategy", override_policy="DENY"))
    engine.register_decision(DecisionRecord("D-parent", "database", "postgres", scope={"scope_id": "strategy"}))
    engine.activate_decision("D-parent")
    engine.register_decision(DecisionRecord("D-child", "database", "sqlite", scope={"scope_id": "implementation", "override": True}))
    with pytest.raises(ValueError, match="denies override"):
        engine.activate_decision("D-child")


def test_sibling_evidence_is_blocked_without_dependency() -> None:
    engine, _ = hierarchy()
    evidence = engine.add_evidence(EvidenceRecord("observation", "A passed", evidence_id="E-a", metadata={"scope_id": "implementation-a"}))
    engine.register_obligation(ObligationRecord("O-b", "Verify B", required_evidence_types=["observation"], scope={"scope_id": "implementation-b"}))
    engine.enable_obligation("O-b")
    engine.set_obligation_status("O-b", "IN_PROGRESS")
    engine.set_obligation_status("O-b", "VERIFYING")
    with pytest.raises(ValueError, match="cannot flow"):
        engine.set_obligation_status("O-b", "VERIFIED", evidence_ids=[evidence.evidence_id])


def test_dependency_allows_sibling_evidence_flow() -> None:
    engine, _ = hierarchy()
    evidence = engine.add_evidence(EvidenceRecord("observation", "A passed", evidence_id="E-a", metadata={"scope_id": "implementation-a"}))
    engine.register_scope_dependency(ScopeDependency("SD-a-b", "implementation-a", "implementation-b", evidence_ids=[evidence.evidence_id]))
    engine.register_obligation(ObligationRecord("O-b", "Verify B", required_evidence_types=["observation"], scope={"scope_id": "implementation-b"}))
    engine.enable_obligation("O-b")
    engine.set_obligation_status("O-b", "IN_PROGRESS")
    engine.set_obligation_status("O-b", "VERIFYING")
    result = engine.set_obligation_status("O-b", "VERIFIED", evidence_ids=[evidence.evidence_id])
    assert result["status"] == "VERIFIED"


def test_cross_scope_backjump_invalidates_causal_branch_and_preserves_sibling() -> None:
    engine, decisions = hierarchy()
    evidence = engine.add_evidence(EvidenceRecord("contradiction", "branch A failed", evidence_id="E-conflict", metadata={"scope_id": "implementation-a"}))
    engine.raise_conflict(ConflictRecord("C-a", "ASSUMPTION_CONFLICT", [evidence.evidence_id], implicated_decision_ids=[decisions["architecture-a"]], scope={"scope_id": "implementation-a"}))
    engine.register_explanation(ExplanationRecord("X-a", "C-a", [{"subject": "architecture_a", "op": "EQ", "value": "active", "decision_id": decisions["architecture-a"]}], [evidence.evidence_id], status="VALIDATED", scope={"scope_id": "implementation-a"}))
    result = engine.backjump_conflict("C-a", explanation_id="X-a")
    plan = result["backjump"]
    assert plan["pivot_scope_id"] == "architecture-a"
    assert plan["invalidated_scope_ids"] == ["architecture-a", "implementation-a"]
    assert "architecture-b" in plan["preserved_scope_ids"]
    state = engine.calculus_report()
    assert state["decisions"][decisions["architecture-a"]]["status"] == "INVALIDATED"
    assert state["decisions"][decisions["implementation-b"]]["status"] == "ACTIVE"


def test_scoped_restart_preserves_parent_sibling_and_pinned_decisions() -> None:
    engine, decisions = hierarchy()
    evidence = engine.add_evidence(EvidenceRecord("observation", "retained", evidence_id="E-retained", metadata={"scope_id": "implementation-a"}))
    result = engine.restart_scope("architecture-a")
    assert decisions["architecture-a"] in result["suspended_decision_ids"]
    assert "architecture-b" in result["preserved_scope_ids"]
    state = engine.calculus_report()
    assert state["decisions"][decisions["strategy"]]["status"] == "ACTIVE"
    assert state["decisions"][decisions["implementation-b"]]["status"] == "ACTIVE"
    assert evidence.evidence_id in {row["evidence_id"] for row in engine.snapshot.evidence["records"]}


def test_atomic_multi_scope_candidate_activation_succeeds() -> None:
    engine = AASMEngine(ProblemSpec("candidate"))
    engine.register_scope(DecisionScope("strategy", "Strategy", kind="STRATEGY"))
    engine.register_scope(DecisionScope("architecture", "Architecture", kind="ARCHITECTURE", parent_scope_id="strategy"))
    engine.register_decision(DecisionRecord("D-s", "strategy_choice", "ship", scope={"scope_id": "strategy"}))
    engine.register_decision(DecisionRecord("D-a", "architecture_choice", "api", parent_ids=["D-s"], scope={"scope_id": "architecture"}))
    candidate = CandidateModel("candidate-good", {"strategy::strategy_choice": "D-s", "architecture::architecture_choice": "D-a"}, "test", "1")
    add_candidate(engine, candidate)
    result = engine.activate_candidate(candidate.candidate_id)
    assert result["scope_active_models"]["strategy"] == {"strategy_choice": "D-s"}
    assert result["scope_active_models"]["architecture"] == {"architecture_choice": "D-a"}


def test_multi_scope_candidate_failure_commits_nothing() -> None:
    engine = AASMEngine(ProblemSpec("candidate atomicity"))
    engine.register_scope(DecisionScope("architecture", "Architecture", kind="ARCHITECTURE"))
    engine.register_scope(DecisionScope("implementation", "Implementation", kind="IMPLEMENTATION", parent_scope_id="architecture"))
    engine.register_decision(DecisionRecord("D-old", "architecture_choice", "old", scope={"scope_id": "architecture"}))
    engine.activate_decision("D-old")
    engine.register_decision(DecisionRecord("D-child", "implementation_choice", "child", parent_ids=["D-old"], scope={"scope_id": "implementation"}))
    engine.register_decision(DecisionRecord("D-new", "architecture_choice", "new", scope={"scope_id": "architecture"}))
    candidate = CandidateModel("candidate-bad", {"architecture::architecture_choice": "D-new", "implementation::implementation_choice": "D-child"}, "test", "1")
    report = engine.validate_candidate_model(candidate)
    assert report.valid is False
    state = engine.calculus_report()
    assert state["decisions"]["D-old"]["status"] == "ACTIVE"
    assert state["decisions"]["D-new"]["status"] == "PROPOSED"
    assert state["decisions"]["D-child"]["status"] == "PROPOSED"


def test_legacy_scope_migration_is_evented_and_replayable() -> None:
    engine = AASMEngine(ProblemSpec("migration"))
    engine.register_decision(DecisionRecord("D-root", "mode", "legacy"))
    result = engine.migrate_legacy_scopes()
    assert result["legacy_flat_state_migrated"] is True
    replayed = engine.replay()
    assert replayed.calculus["scope_state"]["migration"]["legacy_flat_state_migrated"] is True
    assert replayed.calculus["decisions"]["D-root"]["scope"]["scope_id"] == "root"


def test_scope_schemas_accept_runtime_output() -> None:
    engine, _ = hierarchy()
    report = engine.scope_report()
    store = {
        path.name: json.loads(path.read_text())
        for path in (ROOT / "schemas").glob("*.schema.json")
    }
    resolver = RefResolver.from_schema(store["scope-report.schema.json"], store={schema.get("$id", name): schema for name, schema in store.items()} | {name: schema for name, schema in store.items()})
    Draft202012Validator(store["scope-report.schema.json"], resolver=resolver).validate(report)


def test_scope_cli_and_adoption_contract_are_visible() -> None:
    from aasm.cli import build_parser

    parser = build_parser()
    help_text = parser.format_help()
    assert "scope-report" in help_text
    contract = validate_public_api_contract()
    assert contract["valid"] is True
    assert contract["contract"]["scopes"] == {
        **contract["contract"]["scopes"]
    }
    assert contract["contract"]["scopes"]["contract_id"] == "aasm.scopes.v1"


def test_sqlite_resume_retains_scope_state_and_exact_replay(tmp_path: Path) -> None:
    store = SQLiteStore(str(tmp_path / "scopes.db"))
    engine = AASMEngine(ProblemSpec("sqlite scopes"), store=store)
    machine_id = engine.snapshot.machine_id
    engine.register_scope(DecisionScope("strategy", "Strategy", kind="STRATEGY"))
    engine.register_decision(DecisionRecord("D-s", "mode", "safe", scope={"scope_id": "strategy"}))
    engine.activate_decision("D-s")
    resumed = AASMEngine.resume(machine_id, store)
    assert resumed.effective_scope_context("strategy")["effective_values"] == {"mode": "safe"}
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()


def test_scope_report_helper_matches_engine_surface() -> None:
    engine, _ = hierarchy()
    assert build_scope_report(engine.snapshot.calculus) == engine.inspect_machine("scopes")
    assert engine.inspect_machine("scope-hierarchy")["contract_id"] == "aasm.scopes.v1"
