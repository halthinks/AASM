from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from ._calculus_model import *
from ._calculus_logic import *
from .scopes import assert_scope_calculus_invariants, scope_id_from, with_scope


_OBLIGATION_SEMANTIC_LIST_FIELDS = (
    "dependencies",
    "decision_dependencies",
    "plan_node_ids",
    "required_evidence_types",
    "artifact_ids",
)


def obligation_identity_payload(record: ObligationRecord | Mapping[str, Any]) -> dict[str, Any]:
    """Return the stable semantic identity of an existing calculus obligation.

    The existing ObligationRecord owns lifecycle state. This projection binds the
    obligation's requirements and graph/application context while deliberately
    excluding mutable execution-progress fields such as status, evidence_ids,
    lock_ids, attempts, sequences, and disposition_reason.
    """
    row = record.to_dict() if isinstance(record, ObligationRecord) else deepcopy(dict(record))
    obligation_id = str(row.get("obligation_id") or "").strip()
    statement = str(row.get("statement") or "").strip()
    if not obligation_id or not statement:
        raise ValueError("obligation semantic identity requires obligation_id and statement")
    scope_id = scope_id_from(row)
    scope = with_scope(row.get("scope") if isinstance(row.get("scope"), dict) else {}, scope_id)
    payload = {
        "obligation_id": obligation_id,
        "statement": statement,
        "activation_condition": deepcopy(row.get("activation_condition") or {"const": True}),
        "persistent": bool(row.get("persistent", True)),
        "mandatory": bool(row.get("mandatory", True)),
        "scope": scope,
    }
    for field_name in _OBLIGATION_SEMANTIC_LIST_FIELDS:
        payload[field_name] = sorted({str(value) for value in (row.get(field_name) or [])})
    return payload


def obligation_fingerprint(record: ObligationRecord | Mapping[str, Any]) -> str:
    """Hash only the stable semantic projection of an existing obligation."""
    return content_hash(obligation_identity_payload(record))


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
