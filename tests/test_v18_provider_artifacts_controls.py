import threading
from http.server import ThreadingHTTPServer

import pytest

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
from aasm.remote import AASMRemoteClient
from aasm.server import make_handler


def test_local_artifact_backend_stays_under_root(tmp_path):
    backend=LocalDirectoryArtifactBackend(tmp_path/"artifacts","local")
    ref=backend.put_text("../../machine","../log","hello")
    assert ref.startswith("artifact+file://local/")
    assert backend.get_text(ref)=="hello"
    assert len(list((tmp_path/"artifacts").rglob("*.txt")))==1


def test_memory_artifact_refs_are_content_stable():
    backend=MemoryArtifactBackend()
    a=backend.put_text("run","log","same")
    b=backend.put_text("run","log","same")
    assert a==b
    assert backend.get_text(a)=="same"


def test_kubernetes_adapter_uses_explicit_argv_and_delta():
    calls=[]
    def runner(argv):
        calls.append(list(argv))
        if "get" in argv: return 0,'{"spec":{"replicas":2}}',''
        return 0,'scaled',''
    from aasm import ProvisioningAction, ProvisioningRequest
    adapter=KubernetesScaleAdapter(runner=runner)
    result=adapter.apply(ProvisioningRequest("kubernetes","pool",ProvisioningAction.PROVISION,2,"scale",metadata={"workload":"aasm-workers","namespace":"agents"}),"idem")
    assert calls[0]==["kubectl","-n","agents","get","deployment","aasm-workers","-o","json"]
    assert calls[1]==["kubectl","-n","agents","scale","deployment","aasm-workers","--replicas=4"]
    assert result["desired_replicas"]==4


def test_worker_controls_are_durable_and_do_not_delete_worker(tmp_path):
    store=SQLiteStore(tmp_path/"controls.db"); e=AASMEngine(ProblemSpec("controls"),store=store)
    e.register_resource(ResourceRecord("pool","agent",["code"],capacity=1)); e.register_worker(WorkerRecord("w","pool"))
    e.control_worker(WorkerControlRecord("w",WorkerControlAction.DRAIN,"operator","maintenance"))
    assert e.list_workers()[0]["status"]=="DRAINING"
    e.control_worker(WorkerControlRecord("w",WorkerControlAction.RESUME,"operator","maintenance complete"))
    assert e.list_workers()[0]["status"]=="ACTIVE"
    mid=e.snapshot.machine_id; store.close(); store=SQLiteStore(tmp_path/"controls.db"); r=AASMEngine.resume(mid,store)
    assert len(r.worker_control_history())==2
    store.close()


def test_store_text_artifact_records_ref_and_telemetry():
    e=AASMEngine(ProblemSpec("artifact")); backend=MemoryArtifactBackend()
    item=e.store_text_artifact(backend,backend_name="memory",namespace="run",name="log",text="hello",worker_id="w",task_id="t",lease_id="l")
    assert item["ref"].startswith("artifact+memory://")
    assert e.external_artifacts()[-1]["ref"]==item["ref"]
    assert e.execution_telemetry()[-1]["artifact_refs"]==[item["ref"]]


def test_remote_artifact_and_control_round_trip(tmp_path):
    db=str(tmp_path/"remote.db"); store=SQLiteStore(db); e=AASMEngine(ProblemSpec("remote"),store=store)
    e.register_resource(ResourceRecord("pool","agent",["code"],capacity=1)); e.register_worker(WorkerRecord("w","pool")); mid=e.snapshot.machine_id; store.close()
    artifacts=ArtifactBackendRegistry(); artifacts.register("memory",MemoryArtifactBackend())
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(db,"secret",None,artifacts)); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        client=AASMRemoteClient(f"http://127.0.0.1:{server.server_port}","secret")
        assert client.health()["version"]=="0.18.0"
        client.control_worker(mid,"w",WorkerControlRecord("w",WorkerControlAction.DRAIN,"operator","maintenance"))
        assert client.execution_controls(mid)["workers"][0]["status"]=="DRAINING"
        stored=client.store_text_artifact(mid,"memory","log","hello",worker_id="w",task_id="t",lease_id="l")
        assert stored["ref"].startswith("artifact+memory://")
        assert client.artifacts(mid)["artifacts"][-1]["ref"]==stored["ref"]
    finally:
        server.shutdown(); server.server_close()
