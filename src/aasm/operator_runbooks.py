from __future__ import annotations

import hashlib
import json
import os
import tempfile
from typing import Callable

from .runbook_approval import run_human_approval
from .runbook_common import RUNBOOK_DEFINITIONS, OperatorRunbookResult, list_operator_runbooks
from .runbook_effect import run_unknown_effect
from .runbook_history import run_history_diagnosis
from .runbook_learning import run_learned_no_good
from .runbook_lease import run_lease_loss_recovery
from .runbook_replay import run_replay_fork
from .runbook_requirement import run_requirement_change

RECOVERY_CONTRACT_ID = "aasm.recovery.v1"
RECOVERY_CONTRACT_VERSION = "0.1.0"
RECOVERY_SCENARIOS = [
    "worker_crash", "lease_expiry_reclaim", "stale_completion_rejection",
    "duplicate_delivery", "database_restart", "supervisor_loss", "unknown_effect_reconciliation",
]

RUNBOOK_HANDLERS: dict[str, Callable[..., OperatorRunbookResult]] = {
    "lease-loss": run_lease_loss_recovery,
    "requirement-change": run_requirement_change,
    "learned-no-good": run_learned_no_good,
    "human-approval": run_human_approval,
    "replay-fork": run_replay_fork,
    "unknown-effect": run_unknown_effect,
    "history-diagnosis": run_history_diagnosis,
}


def execute_operator_runbook(runbook_id: str, *, store=None) -> OperatorRunbookResult:
    try: handler = RUNBOOK_HANDLERS[runbook_id]
    except KeyError:
        raise KeyError(f"unknown operator runbook {runbook_id!r}; available={sorted(RUNBOOK_HANDLERS)}") from None
    return handler(store=store)


def distributed_recovery_contract() -> dict:
    return {
        "contract_id": RECOVERY_CONTRACT_ID,
        "contract_version": RECOVERY_CONTRACT_VERSION,
        "schema_version": 1,
        "scenarios": list(RECOVERY_SCENARIOS),
        "success_rule": "ONE_VALID_AUTHORITY_OR_EXPLICIT_RECONCILIATION",
        "evidence": "DETERMINISTIC_FAILURE_INJECTION",
        "fingerprints": {
            "report_sha256": "FULL_EVIDENCE_REPORT",
            "scenario_signature_sha256": "DETERMINISTIC_SCENARIO_OUTCOMES",
        },
    }


def _setup_cert_engine(store=None, *, prefix="worker"):
    from .runtime_v32 import AASMEngine
    from .model import ProblemSpec
    from .resources import ResourceRecord
    from .workers import WorkerRecord
    engine = AASMEngine(ProblemSpec(f"distributed recovery certification {prefix}"), store=store)
    resource_id = f"{prefix}-pool"
    engine.register_resource(ResourceRecord(resource_id, "worker", ["certify"], capacity=2.0, reliability=0.99))
    engine.register_worker(WorkerRecord(f"{prefix}-a", resource_id, heartbeat_timeout=2.0, last_heartbeat=100.0))
    engine.register_worker(WorkerRecord(f"{prefix}-b", resource_id, heartbeat_timeout=5.0, last_heartbeat=103.0))
    return engine


