import pytest

from aasm import (
    AASMEngine,
    ChangeImpactAnalyzer,
    ChangeKind,
    ChangeSignal,
    PlanEdge,
    PlanGraph,
    PlanNode,
    ProblemSpec,
    ResourceRecord,
    SQLiteStore,
    TaskDemand,
    TeamMember,
    WorkerRecord,
)


def _graph():
    g=PlanGraph()
    for node in ["a","b","c","x"]: g.add_node(PlanNode(node,"task"))
    g.add_edge(PlanEdge("a","b")); g.add_edge(PlanEdge("b","c"))
    return g


def test_impact_closure_only_marks_downstream_dependents():
    result=ChangeImpactAnalyzer().analyze(_graph(),ChangeSignal(ChangeKind.ASSUMPTION_CHANGED,"A changed",seed_nodes=["b"]),["b","c","x"])
    assert result.affected_nodes==["b","c"]
    assert result.affected_active_tasks==["b","c"]
    assert result.preserved_active_tasks==["x"]
    assert "a" in result.unaffected_nodes


def test_unanchored_change_requires_planner_attention_without_invalidating_whole_plan():
    result=ChangeImpactAnalyzer().analyze(_graph(),ChangeSignal(ChangeKind.USER_STEERING,"new compatibility requirement"),["a","x"])
    assert result.requires_plan_interrupt is True
    assert result.affected_nodes==[]
    assert result.preserved_active_tasks==["a","x"]


def test_selective_pause_releases_only_affected_active_lease_and_blocks_reclaim(tmp_path):
    db=tmp_path/"impact.db"; store=SQLiteStore(db); e=AASMEngine(ProblemSpec("impact"),store=store)
    e.register_resource(ResourceRecord("pool","agent",["code"],capacity=2))
    e.register_worker(WorkerRecord("w1","pool")); e.register_worker(WorkerRecord("w2","pool"))
    for node in _graph().nodes.values(): e.plan_add_node(node)
    e.plan_add_edge(PlanEdge("a","b")); e.plan_add_edge(PlanEdge("b","c"))
    ta=TaskDemand("b",["code"]); tx=TaskDemand("x",["code"])
    lb=e.claim_task(ta,"w1",lease_seconds=120); lx=e.claim_task(tx,"w2",lease_seconds=120)
    impact=e.analyze_change(ChangeSignal(ChangeKind.VERIFICATION_FAILED,"b failed tests",seed_nodes=["b"]))
    leases={x["lease_id"]:x for x in e.list_leases()}
    assert leases[lb["lease_id"]]["status"]=="RELEASED"
    assert leases[lx["lease_id"]]["status"]=="ACTIVE"
    assert set(e.paused_tasks())=={"b","c"}
    with pytest.raises(ValueError,match="paused by information-change checkpoint"):
        e.claim_task(ta,"w1",lease_seconds=120)
    store.close()


def test_only_authoritative_planner_can_resolve_and_partial_resume_is_preserved(tmp_path):
    store=SQLiteStore(tmp_path/"resolve.db"); e=AASMEngine(ProblemSpec("resolve"),store=store)
    for node in _graph().nodes.values(): e.plan_add_node(node)
    e.plan_add_edge(PlanEdge("a","b")); e.plan_add_edge(PlanEdge("b","c"))
    e.initialize_team([
        TeamMember("planner","PLANNER"), TeamMember("builder","BUILDER"), TeamMember("verifier","VERIFIER")
    ])
    impact=e.analyze_change(ChangeSignal(ChangeKind.ASSUMPTION_CHANGED,"changed",seed_nodes=["b"]))
    with pytest.raises(PermissionError): e.resolve_change_impact("builder",impact["impact_id"],resume_nodes=["b"])
    partial=e.resolve_change_impact("planner",impact["impact_id"],resume_nodes=["b"])
    assert partial["status"]=="PARTIAL"
    assert e.paused_tasks()==["c"]
    store.close()


def test_user_interrupt_with_seed_nodes_creates_durable_impact(tmp_path):
    db=tmp_path/"steer.db"; store=SQLiteStore(db); e=AASMEngine(ProblemSpec("steer"),store=store)
    for node in _graph().nodes.values(): e.plan_add_node(node)
    e.plan_add_edge(PlanEdge("a","b")); e.plan_add_edge(PlanEdge("b","c"))
    out=e.user_interrupt("also support FreeCAD",metadata={"seed_nodes":["b"],"source":"user"})
    assert out["impact"]["affected_nodes"]==["b","c"]
    mid=e.snapshot.machine_id; store.close()
    store=SQLiteStore(db); resumed=AASMEngine.resume(mid,store)
    assert resumed.paused_tasks()==["b","c"]
    assert resumed.last_impact()["signal"]["kind"]=="user_steering"
    store.close()
