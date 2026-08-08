from pathlib import Path
import threading

import pytest

from aasm import (
    AASMEngine,
    AASMRemoteClient,
    BuilderOutput,
    PlannerDecision,
    PlannerDirective,
    ProblemSpec,
    SQLiteStore,
    TeamMember,
    TeamRole,
    VerifierReport,
)


def members():
    return [
        TeamMember("planner",TeamRole.PLANNER.value,["plan"]),
        TeamMember("builder",TeamRole.BUILDER.value,["code"]),
        TeamMember("verifier",TeamRole.VERIFIER.value,["verify"]),
    ]


def test_builder_and_verifier_cannot_mutate_authoritative_plan():
    e=AASMEngine(ProblemSpec("pbv ownership")); e.initialize_team(members())
    with pytest.raises(PermissionError):
        e.planner_decide(PlannerDecision("builder","t",PlannerDirective.CONTINUE.value,"builder tried"))
    with pytest.raises(PermissionError):
        e.planner_decide(PlannerDecision("verifier","t",PlannerDirective.CONTINUE.value,"verifier tried"))


def test_builder_verifier_planner_round_trip_and_plan_interrupt():
    e=AASMEngine(ProblemSpec("pbv round trip")); e.initialize_team(members())
    out=e.submit_builder_output(BuilderOutput("builder","task-1","implemented",tests={"passed":False}))
    report=e.submit_verifier_report(VerifierReport("verifier","task-1",out["builder_output_id"],PlannerDirective.REPAIR.value,accepted=False,tests_passed=False,findings=["test failed"]))
    assert report["policy_recommendation"]==PlannerDirective.REPAIR.value
    decision=e.planner_decide(PlannerDecision("planner","task-1",PlannerDirective.REPAIR.value,"repair failing test",report["verifier_report_id"]))
    assert decision["plan_revision_after"]==1
    assert e.team_task_directive("task-1")==PlannerDirective.REPAIR.value

    interrupt=e.planner_decide(PlannerDecision(
        "planner","task-1",PlannerDirective.PLAN_INTERRUPT.value,"new dependency discovered",report["verifier_report_id"],
        plan_patch={"add_nodes":[{"node_id":"repair-node","kind":"repair","payload":{"why":"new dependency"}}]},
    ))
    assert interrupt["plan_revision_before"]==1 and interrupt["plan_revision_after"]==2
    assert e.snapshot.graph["nodes"][0]["node_id"]=="repair-node"
    assert e.team_report()["paused"] is True
    e.planner_resume("planner","task-1")
    assert e.team_report()["paused"] is False


def test_verifier_recommends_interrupt_on_changed_assumption_but_planner_authorizes():
    e=AASMEngine(ProblemSpec("unexpected")); e.initialize_team(members())
    out=e.submit_builder_output(BuilderOutput("builder","t","unexpected output"))
    report=e.submit_verifier_report(VerifierReport("verifier","t",out["builder_output_id"],PlannerDirective.INVESTIGATE.value,assumption_changed=True,unexpected_output=True))
    assert report["policy_recommendation"]==PlannerDirective.PLAN_INTERRUPT.value
    # A recommendation is not plan authority; revision is unchanged until Planner acts.
    assert e.team_report()["plan_revision"]==1


def test_invalid_plan_interrupt_is_atomic():
    e=AASMEngine(ProblemSpec("atomic interrupt")); e.initialize_team(members())
    e.planner_decide(PlannerDecision("planner","seed",PlannerDirective.PLAN_INTERRUPT.value,"seed plan",plan_patch={"add_nodes":[{"node_id":"a","kind":"task"},{"node_id":"b","kind":"task"}],"add_edges":[{"src":"a","dst":"b"}]}))
    before=e.snapshot.canonical_hash(); revision=e.team_report()["plan_revision"]
    with pytest.raises(ValueError,match="cycle"):
        e.planner_decide(PlannerDecision("planner","seed",PlannerDirective.PLAN_INTERRUPT.value,"bad cycle",plan_patch={"add_edges":[{"src":"b","dst":"a"}]}))
    assert e.snapshot.canonical_hash()==before
    assert e.team_report()["plan_revision"]==revision


def test_team_protocol_persists_across_restart(tmp_path:Path):
    db=tmp_path/"team.db"; store=SQLiteStore(db); e=AASMEngine(ProblemSpec("restart"),store=store); e.initialize_team(members())
    out=e.submit_builder_output(BuilderOutput("builder","t","done")); report=e.submit_verifier_report(VerifierReport("verifier","t",out["builder_output_id"],PlannerDirective.CONTINUE.value,accepted=True,tests_passed=True)); e.planner_decide(PlannerDecision("planner","t",PlannerDirective.CONTINUE.value,"verified",report["verifier_report_id"])); mid=e.snapshot.machine_id; store.close()
    store=SQLiteStore(db); resumed=AASMEngine.resume(mid,store); assert resumed.team_report()["planner_id"]=="planner"; assert resumed.team_task_directive("t")==PlannerDirective.CONTINUE.value; store.close()


def test_remote_pbv_round_trip(tmp_path:Path):
    from http.server import ThreadingHTTPServer
    from aasm.server import make_handler
    db=str(tmp_path/"remote-team.db"); store=SQLiteStore(db); e=AASMEngine(ProblemSpec("remote pbv"),store=store); mid=e.snapshot.machine_id; store.close()
    server=ThreadingHTTPServer(("127.0.0.1",0),make_handler(db,"secret")); threading.Thread(target=server.serve_forever,daemon=True).start()
    try:
        c=AASMRemoteClient(f"http://127.0.0.1:{server.server_port}","secret")
        c.initialize_team(mid,members())
        out=c.builder_output(mid,BuilderOutput("builder","t","built"))
        rep=c.verifier_report(mid,VerifierReport("verifier","t",out["builder_output_id"],PlannerDirective.CONTINUE.value,accepted=True,tests_passed=True))
        dec=c.planner_decision(mid,PlannerDecision("planner","t",PlannerDirective.CONTINUE.value,"verified",rep["verifier_report_id"]))
        assert dec["directive"]==PlannerDirective.CONTINUE.value
        assert c.team(mid)["latest_decision"]["directive"]==PlannerDirective.CONTINUE.value
    finally:
        server.shutdown(); server.server_close()
