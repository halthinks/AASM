from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class FleetControlPolicy:
    enabled: bool = False
    enforce_admission_limit: bool = True
    floor_workers: int = 0
    ceiling_workers: int | None = None
    auto_refresh_on_plan_interrupt: bool = True
    auto_refresh_on_change_resolution: bool = True

    def __post_init__(self):
        if self.floor_workers < 0:
            raise ValueError("floor_workers must be non-negative")
        if self.ceiling_workers is not None and self.ceiling_workers < 0:
            raise ValueError("ceiling_workers must be non-negative")
        if self.ceiling_workers is not None and self.floor_workers > self.ceiling_workers:
            raise ValueError("floor_workers cannot exceed ceiling_workers")

    def apply(self, recommended_workers: int | None) -> int | None:
        if not self.enabled or recommended_workers is None:
            return None
        value = max(self.floor_workers, int(recommended_workers))
        if self.ceiling_workers is not None:
            value = min(value, self.ceiling_workers)
        return value

    def to_dict(self):
        return asdict(self)
