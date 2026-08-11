from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any

from .persistence.memory import MemoryStore


@dataclass
class OperatorRunbookResult:
    """Machine-readable outcome from an executable operator drill."""

    runbook_id: str
    title: str
    status: str
    machine_id: str | None
    checks: dict[str, bool] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)
    evidence: list[dict[str, Any]] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.status == "PASS" and all(self.checks.values())

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["valid"] = self.valid
        return value


RUNBOOK_DEFINITIONS: dict[str, dict[str, str]] = {
    "lease-loss": {
        "title": "Recover after lease loss",
        "document": "docs/runbooks/lease-loss.md",
        "purpose": "Expire stale ownership, preserve the task, and reclaim it under a new lease.",
    },
    "requirement-change": {
        "title": "Inject a requirement without destroying the plan",
        "document": "docs/runbooks/requirement-change.md",
        "purpose": "Pause only the affected plan region and preserve unrelated work.",
    },
    "learned-no-good": {
        "title": "Inspect and act on a learned no-good",
        "document": "docs/runbooks/learned-no-good.md",
        "purpose": "Inspect certified blocking knowledge and confirm the failed model cannot recur.",
    },
    "human-approval": {
        "title": "Run a human approval gate with policy as data",
        "document": "docs/runbooks/human-approval.md",
        "purpose": "Deny an under-approved proposal and durably authorize it after quorum.",
    },
    "replay-fork": {
        "title": "Safely replay and fork a machine",
        "document": "docs/runbooks/replay-fork.md",
        "purpose": "Verify source history, replay exactly, and create a lineage-bearing fork.",
    },
    "unknown-effect": {
        "title": "Reconcile an UNKNOWN external effect",
        "document": "docs/runbooks/unknown-effect.md",
        "purpose": "Block unsafe retry and reconcile the externally observed outcome explicitly.",
    },
    "history-diagnosis": {
        "title": "Diagnose a failed durable-history verification",
        "document": "docs/runbooks/history-diagnosis.md",
        "purpose": "Identify concrete history issue codes without mutating the authoritative run.",
    },
}


def list_operator_runbooks() -> list[dict[str, str]]:
    return [
        {"runbook_id": runbook_id, **deepcopy(RUNBOOK_DEFINITIONS[runbook_id])}
        for runbook_id in sorted(RUNBOOK_DEFINITIONS)
    ]


def finish_runbook(
    runbook_id: str,
    *,
    machine_id: str | None,
    checks: dict[str, bool],
    summary: dict[str, Any],
    evidence: list[dict[str, Any]] | None = None,
) -> OperatorRunbookResult:
    return OperatorRunbookResult(
        runbook_id=runbook_id,
        title=RUNBOOK_DEFINITIONS[runbook_id]["title"],
        status="PASS" if checks and all(checks.values()) else "FAIL",
        machine_id=machine_id,
        checks=checks,
        summary=summary,
        evidence=list(evidence or []),
    )


def store_or_memory(store):
    return store if store is not None else MemoryStore()
