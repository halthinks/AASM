from __future__ import annotations

from copy import deepcopy
from typing import Any

from ._scopes_model import *
from ._scopes_graph import *

def normalize_scope_active_models(
    scope_state: dict[str, Any],
    raw: dict[str, dict[str, str]] | None,
    legacy_active_model: dict[str, str] | None = None,
) -> dict[str, dict[str, str]]:
    state = normalize_scope_state(scope_state)
    out: dict[str, dict[str, str]] = {
        scope_id: {} for scope_id in state["records"]
    }
    for scope_id, model in (raw or {}).items():
        if scope_id in out:
            out[scope_id] = {
                str(subject): str(decision_id)
                for subject, decision_id in (model or {}).items()
            }
    if legacy_active_model is not None:
        # Historical runtime methods update active_model directly. Treat that
        # compatibility projection as authoritative for root and resynchronize
        # scope_active_models during normalization.
        out[ROOT_SCOPE_ID] = {
            str(subject): str(decision_id)
            for subject, decision_id in legacy_active_model.items()
        }
    return out


def normalize_calculus_scopes(calculus: dict[str, Any]) -> dict[str, Any]:
    out = deepcopy(calculus)
    state = normalize_scope_state(out.get("scope_state"))
    models = normalize_scope_active_models(
        state,
        out.get("scope_active_models"),
        out.get("active_model"),
    )
    out["scope_state"] = state
    out["scope_active_models"] = models
    out["active_model"] = deepcopy(models[ROOT_SCOPE_ID])
    return out


def local_scope_model(calculus: dict[str, Any], scope_id: str) -> dict[str, str]:
    state = normalize_calculus_scopes(calculus)
    if scope_id not in state["scope_active_models"]:
        raise KeyError(scope_id)
    return deepcopy(state["scope_active_models"][scope_id])


def effective_scope_decisions(calculus: dict[str, Any], scope_id: str) -> dict[str, str]:
    state = normalize_calculus_scopes(calculus)
    scope_state = validate_scope_state(state["scope_state"])
    record = scope_state["records"].get(scope_id)
    if record is None:
        raise KeyError(scope_id)
    chain = inheritance_chain(scope_state, scope_id)
    out: dict[str, str] = {}
    for current_scope_id in chain:
        current = scope_state["records"][current_scope_id]
        if current.get("status") != "ACTIVE":
            continue
        out.update(state["scope_active_models"].get(current_scope_id, {}))
    return out


def effective_scope_values(calculus: dict[str, Any], scope_id: str) -> dict[str, Any]:
    state = normalize_calculus_scopes(calculus)
    decisions = state.get("decisions", {})
    out: dict[str, Any] = {}
    for subject, decision_id in effective_scope_decisions(state, scope_id).items():
        decision = decisions.get(decision_id)
        if decision is not None and decision.get("status") == "ACTIVE":
            out[subject] = decision.get("value")
    return out


scope_decision_values = effective_scope_values


def all_active_decision_ids(calculus: dict[str, Any]) -> set[str]:
    state = normalize_calculus_scopes(calculus)
    return {
        decision_id
        for model in state["scope_active_models"].values()
        for decision_id in model.values()
    }


def canonical_active_snapshot(calculus: dict[str, Any], scope_id: str) -> dict[str, str]:
    """Return the effective model keyed by each decision's owning scope.

    A child scope can see inherited decisions, but provenance must continue to
    identify the scope where each decision was actually made.  Using the
    observation scope for every key would make an inherited architecture
    decision look like a local implementation decision and would break
    explanation validation.
    """

    state = normalize_calculus_scopes(calculus)
    snapshot: dict[str, str] = {}
    for subject, decision_id in effective_scope_decisions(state, scope_id).items():
        decision = state.get("decisions", {}).get(decision_id)
        owner_scope_id = scope_id_from(decision) if decision is not None else scope_id
        snapshot[scoped_subject_key(owner_scope_id, subject)] = decision_id
    return snapshot


