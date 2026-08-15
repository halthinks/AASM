from datetime import datetime, timezone

import pytest

from aasm.model import ProblemSpec
from aasm.resource_governance import CapacityWindowKind, ResourceCapacity, ResourceObservation, MeasurementAuthority, ResourceDemandEstimate
from aasm.resource_routing import ResourceAwareCandidate, ResourceRoutingPolicy
from aasm.runtime_v52 import AASMEngine
from aasm.sii import StructuredProposal
from aasm.sii_governance import SIIPrincipalBinding
from aasm.sii_v52 import ResourceAwareStructuredProposal


WORKSPACE = "workspace-a"
SCOPE = "root"


def capacity(resource_id="expert-weekly", total=100.0, consumed=0.0, committed=0.0, reserve=20.0):
    return ResourceCapacity(
        resource_id=resource_id,
        resource_class="EXPERT_MODEL_ALLOWANCE",
        unit="credits",
        owner_principal_id="owner",
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        provider="fixture",
        window_kind=CapacityWindowKind.FIXED,
        total=total,
        consumed=consumed,
        committed=committed,
        protected_reserve=reserve,
        resets_at=datetime(2026, 8, 18, tzinfo=timezone.utc),
    )


def candidate(candidate_id="expert", amount=10.0):
    return ResourceAwareCandidate(
        candidate_id=candidate_id,
        correctness=.96,
        evidence_quality=.95,
        expected_progress=.90,
        scarce_expert_usage=amount,
        demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", amount, "credits", resource_id="expert-weekly", upper_bound=amount),),
    )


def configured_sii_engine():
    engine = AASMEngine(ProblemSpec("resource-aware SII"))
    engine.install_default_sii_scoring_policy(authority_id="policy", authority_class="POLICY")
    engine.bind_sii_principal(
        SIIPrincipalBinding("reasoner", "PROPOSER", can_propose=True),
        authority_id="policy",
        authority_class="POLICY",
    )
    registered = engine.register_sii_proposer(
        principal_id="reasoner",
        name="reasoner",
        kind="llm",
        provider="fixture",
        model_id="expert",
    )
    return engine, registered["identity"]["proposer_id"]


def durable_resource_proposal(engine, proposer_id, *, amount=10.0, workspace_id=WORKSPACE):
    parent = StructuredProposal(proposer_id, "candidate", SCOPE, {"choice": "expert"}, .9)
    submitted_parent = engine.submit_sii_proposal(parent)
    successor = ResourceAwareStructuredProposal(
        parent,
        resource_demands=(ResourceDemandEstimate("EXPERT_MODEL_ALLOWANCE", amount, "credits", resource_id="expert-weekly", upper_bound=amount),),
        expected_correctness=.96,
        expected_evidence_quality=.95,
        expected_progress=.90,
        expected_scarce_expert_usage=amount,
    )
    submitted = engine.submit_resource_aware_sii_proposal(
        successor,
        workspace_id=workspace_id,
        scope_id=SCOPE,
    )
    return parent, submitted_parent, successor, submitted


def report(engine):
    return engine.resource_governance_report(workspace_id=WORKSPACE, scope_id=SCOPE)


def route(engine, rows, policy=None):
    return engine.select_and_reserve_resource_candidate(
        rows,
        policy or ResourceRoutingPolicy(),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
    )


def evidence_row(engine, evidence_id):
    return next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == evidence_id)


def test_capacity_registration_is_durable_and_replay_exact():
    engine = AASMEngine(ProblemSpec("resource replay"))
    engine.register_resource_capacity(capacity())
    value = report(engine)
    assert value["capacities"]["expert-weekly"]["protected_reserve"] == 20.0
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_scoped_capacity_is_hidden_without_context_and_wrong_workspace_cannot_consume():
    engine = AASMEngine(ProblemSpec("resource scope"))
    engine.register_resource_capacity(capacity())
    assert engine.resource_governance_report()["capacities"] == {}
    result = engine.select_and_reserve_resource_candidate([candidate()], ResourceRoutingPolicy(), workspace_id="workspace-b", scope_id=SCOPE)
    assert result["transaction"]["decision"]["selected_candidate_id"] is None
    assert result["transaction"]["reservation"] is None
    assert report(engine)["capacities"]["expert-weekly"]["committed"] == 0.0


