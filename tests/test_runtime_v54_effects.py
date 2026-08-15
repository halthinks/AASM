from threading import Event, Thread

import pytest

from aasm.evidence import EvidenceRecord
from aasm.effects import EffectExecutionError, EffectSpec, EffectStatus, RetryPolicy
from aasm.model import ProblemSpec
from aasm.persistence import SQLiteStore
from aasm.resource_governance import CapacityWindowKind, ResourceCapacity, ResourceDemandEstimate
from aasm.resource_routing import ResourceAwareCandidate, ResourceRoutingPolicy
from aasm.resources import ResourceRecord, TaskDemand
from aasm.runtime_v53 import AASMEngine as V53Engine
from aasm.runtime_v54 import AASMEngine
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.workers import WorkerRecord


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"


def bootstrapped_engine(engine_cls=AASMEngine, *, store=None):
    kwargs = {} if store is None else {"store": store}
    engine = engine_cls(ProblemSpec("v0.54 effect governance"), **kwargs)
    trust = engine.add_evidence(
        EvidenceRecord(
            kind="trust_anchor",
            statement="operator admitted workspace root identity",
            source="fixture.root-of-trust",
        ),
        reason="fixture trust anchor recorded",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    return engine


def grant(engine, *capabilities):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            ROOT,
            ROOT,
            WORKSPACE,
            SCOPE,
            tuple(capabilities),
            delegable=True,
            remaining_delegation_depth=4,
        )
    )


def effect_lease(engine, effect_id, *, worker_id="worker-1", task_id="effect-task"):
    if not engine.list_resources():
        engine.register_resource(
            ResourceRecord(
                "worker-resource",
                "local",
                capabilities=["effect.execute"],
                capacity=4.0,
            )
        )
        engine.register_worker(WorkerRecord(worker_id, "worker-resource"))
    task = TaskDemand(
        task_id,
        required_capabilities=["effect.execute"],
        metadata={"effect_id": effect_id},
    )
    return engine.claim_task(task, worker_id, lease_seconds=600.0)


def resource_reservation(engine):
    grant(
        engine,
        "resource.capacity.register",
        "resource.reserve",
        "resource.release",
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
        "effect-resource-candidate",
        correctness=1.0,
        evidence_quality=1.0,
        expected_progress=1.0,
        demands=(
            ResourceDemandEstimate(
                "api_calls",
                1.0,
                "calls",
                resource_id="api-budget",
            ),
        ),
    )
    result = engine.select_and_reserve_resource_candidate(
        [candidate],
        ResourceRoutingPolicy(),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    reservation = result["transaction"]["reservation"]
    assert reservation["status"] == "ACTIVE"
    return reservation["reservation_id"]


def test_executor_cannot_cross_external_boundary_before_atomic_ownership_and_evidence():
    engine = bootstrapped_engine()
    grant(engine, "effect.authorize", "effect.execute")
    record = engine.propose_effect(
        EffectSpec("external-write", idempotency_key="owned-before-boundary"),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=ROOT,
    )
    lease = effect_lease(engine, record.spec.effect_id)
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    observed = {}

    def executor(spec, key):
        durable = engine.store.load_effect(engine.snapshot.machine_id, spec.effect_id)
        assert durable.status == EffectStatus.RUNNING.value
        assert durable.execution_id
        assert durable.intent is not None
        assert durable.dispatch_request is not None
        assert durable.ownership is not None
        assert durable.ownership["execution_id"] == durable.execution_id
        assert durable.ownership["task_lease_id"] == lease["lease_id"]
        assert durable.ownership["owner_worker_id"] == "worker-1"
        ownership_evidence = [
            row
            for row in engine.snapshot.evidence["records"]
            if (row.get("metadata") or {}).get("aasm_effect_governance_record_type") == "effect_ownership"
            and ((row.get("metadata") or {}).get("document") or {}).get("ownership_id")
            == durable.ownership["ownership_id"]
        ]
        assert len(ownership_evidence) == 1
        assert ownership_evidence[0]["evidence_id"] in durable.evidence
        observed["ownership_id"] = durable.ownership["ownership_id"]
        observed["key"] = key
        return {"ok": True}

    result = engine.execute_effect(
        record.spec.effect_id,
        executor,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        owner_worker_id="worker-1",
        task_lease_id=lease["lease_id"],
    )
    assert observed["key"] == "owned-before-boundary"
    assert result.status == EffectStatus.SUCCEEDED.value
    assert result.ownership["ownership_id"] == observed["ownership_id"]
    assert result.reconciliation["outcome"] == "CONFIRMED"
    assert result.reconciliation["ownership_id"] == observed["ownership_id"]
    assert len(result.dispatch_history) == 1
    assert len(result.ownership_history) == 1
    assert len(result.reconciliation_history) == 1
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_released_task_lease_blocks_dispatch_before_executor_or_ownership():
    engine = bootstrapped_engine()
    grant(engine, "effect.authorize", "effect.execute")
    record = engine.propose_effect(
        EffectSpec("external-write", idempotency_key="released-lease"),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=ROOT,
    )
    lease = effect_lease(engine, record.spec.effect_id)
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    engine.release_lease(lease["lease_id"])
    calls = []
    with pytest.raises(ValueError, match="TaskLease is not ACTIVE"):
        engine.execute_effect(
            record.spec.effect_id,
            lambda spec, key: calls.append(key) or {},
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
            owner_worker_id="worker-1",
            task_lease_id=lease["lease_id"],
        )
    assert calls == []
    durable = engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id)
    assert durable.status == EffectStatus.AUTHORIZED.value
    assert durable.dispatch_request is None
    assert durable.ownership is None


