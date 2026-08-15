import os
import pytest

DSN=os.getenv("AASM_TEST_POSTGRES_DSN")
pytestmark=pytest.mark.skipif(not DSN,reason="AASM_TEST_POSTGRES_DSN not configured")


def _engine(goal="pg", *, capacity=2):
    from aasm import AASMEngine, ProblemSpec, ResourceRecord, WorkerRecord
    from aasm.persistence.postgres import PostgresStore

    store=PostgresStore(DSN)
    engine=AASMEngine(ProblemSpec(goal),store=store)
    engine.register_resource(ResourceRecord("cpu","worker",["code","effect.execute"],capacity=capacity))
    engine.register_worker(WorkerRecord("w1","cpu"))
    return store,engine


def test_postgres_multi_connection_claim_exclusion():
    from aasm import AASMEngine, WorkerRecord, TaskDemand
    from aasm.persistence.postgres import PostgresStore

    a,e=_engine("same-task",capacity=2)
    mid=e.snapshot.machine_id
    b=PostgresStore(DSN)
    other=AASMEngine.resume(mid,b)
    other.register_worker(WorkerRecord("w2","cpu"))
    try:
        e.claim_task(TaskDemand("same",["code"]),"w1",lease_seconds=60)
        with pytest.raises(ValueError,match="already claimed"):
            other.claim_task(TaskDemand("same",["code"]),"w2",lease_seconds=60)
    finally:
        a.close(); b.close()


def test_postgres_different_tasks_cannot_overbook_shared_resource():
    from aasm import AASMEngine, WorkerRecord, TaskDemand
    from aasm.persistence.postgres import PostgresStore

    a,e=_engine("capacity",capacity=1)
    mid=e.snapshot.machine_id
    b=PostgresStore(DSN)
    other=AASMEngine.resume(mid,b)
    other.register_worker(WorkerRecord("w2","cpu"))
    try:
        e.claim_task(TaskDemand("task-a",["code"],demand=1),"w1",lease_seconds=60)
        with pytest.raises(ValueError,match="Resource capacity exhausted"):
            other.claim_task(TaskDemand("task-b",["code"],demand=1),"w2",lease_seconds=60)
    finally:
        a.close(); b.close()


def test_postgres_claim_uses_latest_capacity_not_stale_worker_snapshot():
    from aasm import AASMEngine, TaskDemand
    from aasm.persistence.postgres import PostgresStore

    a,e=_engine("stale-capacity",capacity=2)
    mid=e.snapshot.machine_id
    b=PostgresStore(DSN)
    stale=AASMEngine.resume(mid,b)
    try:
        assert stale.list_resources()[0]["capacity"] == 2
        e.update_resource("cpu",{"capacity":0})
        with pytest.raises(ValueError,match="Resource capacity exhausted"):
            stale.claim_task(TaskDemand("stale-cap-task",["code"],demand=1),"w1",lease_seconds=60)
    finally:
        a.close(); b.close()


def test_postgres_machine_quota_is_enforced_across_hosts():
    from aasm import AASMEngine, WorkerRecord, TaskDemand, QuotaPolicy
    from aasm.persistence.postgres import PostgresStore

    a,e=_engine("quota",capacity=4)
    e.set_quota(QuotaPolicy("one-at-a-time",scope="machine",max_active_leases=1))
    mid=e.snapshot.machine_id
    b=PostgresStore(DSN)
    other=AASMEngine.resume(mid,b)
    other.register_worker(WorkerRecord("w2","cpu"))
    try:
        e.claim_task(TaskDemand("task-a",["code"]),"w1",lease_seconds=60)
        with pytest.raises(ValueError,match="Quota exceeded: one-at-a-time"):
            other.claim_task(TaskDemand("task-b",["code"]),"w2",lease_seconds=60)
    finally:
        a.close(); b.close()


