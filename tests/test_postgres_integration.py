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
        # `other` is intentionally stale after this first claim. The database,
        # not its local snapshot, must reject a different task that would exceed
        # the same shared resource's capacity.
        e.claim_task(TaskDemand("task-a",["code"],demand=1),"w1",lease_seconds=60)
        with pytest.raises(ValueError,match="Resource capacity exhausted"):
            other.claim_task(TaskDemand("task-b",["code"],demand=1),"w2",lease_seconds=60)
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


def test_postgres_stale_hosts_do_not_overwrite_canonical_state():
    from aasm import AASMEngine, ResourceRecord, WorkerRecord
    from aasm.persistence.postgres import PostgresStore

    a,e=_engine("canonical",capacity=2)
    mid=e.snapshot.machine_id
    b=PostgresStore(DSN)
    other=AASMEngine.resume(mid,b)
    try:
        # Both hosts now advance from the same prior snapshot. Historically the
        # second materialized snapshot write could erase the first host's work.
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
