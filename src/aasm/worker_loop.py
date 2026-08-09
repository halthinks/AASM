from __future__ import annotations

from collections.abc import Callable
import threading
import time
from typing import Any

from .remote import AASMRemoteClient
from .workers import WorkerRecord


class RemoteWorkerLoop:
    """Long-running remote worker that pulls tasks from an AASM control plane."""

    def __init__(
        self,
        client: AASMRemoteClient,
        machine_id: str,
        worker: WorkerRecord,
        executor: Callable[[dict], dict[str, Any] | None],
        *,
        lease_seconds: float = 120.0,
        heartbeat_interval: float = 20.0,
        idle_sleep: float = 2.0,
    ):
        if lease_seconds <= 0 or heartbeat_interval <= 0 or idle_sleep <= 0:
            raise ValueError("timings must be positive")
        self.client = client
        self.machine_id = machine_id
        self.worker = worker
        self.executor = executor
        self.lease_seconds = float(lease_seconds)
        self.heartbeat_interval = float(heartbeat_interval)
        self.idle_sleep = float(idle_sleep)
        self._registered = False

    def ensure_registered(self):
        if self._registered:
            return
        state = self.client.state(self.machine_id)
        existing = next(
            (row for row in state.get("workers", []) if row.get("worker_id") == self.worker.worker_id),
            None,
        )
        if existing is None:
            self.client.register_worker(self.machine_id, self.worker)
        elif existing.get("resource_id") != self.worker.resource_id:
            raise ValueError(
                f"Worker {self.worker.worker_id} already exists on resource {existing.get('resource_id')}, "
                f"expected {self.worker.resource_id}"
            )
        self.client.heartbeat(self.machine_id, self.worker.worker_id)
        self._registered = True

    def _keepalive(self, lease_id: str, stop: threading.Event, lost: threading.Event):
        while not stop.wait(self.heartbeat_interval):
            try:
                self.client.heartbeat(self.machine_id, self.worker.worker_id)
                self.client.lease_heartbeat(
                    self.machine_id,
                    lease_id,
                    extend_seconds=self.lease_seconds,
                )
            except Exception:
                # The authoritative lease may have been released, expired, or
                # revoked by mission/worker control. The executor cannot be
                # force-cancelled generically, but its eventual result must not
                # be reported as a successful durable completion.
                lost.set()
                return

    def _telemetry(self, lease, kind, **extra):
        sender = getattr(self.client, "telemetry", None)
        if sender is None:
            return None
        metadata = {"task_class": (lease.get("metadata") or {}).get("task_class")}
        metadata.update(dict(extra.pop("metadata", {}) or {}))
        record = {
            "worker_id": self.worker.worker_id,
            "task_id": lease["task_id"],
            "lease_id": lease["lease_id"],
            "kind": kind,
            "metadata": metadata,
        }
        record.update(extra)
        try:
            return sender(self.machine_id, record)
        except Exception:
            return None

    @staticmethod
    def _status(value) -> str | None:
        return value.get("status") if isinstance(value, dict) else getattr(value, "status", None)

    def run_once(self) -> bool:
        self.ensure_registered()
        self.client.heartbeat(self.machine_id, self.worker.worker_id)
        lease = self.client.claim_next(
            self.machine_id,
            self.worker.worker_id,
            self.lease_seconds,
        )
        if not lease or (lease.get("lease") is None and "lease" in lease):
            return False
        if "lease" in lease:
            lease = lease["lease"]

        stop = threading.Event()
        lost = threading.Event()
        keeper = threading.Thread(
            target=self._keepalive,
            args=(lease["lease_id"], stop, lost),
            daemon=True,
        )
        keeper.start()
        started = time.monotonic()
        self._telemetry(lease, "STARTED")
        try:
            result = self.executor(lease) or {}
            duration = time.monotonic() - started
            artifacts = list(result.get("artifact_refs", []) or []) if isinstance(result, dict) else []
            completion = self.client.complete(
                self.machine_id,
                lease["lease_id"],
                result,
            )
            status = self._status(completion)
            if lost.is_set() or status != "COMPLETED":
                self._telemetry(
                    lease,
                    "LEASE_LOST",
                    duration_seconds=duration,
                    artifact_refs=artifacts,
                    message=f"executor returned after durable lease ownership was lost (status={status or 'unknown'})",
                    metrics={"wall_seconds": duration},
                    metadata={"final_lease_status": status},
                )
            else:
                self._telemetry(
                    lease,
                    "COMPLETED",
                    duration_seconds=duration,
                    artifact_refs=artifacts,
                    metrics={"wall_seconds": duration},
                )
            return True
        except Exception as exc:
            duration = time.monotonic() - started
            final = None
            try:
                final = self.client.fail(
                    self.machine_id,
                    lease["lease_id"],
                    f"{type(exc).__name__}: {exc}",
                )
            except Exception:
                lost.set()
            status = self._status(final)
            if lost.is_set() or (status is not None and status != "FAILED"):
                kind = "LEASE_LOST"
                message = (
                    f"executor failed after durable lease ownership was lost "
                    f"(lease_status={status or 'unknown'}): {type(exc).__name__}: {exc}"
                )
            else:
                kind = "FAILED"
                message = f"{type(exc).__name__}: {exc}"
            self._telemetry(
                lease,
                kind,
                duration_seconds=duration,
                message=message,
                metrics={"wall_seconds": duration},
                metadata={"final_lease_status": status},
            )
            return True
        finally:
            stop.set()
            keeper.join(timeout=max(1.0, self.heartbeat_interval))

    def run_forever(self, stop: threading.Event | None = None):
        stop = stop or threading.Event()
        while not stop.is_set():
            if not self.run_once():
                stop.wait(self.idle_sleep)
