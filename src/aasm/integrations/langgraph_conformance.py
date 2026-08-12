from __future__ import annotations

"""Reference v0.30 conformance driver for the v0.29 LangGraph adapter."""

from copy import deepcopy
from typing import Any

from ..effects import EffectUnknownOutcome
from ..graph import PlanEdge, PlanNode
from ..resources import ResourceRecord, TaskDemand
from ..semantic_result import ProducerRef, SemanticResultEnvelope
from ..workers import WorkerRecord
from .conformance import (
    ADAPTER_CONFORMANCE_VERSION,
    CONFORMANCE_SCENARIOS,
    AdapterCapabilityDeclaration,
    AdapterConformanceContext,
    AdapterScenarioOutcome,
)
from .langgraph import (
    LANGGRAPH_ADAPTER_ID,
    LANGGRAPH_ADAPTER_VERSION,
    LangGraphAdapter,
    LangGraphRecoveryAction,
)


LANGGRAPH_CONFORMANCE_DRIVER_ID = "aasm.langgraph.conformance.v1"
LANGGRAPH_CONFORMANCE_DRIVER_VERSION = "0.1.0"


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}}


class LangGraphConformanceDriver:
    def capability_declaration(self) -> AdapterCapabilityDeclaration:
        return AdapterCapabilityDeclaration(
            adapter_id=LANGGRAPH_ADAPTER_ID,
            adapter_version=LANGGRAPH_ADAPTER_VERSION,
            driver_id=LANGGRAPH_CONFORMANCE_DRIVER_ID,
            driver_version=LANGGRAPH_CONFORMANCE_DRIVER_VERSION,
            scenarios={scenario: True for scenario in CONFORMANCE_SCENARIOS},
            authority={
                "machine_truth_authority": "AASM_EVENT_HISTORY",
                "framework_state_authority": "LANGGRAPH_CHECKPOINTS",
                "decision_authority": "AASM",
                "effect_authority": "AASM",
                "worker_lease_authority": "AASM",
                "recovery_authority": "AASM",
                "direct_storage_writes": False,
                "duplicate_authorities": [],
                "uses_public_aasm_api": True,
            },
            recovery_actions=[
                action.value for action in LangGraphRecoveryAction
            ],
            notes=[
                f"evaluated by {ADAPTER_CONFORMANCE_VERSION}",
                "LangGraph keeps graph/checkpoint state; AASM keeps machine truth",
            ],
        )

    @staticmethod
    def _adapter(context: AdapterConformanceContext) -> LangGraphAdapter:
        return LangGraphAdapter(
            store=context.store,
            namespace=context.namespace,
            engine_class=context.engine_class,
        )

    @staticmethod
    def _report(adapter: LangGraphAdapter, engine: Any) -> dict[str, Any]:
        return adapter.integration_report(engine)

    def _success(self, context: AdapterConformanceContext) -> AdapterScenarioOutcome:
        adapter = self._adapter(context)
        config = _config("success")

        def increment(state):
            return {"value": int(state["value"]) + 1, "preserved": state.get("preserved")}

        original = {"value": 4, "preserved": "framework-state"}
        output = adapter.wrap_node("increment", increment)(original, config)
        engine, _binding = adapter.bind(config)
        obligation = next(iter(engine.calculus_report()["obligations"].values()))
        evidence_id = obligation["evidence_ids"][0]
        semantic = engine.record_semantic_result(
            SemanticResultEnvelope(
                result_id="SR-langgraph-success",
                producer=ProducerRef(
                    "adapter",
                    LANGGRAPH_ADAPTER_ID,
                    version=LANGGRAPH_ADAPTER_VERSION,
                    authority="AASM_EVENT_HISTORY",
                ),
                subject_ids=[obligation["obligation_id"]],
                classification="PASS",
                summary="LangGraph node output was durably evidenced and committed.",
                claims=[{"statement": "original node output was preserved"}],
                evidence=[{"evidence_id": evidence_id}],
                metadata={"conformance_scenario": "success"},
            ),
            reason="adapter conformance semantic result recorded",
        )
        return AdapterScenarioOutcome(
            "success",
            engine.snapshot.machine_id,
            observations={
                "input": original,
                "output": output,
                "original_output_preserved": output
                == {"value": 5, "preserved": "framework-state"},
                "obligation_id": obligation["obligation_id"],
                "semantic_result_id": semantic["result_id"],
            },
            adapter_report=self._report(adapter, engine),
            evidence_ids=[evidence_id],
            framework_state={"checkpoint_owner": "LANGGRAPH", "output": output},
        )

    def _contradiction(self, context: AdapterConformanceContext) -> AdapterScenarioOutcome:
        adapter = self._adapter(context)
        config = _config("contradiction")
        engine, _binding = adapter.bind(config)
        root = adapter.record_decision(
            engine,
            decision_id="D-db",
            subject="database",
            value="postgres",
        )
        schema = adapter.record_decision(
            engine,
            decision_id="D-schema-v2",
            subject="schema",
            value="v2",
            kind="DERIVED",
            parent_ids=[root["decision_id"]],
        )
        adapter.record_decision(
            engine,
            decision_id="D-cache",
            subject="cache",
            value="memory",
        )
        obligation = adapter.record_obligation(
            engine,
            obligation_id="O-schema",
            statement="Verify schema v2 compatibility",
            decision_dependencies=[schema["decision_id"]],
        )
        learned = adapter.record_conflict(
            engine,
            statement="schema v2 violates the compatibility fixture",
            implicated_decision_ids=[schema["decision_id"]],
            observed_at_obligation_id=obligation["obligation_id"],
        )
        adapter.record_decision(
            engine,
            decision_id="D-schema-repeat",
            subject="schema",
            value="v2",
            activate=False,
        )
        repeat_blocked = False
        try:
            engine.activate_decision("D-schema-repeat")
        except ValueError as exc:
            repeat_blocked = "violates learned hard constraints" in str(exc)
        calculus = engine.calculus_report()
        recovery = learned.get("recovery") or {}
        backjump = recovery.get("backjump") or {}
        return AdapterScenarioOutcome(
            "contradiction",
            engine.snapshot.machine_id,
            observations={
                **{key: learned.get(key) for key in (
                    "conflict_id",
                    "explanation_id",
                    "constraint_id",
                    "certificate_id",
                    "evidence_id",
                )},
                "backjump_target": backjump.get("pivot_decision_id"),
                "unrelated_work_preserved": calculus["decisions"]["D-cache"]["status"] == "ACTIVE",
                "repeat_blocked": repeat_blocked,
            },
            adapter_report=self._report(adapter, engine),
            evidence_ids=[learned["evidence_id"]],
        )

    def _requirement_change(self, context: AdapterConformanceContext) -> AdapterScenarioOutcome:
        adapter = self._adapter(context)
        config = _config("requirement-change")
        engine, _binding = adapter.bind(config)
        engine.plan_add_node(PlanNode("design-core", "design", status="in_progress"))
        engine.plan_add_node(PlanNode("update-tests", "verification", status="pending"))
        engine.plan_add_node(PlanNode("publish-notes", "documentation", status="complete"))
        engine.plan_add_edge(PlanEdge("design-core", "update-tests"))
        response = engine.user_interrupt(
            "Require deterministic serialization for the core design.",
            metadata={
                "seed_nodes": ["design-core"],
                "requirement_id": "REQ-deterministic-serialization",
            },
        )
        impact = response["impact"]
        affected = set(impact["affected_nodes"])
        unaffected = set(impact["unaffected_nodes"])
        paused = set(engine.paused_tasks())
        resolved = engine.resolve_change_impact(
            "conformance-operator",
            impact["impact_id"],
            resume_nodes=impact["affected_nodes"],
            retire_nodes=[],
            reason="conformance requirement accepted and affected work resumed",
        )
        node_status = {
            row["node_id"]: row["status"]
            for row in engine.snapshot.graph.get("nodes", [])
        }
        return AdapterScenarioOutcome(
            "requirement_change",
            engine.snapshot.machine_id,
            observations={
                "impact_id": impact["impact_id"],
                "affected_nodes": sorted(affected),
                "unaffected_nodes": sorted(unaffected),
                "affected_region_identified": affected == {"design-core", "update-tests"},
                "unrelated_work_preserved": "publish-notes" in unaffected
                and node_status["publish-notes"] == "complete",
                "only_affected_region_paused": paused == affected,
                "impact_resolved": resolved["status"] == "RESOLVED",
                "plan_resumed": engine.paused_tasks() == [],
            },
            adapter_report=self._report(adapter, engine),
        )

    def _lease_loss(self, context: AdapterConformanceContext) -> AdapterScenarioOutcome:
        adapter = self._adapter(context)
        config = _config("lease-loss")
        engine, _binding = adapter.bind(config)
        engine.register_resource(
            ResourceRecord(
                "conformance-worker-pool",
                "local-process",
                capabilities=["conformance.execute"],
                capacity=1.0,
            )
        )
        engine.register_worker(
            WorkerRecord(
                "worker-lost",
                "conformance-worker-pool",
                heartbeat_timeout=2.0,
                last_heartbeat=1000.0,
            )
        )
        engine.register_worker(
            WorkerRecord(
                "worker-recovery",
                "conformance-worker-pool",
                heartbeat_timeout=5.0,
                last_heartbeat=1003.0,
            )
        )
        task = TaskDemand(
            "conformance-lease-task",
            required_capabilities=["conformance.execute"],
        )
        first = engine.claim_task(
            task, "worker-lost", lease_seconds=2.0, at_time=1000.0
        )
        stale = engine.reap_stale_workers(at_time=1003.0)
        engine.worker_heartbeat("worker-recovery", at_time=1003.0)
        second = engine.claim_task(
            task, "worker-recovery", lease_seconds=10.0, at_time=1003.0
        )
        completed = engine.complete_lease(
            second["lease_id"],
            result={"recovered": True, "source_lease_id": first["lease_id"]},
            at_time=1004.0,
        )
        leases = {row["lease_id"]: row for row in engine.list_leases()}
        return AdapterScenarioOutcome(
            "lease_loss",
            engine.snapshot.machine_id,
            observations={
                "stale_worker_detected": "worker-lost" in stale,
                "lost_lease_expired": leases[first["lease_id"]]["status"] == "EXPIRED",
                "task_reclaimed": second["lease_id"] != first["lease_id"],
                "attempt_incremented": int(second["attempt"]) == 2,
                "recovery_lease_completed": completed["status"] == "COMPLETED",
                "first_lease_id": first["lease_id"],
                "second_lease_id": second["lease_id"],
            },
            adapter_report=self._report(adapter, engine),
        )

    def _unknown_effect(self, context: AdapterConformanceContext) -> AdapterScenarioOutcome:
        adapter = self._adapter(context)
        config = _config("unknown-effect")
        engine, _binding = adapter.bind(config)
        effect = adapter.authorize_effect(
            engine,
            effect_type="conformance.external-write",
            payload={"record_id": "external-42"},
            idempotency_key="conformance-unknown-effect",
            authority="conformance-operator",
        )
        running = context.claim_external_effect_attempt(
            engine.snapshot.machine_id, effect.spec.effect_id
        )
        resumed = context.engine_class.resume(
            engine.snapshot.machine_id,
            context.store,
            recover_effects=True,
            load_history=True,
        )
        unknown = context.store.load_effect(
            resumed.snapshot.machine_id, effect.spec.effect_id
        )
        blocked = False
        try:
            resumed.execute_effect(
                effect.spec.effect_id,
                lambda _spec, _key: {"duplicate": True},
            )
        except EffectUnknownOutcome:
            blocked = True
        reconciled = resumed.reconcile_effect(
            effect.spec.effect_id,
            succeeded=True,
            result={"record_id": "external-42", "observed": "present"},
            evidence=["conformance:external-system-check"],
        )
        return AdapterScenarioOutcome(
            "unknown_effect",
            resumed.snapshot.machine_id,
            observations={
                "effect_id": effect.spec.effect_id,
                "attempt_entered_running": running.status == "RUNNING",
                "resume_marked_unknown": unknown.status == "UNKNOWN",
                "unsafe_retry_blocked": blocked,
                "explicit_reconciliation": reconciled.status == "SUCCEEDED"
                and bool(reconciled.evidence),
            },
            adapter_report=self._report(adapter, resumed),
        )

    def _restart(self, context: AdapterConformanceContext) -> AdapterScenarioOutcome:
        adapter = self._adapter(context)
        config = _config("restart")
        engine, _binding = adapter.bind(config)
        adapter.record_decision(
            engine,
            decision_id="D-policy",
            subject="policy",
            value="safe",
            pinned=True,
        )
        root = adapter.record_decision(
            engine,
            decision_id="D-root",
            subject="architecture",
            value="monolith",
        )
        bad = adapter.record_decision(
            engine,
            decision_id="D-bad",
            subject="schema",
            value="v2",
            kind="DERIVED",
            parent_ids=[root["decision_id"]],
        )
        learned = adapter.record_conflict(
            engine,
            statement="schema v2 conflicts with restart fixture",
            implicated_decision_ids=[bad["decision_id"]],
        )
        adapter.record_decision(
            engine,
            decision_id="D-temp",
            subject="search_strategy",
            value="fast",
        )
        recovery = adapter.recover(
            engine,
            LangGraphRecoveryAction.RESTART,
            reason="discard speculative assignment while retaining verified knowledge",
        )
        return AdapterScenarioOutcome(
            "restart",
            engine.snapshot.machine_id,
            observations={
                "pinned_decision_id": "D-policy",
                "speculative_decision_id": "D-temp",
                "constraint_id": learned["constraint_id"],
                "restart_recorded": recovery.action == "RESTART",
            },
            adapter_report=self._report(adapter, engine),
            evidence_ids=[learned["evidence_id"]],
        )

    def _replay(self, context: AdapterConformanceContext) -> AdapterScenarioOutcome:
        adapter = self._adapter(context)
        config = _config("replay")

        def step(state):
            return {"value": int(state.get("value", 0)) + 1}

        adapter.wrap_node("replay-step", step)({"value": 0}, config)
        engine, _binding = adapter.bind(config)
        history = engine.check_durable_history(persist=False)
        replay_hash = engine.replay().canonical_hash()
        persisted_hash = engine.snapshot.canonical_hash()
        return AdapterScenarioOutcome(
            "replay",
            engine.snapshot.machine_id,
            observations={
                "history_valid": history["valid"] is True,
                "replay_exact": replay_hash == persisted_hash,
                "event_count": len(engine.events),
            },
            adapter_report=self._report(adapter, engine),
        )

    def _fork(self, context: AdapterConformanceContext) -> AdapterScenarioOutcome:
        adapter = self._adapter(context)
        config = _config("fork")

        def step(state):
            return {"value": int(state.get("value", 0)) + 1}

        adapter.wrap_node("fork-step", step)({"value": 0}, config)
        engine, _binding = adapter.bind(config)
        source_sequence = engine.current_sequence()
        recovery = adapter.recover(
            engine,
            LangGraphRecoveryAction.FORK,
            reason="create a lineage-bearing conformance fork",
            at_sequence=source_sequence,
        )
        return AdapterScenarioOutcome(
            "fork",
            engine.snapshot.machine_id,
            observations={
                "source_sequence": source_sequence,
                "fork_machine_id": recovery.fork_machine_id,
            },
            adapter_report=self._report(adapter, engine),
        )

    def run_scenario(
        self,
        scenario_id: str,
        context: AdapterConformanceContext,
    ) -> AdapterScenarioOutcome:
        handlers = {
            "success": self._success,
            "contradiction": self._contradiction,
            "requirement_change": self._requirement_change,
            "lease_loss": self._lease_loss,
            "unknown_effect": self._unknown_effect,
            "restart": self._restart,
            "replay": self._replay,
            "fork": self._fork,
        }
        try:
            handler = handlers[scenario_id]
        except KeyError:
            raise ValueError(f"unknown conformance scenario: {scenario_id}") from None
        return handler(context)


__all__ = [
    "LANGGRAPH_CONFORMANCE_DRIVER_ID",
    "LANGGRAPH_CONFORMANCE_DRIVER_VERSION",
    "LangGraphConformanceDriver",
]
