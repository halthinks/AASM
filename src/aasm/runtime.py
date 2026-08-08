from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .engine import AASMEngine as CoreAASMEngine
from .model import Event, EventType, new_id, now
from .resources import ResourceRecord, TaskDemand
from .workers import WorkerRecord, WorkerStatus, TaskLease, LeaseStatus, QuotaPolicy
from .scheduler import CapabilityScheduler


class AASMEngine(CoreAASMEngine):
    """Public AASM runtime with durable capability/resource scheduling."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduler = CapabilityScheduler(self.flow)

    @classmethod
    def _hydrate(cls, snapshot, events, store, authority=None, definition=None):
        self = super()._hydrate(snapshot, events, store, authority=authority, definition=definition)
        self.scheduler = CapabilityScheduler(self.flow)
        return self

    def register_resource(self, record: ResourceRecord, *, reason: str = "resource registered"):
        event = Event(new_id("evt"), now(), EventType.RESOURCE_REGISTERED.value, self.state_value, self.state_value, reason,
                      data={"resource": asdict(record)}, machine_id=self.snapshot.machine_id)
        self._commit(event)
        return deepcopy(next(x for x in self.snapshot.resources.get("registry", []) if x["resource_id"] == record.resource_id))

    def update_resource(self, resource_id: str, patch: dict, *, reason: str = "resource updated"):
        allowed = {"kind", "capabilities", "capacity", "cost_per_unit", "reliability", "enabled", "metadata"}
        unknown = set(patch) - allowed
        if unknown:
            raise ValueError(f"Unknown resource fields: {sorted(unknown)}")
        current = next((x for x in self.snapshot.resources.get("registry", []) if x["resource_id"] == resource_id), None)
        if current is None:
            raise KeyError(resource_id)
        candidate = deepcopy(current)
        candidate.update(deepcopy(patch))
        ResourceRecord(**candidate)
        event = Event(new_id("evt"), now(), EventType.RESOURCE_UPDATED.value, self.state_value, self.state_value, reason,
                      data={"resource_id": resource_id, "patch": deepcopy(patch)}, machine_id=self.snapshot.machine_id)
        self._commit(event)
        return deepcopy(next(x for x in self.snapshot.resources.get("registry", []) if x["resource_id"] == resource_id))

    def list_resources(self):
        return deepcopy(self.snapshot.resources.get("registry", []))

    def schedule(self, tasks: list[TaskDemand], *, reason: str = "resource schedule computed"):
        resources = [ResourceRecord(**deepcopy(raw)) for raw in self.snapshot.resources.get("registry", [])]
        result = self.scheduler.schedule(resources, tasks)
        event = Event(
            new_id("evt"), now(), EventType.SCHEDULE_COMPUTED.value,
            self.state_value, self.state_value, reason,
            data={
                "tasks": [asdict(x) for x in tasks],
                "assignments": [asdict(x) for x in result.assignments],
                "result": result.to_dict(),
            },
            machine_id=self.snapshot.machine_id,
        )
        self._commit(event)
        by_task: dict[str, list[str]] = {}
        for assignment in result.assignments:
            by_task.setdefault(assignment.task_id, []).append(assignment.resource_id)
        for task_id, owners in by_task.items():
            if task_id in self.graph.nodes:
                owner = owners[0] if len(owners) == 1 else ",".join(sorted(owners))
                self.plan_update_node(task_id, {"owner": owner}, reason="scheduler assigned plan node")
        return result

    def last_schedule(self):
        return deepcopy(self.snapshot.resources.get("last_schedule"))

    def register_worker(self, record: WorkerRecord, *, reason: str = "worker registered"):
        if not any(r["resource_id"] == record.resource_id for r in self.list_resources()):
            raise KeyError(f"Unknown resource for worker: {record.resource_id}")
        self._commit(Event(
            new_id("evt"), now(), EventType.WORKER_REGISTERED.value,
            self.state_value, self.state_value, reason,
            data={"worker": asdict(record)}, machine_id=self.snapshot.machine_id,
        ))
        return deepcopy(next(x for x in self.snapshot.resources.get("workers", []) if x["worker_id"] == record.worker_id))

    def list_workers(self):
        return deepcopy(self.snapshot.resources.get("workers", []))

    def update_worker(self, worker_id: str, patch: dict, *, reason: str = "worker updated"):
        allowed={"resource_id","status","heartbeat_timeout","last_heartbeat","metadata"}
        unknown=set(patch)-allowed
        if unknown:
            raise ValueError(f"Unknown worker fields: {sorted(unknown)}")
        current=next((x for x in self.snapshot.resources.get("workers", []) if x["worker_id"]==worker_id),None)
        if current is None:
            raise KeyError(worker_id)
        candidate=deepcopy(current)
        candidate.update(deepcopy(patch))
        WorkerRecord(**candidate)
        if "resource_id" in patch and not any(r["resource_id"] == patch["resource_id"] for r in self.list_resources()):
            raise KeyError(patch["resource_id"])
        self._commit(Event(
            new_id("evt"),now(),EventType.WORKER_UPDATED.value,
            self.state_value,self.state_value,reason,
            data={"worker_id":worker_id,"patch":deepcopy(patch)},machine_id=self.snapshot.machine_id,
        ))
        return deepcopy(next(x for x in self.snapshot.resources.get("workers", []) if x["worker_id"]==worker_id))

    def worker_heartbeat(self, worker_id: str, *, at_time: float | None = None, reason: str = "worker heartbeat"):
        ts=now() if at_time is None else float(at_time)
        current=next((x for x in self.snapshot.resources.get("workers", []) if x["worker_id"]==worker_id),None)
        if current is None:
            raise KeyError(worker_id)
        patch={"last_heartbeat":ts}
        if current.get("status") == WorkerStatus.STALE.value:
            patch["status"] = WorkerStatus.ACTIVE.value
        self._commit(Event(
            new_id("evt"),ts,EventType.WORKER_HEARTBEAT.value,
            self.state_value,self.state_value,reason,
            data={"worker_id":worker_id,"patch":patch},machine_id=self.snapshot.machine_id,
        ))
        return deepcopy(next(x for x in self.snapshot.resources.get("workers", []) if x["worker_id"]==worker_id))

    def set_quota(self, quota: QuotaPolicy, *, reason: str = "quota set"):
        if quota.scope == "worker" and not any(w["worker_id"] == quota.target_id for w in self.list_workers()):
            raise KeyError(quota.target_id)
        if quota.scope == "resource" and not any(r["resource_id"] == quota.target_id for r in self.list_resources()):
            raise KeyError(quota.target_id)
        self._commit(Event(
            new_id("evt"),now(),EventType.QUOTA_SET.value,
            self.state_value,self.state_value,reason,
            data={"quota":asdict(quota)},machine_id=self.snapshot.machine_id,
        ))
        return deepcopy(next(x for x in self.snapshot.resources.get("quotas", []) if x["quota_id"]==quota.quota_id))

    def list_quotas(self):
        return deepcopy(self.snapshot.resources.get("quotas", []))

    def list_leases(self):
        return deepcopy(self.snapshot.resources.get("leases", []))

    def _active_leases(self, *, at_time: float | None = None):
        ts=now() if at_time is None else float(at_time)
        return [
            x for x in self.snapshot.resources.get("leases", [])
            if x.get("status")==LeaseStatus.ACTIVE.value and float(x.get("expires_at",0))>ts
        ]

    def _quota_allows(self, worker_id: str, resource_id: str, demand: float, *, at_time: float | None = None):
        active=self._active_leases(at_time=at_time)
        for raw in self.snapshot.resources.get("quotas", []):
            q=QuotaPolicy(**deepcopy(raw))
            if not q.enabled:
                continue
            relevant = q.scope=="machine" or (q.scope=="worker" and q.target_id==worker_id) or (q.scope=="resource" and q.target_id==resource_id)
            if not relevant:
                continue
            selected=[
                l for l in active
                if q.scope=="machine"
                or (q.scope=="worker" and l["worker_id"]==worker_id)
                or (q.scope=="resource" and l["resource_id"]==resource_id)
            ]
            if q.max_active_leases is not None and len(selected) >= q.max_active_leases:
                return False, q.quota_id
            if q.max_capacity_units is not None and sum(float(l.get("demand",0)) for l in selected)+demand > q.max_capacity_units+1e-12:
                return False, q.quota_id
        return True, None

    def claim_task(self, task: TaskDemand, worker_id: str, *, lease_seconds: float = 60.0, at_time: float | None = None, reason: str = "task lease claimed"):
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        ts=now() if at_time is None else float(at_time)
        self.expire_leases(at_time=ts)
        worker=next((deepcopy(x) for x in self.snapshot.resources.get("workers", []) if x["worker_id"]==worker_id),None)
        if worker is None:
            raise KeyError(worker_id)
        if worker["status"] != WorkerStatus.ACTIVE.value:
            raise ValueError(f"Worker {worker_id} is not ACTIVE")
        if ts > float(worker["last_heartbeat"])+float(worker["heartbeat_timeout"]):
            self.update_worker(worker_id,{"status":WorkerStatus.STALE.value},reason="worker heartbeat expired")
            raise ValueError(f"Worker {worker_id} is stale")
        resource=next((ResourceRecord(**deepcopy(x)) for x in self.snapshot.resources.get("registry", []) if x["resource_id"]==worker["resource_id"]),None)
        if resource is None:
            raise KeyError(worker["resource_id"])
        if not self.scheduler._eligible(task,resource):
            raise ValueError(f"Resource {resource.resource_id} cannot satisfy task {task.task_id}")

        # Keep the local checks for fast feedback. Durable stores repeat these
        # checks atomically against all live claims so concurrent hosts cannot
        # race past the same capacity/quota boundary.
        used=sum(float(x.get("demand",0)) for x in self._active_leases(at_time=ts) if x["resource_id"]==resource.resource_id)
        if used+float(task.demand) > resource.capacity+1e-12:
            raise ValueError(f"Resource capacity exhausted: {resource.resource_id}")
        ok,quota_id=self._quota_allows(worker_id,resource.resource_id,float(task.demand),at_time=ts)
        if not ok:
            raise ValueError(f"Quota exceeded: {quota_id}")

        previous=[x for x in self.snapshot.resources.get("leases", []) if x["task_id"]==task.task_id]
        attempt=1+max([int(x.get("attempt",1)) for x in previous],default=0)
        lease=TaskLease.from_task(task,worker_id,resource.resource_id,lease_seconds,attempt=attempt)
        lease.acquired_at=ts
        lease.heartbeat_at=ts
        lease.expires_at=ts+float(lease_seconds)

        acquire=getattr(self.store,"acquire_task_claim",None)
        if acquire:
            quotas=deepcopy(self.snapshot.resources.get("quotas", []))
            claimed=acquire(
                self.snapshot.machine_id,
                task.task_id,
                lease.lease_id,
                worker_id,
                lease.expires_at,
                ts,
                resource_id=resource.resource_id,
                demand=float(task.demand),
                resource_capacity=float(resource.capacity),
                quotas=quotas,
            )
            if not claimed:
                raise ValueError(f"Task already claimed: {task.task_id}")

        try:
            self._commit(Event(
                new_id("evt"),ts,EventType.LEASE_CLAIMED.value,
                self.state_value,self.state_value,reason,
                data={"lease":asdict(lease)},machine_id=self.snapshot.machine_id,
            ))
        except Exception:
            release=getattr(self.store,"release_task_claim",None)
            if release:
                release(self.snapshot.machine_id,lease.lease_id)
            raise
        if task.task_id in self.graph.nodes:
            self.plan_update_node(task.task_id,{"owner":worker_id,"status":"leased"},reason="worker claimed plan node")
        return deepcopy(next(x for x in self.snapshot.resources.get("leases", []) if x["lease_id"]==lease.lease_id))

    def lease_heartbeat(self, lease_id: str, *, extend_seconds: float = 60.0, at_time: float | None = None, reason: str = "lease heartbeat"):
        if extend_seconds <= 0:
            raise ValueError("extend_seconds must be positive")
        ts=now() if at_time is None else float(at_time)
        lease=next((x for x in self.snapshot.resources.get("leases", []) if x["lease_id"]==lease_id),None)
        if lease is None:
            raise KeyError(lease_id)
        if lease["status"] != LeaseStatus.ACTIVE.value:
            raise ValueError(f"Lease {lease_id} is not ACTIVE")
        if float(lease["expires_at"]) <= ts:
            self.expire_leases(at_time=ts)
            raise ValueError(f"Lease {lease_id} expired")
        expires=ts+float(extend_seconds)
        renew=getattr(self.store,"renew_task_claim",None)
        if renew and not renew(self.snapshot.machine_id,lease_id,expires):
            raise ValueError(f"Lease claim missing: {lease_id}")
        patch={"heartbeat_at":ts,"expires_at":expires}
        self._commit(Event(
            new_id("evt"),ts,EventType.LEASE_HEARTBEAT.value,
            self.state_value,self.state_value,reason,
            data={"lease_id":lease_id,"patch":patch},machine_id=self.snapshot.machine_id,
        ))
        return deepcopy(next(x for x in self.snapshot.resources.get("leases", []) if x["lease_id"]==lease_id))

    def _finish_lease(self, lease_id: str, status: str, *, result=None, error=None, at_time=None, reason="lease finished"):
        ts=now() if at_time is None else float(at_time)
        lease=next((x for x in self.snapshot.resources.get("leases", []) if x["lease_id"]==lease_id),None)
        if lease is None:
            raise KeyError(lease_id)
        if lease["status"] != LeaseStatus.ACTIVE.value:
            return deepcopy(lease)
        et={
            LeaseStatus.COMPLETED.value:EventType.LEASE_COMPLETED,
            LeaseStatus.FAILED.value:EventType.LEASE_FAILED,
            LeaseStatus.RELEASED.value:EventType.LEASE_RELEASED,
            LeaseStatus.EXPIRED.value:EventType.LEASE_EXPIRED,
        }[status]
        patch={
            "status":status,
            "result":deepcopy(result),
            "error":error,
            "heartbeat_at":ts,
            "expires_at":min(float(lease["expires_at"]),ts),
        }
        self._commit(Event(
            new_id("evt"),ts,et.value,
            self.state_value,self.state_value,reason,
            data={"lease_id":lease_id,"patch":patch},machine_id=self.snapshot.machine_id,
        ))
        release=getattr(self.store,"release_task_claim",None)
        if release:
            release(self.snapshot.machine_id,lease_id)
        if lease["task_id"] in self.graph.nodes:
            node_status={
                LeaseStatus.COMPLETED.value:"complete",
                LeaseStatus.FAILED.value:"failed",
                LeaseStatus.RELEASED.value:"ready",
                LeaseStatus.EXPIRED.value:"ready",
            }[status]
            self.plan_update_node(
                lease["task_id"],
                {"status":node_status,"owner":None if status!=LeaseStatus.COMPLETED.value else lease["worker_id"]},
                reason=reason,
            )
        return deepcopy(next(x for x in self.snapshot.resources.get("leases", []) if x["lease_id"]==lease_id))

    def complete_lease(self,lease_id,*,result=None,at_time=None):
        return self._finish_lease(lease_id,LeaseStatus.COMPLETED.value,result=result,at_time=at_time,reason="lease completed")

    def fail_lease(self,lease_id,*,error=None,at_time=None):
        return self._finish_lease(lease_id,LeaseStatus.FAILED.value,error=error,at_time=at_time,reason="lease failed")

    def release_lease(self,lease_id,*,at_time=None):
        return self._finish_lease(lease_id,LeaseStatus.RELEASED.value,at_time=at_time,reason="lease released")

    def expire_leases(self, *, at_time: float | None = None):
        ts=now() if at_time is None else float(at_time)
        expired=[]
        for lease in list(self.snapshot.resources.get("leases", [])):
            if lease.get("status")==LeaseStatus.ACTIVE.value and float(lease.get("expires_at",0))<=ts:
                expired.append(self._finish_lease(lease["lease_id"],LeaseStatus.EXPIRED.value,at_time=ts,reason="lease expired"))
        return expired

    def reap_stale_workers(self, *, at_time: float | None = None):
        ts=now() if at_time is None else float(at_time)
        stale=[]
        for worker in list(self.snapshot.resources.get("workers", [])):
            if worker.get("status") in {WorkerStatus.ACTIVE.value,WorkerStatus.DRAINING.value} and ts > float(worker.get("last_heartbeat",0))+float(worker.get("heartbeat_timeout",60)):
                self.update_worker(worker["worker_id"],{"status":WorkerStatus.STALE.value},reason="worker heartbeat expired")
                stale.append(worker["worker_id"])
                for lease in list(self.snapshot.resources.get("leases", [])):
                    if lease.get("worker_id")==worker["worker_id"] and lease.get("status")==LeaseStatus.ACTIVE.value:
                        self._finish_lease(lease["lease_id"],LeaseStatus.EXPIRED.value,at_time=ts,reason="worker became stale")
        return stale
