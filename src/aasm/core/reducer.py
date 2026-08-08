from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from ..model import Event, EventType, MachineSnapshot, ProblemSpec
from ..persistence.serde import problem_from_dict


def reduce_event(snapshot: MachineSnapshot | None, event: Event) -> MachineSnapshot:
    """Pure reducer from an event stream to authoritative machine state."""
    if snapshot is None:
        if event.event_type != EventType.MACHINE_CREATED.value:
            raise ValueError("First event must be machine_created")
        problem = problem_from_dict(event.data["problem"])
        return MachineSnapshot(
            machine_id=event.machine_id or event.data["machine_id"],
            version=0,
            state=event.to_state or event.data["state"],
            problem=problem,
        )

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
