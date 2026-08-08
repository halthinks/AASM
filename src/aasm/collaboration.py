from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import ceil, floor
from typing import Any

from .graph import PlanGraph
from .resources import ResourceRecord, TaskDemand
from .scheduler import CapabilityScheduler


@dataclass
class CollaborationPolicy:
    max_workers: int = 256
    coordination_overhead_per_extra_worker: float = 0.05
    min_relative_improvement: float = 0.02
    near_optimal_tolerance: float = 0.02
    default_task_duration: float = 1.0

    def __post_init__(self):
        if self.max_workers < 1:
            raise ValueError("max_workers must be positive")
        if self.coordination_overhead_per_extra_worker < 0:
            raise ValueError("coordination_overhead_per_extra_worker must be non-negative")
        if not 0 <= self.min_relative_improvement <= 1:
            raise ValueError("min_relative_improvement must be between 0 and 1")
        if not 0 <= self.near_optimal_tolerance <= 1:
            raise ValueError("near_optimal_tolerance must be between 0 and 1")
        if self.default_task_duration <= 0:
            raise ValueError("default_task_duration must be positive")


@dataclass
class CollaborationCandidate:
    workers: int
    projected_makespan: float
    ideal_work_bound: float
    coordination_overhead: float
    relative_improvement_vs_previous: float | None

    def to_dict(self):
        return asdict(self)


@dataclass
class CollaborationAnalysis:
    recommended_workers: int
    useful_worker_ceiling: int
    critical_path: float
    total_work: float
    max_parallel_width: int
    waves: list[list[str]]
    candidates: list[CollaborationCandidate]
    bottlenecks: list[str]
    min_cut_edges: list[list[Any]]
    schedulable_fraction: float
    resource_capacity: float
    resource_cost_proxy: float
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        raw=asdict(self)
        raw["candidates"]=[x.to_dict() for x in self.candidates]
        return raw


