from __future__ import annotations

from .model import ProblemSpec
from .resources import ResourceRecord, TaskDemand
from .runbook_common import OperatorRunbookResult, finish_runbook, store_or_memory
from .runtime_v25 import AASMEngine
from .workers import WorkerRecord


def run_lease_loss_recovery(*, store=None) -> OperatorRunbookResult:
    """Exercise stale-worker lease expiry and deterministic task reclamation."""

    store = store_or_memory(store)
    engine = AASMEngine(ProblemSpec("Recover a task after lease ownership is lost"), store=store)
    engine.register_resource(
        ResourceRecord(
            "runbook-worker-pool",
            "local-process",
            capabilities=["runbook.execute"],
            capacity=1.0,
        )
    )
    engine.register_worker(
        WorkerRecord(
            "runbook-worker-lost",
            "runbook-worker-pool",
            heartbeat_timeout=2.0,
            last_heartbeat=1000.0,
        )
    )
    engine.register_worker(
        WorkerRecord(
            "runbook-worker-recovery",
            "runbook-worker-pool",
            heartbeat_timeout=5.0,
            last_heartbeat=1003.0,
        )
    )
    task = TaskDemand(
        "runbook-lease-task",
        required_capabilities=["runbook.execute"],
        metadata={"runbook_id": "lease-loss"},
    )
    first = engine.claim_task(
        task,
        "runbook-worker-lost",
        lease_seconds=2.0,
        at_time=1000.0,
    )
    stale_workers = engine.reap_stale_workers(at_time=1003.0)
    engine.worker_heartbeat("runbook-worker-recovery", at_time=1003.0)
    second = engine.claim_task(
        task,
        "runbook-worker-recovery",
        lease_seconds=10.0,
        at_time=1003.0,
    )
    completed = engine.complete_lease(
        second["lease_id"],
        result={"recovered": True, "source_lease_id": first["lease_id"]},
        at_time=1004.0,
    )
    leases = {row["lease_id"]: row for row in engine.list_leases()}
    checks = {
        "stale_worker_detected": "runbook-worker-lost" in stale_workers,
        "lost_lease_expired": leases[first["lease_id"]]["status"] == "EXPIRED",
        "task_reclaimed_with_new_lease": second["lease_id"] != first["lease_id"],
        "attempt_incremented": int(second["attempt"]) == 2,
        "recovery_lease_completed": completed["status"] == "COMPLETED",
    }
    return finish_runbook(
        "lease-loss",
        machine_id=engine.snapshot.machine_id,
        checks=checks,
        summary={
            "stale_workers": stale_workers,
            "lost_lease": leases[first["lease_id"]],
            "recovery_lease": completed,
            "operator_action": "Reclaim only after canonical lease expiry or release.",
        },
        evidence=[
            {"kind": "lease", "lease_id": first["lease_id"], "status": "EXPIRED"},
            {"kind": "lease", "lease_id": second["lease_id"], "status": "COMPLETED"},
        ],
    )
