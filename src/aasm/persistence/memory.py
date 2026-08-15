from __future__ import annotations

from copy import deepcopy
import threading
import time

from ..checkpoint import Checkpoint
from ..effects import EffectExecutionError, EffectRecord, EffectStatus, EffectUnknownOutcome
from ..model import Event, EventType, MachineSnapshot, MachineState, new_id


class MemoryStore:
    """Thread-safe in-memory Store implementation used by default and in tests.

    The store mirrors the durable-store claim/effect contracts closely enough
    that default in-memory runs exercise the same capacity, quota, execution
    ownership, and stale-state rules without pretending to be multi-process.
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._snapshots: dict[str, MachineSnapshot] = {}
        self._events: dict[str, list[Event]] = {}
        self._checkpoints: dict[tuple[str, str], Checkpoint] = {}
        self._effects: dict[tuple[str, str], EffectRecord] = {}
        self._task_claims: dict[tuple[str, str], dict] = {}

    @staticmethod
    def _replace_snapshot(target: MachineSnapshot, source: MachineSnapshot) -> None:
        target.__dict__.clear()
        target.__dict__.update(deepcopy(source.__dict__))

    def initialize_run(self, snapshot: MachineSnapshot) -> None:
        with self._lock:
            self._snapshots.setdefault(snapshot.machine_id, deepcopy(snapshot))
            self._events.setdefault(snapshot.machine_id, [])

    def append(self, machine_id: str, event: Event, snapshot: MachineSnapshot) -> Event:
        # Imported lazily to avoid persistence.__init__ -> MemoryStore -> reducer
        # while reducer itself is importing persistence.serde.
        from ..core.reducer import reduce_event

        with self._lock:
            if machine_id not in self._snapshots:
                raise KeyError(machine_id)
            events = self._events.setdefault(machine_id, [])
            stored = deepcopy(event)
            stored.machine_id = machine_id
            stored.sequence = len(events) + 1
            canonical = None if not events else deepcopy(self._snapshots[machine_id])
            expected_version = stored.data.get("expected_machine_version")
            if canonical is not None and expected_version is not None and canonical.version != int(expected_version):
                raise ValueError(f"Stale machine version: event expected {int(expected_version)}, canonical version is {canonical.version}")
            if (
                canonical is not None
                and stored.event_type == EventType.TRANSITION_COMMITTED.value
                and stored.from_state is not None
                and canonical.state != stored.from_state
            ):
                raise ValueError(
                    f"Stale transition: event expected {stored.from_state}, canonical state is {canonical.state}"
                )
            canonical = reduce_event(canonical, stored)
            events.append(stored)
            self._snapshots[machine_id] = deepcopy(canonical)
            self._replace_snapshot(snapshot, canonical)
            return deepcopy(stored)

    def load_snapshot(self, machine_id: str) -> MachineSnapshot:
        with self._lock:
            if machine_id not in self._snapshots:
                raise KeyError(machine_id)
            return deepcopy(self._snapshots[machine_id])

    def load_events(self, machine_id: str, after_sequence: int = 0) -> list[Event]:
        with self._lock:
            return [deepcopy(event) for event in self._events.get(machine_id, []) if event.sequence > after_sequence]

    def load_first_event(self, machine_id: str) -> Event:
        with self._lock:
            rows = self._events.get(machine_id, [])
            if not rows:
                raise KeyError(machine_id)
            return deepcopy(rows[0])

    def last_event_sequence(self, machine_id: str) -> int:
        with self._lock:
            if machine_id not in self._snapshots:
                raise KeyError(machine_id)
            rows = self._events.get(machine_id, [])
            return int(rows[-1].sequence) if rows else 0

    def list_unfinished(self) -> list[str]:
        with self._lock:
            result = []
            for machine_id, snapshot in self._snapshots.items():
                definition = snapshot.metadata.get("machine_definition", {})
                terminal = set(
                    definition.get(
                        "terminal_states",
                        [MachineState.COMPLETE.value, MachineState.FAIL.value],
                    )
                )
                if snapshot.state not in terminal:
                    result.append(machine_id)
            return sorted(result)

    def save_checkpoint(self, machine_id: str, checkpoint: Checkpoint) -> None:
        with self._lock:
            self._checkpoints[(machine_id, checkpoint.checkpoint_id)] = deepcopy(checkpoint)

    def load_checkpoint(self, machine_id: str, checkpoint_id: str) -> Checkpoint:
        with self._lock:
            try:
                return deepcopy(self._checkpoints[(machine_id, checkpoint_id)])
            except KeyError:
                raise KeyError(checkpoint_id) from None

    def save_effect(self, record: EffectRecord) -> None:
        with self._lock:
            self._effects[(record.machine_id, record.spec.effect_id)] = deepcopy(record)

    def load_effect(self, machine_id: str, effect_id: str) -> EffectRecord:
        with self._lock:
            try:
                return deepcopy(self._effects[(machine_id, effect_id)])
            except KeyError:
                raise KeyError(effect_id) from None

    def find_effect_by_idempotency(self, machine_id: str, idempotency_key: str) -> EffectRecord | None:
        with self._lock:
            for (current_machine, _), record in self._effects.items():
                if current_machine == machine_id and record.spec.idempotency_key == idempotency_key:
                    return deepcopy(record)
            return None

    def list_effects(self, machine_id: str) -> list[EffectRecord]:
        with self._lock:
            rows = [
                deepcopy(record)
                for (current_machine, _), record in self._effects.items()
                if current_machine == machine_id
            ]
            return sorted(rows, key=lambda row: (row.created_at, row.spec.effect_id))

    @staticmethod
    def _prepare_effect_attempt(record: EffectRecord) -> EffectRecord:
        if record.status == EffectStatus.SUCCEEDED.value:
            return record
        if record.status == EffectStatus.UNKNOWN.value:
            if not record.spec.retry_policy.retry_on_unknown:
                raise EffectUnknownOutcome(
                    f"Effect {record.spec.effect_id} has an unknown prior outcome; reconcile before retry"
                )
            record.status = EffectStatus.AUTHORIZED.value
        if record.status == EffectStatus.FAILED.value:
            if not record.spec.retry_policy.retry_on_failure:
                raise EffectExecutionError(
                    f"Effect {record.spec.effect_id} failed and retry_on_failure is disabled"
                )
            record.status = EffectStatus.AUTHORIZED.value
        if record.status == EffectStatus.RUNNING.value:
            raise EffectExecutionError(
                f"Effect {record.spec.effect_id} is already RUNNING on another executor"
            )
        if record.status != EffectStatus.AUTHORIZED.value:
            raise ValueError(
                f"Effect {record.spec.effect_id} is not authorized (status={record.status})"
            )
        if record.attempts >= max(1, record.spec.retry_policy.max_attempts):
            raise EffectExecutionError(
                f"Effect {record.spec.effect_id} exhausted retry attempts"
            )
        record.attempts += 1
        record.execution_id = new_id("exec")
        record.status = EffectStatus.RUNNING.value
        record.updated_at = time.time()
        return record

    def claim_effect_attempt(self, machine_id: str, effect_id: str) -> EffectRecord:
        with self._lock:
            record = self.load_effect(machine_id, effect_id)
            record = self._prepare_effect_attempt(record)
            if record.status != EffectStatus.SUCCEEDED.value:
                self._effects[(machine_id, effect_id)] = deepcopy(record)
            return deepcopy(record)

    def finish_effect_attempt(self, record: EffectRecord, execution_id: str) -> EffectRecord:
        if record.status not in {EffectStatus.SUCCEEDED.value, EffectStatus.FAILED.value}:
            raise ValueError("effect finalization requires SUCCEEDED or FAILED")
        with self._lock:
            current = self.load_effect(record.machine_id, record.spec.effect_id)
            if (
                current.status != EffectStatus.RUNNING.value
                or current.execution_id != execution_id
                or current.attempts != record.attempts
            ):
                raise EffectExecutionError(
                    f"Effect {record.spec.effect_id} lost execution ownership before durable finalization; reconcile external outcome"
                )
            current.status = record.status
            current.result = deepcopy(record.result)
            current.error = record.error
            current.evidence = deepcopy(record.evidence)
            current.updated_at = record.updated_at
            self._effects[(current.machine_id, current.spec.effect_id)] = deepcopy(current)
            return deepcopy(current)

    def mark_running_effects_unknown(self, machine_id: str) -> list[EffectRecord]:
        with self._lock:
            changed = []
            for record in self.list_effects(machine_id):
                if record.status == EffectStatus.RUNNING.value:
                    record.status = EffectStatus.UNKNOWN.value
                    record.error = "process ended while effect outcome was unresolved"
                    record.updated_at = time.time()
                    self._effects[(machine_id, record.spec.effect_id)] = deepcopy(record)
                    changed.append(deepcopy(record))
            return changed

    @staticmethod
    def _canonical_claim_policy(
        snapshot: MachineSnapshot,
        worker_id: str,
        requested_resource_id: str | None,
        at_time: float,
    ) -> tuple[str, float, list[dict]]:
        resources = snapshot.resources or {}
        worker = next(
            (row for row in resources.get("workers", []) if row.get("worker_id") == worker_id),
            None,
        )
        if worker is None:
            raise KeyError(worker_id)
        if worker.get("status") != "ACTIVE":
            raise ValueError(f"Worker {worker_id} is not ACTIVE")
        if at_time > float(worker.get("last_heartbeat", 0) or 0) + float(
            worker.get("heartbeat_timeout", 60) or 60
        ):
            raise ValueError(f"Worker {worker_id} is stale")
        resource_id = worker.get("resource_id")
        if requested_resource_id is not None and requested_resource_id != resource_id:
            raise ValueError(
                f"Stale worker resource mapping: requested {requested_resource_id}, canonical is {resource_id}"
            )
        resource = next(
            (row for row in resources.get("registry", []) if row.get("resource_id") == resource_id),
            None,
        )
        if resource is None:
            raise KeyError(resource_id)
        if not resource.get("enabled", True):
            raise ValueError(f"Resource {resource_id} is disabled")
        return (
            str(resource_id),
            float(resource.get("capacity", 0) or 0),
            deepcopy(resources.get("quotas", [])),
        )

    @staticmethod
    def _check_claim_limits(
        active: list[dict],
        *,
        worker_id: str,
        resource_id: str,
        demand: float,
        resource_capacity: float,
        quotas: list[dict],
    ) -> None:
        used = sum(
            float(row.get("demand", 0) or 0)
            for row in active
            if row.get("resource_id") == resource_id
        )
        if used + demand > resource_capacity + 1e-12:
            raise ValueError(f"Resource capacity exhausted: {resource_id}")
        for raw in quotas or []:
            if not raw.get("enabled", True):
                continue
            scope = raw.get("scope", "machine")
            target = raw.get("target_id")
            relevant = (
                scope == "machine"
                or (scope == "worker" and target == worker_id)
                or (scope == "resource" and target == resource_id)
            )
            if not relevant:
                continue
            selected = [
                row
                for row in active
                if scope == "machine"
                or (scope == "worker" and row.get("worker_id") == worker_id)
                or (scope == "resource" and row.get("resource_id") == resource_id)
            ]
            maximum_leases = raw.get("max_active_leases")
            if maximum_leases is not None and len(selected) >= int(maximum_leases):
                raise ValueError(f"Quota exceeded: {raw.get('quota_id')}")
            maximum_units = raw.get("max_capacity_units")
            if maximum_units is not None and (
                sum(float(row.get("demand", 0) or 0) for row in selected) + demand
                > float(maximum_units) + 1e-12
            ):
                raise ValueError(f"Quota exceeded: {raw.get('quota_id')}")

    def acquire_task_claim(
        self,
        machine_id: str,
        task_id: str,
        lease_id: str,
        worker_id: str,
        expires_at: float,
        at_time: float,
        *,
        resource_id: str | None = None,
        demand: float = 0.0,
        resource_capacity: float | None = None,
        quotas: list[dict] | None = None,
    ) -> bool:
        del resource_capacity, quotas
        with self._lock:
            snapshot = self.load_snapshot(machine_id)
            canonical_resource, canonical_capacity, canonical_quotas = self._canonical_claim_policy(
                snapshot,
                worker_id,
                resource_id,
                float(at_time),
            )
            for key, claim in list(self._task_claims.items()):
                if key[0] == machine_id and float(claim.get("expires_at", 0)) <= float(at_time):
                    del self._task_claims[key]
            current = self._task_claims.get((machine_id, task_id))
            if current and float(current["expires_at"]) > float(at_time):
                return False
            active = [
                deepcopy(claim)
                for (current_machine, _), claim in self._task_claims.items()
                if current_machine == machine_id and float(claim.get("expires_at", 0)) > float(at_time)
            ]
            self._check_claim_limits(
                active,
                worker_id=worker_id,
                resource_id=canonical_resource,
                demand=float(demand),
                resource_capacity=canonical_capacity,
                quotas=canonical_quotas,
            )
            self._task_claims[(machine_id, task_id)] = {
                "lease_id": lease_id,
                "worker_id": worker_id,
                "resource_id": canonical_resource,
                "demand": float(demand),
                "expires_at": float(expires_at),
            }
            return True

    def renew_task_claim(self, machine_id: str, lease_id: str, expires_at: float) -> bool:
        with self._lock:
            for key, claim in self._task_claims.items():
                if key[0] == machine_id and claim["lease_id"] == lease_id:
                    claim["expires_at"] = float(expires_at)
                    return True
            return False

    def release_task_claim(self, machine_id: str, lease_id: str) -> None:
        with self._lock:
            for key, claim in list(self._task_claims.items()):
                if key[0] == machine_id and claim["lease_id"] == lease_id:
                    del self._task_claims[key]

    def close(self) -> None:
        return None
