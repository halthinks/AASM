from __future__ import annotations

from pathlib import Path
import pytest

from aasm import (
    AASMEngine, ProblemSpec, SQLiteStore, __version__, Claim, CausalDecisionRecord,
    ObligationRecord, ReactiveObligationRule, ReasoningProducer, SemanticDependency,
    SemanticNodeRef, TruthMaintenancePlan, run_semantic_dependency_conformance,
    semantic_dependency_contract, semantic_dependency_document, validate_public_api_contract,
)
from aasm.cli import build_parser
from aasm.evidence import EvidenceRecord
from aasm.semantic_dependencies import TRUTH_MAINTENANCE_CONTRACT_ID


def graph_fixture(engine: AASMEngine):
    observation = engine.add_evidence(EvidenceRecord("observation", "root observation", source="v38-test"))
    root = Claim("root claim", ReasoningProducer("agent-root", "PROPOSER"), evidence_ids=(observation.evidence_id,))
    dependent = Claim("dependent claim", ReasoningProducer("agent-dependent", "PROPOSER"), premise_artifact_ids=(root.artifact_id,))
    sibling = Claim("unrelated sibling", ReasoningProducer("agent-sibling", "PROPOSER"))
    engine.propose_artifact(root); engine.propose_artifact(dependent); engine.propose_artifact(sibling)
    decision = CausalDecisionRecord(decision_id="decision-v38-test", subject="mode", value="safe", caused_by_artifact_ids=[dependent.artifact_id], rejected_alternatives=[{"value": "fast", "reason": "less support"}], confidence=0.91, reasoning="dependent claim selects safe mode")
    engine.register_causal_decision(decision); engine.activate_decision(decision.decision_id)
    rule = ReactiveObligationRule(rule_id="rule-v38-test", watch_event_types=("snapshot_patched",), statement="revalidate mode after durable state change", handler_name="revalidate-mode", decision_dependencies=(decision.decision_id,), once=True)
    engine.register_reactive_obligation_rule(rule, authority_id="policy-v38", authority_class="POLICY")
    derived = engine.derive_reactive_obligations(); assert derived["created"]
    obligation_id = derived["created"][0]["obligation"]["obligation_id"]
    return root, dependent, sibling, decision, rule, obligation_id, observation


def commit_reactive_obligation(engine: AASMEngine, obligation_id: str):
    engine.enable_obligation(obligation_id); engine.set_obligation_status(obligation_id, "IN_PROGRESS"); engine.set_obligation_status(obligation_id, "VERIFYING"); engine.set_obligation_status(obligation_id, "VERIFIED"); engine.set_obligation_status(obligation_id, "COMMITTED")


def test_v38_contract_version_and_public_surface():
    contract = semantic_dependency_contract(); assert contract["contract_id"] == "aasm.semantic.dependencies.v1"; assert contract["truth_maintenance_contract_id"] == "aasm.truth.maintenance.v1"; assert contract["reactive_obligation_contract_id"] == "aasm.reactive.obligation.v1"; assert contract["causal_decision_contract_id"] == "aasm.causal.decision.v1"; assert contract["truth_change_policy"] == "AFFECTED_DESCENDANTS_ONLY"; assert contract["unrelated_sibling_policy"] == "PRESERVE"; assert contract["reactive_policy"] == "DERIVE_OBLIGATION_NEVER_EXECUTE_HANDLER"
    report = validate_public_api_contract(); assert report["valid"] is True, report; assert report["contract"]["runtime_version"] == __version__; assert report["contract"]["contract_version"]


def test_derived_graph_connects_artifact_causal_decision_and_reactive_obligation():
    engine = AASMEngine(ProblemSpec("v38 graph")); root, dependent, sibling, decision, _, obligation_id, _ = graph_fixture(engine); graph = engine.semantic_dependency_graph(); assert graph["valid"] is True, graph["issues"]
    keys = {row["key"] for row in engine.semantic_dependency_impact("ARTIFACT", root.artifact_id)["affected_nodes"]}; assert f"ARTIFACT:{dependent.artifact_id}" in keys; assert f"DECISION:{decision.decision_id}" in keys; assert f"OBLIGATION:{obligation_id}" in keys; assert f"ARTIFACT:{sibling.artifact_id}" not in keys


