from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from .engine import AASMEngine
from .model import MachineState, ProblemSpec
from .persistence import SQLiteStore


def _json(data):
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def _demo(args):
    problem=ProblemSpec("Build verified artifact",features={"dependency_graph":True,"branching_choices":True,"capacity_constraints":True})
    store=SQLiteStore(args.db) if args.db else None
    e=AASMEngine(problem,store=store); e.transition(MachineState.FORMALIZE,"normalized"); e.transition(MachineState.CLASSIFY,"formalized"); e.classify(); e.transition(MachineState.PLAN,"classified")
    _json(e.export())
    if store: store.close()


def _runs(args):
    store=SQLiteStore(args.db)
    _json({"unfinished_runs":store.list_unfinished()})
    store.close()


def _replay(args):
    store=SQLiteStore(args.db)
    engine=AASMEngine.resume(args.machine_id,store)
    _json({"machine_id":args.machine_id,"snapshot":asdict(engine.replay()),"event_count":len(engine.events)})
    store.close()


def _inspect(args):
    store=SQLiteStore(args.db)
    engine=AASMEngine.resume(args.machine_id,store)
    payload=engine.export()
    if not args.events:
        payload.pop("events",None)
    _json(payload)
    store.close()


def build_parser():
    parser=argparse.ArgumentParser(prog="aasm",description="Algorithmic Agent State Machine runtime")
    sub=parser.add_subparsers(dest="command",required=True)
    demo=sub.add_parser("demo",help="run the built-in demonstration")
    demo.add_argument("--db",help="optional SQLite database path for a durable demo")
    demo.set_defaults(func=_demo)
    runs=sub.add_parser("runs",help="list unfinished durable runs")
    runs.add_argument("--db",required=True,help="SQLite database path")
    runs.set_defaults(func=_runs)
    replay=sub.add_parser("replay",help="rebuild a machine snapshot from its event stream")
    replay.add_argument("machine_id")
    replay.add_argument("--db",required=True,help="SQLite database path")
    replay.set_defaults(func=_replay)
    inspect=sub.add_parser("inspect",help="inspect a persisted machine snapshot")
    inspect.add_argument("machine_id")
    inspect.add_argument("--db",required=True,help="SQLite database path")
    inspect.add_argument("--events",action="store_true",help="include the full event stream")
    inspect.set_defaults(func=_inspect)
    return parser


def main():
    args=build_parser().parse_args()
    args.func(args)