def test_unknown_scope_context_fails_closed():
    engine = AASMEngine(ProblemSpec("resource unknown scope"))
    engine.register_resource_capacity(capacity())
    with pytest.raises(KeyError):
        engine.resource_governance_report(workspace_id=WORKSPACE, scope_id="missing-scope")


def test_resource_observation_is_durable_evidence_not_truth_promotion():
    engine = AASMEngine(ProblemSpec("resource observation"))
    engine.register_resource_capacity(capacity())
    result = engine.record_resource_observation(ResourceObservation(
        resource_id="expert-weekly",
        observed_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        source="provider_usage_surface",
        measurement_authority=MeasurementAuthority.OBSERVED,
        reported_remaining=37.0,
        confidence=.9,
    ), workspace_id=WORKSPACE, scope_id=SCOPE)
    value = report(engine)
    assert value["observations"][result["observation_id"]]["measurement_authority"] == "OBSERVED"
    assert value["capacities"]["expert-weekly"]["total"] == 100.0
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_cross_workspace_observation_is_denied():
    engine = AASMEngine(ProblemSpec("resource observation scope"))
    engine.register_resource_capacity(capacity())
    observation = ResourceObservation(
        resource_id="expert-weekly",
        observed_at=datetime(2026, 8, 15, tzinfo=timezone.utc),
        source="fixture",
        measurement_authority=MeasurementAuthority.OBSERVED,
        reported_remaining=37.0,
    )
    with pytest.raises(PermissionError, match="workspace/scope"):
        engine.record_resource_observation(observation, workspace_id="workspace-b", scope_id=SCOPE)


def test_selection_and_reservation_commit_as_one_durable_transaction_projection():
    engine = AASMEngine(ProblemSpec("resource route"))
    engine.register_resource_capacity(capacity())
    local = ResourceAwareCandidate("local", .96, .95, .90, scarce_expert_usage=0)
    expert = candidate()
    result = route(engine, [expert, local], ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9))
    tx = result["transaction"]
    assert tx["decision"]["selected_candidate_id"] == "local"
    assert tx["reservation"]["allocations"] == []
    assert tx["access_context"] == {"workspace_id": WORKSPACE, "scope_id": SCOPE}
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_expert_selection_reserves_then_settlement_reconciles_actual_use():
    engine = AASMEngine(ProblemSpec("resource settle"))
    engine.register_resource_capacity(capacity())
    result = route(engine, [candidate(amount=10)], ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9))
    reservation = result["transaction"]["reservation"]
    reservation_id = reservation["reservation_id"]
    value = report(engine)
    assert value["capacities"]["expert-weekly"]["committed"] == 10.0
    assert value["reservations"][reservation_id]["status"] == "ACTIVE"

    engine.settle_resource_reservation(reservation_id, {"expert-weekly": 7.0}, workspace_id=WORKSPACE, scope_id=SCOPE)
    value = report(engine)
    assert value["capacities"]["expert-weekly"]["committed"] == 0.0
    assert value["capacities"]["expert-weekly"]["consumed"] == 7.0
    assert value["reservations"][reservation_id]["status"] == "SETTLED"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_cross_workspace_settlement_is_denied_without_mutation():
    engine = AASMEngine(ProblemSpec("resource settlement scope"))
    engine.register_resource_capacity(capacity())
    result = route(engine, [candidate()])
    reservation_id = result["transaction"]["reservation"]["reservation_id"]
    with pytest.raises(PermissionError, match="workspace/scope"):
        engine.settle_resource_reservation(reservation_id, {"expert-weekly": 8.0}, workspace_id="workspace-b", scope_id=SCOPE)
    assert report(engine)["capacities"]["expert-weekly"]["committed"] == 10.0


