from datetime import datetime, timezone

from aasm.model import ProblemSpec
from aasm.resource_governance import (
    CapacityWindowKind,
    MeasurementAuthority,
    ResourceCapacity,
    ResourceDemandEstimate,
    ResourceObservation,
)
from aasm.resource_routing import ResourceAwareCandidate, ResourceRoutingPolicy
from aasm.runtime_v52 import AASMEngine
from aasm.sii import StructuredProposal
from aasm.sii_v52 import ResourceAwareStructuredProposal


def test_resource_aware_successor_preserves_parent_identity_and_adds_resource_identity():
    parent = StructuredProposal("p", "decision", "root", {"choice": "x"}, .9)
    wrapped = ResourceAwareStructuredProposal(
        parent,
        resource_demands=(ResourceDemandEstimate("MODEL_ALLOWANCE", 5, "credits", resource_id="expert-weekly", upper_bound=8),),
        expected_correctness=.95,
        expected_evidence_quality=.9,
        expected_progress=.8,
        expected_wall_time_seconds=30,
        expected_monetary_cost=1.25,
        expected_provider_quota_burn=6,
        expected_scarce_expert_usage=5,
    )
    assert wrapped.parent_proposal_id == parent.proposal_id
    assert wrapped.proposal.fingerprint == parent.fingerprint
    assert wrapped.resource_aware_proposal_id.startswith("sii-v52-proposal-")
    assert wrapped.fingerprint != parent.fingerprint


def test_resource_demands_and_provider_quota_burn_participate_in_v52_fingerprint():
    parent = StructuredProposal("p", "decision", "root", "x", .8)
    cheap = ResourceAwareStructuredProposal(parent, resource_demands=(ResourceDemandEstimate("MODEL_ALLOWANCE", 1, "credits"),), expected_provider_quota_burn=1)
    expensive_demand = ResourceAwareStructuredProposal(parent, resource_demands=(ResourceDemandEstimate("MODEL_ALLOWANCE", 2, "credits"),), expected_provider_quota_burn=1)
    expensive_quota = ResourceAwareStructuredProposal(parent, resource_demands=(ResourceDemandEstimate("MODEL_ALLOWANCE", 1, "credits"),), expected_provider_quota_burn=2)
    assert cheap.fingerprint != expensive_demand.fingerprint
    assert cheap.fingerprint != expensive_quota.fingerprint
    assert cheap.parent_proposal_id == expensive_demand.parent_proposal_id == expensive_quota.parent_proposal_id


def test_round_trip_keeps_parent_and_resource_contract():
    parent = StructuredProposal("p", "decision", "root", {"choice": 1}, .7)
    original = ResourceAwareStructuredProposal(parent, resource_demands=(ResourceDemandEstimate("SOLVER", 3, "seconds", confidence=.8),), expected_correctness=.9, expected_provider_quota_burn=2.5)
    restored = ResourceAwareStructuredProposal.from_dict(original.to_dict())
    assert restored.to_dict() == original.to_dict()


def test_invalid_quality_claims_fail_closed():
    parent = StructuredProposal("p", "decision", "root", "x", .5)
    try:
        ResourceAwareStructuredProposal(parent, expected_correctness=1.1)
    except ValueError as exc:
        assert "expected_correctness" in str(exc)
    else:
        raise AssertionError("invalid expected_correctness accepted")


def test_v52_proposal_compiles_directly_into_resource_routing_candidate():
    parent = StructuredProposal("p", "decision", "scope-a", "x", .99)
    wrapped = ResourceAwareStructuredProposal(
        parent,
        resource_demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", 4, "credits", resource_id="expert-weekly", upper_bound=6),),
        expected_correctness=.93,
        expected_evidence_quality=.94,
        expected_progress=.88,
        expected_wall_time_seconds=12,
        expected_monetary_cost=.5,
        expected_provider_quota_burn=3.5,
        expected_scarce_expert_usage=4,
    )
    candidate = wrapped.to_routing_candidate()
    assert candidate.candidate_id == wrapped.resource_aware_proposal_id
    assert candidate.correctness == .93
    assert candidate.evidence_quality == .94
    assert candidate.expected_progress == .88
    assert candidate.provider_quota_burn == 3.5
    assert candidate.demands[0].upper_bound == 6
    assert candidate.metadata["parent_proposal_id"] == parent.proposal_id
    assert candidate.metadata["scope_id"] == "scope-a"


def test_missing_quality_estimates_do_not_inherit_proposer_confidence():
    parent = StructuredProposal("p", "decision", "root", "x", 1.0)
    wrapped = ResourceAwareStructuredProposal(parent)
    candidate = wrapped.to_routing_candidate()
    assert candidate.correctness == 0.0
    assert candidate.evidence_quality == 0.0
    assert candidate.expected_progress == 0.0
    assert candidate.provider_quota_burn == 0.0


def _weekly_capacity(*, consumed=0.0, reserve=20.0):
    return ResourceCapacity(
        resource_id="expert-weekly",
        resource_class="EXPERT_MODEL_ALLOWANCE",
        unit="credits",
        workspace_id="workspace-a",
        scope_id="root",
        provider="fixture",
        window_kind=CapacityWindowKind.FIXED,
        total=100.0,
        consumed=consumed,
        protected_reserve=reserve,
        resets_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
    )


