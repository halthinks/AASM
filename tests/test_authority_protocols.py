import pytest
from aasm.authority import AutonomousAuthority,QuorumAuthority
from aasm.model import Proposal
from aasm.protocols import PlannerBuilderAdapter

def test_autonomous_reversible_only():
    p=Proposal("a","read",reversible=True); assert AutonomousAuthority().authorize(p)
    with pytest.raises(PermissionError): AutonomousAuthority().authorize(Proposal("a","deploy",reversible=False))

def test_quorum():
    q=QuorumAuthority(2); p=Proposal("a","commit")
    assert q.authorize(p,votes={"a":True,"b":True})
    with pytest.raises(PermissionError): q.authorize(p,votes={"a":True})

def test_planner_builder_is_adapter():
    a=PlannerBuilderAdapter(); assert a.controller_decision("REPAIR").payload["decision"]=="REPAIR"
