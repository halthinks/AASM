from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .model import new_id, now
from .resources import TaskDemand


class WorkerStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    OFFLINE = "OFFLINE"
    STALE = "STALE"


class LeaseStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


@dataclass
class WorkerRecord:
    worker_id: str
    resource_id: str
    status: str = WorkerStatus.ACTIVE.value
    heartbeat_timeout: float = 60.0
    last_heartbeat: float = field(default_factory=now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.heartbeat_timeout <= 0:
            raise ValueError("heartbeat_timeout must be positive")
        if self.status not in {x.value for x in WorkerStatus}:
            raise ValueError(f"invalid worker status: {self.status}")


@dataclass
class QuotaPolicy:
    quota_id: str
    scope: str = "machine"  # machine | worker | resource
    target_id: str | None = None
    max_active_leases: int | None = None
    max_capacity_units: float | None = None
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.scope not in {"machine", "worker", "resource"}:
            raise ValueError("quota scope must be machine, worker, or resource")
        if self.scope != "machine" and not self.target_id:
            raise ValueError("worker/resource quotas require target_id")
        if self.max_active_leases is not None and self.max_active_leases < 0:
            raise ValueError("max_active_leases must be non-negative")
        if self.max_capacity_units is not None and self.max_capacity_units < 0:
            raise ValueError("max_capacity_units must be non-negative")


@dataclass
class TaskLease:
    task_id: str
    worker_id: str
    resource_id: str
    demand: float
    required_capabilities: list[str] = field(default_factory=list)
    status: str = LeaseStatus.ACTIVE.value
    lease_id: str = field(default_factory=lambda: new_id("lease"))
    acquired_at: float = field(default_factory=now)
    heartbeat_at: float = field(default_factory=now)
    expires_at: float = 0.0
    attempt: int = 1
    result: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.demand < 0:
            raise ValueError("lease demand must be non-negative")
        if self.status not in {x.value for x in LeaseStatus}:
            raise ValueError(f"invalid lease status: {self.status}")
        self.required_capabilities = sorted(set(self.required_capabilities))

    @classmethod
    def from_task(cls, task: TaskDemand, worker_id: str, resource_id: str, lease_seconds: float, *, attempt: int = 1):
        ts = now()
        return cls(
            task_id=task.task_id,
            worker_id=worker_id,
            resource_id=resource_id,
            demand=float(task.demand),
            required_capabilities=list(task.required_capabilities),
            acquired_at=ts,
            heartbeat_at=ts,
            expires_at=ts + float(lease_seconds),
            attempt=attempt,
            metadata=deepcopy(task.metadata),
        )

    def to_dict(self):
        return asdict(self)
