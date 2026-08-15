import pytest

from aasm.evidence import EvidenceRecord
from aasm.effects import EffectSpec
from aasm.model import ProblemSpec
from aasm.resource_governance import CapacityWindowKind, ResourceCapacity, ResourceDemandEstimate
from aasm.resource_routing import ResourceAwareCandidate, ResourceRoutingPolicy
from aasm.resources import ResourceRecord, TaskDemand
from aasm.runtime_v54_full import AASMEngine
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.workers import WorkerRecord


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"


def _engine():
    engine = AASMEngine(ProblemSpec("v0.54 effect resource settlement"))
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement="settlement root", source="fixture"),
        reason="settlement trust root",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            ROOT,
            ROOT,
            WORKSPACE,
            SCOPE,
            (
                "effect.authorize",
                "effect.execute",
                "resource.capacity.register",
                "resource.reserve",
                "resource.settle",
            ),
        )
    )
    engine.register_resource_capacity(
        ResourceCapacity(
            "api-budget",
            "api_calls",
            "calls",
            owner_principal_id=ROOT,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            window_kind=CapacityWindowKind.FIXED,
            total=10.0,
        ),
        actor_principal_id=ROOT,
    )
    candidate = ResourceAwareCandidate(
        "effect-call",
        correctness=1.0,
        evidence_quality=1.0,
        expected_progress=1.0,
        demands=(
            ResourceDemandEstimate(
                "api_calls",
                2.0,
                "calls",
                resource_id="api-budget",
            ),
        ),
    )
    reserved = engine.select_and_reserve_resource_candidate(
        [candidate],
        ResourceRoutingPolicy(),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    reservation_id = reserved["transaction"]["reservation"]["reservation_id"]
    engine.register_resource(ResourceRecord("effect-worker-resource", "local", capabilities=["effect.execute"], capacity=1.0))
    engine.register_worker(WorkerRecord("worker-1", "effect-worker-resource"))
    return engine, reservation_id


def _effect_with_lease(engine, reservation_id):
    record = engine.propose_effect(
        EffectSpec("external-api-call", idempotency_key="settlement-effect"),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=ROOT,
        resource_reservation_ids=(reservation_id,),
    )
    task = TaskDemand(
        "effect-task",
        required_capabilities=["effect.execute"],
        metadata={"effect_id": record.spec.effect_id},
    )
    lease = engine.claim_task(task, "worker-1", lease_seconds=300)
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    return record, lease


def test_effect_resources_cannot_settle_before_observed_terminal_outcome():
    engine, reservation_id = _engine()
    record, _ = _effect_with_lease(engine, reservation_id)
    before = engine.resource_governance_report(workspace_id=WORKSPACE, scope_id=SCOPE)
    assert before["reservations"][reservation_id]["status"] == "ACTIVE"
    assert before["capacities"]["api-budget"]["committed"] == 2.0
    with pytest.raises(ValueError, match="terminal observed effect outcome"):
        engine.settle_effect_resources(
            record.spec.effect_id,
            {reservation_id: {"api-budget": 1.25}},
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
        )
    after = engine.resource_governance_report(workspace_id=WORKSPACE, scope_id=SCOPE)
    assert after["reservations"][reservation_id]["status"] == "ACTIVE"
    assert after["capacities"]["api-budget"]["committed"] == 2.0
    assert after["capacities"]["api-budget"]["consumed"] == 0.0


def test_confirmed_effect_settles_bound_resource_actuals_and_retry_is_idempotent():
    engine, reservation_id = _engine()
    record, lease = _effect_with_lease(engine, reservation_id)
    completed = engine.execute_effect(
        record.spec.effect_id,
        lambda spec, key: {"http_status": 200},
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        owner_worker_id="worker-1",
        task_lease_id=lease["lease_id"],
    )
    assert completed.reconciliation["outcome"] == "CONFIRMED"
    observation = engine.add_evidence(
        EvidenceRecord(
            kind="resource_observation",
            statement="provider reports 1.25 calls-equivalent actual consumption",
            source="fixture.provider-meter",
        ),
        reason="effect actual resource use observed",
    )
    settled = engine.settle_effect_resources(
        record.spec.effect_id,
        {reservation_id: {"api-budget": 1.25}},
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        observation_evidence_ids=(observation.evidence_id,),
    )
    assert settled["settled_reservation_ids"] == [reservation_id]
    assert settled["settlement"]["outcome"] == "CONFIRMED"
    assert settled["settlement"]["observation_evidence_ids"] == [observation.evidence_id]

    resources = engine.resource_governance_report(workspace_id=WORKSPACE, scope_id=SCOPE)
    assert resources["reservations"][reservation_id]["status"] == "SETTLED"
    assert resources["capacities"]["api-budget"]["committed"] == 0.0
    assert resources["capacities"]["api-budget"]["consumed"] == 1.25
    settlement_id = resources["reservations"][reservation_id]["settlement_id"]
    assert resources["settlements"][settlement_id]["actual_consumption"] == {"api-budget": 1.25}

    summary_evidence = next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == settled["evidence_id"]
    )
    assert observation.evidence_id in summary_evidence["derived_from"]
    resource_settlement_evidence = next(
        row["evidence_id"]
        for row in engine.snapshot.evidence["records"]
        if (row.get("metadata") or {}).get("aasm_resource_record_type") == "settlement_transaction"
        and ((row.get("metadata") or {}).get("document") or {}).get("settlement_id") == settlement_id
    )
    assert resource_settlement_evidence in summary_evidence["derived_from"]

    retried = engine.settle_effect_resources(
        record.spec.effect_id,
        {reservation_id: {"api-budget": 1.25}},
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        observation_evidence_ids=(observation.evidence_id,),
    )
    assert retried["evidence_id"] == settled["evidence_id"]
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_settlement_retry_cannot_rewrite_already_durable_actual_consumption():
    engine, reservation_id = _engine()
    record, lease = _effect_with_lease(engine, reservation_id)
    engine.execute_effect(
        record.spec.effect_id,
        lambda spec, key: {"ok": True},
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        owner_worker_id="worker-1",
        task_lease_id=lease["lease_id"],
    )
    engine.settle_effect_resources(
        record.spec.effect_id,
        {reservation_id: {"api-budget": 1.0}},
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    with pytest.raises(ValueError, match="conflicts with durable actual consumption"):
        engine.settle_effect_resources(
            record.spec.effect_id,
            {reservation_id: {"api-budget": 1.5}},
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
        )
    resources = engine.resource_governance_report(workspace_id=WORKSPACE, scope_id=SCOPE)
    assert resources["capacities"]["api-budget"]["consumed"] == 1.0
