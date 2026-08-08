from __future__ import annotations

from copy import deepcopy

from ..checkpoint import Checkpoint
from ..model import Event, MachineSnapshot, MachineState


class MemoryStore:
    """In-memory Store implementation used by default and in tests."""

    def __init__(self):
        self._snapshots: dict[str, MachineSnapshot] = {}
        self._events: dict[str, list[Event]] = {}
        self._checkpoints: dict[tuple[str, str], Checkpoint] = {}

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
        terminal = {MachineState.COMPLETE.value, MachineState.FAIL.value}
        return sorted(mid for mid, snap in self._snapshots.items() if snap.state not in terminal)

    def save_checkpoint(self, machine_id: str, checkpoint: Checkpoint) -> None:
        self._checkpoints[(machine_id, checkpoint.checkpoint_id)] = deepcopy(checkpoint)

    def load_checkpoint(self, machine_id: str, checkpoint_id: str) -> Checkpoint:
        try:
            return deepcopy(self._checkpoints[(machine_id, checkpoint_id)])
        except KeyError:
            raise KeyError(checkpoint_id) from None

    def close(self) -> None:
        return None
