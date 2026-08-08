from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .codex_telemetry import import_otel_jsonl
from .definitions import MachineDefinition
from .runtime_v09 import AASMEngine
from .model import MachineState, ProblemSpec
from .model_check import check_machine
from .persistence.factory import open_store
from .resources import TaskDemand
from .model_routing import ModelRouteRequest


def _json(data): print(json.dumps(data,indent=2,sort_keys=True,default=str))
def _store_target(args):
    target=getattr(args,"store",None) or getattr(args,"db",None)
    if not target: raise ValueError("a storage target is required")
    return target
def _open(args): return open_store(_store_target(args))
def _add_store_args(parser,*,required=True):
    group=parser.add_mutually_exclusive_group(required=required); group.add_argument("--store",help="SQLite path/sqlite:///... or postgres://.../postgresql://..."); group.add_argument("--db",help="backward-compatible alias for a SQLite database path")


def _demo(args):
    problem=ProblemSpec("Build verified artifact",features={"dependency_graph":True,"branching_choices":True,"capacity_constraints":True}); target=getattr(args,"store",None) or getattr(args,"db",None); store=open_store(target) if target else None; e=AASMEngine(problem,store=store); e.transition(MachineState.FORMALIZE,"normalized"); e.transition(MachineState.CLASSIFY,"formalized"); e.classify(); e.transition(MachineState.PLAN,"classified"); _json(e.export()); store and store.close()
def _runs(args): store=_open(args); _json({"unfinished_runs":store.list_unfinished()}); store.close()
def _replay(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); snap=engine.replay(at_sequence=args.at); _json({"machine_id":args.machine_id,"at_sequence":args.at,"snapshot":asdict(snap),"event_count":len(engine.events)}); store.close()
def _fork(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); forked=engine.fork(args.at); _json({"source_machine_id":args.machine_id,"source_sequence":args.at,"fork_machine_id":forked.snapshot.machine_id,"snapshot":asdict(forked.snapshot)}); store.close()
def _inspect(args):
    store=_open(args); engine=AASMEngine.resume(args.machine_id,store); payload=engine.export();
    if not args.events: payload.pop("events",None)
    _json(payload); store.close()
def _effects(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"effects":[asdict(e) for e in engine.list_effects()]}); store.close()
def _plan(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"graph":engine.snapshot.graph,"frontier":engine.snapshot.frontier,"visited":engine.snapshot.visited,"pruned":engine.snapshot.pruned}); store.close()
def _memory(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"memory":engine.snapshot.memory}); store.close()
def _evidence(args):
    store=_open(args); engine=AASMEngine.resume(args.machine_id,store); payload={"machine_id":args.machine_id,"evidence":engine.snapshot.evidence}
    if args.lineage: payload["lineage"]=[asdict(x) for x in engine.evidence_lineage(args.lineage)]
    _json(payload); store.close()
def _resources(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"resources":engine.list_resources(),"last_schedule":engine.last_schedule()}); store.close()
def _schedule(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); raw=json.loads(open(args.tasks,"r",encoding="utf-8").read()); result=engine.schedule([TaskDemand(**item) for item in raw],reason=f"schedule loaded from {args.tasks}"); _json({"machine_id":args.machine_id,"result":result.to_dict()}); store.close()
def _workers(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"workers":engine.list_workers(),"quotas":engine.list_quotas(),"leases":engine.list_leases()}); store.close()
def _claim(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); task=TaskDemand(**json.loads(open(args.task,"r",encoding="utf-8").read())); lease=engine.claim_task(task,args.worker,lease_seconds=args.lease_seconds); _json({"machine_id":args.machine_id,"lease":lease}); store.close()
def _models(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"models":engine.list_model_profiles(),"last_model_route":engine.last_model_route()}); store.close()
def _model_route(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); result=engine.route_model(ModelRouteRequest(**json.loads(open(args.request,"r",encoding="utf-8").read())); _json(result.to_dict()); store.close()
def _economics(args):
    store=_open(args); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"economics":engine.economics_summary(),"review_decisions":engine.snapshot.resources.get("economics",{}).get("review_decisions",[]),"telemetry_imports":engine.snapshot.resources.get("economics",{}).get("telemetry_imports",[])}); store.close()
def _codex_telemetry(args): store=_open(args); engine=AASMEngine.resume(args.machine_id,store); batch=import_otel_jsonl(args.jsonl); _json({"machine_id":args.machine_id,**engine.import_codex_telemetry(batch)}); store.close()
def _serve(args):
    from .server import serve
    serve(args.store,args.host,args.port,args.token)


def _worker(args):
    from .remote import AASMRemoteClient
    from .workers import WorkerRecord
    from .executor_orchestration import ExecutorBinding, ExecutorRegistry, OrchestratedRemoteWorker
    if args.executor=="codex":
        from .codex_executor import CodexCLIExecutor
        adapter=CodexCLIExecutor(cwd=args.cwd)
    else:
        from .openai_executor import OpenAIResponsesExecutor
        adapter=OpenAIResponsesExecutor()
    registry=ExecutorRegistry(); registry.register(ExecutorBinding(args.executor_id,adapter,[args.provider],args.capability,priority=args.priority,metadata={"kind":args.executor}))
    worker=WorkerRecord(args.worker_id,args.resource_id,metadata={"executors":registry.describe()})
    client=AASMRemoteClient(args.url,args.token,timeout=args.http_timeout)
    runtime=OrchestratedRemoteWorker(client,args.machine_id,worker,registry,lease_seconds=args.lease_seconds,heartbeat_interval=args.heartbeat_interval,idle_sleep=args.idle_sleep)
    if args.once:
        _json({"executed":runtime.run_once(),"worker_id":args.worker_id,"executors":registry.describe()})
    else: runtime.run_forever()


