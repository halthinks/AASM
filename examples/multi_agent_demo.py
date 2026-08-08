from aasm import AASMEngine,ProblemSpec,MachineState,FunctionAgent,Proposal,Result

problem=ProblemSpec(
    goal="Produce and verify an artifact",
    constraints=[{"id":"C1","text":"preserve provenance"}],
    acceptance_tests=[{"id":"T1","text":"all tests pass"}],
    features={"dependency_graph":True,"branching_choices":True,"overlapping_subproblems":True,"capacity_constraints":True}
)
e=AASMEngine(problem)

def proposer(agent,ctx): return Proposal(agent.agent_id,"compute",{"state":ctx.state},rationale="work assigned frontier")
def executor(agent,auth): return Result(agent.agent_id,True,{"artifact":"candidate"},["test:demo"])
e.register_agent(FunctionAgent("specialist",{"compute"},proposer,executor))
e.transition(MachineState.FORMALIZE,"goal normalized")
e.transition(MachineState.CLASSIFY,"problem formalized")
print("route:",e.classify())
e.transition(MachineState.PLAN,"algorithm regime selected")
e.transition(MachineState.SELECT,"frontier chosen")
e.transition(MachineState.EXECUTE,"authorized")
print("result:",e.propose_and_execute("specialist"))
e.transition(MachineState.OBSERVE,"result captured")
e.transition(MachineState.VERIFY,"verify evidence")
print("verify:",e.verify({"claims":[{"text":"artifact exists","requires_evidence":True,"evidence":["test:demo"]}]}))
