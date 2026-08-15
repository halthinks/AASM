import threading
from http.server import ThreadingHTTPServer

import pytest

from aasm import (
    DockerComposeScaleAdapter,
    ExecutionTelemetryRecord,
    ForkRequest,
    LocalProcessSupervisorAdapter,
    MissionControlAction,
    MissionControlRecord,
    MissionPauseMode,
    ProblemSpec,
    ProvisioningAction,
    ProvisioningRequest,
    RemoteWorkerLoop,
    ResourceRecord,
    SQLiteStore,
    TaskDemand,
    TelemetryKind,
    WorkerRecord,
)
from aasm.runtime_v52 import AASMEngine
from aasm.remote import AASMRemoteClient, RemoteProtocolError
from aasm.server import make_handler


def _worker_engine(store=None):
    engine = AASMEngine(ProblemSpec("mission control"), store=store)
    engine.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=2))
    engine.register_worker(WorkerRecord("w1", "pool"))
    engine.register_worker(WorkerRecord("w2", "pool"))
    return engine


def test_quiesce_blocks_new_claims_and_resume_restores_admission():
    engine = _worker_engine()
    engine.pause_mission(MissionControlRecord(MissionControlAction.PAUSE, "operator", "maintenance", MissionPauseMode.QUIESCE))
    assert engine.mission_control_report()["status"] == "PAUSED"
    with pytest.raises(ValueError, match="Mission is PAUSED"):
        engine.claim_task(TaskDemand("blocked", ["code"]), "w1")
    engine.resume_mission(MissionControlRecord(MissionControlAction.RESUME, "operator", "maintenance complete"))
    assert engine.claim_task(TaskDemand("allowed", ["code"]), "w1")["status"] == "ACTIVE"


def test_suspend_releases_active_leases_but_quiesce_does_not():
    engine = _worker_engine()
    lease = engine.claim_task(TaskDemand("active", ["code"]), "w1", lease_seconds=120)
    engine.pause_mission(MissionControlRecord(MissionControlAction.PAUSE, "operator", "stop now", MissionPauseMode.SUSPEND))
    current = next(row for row in engine.list_leases() if row["lease_id"] == lease["lease_id"])
    assert current["status"] == "RELEASED"
    assert engine.mission_control_report()["released_lease_ids"] == [lease["lease_id"]]


def test_controlled_fork_requires_approval_and_is_idempotent(tmp_path):
    store = SQLiteStore(tmp_path / "fork.db")
    engine = AASMEngine(ProblemSpec("controlled fork"), store=store)
    request = ForkRequest(engine.current_sequence(), "operator", "evaluate alternate path")
    proposed = engine.propose_fork(request)
    with pytest.raises(ValueError, match="not authorized"):
        engine.execute_fork(proposed.spec.effect_id)
    engine.authorize_pending_effect(proposed.spec.effect_id, "operator", "approved experiment")
    first = engine.execute_fork(proposed.spec.effect_id)
    second = engine.execute_fork(proposed.spec.effect_id)
    assert first.status == second.status == "SUCCEEDED"
    target = store.load_snapshot(request.target_machine_id)
    assert target.metadata["lineage"]["source_machine_id"] == engine.snapshot.machine_id
    assert target.metadata["lineage"]["source_sequence"] == request.source_sequence
    assert len(engine.fork_report()["executions"]) == 1
    store.close()


def test_cursor_pages_are_stable_and_bounded():
    engine = AASMEngine(ProblemSpec("pages"))
    for index in range(7):
        engine.record_execution_telemetry(ExecutionTelemetryRecord("w", f"t{index}", f"l{index}", TelemetryKind.LOG, message=str(index)))
    first = engine.telemetry_page(limit=3)
    second = engine.telemetry_page(cursor=first["next_cursor"], limit=3)
    third = engine.telemetry_page(cursor=second["next_cursor"], limit=3)
    assert [row["message"] for row in first["items"]] == ["6", "5", "4"]
    assert [row["message"] for row in second["items"]] == ["3", "2", "1"]
    assert [row["message"] for row in third["items"]] == ["0"]
    assert third["has_more"] is False


def test_local_process_supervisor_is_idempotent_and_uses_explicit_argv(tmp_path):
    spawned = []
    stopped = []

    def spawn(argv, cwd, env):
        spawned.append((list(argv), cwd, env["AASM_WORKER_ID"]))
        return 1000 + len(spawned)

    def terminate(pid, timeout):
        stopped.append((pid, timeout))
        return True

    adapter = LocalProcessSupervisorAdapter(
        tmp_path / "state",
        default_argv=["python", "worker.py", "--worker-id", "{worker_id}"],
        workspace_root=tmp_path,
        spawn=spawn,
        terminate=terminate,
    )
    request = ProvisioningRequest("local", "pool", ProvisioningAction.PROVISION, 2, "scale locally")
    first = adapter.apply(request, "idem-1")
    second = adapter.apply(request, "idem-1")
    assert first == second
    assert len(spawned) == 2
    target = first["created"][0]["worker_id"]
    drained = adapter.apply(ProvisioningRequest("local", "pool", ProvisioningAction.DRAIN, 1, "scale down", target_worker_ids=[target]), "idem-2")
    assert drained["drained"][0]["stopped"] is True
    assert stopped


