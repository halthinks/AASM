from __future__ import annotations

from typing import Callable

from .runbook_approval import run_human_approval
from .runbook_common import (
    RUNBOOK_DEFINITIONS,
    OperatorRunbookResult,
    list_operator_runbooks,
)
from .runbook_effect import run_unknown_effect
from .runbook_history import run_history_diagnosis
from .runbook_learning import run_learned_no_good
from .runbook_lease import run_lease_loss_recovery
from .runbook_replay import run_replay_fork
from .runbook_requirement import run_requirement_change


RUNBOOK_HANDLERS: dict[str, Callable[..., OperatorRunbookResult]] = {
    "lease-loss": run_lease_loss_recovery,
    "requirement-change": run_requirement_change,
    "learned-no-good": run_learned_no_good,
    "human-approval": run_human_approval,
    "replay-fork": run_replay_fork,
    "unknown-effect": run_unknown_effect,
    "history-diagnosis": run_history_diagnosis,
}


def execute_operator_runbook(
    runbook_id: str,
    *,
    store=None,
) -> OperatorRunbookResult:
    try:
        handler = RUNBOOK_HANDLERS[runbook_id]
    except KeyError:
        raise KeyError(
            f"unknown operator runbook {runbook_id!r}; "
            f"available={sorted(RUNBOOK_HANDLERS)}"
        ) from None
    return handler(store=store)


__all__ = [
    "RUNBOOK_DEFINITIONS",
    "OperatorRunbookResult",
    "RUNBOOK_HANDLERS",
    "list_operator_runbooks",
    "execute_operator_runbook",
    "run_lease_loss_recovery",
    "run_requirement_change",
    "run_learned_no_good",
    "run_human_approval",
    "run_replay_fork",
    "run_unknown_effect",
    "run_history_diagnosis",
]
