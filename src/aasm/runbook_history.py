from __future__ import annotations

from copy import deepcopy

from .assurance import check_history
from .model import ProblemSpec
from .runbook_common import OperatorRunbookResult, finish_runbook, store_or_memory
from .runtime_v25 import AASMEngine


def run_history_diagnosis(*, store=None) -> OperatorRunbookResult:
    """Diagnose a deliberately corrupted copy without touching canonical history."""

    store = store_or_memory(store)
    engine = AASMEngine(
        ProblemSpec("Diagnose a durable-history verification failure"),
        store=store,
    )
    engine.add_observation(
        "Canonical history remains unchanged while a copied stream is inspected.",
        source="operator-runbook",
    )
    healthy = engine.check_durable_history(persist=False)
    corrupted_events = deepcopy(engine.events)
    if len(corrupted_events) < 2:
        raise RuntimeError("diagnostic fixture did not produce enough events")
    corrupted_events[1].sequence = corrupted_events[0].sequence + 2
    corrupted = check_history(engine.snapshot, corrupted_events).to_dict()
    issue_codes = sorted({row["code"] for row in corrupted["issues"]})
    canonical_after = engine.check_durable_history(persist=False)
    checks = {
        "canonical_history_valid_before": healthy["valid"] is True,
        "copied_history_rejected": corrupted["valid"] is False,
        "sequence_gap_identified": "NON_CONTIGUOUS_SEQUENCE" in issue_codes,
        "canonical_history_not_mutated": canonical_after["valid"] is True,
        "machine_identity_retained": corrupted["machine_id"] == engine.snapshot.machine_id,
    }
    return finish_runbook(
        "history-diagnosis",
        machine_id=engine.snapshot.machine_id,
        checks=checks,
        summary={
            "healthy_report": healthy,
            "diagnostic_report": corrupted,
            "issue_codes": issue_codes,
            "operator_action": (
                "Stop mutation, preserve the authoritative store, identify the first "
                "bad sequence, and compare it with the last known-good backup or replica."
            ),
        },
        evidence=[
            {"kind": "history-issue", "code": code} for code in issue_codes
        ],
    )