def _digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def certify_distributed_recovery() -> dict:
    from .resources import TaskDemand
    from .persistence.sqlite import SQLiteStore
    rows = []

    engine = _setup_cert_engine(prefix="worker")
    task = TaskDemand("recovery-task", ["certify"], demand=1.0)
    first = engine.claim_task(task, "worker-a", lease_seconds=2.0, at_time=100.0)
    stale = engine.reap_stale_workers(at_time=103.0)
    second = engine.claim_task(task, "worker-b", lease_seconds=10.0, at_time=103.0)
    stale_completion_rejected = False
    try: engine.complete_lease(first["lease_id"], result={"stale": True}, at_time=103.5)
    except Exception: stale_completion_rejected = True
    duplicate_rejected = False
    try: engine.claim_task(task, "worker-b", lease_seconds=10.0, at_time=103.5)
    except Exception: duplicate_rejected = True
    completed = engine.complete_lease(second["lease_id"], result={"recovered": True}, at_time=104.0)
    leases = {row["lease_id"]: row for row in engine.list_leases()}
    rows.extend([
        {"scenario": "worker_crash", "status": "PASS" if "worker-a" in stale else "FAIL", "evidence": {"stale_workers": stale}},
        {"scenario": "lease_expiry_reclaim", "status": "PASS" if leases[first["lease_id"]]["status"] == "EXPIRED" and second["attempt"] == 2 and completed["status"] == "COMPLETED" else "FAIL", "evidence": {"first": leases[first["lease_id"]], "second": completed}},
        {"scenario": "stale_completion_rejection", "status": "PASS" if stale_completion_rejected else "FAIL", "evidence": {"stale_lease_id": first["lease_id"], "active_lease_id": second["lease_id"]}},
        {"scenario": "duplicate_delivery", "status": "PASS" if duplicate_rejected else "FAIL", "evidence": {"task_id": task.task_id, "active_lease_id": second["lease_id"]}},
    ])

    with tempfile.TemporaryDirectory() as td:
        db = os.path.join(td, "recovery.db")
        store = SQLiteStore(db)
        persisted = _setup_cert_engine(store=store, prefix="restart")
        lease = persisted.claim_task(TaskDemand("restart-task", ["certify"], demand=1.0), "restart-a", lease_seconds=20.0, at_time=100.0)
        machine_id = persisted.snapshot.machine_id
        store.close()
        resumed_store = SQLiteStore(db)
        from .runtime_v32 import AASMEngine
        resumed = AASMEngine.resume(machine_id, resumed_store)
        resumed_leases = resumed.list_leases()
        restart_ok = len(resumed_leases) == 1 and resumed_leases[0]["lease_id"] == lease["lease_id"] and resumed_leases[0]["status"] == "ACTIVE"
        resumed_store.close()
        rows.append({"scenario": "database_restart", "status": "PASS" if restart_ok else "FAIL", "evidence": {"machine_id": machine_id, "lease_id": lease["lease_id"]}})

    supervisor = _setup_cert_engine(prefix="supervisor")
    super_task = TaskDemand("supervisor-task", ["certify"], demand=1.0)
    lost = supervisor.claim_task(super_task, "supervisor-a", lease_seconds=30.0, at_time=100.0)
    supervisor.reap_stale_workers(at_time=103.0)
    reclaimed = supervisor.claim_task(super_task, "supervisor-b", lease_seconds=10.0, at_time=103.0)
    supervisor_ok = reclaimed["lease_id"] != lost["lease_id"] and reclaimed["attempt"] == 2
    rows.append({"scenario": "supervisor_loss", "status": "PASS" if supervisor_ok else "FAIL", "evidence": {"lost_lease_id": lost["lease_id"], "reclaimed_lease_id": reclaimed["lease_id"]}})

    effect = run_unknown_effect().to_dict()
    effect_ok = effect["valid"] and effect["checks"].get("unsafe_retry_blocked") and effect["summary"].get("final_status") == "SUCCEEDED"
    rows.append({"scenario": "unknown_effect_reconciliation", "status": "PASS" if effect_ok else "FAIL", "evidence": effect})

    order = {name: i for i, name in enumerate(RECOVERY_SCENARIOS)}
    rows.sort(key=lambda row: order[row["scenario"]])
    report = {
        "contract_id": RECOVERY_CONTRACT_ID,
        "contract_version": RECOVERY_CONTRACT_VERSION,
        "schema_version": 1,
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "scenarios": rows,
    }
    # Preserve a hash over the exact evidence package, including concrete
    # machine/lease/effect identities, and a separate deterministic signature
    # over scenario semantics. Independent executions should have different
    # evidence identities but identical scenario signatures when behavior agrees.
    report["scenario_signature_sha256"] = _digest({
        "contract_id": RECOVERY_CONTRACT_ID,
        "contract_version": RECOVERY_CONTRACT_VERSION,
        "status": report["status"],
        "scenarios": [{"scenario": row["scenario"], "status": row["status"]} for row in rows],
    })
    report["report_sha256"] = _digest(report)
    return report


__all__ = [
    "RUNBOOK_DEFINITIONS", "OperatorRunbookResult", "RUNBOOK_HANDLERS", "list_operator_runbooks",
    "execute_operator_runbook", "run_lease_loss_recovery", "run_requirement_change", "run_learned_no_good",
    "run_human_approval", "run_replay_fork", "run_unknown_effect", "run_history_diagnosis",
    "RECOVERY_CONTRACT_ID", "RECOVERY_CONTRACT_VERSION", "RECOVERY_SCENARIOS",
    "distributed_recovery_contract", "certify_distributed_recovery",
]