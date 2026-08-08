from aasm import AASMEngine, ProblemSpec, ResourceRecord, TaskDemand, WorkerRecord, QuotaPolicy

engine = AASMEngine(ProblemSpec("Coordinate two bounded workers"))
engine.register_resource(ResourceRecord("cpu-pool", "worker", ["python"], capacity=2))
engine.register_worker(WorkerRecord("worker-1", "cpu-pool"))
engine.register_worker(WorkerRecord("worker-2", "cpu-pool"))
engine.set_quota(QuotaPolicy("pool-limit", "resource", "cpu-pool", max_active_leases=2))

lease = engine.claim_task(TaskDemand("task-1", ["python"]), "worker-1", lease_seconds=60)
engine.lease_heartbeat(lease["lease_id"], extend_seconds=60)
engine.complete_lease(lease["lease_id"], result={"ok": True})
print(engine.list_leases())
