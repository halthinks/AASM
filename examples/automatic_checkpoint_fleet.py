from aasm import (
    AASMEngine,
    BuilderOutput,
    FleetControlPolicy,
    PlanEdge,
    PlanNode,
    ProblemSpec,
    ResourceRecord,
    TaskDemand,
    TeamMember,
    VerifierReport,
)

engine = AASMEngine(ProblemSpec("Automatic checkpoint + fleet-control demo"))
engine.plan_add_node(PlanNode("build", "task"))
engine.plan_add_node(PlanNode("integrate", "task"))
engine.plan_add_edge(PlanEdge("build", "integrate"))
engine.register_resource(ResourceRecord("workers", "agent", ["code"], capacity=8))
engine.schedule([TaskDemand("build", ["code"]), TaskDemand("integrate", ["code"])])
engine.configure_fleet_control(FleetControlPolicy(enabled=True))
engine.initialize_team([
    TeamMember("planner", "PLANNER"),
    TeamMember("builder", "BUILDER"),
    TeamMember("verifier", "VERIFIER"),
])

built = engine.submit_builder_output(BuilderOutput("builder", "build", "implementation complete"))
engine.submit_verifier_report(VerifierReport(
    "verifier",
    "build",
    built["builder_output_id"],
    "REPAIR",
    accepted=False,
    tests_passed=False,
))

print(engine.last_checkpoint_trigger())
print(engine.paused_tasks())
print(engine.fleet_control_report())