class CollaborationPlanner:
    """Decide how much parallelism is useful before spawning more workers.

    The planner combines DAG critical-path/width limits with capability-aware
    max-flow capacity. It deliberately recommends the smallest worker count
    within the near-optimal makespan band instead of maximizing concurrency.
    """

    def __init__(self, scheduler: CapabilityScheduler | None = None):
        self.scheduler=scheduler or CapabilityScheduler()

    @staticmethod
    def _task_duration(task: TaskDemand, graph: PlanGraph, default: float) -> float:
        value=(task.metadata or {}).get("estimated_duration")
        if value is not None:
            value=float(value)
            if value <= 0: raise ValueError(f"task {task.task_id} estimated_duration must be positive")
            return value
        node=graph.nodes.get(task.task_id)
        if node is not None and float(node.estimated_cost) > 0:
            return float(node.estimated_cost)
        return float(default)

    @staticmethod
    def _waves(graph: PlanGraph, task_ids: set[str]) -> list[list[str]]:
        if not task_ids:
            return []
        preds={tid:set() for tid in task_ids}
        for edge in graph.edges:
            if edge.src in task_ids and edge.dst in task_ids:
                preds[edge.dst].add(edge.src)
        remaining=set(task_ids); done=set(); waves=[]
        while remaining:
            wave=sorted(t for t in remaining if preds[t].issubset(done))
            if not wave:
                raise ValueError("task dependency graph contains a cycle")
            waves.append(wave); done.update(wave); remaining.difference_update(wave)
        return waves

    @staticmethod
    def _critical_path(graph: PlanGraph, task_ids: set[str], durations: dict[str,float]) -> float:
        if not task_ids: return 0.0
        order=[x for x in graph.topological_order() if x in task_ids]
        pred={tid:[] for tid in task_ids}
        for edge in graph.edges:
            if edge.src in task_ids and edge.dst in task_ids:
                pred[edge.dst].append(edge.src)
        finish={}
        for tid in order:
            finish[tid]=durations[tid]+max((finish[p] for p in pred[tid]),default=0.0)
        # Tasks absent from the graph are independent roots.
        for tid in sorted(task_ids-set(order)):
            finish[tid]=durations[tid]
        return max(finish.values(),default=0.0)

    def analyze(self, graph: PlanGraph, resources: list[ResourceRecord], tasks: list[TaskDemand], policy: CollaborationPolicy | None = None) -> CollaborationAnalysis:
        policy=policy or CollaborationPolicy()
        tasks=sorted(tasks,key=lambda t:t.task_id)
        task_ids={t.task_id for t in tasks}
        if not tasks:
            return CollaborationAnalysis(0,0,0.0,0.0,0,[],[],[],[],1.0,0.0,0.0,"no runnable tasks")
        # Validate the plan before estimating concurrency.
        if graph.nodes:
            graph.topological_order()
        durations={t.task_id:self._task_duration(t,graph,policy.default_task_duration) for t in tasks}
        total_work=sum(durations.values())
        critical_path=self._critical_path(graph,task_ids,durations)
        waves=self._waves(graph,task_ids)
        max_width=max((len(w) for w in waves),default=len(tasks))

        schedule=self.scheduler.schedule(resources,tasks)
        total_demand=sum(float(t.demand) for t in tasks)
        schedulable_fraction=1.0 if total_demand<=1e-12 else min(1.0,float(schedule.max_flow)/total_demand)
        enabled_capacity=sum(float(r.capacity) for r in resources if r.enabled)
        capacity_slots=max(1,int(floor(enabled_capacity+1e-12))) if enabled_capacity>0 else 0
        useful_ceiling=min(policy.max_workers,len(tasks),max_width,capacity_slots) if capacity_slots else 0

        resource_by_id={r.resource_id:r for r in resources}
        resource_cost_proxy=sum(float(a.amount)*float(resource_by_id[a.resource_id].cost_per_unit) for a in schedule.assignments if a.resource_id in resource_by_id)
        candidates=[]
        previous=None
        for workers in range(1,useful_ceiling+1):
            ideal=max(critical_path,total_work/workers)
            overhead=policy.coordination_overhead_per_extra_worker*max(0,workers-1)
            projected=ideal+overhead
            improvement=None if previous is None or previous<=0 else max(0.0,(previous-projected)/previous)
            candidates.append(CollaborationCandidate(workers,projected,ideal,overhead,improvement))
            previous=projected

        if not candidates:
            reason="no eligible worker capacity can satisfy the current task set"
            recommended=0
        else:
            best=min(c.projected_makespan for c in candidates)
            near=best*(1.0+policy.near_optimal_tolerance)
            recommended=next(c.workers for c in candidates if c.projected_makespan<=near)
            # Avoid adding workers whose marginal benefit is below policy even if
            # they are still fractionally inside the mathematical optimum.
            for c in candidates[1:]:
                if c.workers>recommended: break
                if c.relative_improvement_vs_previous is not None and c.relative_improvement_vs_previous < policy.min_relative_improvement:
                    recommended=max(1,c.workers-1); break
            if recommended>=useful_ceiling:
                reason="parallelism is capped by plan width and/or eligible resource capacity"
            elif recommended==1:
                reason="critical path or coordination overhead makes additional workers non-beneficial"
            else:
                reason="smallest worker count within the near-optimal projected makespan band"

        return CollaborationAnalysis(
            recommended_workers=recommended,
            useful_worker_ceiling=useful_ceiling,
            critical_path=critical_path,
            total_work=total_work,
            max_parallel_width=max_width,
            waves=waves,
            candidates=candidates,
            bottlenecks=list(schedule.bottlenecks),
            min_cut_edges=[list(x) for x in schedule.min_cut_edges],
            schedulable_fraction=schedulable_fraction,
            resource_capacity=enabled_capacity,
            resource_cost_proxy=resource_cost_proxy,
            reason=reason,
            metadata={"fully_schedulable":schedule.fully_scheduled,"unmet":dict(schedule.unmet)},
        )
