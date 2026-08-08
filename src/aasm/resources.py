from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field, asdict
from typing import Any


@dataclass
class ResourceRecord:
    resource_id: str
    kind: str
    capabilities: list[str] = field(default_factory=list)
    capacity: float = 1.0
    cost_per_unit: float = 0.0
    reliability: float = 1.0
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.capacity < 0:
            raise ValueError("capacity must be non-negative")
        if not 0.0 <= self.reliability <= 1.0:
            raise ValueError("reliability must be between 0 and 1")
        self.capabilities = sorted(set(self.capabilities))

    def supports(self, required: list[str]) -> bool:
        return set(required).issubset(set(self.capabilities))


@dataclass
class TaskDemand:
    task_id: str
    required_capabilities: list[str] = field(default_factory=list)
    demand: float = 1.0
    priority: int = 0
    allowed_kinds: list[str] = field(default_factory=list)
    max_cost_per_unit: float | None = None
    min_reliability: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.demand < 0:
            raise ValueError("demand must be non-negative")
        if not 0.0 <= self.min_reliability <= 1.0:
            raise ValueError("min_reliability must be between 0 and 1")
        self.required_capabilities = sorted(set(self.required_capabilities))
        self.allowed_kinds = sorted(set(self.allowed_kinds))


@dataclass
class Assignment:
    task_id: str
    resource_id: str
    amount: float


@dataclass
class ScheduleResult:
    assignments: list[Assignment] = field(default_factory=list)
    unmet: dict[str, float] = field(default_factory=dict)
    max_flow: float = 0.0
    total_demand: float = 0.0
    min_cut_edges: list[tuple[str, str, float]] = field(default_factory=list)
    bottlenecks: list[str] = field(default_factory=list)
    resource_utilization: dict[str, float] = field(default_factory=dict)

    @property
    def fully_scheduled(self) -> bool:
        return all(v <= 1e-12 for v in self.unmet.values())

    def to_dict(self):
        return {
            "assignments": [asdict(x) for x in self.assignments],
            "unmet": deepcopy(self.unmet),
            "max_flow": self.max_flow,
            "total_demand": self.total_demand,
            "min_cut_edges": [list(x) for x in self.min_cut_edges],
            "bottlenecks": list(self.bottlenecks),
            "resource_utilization": deepcopy(self.resource_utilization),
            "fully_scheduled": self.fully_scheduled,
        }
