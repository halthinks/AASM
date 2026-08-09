from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from .model import now


class WorkerControlAction:
    DRAIN = "DRAIN"
    RESUME = "RESUME"
    OFFLINE = "OFFLINE"
    ALL = {DRAIN, RESUME, OFFLINE}


@dataclass
class WorkerControlRecord:
    worker_id: str
    action: str
    actor: str
    reason: str
    ts: float = field(default_factory=now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.worker_id or not self.actor or not self.reason:
            raise ValueError("worker_id, actor, and reason are required")
        if self.action not in WorkerControlAction.ALL:
            raise ValueError(f"invalid worker control action: {self.action}")

    def to_dict(self):
        return asdict(self)
