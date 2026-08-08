from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .graph import PlanEdge, PlanGraph, PlanNode
from .model import new_id
from .runtime_v12 import AASMEngine as V12Engine
from .team_protocol import (
    BuilderOutput,
    PlannerBuilderVerifierPolicy,
    PlannerDecision,
    PlannerDirective,
    TeamMember,
    TeamRole,
    VerifierReport,
)


class AASMEngine(V12Engine):
    """v0.13 runtime: executable Planner / Builder / Verifier protocol."""

    def _team_state(self):
        return deepcopy(self.snapshot.resources.get("team_protocol", {}))

    def initialize_team(self, members: list[TeamMember], *, reason: str = "Planner Builder Verifier team initialized"):
        if self.snapshot.resources.get("team_protocol"):
            raise ValueError("PBV team is already initialized")
        raw = [asdict(member) for member in members]
        ids = [x["member_id"] for x in raw]
        if len(ids) != len(set(ids)):
            raise ValueError("team member IDs must be unique")
        planners = [x for x in raw if x["role"] == TeamRole.PLANNER.value and x.get("enabled", True)]
        if len(planners) != 1:
            raise ValueError("executable PBV profile requires exactly one enabled Planner")
        team = {
            "planner_id": planners[0]["member_id"],
            "members": raw,
            "plan_revision": 1,
            "builder_outputs": [],
            "verifier_reports": [],
            "planner_decisions": [],
            "task_directives": {},
            "paused": False,
        }
        resources = deepcopy(self.snapshot.resources)
        resources["team_protocol"] = team
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(team)

    def team_report(self):
        team = self._team_state()
        if not team:
            return {"configured": False}
        return {
            "configured": True,
            "planner_id": team.get("planner_id"),
            "members": deepcopy(team.get("members", [])),
            "plan_revision": int(team.get("plan_revision", 0) or 0),
            "paused": bool(team.get("paused", False)),
            "task_directives": deepcopy(team.get("task_directives", {})),
            "builder_outputs": len(team.get("builder_outputs", [])),
            "verifier_reports": len(team.get("verifier_reports", [])),
            "planner_decisions": len(team.get("planner_decisions", [])),
            "latest_decision": deepcopy(team.get("planner_decisions", [])[-1]) if team.get("planner_decisions") else None,
        }

    def submit_builder_output(self, output: BuilderOutput, *, reason: str = "Builder output recorded"):
        resources = deepcopy(self.snapshot.resources)
        team = resources.get("team_protocol")
        if not team:
            raise RuntimeError("PBV team is not initialized")
        PlannerBuilderVerifierPolicy.require_role(team["members"], output.builder_id, TeamRole.BUILDER.value)
        raw = asdict(output)
        raw["builder_output_id"] = new_id("build")
        raw["plan_revision"] = int(team.get("plan_revision", 0) or 0)
        team.setdefault("builder_outputs", []).append(raw)
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(raw)

    def submit_verifier_report(self, report: VerifierReport, *, reason: str = "Verifier report recorded"):
        resources = deepcopy(self.snapshot.resources)
        team = resources.get("team_protocol")
        if not team:
            raise RuntimeError("PBV team is not initialized")
        PlannerBuilderVerifierPolicy.require_role(team["members"], report.verifier_id, TeamRole.VERIFIER.value)
        source = next((x for x in team.get("builder_outputs", []) if x.get("builder_output_id") == report.builder_output_id), None)
        if source is None:
            raise KeyError(report.builder_output_id)
        if source.get("task_id") != report.task_id:
            raise ValueError("verifier report task_id does not match Builder output")
        raw = asdict(report)
        raw["verifier_report_id"] = new_id("verify")
        raw["plan_revision"] = int(team.get("plan_revision", 0) or 0)
        raw["policy_recommendation"] = PlannerBuilderVerifierPolicy.recommended_directive(report)
        team.setdefault("verifier_reports", []).append(raw)
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(raw)

    @staticmethod
    def _apply_plan_patch(graph_dict: dict, patch: dict):
        graph = PlanGraph.from_dict(deepcopy(graph_dict))
        for raw in patch.get("add_nodes", []) or []:
            graph.add_node(PlanNode(**deepcopy(raw)))
        for raw in patch.get("add_edges", []) or []:
            graph.add_edge(PlanEdge(**deepcopy(raw)))
        for item in patch.get("update_nodes", []) or []:
            item = deepcopy(item)
            node_id = item.pop("node_id")
            graph.update_node(node_id, **item)
        pruned = []
        for node_id in patch.get("prune_nodes", []) or []:
            graph.update_node(node_id, status="pruned", owner=None)
            pruned.append(node_id)
        if graph.nodes:
            graph.topological_order()
        return graph.to_dict(), pruned

    def planner_decide(
        self,
        decision: PlannerDecision,
        *,
        reason: str = "Planner directive committed",
    ):
        resources = deepcopy(self.snapshot.resources)
        team = resources.get("team_protocol")
        if not team:
            raise RuntimeError("PBV team is not initialized")
        PlannerBuilderVerifierPolicy.require_role(team["members"], decision.planner_id, TeamRole.PLANNER.value)
        if decision.planner_id != team.get("planner_id"):
            raise PermissionError("only the registered authoritative Planner may issue directives")
        PlannerBuilderVerifierPolicy.validate_plan_change(decision.directive, decision.plan_patch)
        if decision.verifier_report_id:
            report = next((x for x in team.get("verifier_reports", []) if x.get("verifier_report_id") == decision.verifier_report_id), None)
            if report is None:
                raise KeyError(decision.verifier_report_id)
            if report.get("task_id") != decision.task_id:
                raise ValueError("Planner decision task_id does not match Verifier report")

        before = int(team.get("plan_revision", 0) or 0)
        new_graph = deepcopy(self.snapshot.graph)
        new_pruned = deepcopy(self.snapshot.pruned)
        new_frontier = deepcopy(self.snapshot.frontier)
        after = before
        if decision.directive == PlannerDirective.PLAN_INTERRUPT.value:
            new_graph, pruned_now = self._apply_plan_patch(self.snapshot.graph, decision.plan_patch or {})
            for node_id in pruned_now:
                if node_id not in new_pruned:
                    new_pruned.append(node_id)
                new_frontier = [x for x in new_frontier if x != node_id]
            after = before + 1

        raw = asdict(decision)
        raw["planner_decision_id"] = new_id("decision")
        raw["plan_revision_before"] = before
        raw["plan_revision_after"] = after
        team["plan_revision"] = after
        team.setdefault("planner_decisions", []).append(raw)
        team.setdefault("task_directives", {})[decision.task_id] = decision.directive
        team["paused"] = decision.directive in {PlannerDirective.PAUSE.value, PlannerDirective.PLAN_INTERRUPT.value}

        patch = {"resources": resources}
        if new_graph != self.snapshot.graph:
            patch["graph"] = new_graph
        if new_pruned != self.snapshot.pruned:
            patch["pruned"] = new_pruned
        if new_frontier != self.snapshot.frontier:
            patch["frontier"] = new_frontier
        self.patch_snapshot(patch, reason)
        return deepcopy(raw)

    def planner_resume(self, planner_id: str, task_id: str, *, reason: str = "Planner resumed work"):
        return self.planner_decide(
            PlannerDecision(planner_id, task_id, PlannerDirective.CONTINUE.value, reason),
            reason=reason,
        )

    def team_task_directive(self, task_id: str):
        return self._team_state().get("task_directives", {}).get(task_id)

    def dashboard(self):
        out = super().dashboard()
        out["team_protocol"] = self.team_report()
        return out
