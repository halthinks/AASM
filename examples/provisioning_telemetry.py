from aasm import (
    AASMEngine,
    ExecutionTelemetryRecord,
    FleetControlPolicy,
    FunctionProvisioningAdapter,
    PlanNode,
    ProblemSpec,
    ProvisioningAction,
    ResourceRecord,
    TaskDemand,
    TelemetryKind,
    WorkerRecord,
)

engine = AASMEngine(ProblemSpec("Scale a small coding fleet from live evidence"))
engine.register_resource(ResourceRecord("coding-pool", "agent", ["code"], capacity=8))
engine.register_worker(WorkerRecord("worker-1", "coding-pool"))

for task_id in ["a", "b", "c"]:
    engine.plan_add_node(PlanNode(task_id, "task"))
engine.schedule([
    TaskDemand("a", ["code"], metadata={"task_class": "compile"}),
    TaskDemand("b", ["code"], metadata={"task_class": "compile"}),
    TaskDemand("c", ["code"], metadata={"task_class": "compile"}),
])

# Observed completion time becomes future scheduling evidence.
engine.record_execution_telemetry(ExecutionTelemetryRecord(
    "worker-1", "a", "lease-example", TelemetryKind.COMPLETED,
    duration_seconds=12.0,
    artifact_refs=["artifact://build/a"],
    metadata={"task_class": "compile"},
))

engine.configure_fleet_control(FleetControlPolicy(enabled=True))
print(engine.fleet_control_report())

# Convert the fleet target into a provider-neutral provisioning plan.
plan = engine.plan_fleet_provisioning("demo-provider", "coding-pool")
print(plan)

if plan["requests"]:
    from aasm import ProvisioningRequest
    request = ProvisioningRequest(**plan["requests"][0])
    effect = engine.propose_provisioning(request)

    # An authority decision is deliberately separate from planning.
    engine.authorize_effect(effect.spec.effect_id, authority="operator")

    # A real integration would call Kubernetes/cloud/local supervisor APIs here.
    adapter = FunctionProvisioningAdapter(
        lambda req, key: {"provider": req.provider, "action": req.action, "count": req.count, "idempotency_key": key}
    )
    result = engine.execute_provisioning(effect.spec.effect_id, adapter)
    print(result.status, result.result)
