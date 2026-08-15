from datetime import datetime, timezone

from aasm.resource_governance import (
    CapacityWindowKind,
    ResourceCapacity,
    ResourceDemandEstimate,
)
from aasm.resource_routing import (
    ResourceAwareCandidate,
    ResourceRoutingPolicy,
    select_resource_aware_candidate,
)


def weekly_capacity(*, consumed=0.0, reserve=0.0):
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
    )


def test_hard_quality_thresholds_dominate_resource_savings():
    local = ResourceAwareCandidate(
        "local",
        correctness=.80,
        evidence_quality=.90,
        expected_progress=.95,
        monetary_cost=0,
        scarce_expert_usage=0,
    )
    expert = ResourceAwareCandidate(
        "expert",
        correctness=.95,
        evidence_quality=.95,
        expected_progress=.90,
        monetary_cost=5,
        scarce_expert_usage=10,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 10, "credits", resource_id="expert-weekly"),),
    )
    decision = select_resource_aware_candidate(
        [local, expert],
        [weekly_capacity()],
        ResourceRoutingPolicy(min_correctness=.90, min_evidence_quality=.90),
    )
    assert decision.selected_candidate_id == "expert"
    assert decision.rejected["local"] == ("below_min_correctness",)


def test_equivalent_quality_preserves_scarce_expert_capacity():
    local = ResourceAwareCandidate("local", .95, .95, .90, scarce_expert_usage=0, monetary_cost=1)
    expert = ResourceAwareCandidate(
        "expert",
        .95,
        .95,
        .90,
        scarce_expert_usage=10,
        monetary_cost=0,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 10, "credits", resource_id="expert-weekly"),),
    )
    decision = select_resource_aware_candidate(
        [expert, local],
        [weekly_capacity()],
        ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9),
    )
    assert decision.selected_candidate_id == "local"
    assert decision.reason == "LEXICOGRAPHIC_QUALITY_THEN_RESOURCE_ECONOMY"


def test_protected_reserve_can_make_expert_path_ineligible():
    expert = ResourceAwareCandidate(
        "expert",
        .99,
        .99,
        .99,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 25, "credits", resource_id="expert-weekly"),),
    )
    fallback = ResourceAwareCandidate("fallback", .92, .92, .92)
    decision = select_resource_aware_candidate(
        [expert, fallback],
        [weekly_capacity(consumed=60, reserve=20)],
        ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9),
    )
    assert decision.selected_candidate_id == "fallback"
    assert decision.rejected["expert"] == ("insufficient_or_unknown_capacity:expert-weekly",)


def test_unknown_external_capacity_fails_closed_and_uses_available_alternative():
    unknown = ResourceCapacity(
        resource_id="expert-weekly",
        resource_class="EXPERT_MODEL_ALLOWANCE",
        unit="credits",
    )
    expert = ResourceAwareCandidate(
        "expert",
        .99,
        .99,
        .99,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 5, "credits", resource_id="expert-weekly"),),
    )
    local = ResourceAwareCandidate("local", .91, .91, .91)
    decision = select_resource_aware_candidate(
        [expert, local],
        [unknown],
        ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9),
    )
    assert decision.selected_candidate_id == "local"
    assert "insufficient_or_unknown_capacity:expert-weekly" in decision.rejected["expert"]


def test_upper_bound_not_mean_estimate_controls_feasibility():
    expert = ResourceAwareCandidate(
        "expert",
        .99,
        .99,
        .99,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 10, "credits", resource_id="expert-weekly", upper_bound=25),),
    )
    decision = select_resource_aware_candidate(
        [expert],
        [weekly_capacity(consumed=60, reserve=20)],
        ResourceRoutingPolicy(),
    )
    assert decision.selected_candidate_id is None
    assert decision.reason == "NO_ELIGIBLE_CANDIDATE"