def test_released_resource_reservation_blocks_dispatch_before_executor():
    engine = bootstrapped_engine()
    grant(engine, "effect.authorize", "effect.execute")
    reservation_id = resource_reservation(engine)
    record = engine.propose_effect(
        EffectSpec("external-write", idempotency_key="released-reservation"),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=ROOT,
        resource_reservation_ids=(reservation_id,),
    )
    lease = effect_lease(engine, record.spec.effect_id)
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    engine.release_resource_reservation(
        reservation_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    calls = []
    with pytest.raises(ValueError, match="resource reservation is not ACTIVE"):
        engine.execute_effect(
            record.spec.effect_id,
            lambda spec, key: calls.append(key) or {},
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
            owner_worker_id="worker-1",
            task_lease_id=lease["lease_id"],
        )
    assert calls == []
    assert engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id).ownership is None


def test_retry_appends_new_ownership_and_reconciliation_instead_of_overwriting_history():
    engine = bootstrapped_engine()
    grant(engine, "effect.authorize", "effect.execute")
    record = engine.propose_effect(
        EffectSpec(
            "external-write",
            idempotency_key="retry-history",
            retry_policy=RetryPolicy(max_attempts=2, retry_on_failure=True),
        ),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=ROOT,
    )
    lease = effect_lease(engine, record.spec.effect_id)
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    first = engine.execute_effect(
        record.spec.effect_id,
        lambda spec, key: (_ for _ in ()).throw(RuntimeError("first attempt")),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        owner_worker_id="worker-1",
        task_lease_id=lease["lease_id"],
    )
    assert first.status == EffectStatus.FAILED.value
    assert first.reconciliation["outcome"] == "FAILED"
    first_ownership_id = first.ownership["ownership_id"]

    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    second = engine.execute_effect(
        record.spec.effect_id,
        lambda spec, key: {"attempt": 2},
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        owner_worker_id="worker-1",
        task_lease_id=lease["lease_id"],
    )
    assert second.status == EffectStatus.SUCCEEDED.value
    assert second.ownership["ownership_id"] != first_ownership_id
    assert second.reconciliation["outcome"] == "CONFIRMED"
    assert len(second.dispatch_history) == 1
    assert len(second.ownership_history) == 2
    assert len(second.reconciliation_history) == 2
    assert {row["outcome"] for row in second.reconciliation_history} == {"FAILED", "CONFIRMED"}