def test_settlement_requires_exact_reserved_resource_set_and_is_idempotency_safe():
    engine = AASMEngine(ProblemSpec("resource settle safety"))
    engine.register_resource_capacity(capacity())
    result = route(engine, [candidate()])
    reservation_id = result["transaction"]["reservation"]["reservation_id"]
    with pytest.raises(ValueError, match="exactly match"):
        engine.settle_resource_reservation(reservation_id, {}, workspace_id=WORKSPACE, scope_id=SCOPE)
    engine.settle_resource_reservation(reservation_id, {"expert-weekly": 8.0}, workspace_id=WORKSPACE, scope_id=SCOPE)
    with pytest.raises(ValueError, match="not active"):
        engine.settle_resource_reservation(reservation_id, {"expert-weekly": 8.0}, workspace_id=WORKSPACE, scope_id=SCOPE)


def test_failed_selection_does_not_create_reservation_or_mutate_capacity():
    engine = AASMEngine(ProblemSpec("resource fail closed"))
    engine.register_resource_capacity(capacity(total=30, consumed=10, reserve=20))
    result = route(engine, [candidate(amount=1)])
    tx = result["transaction"]
    assert tx["decision"]["selected_candidate_id"] is None
    assert tx["reservation"] is None
    value = report(engine)
    assert value["capacities"]["expert-weekly"]["committed"] == 0.0
    assert value["capacities"]["expert-weekly"]["consumed"] == 10.0


def test_resource_aware_successor_requires_already_durable_governed_parent():
    engine, proposer_id = configured_sii_engine()
    parent = StructuredProposal(proposer_id, "candidate", SCOPE, "expert", .9)
    successor = ResourceAwareStructuredProposal(parent, expected_correctness=.95, expected_evidence_quality=.95, expected_progress=.9)
    with pytest.raises(KeyError, match="already durable governed parent"):
        engine.submit_resource_aware_sii_proposal(successor, workspace_id=WORKSPACE, scope_id=SCOPE)


def test_resource_aware_successor_evidence_derives_from_parent_sii_proposal():
    engine, proposer_id = configured_sii_engine()
    parent, parent_submission, successor, submitted = durable_resource_proposal(engine, proposer_id)
    assert submitted["proposal"]["parent_proposal_id"] == parent.proposal_id
    assert submitted["proposal"]["parent_proposal_evidence_id"] == parent_submission["proposal_evidence_id"]
    row = evidence_row(engine, submitted["evidence_id"])
    assert parent_submission["proposal_evidence_id"] in row["derived_from"]
    report = engine.resource_aware_sii_proposal_report(workspace_id=WORKSPACE, scope_id=SCOPE)
    assert successor.resource_aware_proposal_id in report["proposals"]
    assert engine.resource_aware_sii_proposal_report(workspace_id="workspace-b", scope_id=SCOPE)["proposals"] == {}
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_routing_from_durable_sii_proposal_carries_proposal_evidence_lineage_and_reserves():
    engine, proposer_id = configured_sii_engine()
    engine.register_resource_capacity(capacity())
    _, _, successor, submitted = durable_resource_proposal(engine, proposer_id)
    result = engine.route_resource_aware_sii_proposals(
        [successor.resource_aware_proposal_id],
        ResourceRoutingPolicy(min_correctness=.9, min_evidence_quality=.9),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
    )
    tx = result["transaction"]
    assert tx["decision"]["selected_candidate_id"] == successor.resource_aware_proposal_id
    assert tx["reservation"]["allocations"] == [["expert-weekly", 10.0]]
    route_row = evidence_row(engine, result["evidence_id"])
    assert submitted["evidence_id"] in route_row["derived_from"]
    assert report(engine)["capacities"]["expert-weekly"]["committed"] == 10.0
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_durable_resource_proposal_cannot_be_routed_from_wrong_workspace_context():
    engine, proposer_id = configured_sii_engine()
    engine.register_resource_capacity(capacity())
    _, _, successor, _ = durable_resource_proposal(engine, proposer_id)
    with pytest.raises(KeyError, match="unknown resource-aware proposal"):
        engine.route_resource_aware_sii_proposals(
            [successor.resource_aware_proposal_id],
            ResourceRoutingPolicy(),
            workspace_id="workspace-b",
            scope_id=SCOPE,
        )
