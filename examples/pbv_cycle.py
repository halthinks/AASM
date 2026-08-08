from aasm import (
    AASMEngine,
    BuilderOutput,
    PBVCoordinator,
    PlannerDirective,
    ProblemSpec,
    TeamMember,
    TeamRole,
)

engine=AASMEngine(ProblemSpec("Build and verify one change"))
engine.initialize_team([
    TeamMember("planner",TeamRole.PLANNER.value,["plan"]),
    TeamMember("builder",TeamRole.BUILDER.value,["code"]),
    TeamMember("verifier",TeamRole.VERIFIER.value,["verify"]),
])


def verifier(payload):
    tests=payload["builder_output"].get("tests",{})
    passed=bool(tests.get("passed"))
    return {
        "verifier_id":"verifier",
        "recommendation":PlannerDirective.CONTINUE.value if passed else PlannerDirective.REPAIR.value,
        "accepted":passed,
        "tests_passed":passed,
        "findings":[] if passed else ["tests failed"],
    }


def planner(payload):
    recommendation=payload["policy_recommendation"]
    return {
        "directive":recommendation,
        "reason":"accept verified result" if recommendation==PlannerDirective.CONTINUE.value else "repair before continuing",
    }

cycle=PBVCoordinator(engine,verifier,planner).process_builder_output(
    BuilderOutput("builder","task-1","implemented feature",tests={"passed":True})
)
print(cycle.to_dict())
print(engine.team_report())
