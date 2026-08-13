from __future__ import annotations

from copy import deepcopy
from typing import Any

from ._calculus_model import *
from .scopes import *

def decision_values(
    calculus: dict[str, Any],
    active_model: dict[str, str] | None = None,
    *,
    scope_id: str = ROOT_SCOPE_ID,
) -> dict[str, Any]:
    state = normalize_calculus_state(calculus)
    if active_model is not None:
        decisions = state.get("decisions", {})
        out: dict[str, Any] = {}
        for subject, decision_id in active_model.items():
            record = decisions.get(decision_id)
            if record is not None and record.get("status") == "ACTIVE":
                out[subject] = record.get("value")
        return out
    return effective_scope_values(state, scope_id)


def literal_holds(literal: dict[str, Any], values: dict[str, Any]) -> bool:
    item = DecisionLiteral(**deepcopy(literal))
    if item.subject not in values:
        return False
    equal = values[item.subject] == item.value
    return equal if item.op == "EQ" else not equal


def condition_holds(condition: dict[str, Any] | None, values: dict[str, Any]) -> bool:
    if condition is None:
        return True
    if "const" in condition:
        return bool(condition["const"])
    if "decision" in condition:
        return literal_holds(condition["decision"], values)
    if "all" in condition:
        return all(condition_holds(item, values) for item in condition["all"])
    if "any" in condition:
        return any(condition_holds(item, values) for item in condition["any"])
    if "not" in condition:
        return not condition_holds(condition["not"], values)
    raise ValueError(f"unknown condition form: {sorted(condition)}")


def constraint_violated(constraint: dict[str, Any], values: dict[str, Any]) -> bool:
    if constraint.get("status") != "ACTIVE" or constraint.get("strength") != "HARD":
        return False
    return condition_holds(constraint.get("guard"), values) and all(
        literal_holds(literal, values) for literal in constraint.get("body", [])
    )


def violated_hard_constraints(
    calculus: dict[str, Any],
    values: dict[str, Any] | None = None,
) -> list[str]:
    state = normalize_calculus_state(calculus)
    violated: list[str] = []
    for constraint_id, constraint in state.get("constraints", {}).items():
        scope_id = scope_id_from(constraint)
        scoped_values = values if values is not None and scope_id == ROOT_SCOPE_ID else effective_scope_values(state, scope_id)
        if constraint_violated(constraint, scoped_values):
            violated.append(constraint_id)
    return sorted(violated)


def violated_hard_constraints_for_scope(
    calculus: dict[str, Any],
    scope_id: str,
) -> list[str]:
    state = normalize_calculus_state(calculus)
    values = effective_scope_values(state, scope_id)
    lineage = set(scope_ancestors(state["scope_state"], scope_id))
    return sorted(
        constraint_id
        for constraint_id, constraint in state.get("constraints", {}).items()
        if scope_id_from(constraint) in lineage and constraint_violated(constraint, values)
    )


def _literal_key(literal: dict[str, Any]) -> str:
    return canonical_json({"subject": literal["subject"], "op": literal["op"], "value": literal.get("value")})


def validate_explanation(calculus: dict[str, Any], explanation: dict[str, Any]) -> None:
    record = ExplanationRecord(**deepcopy(explanation))
    conflict = calculus.get("conflicts", {}).get(record.conflict_id)
    if conflict is None:
        raise KeyError(record.conflict_id)
    evidence = set(conflict.get("evidence_ids", []))
    if not set(record.evidence_ids).issubset(evidence):
        raise ValueError("explanation evidence must be drawn from its conflict")
    seen: dict[str, str] = {}
    snapshot = conflict.get("active_model_snapshot", {})
    decisions = calculus.get("decisions", {})
    for raw in record.assumption_literals:
        literal = DecisionLiteral(**raw)
        if literal.decision_id is None:
            raise ValueError("explanation literals require decision_id provenance")
        decision = decisions.get(literal.decision_id)
        if decision is None:
            raise KeyError(literal.decision_id)
        literal_scope_id = scope_id_from(decision)
        snapshot_decision_id = snapshot.get(scoped_subject_key(literal_scope_id, literal.subject))
        if snapshot_decision_id is None and literal_scope_id == ROOT_SCOPE_ID:
            snapshot_decision_id = snapshot.get(literal.subject)
        if snapshot_decision_id != literal.decision_id:
            raise ValueError("explanation literal was not active in the conflict snapshot")
        if decision.get("subject") != literal.subject or decision.get("value") != literal.value:
            raise ValueError("explanation literal does not match its decision")
        if literal.op != "EQ":
            raise ValueError("conflict explanations must name active assignment literals with EQ")
        prior = seen.get(literal.subject)
        key = _literal_key(raw)
        if prior is not None and prior != key:
            raise ValueError("explanation contains contradictory literals for one subject")
        seen[literal.subject] = key
    if record.status == "PROVEN" and not record.certificate:
        raise ValueError("PROVEN explanation requires a certificate")


