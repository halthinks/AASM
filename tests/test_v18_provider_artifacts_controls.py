import threading
from http.server import ThreadingHTTPServer

from aasm import (
    AASMEngine,
    ArtifactBackendRegistry,
    KubernetesScaleAdapter,
    LocalDirectoryArtifactBackend,
    MemoryArtifactBackend,
    ProblemSpec,
    ResourceRecord,
    SQLiteStore,
    WorkerControlAction,
    WorkerControlRecord,
    WorkerRecord,
)
from aasm.remote import AASMRemoteClient, RemoteProtocolError
from aasm.server import make_handler


def test_local_artifact_backend_stays_under_root(tmp_path):
    backend = LocalDirectoryArtifactBackend(tmp_path / "artifacts", "local")
    ref = backend.put_text("../../machine", "../log", "hello")
    assert ref.startswith("artifact+file://local/")
    assert backend.get_text(ref) == "hello"
    assert len(list((tmp_path / "artifacts").rglob("*.txt"))) == 1


def test_memory_artifact_refs_are_content_stable():
    backend = MemoryArtifactBackend()
    first = backend.put_text("run", "log", "same")
    second = backend.put_text("run", "log", "same")
    assert first == second
    assert backend.get_text(first) == "same"


def test_kubernetes_adapter_uses_explicit_argv_and_delta():
    calls = []

    def runner(argv):
        calls.append(list(argv))
        if "get" in argv:
            return 0, '{"spec":{"replicas":2}}', ""
        return 0, "scaled", ""

    from aasm import ProvisioningAction, ProvisioningRequest

    adapter = KubernetesScaleAdapter(runner=runner)
    result = adapter.apply(ProvisioningRequest("kubernetes", "pool", ProvisioningAction.PROVISION, 2, "scale", metadata={"workload": "aasm-workers", "namespace": "agents"}), "idem")
    assert calls[0] == ["kubectl", "-n", "agents", "get", "deployment", "aasm-workers", "-o", "json"]
    assert calls[1] == ["kubectl", "-n", "agents", "scale", "deployment", "aasm-workers", "--replicas=4"]
    assert result["desired_replicas"] == 4


def test_worker_controls_are_durable_and_do_not_delete_worker(tmp_path):
    store = SQLiteStore(tmp_path / "controls.db")
    engine = AASMEngine(ProblemSpec("controls"), store=store)
    engine.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=1))
    engine.register_worker(WorkerRecord("w", "pool"))
    engine.control_worker(WorkerControlRecord("w", WorkerControlAction.DRAIN, "operator", "maintenance"))
    assert engine.list_workers()[0]["status"] == "DRAINING"
    engine.control_worker(WorkerControlRecord("w", WorkerControlAction.RESUME, "operator", "maintenance complete"))
    assert engine.list_workers()[0]["status"] == "ACTIVE"
    machine_id = engine.snapshot.machine_id
    store.close()
    store = SQLiteStore(tmp_path / "controls.db")
    resumed = AASMEngine.resume(machine_id, store)
    assert len(resumed.worker_control_history()) == 2
    store.close()


def test_store_text_artifact_records_ref_and_telemetry():
    engine = AASMEngine(ProblemSpec("artifact"))
    backend = MemoryArtifactBackend()
    item = engine.store_text_artifact(backend, backend_name="memory", namespace="run", name="log", text="hello", worker_id="w", task_id="t", lease_id="l")
    assert item["ref"].startswith("artifact+memory://")
    assert engine.external_artifacts()[-1]["ref"] == item["ref"]
    assert engine.execution_telemetry()[-1]["artifact_refs"] == [item["ref"]]


def test_remote_artifact_and_control_round_trip(tmp_path):
    database = str(tmp_path / "remote.db")
    store = SQLiteStore(database)
    engine = AASMEngine(ProblemSpec("remote"), store=store)
    engine.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=1))
    engine.register_worker(WorkerRecord("w", "pool"))
    machine_id = engine.snapshot.machine_id
    store.close()
    artifacts = ArtifactBackendRegistry()
    artifacts.register("memory", MemoryArtifactBackend())
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(database, "secret", None, artifacts))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = AASMRemoteClient(f"http://127.0.0.1:{server.server_port}", "secret")
        assert client.health()["protocol"] == "aasm.remote.v1"
        client.control_worker(machine_id, "w", WorkerControlRecord("w", WorkerControlAction.DRAIN, "operator", "maintenance"))
        assert client.execution_controls(machine_id)["workers"][0]["status"] == "DRAINING"
        stored = client.store_text_artifact(machine_id, "memory", "log", "hello", worker_id="w", task_id="t", lease_id="l")
        assert stored["ref"].startswith("artifact+memory://")
        assert client.artifacts(machine_id)["artifacts"][-1]["ref"] == stored["ref"]
        preview = client.artifact_content(machine_id, "memory", stored["ref"])
        assert preview["text"] == "hello"

        other_store = SQLiteStore(database)
        other = AASMEngine(ProblemSpec("other"), store=other_store)
        other_id = other.snapshot.machine_id
        other_store.close()
        try:
            client.artifact_content(other_id, "memory", stored["ref"])
        except RemoteProtocolError:
            pass
        else:
            raise AssertionError("cross-machine artifact content must be rejected")
    finally:
        server.shutdown(); server.server_close()
