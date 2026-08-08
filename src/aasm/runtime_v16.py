from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .checkpoint_triggers import CheckpointTriggerEngine, CheckpointTriggerPolicy
from .collaboration import CollaborationPolicy
from .fleet_control import FleetControlPolicy
from .resources import TaskDemand
from .runtime_v15 import AASMEngine as V15Engine
from .team_protocol import PlannerDecision, PlannerDirective, VerifierReport
from .workers import QuotaPolicy


FLEET_QUOTA_ID = "__aasm_fleet_admission__"


class AASMEngine(V15Engine):
    """v0.16 runtime: automatic checkpoint triggers and fleet admission control."""

    def checkpoint_trigger_policy(self):
        raw = self.snapshot.resources.get("checkpoint_trigger_policy")
        return CheckpointTriggerPolicy(**deepcopy(raw)) if raw else CheckpointTriggerPolicy()

    def configure_checkpoint_triggers(self, policy: CheckpointTriggerPolicy, *, reason="checkpoint trigger policy configured"):
        resources = deepcopy(self.snapshot.resources)
        resources["checkpoint_trigger_policy"] = asdict(policy)
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(resources["checkpoint_trigger_policy"])

    def checkpoint_trigger_history(self):
        return deepcopy(self.snapshot.resources.get("checkpoint_triggers", []) or [])

    def last_checkpoint_trigger(self):
        items = self.checkpoint_trigger_history()
        return items[-1] if items else None

    def _record_checkpoint_trigger(self, trigger, impact=None, *, reason="automatic checkpoint trigger recorded"):
        resources = deepcopy(self.snapshot.resources)
        raw = trigger.to_dict()
        raw["impact_id"] = None if impact is None else impact.get("impact_id")
        resources.setdefault("checkpoint_triggers", []).append(raw)
        resources["last_checkpoint_trigger"] = raw
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(raw)

    def submit_verifier_report(self, report: VerifierReport, *, reason: str = "Verifier report recorded"):
        verified = super().submit_verifier_report(report, reason=reason)
        policy = self.checkpoint_trigger_policy()
        trigger = CheckpointTriggerEngine().evaluate(verified, policy)
        impact = None
        if trigger.triggered:
            # A task may be a valid PBV work item without being a plan-graph node.
            # In that case require Planner attention without fabricating a graph anchor.
            if trigger.signal and trigger.signal.seed_nodes:
                known = {x.get("node_id") for x in self.snapshot.graph.get("nodes", [])}
                trigger.signal.seed_nodes = [x for x in trigger.signal.seed_nodes if x in known]
            impact = self.analyze_change(trigger.signal, pause_affected=policy.pause_affected, reason="Verifier checkpoint trigger impact analyzed")
        self._record_checkpoint_trigger(trigger, impact)
        if impact is not None and self.fleet_control_policy().enabled:
            self.refresh_fleet_control(reason="fleet control refreshed after automatic checkpoint")
        return verified

    def fleet_control_policy(self):
        raw = self.snapshot.resources.get("fleet_control", {}).get("policy")
        return FleetControlPolicy(**deepcopy(raw)) if raw else FleetControlPolicy()

    def fleet_control_report(self):
        raw = deepcopy(self.snapshot.resources.get("fleet_control", {}) or {})
        raw.setdefault("policy", asdict(self.fleet_control_policy()))
        raw.setdefault("admission_limit", None)
        raw.setdefault("last_refresh", None)
        return raw

    def configure_fleet_control(self, policy: FleetControlPolicy, *, refresh=True, reason="fleet control configured"):
        resources = deepcopy(self.snapshot.resources)
        control = resources.setdefault("fleet_control", {})
        control["policy"] = asdict(policy)
        control.setdefault("admission_limit", None)
        control.setdefault("last_refresh", None)
        self.patch_snapshot({"resources": resources}, reason)
        if refresh:
            return self.refresh_fleet_control(reason="fleet control refreshed after configuration")
        return self.fleet_control_report()

    def _runnable_scheduled_tasks(self):
        paused = set(self.paused_tasks())
        completed = {x.get("task_id") for x in self.snapshot.resources.get("leases", []) if x.get("status") == "COMPLETED"}
        node_status = {x.get("node_id"): x.get("status") for x in self.snapshot.graph.get("nodes", [])}
        rows = []
        for raw in self.snapshot.resources.get("tasks", []) or []:
            task_id = raw.get("task_id")
            if task_id in paused or task_id in completed:
                continue
            if node_status.get(task_id) in {"complete", "pruned"}:
                continue
            rows.append(TaskDemand(**deepcopy(raw)))
        return rows

    def refresh_fleet_control(self, *, collaboration_policy: CollaborationPolicy | None = None, reason="fleet admission control refreshed"):
        policy = self.fleet_control_policy()
        tasks = self._runnable_scheduled_tasks()
        analysis = None
        recommended = None
        if tasks:
            analysis = self.analyze_collaboration(tasks, collaboration_policy or CollaborationPolicy(), reason="fleet-control collaboration analysis")
            recommended = analysis.get("recommended_workers")
        admission_limit = policy.apply(recommended)
        enforce = bool(policy.enabled and policy.enforce_admission_limit and admission_limit is not None)

        # Reuse the existing machine-quota path so SQLite/PostgreSQL enforce the
        # admission limit atomically with all other claim limits.
        self.set_quota(
            QuotaPolicy(
                quota_id=FLEET_QUOTA_ID,
                scope="machine",
                max_active_leases=admission_limit if enforce else None,
                enabled=enforce,
                metadata={"source": "fleet_control", "recommended_workers": recommended},
            ),
            reason=reason,
        )
        resources = deepcopy(self.snapshot.resources)
        control = resources.setdefault("fleet_control", {})
        control["policy"] = asdict(policy)
        control["admission_limit"] = admission_limit
        control["last_refresh"] = {
            "recommended_workers": recommended,
            "admission_limit": admission_limit,
            "enforced": enforce,
            "task_ids": [x.task_id for x in tasks],
            "analysis": deepcopy(analysis),
        }
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(control)

    def planner_decide(self, decision: PlannerDecision, *, reason: str = "Planner directive committed"):
        raw = super().planner_decide(decision, reason=reason)
        resolution = (decision.metadata or {}).get("resolve_impact")
        if resolution:
            self.resolve_change_impact(
                decision.planner_id,
                resolution["impact_id"],
                resume_nodes=list(resolution.get("resume_nodes", []) or []),
                retire_nodes=list(resolution.get("retire_nodes", []) or []),
                plan_decision_id=raw.get("planner_decision_id"),
                reason="Planner decision resolved information-change checkpoint",
            )
        policy = self.fleet_control_policy()
        if decision.directive == PlannerDirective.PLAN_INTERRUPT.value and policy.enabled and policy.auto_refresh_on_plan_interrupt:
            self.refresh_fleet_control(reason="fleet control refreshed after PLAN_INTERRUPT")
        return raw

    def resolve_change_impact(self, planner_id: str, impact_id: str, **kwargs):
        out = super().resolve_change_impact(planner_id, impact_id, **kwargs)
        policy = self.fleet_control_policy()
        if policy.enabled and policy.auto_refresh_on_change_resolution:
            self.refresh_fleet_control(reason="fleet control refreshed after change resolution")
        return out

    def dashboard(self):
        out = super().dashboard()
        out["checkpoint_triggers"] = {
            "policy": asdict(self.checkpoint_trigger_policy()),
            "count": len(self.checkpoint_trigger_history()),
            "last": self.last_checkpoint_trigger(),
        }
        out["fleet_control"] = self.fleet_control_report()
        return out