def project_constraint(
    calculus: dict[str, Any],
    explanation: dict[str, Any],
    constraint_id: str,
    *,
    requested_strength: str = "HARD",
    created_sequence: int = 0,
) -> dict[str, Any]:
    validate_explanation(calculus, explanation)
    conflict = calculus["conflicts"][explanation["conflict_id"]]
    status = explanation.get("status")
    hard_allowed = (
        conflict.get("kind") == "ASSUMPTION_CONFLICT"
        and status in {"VALIDATED", "PROVEN"}
    )
    strength = "HARD" if requested_strength == "HARD" and hard_allowed else "SOFT"
    validation = "PROVEN" if status == "PROVEN" else ("VALIDATED" if status == "VALIDATED" else "HEURISTIC")
    body = sorted(
        [DecisionLiteral(**raw).to_dict() for raw in explanation.get("assumption_literals", [])],
        key=_literal_key,
    )
    record = LearnedConstraint(
        constraint_id=constraint_id,
        body=body,
        guard=deepcopy(explanation.get("guard") or {"const": True}),
        strength=strength,
        status="ACTIVE" if strength == "HARD" else "SOFT",
        validation=validation,
        source_conflict_id=explanation["conflict_id"],
        source_explanation_id=explanation["explanation_id"],
        evidence_ids=list(explanation.get("evidence_ids", [])),
        scope=deepcopy(explanation.get("scope") or {}),
        created_sequence=created_sequence,
    )
    return record.to_dict()


def _active_decision_children(calculus: dict[str, Any]) -> dict[str, set[str]]:
    children: dict[str, set[str]] = {decision_id: set() for decision_id in calculus.get("decisions", {})}
    for decision_id, decision in calculus.get("decisions", {}).items():
        if decision.get("status") != "ACTIVE":
            continue
        for parent_id in decision.get("parent_ids", []):
            children.setdefault(parent_id, set()).add(decision_id)
    for edge in calculus.get("decision_edges", []):
        if edge.get("relation") in {"DEPENDS_ON", "DERIVES"}:
            children.setdefault(edge.get("src"), set()).add(edge.get("dst"))
    return children


def decision_descendants(calculus: dict[str, Any], root_id: str) -> set[str]:
    children = _active_decision_children(calculus)
    seen = {root_id}
    todo = [root_id]
    while todo:
        current = todo.pop()
        for child in children.get(current, set()):
            if child not in seen:
                seen.add(child)
                todo.append(child)
    return seen


def causal_roots(calculus: dict[str, Any], decision_id: str) -> set[str]:
    decisions = calculus.get("decisions", {})
    seen: set[str] = set()

    def visit(current_id: str) -> set[str]:
        if current_id in seen:
            return set()
        seen.add(current_id)
        current = decisions.get(current_id)
        if current is None:
            return set()
        parents = [parent for parent in current.get("parent_ids", []) if parent in decisions]
        if current.get("kind") != "DERIVED" or not parents:
            return {current_id}
        roots: set[str] = set()
        for parent in parents:
            roots.update(visit(parent))
        return roots

    return visit(decision_id)


