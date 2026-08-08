from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .engine import AASMEngine as CoreAASMEngine
from .model import Event, EventType, new_id, now
from .resources import ResourceRecord, TaskDemand
from .scheduler import CapabilityScheduler


class AASMEngine(CoreAASMEngine):
    """Public AASM runtime with durable capability/resource scheduling.

    v0.6 layers capability scheduling over the stable core engine so the public
    package can evolve without duplicating the event-sourced state machine.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduler = CapabilityScheduler(self.flow)

    @classmethod
    def _hydrate(cls, snapshot, events, store, authority=None, definition=None):
        self = super()._hydrate(snapshot, events, store, authority=authority, definition=definition)
        self.scheduler = CapabilityScheduler(self.flow)
        return self

    def register_resource(self, record: ResourceRecord, *, reason: str = "resource registered"):
        event = Event(
            new_id("evt"), now(), EventType.RESOURCE_REGISTERED.value,
            self.state_value, self.state_value, reason,
            data={"resource": asdict(record)}, machine_id=self.snapshot.machine_id,
        )
        self._commit(event)
        return deepcopy(next(x for x in self.snapshot.resources.get("registry", []) if x["resource_id"] == record.resource_id))

    def update_resource(self, resource_id: str, patch: dict, *, reason: str = "resource updated"):
        allowed = {"kind", "capabilities", "capacity", "cost_per_unit", "reliability", "enabled", "metadata"}
        unknown = set(patch) - allowed
        if unknown:
            raise ValueError(f"Unknown resource fields: {sorted(unknown)}")
        current = next((x for x in self.snapshot.resources.get("registry", []) if x["resource_id"] == resource_id), None)
        if current is None:
            raise KeyError(resource_id)
        candidate = deepcopy(current)
        candidate.update(deepcopy(patch))
        ResourceRecord(**candidate)
        event = Event(
            new_id("evt"), now(), EventType.RESOURCE_UPDATED.value,
            self.state_value, self.state_value, reason,
            data={"resource_id": resource_id, "patch": deepcopy(patch)}, machine_id=self.snapshot.machine_id,
        )
        self._commit(event)
        return deepcopy(next(x for x in self.snapshot.resources.get("registry", []) if x["resource_id"] == resource_id))

    def list_resources(self):
        return deepcopy(self.snapshot.resources.get("registry", []))

    def schedule(self, tasks: list[TaskDemand], *, reason: str = "resource schedule computed"):
        resources = [ResourceRecord(**deepcopy(raw)) for raw in self.snapshot.resources.get("registry", [])]
        result = self.scheduler.schedule(resources, tasks)
        event = Event(
            new_id("evt"), now(), EventType.SCHEDULE_COMPUTED.value,
            self.state_value, self.state_value, reason,
            data={
                "tasks": [asdict(x) for x in tasks],
                "assignments": [asdict(x) for x in result.assignments],
                "result": result.to_dict(),
            },
            machine_id=self.snapshot.machine_id,
        )
        self._commit(event)
        by_task: dict[str, list[str]] = {}
        for assignment in result.assignments:
            by_task.setdefault(assignment.task_id, []).append(assignment.resource_id)
        for task_id, owners in by_task.items():
            if task_id in self.graph.nodes:
                owner = owners[0] if len(owners) == 1 else ",".join(sorted(owners))
                self.plan_update_node(task_id, {"owner": owner}, reason="scheduler assigned plan node")
        return result

    def last_schedule(self):
        return deepcopy(self.snapshot.resources.get("last_schedule"))