def test_docker_compose_adapter_scales_with_explicit_argv():
    calls = []

    def runner(argv):
        calls.append(list(argv))
        if "ps" in argv:
            return 0, "c1\nc2\n", ""
        return 0, "scaled", ""

    adapter = DockerComposeScaleAdapter(default_service="aasm-worker", runner=runner)
    result = adapter.apply(ProvisioningRequest("compose", "pool", ProvisioningAction.PROVISION, 2, "scale"), "idem")
    assert calls[0] == ["docker", "compose", "ps", "-q", "aasm-worker"]
    assert calls[1] == ["docker", "compose", "up", "-d", "--scale", "aasm-worker=4", "aasm-worker"]
    assert result["desired_replicas"] == 4


def test_replica_count_drain_does_not_falsely_mark_logical_target():
    engine = _worker_engine()
    request = ProvisioningRequest(
        "replica-provider",
        "pool",
        ProvisioningAction.DRAIN,
        1,
        "scale replica pool",
        target_worker_ids=["w2"],
    )
    effect = engine.propose_provisioning(request)
    engine.authorize_pending_effect(effect.spec.effect_id, "operator", "approve scale down")

    class ReplicaAdapter:
        def apply(self, request, idempotency_key):
            return {
                "previous_replicas": 2,
                "desired_replicas": 1,
                "drain_scope": "replica-count",
                "idempotency_key": idempotency_key,
            }

    engine.execute_provisioning(effect.spec.effect_id, ReplicaAdapter())
    states = {row["worker_id"]: row["status"] for row in engine.list_workers()}
    assert states["w2"] == "ACTIVE"
    execution = engine.provisioning_report()["executions"][-1]
    assert execution["confirmed_drained_worker_ids"] == []
    assert execution["unconfirmed_logical_targets"] == ["w2"]


def test_remote_worker_reports_lease_lost_instead_of_false_completion():
    telemetry = []

    class Client:
        def state(self, machine_id):
            return {"workers": [{"worker_id": "w", "resource_id": "pool"}]}

        def heartbeat(self, machine_id, worker_id):
            return {"worker_id": worker_id}

        def claim_next(self, machine_id, worker_id, lease_seconds):
            return {"lease_id": "lease", "task_id": "task", "metadata": {}}

        def lease_heartbeat(self, machine_id, lease_id, extend_seconds):
            return {"status": "ACTIVE"}

        def complete(self, machine_id, lease_id, result):
            return {"status": "RELEASED"}

        def fail(self, machine_id, lease_id, error):
            return {"status": "RELEASED"}

        def telemetry(self, machine_id, record):
            telemetry.append(dict(record))
            return record

    loop = RemoteWorkerLoop(
        Client(),
        "machine",
        WorkerRecord("w", "pool"),
        lambda lease: {"ok": True},
        lease_seconds=30,
        heartbeat_interval=5,
    )
    assert loop.run_once() is True
    assert [row["kind"] for row in telemetry] == ["STARTED", "LEASE_LOST"]


def test_effect_queue_separates_approval_execution_and_reconciliation():
    engine = AASMEngine(ProblemSpec("effects"))
    request = ForkRequest(engine.current_sequence(), "operator", "alternate")
    effect = engine.propose_fork(request)
    report = engine.effect_queue_report()
    assert [row["spec"]["effect_id"] for row in report["pending_approval"]] == [effect.spec.effect_id]
    engine.authorize_pending_effect(effect.spec.effect_id, "operator", "approved")
    report = engine.effect_queue_report()
    assert [row["spec"]["effect_id"] for row in report["authorized"]] == [effect.spec.effect_id]


def test_remote_mission_effect_fork_and_paging_round_trip(tmp_path):
    database = str(tmp_path / "remote-v19.db")
    store = SQLiteStore(database)
    engine = _worker_engine(store)
    machine_id = engine.snapshot.machine_id
    engine.record_execution_telemetry(ExecutionTelemetryRecord("w1", "task", "lease", TelemetryKind.LOG, message="hello"))
    store.close()

    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(database, "secret"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = AASMRemoteClient(f"http://127.0.0.1:{server.server_port}", "secret")
        assert client.health()["version"] == "0.19.0"
        client.pause_mission(machine_id, "operator", "hold", "QUIESCE")
        assert client.mission_control(machine_id)["status"] == "PAUSED"
        client.resume_mission(machine_id, "operator", "continue")
        page = client.telemetry_page(machine_id, limit=1)
        assert page["items"][0]["message"] == "hello"
        request = ForkRequest(client.dashboard(machine_id)["event_sequence"], "operator", "remote branch")
        proposed = client.propose_fork(machine_id, request)
        effect_id = proposed["spec"]["effect_id"]
        with pytest.raises(RemoteProtocolError):
            client.execute_fork(machine_id, effect_id)
        client.authorize_effect(machine_id, effect_id, "operator", "approve branch")
        result = client.execute_fork(machine_id, effect_id)
        assert result["status"] == "SUCCEEDED"
    finally:
        server.shutdown()
        server.server_close()


def test_runtime_config_builds_local_and_artifact_registries(tmp_path):
    import json
    from aasm import load_runtime_registries

    path = tmp_path / "runtime.json"
    path.write_text(json.dumps({
        "provisioners": [{
            "name": "local",
            "kind": "local-process",
            "state_dir": str(tmp_path / "state"),
            "workspace_root": str(tmp_path),
            "argv": ["worker", "--id", "{worker_id}"],
        }],
        "artifacts": [{"name": "local", "kind": "local-directory", "root": str(tmp_path / "artifacts")}],
    }))
    provisioners, artifacts = load_runtime_registries(path)
    assert provisioners.providers() == ["local"]
    assert artifacts.names() == ["local"]