def compute_backjump(calculus: dict[str, Any], conflict_id: str, explanation_id: str | None = None) -> dict[str, Any]:
    conflict = calculus.get("conflicts", {}).get(conflict_id)
    if conflict is None:
        raise KeyError(conflict_id)
    if explanation_id is None:
        candidates = [
            item for item in conflict.get("explanation_ids", [])
            if calculus.get("explanations", {}).get(item, {}).get("status") in {"VALIDATED", "PROVEN"}
        ]
        if not candidates:
            raise ValueError("backjump requires a validated explanation")
        explanation_id = sorted(candidates)[0]
    explanation = calculus.get("explanations", {}).get(explanation_id)
    if explanation is None:
        raise KeyError(explanation_id)
    validate_explanation(calculus, explanation)

    root_ids: set[str] = set()
    for literal in explanation.get("assumption_literals", []):
        root_ids.update(causal_roots(calculus, literal["decision_id"]))
    decisions = calculus.get("decisions", {})
    revisable = [
        decision_id for decision_id in root_ids
        if decision_id in decisions
        and decisions[decision_id].get("status") == "ACTIVE"
        and not decisions[decision_id].get("pinned", False)
        and decisions[decision_id].get("kind") not in {"ROOT", "PINNED"}
    ]
    if not revisable:
        return {
            "conflict_id": conflict_id,
            "explanation_id": explanation_id,
            "pivot_decision_id": None,
            "invalidated_decision_ids": [],
            "impacted_obligation_ids": [],
            "impacted_plan_node_ids": [],
            "reason": "no revisable causal pivot",
        }

    closures = {decision_id: decision_descendants(calculus, decision_id) for decision_id in revisable}
    pivot = sorted(
        revisable,
        key=lambda decision_id: (
            -int(decisions[decision_id].get("level", 0)),
            len(closures[decision_id]),
            decision_id,
        ),
    )[0]
    invalidated = closures[pivot]
    obligations = calculus.get("obligations", {})
    impacted_obligations = sorted(
        obligation_id
        for obligation_id, obligation in obligations.items()
        if set(obligation.get("decision_dependencies", [])) & invalidated
    )
    plan_nodes: set[str] = set(decisions[pivot].get("plan_node_ids", []))
    for decision_id in invalidated:
        plan_nodes.update(decisions.get(decision_id, {}).get("plan_node_ids", []))
    for obligation_id in impacted_obligations:
        plan_nodes.update(obligations[obligation_id].get("plan_node_ids", []))
    return {
        "conflict_id": conflict_id,
        "explanation_id": explanation_id,
        "pivot_decision_id": pivot,
        "invalidated_decision_ids": sorted(invalidated),
        "impacted_obligation_ids": impacted_obligations,
        "impacted_plan_node_ids": sorted(plan_nodes),
        "reason": "deepest revisable causal pivot with smallest dependent closure",
    }


def apply_backjump(calculus: dict[str, Any], plan: dict[str, Any], *, sequence: int = 0) -> dict[str, Any]:
    out = normalize_calculus_state(calculus)
    conflict = out["conflicts"][plan["conflict_id"]]
    invalidated = set(plan.get("invalidated_decision_ids", []))
    for decision_id in invalidated:
        decision = out["decisions"][decision_id]
        decision["status"] = "INVALIDATED"
        decision["invalidated_by_conflict_id"] = plan["conflict_id"]
    for scope_id, model in out.get("scope_active_models", {}).items():
        out["scope_active_models"][scope_id] = {
            subject: decision_id
            for subject, decision_id in model.items()
            if decision_id not in invalidated
        }
    out["active_model"] = deepcopy(out["scope_active_models"].get(ROOT_SCOPE_ID, {}))
    for obligation_id in plan.get("impacted_obligation_ids", []):
        obligation = out["obligations"][obligation_id]
        if obligation.get("status") not in {"REJECTED", "SUPERSEDED", "IMPOSSIBLE"}:
            obligation["status"] = "NEEDS_REVALIDATION"
            obligation["last_state_change_sequence"] = sequence
    conflict["status"] = "RESOLVED"
    conflict["resolved_sequence"] = sequence
    conflict["backjump"] = deepcopy(plan)
    out["epoch"] = int(out.get("epoch", 0)) + 1
    out["search_local"] = {}
    return out


