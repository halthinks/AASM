from __future__ import annotations

from .graph import PlanEdge, PlanNode
from .model import ProblemSpec
from .runbook_common import OperatorRunbookResult, finish_runbook, store_or_memory
from .runtime_v25 import AASMEngine


def run_requirement_change(*, store=None) -> OperatorRunbookResult:
    """Exercise selective steering over an existing plan graph."""

    store = store_or_memory(store)
    engine = AASMEngine(
        ProblemSpec("Inject a requirement while preserving unrelated work"),
        store=store,
    )
    engine.plan_add_node(PlanNode("design-core", "design", status="in_progress"))
    engine.plan_add_node(PlanNode("update-tests", "verification", status="pending"))
    engine.plan_add_node(PlanNode("publish-notes", "documentation", status="complete"))
    engine.plan_add_edge(PlanEdge("design-core", "update-tests"))
    response = engine.user_interrupt(
        "Require deterministic serialization for the core design.",
        metadata={
            "seed_nodes": ["design-core"],
            "requirement_id": "REQ-deterministic-serialization",
        },
    )
    impact = response["impact"]
    affected = set(impact["affected_nodes"])
    unaffected = set(impact["unaffected_nodes"])
    paused_before_resolution = set(engine.paused_tasks())
    resolved = engine.resolve_change_impact(
        "operator",
        impact["impact_id"],
        resume_nodes=impact["affected_nodes"],
        retire_nodes=[],
        reason="operator accepted the additive requirement and resumed affected work",
    )
    node_status = {
        row["node_id"]: row["status"] for row in engine.snapshot.graph.get("nodes", [])
    }
    checks = {
        "dependent_region_identified": affected == {"design-core", "update-tests"},
        "unrelated_work_preserved": "publish-notes" in unaffected,
        "only_affected_region_paused": paused_before_resolution == affected,
        "impact_resolved": resolved["status"] == "RESOLVED",
        "unrelated_completion_retained": node_status["publish-notes"] == "complete",
        "plan_resumed": engine.paused_tasks() == [],
    }
    return finish_runbook(
        "requirement-change",
        machine_id=engine.snapshot.machine_id,
        checks=checks,
        summary={
            "requirement_id": "REQ-deterministic-serialization",
            "impact_id": impact["impact_id"],
            "affected_nodes": sorted(affected),
            "unaffected_nodes": sorted(unaffected),
            "resolution": resolved,
        },
        evidence=[
            {
                "kind": "change-impact",
                "impact_id": impact["impact_id"],
                "affected_nodes": sorted(affected),
            }
        ],
    )
