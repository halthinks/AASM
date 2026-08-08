from __future__ import annotations
import threading
from collections.abc import Callable
from typing import Any
from .remote import AASMRemoteClient
from .workers import WorkerRecord


class RemoteWorkerLoop:
    """Long-running remote worker that pulls tasks from an AASM control plane."""
    def __init__(self,client:AASMRemoteClient,machine_id:str,worker:WorkerRecord,executor:Callable[[dict],dict[str,Any]|None],*,lease_seconds:float=120.0,heartbeat_interval:float=20.0,idle_sleep:float=2.0):
        if lease_seconds<=0 or heartbeat_interval<=0 or idle_sleep<=0: raise ValueError("timings must be positive")
        self.client=client; self.machine_id=machine_id; self.worker=worker; self.executor=executor
        self.lease_seconds=float(lease_seconds); self.heartbeat_interval=float(heartbeat_interval); self.idle_sleep=float(idle_sleep); self._registered=False

    def ensure_registered(self):
        if not self._registered:
            self.client.register_worker(self.machine_id,self.worker); self._registered=True

    def _keepalive(self,lease_id:str,stop:threading.Event):
        while not stop.wait(self.heartbeat_interval):
            self.client.heartbeat(self.machine_id,self.worker.worker_id)
            self.client.lease_heartbeat(self.machine_id,lease_id,extend_seconds=self.lease_seconds)

    def run_once(self)->bool:
        self.ensure_registered(); self.client.heartbeat(self.machine_id,self.worker.worker_id)
        lease=self.client.claim_next(self.machine_id,self.worker.worker_id,self.lease_seconds)
        if not lease or (lease.get("lease") is None and "lease" in lease): return False
        if "lease" in lease: lease=lease["lease"]
        stop=threading.Event(); keeper=threading.Thread(target=self._keepalive,args=(lease["lease_id"],stop),daemon=True); keeper.start()
        try:
            result=self.executor(lease) or {}; self.client.complete(self.machine_id,lease["lease_id"],result); return True
        except Exception as exc:
            self.client.fail(self.machine_id,lease["lease_id"],f"{type(exc).__name__}: {exc}"); return True
        finally:
            stop.set(); keeper.join(timeout=max(1.0,self.heartbeat_interval))

    def run_forever(self,stop:threading.Event|None=None):
        stop=stop or threading.Event()
        while not stop.is_set():
            if not self.run_once(): stop.wait(self.idle_sleep)
