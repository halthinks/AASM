from __future__ import annotations

from copy import deepcopy

from ..checkpoint import Checkpoint
from ..model import Event, MachineSnapshot, MachineState
from ..effects import EffectRecord


class MemoryStore:
    """In-memory Store implementation used by default and in tests."""

    def __init__(self):
        self._snapshots: dict[str, MachineSnapshot] = {}
        self._events: dict[str, list[Event]] = {}
        self._checkpoints: dict[tuple[str, str], Checkpoint] = {}
        self._effects: dict[tuple[str, str], EffectRecord] = {}

    def initialize_run(self, snapshot: MachineSnapshot) -> None:
        self._snapshots[snapshot.machine_id] = deepcopy(snapshot)
        self._events.setdefault(snapshot.machine_id, [])

    def append(self, machine_id: str, event: Event, snapshot: MachineSnapshot) -> Event:
        events = self._events.setdefault(machine_id, [])
        event = deepcopy(event)
        event.machine_id = machine_id
        event.sequence = len(events) + 1
        events.append(event)
        self._snapshots[machine_id] = deepcopy(snapshot)
        return deepcopy(event)

    def load_snapshot(self, machine_id: str) -> MachineSnapshot:
        if machine_id not in self._snapshots:
            raise KeyError(machine_id)
        return deepcopy(self._snapshots[machine_id])

    def load_events(self, machine_id: str, after_sequence: int = 0) -> list[Event]:
        return [deepcopy(e) for e in self._events.get(machine_id, []) if e.sequence > after_sequence]

    def list_unfinished(self) -> list[str]:
        result=[]
        for mid, snap in self._snapshots.items():
            definition=snap.metadata.get("machine_definition", {})
            terminal=set(definition.get("terminal_states", [MachineState.COMPLETE.value, MachineState.FAIL.value]))
            if snap.state not in terminal:
                result.append(mid)
        return sorted(result)

    def save_checkpoint(self, machine_id: str, checkpoint: Checkpoint) -> None:
        self._checkpoints[(machine_id, checkpoint.checkpoint_id)] = deepcopy(checkpoint)

    def load_checkpoint(self, machine_id: str, checkpoint_id: str) -> Checkpoint:
        try:
            return deepcopy(self._checkpoints[(machine_id, checkpoint_id)])
        except KeyError:
            raise KeyError(checkpoint_id) from None

    def save_effect(self, record: EffectRecord) -> None:
        self._effects[(record.machine_id, record.spec.effect_id)] = deepcopy(record)

    def load_effect(self, machine_id: str, effect_id: str) -> EffectRecord:
        try:
            return deepcopy(self._effects[(machine_id, effect_id)])
        except KeyError:
            raise KeyError(effect_id) from None

    def find_effect_by_idempotency(self, machine_id: str, idempotency_key: str) -> EffectRecord | None:
        for (mid, _), record in self._effects.items():
            if mid == machine_id and record.spec.idempotency_key == idempotency_key:
                return deepcopy(record)
        return None

    def list_effects(self, machine_id: str) -> list[EffectRecord]:
        return [deepcopy(r) for (mid, _), r in self._effects.items() if mid == machine_id]

    def close(self) -> None:
        return None