def _expert_candidate(amount=4.0):
    return ResourceAwareCandidate(
        "expert", .96, .95, .90,
        provider_quota_burn=amount,
        scarce_expert_usage=amount,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", amount, "credits", resource_id="expert-weekly", upper_bound=amount),),
    )


def test_routing_explanation_persists_policy_and_pre_reservation_weekly_capacity_snapshot():
    engine = AASMEngine(ProblemSpec("resource explanation"))
    engine.register_resource_capacity(_weekly_capacity(consumed=60, reserve=20))
    engine.record_resource_observation(
        ResourceObservation(
            resource_id="expert-weekly",
            observed_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
            source="provider_usage_surface",
            measurement_authority=MeasurementAuthority.OBSERVED,
            reported_remaining=25.0,
            confidence=.9,
        ),
        workspace_id="workspace-a",
        scope_id="root",
    )
    result = engine.select_and_reserve_resource_candidate(
        [_expert_candidate(amount=4)],
        ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9),
        workspace_id="workspace-a",
        scope_id="root",
    )
    tx_id = result["transaction"]["transaction_id"]
    explanation = engine.resource_routing_explanation_report(workspace_id="workspace-a", scope_id="root")["explanations"][tx_id]
    doc = explanation["document"]
    snapshot = doc["capacity_snapshot"]["expert-weekly"]
    assert snapshot["declared_allocatable"] == 20.0
    assert snapshot["planning_allocatable"] == 5.0
    assert snapshot["protected_reserve"] == 20.0
    assert snapshot["latest_observation"]["measurement_authority"] == "OBSERVED"
    assert doc["policy"]["prefer_lower_provider_quota_burn"] is True
    assert any(row["objective_id"] == "provider_quota_burn" for row in doc["policy"]["objectives"])
    assert doc["candidate_objectives"]["expert"]["provider_quota_burn"] == 4.0
    assert result["evidence_id"] in explanation["derived_from"]
    assert engine.resource_routing_explanation_report(workspace_id="workspace-b", scope_id="root")["explanations"] == {}
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_resource_candidate_pareto_evidence_is_non_mutating_scope_safe_and_replayable():
    engine = AASMEngine(ProblemSpec("resource Pareto evidence"))
    engine.register_resource_capacity(_weekly_capacity(consumed=0, reserve=20))
    quota_route = ResourceAwareCandidate("quota-route", .95, .95, .90, provider_quota_burn=1, monetary_cost=5, wall_time_seconds=10, scarce_expert_usage=2)
    money_route = ResourceAwareCandidate("money-route", .95, .95, .90, provider_quota_burn=5, monetary_cost=1, wall_time_seconds=10, scarce_expert_usage=2)
    dominated = ResourceAwareCandidate("dominated", .95, .95, .90, provider_quota_burn=7, monetary_cost=7, wall_time_seconds=12, scarce_expert_usage=3)
    before = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")["capacities"]["expert-weekly"]["committed"]
    result = engine.record_resource_candidate_pareto_frontier(
        [dominated, money_route, quota_route],
        ResourceRoutingPolicy(),
        workspace_id="workspace-a",
        scope_id="root",
    )
    frontier = result["frontier"]
    assert set(frontier["frontier"]["frontier_candidate_ids"]) == {"quota-route", "money-route"}
    assert result["authority"] == "EVIDENCE_ONLY"
    after = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")["capacities"]["expert-weekly"]["committed"]
    assert before == after == 0.0
    report = engine.resource_candidate_pareto_report(workspace_id="workspace-a", scope_id="root")
    assert frontier["frontier_id"] in report["frontiers"]
    assert engine.resource_candidate_pareto_report(workspace_id="workspace-b", scope_id="root")["frontiers"] == {}
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_settlement_history_projects_resource_estimation_calibration_as_performance_evidence():
    engine = AASMEngine(ProblemSpec("resource calibration"))
    engine.register_resource_capacity(_weekly_capacity(consumed=0, reserve=20))
    result = engine.select_and_reserve_resource_candidate(
        [_expert_candidate(amount=10)],
        ResourceRoutingPolicy(),
        workspace_id="workspace-a",
        scope_id="root",
    )
    reservation_id = result["transaction"]["reservation"]["reservation_id"]
    engine.settle_resource_reservation(reservation_id, {"expert-weekly": 7.0}, workspace_id="workspace-a", scope_id="root")
    calibration = engine.resource_consumption_calibration_report(workspace_id="workspace-a", scope_id="root")
    row = calibration["resources"]["expert-weekly"]
    assert row["samples"] == 1
    assert row["reserved_total"] == 10.0
    assert row["actual_total"] == 7.0
    assert row["mean_signed_error"] == -3.0
    assert row["mean_absolute_error"] == 3.0
    assert row["actual_to_reserved_ratio"] == .7
    assert calibration["authority"] == "PERFORMANCE_EVIDENCE_ONLY"
