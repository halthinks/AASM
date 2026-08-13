from __future__ import annotations

from typing import Any

from ._scopes_model import *
from ._scopes_graph import *
from ._scopes_projection import *

def assert_scope_calculus_invariants(calculus: dict[str, Any]) -> None:
    state = normalize_calculus_scopes(calculus)
    scope_state = validate_scope_state(state["scope_state"])
    decisions = state.get("decisions", {})
    represented: set[str] = set()

    if state.get("active_model", {}) != state["scope_active_models"][ROOT_SCOPE_ID]:
        raise ValueError("legacy active_model must equal the root scope active model")

    for scope_id, model in state["scope_active_models"].items():
        scope_record = scope_state["records"][scope_id]
        if scope_record.get("status") not in {"ACTIVE", "NEEDS_REVALIDATION"} and model:
            raise ValueError(f"inactive scope {scope_id} retains an active model")
        inherited: dict[str, str] = {}
        if scope_id != ROOT_SCOPE_ID and scope_record.get("inheritance") != "ISOLATED":
            parent_id = scope_record.get("parent_scope_id")
            if parent_id:
                inherited = effective_scope_decisions(state, parent_id)
        for subject, decision_id in model.items():
            decision = decisions.get(decision_id)
            if decision is None:
                raise ValueError(
                    f"scope {scope_id} references unknown active decision {decision_id}"
                )
            if decision.get("status") != "ACTIVE":
                raise ValueError(
                    f"scope {scope_id} references non-active decision {decision_id}"
                )
            if decision.get("subject") != subject:
                raise ValueError(f"scope active-model subject mismatch for {decision_id}")
            if scope_id_from(decision) != scope_id:
                raise ValueError(f"decision {decision_id} is active in the wrong scope")
            if decision_id in represented:
                raise ValueError(
                    f"active decision {decision_id} appears in multiple scopes"
                )
            represented.add(decision_id)
            if subject in inherited and inherited[subject] != decision_id:
                if scope_record.get("override_policy") == "DENY":
                    raise ValueError(
                        f"scope {scope_id} denies override of inherited subject {subject}"
                    )
                if not bool((decision.get("scope") or {}).get("override")):
                    raise ValueError(
                        f"scope {scope_id} requires explicit override of inherited subject {subject}"
                    )

    unrepresented = sorted(
        decision_id
        for decision_id, decision in decisions.items()
        if decision.get("status") == "ACTIVE" and decision_id not in represented
    )
    if unrepresented:
        raise ValueError(
            f"active decisions are missing from scope models: {unrepresented}"
        )

    for collection in (
        "decisions",
        "obligations",
        "locks",
        "conflicts",
        "explanations",
        "constraints",
    ):
        for identity, record in state.get(collection, {}).items():
            scope_id = scope_id_from(record)
            if scope_id not in scope_state["records"]:
                raise ValueError(
                    f"{collection} record {identity} references unknown scope {scope_id}"
                )

    for decision_id, decision in decisions.items():
        target_scope = scope_id_from(decision)
        for parent_id in decision.get("parent_ids", []):
            parent = decisions.get(parent_id)
            if parent is None:
                continue
            source_scope = scope_id_from(parent)
            if not scope_flow_allowed(scope_state, source_scope, target_scope):
                raise ValueError(
                    f"decision {decision_id} has illegal cross-scope parent {parent_id}"
                )

__all__ = [name for name in globals() if not name.startswith("_")]
