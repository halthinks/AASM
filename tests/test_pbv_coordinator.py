from aasm import (
    AASMEngine,
    BuilderOutput,
    PBVCoordinator,
    PlannerDirective,
    ProblemSpec,
    TeamMember,
    TeamRole,
)


def team():
    return [
        TeamMember("planner",TeamRole.PLANNER.value),
        TeamMember("builder",TeamRole.BUILDER.value),
        TeamMember("verifier",TeamRole.VERIFIER.value),
    ]


def test_coordinator_executes_builder_verifier_planner_handoff():
    e=AASMEngine(ProblemSpec("cycle")); e.initialize_team(team())
    def verifier(payload):
        assert payload["instruction"].startswith("Verify")
        return {"verifier_id":"verifier","recommendation":PlannerDirective.REPAIR.value,"accepted":False,"tests_passed":False,"findings":["unit test failed"]}
    def planner(payload):
        assert payload["policy_recommendation"]==PlannerDirective.REPAIR.value
        return {"directive":PlannerDirective.REPAIR.value,"reason":"repair before continuing"}
    result=PBVCoordinator(e,verifier,planner).process_builder_output(BuilderOutput("builder","t","implementation",tests={"passed":False}))
    assert result.planner_decision["directive"]==PlannerDirective.REPAIR.value
    assert e.team_task_directive("t")==PlannerDirective.REPAIR.value


def test_planner_can_override_verifier_without_losing_provenance():
    e=AASMEngine(ProblemSpec("override")); e.initialize_team(team())
    def verifier(payload):
        return {"verifier_id":"verifier","recommendation":PlannerDirective.INVESTIGATE.value,"accepted":False,"findings":["evidence incomplete"]}
    def planner(payload):
        return {"directive":PlannerDirective.PAUSE.value,"reason":"external dependency required"}
    result=PBVCoordinator(e,verifier,planner).process_builder_output(BuilderOutput("builder","t","partial"))
    assert result.verifier_report["recommendation"]==PlannerDirective.INVESTIGATE.value
    assert result.planner_decision["directive"]==PlannerDirective.PAUSE.value
    assert result.planner_decision["verifier_report_id"]==result.verifier_report["verifier_report_id"]
    assert e.team_report()["paused"] is True
