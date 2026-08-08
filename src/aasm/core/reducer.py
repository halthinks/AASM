from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from ..model import Event, EventType, MachineSnapshot, ProblemSpec
from ..persistence.serde import problem_from_dict


def reduce_event(snapshot: MachineSnapshot | None, event: Event) -> MachineSnapshot:
    """Pure reducer from an event stream to authoritative machine state."""
    if snapshot is None:
        if event.event_type == EventType.MACHINE_CREATED.value:
            problem = problem_from_dict(event.data["problem"])
            snapshot = MachineSnapshot(
                machine_id=event.machine_id or event.data["machine_id"],
                version=0,
                state=event.to_state or event.data["state"],
                problem=problem,
            )
            definition = event.data.get("machine_definition")
            if definition:
                snapshot.metadata["machine_definition"] = {
                    "name": definition.get("name", "unnamed-machine"),
                    "schema_version": definition.get("schema_version", 1),
                    "terminal_states": list(definition.get("terminal_states", ["COMPLETE", "FAIL"])),
                }
            return snapshot
        if event.event_type == EventType.MACHINE_FORKED.value:
            from ..persistence.serde import snapshot_from_dict
            restored = snapshot_from_dict(event.data["snapshot"])
            restored.machine_id = event.machine_id or restored.machine_id
            return restored
        raise ValueError("First event must be machine_created or machine_forked")

    next_snapshot = deepcopy(snapshot)
    if event.event_type == EventType.TRANSITION_COMMITTED.value:
        if event.to_state is None:
            raise ValueError("transition_committed requires to_state")
        next_snapshot.state = event.to_state
        next_snapshot.version += 1
    elif event.event_type == EventType.SNAPSHOT_PATCHED.value:
        patch = event.data.get("patch", {})
        for key, value in patch.items():
            if key == "metadata":
                next_snapshot.metadata.update(value)
            elif hasattr(next_snapshot, key):
                setattr(next_snapshot, key, deepcopy(value))
            else:
                raise ValueError(f"Unknown snapshot field in patch: {key}")
        next_snapshot.version += 1
    elif event.event_type == EventType.CHECKPOINT_RESTORED.value:
        restored = event.data.get("snapshot")
        if restored is None:
            raise ValueError("checkpoint_restored requires snapshot")
        from ..persistence.serde import snapshot_from_dict
        next_snapshot = snapshot_from_dict(restored)
        next_snapshot.version = snapshot.version + 1
    elif event.event_type == EventType.PLAN_NODE_ADDED.value:
        node = deepcopy(event.data["node"])
        if any(x.get("node_id") == node.get("node_id") for x in next_snapshot.graph.get("nodes", [])):
            raise ValueError(f"Plan node already exists: {node.get('node_id')}")
        next_snapshot.graph.setdefault("nodes", []).append(node)
        next_snapshot.version += 1
    elif event.event_type == EventType.PLAN_EDGE_ADDED.value:
        edge = deepcopy(event.data["edge"])
        ids = {x.get("node_id") for x in next_snapshot.graph.get("nodes", [])}
        if edge.get("src") not in ids or edge.get("dst") not in ids:
            raise ValueError("Both plan edge endpoints must exist")
        next_snapshot.graph.setdefault("edges", []).append(edge)
        next_snapshot.version += 1
    elif event.event_type == EventType.PLAN_NODE_UPDATED.value:
        node_id = event.data["node_id"]
        patch = deepcopy(event.data.get("patch", {}))
        found = False
        for node in next_snapshot.graph.get("nodes", []):
            if node.get("node_id") == node_id:
                node.update(patch); found = True; break
        if not found:
            raise KeyError(node_id)
        next_snapshot.version += 1
    elif event.event_type == EventType.PLAN_NODE_PRUNED.value:
        node_id = event.data["node_id"]
        if node_id not in next_snapshot.pruned:
            next_snapshot.pruned.append(node_id)
        next_snapshot.frontier = [x for x in next_snapshot.frontier if x != node_id]
        for node in next_snapshot.graph.get("nodes", []):
            if node.get("node_id") == node_id:
                node["status"] = "pruned"
                break
        next_snapshot.version += 1
    elif event.event_type == EventType.MEMORY_PUT.value:
        next_snapshot.memory[event.data["key"]] = deepcopy(event.data["record"])
        next_snapshot.version += 1
    elif event.event_type == EventType.MEMORY_INVALIDATED.value:
        key = event.data["key"]
        if key not in next_snapshot.memory:
            raise KeyError(key)
        next_snapshot.memory[key].update(deepcopy(event.data["record"]))
        next_snapshot.version += 1
    elif event.event_type == EventType.EVIDENCE_ADDED.value:
        record = deepcopy(event.data["record"])
        evidence = next_snapshot.evidence
        evidence.setdefault("records", []).append(record)
        mapping = {"claim":"claims", "observation":"observations", "contradiction":"contradictions", "assumption":"assumptions"}
        bucket = mapping.get(record.get("kind"))
        if bucket:
            evidence.setdefault(bucket, []).append(record["evidence_id"])
        next_snapshot.version += 1
    elif event.event_type == EventType.EVIDENCE_INVALIDATED.value:
        evidence_id = event.data["evidence_id"]
        found = False
        for record in next_snapshot.evidence.get("records", []):
            if record.get("evidence_id") == evidence_id:
                record.update(deepcopy(event.data["record"])); found = True; break
        if not found:
            raise KeyError(evidence_id)
        next_snapshot.version += 1
    elif event.event_type == EventType.RESOURCE_REGISTERED.value:
        record = deepcopy(event.data["resource"])
        resources = next_snapshot.resources
        registry = resources.setdefault("registry", [])
        if any(x.get("resource_id") == record.get("resource_id") for x in registry):
            raise ValueError(f"Resource already exists: {record.get('resource_id')}")
        registry.append(record)
        next_snapshot.version += 1
    elif event.event_type == EventType.RESOURCE_UPDATED.value:
        resource_id = event.data["resource_id"]
        patch = deepcopy(event.data.get("patch", {}))
        found = False
        for record in next_snapshot.resources.setdefault("registry", []):
            if record.get("resource_id") == resource_id:
                record.update(patch); found = True; break
        if not found:
            raise KeyError(resource_id)
        next_snapshot.version += 1
    elif event.event_type == EventType.SCHEDULE_COMPUTED.value:
        resources = next_snapshot.resources
        resources["tasks"] = deepcopy(event.data.get("tasks", []))
        resources["assignments"] = deepcopy(event.data.get("assignments", []))
        resources["last_schedule"] = deepcopy(event.data.get("result", {}))
        next_snapshot.version += 1
    return next_snapshot


def replay_events(events: Iterable[Event]) -> MachineSnapshot:
    snapshot: MachineSnapshot | None = None
    seen = False
    for event in events:
        snapshot = reduce_event(snapshot, event)
        seen = True
    if not seen or snapshot is None:
        raise ValueError("Cannot replay an empty event stream")
    return snapshot