def test_propagating_cycle_is_rejected_but_descriptive_cycle_is_allowed():
    engine = AASMEngine(ProblemSpec("v38 cycles")); root, dependent, _, _, _, _, _ = graph_fixture(engine)
    with pytest.raises(ValueError, match="PROPAGATING_CYCLE"):
        engine.register_semantic_dependency(SemanticDependency(SemanticNodeRef("ARTIFACT", dependent.artifact_id), SemanticNodeRef("ARTIFACT", root.artifact_id), "DEPENDS_ON", True), authority_id="policy", authority_class="POLICY")
    allowed = engine.register_semantic_dependency(SemanticDependency(SemanticNodeRef("ARTIFACT", dependent.artifact_id), SemanticNodeRef("ARTIFACT", root.artifact_id), "SUPPORTS", False), authority_id="policy", authority_class="POLICY"); assert allowed["dependency"]["propagates_stale"] is False; assert engine.semantic_dependency_graph()["valid"] is True


def test_dependency_admission_requires_policy_authority():
    engine = AASMEngine(ProblemSpec("v38 dependency authority")); root, dependent, _, _, _, _, _ = graph_fixture(engine); edge = SemanticDependency(SemanticNodeRef("ARTIFACT", root.artifact_id), SemanticNodeRef("ARTIFACT", dependent.artifact_id), "SUPPORTS", False)
    with pytest.raises(PermissionError, match="POLICY or CONTROLLER"): engine.register_semantic_dependency(edge, authority_id="agent", authority_class="PROPOSER")


def test_causal_decision_rejects_unknown_event_and_artifact_provenance():
    engine = AASMEngine(ProblemSpec("v38 causal provenance"))
    with pytest.raises(KeyError, match="causal event"): engine.register_causal_decision(CausalDecisionRecord(decision_id="bad-event", subject="x", value=1, caused_by_event_ids=["event-missing"]))
    with pytest.raises(KeyError, match="causal artifact"): engine.register_causal_decision(CausalDecisionRecord(decision_id="bad-artifact", subject="x", value=1, caused_by_artifact_ids=["artifact-missing"]))


def test_reactive_rules_derive_obligations_but_never_execute_handlers():
    engine = AASMEngine(ProblemSpec("v38 reactive")); _, _, _, _, rule, obligation_id, _ = graph_fixture(engine); report = engine.reactive_obligation_report(); assert report["handler_execution"] == "NONE"; assert report["obligations"][obligation_id]["handler_name"] == rule.handler_name
    second = engine.derive_reactive_obligations(); assert second["created"] == []; assert second["handler_execution"] == "NONE"


def test_truth_maintenance_is_descendant_only_reopens_consumed_work_and_is_idempotent():
    engine = AASMEngine(ProblemSpec("v38 truth")); root, dependent, sibling, decision, _, obligation_id, observation = graph_fixture(engine); commit_reactive_obligation(engine, obligation_id)
    first = engine.apply_truth_change("ARTIFACT", root.artifact_id, reason="root evidence no longer valid", authority_id="verifier-v38", authority_class="VERIFIER", evidence_ids=[observation.evidence_id]); assert first["already_applied"] is False
    reasoning = engine.reasoning_report(); calculus = engine.calculus_report(); assert reasoning["artifacts"][root.artifact_id]["state"] == "STALE"; assert reasoning["artifacts"][dependent.artifact_id]["state"] == "STALE"; assert reasoning["artifacts"][sibling.artifact_id]["state"] == "PROPOSED"; assert calculus["decisions"][decision.decision_id]["status"] == "INVALIDATED"; assert calculus["obligations"][obligation_id]["status"] == "NEEDS_REVALIDATION"; assert first["application"]["handler_execution"] == "NONE"
    second = engine.apply_truth_change("ARTIFACT", root.artifact_id, reason="root evidence no longer valid", authority_id="verifier-v38", authority_class="VERIFIER", evidence_ids=[observation.evidence_id]); assert second["already_applied"] is True; assert second["plan"]["plan_id"] == first["plan"]["plan_id"]


