import pytest

from aasm import AASMEngine, PlannerDecision, PlannerDirective, ProblemSpec, TeamMember, TeamRole


def test_plan_interrupt_pruning_updates_graph_pruned_and_frontier_atomically():
    e=AASMEngine(ProblemSpec("pbv indexes"))
    e.initialize_team([TeamMember("planner",TeamRole.PLANNER.value)])
    e.planner_decide(PlannerDecision(
        "planner","seed",PlannerDirective.PLAN_INTERRUPT.value,"seed",
        plan_patch={"add_nodes":[{"node_id":"a","kind":"task"}]},
    ))
    e.snapshot.frontier=["a"]
    # Persist the frontier setup through the ordinary durable patch path.
    e.patch_snapshot({"frontier":["a"]},"seed frontier")
    e.planner_decide(PlannerDecision(
        "planner","a",PlannerDirective.PLAN_INTERRUPT.value,"prune invalid path",
        plan_patch={"prune_nodes":["a"]},
    ))
    assert "a" in e.snapshot.pruned
    assert "a" not in e.snapshot.frontier
    assert next(x for x in e.snapshot.graph["nodes"] if x["node_id"]=="a")["status"]=="pruned"


def test_team_cannot_be_silently_reinitialized():
    e=AASMEngine(ProblemSpec("team identity"))
    e.initialize_team([TeamMember("planner",TeamRole.PLANNER.value)])
    with pytest.raises(ValueError,match="already initialized"):
        e.initialize_team([TeamMember("other",TeamRole.PLANNER.value)])
