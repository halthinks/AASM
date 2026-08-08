from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .effects import EffectSpec, RetryPolicy
from .execution_telemetry import ExecutionTelemetryLedger, ExecutionTelemetryRecord, TelemetryKind, TelemetryPolicy
from .provisioning import ProvisioningAction, ProvisioningPlan, ProvisioningRequest
from .runtime_v16 import AASMEngine as V16Engine
from .workers import WorkerStatus


class AASMEngine(V16Engine):
    """v0.17 runtime: authority-gated fleet provisioning and live telemetry."""

    def telemetry_policy(self):
        raw = self.snapshot.resources.get("telemetry_policy")
        return TelemetryPolicy(**deepcopy(raw)) if raw else TelemetryPolicy()

    def configure_telemetry(self, policy: TelemetryPolicy, *, reason="execution telemetry policy configured"):
        resources = deepcopy(self.snapshot.resources)
        resources["telemetry_policy"] = asdict(policy)
        self.patch_snapshot({"resources": resources}, reason)
        return deepcopy(resources["telemetry_policy"])

    def execution_telemetry(self, *, task_id=None, worker_id=None, kind=None, limit=None):
        rows = deepcopy(self.snapshot.resources.get("execution_telemetry", []) or [])
        if task_id is not None: rows = [x for x in rows if x.get("task_id") == task_id]
        if worker_id is not None: rows = [x for x in rows if x.get("worker_id") == worker_id]
        if kind is not None: rows = [x for x in rows if x.get("kind") == kind]
        if limit is not None: rows = rows[-max(0, int(limit)):]
        return rows

    def telemetry_report(self):
        rows = self.execution_telemetry()
        return {
            "policy": asdict(self.telemetry_policy()),
            "records": len(rows),
            "duration_stats": ExecutionTelemetryLedger.duration_stats(rows),
            "latest": deepcopy(rows[-1]) if rows else None,
            "artifacts": [
                {"task_id": x.get("task_id"), "worker_id": x.get("worker_id"), "lease_id": x.get("lease_id"), "refs": list(x.get("artifact_refs", []) or []), "ts": x.get("ts")}
                for x in rows if x.get("artifact_refs")
            ][-100:],
        }

    def record_execution_telemetry(self, record: ExecutionTelemetryRecord, *, reason="execution telemetry recorded"):
        policy = self.telemetry_policy()
        resources = deepcopy(self.snapshot.resources)
        rows = resources.setdefault("execution_telemetry", [])
        rows.append(record.to_dict())
        if len(rows) > policy.max_records:
            del rows[:-policy.max_records]
        self.patch_snapshot({"resources": resources}, reason)
        if record.kind == TelemetryKind.COMPLETED and policy.auto_refresh_fleet_on_completion and self.fleet_control_policy().enabled:
            self.refresh_fleet_control(reason="fleet control refreshed from observed execution duration")
        return deepcopy(rows[-1])

    def _observed_duration_for(self, task):
        policy = self.telemetry_policy()
        if not policy.use_observed_durations:
            return None
        stats = ExecutionTelemetryLedger.duration_stats(self.execution_telemetry())
        task_class = (task.metadata or {}).get("task_class")
        if policy.prefer_task_class_duration and task_class:
            row = stats["by_task_class"].get(str(task_class))
            if row and row["samples"] >= policy.min_duration_samples:
                return float(row["mean_seconds"])
        row = stats["by_task"].get(task.task_id)
        if row and row["samples"] >= policy.min_duration_samples:
            return float(row["mean_seconds"])
        return None

    def _runnable_scheduled_tasks(self):
        tasks = super()._runnable_scheduled_tasks()
        for task in tasks:
            observed = self._observed_duration_for(task)
            if observed is not None and not bool((task.metadata or {}).get("lock_estimated_duration")):
                task.metadata = deepcopy(task.metadata or {})
                task.metadata["estimated_duration"] = observed
                task.metadata["duration_source"] = "observed_telemetry"
        return tasks

    def provisioning_history(self):
        return deepcopy(self.snapshot.resources.get("provisioning_history", []) or [])

    def plan_fleet_provisioning(self, provider: str, resource_id: str, *, desired_workers=None, reason="align physical fleet with admission target"):
        if desired_workers is None:
            desired_workers = self.fleet_control_report().get("admission_limit")
        if desired_workers is None:
            raise ValueError("No desired worker count is available; configure/refresh fleet control or provide desired_workers")
        desired_workers = max(0, int(desired_workers))
        workers = [x for x in self.list_workers() if x.get("resource_id") == resource_id]
        active = [x for x in workers if x.get("status") == WorkerStatus.ACTIVE.value]
        current = len(active)
        delta = desired_workers - current
        requests = []
        if delta > 0:
            requests.append(ProvisioningRequest(provider, resource_id, ProvisioningAction.PROVISION, delta, reason, metadata={"desired_workers": desired_workers, "current_workers": current}))
        elif delta < 0:
            leased = {x.get("worker_id") for x in self.list_leases() if x.get("status") == "ACTIVE"}
            idle = sorted(x.get("worker_id") for x in active if x.get("worker_id") not in leased)
            count = min(-delta, len(idle))
            if count:
                requests.append(ProvisioningRequest(provider, resource_id, ProvisioningAction.DRAIN, count, reason, target_worker_ids=idle[:count], metadata={"desired_workers": desired_workers, "current_workers": current}))
        return ProvisioningPlan(desired_workers, current, delta, requests, {"provider": provider, "resource_id": resource_id, "unfulfilled_drain": max(0, -delta - sum(x.count for x in requests if x.action == ProvisioningAction.DRAIN))}).to_dict()

    def propose_provisioning(self, request: ProvisioningRequest, *, reason="fleet provisioning proposed"):
        payload = request.to_dict()
        reversible = request.action == ProvisioningAction.PROVISION
        spec = EffectSpec(
            "fleet.provision" if request.action == ProvisioningAction.PROVISION else "fleet.drain",
            payload=payload,
            idempotency_key=f"fleet:{request.request_id}",
            retry_policy=RetryPolicy(max_attempts=1, retry_on_failure=False, retry_on_unknown=False),
            reversible=reversible,
            compensation={"action": "DRAIN", "resource_id": request.resource_id, "count": request.count} if reversible else None,
        )
        record = self.propose_effect(spec)
        resources = deepcopy(self.snapshot.resources)
        resources.setdefault("provisioning_history", []).append({"request": payload, "effect_id": record.spec.effect_id, "status": record.status, "reason": reason})
        self.patch_snapshot({"resources": resources}, reason)
        return record

    def execute_provisioning(self, effect_id: str, adapter, *, reason="authorized fleet provisioning executed"):
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.spec.effect_type not in {"fleet.provision", "fleet.drain"}:
            raise ValueError(f"Effect {effect_id} is not a fleet provisioning effect")
        request = ProvisioningRequest(**deepcopy(record.spec.payload))

        def executor(spec, idempotency_key):
            return adapter.apply(request, idempotency_key)

        result = self.execute_effect(effect_id, executor)
        if result.status == "SUCCEEDED" and request.action == ProvisioningAction.DRAIN:
            for worker_id in request.target_worker_ids:
                try:
                    self.update_worker(worker_id, {"status": WorkerStatus.DRAINING.value}, reason="provisioning adapter drained worker")
                except KeyError:
                    pass
        resources = deepcopy(self.snapshot.resources)
        resources.setdefault("provisioning_executions", []).append({
            "effect_id": effect_id,
            "request_id": request.request_id,
            "provider": request.provider,
            "action": request.action,
            "status": result.status,
            "result": deepcopy(result.result),
            "error": result.error,
        })
        self.patch_snapshot({"resources": resources}, reason)
        return result

    def provisioning_report(self):
        return {
            "history": self.provisioning_history(),
            "executions": deepcopy(self.snapshot.resources.get("provisioning_executions", []) or []),
            "pending_effects": [
                {"effect_id": x.spec.effect_id, "effect_type": x.spec.effect_type, "status": x.status, "payload": deepcopy(x.spec.payload)}
                for x in self.list_effects() if x.spec.effect_type in {"fleet.provision", "fleet.drain"} and x.status not in {"SUCCEEDED", "CANCELLED"}
            ],
        }

    def dashboard(self):
        out = super().dashboard()
        out["execution_telemetry"] = self.telemetry_report()
        out["provisioning"] = self.provisioning_report()
        return out
