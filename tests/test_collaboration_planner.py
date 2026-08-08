from aasm import (
    AASMEngine,
    CollaborationPlanner,
    CollaborationPolicy,
    PlanEdge,
    PlanGraph,
    PlanNode,
    ProblemSpec,
    ResourceRecord,
    SQLiteStore,
    TaskDemand,
)


def graph_for(nodes, edges=()):
    g=PlanGraph()
    for n in nodes: g.add_node(PlanNode(n,"task",estimated_cost=1.0))
    for a,b in edges: g.add_edge(PlanEdge(a,b))
    return g


def tasks(ids,cap="code"):
    return [TaskDemand(x,[cap],metadata={"estimated_duration":1.0}) for x in ids]


def test_serial_critical_path_rejects_useless_fanout():
    ids=[f"t{i}" for i in range(6)]
    g=graph_for(ids,list(zip(ids,ids[1:])))
    resources=[ResourceRecord("fleet","agent",["code"],capacity=100)]
    result=CollaborationPlanner().analyze(g,resources,tasks(ids),CollaborationPolicy(coordination_overhead_per_extra_worker=0))
    assert result.max_parallel_width==1
    assert result.useful_worker_ceiling==1
    assert result.recommended_workers==1
    assert result.critical_path==6


def test_independent_work_uses_full_parallel_width_when_overhead_zero():
    ids=[f"t{i}" for i in range(8)]
    g=graph_for(ids)
    resources=[ResourceRecord("fleet","agent",["code"],capacity=20)]
    result=CollaborationPlanner().analyze(g,resources,tasks(ids),CollaborationPolicy(coordination_overhead_per_extra_worker=0,min_relative_improvement=0,near_optimal_tolerance=0))
    assert result.max_parallel_width==8
    assert result.useful_worker_ceiling==8
    assert result.recommended_workers==8
    assert result.candidates[-1].projected_makespan==1


def test_coordination_overhead_can_make_smaller_team_optimal():
    ids=[f"t{i}" for i in range(12)]
    result=CollaborationPlanner().analyze(graph_for(ids),[ResourceRecord("fleet","agent",["code"],capacity=20)],tasks(ids),CollaborationPolicy(coordination_overhead_per_extra_worker=.8,min_relative_improvement=0,near_optimal_tolerance=0))
    assert 1 < result.recommended_workers < 12


def test_resource_capacity_caps_useful_workers():
    ids=[f"t{i}" for i in range(10)]
    result=CollaborationPlanner().analyze(graph_for(ids),[ResourceRecord("fleet","agent",["code"],capacity=2)],tasks(ids),CollaborationPolicy(coordination_overhead_per_extra_worker=0,min_relative_improvement=0,near_optimal_tolerance=0))
    assert result.useful_worker_ceiling==2
    assert result.recommended_workers==2


def test_capability_min_cut_can_reduce_fanout_to_zero():
    ids=["a","b"]
    result=CollaborationPlanner().analyze(graph_for(ids),[ResourceRecord("gpu","agent",["gpu"],capacity=50)],tasks(ids,"code"))
    assert result.eligible_capacity==0
    assert result.recommended_workers==0
    assert result.schedulable_fraction==0
    assert any(x.startswith("capability:") for x in result.bottlenecks)


def test_engine_persists_collaboration_analysis_across_restart(tmp_path):
    db=tmp_path/"collab.db"; store=SQLiteStore(db); e=AASMEngine(ProblemSpec("parallel"),store=store)
    e.register_resource(ResourceRecord("fleet","agent",["code"],capacity=4))
    for i in range(4): e.plan_add_node(PlanNode(f"t{i}","task"))
    e.schedule(tasks([f"t{i}" for i in range(4)]))
    result=e.analyze_collaboration(policy=CollaborationPolicy(coordination_overhead_per_extra_worker=0,min_relative_improvement=0,near_optimal_tolerance=0))
    assert result["recommended_workers"]==4
    mid=e.snapshot.machine_id; store.close()
    store=SQLiteStore(db); resumed=AASMEngine.resume(mid,store)
    assert resumed.last_collaboration_analysis()["recommended_workers"]==4
    assert resumed.dashboard()["collaboration"]["max_parallel_width"]==4
    store.close()