def _verify_machine(args):
    definition=MachineDefinition.load(args.path); report=check_machine(definition); _json(report.to_dict())
    if not report.valid: raise SystemExit(2)


def build_parser():
    parser=argparse.ArgumentParser(prog="aasm",description="Algorithmic Agent State Machine runtime"); sub=parser.add_subparsers(dest="command",required=True)
    demo=sub.add_parser("demo",help="run the built-in demonstration"); _add_store_args(demo,required=False); demo.set_defaults(func=_demo)
    runs=sub.add_parser("runs",help="list unfinished durable runs"); _add_store_args(runs); runs.set_defaults(func=_runs)
    replay=sub.add_parser("replay",help="rebuild a machine snapshot from its event stream"); replay.add_argument("machine_id"); _add_store_args(replay); replay.add_argument("--at",type=int); replay.set_defaults(func=_replay)
    fork=sub.add_parser("fork",help="fork a durable run from an earlier event sequence"); fork.add_argument("machine_id"); _add_store_args(fork); fork.add_argument("--at",type=int,required=True); fork.set_defaults(func=_fork)
    inspect=sub.add_parser("inspect",help="inspect a persisted machine snapshot"); inspect.add_argument("machine_id"); _add_store_args(inspect); inspect.add_argument("--events",action="store_true"); inspect.set_defaults(func=_inspect)
    effects=sub.add_parser("effects",help="list durable external effects for a run"); effects.add_argument("machine_id"); _add_store_args(effects); effects.set_defaults(func=_effects)
    plan=sub.add_parser("plan",help="inspect durable planning graph/frontier state"); plan.add_argument("machine_id"); _add_store_args(plan); plan.set_defaults(func=_plan)
    memory=sub.add_parser("memory",help="inspect durable DP memory"); memory.add_argument("machine_id"); _add_store_args(memory); memory.set_defaults(func=_memory)
    evidence=sub.add_parser("evidence",help="inspect durable evidence and lineage"); evidence.add_argument("machine_id"); _add_store_args(evidence); evidence.add_argument("--lineage"); evidence.set_defaults(func=_evidence)
    resources=sub.add_parser("resources",help="inspect durable capability/resource registry and last schedule"); resources.add_argument("machine_id"); _add_store_args(resources); resources.set_defaults(func=_resources)
    schedule=sub.add_parser("schedule",help="compute and persist a capability-aware schedule"); schedule.add_argument("machine_id"); _add_store_args(schedule); schedule.add_argument("--tasks",required=True); schedule.set_defaults(func=_schedule)
    workers=sub.add_parser("workers",help="inspect durable workers, quotas, and leases"); workers.add_argument("machine_id"); _add_store_args(workers); workers.set_defaults(func=_workers)
    claim=sub.add_parser("claim",help="atomically claim one task for a worker"); claim.add_argument("machine_id"); _add_store_args(claim); claim.add_argument("--worker",required=True); claim.add_argument("--task",required=True); claim.add_argument("--lease-seconds",type=float,default=60.0); claim.set_defaults(func=_claim)
    models=sub.add_parser("models",help="inspect durable model profiles and last route"); models.add_argument("machine_id"); _add_store_args(models); models.set_defaults(func=_models)
    mr=sub.add_parser("model-route",help="route a task to a registered model profile"); mr.add_argument("machine_id"); _add_store_args(mr); mr.add_argument("--request",required=True); mr.set_defaults(func=_model_route)
    econ=sub.add_parser("economics",help="inspect cache-adjusted model spend and governance overhead"); econ.add_argument("machine_id"); _add_store_args(econ); econ.set_defaults(func=_economics)
    telemetry=sub.add_parser("codex-telemetry",help="import Codex OpenTelemetry JSONL token usage into a run"); telemetry.add_argument("machine_id"); _add_store_args(telemetry); telemetry.add_argument("--jsonl",required=True); telemetry.set_defaults(func=_codex_telemetry)
    servep=sub.add_parser("serve",help="run the remote AASM HTTP control plane and browser UI"); servep.add_argument("--store",required=True); servep.add_argument("--host",default="127.0.0.1"); servep.add_argument("--port",type=int,default=8787); servep.add_argument("--token"); servep.set_defaults(func=_serve)
    worker=sub.add_parser("worker",help="run a routed remote executor worker"); worker.add_argument("--url",required=True); worker.add_argument("--machine-id",required=True); worker.add_argument("--worker-id",required=True); worker.add_argument("--resource-id",required=True); worker.add_argument("--executor",choices=["codex","responses"],required=True); worker.add_argument("--executor-id",default="default"); worker.add_argument("--provider",default="openai"); worker.add_argument("--capability",action="append",default=[]); worker.add_argument("--priority",type=int,default=0); worker.add_argument("--cwd"); worker.add_argument("--token"); worker.add_argument("--lease-seconds",type=float,default=120.0); worker.add_argument("--heartbeat-interval",type=float,default=20.0); worker.add_argument("--idle-sleep",type=float,default=2.0); worker.add_argument("--http-timeout",type=float,default=30.0); worker.add_argument("--once",action="store_true"); worker.set_defaults(func=_worker)
    verify=sub.add_parser("verify-machine",help="statically validate a declarative machine definition"); verify.add_argument("path"); verify.set_defaults(func=_verify_machine)
    return parser


def main():
    args=build_parser().parse_args(); args.func(args)
