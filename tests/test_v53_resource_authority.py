import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.resource_governance import CapacityWindowKind, ResourceCapacity, ResourceDemandEstimate
from aasm.resource_routing import ResourceAwareCandidate, ResourceRoutingPolicy
from aasm.runtime_v53 import AASMEngine, RESOURCE_AUTHORITY_CAPABILITIES
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace


def engine_with_workspace_and_root(*capabilities):
    engine = AASMEngine(ProblemSpec("v0.53 resource authority"))
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement="fixture root", source="fixture"),
        reason="fixture root recorded",
    )
    engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace("workspace-a", "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    if capabilities:
        engine.admit_scoped_authority_grant(
            ScopedAuthorityGrant(
                "root",
                "root",
                "workspace-a",
                "root",
                tuple(capabilities),
                delegable=True,
                remaining_delegation_depth=4,
            )
        )
    return engine


def capacity():
    return ResourceCapacity(
        resource_id="expert-weekly",
        resource_class="EXPERT_MODEL_ALLOWANCE",
        unit="credits",
        owner_principal_id="root",
        workspace_id="workspace-a",
        scope_id="root",
        provider="fixture",
        window_kind=CapacityWindowKind.FIXED,
        total=100.0,
        protected_reserve=20.0,
    )


def candidate(amount=10.0):
    return ResourceAwareCandidate(
        "expert",
        correctness=.95,
        evidence_quality=.95,
        expected_progress=.9,
        provider_quota_burn=amount,
        scarce_expert_usage=amount,
        demands=(
            ResourceDemandEstimate(
                "EXPERT_MODEL_ALLOWANCE",
                amount,
                "credits",
                resource_id="expert-weekly",
                upper_bound=amount,
            ),
        ),
    )


def test_v53_resource_capacity_registration_requires_actor_workspace_and_scope_authority():
    engine = engine_with_workspace_and_root(RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"])
    with pytest.raises(PermissionError, match="actor_principal_id"):
        engine.register_resource_capacity(capacity())
    assert engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")["capacities"] == {}

    result = engine.register_resource_capacity(capacity(), actor_principal_id="root")
    assert result["capacity"]["resource_id"] == "expert-weekly"
    assert result["authority_decision_evidence_id"]
    assert result["authority_binding_evidence_id"]
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_denied_reservation_is_durable_authority_evidence_but_never_resource_commitment():
    engine = engine_with_workspace_and_root(RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"])
    engine.register_resource_capacity(capacity(), actor_principal_id="root")
    before_resource = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")
    before_authority = engine.scoped_authority_report(workspace_id="workspace-a")

    with pytest.raises(PermissionError, match="resource.reserve"):
        engine.select_and_reserve_resource_candidate(
            [candidate()],
            ResourceRoutingPolicy(),
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )

    after_resource = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")
    after_authority = engine.scoped_authority_report(workspace_id="workspace-a")
    assert after_resource["reservations"] == before_resource["reservations"] == {}
    assert len(after_authority["decisions"]) == len(before_authority["decisions"]) + 1
    assert any(
        row["decision"]["reason"] == "NO_APPLICABLE_GRANT"
        for row in after_authority["decisions"].values()
    )


def test_authorized_reservation_transaction_derives_from_authority_decision():
    engine = engine_with_workspace_and_root(
        RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],
        RESOURCE_AUTHORITY_CAPABILITIES["reserve"],
    )
    engine.register_resource_capacity(capacity(), actor_principal_id="root")
    result = engine.select_and_reserve_resource_candidate(
        [candidate()],
        ResourceRoutingPolicy(),
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    authority_evidence_id = result["authority_decision_evidence_id"]
    transaction_evidence_id = result["evidence_id"]
    transaction_evidence = next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == transaction_evidence_id
    )
    assert authority_evidence_id in transaction_evidence["derived_from"]
    reservation = result["transaction"]["reservation"]
    assert reservation["status"] == "ACTIVE"
    assert reservation["total_reserved"] == 10.0
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_settlement_has_independent_capability_and_preserves_reservation_when_denied():
    engine = engine_with_workspace_and_root(
        RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],
        RESOURCE_AUTHORITY_CAPABILITIES["reserve"],
    )
    engine.register_resource_capacity(capacity(), actor_principal_id="root")
    reserved = engine.select_and_reserve_resource_candidate(
        [candidate()],
        ResourceRoutingPolicy(),
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    reservation_id = reserved["transaction"]["reservation"]["reservation_id"]
    with pytest.raises(PermissionError, match="resource.settle"):
        engine.settle_resource_reservation(
            reservation_id,
            {"expert-weekly": 7.0},
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
    report = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")
    assert report["reservations"][reservation_id]["status"] == "ACTIVE"
    assert report["settlements"] == {}

    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "root",
            "root",
            "workspace-a",
            "root",
            (RESOURCE_AUTHORITY_CAPABILITIES["settle"],),
        )
    )
    settled = engine.settle_resource_reservation(
        reservation_id,
        {"expert-weekly": 7.0},
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    settlement_evidence = next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == settled["evidence_id"]
    )
    assert settled["authority_decision_evidence_id"] in settlement_evidence["derived_from"]
    assert engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")["reservations"][reservation_id]["status"] == "SETTLED"


def test_v53_rejects_unscoped_resource_capacity_instead_of_falling_back_to_v52_bypass():
    engine = engine_with_workspace_and_root(RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"])
    unscoped = ResourceCapacity(
        "legacy-global",
        "CPU_SECONDS",
        "seconds",
        window_kind=CapacityWindowKind.FIXED,
        total=10,
    )
    with pytest.raises(PermissionError, match="workspace_id, and scope_id"):
        engine.register_resource_capacity(unscoped, actor_principal_id="root")
