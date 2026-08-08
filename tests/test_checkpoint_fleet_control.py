import threading
from http.server import ThreadingHTTPServer

import pytest

from aasm import (
    AASMEngine,
    BuilderOutput,
    CheckpointTriggerPolicy,
    FleetControlPolicy,
    PBVCoordinator,
    PlanEdge,
    PlanNode,
    PlannerDecision,
    ProblemSpec,
    ResourceRecord,
    SQLiteStore,
    TaskDemand,
    TeamMember,
    VerifierReport,
    WorkerRecord,
)
from aasm.remote import AASMRemoteClient
from aasm.server import make_handler


def _team(engine):
    engine.initialize_team([
        TeamMember("planner", "PLANNER"),
        TeamMember("builder", "BUILDER"),
        TeamMember("verifier", "VERIFIER"),
    ])


def _plan(engine):
    engine.plan_add_node(PlanNode("b", "task"))
    engine.plan_add_node(PlanNode("c", "task"))
    engine.plan_add_edge(PlanEdge("b", "c"))


def test_failed_verification_automatically_opens_selective_checkpoint():
    e = AASMEngine(ProblemSpec("auto checkpoint"))
    _plan(e); _team(e)
    built = e.submit_builder_output(BuilderOutput("builder", "b", "implemented"))
    verified = e.submit_verifier_report(VerifierReport(
        "verifier", "b", built["builder_output_id"], "REPAIR",
        accepted=False, tests_passed=False,
    ))
    trigger = e.last_checkpoint_trigger()
    assert trigger["triggered"] is True
    assert trigger["verifier_report_id"] == verified["verifier_report_id"]
    assert e.paused_tasks() == ["b", "c"]
    assert e.last_impact()["signal"]["kind"] == "verification_failed"


def test_clean_verification_records_non_trigger_without_pausing_work():
    e = AASMEngine(ProblemSpec("clean verification"))
    _plan(e); _team(e)
    built = e.submit_builder_output(BuilderOutput("builder", "b", "implemented"))
    e.submit_verifier_report(VerifierReport(
        "verifier", "b", built["builder_output_id"], "CONTINUE",
        accepted=True, tests_passed=True,
    ))
    assert e.last_checkpoint_trigger()["triggered"] is False
    assert e.paused_tasks() == []
    assert e.last_impact() is None


def test_pbv_planner_receives_automatic_checkpoint_and_can_resolve_part_of_it():
    e = AASMEngine(ProblemSpec("planner checkpoint"))
    _plan(e); _team(e)
    seen = {}

    def verifier(payload):
        return VerifierReport("verifier", "b", payload["builder_output"]["builder_output_id"], "REPAIR", accepted=False, tests_passed=False)

    def planner(payload):
        seen.update(payload)
        impact_id = payload["change_control"]["last_impact"]["impact_id"]
        return PlannerDecision(
            "planner", "b", "REPAIR", "repair b first",
            metadata={"resolve_impact": {"impact_id": impact_id, "resume_nodes": ["b"]}},
        )

    PBVCoordinator(e, verifier, planner).process_builder_output(BuilderOutput("builder", "b", "changed"))
    assert seen["automatic_checkpoint_trigger"]["triggered"] is True
    assert seen["change_control"]["last_impact"]["affected_nodes"] == ["b", "c"]
    assert e.paused_tasks() == ["c"]
    assert e.last_impact()["status"] == "PARTIAL"


def test_requires_predecessor_must_complete_before_downstream_claim(tmp_path):
    store = SQLiteStore(tmp_path / "deps.db")
    e = AASMEngine(ProblemSpec("dependency claims"), store=store)
    e.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=2))
    e.register_worker(WorkerRecord("w1", "pool")); e.register_worker(WorkerRecord("w2", "pool"))
    e.plan_add_node(PlanNode("a", "task")); e.plan_add_node(PlanNode("b", "task")); e.plan_add_edge(PlanEdge("a", "b", relation="requires"))
    ta, tb = TaskDemand("a", ["code"]), TaskDemand("b", ["code"])
    with pytest.raises(ValueError, match="dependencies not complete"):
        e.claim_task(tb, "w2", lease_seconds=120)
    first = e.claim_task(ta, "w1", lease_seconds=120)
    with pytest.raises(ValueError, match="dependencies not complete"):
        e.claim_task(tb, "w2", lease_seconds=120)
    e.complete_lease(first["lease_id"], result={"ok": True})
    second = e.claim_task(tb, "w2", lease_seconds=120)
    assert second["status"] == "ACTIVE"
    store.close()


def test_fleet_control_enforces_admission_limit_as_atomic_machine_quota(tmp_path):
    store = SQLiteStore(tmp_path / "fleet.db")
    e = AASMEngine(ProblemSpec("fleet control"), store=store)
    e.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=5))
    e.register_worker(WorkerRecord("w1", "pool")); e.register_worker(WorkerRecord("w2", "pool"))
    e.plan_add_node(PlanNode("a", "task")); e.plan_add_node(PlanNode("b", "task"))
    tasks = [TaskDemand("a", ["code"]), TaskDemand("b", ["code"])]
    e.schedule(tasks)
    fleet = e.configure_fleet_control(FleetControlPolicy(enabled=True, ceiling_workers=1))
    assert fleet["admission_limit"] == 1
    first = e.claim_task(tasks[0], "w1", lease_seconds=120)
    with pytest.raises(ValueError, match="Quota exceeded"):
        e.claim_task(tasks[1], "w2", lease_seconds=120)
    e.complete_lease(first["lease_id"], result={"ok": True})
    second = e.claim_task(tasks[1], "w2", lease_seconds=120)
    assert second["status"] == "ACTIVE"
    store.close()


def test_fleet_control_is_opt_in_and_does_not_provision_workers():
    e = AASMEngine(ProblemSpec("fleet opt in"))
    report = e.fleet_control_report()
    assert report["policy"]["enabled"] is False
    assert report["admission_limit"] is None


def test_remote_checkpoint_and_fleet_configuration_round_trip(tmp_path):
    db = str(tmp_path / "v16-remote.db")
    store = SQLiteStore(db); e = AASMEngine(ProblemSpec("remote v16"), store=store); mid = e.snapshot.machine_id; store.close()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(db, "secret")); threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = AASMRemoteClient(f"http://127.0.0.1:{server.server_port}", "secret")
        assert client.health()["version"] == "0.16.0"
        client.configure_checkpoint_triggers(mid, CheckpointTriggerPolicy(on_blocking=False))
        assert client.checkpoint_triggers(mid)["policy"]["on_blocking"] is False
        client.configure_fleet_control(mid, FleetControlPolicy(enabled=True), refresh=False)
        assert client.fleet_control(mid)["policy"]["enabled"] is True
    finally:
        server.shutdown(); server.server_close()
