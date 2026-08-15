from datetime import datetime, timezone

import pytest

from aasm.resource_governance import (
    CapacityWindowKind,
    MeasurementAuthority,
    ResourceCapacity,
    ResourceDemandEstimate,
    ResourceObservation,
)
from aasm.resource_routing import (
    ResourceAwareCandidate,
    ResourceRoutingPolicy,
    planning_allocatable,
    reserve_candidate_resources,
    select_resource_aware_candidate,
)


def weekly_capacity(*, consumed=0.0, reserve=0.0, observation=None):
    return ResourceCapacity(
        resource_id="expert-weekly",
        resource_class="EXPERT_MODEL_ALLOWANCE",
        unit="credits",
        provider="fixture",
        window_kind=CapacityWindowKind.FIXED,
        total=100.0,
        consumed=consumed,
        protected_reserve=reserve,
        resets_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
        latest_observation=observation,
    )


def observed_remaining(remaining, *, authority=MeasurementAuthority.OBSERVED, confidence=1.0, freshness_seconds=0.0):
    return ResourceObservation(
        resource_id="expert-weekly",
        observed_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        source="provider_usage_surface",
        measurement_authority=authority,
        reported_remaining=remaining,
        confidence=confidence,
        freshness_seconds=freshness_seconds,
    )


def test_hard_quality_thresholds_dominate_resource_savings():
    local = ResourceAwareCandidate("local", correctness=.80, evidence_quality=.90, expected_progress=.95, monetary_cost=0, scarce_expert_usage=0)
    expert = ResourceAwareCandidate(
        "expert", correctness=.95, evidence_quality=.95, expected_progress=.90, monetary_cost=5, provider_quota_burn=10, scarce_expert_usage=10,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 10, "credits", resource_id="expert-weekly"),),
    )
    decision = select_resource_aware_candidate([local, expert], [weekly_capacity()], ResourceRoutingPolicy(min_correctness=.90, min_evidence_quality=.90))
    assert decision.selected_candidate_id == "expert"
    assert decision.rejected["local"] == ("below_min_correctness",)


def test_equivalent_quality_preserves_scarce_expert_capacity():
    local = ResourceAwareCandidate("local", .95, .95, .90, scarce_expert_usage=0, monetary_cost=1)
    expert = ResourceAwareCandidate(
        "expert", .95, .95, .90, scarce_expert_usage=10, monetary_cost=0,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 10, "credits", resource_id="expert-weekly"),),
    )
    decision = select_resource_aware_candidate([expert, local], [weekly_capacity()], ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9))
    assert decision.selected_candidate_id == "local"
    assert decision.reason == "LEXICOGRAPHIC_QUALITY_THEN_RESOURCE_ECONOMY"


def test_provider_quota_burn_is_independent_and_precedes_other_economic_tiebreakers():
    quota_efficient = ResourceAwareCandidate(
        "quota-efficient",
        .95,
        .95,
        .90,
        monetary_cost=5,
        provider_quota_burn=1,
        scarce_expert_usage=10,
    )
    quota_hungry = ResourceAwareCandidate(
        "quota-hungry",
        .95,
        .95,
        .90,
        monetary_cost=0,
        provider_quota_burn=8,
        scarce_expert_usage=0,
    )
    decision = select_resource_aware_candidate([quota_hungry, quota_efficient], [], ResourceRoutingPolicy())
    assert decision.selected_candidate_id == "quota-efficient"
    ignored = select_resource_aware_candidate(
        [quota_hungry, quota_efficient],
        [],
        ResourceRoutingPolicy(prefer_lower_provider_quota_burn=False),
    )
    assert ignored.selected_candidate_id == "quota-hungry"


def test_protected_reserve_can_make_expert_path_ineligible():
    expert = ResourceAwareCandidate(
        "expert", .99, .99, .99,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 25, "credits", resource_id="expert-weekly"),),
    )
    fallback = ResourceAwareCandidate("fallback", .92, .92, .92)
    decision = select_resource_aware_candidate([expert, fallback], [weekly_capacity(consumed=60, reserve=20)], ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9))
    assert decision.selected_candidate_id == "fallback"
    assert decision.rejected["expert"] == ("insufficient_or_unknown_capacity:expert-weekly",)


def test_unknown_external_capacity_fails_closed_and_uses_available_alternative():
    unknown = ResourceCapacity(resource_id="expert-weekly", resource_class="EXPERT_MODEL_ALLOWANCE", unit="credits")
    expert = ResourceAwareCandidate(
        "expert", .99, .99, .99,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 5, "credits", resource_id="expert-weekly"),),
    )
    local = ResourceAwareCandidate("local", .91, .91, .91)
    decision = select_resource_aware_candidate([expert, local], [unknown], ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9))
    assert decision.selected_candidate_id == "local"
    assert "insufficient_or_unknown_capacity:expert-weekly" in decision.rejected["expert"]