def test_postgres_claim_uses_latest_quota_not_stale_worker_snapshot():
    from aasm import AASMEngine, WorkerRecord, TaskDemand, QuotaPolicy
    from aasm.persistence.postgres import PostgresStore

    a,e=_engine("stale-quota",capacity=4)
    e.register_worker(WorkerRecord("w2","cpu"))
    mid=e.snapshot.machine_id
    b=PostgresStore(DSN)
    stale=AASMEngine.resume(mid,b)
    try:
        assert stale.list_quotas() == []
        e.set_quota(QuotaPolicy("new-one-at-a-time",scope="machine",max_active_leases=1))
        e.claim_task(TaskDemand("task-a",["code"]),"w1",lease_seconds=60)
        with pytest.raises(ValueError,match="Quota exceeded: new-one-at-a-time"):
            stale.claim_task(TaskDemand("task-b",["code"],demand=1),"w2",lease_seconds=60)
    finally:
        a.close(); b.close()


def test_postgres_stale_hosts_do_not_overwrite_canonical_state():
    from aasm import AASMEngine, ResourceRecord, WorkerRecord
    from aasm.persistence.postgres import PostgresStore

    a,e=_engine("canonical",capacity=2)
    mid=e.snapshot.machine_id
    b=PostgresStore(DSN)
    other=AASMEngine.resume(mid,b)
    try:
        e.register_resource(ResourceRecord("gpu","worker",["verify"],capacity=1))
        other.register_worker(WorkerRecord("w2","cpu"))

        c=PostgresStore(DSN)
        try:
            canonical=AASMEngine.resume(mid,c)
            assert {r["resource_id"] for r in canonical.list_resources()} == {"cpu","gpu"}
            assert {w["worker_id"] for w in canonical.list_workers()} == {"w1","w2"}
            assert canonical.snapshot.canonical_hash() == canonical.replay().canonical_hash()
        finally:
            c.close()
    finally:
        a.close(); b.close()