def test_sqlite_recovery_retains_ownership_marks_unknown_and_requires_scoped_reconciliation(tmp_path):
    db = tmp_path / "v54-unknown.db"
    first_store = SQLiteStore(db)
    first = bootstrapped_engine(store=first_store)
    grant(first, "effect.authorize", "effect.execute", "effect.reconcile")
    record = first.propose_effect(
        EffectSpec("external-write", idempotency_key="v54-unknown"),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=ROOT,
    )
    lease = effect_lease(first, record.spec.effect_id)
    first.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    machine_id = first.snapshot.machine_id
    entered = Event()
    release = Event()
    error_box = {}

    def executor(spec, key):
        durable = first_store.load_effect(machine_id, spec.effect_id)
        assert durable.ownership is not None
        entered.set()
        if not release.wait(10):
            raise TimeoutError("test executor was not released")
        return {"external": "may-have-succeeded"}

    def run_first():
        try:
            first.execute_effect(
                record.spec.effect_id,
                executor,
                workspace_id=WORKSPACE,
                scope_id=SCOPE,
                actor_principal_id=ROOT,
                owner_worker_id="worker-1",
                task_lease_id=lease["lease_id"],
            )
        except Exception as exc:
            error_box["error"] = exc

    thread = Thread(target=run_first, daemon=True)
    thread.start()
    recovery_store = SQLiteStore(db)
    try:
        assert entered.wait(10), "executor never crossed the external boundary"
        running = recovery_store.load_effect(machine_id, record.spec.effect_id)
        ownership_id = running.ownership["ownership_id"]
        execution_id = running.execution_id

        recovered = AASMEngine.resume(machine_id, recovery_store, recover_effects=True)
        unknown = recovery_store.load_effect(machine_id, record.spec.effect_id)
        assert unknown.status == EffectStatus.UNKNOWN.value
        assert unknown.execution_id == execution_id
        assert unknown.ownership["ownership_id"] == ownership_id
        assert unknown.reconciliation["outcome"] == "UNKNOWN"
        assert unknown.reconciliation["ownership_id"] == ownership_id
        assert unknown.reconciliation["retry_blocked"] is True
        assert len(unknown.ownership_history) == 1
        assert len(unknown.reconciliation_history) == 1

        calls = []
        with pytest.raises(ValueError, match="status UNKNOWN"):
            recovered.execute_effect(
                record.spec.effect_id,
                lambda spec, key: calls.append(key) or {},
                workspace_id=WORKSPACE,
                scope_id=SCOPE,
                actor_principal_id=ROOT,
                owner_worker_id="worker-1",
                task_lease_id=lease["lease_id"],
            )
        assert calls == []

        release.set()
        thread.join(10)
        assert isinstance(error_box.get("error"), EffectExecutionError)
        assert "lost execution ownership" in str(error_box["error"])
        assert recovery_store.load_effect(machine_id, record.spec.effect_id).status == EffectStatus.UNKNOWN.value

        reconciled = recovered.reconcile_effect(
            record.spec.effect_id,
            succeeded=True,
            result={"observed": True},
            evidence=["external-observation"],
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
        )
        assert reconciled.status == EffectStatus.SUCCEEDED.value
        assert reconciled.ownership["ownership_id"] == ownership_id
        assert reconciled.reconciliation["outcome"] == "CONFIRMED"
        assert reconciled.reconciliation["ownership_id"] == ownership_id
        assert reconciled.reconciliation["retry_blocked"] is False
        assert len(reconciled.reconciliation_history) == 2
        assert [row["outcome"] for row in reconciled.reconciliation_history] == ["UNKNOWN", "CONFIRMED"]
        report = recovered.effect_governance_report(workspace_id=WORKSPACE, scope_id=SCOPE)
        assert ownership_id in report["ownerships"]
        assert reconciled.reconciliation["reconciliation_id"] in report["reconciliations"]
        assert recovered.replay().canonical_hash() == recovered.snapshot.canonical_hash()
    finally:
        release.set()
        thread.join(10)
        first_store.close()
        recovery_store.close()


def test_v54_refuses_to_silently_adopt_legacy_v53_effect_without_intent():
    store_engine = bootstrapped_engine(V53Engine)
    legacy = store_engine.propose_effect(
        EffectSpec("external-write", idempotency_key="legacy-v53"),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=ROOT,
    )
    machine_id = store_engine.snapshot.machine_id
    upgraded = AASMEngine.resume(machine_id, store_engine.store)
    with pytest.raises(PermissionError, match="explicit intent migration"):
        upgraded.authorize_effect(
            legacy.spec.effect_id,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
        )
    assert upgraded.store.load_effect(machine_id, legacy.spec.effect_id).intent is None


def test_effect_governance_report_is_scope_safe():
    engine = bootstrapped_engine()
    record = engine.propose_effect(
        EffectSpec("external-write", idempotency_key="scope-safe-report"),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=ROOT,
    )
    root_report = engine.effect_governance_report(workspace_id=WORKSPACE, scope_id=SCOPE)
    assert record.spec.effect_id in root_report["effects"]
    assert record.intent["intent_id"] in root_report["intents"]
    other_report = engine.effect_governance_report(workspace_id=WORKSPACE, scope_id="other-scope")
    assert record.spec.effect_id not in other_report["effects"]
    assert root_report["contract"]["resource_state_grants_authority"] is False
