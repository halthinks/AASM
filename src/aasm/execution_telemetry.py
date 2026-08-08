from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .model import now


class TelemetryKind:
    STARTED = "STARTED"
    LOG = "LOG"
    PROGRESS = "PROGRESS"
    ARTIFACT = "ARTIFACT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HEARTBEAT = "HEARTBEAT"

    ALL = {STARTED, LOG, PROGRESS, ARTIFACT, COMPLETED, FAILED, HEARTBEAT}


@dataclass
class TelemetryPolicy:
    max_records: int = 2000
    use_observed_durations: bool = True
    prefer_task_class_duration: bool = True
    min_duration_samples: int = 1
    auto_refresh_fleet_on_completion: bool = True

    def __post_init__(self):
        if self.max_records < 1:
            raise ValueError("max_records must be positive")
        if self.min_duration_samples < 1:
            raise ValueError("min_duration_samples must be positive")


@dataclass
class ExecutionTelemetryRecord:
    worker_id: str
    task_id: str
    lease_id: str
    kind: str
    ts: float = field(default_factory=now)
    duration_seconds: float | None = None
    message: str | None = None
    progress: float | None = None
    artifact_refs: list[str] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.worker_id or not self.task_id or not self.lease_id:
            raise ValueError("worker_id, task_id, and lease_id are required")
        if self.kind not in TelemetryKind.ALL:
            raise ValueError(f"invalid telemetry kind: {self.kind}")
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("duration_seconds must be non-negative")
        if self.progress is not None and not 0 <= float(self.progress) <= 1:
            raise ValueError("progress must be between 0 and 1")
        self.artifact_refs = list(dict.fromkeys(self.artifact_refs))

    def to_dict(self):
        return asdict(self)


class ExecutionTelemetryLedger:
    @staticmethod
    def duration_stats(records: list[dict[str, Any]]):
        task: dict[str, list[float]] = {}
        task_class: dict[str, list[float]] = {}
        for raw in records:
            if raw.get("kind") != TelemetryKind.COMPLETED:
                continue
            duration = raw.get("duration_seconds")
            if duration is None:
                continue
            duration = float(duration)
            task.setdefault(str(raw.get("task_id")), []).append(duration)
            cls = (raw.get("metadata") or {}).get("task_class")
            if cls:
                task_class.setdefault(str(cls), []).append(duration)

        def summarize(values):
            return {
                "samples": len(values),
                "mean_seconds": sum(values) / len(values),
                "min_seconds": min(values),
                "max_seconds": max(values),
            }

        return {
            "by_task": {k: summarize(v) for k, v in sorted(task.items())},
            "by_task_class": {k: summarize(v) for k, v in sorted(task_class.items())},
        }
