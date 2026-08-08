from aasm.memory import DPMemory
from aasm.flow import ResourceFlowAllocator
from aasm.adversary import default_verifier

def test_dp_memory_scope():
    m=DPMemory(); k=m.signature("x",{"a":1}); m.put(k,{"answer":2},scope={"version":1})
    assert m.get(k,scope={"version":1})=={"answer":2}
    assert m.get(k,scope={"version":2}) is None

def test_maxflow_and_mincut():
    c={"s":{"a":3,"b":2},"a":{"t":2},"b":{"t":2}}
    r=ResourceFlowAllocator().solve(c,"s","t")
    assert r["max_flow"]==4
    assert r["min_cut_edges"]

def test_adversary_blocks_unsupported_claim():
    v=default_verifier(); r=v.verify({"claims":[{"text":"x","requires_evidence":True,"evidence":[]} ]})
    assert not r["ok"]
