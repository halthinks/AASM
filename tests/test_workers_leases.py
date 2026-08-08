import os
import tempfile

import pytest

from aasm import AASMEngine, ProblemSpec, ResourceRecord, TaskDemand, SQLiteStore
from aasm.workers import WorkerRecord, WorkerStatus, LeaseStatus, QuotaPolicy


def setup_engine(store=None):
    e=AASMEngine(ProblemSpec("distributed work"),store=store)
    e.register_resource(ResourceRecord("cpu-a","worker",["python","tests"],capacity=2.0,reliability=0.99))
    e.register_worker(WorkerRecord("worker-a","cpu-a",heartbeat_timeout=30.0,last_heartbeat=100.0))
    return e


def test_claim_heartbeat_complete_and_reclaim():
    e=setup_engine()
    task=TaskDemand("t1",["python"],demand=1.0)
    lease=e.claim_task(task,"worker-a",lease_seconds=10,at_time=100.0)
    assert lease["status"] == LeaseStatus.ACTIVE.value
    assert lease["expires_at"] == 110.0
    lease=e.lease_heartbeat(lease["lease_id"],extend_seconds=20,at_time=105.0)
    assert lease["expires_at"] == 125.0
    done=e.complete_lease(lease["lease_id"],result={"ok":True},at_time=106.0)
    assert done["status"] == LeaseStatus.COMPLETED.value
    lease2=e.claim_task(task,"worker-a",lease_seconds=5,at_time=107.0)
    assert lease2["attempt"] == 2


def test_expired_lease_can_be_reclaimed():
    e=setup_engine()
    task=TaskDemand("t2",["python"],demand=1.0)
    first=e.claim_task(task,"worker-a",lease_seconds=5,at_time=100.0)
    expired=e.expire_leases(at_time=106.0)
    assert expired[0]["status"] == LeaseStatus.EXPIRED.value
    second=e.claim_task(task,"worker-a",lease_seconds=5,at_time=106.0)
    assert second["attempt"] == 2
    assert second["lease_id"] != first["lease_id"]


def test_quota_and_capacity_are_enforced():
    e=setup_engine()
    e.set_quota(QuotaPolicy("worker-one","worker","worker-a",max_active_leases=1))
    e.claim_task(TaskDemand("a",["python"],1.0),"worker-a",lease_seconds=20,at_time=100.0)
    with pytest.raises(ValueError,match="Quota exceeded"):
        e.claim_task(TaskDemand("b",["python"],1.0),"worker-a",lease_seconds=20,at_time=100.0)


def test_stale_worker_expires_leases():
    e=setup_engine()
    lease=e.claim_task(TaskDemand("a",["python"],1.0),"worker-a",lease_seconds=100,at_time=100.0)
    stale=e.reap_stale_workers(at_time=131.0)
    assert stale == ["worker-a"]
    worker=next(x for x in e.list_workers() if x["worker_id"]=="worker-a")
    assert worker["status"] == WorkerStatus.STALE.value
    lease=next(x for x in e.list_leases() if x["lease_id"]==lease["lease_id"])
    assert lease["status"] == LeaseStatus.EXPIRED.value


def test_sqlite_claim_is_cross_process_safe():
    with tempfile.TemporaryDirectory() as td:
        db=os.path.join(td,"runs.db")
        s1=SQLiteStore(db); e1=setup_engine(s1); mid=e1.snapshot.machine_id
        e2=AASMEngine.resume(mid,SQLiteStore(db))
        task=TaskDemand("same",["python"],1.0)
        e1.claim_task(task,"worker-a",lease_seconds=60,at_time=100.0)
        with pytest.raises(ValueError,match="already claimed"):
            e2.claim_task(task,"worker-a",lease_seconds=60,at_time=100.0)
        s1.close(); e2.store.close()


def test_restart_and_fork_preserve_historical_leases():
    with tempfile.TemporaryDirectory() as td:
        db=os.path.join(td,"runs.db")
        store=SQLiteStore(db); e=setup_engine(store)
        e.claim_task(TaskDemand("x",["python"],1.0),"worker-a",lease_seconds=20,at_time=100.0)
        seq=e.events[-1].sequence
        mid=e.snapshot.machine_id; store.close()
        store=SQLiteStore(db); resumed=AASMEngine.resume(mid,store)
        assert len(resumed.list_leases()) == 1
        resumed.complete_lease(resumed.list_leases()[0]["lease_id"],at_time=101.0)
        forked=resumed.fork(seq)
        assert forked.list_leases()[0]["status"] == LeaseStatus.ACTIVE.value
        store.close()
