from pathlib import Path

from aasm import AASMEngine, ProblemSpec, ResourceRecord, SQLiteStore, TaskDemand
from aasm.graph import PlanNode


def test_capability_scheduler_matches_tasks_and_persists(tmp_path: Path):
    store = SQLiteStore(tmp_path / "sched.db")
    engine = AASMEngine(ProblemSpec("schedule specialists"), store=store)
    engine.register_resource(ResourceRecord("researcher", "agent", ["retrieval", "evidence"], capacity=1))
    engine.register_resource(ResourceRecord("builder", "agent", ["python", "implementation"], capacity=2))
    engine.plan_add_node(PlanNode("research", "task"))
    engine.plan_add_node(PlanNode("build", "task"))

    result = engine.schedule([
        TaskDemand("research", ["retrieval"], demand=1, priority=10),
        TaskDemand("build", ["python"], demand=1, priority=5),
    ])
    assert result.fully_scheduled
    pairs = {(x.task_id, x.resource_id) for x in result.assignments}
    assert pairs == {("research", "researcher"), ("build", "builder")}
    assert engine.graph.nodes["research"].owner == "researcher"
    assert engine.graph.nodes["build"].owner == "builder"

    mid = engine.snapshot.machine_id
    store.close()
    store = SQLiteStore(tmp_path / "sched.db")
    recovered = AASMEngine.resume(mid, store)
    assert {x["resource_id"] for x in recovered.list_resources()} == {"researcher", "builder"}
    assert recovered.last_schedule()["fully_scheduled"] is True
    assert recovered.graph.nodes["build"].owner == "builder"
    store.close()


def test_scheduler_exposes_capacity_bottleneck():
    engine = AASMEngine(ProblemSpec("capacity bottleneck"))
    engine.register_resource(ResourceRecord("verifier", "agent", ["verify"], capacity=1))
    result = engine.schedule([
        TaskDemand("verify-a", ["verify"], demand=1, priority=10),
        TaskDemand("verify-b", ["verify"], demand=1, priority=5),
    ])
    assert result.max_flow == 1
    assert sum(result.unmet.values()) == 1
    assert "verifier" in result.bottlenecks
    assert result.resource_utilization["verifier"] == 1.0


def test_scheduler_reports_missing_capability():
    engine = AASMEngine(ProblemSpec("missing capability"))
    engine.register_resource(ResourceRecord("coder", "agent", ["python"], capacity=1))
    result = engine.schedule([TaskDemand("sim", ["cfd"], demand=1)])
    assert result.max_flow == 0
    assert result.unmet["sim"] == 1
    assert "capability:sim" in result.bottlenecks


def test_resource_update_is_durable_and_changes_eligibility(tmp_path: Path):
    store = SQLiteStore(tmp_path / "resource.db")
    engine = AASMEngine(ProblemSpec("resource updates"), store=store)
    engine.register_resource(ResourceRecord("worker", "agent", ["python"], capacity=1, reliability=0.8))
    first = engine.schedule([TaskDemand("t", ["python"], min_reliability=0.9)])
    assert not first.fully_scheduled
    engine.update_resource("worker", {"reliability": 0.95, "capacity": 2})
    second = engine.schedule([TaskDemand("t", ["python"], min_reliability=0.9)])
    assert second.fully_scheduled
    mid = engine.snapshot.machine_id
    store.close()
    store = SQLiteStore(tmp_path / "resource.db")
    resumed = AASMEngine.resume(mid, store)
    worker = next(x for x in resumed.list_resources() if x["resource_id"] == "worker")
    assert worker["reliability"] == 0.95
    assert worker["capacity"] == 2
    store.close()


def test_historical_fork_has_only_resources_and_schedule_at_boundary(tmp_path: Path):
    store = SQLiteStore(tmp_path / "fork-sched.db")
    source = AASMEngine(ProblemSpec("fork scheduler"), store=store)
    source.register_resource(ResourceRecord("r1", "agent", ["x"], capacity=1))
    source.schedule([TaskDemand("t1", ["x"])])
    fork_at = source.events[-1].sequence
    source.register_resource(ResourceRecord("r2", "agent", ["y"], capacity=1))
    source.schedule([TaskDemand("t2", ["y"])])

    forked = source.fork(fork_at)
    assert [x["resource_id"] for x in forked.list_resources()] == ["r1"]
    assert forked.last_schedule()["assignments"][0]["task_id"] == "t1"
    assert "r2" not in {x["resource_id"] for x in forked.list_resources()}
    store.close()
