from dataclasses import dataclass

from aasm import (
    AASMEngine,
    ExecutorBinding,
    ExecutorRegistry,
    ExecutionContract,
    ExecutionOrchestrator,
    ModelProfile,
    ModelUsageRecord,
    OrchestratedRemoteWorker,
    ProblemSpec,
    ResourceRecord,
    SQLiteStore,
    TaskDemand,
    WorkerRecord,
)


@dataclass
class FakeResult:
    output_text: str
    usage: ModelUsageRecord
    response_id: str | None = None
    thread_id: str | None = None


class FakeAdapter:
    def __init__(self,label="fake"):
        self.label=label; self.calls=[]
    def run(self,prompt,*,model=None,purpose="productive",task_id=None,**kwargs):
        self.calls.append({"prompt":prompt,"model":model,"purpose":purpose,"task_id":task_id,"kwargs":kwargs})
        return FakeResult(f"{self.label}:{prompt}",ModelUsageRecord(model or "none",purpose,input_tokens=100,output_tokens=20,task_id=task_id),response_id="resp-1")


class FakeClient:
    def __init__(self):
        self.usage=[]; self.route={"task_id":"task","selected_model_id":"terra","provider":"openai","score":1.0,"eligible":["terra"],"rejected":{},"reason":"test"}; self.models=[{"model_id":"sol","provider":"openai"}]
    def route_model(self,machine_id,request): out=dict(self.route); out["task_id"]=request.task_id; return out
    def model_usage(self,machine_id,record): self.usage.append(record); return record
    def state(self,machine_id): return {"models":self.models}


def test_execution_contract_accepts_legacy_prompt_metadata():
    contract=ExecutionContract.from_lease({"metadata":{"prompt":"do it","purpose":"verification"}})
    assert contract.prompt=="do it" and contract.purpose=="verification"


def test_registry_selects_provider_capability_and_priority():
    registry=ExecutorRegistry(); registry.register(ExecutorBinding("low",FakeAdapter("low"),["openai"],["code"],priority=1)); registry.register(ExecutorBinding("high",FakeAdapter("high"),["openai"],["code"],priority=10))
    assert registry.select(provider="openai",required_capabilities=["code"]).executor_id=="high"


def test_orchestrator_routes_executes_and_reports_usage():
    client=FakeClient(); adapter=FakeAdapter(); registry=ExecutorRegistry(); registry.register(ExecutorBinding("responses",adapter,["openai"],["code"]))
    result=ExecutionOrchestrator(client,"m1",registry).execute({"task_id":"t1","lease_id":"l1","metadata":{"execution":{"prompt":"implement","executor_required_capabilities":["code"],"min_strength":0.5}}})
    assert result["model_id"]=="terra" and result["executor_id"]=="responses" and result["output_text"]=="fake:implement"
    assert result["evidence"]==["openai_response:resp-1"] and client.usage[0]["task_id"]=="t1" and adapter.calls[0]["model"]=="terra"


def test_orchestrator_fixed_model_uses_registered_provider():
    client=FakeClient(); registry=ExecutorRegistry(); registry.register(ExecutorBinding("responses",FakeAdapter(),["openai"],[]))
    result=ExecutionOrchestrator(client,"m1",registry).execute({"task_id":"t2","lease_id":"l2","metadata":{"execution":{"prompt":"review","fixed_model_id":"sol"}}})
    assert result["model_id"]=="sol" and result["route"]["reason"].startswith("fixed model")


def test_orchestrated_remote_worker_executes_real_http_lease(tmp_path):
    import threading
    from http.server import ThreadingHTTPServer
    from aasm import AASMRemoteClient
    from aasm.server import make_handler

    db=str(tmp_path/"orchestrated.db"); store=SQLiteStore(db); engine=AASMEngine(ProblemSpec("orchestrate"),store=store)
    engine.register_resource(ResourceRecord("cpu","worker",["code"],capacity=1)); engine.register_model_profile(ModelProfile("terra","openai",["code"],strength=.8,cost_per_1k_output=1)); engine.schedule([TaskDemand("job",["code"],metadata={"execution":{"prompt":"ship it","model_required_capabilities":["code"],"executor_required_capabilities":["code"]}})]); mid=engine.snapshot.machine_id; store.close()
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(db,"secret")); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        client=AASMRemoteClient(f"http://127.0.0.1:{server.server_port}","secret"); adapter=FakeAdapter("http"); registry=ExecutorRegistry(); registry.register(ExecutorBinding("responses",adapter,["openai"],["code"])); worker=OrchestratedRemoteWorker(client,mid,WorkerRecord("worker-1","cpu"),registry,lease_seconds=30,heartbeat_interval=5)
        assert worker.run_once() is True
        state=client.state(mid); assert state["leases"][-1]["status"]=="COMPLETED" and state["leases"][-1]["result"]["model_id"]=="terra" and adapter.calls[0]["prompt"]=="ship it"
        # A process restart with the same durable worker identity reconnects.
        restarted=OrchestratedRemoteWorker(client,mid,WorkerRecord("worker-1","cpu"),registry,lease_seconds=30,heartbeat_interval=5)
        assert restarted.run_once() is False
        assert [w["worker_id"] for w in client.state(mid)["workers"]].count("worker-1")==1
    finally:
        server.shutdown(); server.server_close()


def test_worker_cli_is_exposed():
    from aasm.cli import build_parser
    args=build_parser().parse_args(["worker","--url","http://127.0.0.1:8787","--machine-id","m","--worker-id","w","--resource-id","r","--executor","codex","--capability","code","--once"])
    assert args.command=="worker" and args.executor=="codex" and args.capability==["code"]
