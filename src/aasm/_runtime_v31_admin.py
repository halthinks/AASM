from __future__ import annotations

from copy import deepcopy
from typing import Any

from .calculus import (
    ConflictRecord,
    DecisionRecord,
    ExplanationRecord,
    FairnessPolicy,
    LockRecord,
    ObligationRecord,
    OBLIGATION_TRANSITIONS,
    apply_backjump,
    audit_fairness,
    candidate_exposes_overdue,
    canonical_json,
    condition_holds,
    compute_backjump,
    decision_descendants,
    decision_values,
    normalize_calculus_state,
    reevaluate_locks,
    validate_explanation,
    violated_hard_constraints,
    violated_hard_constraints_for_scope,
)
from .domain_adapters import CandidateModel, CandidateValidationReport
from .evidence import EvidenceRecord
from .runtime_v30 import AASMEngine as V30Engine, default_profile_registry
from .scopes import (
    ROOT_SCOPE_ID,
    SCOPE_CONTRACT_ID,
    SCOPE_CONTRACT_VERSION,
    DecisionScope,
    ScopeDependency,
    build_scope_report,
    canonical_active_snapshot,
    dependency_impacted_scopes,
    effective_scope_decisions,
    effective_scope_values,
    local_scope_model,
    normalize_scope_active_models,
    normalize_scope_state,
    scope_ancestors,
    scope_depth,
    scope_descendants,
    scope_flow_allowed,
    scope_id_from,
    scoped_subject_key,
    validate_scope_state,
    with_scope,
)


class ScopeAdminMixin:
    def register_scope(
        self,
        scope: DecisionScope | dict[str, Any],
        *,
        reason: str = "decision scope registered",
    ) -> dict[str, Any]:
        state = self._begin_calculus()
        item = scope if isinstance(scope, DecisionScope) else DecisionScope(**deepcopy(scope))
        if item.scope_id == ROOT_SCOPE_ID:
            raise ValueError("the canonical root scope already exists")
        scope_state = normalize_scope_state(state.get("scope_state"))
        if item.scope_id in scope_state["records"]:
            raise ValueError(f"scope already exists: {item.scope_id}")
        if item.parent_scope_id not in scope_state["records"]:
            raise KeyError(item.parent_scope_id)
        if scope_state["records"][item.parent_scope_id].get("status") != "ACTIVE":
            raise ValueError("a new scope requires an active parent")
        item.created_sequence = self._sequence() + 1
        scope_state["records"][item.scope_id] = item.to_dict()
        validate_scope_state(scope_state)
        state["scope_state"] = scope_state
        state["scope_active_models"].setdefault(item.scope_id, {})
        self._commit_calculus(state, reason)
        return deepcopy(state["scope_state"]["records"][item.scope_id])

    def register_scope_dependency(
        self,
        dependency: ScopeDependency | dict[str, Any],
        *,
        reason: str = "scope dependency registered",
    ) -> dict[str, Any]:
        state = self._begin_calculus()
        item = (
            dependency
            if isinstance(dependency, ScopeDependency)
            else ScopeDependency(**deepcopy(dependency))
        )
        scope_state = normalize_scope_state(state.get("scope_state"))
        if item.dependency_id in scope_state["dependencies"]:
            raise ValueError(f"scope dependency already exists: {item.dependency_id}")
        if item.upstream_scope_id not in scope_state["records"]:
            raise KeyError(item.upstream_scope_id)
        if item.downstream_scope_id not in scope_state["records"]:
            raise KeyError(item.downstream_scope_id)
        missing = sorted(set(item.evidence_ids) - self._evidence_ids(self.snapshot))
        if missing:
            raise KeyError(f"unknown evidence IDs: {missing}")
        item.created_sequence = self._sequence() + 1
        scope_state["dependencies"][item.dependency_id] = item.to_dict()
        validate_scope_state(scope_state)
        state["scope_state"] = scope_state
        self._commit_calculus(state, reason)
        return deepcopy(state["scope_state"]["dependencies"][item.dependency_id])

    def scope_report(self) -> dict[str, Any]:
        return build_scope_report(self._begin_calculus())

    def effective_scope_context(self, scope_id: str) -> dict[str, Any]:
        state = self._begin_calculus()
        scope_state = validate_scope_state(state["scope_state"])
        if scope_id not in scope_state["records"]:
            raise KeyError(scope_id)
        model = effective_scope_decisions(state, scope_id)
        return {
            "contract_id": SCOPE_CONTRACT_ID,
            "contract_version": SCOPE_CONTRACT_VERSION,
            "machine_id": self.snapshot.machine_id,
            "scope": deepcopy(scope_state["records"][scope_id]),
            "path": scope_ancestors(scope_state, scope_id),
            "local_active_model": local_scope_model(state, scope_id),
            "effective_active_model": model,
            "effective_values": effective_scope_values(state, scope_id),
            "decisions": [
                deepcopy(state["decisions"][decision_id])
                for decision_id in model.values()
                if decision_id in state["decisions"]
            ],
        }

    def migrate_legacy_scopes(
        self,
        *,
        reason: str = "legacy flat calculus records migrated to root scope metadata",
    ) -> dict[str, Any]:
        state = self._begin_calculus()
        migration = state["scope_state"]["migration"]
        if migration.get("legacy_flat_state_migrated"):
            return deepcopy(migration)
        for collection in (
            "decisions",
            "obligations",
            "locks",
            "conflicts",
            "explanations",
            "constraints",
        ):
            for record in state.get(collection, {}).values():
                record["scope"] = with_scope(record.get("scope"), scope_id_from(record))
        migration["legacy_flat_state_migrated"] = True
        migration["migrated_sequence"] = self._sequence() + 1
        self._commit_calculus(state, reason)
        return deepcopy(state["scope_state"]["migration"])


__all__ = ["ScopeAdminMixin"]
