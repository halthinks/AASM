from aasm.resource_governance import ResourceDemandEstimate
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
        expected_scarce_expert_usage=5,
    )

    assert wrapped.parent_proposal_id == parent.proposal_id
    assert wrapped.proposal.fingerprint == parent.fingerprint
    assert wrapped.resource_aware_proposal_id.startswith("sii-v52-proposal-")
    assert wrapped.fingerprint != parent.fingerprint


def test_resource_demands_participate_in_v52_fingerprint():
    parent = StructuredProposal("p", "decision", "root", "x", .8)
    cheap = ResourceAwareStructuredProposal(
        parent,
        resource_demands=(ResourceDemandEstimate("MODEL_ALLOWANCE", 1, "credits"),),
    )
    expensive = ResourceAwareStructuredProposal(
        parent,
        resource_demands=(ResourceDemandEstimate("MODEL_ALLOWANCE", 2, "credits"),),
    )
    assert cheap.fingerprint != expensive.fingerprint
    assert cheap.parent_proposal_id == expensive.parent_proposal_id


def test_round_trip_keeps_parent_and_resource_contract():
    parent = StructuredProposal("p", "decision", "root", {"choice": 1}, .7)
    original = ResourceAwareStructuredProposal(
        parent,
        resource_demands=(ResourceDemandEstimate("SOLVER", 3, "seconds", confidence=.8),),
        expected_correctness=.9,
    )
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
        expected_scarce_expert_usage=4,
    )
    candidate = wrapped.to_routing_candidate()
    assert candidate.candidate_id == wrapped.resource_aware_proposal_id
    assert candidate.correctness == .93
    assert candidate.evidence_quality == .94
    assert candidate.expected_progress == .88
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
