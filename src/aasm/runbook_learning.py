from __future__ import annotations

from copy import deepcopy

from .research_demo import run_research_synthesis_demo
from .runbook_common import OperatorRunbookResult, finish_runbook, store_or_memory


def run_learned_no_good(*, store=None) -> OperatorRunbookResult:
    """Inspect the canonical research conflict and its certified learned no-good."""

    store = store_or_memory(store)
    reference = run_research_synthesis_demo(store=store, mode="complete")
    engine = reference.engine
    calculus = engine.calculus_report()
    constraint = calculus["constraints"]["LC-retrieval-only"]
    conflict = calculus["conflicts"]["C-retrieval-only"]
    certificate = engine.snapshot.assurance_state["certificates"]["CERT-retrieval-only"]
    checks = {
        "conflict_resolved": conflict["status"] == "RESOLVED",
        "constraint_active": constraint["status"] == "ACTIVE",
        "constraint_hard": constraint["strength"] == "HARD",
        "certificate_verified": certificate["status"] == "VERIFIED",
        "failed_model_blocked": bool(reference.summary["repeat_failed_model_blocked"]),
        "causal_backjump_recorded": (
            reference.summary["backjump_target"] == "D-model-retrieval-only"
        ),
    }
    return finish_runbook(
        "learned-no-good",
        machine_id=engine.snapshot.machine_id,
        checks=checks,
        summary={
            "conflict_id": "C-retrieval-only",
            "constraint": deepcopy(constraint),
            "certificate": deepcopy(certificate),
            "backjump_target": reference.summary["backjump_target"],
            "invalidated_decisions": reference.summary["invalidated_decisions"],
            "operator_action": (
                "Treat the active hard constraint as durable blocking knowledge; "
                "inspect its explanation and certificate before changing policy."
            ),
        },
        evidence=[
            {
                "kind": "learned-constraint",
                "constraint_id": "LC-retrieval-only",
                "certificate_id": "CERT-retrieval-only",
            }
        ],
    )
