from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .collaboration import CollaborationPlanner, CollaborationPolicy
from .graph import PlanGraph
from .resources import ResourceRecord, TaskDemand
from .runtime_v13 import AASMEngine as V13Engine


class AASMEngine(V13Engine):
    """v0.14 runtime: evidence-based massive collaboration planning."""

    def analyze_collaboration(self, tasks: list[TaskDemand] | None = None, policy: CollaborationPolicy | None = None, *, reason: str = "collaboration parallelism analyzed"):
        if tasks is None:
            tasks=[TaskDemand(**deepcopy(x)) for x in self.snapshot.resources.get("tasks",[]) or []]
        resources=[ResourceRecord(**deepcopy(x)) for x in self.list_resources()]
        graph=PlanGraph.from_dict(self.snapshot.graph)
        analysis=CollaborationPlanner().analyze(graph,resources,tasks,policy)
        raw=analysis.to_dict()
        raw["policy"]=asdict(policy or CollaborationPolicy())
        raw["task_ids"]=[t.task_id for t in tasks]
        store=deepcopy(self.snapshot.resources)
        store["last_collaboration_analysis"]=raw
        store.setdefault("collaboration_history",[]).append(raw)
        self.patch_snapshot({"resources":store},reason)
        return deepcopy(raw)

    def last_collaboration_analysis(self):
        return deepcopy(self.snapshot.resources.get("last_collaboration_analysis"))

    def collaboration_history(self):
        return deepcopy(self.snapshot.resources.get("collaboration_history",[]))

    def dashboard(self):
        out=super().dashboard()
        out["collaboration"]=self.last_collaboration_analysis()
        return out
