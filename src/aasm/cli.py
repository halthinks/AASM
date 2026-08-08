from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .definitions import MachineDefinition
from .runtime import AASMEngine
from .model import MachineState, ProblemSpec
from .model_check import check_machine
from .persistence import SQLiteStore
from .resources import TaskDemand
from .workers import WorkerRecord, QuotaPolicy


def _json(data): print(json.dumps(data, indent=2, sort_keys=True, default=str))


def _demo(args):
    problem=ProblemSpec("Build verified artifact",features={"dependency_graph":True,"branching_choices":True,"capacity_constraints":True})
    store=SQLiteStore(args.db) if args.db else None
    e=AASMEngine(problem,store=store); e.transition(MachineState.FORMALIZE,"normalized"); e.transition(MachineState.CLASSIFY,"formalized"); e.classify(); e.transition(MachineState.PLAN,"classified")
    _json(e.export())
    if store: store.close()


def _runs(args):
    store=SQLiteStore(args.db); _json({"unfinished_runs":store.list_unfinished()}); store.close()


def _replay(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    snap=engine.replay(at_sequence=args.at)
    _json({"machine_id":args.machine_id,"at_sequence":args.at,"snapshot":asdict(snap),"event_count":len(engine.events)})
    store.close()


def _fork(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); forked=engine.fork(args.at)
    _json({"source_machine_id":args.machine_id,"source_sequence":args.at,"fork_machine_id":forked.snapshot.machine_id,"snapshot":asdict(forked.snapshot)})
    store.close()


def _inspect(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); payload=engine.export()
    if not args.events: payload.pop("events",None)
    _json(payload); store.close()


def _effects(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    _json({"machine_id":args.machine_id,"effects":[asdict(e) for e in engine.list_effects()]}); store.close()


def _plan(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    _json({"machine_id":args.machine_id,"graph":engine.snapshot.graph,"frontier":engine.snapshot.frontier,"visited":engine.snapshot.visited,"pruned":engine.snapshot.pruned}); store.close()


def _memory(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    _json({"machine_id":args.machine_id,"memory":engine.snapshot.memory}); store.close()


def _evidence(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    payload={"machine_id":args.machine_id,"evidence":engine.snapshot.evidence}
    if args.lineage:
        payload["lineage"]=[asdict(x) for x in engine.evidence_lineage(args.lineage)]
    _json(payload); store.close()


def _resources(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    _json({"machine_id":args.machine_id,"resources":engine.list_resources(),"last_schedule":engine.last_schedule()}); store.close()


def _schedule(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    raw=json.loads(open(args.tasks,"r",encoding="utf-8").read())
    tasks=[TaskDemand(**item) for item in raw]
    result=engine.schedule(tasks,reason=f"schedule loaded from {args.tasks}")
    _json({"machine_id":args.machine_id,"result":result.to_dict()}); store.close()


def _workers(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    _json({"machine_id":args.machine_id,"workers":engine.list_workers(),"quotas":engine.list_quotas(),"leases":engine.list_leases()}); store.close()


def _claim(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store)
    raw=json.loads(open(args.task,"r",encoding="utf-8").read()); task=TaskDemand(**raw)
    lease=engine.claim_task(task,args.worker,lease_seconds=args.lease_seconds)
    _json({"machine_id":args.machine_id,"lease":lease}); store.close()


def _verify_machine(args):
    definition=MachineDefinition.load(args.path); report=check_machine(definition); _json(report.to_dict())
    if not report.valid: raise SystemExit(2)


def build_parser():
    parser=argparse.ArgumentParser(prog="aasm",description="Algorithmic Agent State Machine runtime")
    sub=parser.add_subparsers(dest="command",required=True)
    demo=sub.add_parser("demo",help="run the built-in demonstration"); demo.add_argument("--db",help="optional SQLite database path for a durable demo"); demo.set_defaults(func=_demo)
    runs=sub.add_parser("runs",help="list unfinished durable runs"); runs.add_argument("--db",required=True,help="SQLite database path"); runs.set_defaults(func=_runs)
    replay=sub.add_parser("replay",help="rebuild a machine snapshot from its event stream"); replay.add_argument("machine_id"); replay.add_argument("--db",required=True,help="SQLite database path"); replay.add_argument("--at",type=int,help="replay only through this event sequence"); replay.set_defaults(func=_replay)
    fork=sub.add_parser("fork",help="fork a durable run from an earlier event sequence"); fork.add_argument("machine_id"); fork.add_argument("--db",required=True,help="SQLite database path"); fork.add_argument("--at",type=int,required=True,help="source event sequence to fork from"); fork.set_defaults(func=_fork)
    inspect=sub.add_parser("inspect",help="inspect a persisted machine snapshot"); inspect.add_argument("machine_id"); inspect.add_argument("--db",required=True,help="SQLite database path"); inspect.add_argument("--events",action="store_true",help="include the full event stream"); inspect.set_defaults(func=_inspect)
    effects=sub.add_parser("effects",help="list durable external effects for a run"); effects.add_argument("machine_id"); effects.add_argument("--db",required=True,help="SQLite database path"); effects.set_defaults(func=_effects)
    plan=sub.add_parser("plan",help="inspect durable planning graph/frontier state"); plan.add_argument("machine_id"); plan.add_argument("--db",required=True); plan.set_defaults(func=_plan)
    memory=sub.add_parser("memory",help="inspect durable DP memory"); memory.add_argument("machine_id"); memory.add_argument("--db",required=True); memory.set_defaults(func=_memory)
    evidence=sub.add_parser("evidence",help="inspect durable evidence and lineage"); evidence.add_argument("machine_id"); evidence.add_argument("--db",required=True); evidence.add_argument("--lineage",help="show ancestry for one evidence id"); evidence.set_defaults(func=_evidence)
    resources=sub.add_parser("resources",help="inspect durable capability/resource registry and last schedule"); resources.add_argument("machine_id"); resources.add_argument("--db",required=True); resources.set_defaults(func=_resources)
    schedule=sub.add_parser("schedule",help="compute and persist a capability-aware schedule from a JSON task list"); schedule.add_argument("machine_id"); schedule.add_argument("--db",required=True); schedule.add_argument("--tasks",required=True,help="JSON file containing a list of TaskDemand objects"); schedule.set_defaults(func=_schedule)
    workers=sub.add_parser("workers",help="inspect durable workers, quotas, and leases"); workers.add_argument("machine_id"); workers.add_argument("--db",required=True); workers.set_defaults(func=_workers)
    claim=sub.add_parser("claim",help="atomically claim one task for a worker"); claim.add_argument("machine_id"); claim.add_argument("--db",required=True); claim.add_argument("--worker",required=True); claim.add_argument("--task",required=True,help="JSON file containing one TaskDemand"); claim.add_argument("--lease-seconds",type=float,default=60.0); claim.set_defaults(func=_claim)
    verify=sub.add_parser("verify-machine",help="statically validate a declarative machine definition"); verify.add_argument("path",help="JSON/TOML machine definition; YAML when PyYAML is installed"); verify.set_defaults(func=_verify_machine)
    return parser


def main():
    args=build_parser().parse_args(); args.func(args)
