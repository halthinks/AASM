import threading
from http.server import ThreadingHTTPServer

import pytest

from aasm import (
    AASMEngine,
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
from aasm.remote import AASMRemoteClient
from aasm.server import make_handler


def test_provisioning_cannot_execute_before_explicit_authorization(tmp_path):
    store = SQLiteStore(tmp_path / "provision.db")
    e = AASMEngine(ProblemSpec("provision"), store=store)
    request = ProvisioningRequest("fake-cloud", "pool", ProvisioningAction.PROVISION, 2, "scale to fleet target")
    effect = e.propose_provisioning(request)
    called = []
    adapter = FunctionProvisioningAdapter(lambda req, key: called.append((req.count, key)) or {"instances": ["i1", "i2"]})
    with pytest.raises(ValueError, match="not authorized"):
        e.execute_provisioning(effect.spec.effect_id, adapter)
    assert called == []
    e.authorize_effect(effect.spec.effect_id, authority="planner-approved-deploy")
    result = e.execute_provisioning(effect.spec.effect_id, adapter)
    assert result.status == "SUCCEEDED"
    assert called and called[0][0] == 2
    store.close()


def test_repeated_provisioning_execution_does_not_duplicate_provider_call_or_history(tmp_path):
    store = SQLiteStore(tmp_path / "provision-idempotent.db")
    e = AASMEngine(ProblemSpec("provision idempotent"), store=store)
    request = ProvisioningRequest("fake-cloud", "pool", ProvisioningAction.PROVISION, 1, "scale")
    first = e.propose_provisioning(request)
    second = e.propose_provisioning(request)
    assert first.spec.effect_id == second.spec.effect_id
    assert len(e.provisioning_history()) == 1
    calls = []
    adapter = FunctionProvisioningAdapter(lambda req, key: calls.append(key) or {"ok": True})
    e.authorize_effect(first.spec.effect_id)
    e.execute_provisioning(first.spec.effect_id, adapter)
    e.execute_provisioning(first.spec.effect_id, adapter)
    assert len(calls) == 1
    assert len(e.provisioning_report()["executions"]) == 1
    store.close()


def test_drain_execution_marks_only_targeted_workers_draining(tmp_path):
    store = SQLiteStore(tmp_path / "drain.db")
    e = AASMEngine(ProblemSpec("drain"), store=store)
    e.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=3))
    for wid in ["w1", "w2", "w3"]: e.register_worker(WorkerRecord(wid, "pool"))
    request = ProvisioningRequest("fake-cloud", "pool", ProvisioningAction.DRAIN, 1, "scale down", target_worker_ids=["w2"])
    effect = e.propose_provisioning(request); e.authorize_effect(effect.spec.effect_id)
    e.execute_provisioning(effect.spec.effect_id, FunctionProvisioningAdapter(lambda req, key: {"drained": req.target_worker_ids}))
    states = {x["worker_id"]: x["status"] for x in e.list_workers()}
    assert states == {"w1": "ACTIVE", "w2": "DRAINING", "w3": "ACTIVE"}
    store.close()


def test_provisioning_plan_prefers_idle_workers_for_drain():
    e = AASMEngine(ProblemSpec("plan drain"))
    e.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=3))
    for wid in ["w1", "w2", "w3"]: e.register_worker(WorkerRecord(wid, "pool"))
    busy = e.claim_task(TaskDemand("busy", ["code"]), "w1", lease_seconds=120)
    plan = e.plan_fleet_provisioning("fake", "pool", desired_workers=1)
    assert plan["delta"] == -2
    assert plan["requests"][0]["target_worker_ids"] == ["w2", "w3"]
    e.release_lease(busy["lease_id"])


