from __future__ import annotations

from copy import deepcopy

from .artifact_backends import ArtifactBackend
from .execution_controls import WorkerControlAction, WorkerControlRecord
from .execution_telemetry import ExecutionTelemetryRecord, TelemetryKind
from .runtime_v17 import AASMEngine as V17Engine
from .workers import WorkerStatus


class AASMEngine(V17Engine):
    """v0.18 runtime: external artifact refs and durable execution controls."""

    def worker_control_history(self):
        return deepcopy(self.snapshot.resources.get("worker_control_history", []) or [])

    def control_worker(self, record: WorkerControlRecord, *, reason="worker execution control applied"):
        current = next((x for x in self.list_workers() if x.get("worker_id") == record.worker_id), None)
        if current is None:
            raise KeyError(record.worker_id)
        if record.action == WorkerControlAction.DRAIN:
            target = WorkerStatus.DRAINING.value
        elif record.action == WorkerControlAction.RESUME:
            target = WorkerStatus.ACTIVE.value
        elif record.action == WorkerControlAction.OFFLINE:
            target = WorkerStatus.OFFLINE.value
        else:
            raise ValueError(record.action)
        updated = self.update_worker(record.worker_id, {"status": target}, reason=reason)
        released=[]
        if record.action == WorkerControlAction.OFFLINE:
            for lease in list(self.list_leases()):
                if lease.get("worker_id") == record.worker_id and lease.get("status") == "ACTIVE":
                    self.release_lease(lease["lease_id"])
                    released.append(lease["lease_id"])
        resources = deepcopy(self.snapshot.resources)
        raw = record.to_dict()
        raw["previous_status"] = current.get("status")
        raw["new_status"] = target
        raw["released_lease_ids"] = released
        resources.setdefault("worker_control_history", []).append(raw)
        resources["last_worker_control"] = raw
        self.patch_snapshot({"resources": resources}, reason)
        return {"worker": deepcopy(updated), "control": deepcopy(raw)}

    def execution_control_report(self):
        history = self.worker_control_history()
        return {
            "last": deepcopy(history[-1]) if history else None,
            "history": history[-200:],
            "workers": self.list_workers(),
        }

    def store_text_artifact(
        self,
        backend: ArtifactBackend,
        *,
        backend_name: str,
        namespace: str,
        name: str,
        text: str,
        worker_id: str | None = None,
        task_id: str | None = None,
        lease_id: str | None = None,
        telemetry_kind: str = TelemetryKind.ARTIFACT,
        metadata: dict | None = None,
        reason="external artifact stored",
    ):
        ref = backend.put_text(namespace, name, text)
        resources = deepcopy(self.snapshot.resources)
        entry = {
            "backend": backend_name,
            "namespace": namespace,
            "name": name,
            "ref": ref,
            "worker_id": worker_id,
            "task_id": task_id,
            "lease_id": lease_id,
            "metadata": deepcopy(metadata or {}),
        }
        resources.setdefault("external_artifacts", []).append(entry)
        if len(resources["external_artifacts"]) > 1000:
            del resources["external_artifacts"][:-1000]
        self.patch_snapshot({"resources": resources}, reason)
        if worker_id and task_id and lease_id:
            self.record_execution_telemetry(
                ExecutionTelemetryRecord(
                    worker_id,
                    task_id,
                    lease_id,
                    telemetry_kind,
                    artifact_refs=[ref],
                    metadata={"artifact_backend": backend_name, **deepcopy(metadata or {})},
                ),
                reason="external artifact telemetry recorded",
            )
        return deepcopy(entry)

    def external_artifacts(self, *, task_id=None, worker_id=None, limit=200):
        rows = deepcopy(self.snapshot.resources.get("external_artifacts", []) or [])
        if task_id is not None:
            rows = [x for x in rows if x.get("task_id") == task_id]
        if worker_id is not None:
            rows = [x for x in rows if x.get("worker_id") == worker_id]
        return rows[-max(0, int(limit)):]

    def dashboard(self):
        out = super().dashboard()
        telemetry = dict(out.get("execution_telemetry") or {})
        telemetry["recent"] = self.execution_telemetry(limit=20)
        out["execution_telemetry"] = telemetry
        out["execution_controls"] = self.execution_control_report()
        out["external_artifacts"] = self.external_artifacts(limit=100)
        return out
