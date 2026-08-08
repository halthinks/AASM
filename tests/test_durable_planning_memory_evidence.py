from pathlib import Path
from aasm import AASMEngine, PlanEdge, PlanNode, ProblemSpec, SQLiteStore
from aasm.memory import DPMemory


def test_plan_graph_survives_restart_and_replay(tmp_path: Path):
    store=SQLiteStore(tmp_path/'plan.db'); e=AASMEngine(ProblemSpec('durable plan'),store=store)
    e.plan_add_node(PlanNode('research','task',{'topic':'AASM'},estimated_cost=2.0)); seq=e.events[-1].sequence
    e.plan_add_node(PlanNode('build','task')); e.plan_add_edge(PlanEdge('research','build','requires',3.0)); e.plan_update_node('research',{'status':'done','owner':'agent-r'}); e.plan_mark_visited('research')
    resumed=AASMEngine.resume(e.snapshot.machine_id,store); assert set(resumed.graph.nodes)=={'research','build'}; assert resumed.graph.nodes['research'].status=='done'; assert resumed.graph.edges[0].cost==3.0
    historical=e.replay(at_sequence=seq); assert {n['node_id'] for n in historical.graph['nodes']}=={'research'}; assert historical.graph['edges']==[]; store.close()


def test_dp_memory_survives_restart_scope_and_invalidation(tmp_path: Path):
    store=SQLiteStore(tmp_path/'memo.db'); e=AASMEngine(ProblemSpec('memo'),store=store); key=DPMemory.signature('constraint',{'x':3},{'mode':'strict'})
    e.memo_put(key,{'answer':42},scope={'repo':'AASM','version':4},proof=['test:1']); resumed=AASMEngine.resume(e.snapshot.machine_id,store)
    assert resumed.memo_get(key,scope={'repo':'AASM','version':4})=={'answer':42}; assert resumed.memo_get(key,scope={'repo':'AASM','version':5}) is None
    resumed.memo_invalidate(key,'machine definition changed'); again=AASMEngine.resume(e.snapshot.machine_id,store); assert again.memo_get(key,scope={'repo':'AASM','version':4}) is None; store.close()


def test_evidence_lineage_survives_restart_and_invalidation(tmp_path: Path):
    store=SQLiteStore(tmp_path/'evidence.db'); e=AASMEngine(ProblemSpec('evidence'),store=store)
    obs=e.add_observation('test suite passes',source='pytest',confidence=1.0); assumption=e.add_assumption('passing tests imply local compatibility',derived_from=[obs.evidence_id]); claim=e.add_claim('runtime is locally compatible',derived_from=[obs.evidence_id,assumption.evidence_id],confidence=0.95)
    resumed=AASMEngine.resume(e.snapshot.machine_id,store); lineage=resumed.evidence_lineage(claim.evidence_id); assert {x.evidence_id for x in lineage}=={obs.evidence_id,assumption.evidence_id,claim.evidence_id}
    resumed.invalidate_evidence(assumption.evidence_id,'new counterexample'); again=AASMEngine.resume(e.snapshot.machine_id,store); assert again.evidence_ledger.get(assumption.evidence_id).status=='invalidated'; store.close()


def test_historical_fork_carries_only_state_at_boundary(tmp_path: Path):
    store=SQLiteStore(tmp_path/'fork.db'); source=AASMEngine(ProblemSpec('fork cognition'),store=store); source.plan_add_node(PlanNode('A','task')); source.memo_put('memo-a',{'value':'before'}); obs=source.add_observation('before fork'); fork_at=source.events[-1].sequence
    source.plan_add_node(PlanNode('B','task')); source.memo_put('memo-b',{'value':'after'}); later=source.add_claim('after fork',derived_from=[obs.evidence_id]); forked=source.fork(fork_at)
    assert set(forked.graph.nodes)=={'A'}; assert forked.memo_get('memo-a')=={'value':'before'}; assert forked.memo_get('memo-b') is None; assert forked.evidence_ledger.get(obs.evidence_id).statement=='before fork'
    try: forked.evidence_ledger.get(later.evidence_id)
    except KeyError: pass
    else: raise AssertionError('post-fork evidence leaked')
    forked.plan_add_node(PlanNode('C','task')); assert 'C' not in source.graph.nodes; store.close()


def test_plan_pruning_is_durable(tmp_path: Path):
    store=SQLiteStore(tmp_path/'prune.db'); e=AASMEngine(ProblemSpec('prune'),store=store); e.plan_add_node(PlanNode('bad','candidate')); e.plan_prune_node('bad',reason='constraint failed'); resumed=AASMEngine.resume(e.snapshot.machine_id,store); assert resumed.graph.nodes['bad'].status=='pruned'; assert 'bad' in resumed.snapshot.pruned; assert 'bad' not in resumed.snapshot.frontier; store.close()