def reevaluate_locks(calculus: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    out = normalize_calculus_state(calculus)
    broken: list[str] = []
    for lock_id, lock in out.get("locks", {}).items():
        if lock.get("status") != "ACTIVE":
            continue
        values = effective_scope_values(out, scope_id_from(lock))
        if not condition_holds(lock.get("condition"), values):
            lock["status"] = "BROKEN"
            lock["broken_epoch"] = int(out.get("epoch", 0))
            broken.append(lock_id)
    for obligation in out.get("obligations", {}).values():
        active_locks = [
            lock_id for lock_id in obligation.get("lock_ids", [])
            if out.get("locks", {}).get(lock_id, {}).get("status") == "ACTIVE"
        ]
        if obligation.get("status") == "LOCKED" and not active_locks:
            obligation["status"] = "AVAILABLE"
    return out, sorted(broken)


def audit_fairness(calculus: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[str]]]:
    out = normalize_calculus_state(calculus)
    epoch = int(out.get("epoch", 0))
    policy = FairnessPolicy(**deepcopy(out["fairness"]["policy"]))
    records = out["fairness"].setdefault("records", {})
    values = decision_values(out)
    due: list[str] = []
    overdue: list[str] = []
    for obligation_id, obligation in out.get("obligations", {}).items():
        record = records.setdefault(
            obligation_id,
            {
                "created_epoch": epoch,
                "last_considered_epoch": epoch,
                "last_enabled_epoch": None,
                "last_reviewed_epoch": None,
                "current_lock_start_epoch": None,
                "lock_count": 0,
                "hidden_epochs": 0,
                "continuous_lock_epochs": 0,
                "fairness_status": "NORMAL",
                "explicit_deferral_until_epoch": None,
            },
        )
        if obligation.get("status") in TERMINAL_OBLIGATION_STATUSES or not obligation.get("persistent", True):
            record["fairness_status"] = "NORMAL"
            continue
        if obligation.get("status") in {"ENABLED", "IN_PROGRESS", "VERIFYING", "VERIFIED", "COMMITTED"}:
            record["last_enabled_epoch"] = epoch
            record["last_considered_epoch"] = epoch
            record["hidden_epochs"] = 0
            record["fairness_status"] = "NORMAL"
            continue
        active_locks = [
            lock_id for lock_id in obligation.get("lock_ids", [])
            if out.get("locks", {}).get(lock_id, {}).get("status") == "ACTIVE"
        ]
        if active_locks:
            starts = [int(out["locks"][lock_id].get("created_epoch", epoch)) for lock_id in active_locks]
            record["current_lock_start_epoch"] = min(starts)
            record["continuous_lock_epochs"] = epoch - record["current_lock_start_epoch"]
            record["lock_count"] = max(int(record.get("lock_count", 0)), len(obligation.get("lock_ids", [])))
        else:
            record["current_lock_start_epoch"] = None
            record["continuous_lock_epochs"] = 0
        record["hidden_epochs"] = epoch - int(record.get("last_considered_epoch", record["created_epoch"]))
        deferred_until = record.get("explicit_deferral_until_epoch")
        if deferred_until is not None and epoch <= int(deferred_until):
            record["fairness_status"] = "NORMAL"
            continue
        score_due = (
            record["hidden_epochs"] >= policy.max_hidden_epochs
            or record["continuous_lock_epochs"] >= policy.max_lock_age_epochs
            or record["lock_count"] >= policy.max_lock_count
        )
        score_overdue = (
            record["hidden_epochs"] > policy.max_hidden_epochs
            or record["continuous_lock_epochs"] > policy.max_lock_age_epochs
            or record["lock_count"] > policy.max_lock_count
        )
        if score_overdue:
            record["fairness_status"] = "OVERDUE"
            overdue.append(obligation_id)
        elif score_due:
            record["fairness_status"] = "DUE"
            due.append(obligation_id)
        else:
            record["fairness_status"] = "NORMAL"
    return out, {"due": sorted(due), "overdue": sorted(overdue)}


def candidate_exposes_overdue(
    calculus: dict[str, Any],
    values: dict[str, Any],
    *,
    previous_values: dict[str, Any] | None = None,
) -> bool:
    overdue = [
        obligation_id for obligation_id, record in calculus.get("fairness", {}).get("records", {}).items()
        if record.get("fairness_status") == "OVERDUE"
    ]
    if not overdue:
        return True
    previous_values = previous_values or {}
    for obligation_id in overdue:
        obligation = calculus.get("obligations", {}).get(obligation_id, {})
        scope_id = scope_id_from(obligation)
        scoped_values = values if scope_id == ROOT_SCOPE_ID else effective_scope_values(calculus, scope_id)
        scoped_previous = previous_values if scope_id == ROOT_SCOPE_ID else {}
        now_exposed = condition_holds(obligation.get("activation_condition"), scoped_values)
        already_exposed = condition_holds(obligation.get("activation_condition"), scoped_previous)
        if now_exposed and not already_exposed:
            return True
    return False

__all__ = [name for name in globals() if not name.startswith("_")]