def test_available_obligation_is_preserved_until_it_has_consumed_stale_truth():
    engine = AASMEngine(ProblemSpec("v38 available")); root, dependent, _, decision, _, _, observation = graph_fixture(engine); obligation = ObligationRecord(obligation_id="available-obligation", statement="future work", decision_dependencies=[decision.decision_id], status="AVAILABLE"); engine.register_obligation(obligation)
    assert f"OBLIGATION:{obligation.obligation_id}" in {row["key"] for row in engine.semantic_dependency_impact("ARTIFACT", root.artifact_id)["affected_nodes"]}
    engine.apply_truth_change("ARTIFACT", root.artifact_id, reason="invalidate before work begins", authority_id="verifier", authority_class="VERIFIER", evidence_ids=[observation.evidence_id]); assert engine.calculus_report()["obligations"][obligation.obligation_id]["status"] == "AVAILABLE"; assert engine.reasoning_report(dependent.artifact_id)["state"] == "STALE"


def test_pending_truth_plan_survives_sqlite_restart_and_resumes(tmp_path: Path):
    path = tmp_path / "v38.db"; store = SQLiteStore(str(path)); engine = AASMEngine(ProblemSpec("v38 restart"), store=store); machine_id = engine.snapshot.machine_id; root, _, _, _, _, _, observation = graph_fixture(engine); graph = engine.semantic_dependency_graph(); impact = engine.semantic_dependency_impact("ARTIFACT", root.artifact_id)
    plan = TruthMaintenancePlan(root=SemanticNodeRef("ARTIFACT", root.artifact_id), affected_nodes=tuple(SemanticNodeRef(row["node_type"], row["node_id"]) for row in impact["affected_nodes"]), reason="pending restart fixture", authority_id="verifier", authority_class="VERIFIER", graph_fingerprint=graph["graph_fingerprint"], evidence_ids=(observation.evidence_id,))
    engine.add_evidence(EvidenceRecord(kind="truth_maintenance_plan", statement=semantic_dependency_document(plan), source=TRUTH_MAINTENANCE_CONTRACT_ID, derived_from=[observation.evidence_id], metadata={"semantic_dependency_record_type": "TRUTH_PLAN", "truth_contract_id": TRUTH_MAINTENANCE_CONTRACT_ID, "plan_id": plan.plan_id, "plan_fingerprint": plan.fingerprint})); assert plan.plan_id in engine.truth_maintenance_report()["pending_plan_ids"]; store.close()
    resumed_store = SQLiteStore(str(path)); resumed = AASMEngine.resume(machine_id, resumed_store); applied = resumed.resume_truth_maintenance(plan.plan_id); assert applied["already_applied"] is False; assert resumed.reasoning_report(root.artifact_id)["state"] == "STALE"; assert plan.plan_id not in resumed.truth_maintenance_report()["pending_plan_ids"]; assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash(); resumed_store.close()


def test_lineage_and_v40_memory_signal_projection_are_deterministic():
    engine = AASMEngine(ProblemSpec("v38 memory signals")); root, _, _, _, _, obligation_id, _ = graph_fixture(engine); lineage = engine.semantic_dependency_lineage("OBLIGATION", obligation_id); assert any(row["key"] == f"ARTIFACT:{root.artifact_id}" for row in lineage["lineage"])
    first = engine.semantic_memory_projection_signals(); second = engine.semantic_memory_projection_signals(); assert first == second; root_signal = first["signals"][f"ARTIFACT:{root.artifact_id}"]; assert set(("VALID", "STALE", "REFUTED", "AUTHORIZED", "scope_visibility", "dependency_depth", "causal_relevance", "objective_relevance", "last_verified_at", "verification_strength", "superseded_by")).issubset(root_signal)


def test_v38_conformance_and_cli_are_visible():
    report = run_semantic_dependency_conformance(); assert report["status"] == "PASS", report; assert all(report["checks"].values()); help_text = build_parser().format_help()
    for name in ("semantic-dependency-contract", "semantic-dependency-conformance", "dependency-graph", "dependency-impact", "dependency-lineage", "dependency-add", "causal-decision-add", "reactive-rule-add", "reactive-derive", "reactive-obligations", "truth-maintain", "truth-resume", "truth-maintenance-report", "semantic-memory-signals"): assert name in help_text
