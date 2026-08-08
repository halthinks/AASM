from __future__ import annotations

from collections import defaultdict
from .flow import ResourceFlowAllocator
from .resources import Assignment, ResourceRecord, ScheduleResult, TaskDemand


class CapabilityScheduler:
    """Deterministic capability-aware scheduler backed by max-flow/min-cut."""

    def __init__(self, allocator: ResourceFlowAllocator | None = None):
        self.allocator = allocator or ResourceFlowAllocator()

    @staticmethod
    def _eligible(task: TaskDemand, resource: ResourceRecord) -> bool:
        if not resource.enabled:
            return False
        if task.allowed_kinds and resource.kind not in task.allowed_kinds:
            return False
        if resource.reliability < task.min_reliability:
            return False
        if task.max_cost_per_unit is not None and resource.cost_per_unit > task.max_cost_per_unit:
            return False
        return resource.supports(task.required_capabilities)

    def schedule(self, resources: list[ResourceRecord], tasks: list[TaskDemand]) -> ScheduleResult:
        resources = sorted(resources, key=lambda r: r.resource_id)
        tasks = sorted(tasks, key=lambda t: (-t.priority, t.task_id))
        source, sink = "__source__", "__sink__"
        capacities: dict[str, dict[str, float]] = {source: {}}
        total_demand = 0.0

        # Insertion order is intentional: higher-priority tasks are traversed first
        # by Edmonds-Karp when capacity is insufficient.
        for task in tasks:
            tnode = f"task:{task.task_id}"
            capacities[source][tnode] = float(task.demand)
            capacities.setdefault(tnode, {})
            total_demand += float(task.demand)
            for resource in resources:
                if self._eligible(task, resource):
                    rnode = f"resource:{resource.resource_id}"
                    capacities[tnode][rnode] = float(task.demand)

        for resource in resources:
            rnode = f"resource:{resource.resource_id}"
            capacities.setdefault(rnode, {})[sink] = float(resource.capacity if resource.enabled else 0.0)

        solved = self.allocator.solve(capacities, source, sink)
        assignments: list[Assignment] = []
        delivered = defaultdict(float)
        resource_used = defaultdict(float)
        for edge, amount in solved.get("flows", {}).items():
            u, v = edge.split("->", 1)
            if u.startswith("task:") and v.startswith("resource:") and amount > 1e-12:
                task_id = u.split(":", 1)[1]
                resource_id = v.split(":", 1)[1]
                assignments.append(Assignment(task_id, resource_id, amount))
                delivered[task_id] += amount
                resource_used[resource_id] += amount

        assignments.sort(key=lambda x: (x.task_id, x.resource_id))
        unmet = {task.task_id: max(0.0, float(task.demand) - delivered[task.task_id]) for task in tasks}
        utilization = {}
        for r in resources:
            utilization[r.resource_id] = 0.0 if r.capacity <= 0 else resource_used[r.resource_id] / r.capacity

        bottlenecks = set()
        for u, v, _ in solved["min_cut_edges"]:
            for node in (u, v):
                if node.startswith("resource:"):
                    bottlenecks.add(node.split(":", 1)[1])
        if not bottlenecks and any(v > 1e-12 for v in unmet.values()):
            # When task->resource eligibility itself is the cut, identify tasks as
            # capability bottlenecks rather than inventing a resource.
            for task_id, amount in unmet.items():
                if amount > 1e-12:
                    bottlenecks.add(f"capability:{task_id}")

        return ScheduleResult(
            assignments=assignments,
            unmet=unmet,
            max_flow=float(solved["max_flow"]),
            total_demand=total_demand,
            min_cut_edges=list(solved["min_cut_edges"]),
            bottlenecks=sorted(bottlenecks),
            resource_utilization=utilization,
        )
