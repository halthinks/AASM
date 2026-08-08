import argparse,json
from .model import ProblemSpec,MachineState
from .engine import AASMEngine

def main():
    p=argparse.ArgumentParser(prog="aasm"); p.add_argument("command",choices=["demo"]); args=p.parse_args()
    if args.command=="demo":
        problem=ProblemSpec("Build verified artifact",features={"dependency_graph":True,"branching_choices":True,"capacity_constraints":True})
        e=AASMEngine(problem); e.transition(MachineState.FORMALIZE,"normalized"); e.transition(MachineState.CLASSIFY,"formalized"); e.classify(); e.transition(MachineState.PLAN,"classified")
        print(json.dumps(e.export(),indent=2))
