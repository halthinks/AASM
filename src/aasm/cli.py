from __future__ import annotations
import argparse, json
from dataclasses import asdict
from .definitions import MachineDefinition
from .engine import AASMEngine
from .model import MachineState, ProblemSpec
from .model_check import check_machine
from .persistence import SQLiteStore

def _json(data): print(json.dumps(data, indent=2, sort_keys=True, default=str))
def _demo(args):
    problem=ProblemSpec("Build verified artifact",features={"dependency_graph":True,"branching_choices":True,"capacity_constraints":True}); store=SQLiteStore(args.db) if args.db else None; e=AASMEngine(problem,store=store); e.transition(MachineState.FORMALIZE,"normalized"); e.transition(MachineState.CLASSIFY,"formalized"); e.classify(); e.transition(MachineState.PLAN,"classified"); _json(e.export()); store and store.close()
def _runs(args): store=SQLiteStore(args.db); _json({"unfinished_runs":store.list_unfinished()}); store.close()
def _replay(args): store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); snap=engine.replay(at_sequence=args.at); _json({"machine_id":args.machine_id,"at_sequence":args.at,"snapshot":asdict(snap),"event_count":len(engine.events)}); store.close()
def _fork(args): store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); forked=engine.fork(args.at); _json({"source_machine_id":args.machine_id,"source_sequence":args.at,"fork_machine_id":forked.snapshot.machine_id,"snapshot":asdict(forked.snapshot)}); store.close()
def _inspect(args): store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); payload=engine.export(); (None if args.events else payload.pop("events",None)); _json(payload); store.close()
def _effects(args): store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"effects":[asdict(e) for e in engine.list_effects()]}); store.close()
def _plan(args): store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"graph":engine.snapshot.graph,"frontier":engine.snapshot.frontier,"visited":engine.snapshot.visited,"pruned":engine.snapshot.pruned}); store.close()
def _memory(args): store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); _json({"machine_id":args.machine_id,"memory":engine.snapshot.memory}); store.close()
def _evidence(args):
    store=SQLiteStore(args.db); engine=AASMEngine.resume(args.machine_id,store); payload={"machine_id":args.machine_id,"evidence":engine.snapshot.evidence}
    if args.lineage: payload["lineage"]=[asdict(x) for x in engine.evidence_lineage(args.lineage)]
    _json(payload); store.close()
def _verify_machine(args): definition=MachineDefinition.load(args.path); report=check_machine(definition); _json(report.to_dict()); (None if report.valid else (_ for _ in ()).throw(SystemExit(2)))
def build_parser():
    parser=argparse.ArgumentParser(prog="aasm",description="Algorithmic Agent State Machine runtime"); sub=parser.add_subparsers(dest="command",required=True)
    demo=sub.add_parser("demo"); demo.add_argument("--db"); demo.set_defaults(func=_demo)
    runs=sub.add_parser("runs"); runs.add_argument("--db",required=True); runs.set_defaults(func=_runs)
    replay=sub.add_parser("replay"); replay.add_argument("machine_id"); replay.add_argument("--db",required=True); replay.add_argument("--at",type=int); replay.set_defaults(func=_replay)
    fork=sub.add_parser("fork"); fork.add_argument("machine_id"); fork.add_argument("--db",required=True); fork.add_argument("--at",type=int,required=True); fork.set_defaults(func=_fork)
    inspect=sub.add_parser("inspect"); inspect.add_argument("machine_id"); inspect.add_argument("--db",required=True); inspect.add_argument("--events",action="store_true"); inspect.set_defaults(func=_inspect)
    effects=sub.add_parser("effects"); effects.add_argument("machine_id"); effects.add_argument("--db",required=True); effects.set_defaults(func=_effects)
    plan=sub.add_parser("plan"); plan.add_argument("machine_id"); plan.add_argument("--db",required=True); plan.set_defaults(func=_plan)
    memory=sub.add_parser("memory"); memory.add_argument("machine_id"); memory.add_argument("--db",required=True); memory.set_defaults(func=_memory)
    evidence=sub.add_parser("evidence"); evidence.add_argument("machine_id"); evidence.add_argument("--db",required=True); evidence.add_argument("--lineage"); evidence.set_defaults(func=_evidence)
    verify=sub.add_parser("verify-machine"); verify.add_argument("path"); verify.set_defaults(func=_verify_machine)
    return parser
def main(): args=build_parser().parse_args(); args.func(args)