def test_upper_bound_not_mean_estimate_controls_feasibility():
    expert = ResourceAwareCandidate(
        "expert", .99, .99, .99,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 10, "credits", resource_id="expert-weekly", upper_bound=25),),
    )
    decision = select_resource_aware_candidate([expert], [weekly_capacity(consumed=60, reserve=20)], ResourceRoutingPolicy())
    assert decision.selected_candidate_id is None
    assert decision.reason == "NO_ELIGIBLE_CANDIDATE"


def test_selected_candidate_reserves_upper_bound_atomically():
    capacity = weekly_capacity()
    candidate = ResourceAwareCandidate(
        "expert", .95, .95, .95,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 5, "credits", resource_id="expert-weekly", upper_bound=8),),
    )
    reservation = reserve_candidate_resources(candidate, [capacity])
    assert reservation.allocations == (("expert-weekly", 8.0),)
    assert reservation.total_reserved == 8.0
    assert capacity.committed == 8.0


def test_multi_demand_reservation_is_all_or_nothing():
    expert = weekly_capacity(consumed=80, reserve=10)
    compute = ResourceCapacity("local-cpu", "CPU_SECONDS", "seconds", window_kind=CapacityWindowKind.FIXED, total=100)
    candidate = ResourceAwareCandidate(
        "mixed", .95, .95, .95,
        demands=(
            ResourceDemandEstimate("CPU_SECONDS", 20, "seconds", resource_id="local-cpu"),
            ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 20, "credits", resource_id="expert-weekly"),
        ),
    )
    with pytest.raises(ValueError, match="reservation infeasible"):
        reserve_candidate_resources(candidate, [compute, expert])
    assert compute.committed == 0.0
    assert expert.committed == 0.0


def test_resource_class_only_reservation_is_deterministic():
    a = ResourceCapacity("a", "CPU_SECONDS", "seconds", window_kind=CapacityWindowKind.FIXED, total=50)
    b = ResourceCapacity("b", "CPU_SECONDS", "seconds", window_kind=CapacityWindowKind.FIXED, total=50)
    candidate = ResourceAwareCandidate("local", .9, .9, .9, demands=(ResourceDemandEstimate("CPU_SECONDS", 10, "seconds"),))
    reservation = reserve_candidate_resources(candidate, [b, a])
    assert reservation.allocations == (("a", 10.0),)
    assert a.committed == 10.0
    assert b.committed == 0.0


def test_observed_weekly_remaining_reduces_planning_capacity_without_changing_declared_total():
    capacity = weekly_capacity(consumed=60, reserve=20, observation=observed_remaining(37))
    policy = ResourceRoutingPolicy()
    assert capacity.allocatable == 20.0
    assert planning_allocatable(capacity, policy) == 17.0
    assert capacity.total == 100.0
    assert capacity.latest_observation.measurement_authority is MeasurementAuthority.OBSERVED


def test_observed_remaining_can_force_fallback_even_when_declared_capacity_would_fit():
    capacity = weekly_capacity(consumed=60, reserve=20, observation=observed_remaining(25))
    expert = ResourceAwareCandidate(
        "expert", .99, .99, .99,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 10, "credits", resource_id="expert-weekly"),),
    )
    fallback = ResourceAwareCandidate("fallback", .92, .92, .92)
    decision = select_resource_aware_candidate([expert, fallback], [capacity], ResourceRoutingPolicy(min_correctness=.9))
    assert decision.selected_candidate_id == "fallback"
    assert capacity.allocatable == 20.0
    assert planning_allocatable(capacity, ResourceRoutingPolicy()) == 5.0


def test_unaccepted_declared_observation_does_not_silently_constrain_default_policy():
    capacity = weekly_capacity(consumed=60, reserve=20, observation=observed_remaining(1, authority=MeasurementAuthority.DECLARED))
    assert planning_allocatable(capacity, ResourceRoutingPolicy()) == 20.0
    policy = ResourceRoutingPolicy(accepted_measurement_authorities=("DECLARED",))
    assert planning_allocatable(capacity, policy) == 0.0


def test_low_confidence_or_stale_observation_only_constrains_when_policy_accepts_it():
    low_confidence = weekly_capacity(consumed=60, reserve=20, observation=observed_remaining(25, confidence=.4))
    strict_confidence = ResourceRoutingPolicy(min_observation_confidence=.8)
    assert planning_allocatable(low_confidence, strict_confidence) == 20.0

    stale = weekly_capacity(consumed=60, reserve=20, observation=observed_remaining(25, freshness_seconds=500))
    freshness_policy = ResourceRoutingPolicy(max_observation_freshness_seconds=60)
    assert planning_allocatable(stale, freshness_policy) == 20.0


def test_observation_never_expands_unknown_declared_capacity():
    capacity = ResourceCapacity(
        resource_id="expert-weekly",
        resource_class="EXPERT_MODEL_ALLOWANCE",
        unit="credits",
        latest_observation=observed_remaining(50),
    )
    assert planning_allocatable(capacity, ResourceRoutingPolicy()) is None
