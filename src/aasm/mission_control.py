from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .model import new_id, now


class MissionStatus:
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    ALL = {RUNNING, PAUSED}


class MissionControlAction:
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    ALL = {PAUSE, RESUME}


class MissionPauseMode:
    """QUIESCE blocks new claims; SUSPEND also releases active leases."""

    QUIESCE = "QUIESCE"
    SUSPEND = "SUSPEND"
    ALL = {QUIESCE, SUSPEND}


@dataclass
class MissionControlRecord:
    action: str
    actor: str
    reason: str
    mode: str = MissionPauseMode.QUIESCE
    ts: float = field(default_factory=now)
    metadata: dict[str, Any] = field(default_factory=dict)
    control_id: str = field(default_factory=lambda: new_id("mission-control"))

    def __post_init__(self):
        if self.action not in MissionControlAction.ALL:
            raise ValueError(f"invalid mission control action: {self.action}")
        if not str(self.actor).strip() or not str(self.reason).strip():
            raise ValueError("actor and reason are required")
        if self.mode not in MissionPauseMode.ALL:
            raise ValueError(f"invalid mission pause mode: {self.mode}")

    def to_dict(self):
        return asdict(self)


@dataclass
class ForkRequest:
    source_sequence: int
    actor: str
    reason: str
    target_machine_id: str = field(default_factory=lambda: new_id("machine"))
    request_id: str = field(default_factory=lambda: new_id("fork"))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.source_sequence = int(self.source_sequence)
        if self.source_sequence < 1:
            raise ValueError("source_sequence must be positive")
        if not str(self.actor).strip() or not str(self.reason).strip():
            raise ValueError("actor and reason are required")
        if not str(self.target_machine_id).strip():
            raise ValueError("target_machine_id is required")

    def to_dict(self):
        return asdict(self)
