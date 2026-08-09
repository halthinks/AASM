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
    engine = AASMEngine(ProblemSpec("auto checkpoint"))
    _plan(engine); _team(engine)
    built = engine.submit_builder_output(BuilderOutput("builder", "b", "implemented"))
    verified = engine.submit_verifier_report(VerifierReport("verifier", "b", built["builder_output_id"], "REPAIR", accepted=False, tests_passed=False))
    trigger = engine.last_checkpoint_trigger()
    assert trigger["triggered"] is True
    assert trigger["verifier_report_id"] == verified["verifier_report_id"]
    assert engine.paused_tasks() == ["b", "c"]
    assert engine.last_impact()["signal"]["kind"] == "verification_failed"


def test_clean_verification_records_non_trigger_without_pausing_work():
    engine = AASMEngine(ProblemSpec("clean verification"))
    _plan(engine); _team(engine)
    built = engine.submit_builder_output(BuilderOutput("builder", "b", "implemented"))
    engine.submit_verifier_report(VerifierReport("verifier", "b", built["builder_output_id"], "CONTINUE", accepted=True, tests_passed=True))
    assert engine.last_checkpoint_trigger()["triggered"] is False
    assert engine.paused_tasks() == []
    assert engine.last_impact() is None


def test_pbv_planner_receives_automatic_checkpoint_and_can_resolve_part_of_it():
    engine = AASMEngine(ProblemSpec("planner checkpoint"))
    _plan(engine); _team(engine)
    seen = {}

    def verifier(payload):
        return VerifierReport("verifier", "b", payload["builder_output"]["builder_output_id"], "REPAIR", accepted=False, tests_passed=False)

    def planner(payload):
        seen.update(payload)
        impact_id = payload["change_control"]["last_impact"]["impact_id"]
        return PlannerDecision("planner", "b", "REPAIR", "repair b first", metadata={"resolve_impact": {"impact_id": impact_id, "resume_nodes": ["b"]}})

    PBVCoordinator(engine, verifier, planner).process_builder_output(BuilderOutput("builder", "b", "changed"))
    assert seen["automatic_checkpoint_trigger"]["triggered"] is True
    assert seen["change_control"]["last_impact"]["affected_nodes"] == ["b", "c"]
    assert engine.paused_tasks() == ["c"]
    assert engine.last_impact()["status"] == "PARTIAL"


def test_fleet_control_enforces_collaboration_recommendation_as_atomic_machine_quota(tmp_path):
    store = SQLiteStore(tmp_path / "fleet.db")
    engine = AASMEngine(ProblemSpec("fleet control"), store=store)
    engine.register_resource(ResourceRecord("pool", "agent", ["code"], capacity=5))
    engine.register_worker(WorkerRecord("w1", "pool")); engine.register_worker(WorkerRecord("w2", "pool"))
    engine.plan_add_node(PlanNode("a", "task")); engine.plan_add_node(PlanNode("b", "task")); engine.plan_add_edge(PlanEdge("a", "b"))
    tasks = [TaskDemand("a", ["code"]), TaskDemand("b", ["code"])]
    engine.schedule(tasks)
    fleet = engine.configure_fleet_control(FleetControlPolicy(enabled=True))
    assert fleet["admission_limit"] == 1
    first = engine.claim_task(tasks[0], "w1", lease_seconds=120)
    with pytest.raises(ValueError):
        engine.claim_task(tasks[1], "w2", lease_seconds=120)
    engine.complete_lease(first["lease_id"], result={"ok": True})
    second = engine.claim_task(tasks[1], "w2", lease_seconds=120)
    assert second["status"] == "ACTIVE"
    store.close()


def test_fleet_control_is_opt_in_and_does_not_provision_workers():
    engine = AASMEngine(ProblemSpec("fleet opt in"))
    report = engine.fleet_control_report()
    assert report["policy"]["enabled"] is False
    assert report["admission_limit"] is None


def test_remote_checkpoint_and_fleet_configuration_round_trip(tmp_path):
    database = str(tmp_path / "v16-remote.db")
    store = SQLiteStore(database)
    engine = AASMEngine(ProblemSpec("remote checkpoint fleet"), store=store)
    machine_id = engine.snapshot.machine_id
    store.close()
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(database, "secret"))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = AASMRemoteClient(f"http://127.0.0.1:{server.server_port}", "secret")
        assert client.health()["protocol"] == "aasm.remote.v1"
        client.configure_checkpoint_triggers(machine_id, CheckpointTriggerPolicy(on_blocking=False))
        assert client.checkpoint_triggers(machine_id)["policy"]["on_blocking"] is False
        client.configure_fleet_control(machine_id, FleetControlPolicy(enabled=True), refresh=False)
        assert client.fleet_control(machine_id)["policy"]["enabled"] is True
    finally:
        server.shutdown(); server.server_close()
