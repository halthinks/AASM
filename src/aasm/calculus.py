from __future__ import annotations

from typing import Any

from ._calculus_model import *
from ._calculus_logic import *
from .scopes import assert_scope_calculus_invariants

def assert_calculus_invariants(calculus: dict[str, Any]) -> None:
    state = normalize_calculus_state(calculus)
    decisions = state["decisions"]
    for subject, decision_id in state["active_model"].items():
        decision = decisions.get(decision_id)
        if decision is None:
            raise ValueError(f"active model references unknown decision: {decision_id}")
        if decision.get("status") != "ACTIVE":
            raise ValueError(f"active model references non-active decision: {decision_id}")
        if decision.get("subject") != subject:
            raise ValueError(f"active model subject mismatch for {decision_id}")
    violations = violated_hard_constraints(state)
    unresolved = []
    for constraint_id in violations:
        constraint = state["constraints"][constraint_id]
        conflict = state["conflicts"].get(constraint.get("source_conflict_id"), {})
        if conflict.get("status") not in {"OPEN", "EXPLAINED", "LEARNED"}:
            unresolved.append(constraint_id)
    if unresolved:
        raise ValueError(f"active model violates hard constraints without an unresolved source conflict: {unresolved}")
    for lock_id, lock in state["locks"].items():
        if lock.get("obligation_id") not in state["obligations"]:
            raise ValueError(f"lock {lock_id} references unknown obligation")
        if lock.get("origin_decision_id") not in decisions:
            raise ValueError(f"lock {lock_id} references unknown decision")
    for constraint_id, constraint in state["constraints"].items():
        if constraint.get("strength") == "HARD" and constraint.get("status") == "ACTIVE":
            if constraint.get("validation") not in {"VALIDATED", "PROVEN"}:
                raise ValueError(f"hard constraint {constraint_id} lacks validated provenance")
            if constraint.get("source_explanation_id") not in state["explanations"]:
                raise ValueError(f"constraint {constraint_id} references unknown explanation")
            if constraint.get("source_conflict_id") not in state["conflicts"]:
                raise ValueError(f"constraint {constraint_id} references unknown conflict")

    assert_scope_calculus_invariants(state)

    scope_state = validate_scope_state(state.get("scope_state") or {})
    unresolved_scoped: list[str] = []
    for scope_id in scope_state["records"]:
        for constraint_id in violated_hard_constraints_for_scope(state, scope_id):
            constraint = state["constraints"][constraint_id]
            conflict = state["conflicts"].get(constraint.get("source_conflict_id"), {})
            if conflict.get("status") not in {"OPEN", "EXPLAINED", "LEARNED"}:
                unresolved_scoped.append(f"{scope_id}:{constraint_id}")
    if unresolved_scoped:
        raise ValueError(
            "scope models violate hard constraints without unresolved source conflicts: "
            f"{sorted(unresolved_scoped)}"
        )


__all__ = [name for name in globals() if not name.startswith("_")]
