from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .effects import EffectSpec, EffectStatus, RetryPolicy
from .execution_telemetry import ExecutionTelemetryRecord
from .mission_control import (
    ForkRequest,
    MissionControlAction,
    MissionControlRecord,
    MissionPauseMode,
    MissionStatus,
)
from .model import new_id, now
from .pagination import page_records
from .provisioning import ProvisioningAction, ProvisioningRequest
from .runtime_v18 import AASMEngine as V18Engine
from .workers import WorkerStatus


class AASMEngine(V18Engine):
    """v0.19 runtime: mission controls, controlled forks, and cursor paging."""

    def _refresh_canonical_snapshot(self):
        self.snapshot = self.store.load_snapshot(self.snapshot.machine_id)
        self._refresh_runtime_views()
        return self.snapshot

    def current_sequence(self) -> int:
        loader = getattr(self.store, "last_event_sequence", None)
        if loader is not None:
            value = loader(self.snapshot.machine_id)
            if value is not None:
                return int(value)
        if self.events:
            return int(self.events[-1].sequence)
        rows = self.store.load_events(self.snapshot.machine_id)
        if not rows:
            raise KeyError(self.snapshot.machine_id)
        return int(rows[-1].sequence)

    def mission_control_report(self):
        raw = deepcopy(self.snapshot.resources.get("mission_control", {}) or {})
        raw.setdefault("status", MissionStatus.RUNNING)
        raw.setdefault("mode", None)
        raw.setdefault("actor", None)
        raw.setdefault("reason", None)
        raw.setdefault("updated_at", None)
        raw.setdefault("released_lease_ids", [])
        raw.setdefault("history", [])
        return raw

    def _canonical_mission_paused(self) -> bool:
        snapshot = self.store.load_snapshot(self.snapshot.machine_id)
        control = snapshot.resources.get("mission_control", {}) or {}
        return control.get("status", MissionStatus.RUNNING) == MissionStatus.PAUSED

    def pause_mission(self, record: MissionControlRecord, *, reason="mission paused"):
        self._refresh_canonical_snapshot()
        if record.action != MissionControlAction.PAUSE:
            raise ValueError("pause_mission requires a PAUSE record")
        current = self.mission_control_report()
        if current["status"] == MissionStatus.PAUSED:
            return current

        resources = deepcopy(self.snapshot.resources)
        control = resources.setdefault("mission_control", {})
        entry = record.to_dict()
        entry["released_lease_ids"] = []
        control.update({
            "status": MissionStatus.PAUSED,
            "mode": record.mode,
            "actor": record.actor,
            "reason": record.reason,
            "updated_at": record.ts,
            "released_lease_ids": [],
        })
        history = control.setdefault("history", [])
        history.append(entry)
        if len(history) > 1000:
            del history[:-1000]
        self.patch_snapshot({"resources": resources}, reason)

        released: list[str] = []
        if record.mode == MissionPauseMode.SUSPEND:
            # The pause is authoritative before ownership is released. New
            # claims are rejected by the canonical pre/post claim checks below.
            for lease in list(self.snapshot.resources.get("leases", []) or []):
                if lease.get("status") == "ACTIVE":
                    self.release_lease(lease["lease_id"])
                    released.append(lease["lease_id"])
            if released:
                resources = deepcopy(self.snapshot.resources)
                control = resources.setdefault("mission_control", {})
                control["released_lease_ids"] = list(released)
                if control.get("history"):
                    control["history"][-1]["released_lease_ids"] = list(released)
                self.patch_snapshot({"resources": resources}, "active leases released by mission suspension")
        return self.mission_control_report()

    def resume_mission(self, record: MissionControlRecord, *, reason="mission resumed"):
        self._refresh_canonical_snapshot()
        if record.action != MissionControlAction.RESUME:
            raise ValueError("resume_mission requires a RESUME record")
        resources = deepcopy(self.snapshot.resources)
        control = resources.setdefault("mission_control", {})
        entry = record.to_dict()
        entry["released_lease_ids"] = []
        control.update({
            "status": MissionStatus.RUNNING,
            "mode": None,
            "actor": record.actor,
            "reason": record.reason,
            "updated_at": record.ts,
            "released_lease_ids": [],
        })
        history = control.setdefault("history", [])
        history.append(entry)
        if len(history) > 1000:
            del history[:-1000]
        self.patch_snapshot({"resources": resources}, reason)
        return self.mission_control_report()

    def claim_task(self, task, worker_id, **kwargs):
        if self._canonical_mission_paused():
            raise ValueError("Mission is PAUSED; task claims are disabled")
        lease = super().claim_task(task, worker_id, **kwargs)
        if self._canonical_mission_paused():
            self.release_lease(lease["lease_id"])
            raise ValueError("Mission became PAUSED during claim")
        return lease

    def claim_next_task(self, worker_id: str, *, lease_seconds: float = 60.0):
        if self._canonical_mission_paused():
            return None
        return super().claim_next_task(worker_id, lease_seconds=lease_seconds)

    def effect_queue_report(self):
        rows = [asdict(record) for record in self.list_effects()]
        by_status = {
            status: [row for row in rows if row.get("status") == status]
            for status in [
                EffectStatus.PROPOSED.value,
                EffectStatus.AUTHORIZED.value,
                EffectStatus.RUNNING.value,
                EffectStatus.UNKNOWN.value,
                EffectStatus.FAILED.value,
                EffectStatus.SUCCEEDED.value,
                EffectStatus.CANCELLED.value,
            ]
        }
        approvals = deepcopy(self.snapshot.resources.get("effect_approvals", []) or [])
        actionable = (
            by_status[EffectStatus.PROPOSED.value]
            + by_status[EffectStatus.AUTHORIZED.value]
            + by_status[EffectStatus.UNKNOWN.value]
            + by_status[EffectStatus.FAILED.value]
        )
        return {
            # Backward-compatible union used by older clients. Consumers should
            # inspect status before offering an action.
            "pending": actionable,
            "pending_approval": by_status[EffectStatus.PROPOSED.value],
            "authorized": by_status[EffectStatus.AUTHORIZED.value],
            "running": by_status[EffectStatus.RUNNING.value],
            "requires_reconciliation": by_status[EffectStatus.UNKNOWN.value],
            "failed": by_status[EffectStatus.FAILED.value],
            "all": rows[-500:],
            "approvals": approvals[-500:],
        }

    def authorize_pending_effect(self, effect_id: str, actor: str, reason: str):
        self._refresh_canonical_snapshot()
        if not str(actor).strip() or not str(reason).strip():
            raise ValueError("actor and reason are required")
        before = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if before.status == EffectStatus.PROPOSED.value:
            record = self.authorize_effect(effect_id, authority=actor)
        elif before.status == EffectStatus.FAILED.value:
            if not before.spec.retry_policy.retry_on_failure:
                raise ValueError(
                    f"Effect {effect_id} failed and retry_on_failure is disabled; reconcile or create a new effect"
                )
            record = self.authorize_effect(effect_id, authority=actor)
        elif before.status in {EffectStatus.AUTHORIZED.value, EffectStatus.SUCCEEDED.value}:
            record = before
        elif before.status == EffectStatus.UNKNOWN.value:
            raise ValueError(
                f"Effect {effect_id} has an UNKNOWN external outcome; reconcile it before any retry"
            )
        else:
            raise ValueError(f"Effect {effect_id} cannot be authorized from status {before.status}")
        resources = deepcopy(self.snapshot.resources)
        approvals = resources.setdefault("effect_approvals", [])
        if not any(
            row.get("effect_id") == effect_id
            and row.get("authorization_id") == record.authorization_id
            for row in approvals
        ):
            approvals.append({
                "approval_id": new_id("approval"),
                "effect_id": effect_id,
                "effect_type": record.spec.effect_type,
                "authorization_id": record.authorization_id,
                "actor": actor,
                "reason": reason,
                "ts": now(),
                "status": record.status,
            })
            if len(approvals) > 5000:
                del approvals[:-5000]
            self.patch_snapshot({"resources": resources}, "pending effect explicitly approved")
        return asdict(record)

    @staticmethod
    def _confirmed_drained_worker_ids(result_payload):
        payload = result_payload or {}
        explicit = payload.get("drained_worker_ids")
        if isinstance(explicit, list) and all(isinstance(value, str) for value in explicit):
            return sorted(set(explicit))
        legacy = payload.get("drained")
        if isinstance(legacy, list) and all(isinstance(value, str) for value in legacy):
            return sorted(set(legacy))
        return []

    def execute_provisioning(
        self,
        effect_id: str,
        adapter,
        *,
        reason="authorized fleet provisioning executed",
    ):
        self._refresh_canonical_snapshot()
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.spec.effect_type not in {"fleet.provision", "fleet.drain"}:
            raise ValueError(f"Effect {effect_id} is not a fleet provisioning effect")
        request = ProvisioningRequest(**deepcopy(record.spec.payload))

        def executor(spec, idempotency_key):
            return adapter.apply(request, idempotency_key)

        result = self.execute_effect(effect_id, executor)
        confirmed_drained = []
        unconfirmed_targets = []
        if result.status == EffectStatus.SUCCEEDED.value and request.action == ProvisioningAction.DRAIN:
            confirmed_drained = self._confirmed_drained_worker_ids(result.result)
            unconfirmed_targets = sorted(set(request.target_worker_ids) - set(confirmed_drained))
            for worker_id in confirmed_drained:
                current = next(
                    (row for row in self.list_workers() if row.get("worker_id") == worker_id),
                    None,
                )
                if current and current.get("status") != WorkerStatus.DRAINING.value:
                    self.update_worker(
                        worker_id,
                        {"status": WorkerStatus.DRAINING.value},
                        reason="provisioning adapter confirmed targeted worker drain",
                    )

        resources = deepcopy(self.snapshot.resources)
        executions = resources.setdefault("provisioning_executions", [])
        if not any(row.get("effect_id") == effect_id for row in executions):
            executions.append({
                "effect_id": effect_id,
                "request_id": request.request_id,
                "provider": request.provider,
                "action": request.action,
                "status": result.status,
                "result": deepcopy(result.result),
                "error": result.error,
                "confirmed_drained_worker_ids": confirmed_drained,
                "unconfirmed_logical_targets": unconfirmed_targets,
                "drain_scope": (result.result or {}).get("drain_scope") if isinstance(result.result, dict) else None,
            })
            if len(executions) > 2000:
                del executions[:-2000]
            self.patch_snapshot({"resources": resources}, reason)
        return result

    def propose_fork(self, request: ForkRequest, *, reason="controlled fork proposed"):
        self._refresh_canonical_snapshot()
        current = self.current_sequence()
        if request.source_sequence > current:
            raise ValueError(f"fork sequence {request.source_sequence} exceeds current sequence {current}")
        # Validate the boundary before creating an approval item.
        self.replay(at_sequence=request.source_sequence)
        spec = EffectSpec(
            "machine.fork",
            payload=request.to_dict(),
            idempotency_key=f"fork:{self.snapshot.machine_id}:{request.source_sequence}:{request.target_machine_id}",
            retry_policy=RetryPolicy(max_attempts=1, retry_on_failure=False, retry_on_unknown=False),
            reversible=False,
        )
        record = self.propose_effect(spec)
        resources = deepcopy(self.snapshot.resources)
        history = resources.setdefault("fork_history", [])
        if not any(x.get("effect_id") == record.spec.effect_id for x in history):
            history.append({
                "request": request.to_dict(),
                "effect_id": record.spec.effect_id,
                "status": record.status,
                "reason": reason,
            })
            if len(history) > 1000:
                del history[:-1000]
            self.patch_snapshot({"resources": resources}, reason)
        return record

    def propose_current_fork(self, actor: str, reason: str, *, source_sequence=None, target_machine_id=None, metadata=None):
        return self.propose_fork(ForkRequest(
            source_sequence=self.current_sequence() if source_sequence is None else int(source_sequence),
            actor=actor,
            reason=reason,
            target_machine_id=target_machine_id or new_id("machine"),
            metadata=deepcopy(metadata or {}),
        ))

    def execute_fork(self, effect_id: str, *, reason="authorized controlled fork executed"):
        self._refresh_canonical_snapshot()
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.spec.effect_type != "machine.fork":
            raise ValueError(f"Effect {effect_id} is not a machine.fork effect")
        request = ForkRequest(**deepcopy(record.spec.payload))

        def executor(spec, idempotency_key):
            try:
                existing = self.store.load_snapshot(request.target_machine_id)
            except KeyError:
                forked = self.fork(
                    request.source_sequence,
                    store=self.store,
                    machine_id=request.target_machine_id,
                )
                return {
                    "target_machine_id": forked.snapshot.machine_id,
                    "source_machine_id": self.snapshot.machine_id,
                    "source_sequence": request.source_sequence,
                    "existing": False,
                    "idempotency_key": idempotency_key,
                }
            lineage = (existing.metadata or {}).get("lineage", {})
            if lineage.get("source_machine_id") != self.snapshot.machine_id or int(lineage.get("source_sequence", -1)) != request.source_sequence:
                raise ValueError("target machine ID already belongs to a different fork lineage")
            return {
                "target_machine_id": existing.machine_id,
                "source_machine_id": self.snapshot.machine_id,
                "source_sequence": request.source_sequence,
                "existing": True,
                "idempotency_key": idempotency_key,
            }

        result = self.execute_effect(effect_id, executor)
        resources = deepcopy(self.snapshot.resources)
        executions = resources.setdefault("fork_executions", [])
        if not any(x.get("effect_id") == effect_id and x.get("status") == result.status for x in executions):
            executions.append({
                "effect_id": effect_id,
                "request_id": request.request_id,
                "target_machine_id": request.target_machine_id,
                "source_sequence": request.source_sequence,
                "status": result.status,
                "result": deepcopy(result.result),
                "error": result.error,
            })
            if len(executions) > 1000:
                del executions[:-1000]
            self.patch_snapshot({"resources": resources}, reason)
        return result

    def fork_report(self):
        effects = {record.spec.effect_id: record for record in self.list_effects()}
        history = deepcopy(self.snapshot.resources.get("fork_history", []) or [])
        for row in history:
            current = effects.get(row.get("effect_id"))
            if current is not None:
                row["status"] = current.status
        return {
            "history": history,
            "executions": deepcopy(self.snapshot.resources.get("fork_executions", []) or []),
            "pending": [
                row for row in self.effect_queue_report()["pending"]
                if (row.get("spec") or {}).get("effect_type") == "machine.fork"
            ],
        }

    def record_execution_telemetry(self, record: ExecutionTelemetryRecord, **kwargs):
        return super().record_execution_telemetry(record, **kwargs)

    def telemetry_page(self, *, cursor=None, limit=100, task_id=None, worker_id=None, kind=None):
        rows = self.execution_telemetry(task_id=task_id, worker_id=worker_id, kind=kind)
        return page_records(rows, cursor=cursor, limit=limit, id_field="record_id")

    def store_text_artifact(self, *args, **kwargs):
        self._refresh_canonical_snapshot()
        entry = super().store_text_artifact(*args, **kwargs)
        if entry.get("artifact_id"):
            return entry
        resources = deepcopy(self.snapshot.resources)
        rows = resources.setdefault("external_artifacts", [])
        target = next((row for row in reversed(rows) if row.get("ref") == entry.get("ref") and row.get("name") == entry.get("name")), None)
        if target is None:
            return entry
        target["artifact_id"] = new_id("artifact")
        self.patch_snapshot({"resources": resources}, "external artifact assigned stable cursor identity")
        return deepcopy(target)

    def artifact_page(self, *, cursor=None, limit=100, task_id=None, worker_id=None):
        rows = self.external_artifacts(task_id=task_id, worker_id=worker_id, limit=1000)
        return page_records(rows, cursor=cursor, limit=limit, id_field="artifact_id")

    def dashboard(self):
        out = super().dashboard()
        out["event_sequence"] = self.current_sequence()
        out["mission_control"] = self.mission_control_report()
        out["effect_queue"] = self.effect_queue_report()
        out["forks"] = self.fork_report()
        out["telemetry_page"] = self.telemetry_page(limit=50)
        out["artifact_page"] = self.artifact_page(limit=50)
        return out
