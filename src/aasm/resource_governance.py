from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class CapacityWindowKind(str, Enum):
    """How a resource's usable capacity changes over time."""

    FIXED = "FIXED"
    ROLLING = "ROLLING"
    REFILLING = "REFILLING"
    CREDIT_BALANCE = "CREDIT_BALANCE"
    UNBOUNDED = "UNBOUNDED"
    UNKNOWN = "UNKNOWN"


class MeasurementAuthority(str, Enum):
    """Epistemic status of a capacity or consumption observation."""

    AUTHORITATIVE = "AUTHORITATIVE"
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    ESTIMATED = "ESTIMATED"
    DECLARED = "DECLARED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ResourceObservation:
    """Evidence about capacity; never silently promoted to provider truth."""

    resource_id: str
    observed_at: datetime
    source: str
    measurement_authority: MeasurementAuthority
    reported_capacity: float | None = None
    reported_consumed: float | None = None
    reported_remaining: float | None = None
    confidence: float = 1.0
    freshness_seconds: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.freshness_seconds is not None and self.freshness_seconds < 0:
            raise ValueError("freshness_seconds must be non-negative")
        for name in ("reported_capacity", "reported_consumed", "reported_remaining"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")

    @property
    def is_authoritative(self) -> bool:
        return self.measurement_authority is MeasurementAuthority.AUTHORITATIVE


@dataclass
class ResourceCapacity:
    """Governed capacity envelope from which leases/reservations may draw.

    Capacity may represent resources AASM owns directly or externally metered
    capacity such as a weekly model/subscription allowance. Unknown or merely
    observed provider capacity remains explicitly distinguishable from an
    authoritative meter.
    """

    resource_id: str
    resource_class: str
    unit: str
    owner_principal_id: str | None = None
    workspace_id: str | None = None
    scope_id: str | None = None
    provider: str | None = None
    window_kind: CapacityWindowKind = CapacityWindowKind.UNKNOWN
    total: float | None = None
    consumed: float = 0.0
    committed: float = 0.0
    protected_reserve: float = 0.0
    window_seconds: float | None = None
    resets_at: datetime | None = None
    refill_rate_per_second: float | None = None
    latest_observation: ResourceObservation | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in (
            "total",
            "consumed",
            "committed",
            "protected_reserve",
            "window_seconds",
            "refill_rate_per_second",
        ):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} must be non-negative")
        if self.resets_at is not None and self.resets_at.tzinfo is None:
            raise ValueError("resets_at must be timezone-aware")
        if self.latest_observation is not None and self.latest_observation.resource_id != self.resource_id:
            raise ValueError("latest_observation must refer to this resource_id")
        if self.window_kind is CapacityWindowKind.UNBOUNDED and self.total is not None:
            raise ValueError("UNBOUNDED capacity must not declare a finite total")

    @property
    def allocatable(self) -> float | None:
        if self.window_kind is CapacityWindowKind.UNBOUNDED:
            return float("inf")
        if self.total is None:
            return None
        return max(0.0, self.total - self.consumed - self.committed - self.protected_reserve)

    def can_reserve(self, amount: float) -> bool:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        available = self.allocatable
        if available is None:
            return False
        return amount <= available

    def reserve(self, amount: float) -> None:
        if not self.can_reserve(amount):
            raise ValueError("insufficient allocatable capacity")
        self.committed += amount

    def release(self, amount: float) -> None:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        if amount > self.committed:
            raise ValueError("cannot release more than committed capacity")
        self.committed -= amount

    def settle(self, reserved_amount: float, actual_consumption: float) -> None:
        """Reconcile a reservation with actual metered consumption."""

        if reserved_amount < 0 or actual_consumption < 0:
            raise ValueError("settlement amounts must be non-negative")
        if reserved_amount > self.committed:
            raise ValueError("reserved_amount exceeds committed capacity")
        self.committed -= reserved_amount
        self.consumed += actual_consumption

    def seconds_until_reset(self, *, now: datetime | None = None) -> float | None:
        if self.resets_at is None:
            return None
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return max(0.0, (self.resets_at - current).total_seconds())


@dataclass(frozen=True)
class ResourceDemandEstimate:
    """A proposal-side estimate used for governed allocation and replanning."""

    resource_class: str
    amount: float
    unit: str
    resource_id: str | None = None
    upper_bound: float | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("amount must be non-negative")
        if self.upper_bound is not None and self.upper_bound < self.amount:
            raise ValueError("upper_bound must be >= amount")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
