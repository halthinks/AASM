from __future__ import annotations

import argparse, json
from dataclasses import asdict
from .adaptive_routing import ModelOutcomeRecord
from .codex_telemetry import import_otel_jsonl
from .definitions import MachineDefinition
from .governance import GovernanceBudgetPolicy, GovernanceContext
from .runtime_v13 import AASMEngine
from .team_protocol import BuilderOutput, PlannerDecision, TeamMember, VerifierReport
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
    group=parser.add_mutually_exclusive_group(required=required); group.add_argument("--store"); group.add_argument("--db")
def _load(path): return json.load(open(path,encoding="utf-8"))

def _demo(args):
    store=open_store(args.store or args.db) if (args.store or args.db) else None; e=AASMEngine(ProblemSpec("Build verified artifact",features={"dependency_graph":True,"branching_choices":True,"capacity_constraints":True}),store=store); e.transition(MachineState.FORMALIZE,"normalized"); e.transition(MachineState.CLASSIFY,"formalized"); e.classify(); e.transition(MachineState.PLAN,"classified"); _json(e.export()); store and store.close()
def _runs(args): store=_open(args); _json({"unfinished_runs":store.list_unfinished()}); store.close()
def _replay(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"snapshot":asdict(e.replay(at_sequence=args.at))}); store.close()
def _fork(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); f=e.fork(args.at); _json({"fork_machine_id":f.snapshot.machine_id,"snapshot":asdict(f.snapshot)}); store.close()
def _inspect(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); p=e.export(); (None if args.events else p.pop("events",None)); _json(p); store.close()
def _effects(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json({"effects":[asdict(x) for x in e.list_effects()]}); store.close()
def _plan(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json({"graph":e.snapshot.graph,"frontier":e.snapshot.frontier,"visited":e.snapshot.visited,"pruned":e.snapshot.pruned}); store.close()
def _memory(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.snapshot.memory); store.close()
def _evidence(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); p={"evidence":e.snapshot.evidence}; p.update({"lineage":[asdict(x) for x in e.evidence_lineage(args.lineage)]} if args.lineage else {}); _json(p); store.close()
def _resources(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json({"resources":e.list_resources(),"last_schedule":e.last_schedule()}); store.close()
def _schedule(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.schedule([TaskDemand(**x) for x in _load(args.tasks)]).to_dict()); store.close()
def _workers(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json({"workers":e.list_workers(),"quotas":e.list_quotas(),"leases":e.list_leases()}); store.close()
def _claim(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.claim_task(TaskDemand(**_load(args.task)),args.worker,lease_seconds=args.lease_seconds)); store.close()
def _models(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json({"models":e.list_model_profiles(),"last_model_route":e.last_model_route()}); store.close()
def _model_route(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.route_model(ModelRouteRequest(**_load(args.request))).to_dict()); store.close()
def _model_outcome(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.record_model_outcome(ModelOutcomeRecord(**_load(args.record)))); store.close()
def _model_performance(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json({"task_class":args.task_class,"performance":e.model_performance(args.task_class)}); store.close()
def _economics(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.economics_summary()); store.close()
def _governance(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.governance_report()); store.close()
def _governance_budget(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.configure_governance_budget(GovernanceBudgetPolicy(**_load(args.policy)))); store.close()
def _governance_decide(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.governance_decide(GovernanceContext(**_load(args.context)))); store.close()
def _governance_complete(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.complete_governance_review(args.decision_id,evidence=_load(args.evidence) if args.evidence else [])); store.close()
def _team(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.team_report()); store.close()
def _team_init(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); raw=_load(args.members); _json(e.initialize_team([TeamMember(**x) for x in raw])); store.close()
def _builder_output(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.submit_builder_output(BuilderOutput(**_load(args.record)))); store.close()
def _verifier_report(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.submit_verifier_report(VerifierReport(**_load(args.record)))); store.close()
def _planner_decision(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.planner_decide(PlannerDecision(**_load(args.record)))); store.close()
def _codex_telemetry(args): store=_open(args); e=AASMEngine.resume(args.machine_id,store); _json(e.import_codex_telemetry(import_otel_jsonl(args.jsonl))); store.close()
def _serve(args):
    from .server import serve
    serve(args.store,args.host,args.port,args.token)
def _worker(args):
    from .remote import AASMRemoteClient
    from .workers import WorkerRecord
    from .executor_orchestration import ExecutorBinding,ExecutorRegistry,OrchestratedRemoteWorker
    if args.executor=="codex":
        from .codex_executor import CodexCLIExecutor
        adapter=CodexCLIExecutor(cwd=args.cwd)
    else:
        from .openai_executor import OpenAIResponsesExecutor
        adapter=OpenAIResponsesExecutor()
    registry=ExecutorRegistry(); registry.register(ExecutorBinding(args.executor_id,adapter,[args.provider],args.capability,priority=args.priority,metadata={"kind":args.executor})); worker=WorkerRecord(args.worker_id,args.resource_id,metadata={"executors":registry.describe()}); runtime=OrchestratedRemoteWorker(AASMRemoteClient(args.url,args.token,timeout=args.http_timeout),args.machine_id,worker,registry,lease_seconds=args.lease_seconds,heartbeat_interval=args.heartbeat_interval,idle_sleep=args.idle_sleep)
    _json({"executed":runtime.run_once()}) if args.once else runtime.run_forever()
def _verify_machine(args): report=check_machine(MachineDefinition.load(args.path)); _json(report.to_dict()); (None if report.valid else (_ for _ in ()).throw(SystemExit(2)))

def build_parser():
    p=argparse.ArgumentParser(prog="aasm"); s=p.add_subparsers(dest="command",required=True)
    def stored(name,help): return s.add_parser(name,help=help)
    q=stored("demo","run demo"); _add_store_args(q,required=False); q.set_defaults(func=_demo)
    q=stored("runs","runs"); _add_store_args(q); q.set_defaults(func=_runs)
    q=stored("replay","replay"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--at",type=int); q.set_defaults(func=_replay)
    q=stored("fork","fork"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--at",type=int,required=True); q.set_defaults(func=_fork)
    q=stored("inspect","inspect"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--events",action="store_true"); q.set_defaults(func=_inspect)
    for name,func in [("effects",_effects),("plan",_plan),("memory",_memory),("resources",_resources),("workers",_workers),("models",_models),("economics",_economics),("governance",_governance),("team",_team)]: q=stored(name,name); q.add_argument("machine_id"); _add_store_args(q); q.set_defaults(func=func)
    q=stored("evidence","evidence"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--lineage"); q.set_defaults(func=_evidence)
    q=stored("schedule","schedule"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--tasks",required=True); q.set_defaults(func=_schedule)
    q=stored("claim","claim"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--worker",required=True); q.add_argument("--task",required=True); q.add_argument("--lease-seconds",type=float,default=60); q.set_defaults(func=_claim)
    q=stored("model-route","model route"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--request",required=True); q.set_defaults(func=_model_route)
    q=stored("model-outcome","record evaluated model outcome"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--record",required=True); q.set_defaults(func=_model_outcome)
    q=stored("model-performance","inspect empirical model performance"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--task-class"); q.set_defaults(func=_model_performance)
    q=stored("governance-budget","configure governance budget"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--policy",required=True); q.set_defaults(func=_governance_budget)
    q=stored("governance-decide","evaluate semantic-review requirement"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--context",required=True); q.set_defaults(func=_governance_decide)
    q=stored("governance-complete","mark semantic review completed"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--decision-id",required=True); q.add_argument("--evidence"); q.set_defaults(func=_governance_complete)
    q=stored("team-init","initialize Planner Builder Verifier team"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--members",required=True); q.set_defaults(func=_team_init)
    q=stored("builder-output","record Builder output"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--record",required=True); q.set_defaults(func=_builder_output)
    q=stored("verifier-report","record Verifier report"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--record",required=True); q.set_defaults(func=_verifier_report)
    q=stored("planner-decision","commit Planner directive"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--record",required=True); q.set_defaults(func=_planner_decision)
    q=stored("codex-telemetry","import telemetry"); q.add_argument("machine_id"); _add_store_args(q); q.add_argument("--jsonl",required=True); q.set_defaults(func=_codex_telemetry)
    q=stored("serve","serve"); q.add_argument("--store",required=True); q.add_argument("--host",default="127.0.0.1"); q.add_argument("--port",type=int,default=8787); q.add_argument("--token"); q.set_defaults(func=_serve)
    q=stored("worker","run executor worker"); q.add_argument("--url",required=True); q.add_argument("--machine-id",required=True); q.add_argument("--worker-id",required=True); q.add_argument("--resource-id",required=True); q.add_argument("--executor",choices=["codex","responses"],required=True); q.add_argument("--executor-id",default="default"); q.add_argument("--provider",default="openai"); q.add_argument("--capability",action="append",default=[]); q.add_argument("--priority",type=int,default=0); q.add_argument("--cwd"); q.add_argument("--token"); q.add_argument("--lease-seconds",type=float,default=120); q.add_argument("--heartbeat-interval",type=float,default=20); q.add_argument("--idle-sleep",type=float,default=2); q.add_argument("--http-timeout",type=float,default=30); q.add_argument("--once",action="store_true"); q.set_defaults(func=_worker)
    q=stored("verify-machine","verify machine"); q.add_argument("path"); q.set_defaults(func=_verify_machine)
    return p

def main(): args=build_parser().parse_args(); args.func(args)