def dependency_impacted_scopes(
    scope_state: dict[str, Any],
    origin_scope_id: str,
) -> tuple[set[str], set[str]]:
    """Return scope subtrees to invalidate and scopes to revalidate."""

    state = validate_scope_state(scope_state)
    invalidate = set(scope_descendants(state, origin_scope_id))
    revalidate: set[str] = set()
    changed = True
    while changed:
        changed = False
        for dependency in state["dependencies"].values():
            upstream = str(dependency["upstream_scope_id"])
            downstream = str(dependency["downstream_scope_id"])
            if upstream not in invalidate and upstream not in revalidate:
                continue
            policy = dependency.get("invalidation_policy", "REVALIDATE")
            if policy == "INVALIDATE":
                addition = scope_descendants(state, downstream)
                if not addition.issubset(invalidate):
                    invalidate.update(addition)
                    changed = True
            elif (
                policy == "REVALIDATE"
                and downstream not in invalidate
                and downstream not in revalidate
            ):
                revalidate.add(downstream)
                changed = True
    revalidate.difference_update(invalidate)
    return invalidate, revalidate


def scope_object_counts(calculus: dict[str, Any], scope_id: str) -> dict[str, int]:
    def count(collection: str) -> int:
        return sum(
            1
            for record in calculus.get(collection, {}).values()
            if scope_id_from(record) == scope_id
        )

    return {
        "decisions": count("decisions"),
        "obligations": count("obligations"),
        "locks": count("locks"),
        "conflicts": count("conflicts"),
        "constraints": count("constraints"),
    }


def build_scope_report(calculus: dict[str, Any]) -> dict[str, Any]:
    state = normalize_calculus_scopes(calculus)
    scope_state = validate_scope_state(state["scope_state"])
    fairness_records = state.get("fairness", {}).get("records", {})
    obligations = state.get("obligations", {})
    rows: list[dict[str, Any]] = []
    for scope_id in sorted(scope_state["records"]):
        raw = deepcopy(scope_state["records"][scope_id])
        raw["local_active_model"] = deepcopy(
            state["scope_active_models"].get(scope_id, {})
        )
        raw["effective_active_model"] = effective_scope_decisions(state, scope_id)
        raw["effective_values"] = effective_scope_values(state, scope_id)
        raw["object_counts"] = scope_object_counts(state, scope_id)
        scoped_obligations = [
            obligation_id
            for obligation_id, obligation in obligations.items()
            if scope_id_from(obligation) == scope_id
        ]
        raw["fairness_debt"] = {
            "due": sorted(
                obligation_id
                for obligation_id in scoped_obligations
                if fairness_records.get(obligation_id, {}).get("fairness_status")
                == "DUE"
            ),
            "overdue": sorted(
                obligation_id
                for obligation_id in scoped_obligations
                if fairness_records.get(obligation_id, {}).get("fairness_status")
                == "OVERDUE"
            ),
        }
        raw["ancestor_scope_ids"] = scope_ancestors(
            scope_state, scope_id, include_self=False
        )
        raw["descendant_scope_ids"] = sorted(
            scope_descendants(scope_state, scope_id, include_self=False)
        )
        rows.append(raw)
    return {
        "contract_id": SCOPE_CONTRACT_ID,
        "contract_version": SCOPE_CONTRACT_VERSION,
        "schema_version": 1,
        "root_scope_id": ROOT_SCOPE_ID,
        "scopes": rows,
        "dependencies": [
            deepcopy(scope_state["dependencies"][dependency_id])
            for dependency_id in sorted(scope_state["dependencies"])
        ],
        "migration": deepcopy(scope_state["migration"]),
        "scope_count": len(rows),
        "dependency_count": len(scope_state["dependencies"]),
    }

__all__ = [name for name in globals() if not name.startswith("_")]