def test_postgres_effect_execution_has_single_owner_across_hosts():
    from threading import Event, Thread
    from aasm import AASMEngine, EffectSpec, EffectStatus, TaskDemand
    from aasm.evidence import EvidenceRecord
    from aasm.persistence.postgres import PostgresStore
    from aasm.runtime_v53 import EFFECT_AUTHORITY_CAPABILITIES
    from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace

    a,e=_engine("effect-owner",capacity=1)
    trust=e.add_evidence(
        EvidenceRecord(kind="trust_anchor",statement="postgres effect root",source="fixture"),
        reason="postgres effect trust root",
    )
    e.bootstrap_scoped_workspace(
        Principal("root","SYSTEM"),
        Workspace("workspace-a","root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    e.admit_scoped_authority_grant(ScopedAuthorityGrant(
        "root","root","workspace-a","root",
        (EFFECT_AUTHORITY_CAPABILITIES["authorize"],EFFECT_AUTHORITY_CAPABILITIES["execute"]),
    ))
    rec=e.propose_effect(
        EffectSpec("external-write",idempotency_key="shared-effect"),
        workspace_id="workspace-a",
        scope_id="root",
        proposer_principal_id="root",
    )
    e.authorize_effect(
        rec.spec.effect_id,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    lease=e.claim_task(
        TaskDemand("effect-task",["effect.execute"],metadata={"effect_id":rec.spec.effect_id}),
        "w1",
        lease_seconds=60,
    )
    mid=e.snapshot.machine_id
    b=PostgresStore(DSN)
    other=AASMEngine.resume(mid,b)

    entered=Event()
    release=Event()
    calls=[]
    result_box={}
    error_box={}

    def first_executor(spec,key):
        calls.append("first")
        entered.set()
        if not release.wait(10):
            raise TimeoutError("test executor was not released")
        return {"owner":"first"}

    def run_first():
        try:
            result_box["record"]=e.execute_effect(
                rec.spec.effect_id,
                first_executor,
                workspace_id="workspace-a",
                scope_id="root",
                actor_principal_id="root",
                owner_worker_id="w1",
                task_lease_id=lease["lease_id"],
            )
        except Exception as exc:  # surfaced in the main test thread below
            error_box["error"]=exc

    thread=Thread(target=run_first,daemon=True)
    thread.start()
    try:
        assert entered.wait(10), "first executor never reached the external boundary"

        def forbidden_second_executor(spec,key):
            calls.append("second")
            return {"owner":"second"}

        with pytest.raises(ValueError,match="cannot accept a new dispatch request from status RUNNING"):
            other.execute_effect(
                rec.spec.effect_id,
                forbidden_second_executor,
                workspace_id="workspace-a",
                scope_id="root",
                actor_principal_id="root",
                owner_worker_id="w1",
                task_lease_id=lease["lease_id"],
            )
        assert calls == ["first"]
    finally:
        release.set()
        thread.join(10)
        a.close(); b.close()

    assert not thread.is_alive()
    assert "error" not in error_box
    assert result_box["record"].status == EffectStatus.SUCCEEDED.value
    assert result_box["record"].result == {"owner":"first"}


def test_postgres_v53_resource_guard_rejects_stale_reservation_commit():
    from threading import Event, Thread

    from aasm.evidence import EvidenceRecord
    from aasm.model import ProblemSpec
    from aasm.persistence.postgres import PostgresStore
    from aasm.resource_governance import CapacityWindowKind, ResourceCapacity, ResourceDemandEstimate
    from aasm.resource_routing import ResourceAwareCandidate, ResourceRoutingPolicy
    from aasm.runtime_v53 import AASMEngine, RESOURCE_AUTHORITY_CAPABILITIES
    from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace

    seed_store=PostgresStore(DSN)
    seed=AASMEngine(ProblemSpec("postgres v0.53 resource CAS"),store=seed_store)
    trust=seed.add_evidence(EvidenceRecord(kind="trust_anchor",statement="postgres v53 root",source="fixture"),reason="postgres v53 trust")
    seed.bootstrap_scoped_workspace(Principal("root","SYSTEM"),Workspace("workspace-a","root"),trust_anchor_evidence_id=trust.evidence_id)
    seed.admit_scoped_authority_grant(ScopedAuthorityGrant(
        "root","root","workspace-a","root",
        (RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],RESOURCE_AUTHORITY_CAPABILITIES["reserve"]),
        delegable=True,remaining_delegation_depth=4,
    ))
    seed.register_resource_capacity(ResourceCapacity(
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
    ),actor_principal_id="root")
    mid=seed.snapshot.machine_id
    seed_store.close()

    store_a=PostgresStore(DSN)
    store_b=PostgresStore(DSN)
    host_a=AASMEngine.resume(mid,store_a)
    host_b=AASMEngine.resume(mid,store_b)
    reached_commit=Event()
    release_commit=Event()
    outcome={}
    original_record=host_b._record_resource_document

    def candidate():
        return ResourceAwareCandidate(
            "expert",
            correctness=.95,
            evidence_quality=.95,
            expected_progress=.9,
            provider_quota_burn=50,
            scarce_expert_usage=50,
            demands=(ResourceDemandEstimate(
                "EXPERT_MODEL_ALLOWANCE",50,"credits",resource_id="expert-weekly",upper_bound=50,
            ),),
        )

    def blocked_record(*,record_type,**kwargs):
        if record_type=="routing_transaction":
            reached_commit.set()
            if not release_commit.wait(10):
                raise TimeoutError("PostgreSQL stale reservation test was not released")
        return original_record(record_type=record_type,**kwargs)

    host_b._record_resource_document=blocked_record

    def run_stale_host():
        try:
            outcome["result"]=host_b.select_and_reserve_resource_candidate(
                [candidate()],ResourceRoutingPolicy(),workspace_id="workspace-a",scope_id="root",actor_principal_id="root",
            )
        except Exception as exc:
            outcome["error"]=exc

    thread=Thread(target=run_stale_host,daemon=True)
    thread.start()
    try:
        assert reached_commit.wait(10),"PostgreSQL host B never reached guarded resource commit"
        first=host_a.select_and_reserve_resource_candidate(
            [candidate()],ResourceRoutingPolicy(),workspace_id="workspace-a",scope_id="root",actor_principal_id="root",
        )
        assert first["transaction"]["reservation"]["total_reserved"]==50.0
    finally:
        release_commit.set()
        thread.join(10)

    try:
        assert not thread.is_alive()
        assert "result" not in outcome
        assert isinstance(outcome.get("error"),ValueError)
        assert "Stale machine version" in str(outcome["error"])
        canonical=store_a.load_snapshot(mid)
        assert host_b.snapshot.canonical_hash()==canonical.canonical_hash()
        report=host_b.resource_governance_report(workspace_id="workspace-a",scope_id="root")
        assert len(report["reservations"])==1
        assert report["capacities"]["expert-weekly"]["committed"]==50.0
        assert host_b.replay().canonical_hash()==canonical.canonical_hash()
    finally:
        store_a.close(); store_b.close()
