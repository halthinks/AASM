import os
import pytest

DSN=os.getenv("AASM_TEST_POSTGRES_DSN")
pytestmark=pytest.mark.skipif(not DSN,reason="AASM_TEST_POSTGRES_DSN not configured")


def _engine(goal="pg", *, capacity=2):
    from aasm import AASMEngine, ProblemSpec, ResourceRecord, WorkerRecord
    from aasm.persistence.postgres import PostgresStore

    store=PostgresStore(DSN)
    engine=AASMEngine(ProblemSpec(goal),store=store)
    engine.register_resource(ResourceRecord("cpu","worker",["code"],capacity=capacity))
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
        # The stale engine still believes capacity is 2. PostgreSQL must apply
        # the canonical capacity=0 configuration written by the other host.
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
        # `stale` has no local copy of the new quota, so only DB-canonical
        # enforcement can reject this different task.
        with pytest.raises(ValueError,match="Quota exceeded: new-one-at-a-time"):
            stale.claim_task(TaskDemand("task-b",["code"]),"w2",lease_seconds=60)
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