def test_telemetry_is_bounded_and_tracks_artifacts_and_durations():
    e = AASMEngine(ProblemSpec("telemetry"))
    e.configure_telemetry(TelemetryPolicy(max_records=3, auto_refresh_fleet_on_completion=False))
    for idx in range(4):
        e.record_execution_telemetry(ExecutionTelemetryRecord("w", "t", f"l{idx}", TelemetryKind.LOG, message=str(idx)))
    e.record_execution_telemetry(ExecutionTelemetryRecord("w", "t", "l4", TelemetryKind.COMPLETED, duration_seconds=8.0, artifact_refs=["artifact://report"], metadata={"task_class": "compile"}))
    rows = e.execution_telemetry()
    assert len(rows) == 3
    report = e.telemetry_report()
    assert report["duration_stats"]["by_task_class"]["compile"]["mean_seconds"] == 8.0
    assert report["artifacts"][-1]["refs"] == ["artifact://report"]
    assert report["recent"] == rows


def test_observed_task_class_duration_feeds_next_collaboration_estimate():
    e = AASMEngine(ProblemSpec("observed duration"))
    e.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=4))
    e.plan_add_node(PlanNode("a", "task")); e.plan_add_node(PlanNode("b", "task"))
    e.schedule([
        TaskDemand("a", ["code"], metadata={"task_class": "compile", "estimated_duration": 1.0}),
        TaskDemand("b", ["code"], metadata={"task_class": "compile", "estimated_duration": 1.0}),
    ])
    e.record_execution_telemetry(ExecutionTelemetryRecord("w", "a", "lease-a", TelemetryKind.COMPLETED, duration_seconds=9.0, metadata={"task_class": "compile"}))
    analysis = e.analyze_collaboration(e._runnable_scheduled_tasks())
    assert analysis["total_work"] == 18.0


def test_remote_worker_emits_started_and_completed_telemetry(tmp_path):
    db = str(tmp_path / "remote-telemetry.db")
    store = SQLiteStore(db); e = AASMEngine(ProblemSpec("remote telemetry"), store=store)
    e.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=1))
    e.schedule([TaskDemand("job", ["code"], metadata={"task_class": "unit", "prompt": "run"})]); mid=e.snapshot.machine_id; store.close()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db, "secret")); threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client=AASMRemoteClient(f"http://127.0.0.1:{server.server_port}","secret")
        loop=RemoteWorkerLoop(client,mid,WorkerRecord("w","pool"),lambda lease:{"artifact_refs":["artifact://x"]},lease_seconds=30,heartbeat_interval=5)
        assert loop.run_once() is True
        report=client.telemetry_report(mid)
        kinds=[x["kind"] for x in client.state(mid)["snapshot"]["resources"]["execution_telemetry"]]
        assert kinds[-2:]==["STARTED","COMPLETED"]
        assert report["artifacts"][-1]["refs"]==["artifact://x"]
        assert report["duration_stats"]["by_task_class"]["unit"]["samples"]==1
    finally:
        server.shutdown(); server.server_close()


def test_remote_authorized_provisioning_executes_only_with_registered_adapter(tmp_path):
    db=str(tmp_path / "remote-provision.db"); store=SQLiteStore(db); e=AASMEngine(ProblemSpec("remote provision"),store=store); mid=e.snapshot.machine_id; store.close()
    registry=ProvisioningRegistry(); seen=[]
    registry.register("fake",FunctionProvisioningAdapter(lambda req,key: seen.append((req.action,req.count,key)) or {"ok":True}))
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(db,"secret",registry)); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        client=AASMRemoteClient(f"http://127.0.0.1:{server.server_port}","secret")
        proposed=client.propose_provisioning(mid,ProvisioningRequest("fake","pool",ProvisioningAction.PROVISION,1,"need worker"))
        effect_id=proposed["spec"]["effect_id"]
        client.authorize_provisioning(mid,effect_id,"operator")
        done=client.execute_provisioning(mid,effect_id)
        assert done["status"]=="SUCCEEDED"
        assert seen and seen[0][:2]==("PROVISION",1)
    finally:
        server.shutdown(); server.server_close()
