from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .resource_governance import MeasurementAuthority, ResourceCapacity, ResourceDemandEstimate

RESOURCE_ROUTING_CONTRACT_ID = "aasm.resource.routing.v1"
RESOURCE_ROUTING_CONTRACT_VERSION = "0.1.0"
RESOURCE_ROUTING_STABILITY = "FOUNDATION_EXPERIMENTAL"


@dataclass(frozen=True)
class ResourceAwareCandidate:
    candidate_id: str
    correctness: float
    evidence_quality: float
    expected_progress: float
    wall_time_seconds: float = 0.0
    monetary_cost: float = 0.0
    scarce_expert_usage: float = 0.0
    demands: tuple[ResourceDemandEstimate, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.candidate_id.strip():
            raise ValueError("candidate_id is required")
        for name in ("correctness", "evidence_quality", "expected_progress"):
            if not 0.0 <= float(getattr(self, name)) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        for name in ("wall_time_seconds", "monetary_cost", "scarce_expert_usage"):
            if float(getattr(self, name)) < 0:
                raise ValueError(f"{name} must be non-negative")


@dataclass(frozen=True)
class ResourceRoutingPolicy:
    min_correctness: float = 0.0
    min_evidence_quality: float = 0.0
    min_expected_progress: float = 0.0
    preserve_protected_reserve: bool = True
    prefer_lower_scarce_expert_usage: bool = True
    prefer_lower_monetary_cost: bool = True
    prefer_lower_wall_time: bool = True
    constrain_with_observed_remaining: bool = True
    accepted_measurement_authorities: tuple[str, ...] = (
        MeasurementAuthority.AUTHORITATIVE.value,
        MeasurementAuthority.OBSERVED.value,
        MeasurementAuthority.DERIVED.value,
    )
    min_observation_confidence: float = 0.0
    max_observation_freshness_seconds: float | None = None

    def __post_init__(self) -> None:
        for name in ("min_correctness", "min_evidence_quality", "min_expected_progress", "min_observation_confidence"):
            if not 0.0 <= float(getattr(self, name)) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        allowed = {item.value for item in MeasurementAuthority}
        unknown = sorted(set(self.accepted_measurement_authorities) - allowed)
        if unknown:
            raise ValueError(f"unknown measurement authorities: {unknown}")
        object.__setattr__(self, "accepted_measurement_authorities", tuple(sorted(set(self.accepted_measurement_authorities))))
        if self.max_observation_freshness_seconds is not None and self.max_observation_freshness_seconds < 0:
            raise ValueError("max_observation_freshness_seconds must be non-negative")


@dataclass(frozen=True)
class ResourceRoutingDecision:
    selected_candidate_id: str | None
    eligible_candidate_ids: tuple[str, ...]
    rejected: dict[str, tuple[str, ...]]
    reason: str
    contract_id: str = RESOURCE_ROUTING_CONTRACT_ID
    contract_version: str = RESOURCE_ROUTING_CONTRACT_VERSION


@dataclass(frozen=True)
class ResourceReservation:
    candidate_id: str
    allocations: tuple[tuple[str, float], ...]
    contract_id: str = RESOURCE_ROUTING_CONTRACT_ID
    contract_version: str = RESOURCE_ROUTING_CONTRACT_VERSION

    @property
    def total_reserved(self) -> float:
        return sum(amount for _, amount in self.allocations)


def _demand_amount(demand: ResourceDemandEstimate) -> float:
    return float(demand.upper_bound if demand.upper_bound is not None else demand.amount)


def _matching_capacities(demand: ResourceDemandEstimate, capacities: dict[str, ResourceCapacity]) -> list[ResourceCapacity]:
    if demand.resource_id is not None:
        value = capacities.get(demand.resource_id)
        return [value] if value is not None else []
    return sorted(
        (row for row in capacities.values() if row.resource_class == demand.resource_class and row.unit == demand.unit),
        key=lambda row: row.resource_id,
    )


def planning_allocatable(capacity: ResourceCapacity, policy: ResourceRoutingPolicy) -> float | None:
    declared = capacity.allocatable
    if declared is None or not policy.constrain_with_observed_remaining:
        return declared
    observation = capacity.latest_observation
    if observation is None or observation.reported_remaining is None:
        return declared
    if observation.measurement_authority.value not in policy.accepted_measurement_authorities:
        return declared
    if observation.confidence < policy.min_observation_confidence:
        return declared
    if policy.max_observation_freshness_seconds is not None:
        if observation.freshness_seconds is None:
            return declared
        if observation.freshness_seconds > policy.max_observation_freshness_seconds:
            return declared
    observed_available = max(
        0.0,
        float(observation.reported_remaining) - float(capacity.committed) - float(capacity.protected_reserve),
    )
    return min(float(declared), observed_available)


def _capacity_rejection_reasons(candidate: ResourceAwareCandidate, capacities: dict[str, ResourceCapacity], policy: ResourceRoutingPolicy) -> list[str]:
    reasons: list[str] = []
    for demand in candidate.demands:
        matching = _matching_capacities(demand, capacities)
        if not matching:
            reasons.append(f"missing_capacity:{demand.resource_id or demand.resource_class}")
            continue
        required = _demand_amount(demand)
        feasible = False
        for capacity in matching:
            available = planning_allocatable(capacity, policy)
            if available is not None and required <= available:
                feasible = True
                break
        if not feasible:
            reasons.append(f"insufficient_or_unknown_capacity:{demand.resource_id or demand.resource_class}")
    return reasons


def select_resource_aware_candidate(candidates: Iterable[ResourceAwareCandidate], capacities: Iterable[ResourceCapacity], policy: ResourceRoutingPolicy) -> ResourceRoutingDecision:
    capacity_map = {row.resource_id: row for row in capacities}
    rows = sorted(candidates, key=lambda row: row.candidate_id)
    rejected: dict[str, tuple[str, ...]] = {}
    eligible: list[ResourceAwareCandidate] = []
    for candidate in rows:
        reasons: list[str] = []
        if candidate.correctness < policy.min_correctness:
            reasons.append("below_min_correctness")
        if candidate.evidence_quality < policy.min_evidence_quality:
            reasons.append("below_min_evidence_quality")
        if candidate.expected_progress < policy.min_expected_progress:
            reasons.append("below_min_expected_progress")
        reasons.extend(_capacity_rejection_reasons(candidate, capacity_map, policy))
        if reasons:
            rejected[candidate.candidate_id] = tuple(sorted(set(reasons)))
        else:
            eligible.append(candidate)
    if not eligible:
        return ResourceRoutingDecision(None, (), rejected, "NO_ELIGIBLE_CANDIDATE")

    def rank(candidate: ResourceAwareCandidate) -> tuple[Any, ...]:
        return (
            -candidate.correctness,
            -candidate.evidence_quality,
            -candidate.expected_progress,
            candidate.scarce_expert_usage if policy.prefer_lower_scarce_expert_usage else 0.0,
            candidate.monetary_cost if policy.prefer_lower_monetary_cost else 0.0,
            candidate.wall_time_seconds if policy.prefer_lower_wall_time else 0.0,
            candidate.candidate_id,
        )

    selected = min(eligible, key=rank)
    return ResourceRoutingDecision(
        selected.candidate_id,
        tuple(row.candidate_id for row in sorted(eligible, key=lambda row: row.candidate_id)),
        rejected,
        "LEXICOGRAPHIC_QUALITY_THEN_RESOURCE_ECONOMY",
    )


def reserve_candidate_resources(candidate: ResourceAwareCandidate, capacities: Iterable[ResourceCapacity], policy: ResourceRoutingPolicy | None = None) -> ResourceReservation:
    policy = policy or ResourceRoutingPolicy()
    capacity_map = {row.resource_id: row for row in capacities}
    planned: list[tuple[ResourceCapacity, float]] = []
    provisional: dict[str, float] = {}
    for demand in candidate.demands:
        required = _demand_amount(demand)
        selected: ResourceCapacity | None = None
        for capacity in _matching_capacities(demand, capacity_map):
            already_planned = provisional.get(capacity.resource_id, 0.0)
            available = planning_allocatable(capacity, policy)
            if available is not None and required + already_planned <= available:
                selected = capacity
                break
        if selected is None:
            raise ValueError(f"candidate resource reservation infeasible: {demand.resource_id or demand.resource_class}")
        planned.append((selected, required))
        provisional[selected.resource_id] = provisional.get(selected.resource_id, 0.0) + required
    for capacity, amount in planned:
        capacity.reserve(amount)
    return ResourceReservation(candidate.candidate_id, tuple((capacity.resource_id, amount) for capacity, amount in planned))


__all__ = [
    "RESOURCE_ROUTING_CONTRACT_ID",
    "RESOURCE_ROUTING_CONTRACT_VERSION",
    "RESOURCE_ROUTING_STABILITY",
    "ResourceAwareCandidate",
    "ResourceReservation",
    "ResourceRoutingDecision",
    "ResourceRoutingPolicy",
    "planning_allocatable",
    "reserve_candidate_resources",
    "select_resource_aware_candidate",
]
