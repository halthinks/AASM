from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .resource_governance import ResourceCapacity, ResourceDemandEstimate


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
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
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

    def __post_init__(self) -> None:
        for name in ("min_correctness", "min_evidence_quality", "min_expected_progress"):
            value = float(getattr(self, name))
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")


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


def _matching_capacities(
    demand: ResourceDemandEstimate,
    capacities: dict[str, ResourceCapacity],
) -> list[ResourceCapacity]:
    if demand.resource_id is not None:
        capacity = capacities.get(demand.resource_id)
        return [capacity] if capacity is not None else []
    return sorted(
        (
            capacity
            for capacity in capacities.values()
            if capacity.resource_class == demand.resource_class and capacity.unit == demand.unit
        ),
        key=lambda row: row.resource_id,
    )


def _capacity_rejection_reasons(
    candidate: ResourceAwareCandidate,
    capacities: dict[str, ResourceCapacity],
) -> list[str]:
    reasons: list[str] = []
    for demand in candidate.demands:
        matching = _matching_capacities(demand, capacities)
        if not matching:
            reasons.append(f"missing_capacity:{demand.resource_id or demand.resource_class}")
            continue
        required = _demand_amount(demand)
        if not any(capacity.can_reserve(required) for capacity in matching):
            reasons.append(f"insufficient_or_unknown_capacity:{demand.resource_id or demand.resource_class}")
    return reasons


def select_resource_aware_candidate(
    candidates: Iterable[ResourceAwareCandidate],
    capacities: Iterable[ResourceCapacity],
    policy: ResourceRoutingPolicy,
) -> ResourceRoutingDecision:
    """Select deterministically under hard quality and resource constraints.

    Ordering is lexicographic and intentionally policy-transparent:
    correctness, evidence quality, expected progress are maximized first.
    Only among candidates with identical quality vectors do scarcity, money,
    and wall time break ties. Resource availability is a hard feasibility gate.
    """

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
        reasons.extend(_capacity_rejection_reasons(candidate, capacity_map))
        if reasons:
            rejected[candidate.candidate_id] = tuple(sorted(set(reasons)))
        else:
            eligible.append(candidate)

    if not eligible:
        return ResourceRoutingDecision(
            selected_candidate_id=None,
            eligible_candidate_ids=(),
            rejected=rejected,
            reason="NO_ELIGIBLE_CANDIDATE",
        )

    def rank(candidate: ResourceAwareCandidate) -> tuple[Any, ...]:
        scarcity = candidate.scarce_expert_usage if policy.prefer_lower_scarce_expert_usage else 0.0
        money = candidate.monetary_cost if policy.prefer_lower_monetary_cost else 0.0
        time = candidate.wall_time_seconds if policy.prefer_lower_wall_time else 0.0
        return (
            -candidate.correctness,
            -candidate.evidence_quality,
            -candidate.expected_progress,
            scarcity,
            money,
            time,
            candidate.candidate_id,
        )

    selected = min(eligible, key=rank)
    return ResourceRoutingDecision(
        selected_candidate_id=selected.candidate_id,
        eligible_candidate_ids=tuple(row.candidate_id for row in sorted(eligible, key=lambda row: row.candidate_id)),
        rejected=rejected,
        reason="LEXICOGRAPHIC_QUALITY_THEN_RESOURCE_ECONOMY",
    )


def reserve_candidate_resources(
    candidate: ResourceAwareCandidate,
    capacities: Iterable[ResourceCapacity],
) -> ResourceReservation:
    """Atomically reserve the candidate's conservative demand envelope.

    This function performs a full deterministic allocation plan before mutating
    any capacity. If any demand is infeasible, no reservation is made.
    Resource-class-only demands choose the lexicographically first feasible
    resource ID to keep identical inputs deterministic.
    """

    capacity_map = {row.resource_id: row for row in capacities}
    planned: list[tuple[ResourceCapacity, float]] = []
    provisional: dict[str, float] = {}

    for demand in candidate.demands:
        required = _demand_amount(demand)
        selected: ResourceCapacity | None = None
        for capacity in _matching_capacities(demand, capacity_map):
            already_planned = provisional.get(capacity.resource_id, 0.0)
            available = capacity.allocatable
            if available is not None and required + already_planned <= available:
                selected = capacity
                break
        if selected is None:
            raise ValueError(f"candidate resource reservation infeasible: {demand.resource_id or demand.resource_class}")
        planned.append((selected, required))
        provisional[selected.resource_id] = provisional.get(selected.resource_id, 0.0) + required

    for capacity, amount in planned:
        capacity.reserve(amount)

    return ResourceReservation(
        candidate_id=candidate.candidate_id,
        allocations=tuple((capacity.resource_id, amount) for capacity, amount in planned),
    )


__all__ = [
    "RESOURCE_ROUTING_CONTRACT_ID",
    "RESOURCE_ROUTING_CONTRACT_VERSION",
    "RESOURCE_ROUTING_STABILITY",
    "ResourceAwareCandidate",
    "ResourceReservation",
    "ResourceRoutingDecision",
    "ResourceRoutingPolicy",
    "reserve_candidate_resources",
    "select_resource_aware_candidate",
]
