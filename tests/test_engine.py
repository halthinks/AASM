import pytest
from aasm import AASMEngine, ProblemSpec, MachineState

def test_legal_transitions_and_route():
    e=AASMEngine(ProblemSpec("x",features={"dependency_graph":True,"overlapping_subproblems":True}))
    e.transition(MachineState.FORMALIZE,"ok")
    e.transition(MachineState.CLASSIFY,"ok")
    d=e.classify()
    assert "dynamic_programming" in d.operators
    assert "graph_planning" in d.operators

def test_illegal_transition_rejected():
    e=AASMEngine(ProblemSpec("x"))
    with pytest.raises(ValueError): e.transition(MachineState.COMPLETE,"nope")

def test_checkpoint_restore():
    e=AASMEngine(ProblemSpec("x")); e.transition(MachineState.FORMALIZE,"ok"); cp=e.checkpoint("before mutation")
    e.snapshot.metadata["x"]=1; e.transition(MachineState.CLASSIFY,"ok"); e.transition(MachineState.PLAN,"skip decompose")
    e.transition(MachineState.SELECT,"ready"); e.transition(MachineState.EXECUTE,"run"); e.transition(MachineState.OBSERVE,"done"); e.transition(MachineState.VERIFY,"check")
    e.transition(MachineState.BACKTRACK,"bad branch")
    restored=e.backtrack(cp.checkpoint_id)
    assert "x" not in restored.metadata
    assert restored.state==MachineState.FORMALIZE.value
