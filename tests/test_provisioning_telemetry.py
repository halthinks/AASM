import threading
from http.server import ThreadingHTTPServer

import pytest

from aasm import (
    ExecutionTelemetryRecord,
    FleetControlPolicy,
    FunctionProvisioningAdapter,
    PlanNode,
    ProblemSpec,
    ProvisioningAction,
    ProvisioningRegistry,
    ProvisioningRequest,
    RemoteWorkerLoop,
    ResourceRecord,
    SQLiteStore,
    TaskDemand,
    TelemetryKind,
    TelemetryPolicy,
    WorkerRecord,
)
from aasm.runtime_v52 import AASMEngine
from aasm.remote import AASMRemoteClient
from aasm.server import make_handler


def test_provisioning_cannot_execute_before_explicit_authorization(tmp_path):
    store = SQLiteStore(tmp_path / "provision.db")
    engine = AASMEngine(ProblemSpec("provision"), store=store)
    request = ProvisioningRequest("fake-cloud", "pool", ProvisioningAction.PROVISION, 2, "scale to fleet target")
    effect = engine.propose_provisioning(request)
    called = []
    adapter = FunctionProvisioningAdapter(lambda req, key: called.append((req.count, key)) or {"instances": ["i1", "i2"]})
    with pytest.raises(ValueError, match="not authorized"):
        engine.execute_provisioning(effect.spec.effect_id, adapter)
    assert called == []
    engine.authorize_effect(effect.spec.effect_id, authority="planner-approved-deploy")
    result = engine.execute_provisioning(effect.spec.effect_id, adapter)
    assert result.status == "SUCCEEDED"
    assert called and called[0][0] == 2
    store.close()


def test_drain_execution_marks_only_targeted_workers_draining(tmp_path):
    store = SQLiteStore(tmp_path / "drain.db")
    engine = AASMEngine(ProblemSpec("drain"), store=store)
    engine.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=3))
    for worker_id in ["w1", "w2", "w3"]:
        engine.register_worker(WorkerRecord(worker_id, "pool"))
    request = ProvisioningRequest("fake-cloud", "pool", ProvisioningAction.DRAIN, 1, "scale down", target_worker_ids=["w2"])
    effect = engine.propose_provisioning(request)
    engine.authorize_effect(effect.spec.effect_id)
    engine.execute_provisioning(effect.spec.effect_id, FunctionProvisioningAdapter(lambda req, key: {"drained": req.target_worker_ids}))
    states = {row["worker_id"]: row["status"] for row in engine.list_workers()}
    assert states == {"w1": "ACTIVE", "w2": "DRAINING", "w3": "ACTIVE"}
    store.close()


def test_provisioning_plan_prefers_idle_workers_for_drain():
    engine = AASMEngine(ProblemSpec("plan drain"))
    engine.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=3))
    for worker_id in ["w1", "w2", "w3"]:
        engine.register_worker(WorkerRecord(worker_id, "pool"))
    busy = engine.claim_task(TaskDemand("busy", ["code"]), "w1", lease_seconds=120)
    plan = engine.plan_fleet_provisioning("fake", "pool", desired_workers=1)
    assert plan["delta"] == -2
    assert plan["requests"][0]["target_worker_ids"] == ["w2", "w3"]
    engine.release_lease(busy["lease_id"])


def test_telemetry_is_bounded_and_tracks_artifacts_and_durations():
    engine = AASMEngine(ProblemSpec("telemetry"))
    engine.configure_telemetry(TelemetryPolicy(max_records=3, auto_refresh_fleet_on_completion=False))
    for index in range(4):
        engine.record_execution_telemetry(ExecutionTelemetryRecord("w", "t", f"l{index}", TelemetryKind.LOG, message=str(index)))
    engine.record_execution_telemetry(ExecutionTelemetryRecord("w", "t", "l4", TelemetryKind.COMPLETED, duration_seconds=8.0, artifact_refs=["artifact://report"], metadata={"task_class": "compile"}))
    rows = engine.execution_telemetry()
    assert len(rows) == 3
    report = engine.telemetry_report()
    assert report["duration_stats"]["by_task_class"]["compile"]["mean_seconds"] == 8.0
    assert report["artifacts"][-1]["refs"] == ["artifact://report"]


def test_observed_task_class_duration_feeds_next_collaboration_estimate():
    engine = AASMEngine(ProblemSpec("observed duration"))
    engine.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=4))
    engine.plan_add_node(PlanNode("a", "task")); engine.plan_add_node(PlanNode("b", "task"))
    engine.schedule([
        TaskDemand("a", ["code"], metadata={"task_class": "compile", "estimated_duration": 1.0}),
        TaskDemand("b", ["code"], metadata={"task_class": "compile", "estimated_duration": 1.0}),
    ])
    engine.record_execution_telemetry(ExecutionTelemetryRecord("w", "a", "lease-a", TelemetryKind.COMPLETED, duration_seconds=9.0, metadata={"task_class": "compile"}))
    analysis = engine.analyze_collaboration(engine._runnable_scheduled_tasks())
    assert analysis["total_work"] == 18.0


def test_remote_worker_emits_started_and_completed_telemetry(tmp_path):
    database = str(tmp_path / "remote-telemetry.db")
    store = SQLiteStore(database)
    engine = AASMEngine(ProblemSpec("remote telemetry"), store=store)
    engine.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=1))
    engine.schedule([TaskDemand("job", ["code"], metadata={"task_class": "unit", "prompt": "run"})])
    machine_id = engine.snapshot.machine_id
    store.close()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(database, "secret"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = AASMRemoteClient(f"http://127.0.0.1:{server.server_port}", "secret")
        assert client.health()["protocol"] == "aasm.remote.v1"
        loop = RemoteWorkerLoop(client, machine_id, WorkerRecord("w", "pool"), lambda lease: {"artifact_refs": ["artifact://x"]}, lease_seconds=30, heartbeat_interval=5)
        assert loop.run_once() is True
        report = client.telemetry_report(machine_id)
        kinds = [row["kind"] for row in client.state(machine_id)["snapshot"]["resources"]["execution_telemetry"]]
        assert kinds[-2:] == ["STARTED", "COMPLETED"]
        assert report["artifacts"][-1]["refs"] == ["artifact://x"]
        assert report["duration_stats"]["by_task_class"]["unit"]["samples"] == 1
    finally:
        server.shutdown(); server.server_close()


def test_remote_authorized_provisioning_executes_only_with_registered_adapter(tmp_path):
    database = str(tmp_path / "remote-provision.db")
    store = SQLiteStore(database)
    engine = AASMEngine(ProblemSpec("remote provision"), store=store)
    machine_id = engine.snapshot.machine_id
    store.close()
    registry = ProvisioningRegistry()
    seen = []
    registry.register("fake", FunctionProvisioningAdapter(lambda req, key: seen.append((req.action, req.count, key)) or {"ok": True}))
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(database, "secret", registry))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = AASMRemoteClient(f"http://127.0.0.1:{server.server_port}", "secret")
        proposed = client.propose_provisioning(machine_id, ProvisioningRequest("fake", "pool", ProvisioningAction.PROVISION, 1, "need worker"))
        effect_id = proposed["spec"]["effect_id"]
        client.authorize_provisioning(machine_id, effect_id, "operator")
        done = client.execute_provisioning(machine_id, effect_id)
        assert done["status"] == "SUCCEEDED"
        assert seen and seen[0][:2] == ("PROVISION", 1)
    finally:
        server.shutdown(); server.server_close()
