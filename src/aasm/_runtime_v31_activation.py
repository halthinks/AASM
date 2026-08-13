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



class ScopeActivationMixin:
    def activate_decision(
        self,
        decision_id: str,
        *,
        supersede_decision_id: str | None = None,
        reason: str = "calculus decision activated",
    ):
        state = self._begin_calculus()
        decision = state["decisions"].get(decision_id)
        if decision is None:
            raise KeyError(decision_id)
        scope_id = scope_id_from(decision)
        if scope_id == ROOT_SCOPE_ID:
            return super().activate_decision(
                decision_id,
                supersede_decision_id=supersede_decision_id,
                reason=reason,
            )
        state, fairness = audit_fairness(state)
        decision = state["decisions"][decision_id]
        scope = self._require_scope(state, scope_id)
        if decision.get("status") not in {"PROPOSED", "SUSPENDED"}:
            raise ValueError(
                f"decision {decision_id} cannot activate from {decision.get('status')}"
            )
        inactive_parents = sorted(
            parent_id
            for parent_id in decision.get("parent_ids", [])
            if state["decisions"].get(parent_id, {}).get("status") != "ACTIVE"
        )
        if inactive_parents:
            raise ValueError(f"decision parents inactive: {inactive_parents}")
        inactive_antecedents = sorted(
            constraint_id
            for constraint_id in decision.get("antecedent_constraint_ids", [])
            if state["constraints"].get(constraint_id, {}).get("status")
            not in {"ACTIVE", "SOFT"}
        )
        if inactive_antecedents:
            raise ValueError(
                f"decision antecedent constraints are inactive: {inactive_antecedents}"
            )
        previous_values = effective_scope_values(state, scope_id)
        subject = decision["subject"]
        local_model = state["scope_active_models"].setdefault(scope_id, {})
        current_id = local_model.get(subject)
        inherited = effective_scope_decisions(state, scope_id)
        inherited_id = inherited.get(subject) if current_id is None else None
        if inherited_id and inherited_id != decision_id:
            if scope.get("override_policy") == "DENY":
                raise ValueError(f"scope {scope_id} denies override of {subject}")
            if not bool((decision.get("scope") or {}).get("override")):
                raise ValueError(
                    f"decision {decision_id} requires explicit scope override for {subject}"
                )
        suspended_dependents: set[str] = set()
        if current_id and current_id != decision_id:
            if supersede_decision_id != current_id:
                raise ValueError(
                    f"scope {scope_id} subject {subject} already has active decision "
                    f"{current_id}; explicit supersession required"
                )
            current = state["decisions"][current_id]
            if current.get("pinned"):
                raise ValueError(f"pinned decision cannot be superseded: {current_id}")
            current["status"] = "SUPERSEDED"
            current["superseded_by"] = decision_id
            suspended_dependents = decision_descendants(state, current_id) - {current_id}
            for dependent_id in sorted(suspended_dependents):
                dependent = state["decisions"].get(dependent_id)
                if dependent is not None and dependent.get("status") == "ACTIVE":
                    dependent["status"] = "SUSPENDED"
            removed = suspended_dependents | {current_id}
            for model in state["scope_active_models"].values():
                for active_subject, active_id in list(model.items()):
                    if active_id in removed:
                        del model[active_subject]
        decision["status"] = "ACTIVE"
        decision["activated_sequence"] = self._sequence() + 1
        state["scope_active_models"].setdefault(scope_id, {})[subject] = decision_id
        values = effective_scope_values(state, scope_id)
        violations = violated_hard_constraints_for_scope(state, scope_id)
        if violations:
            raise ValueError(
                f"candidate scope model violates learned hard constraints: {violations}"
            )
        policy = FairnessPolicy(**deepcopy(state["fairness"]["policy"]))
        if (
            fairness["overdue"]
            and policy.enforcement == "BLOCK_PLANNING"
            and not candidate_exposes_overdue(
                state, values, previous_values=previous_values
            )
        ):
            raise ValueError(
                "fairness blocks model selection until overdue obligations are "
                f"exposed or dispositioned: {fairness['overdue']}"
            )
        state["epoch"] = int(state.get("epoch", 0)) + 1
        state, broken = reevaluate_locks(state)
        state, report = audit_fairness(state)
        self._commit_calculus(state, reason)
        return {
            "decision": deepcopy(state["decisions"][decision_id]),
            "scope_id": scope_id,
            "local_active_model": local_scope_model(state, scope_id),
            "effective_active_model": effective_scope_decisions(state, scope_id),
            "broken_lock_ids": broken,
            "suspended_dependent_decision_ids": sorted(suspended_dependents),
            "fairness": report,
        }
    def enable_obligation(
        self,
        obligation_id: str,
        *,
        reason: str = "calculus obligation enabled",
    ):
        state = self._begin_calculus()
        obligation = state["obligations"].get(obligation_id)
        if obligation is None:
            raise KeyError(obligation_id)
        scope_id = scope_id_from(obligation)
        if scope_id == ROOT_SCOPE_ID:
            return super().enable_obligation(obligation_id, reason=reason)
        self._require_scope(state, scope_id)
        if obligation.get("status") not in {
            "AVAILABLE",
            "BLOCKED",
            "NEEDS_REVALIDATION",
        }:
            raise ValueError(
                f"obligation {obligation_id} cannot enable from {obligation.get('status')}"
            )
        if not condition_holds(
            obligation.get("activation_condition"),
            effective_scope_values(state, scope_id),
        ):
            raise ValueError(
                "obligation activation condition is false under the effective scope model"
            )
        active_locks = [
            lock_id
            for lock_id in obligation.get("lock_ids", [])
            if state["locks"].get(lock_id, {}).get("status") == "ACTIVE"
        ]
        if active_locks:
            raise ValueError(f"obligation is locked: {active_locks}")
        incomplete = [
            dependency
            for dependency in obligation.get("dependencies", [])
            if state["obligations"].get(dependency, {}).get("status")
            not in {"VERIFIED", "COMMITTED"}
        ]
        if incomplete:
            raise ValueError(f"obligation dependencies are incomplete: {incomplete}")
        obligation["status"] = "ENABLED"
        obligation["last_state_change_sequence"] = self._sequence() + 1
        fairness = state["fairness"]["records"].setdefault(obligation_id, {})
        fairness.update(
            {
                "last_enabled_epoch": int(state["epoch"]),
                "last_considered_epoch": int(state["epoch"]),
                "hidden_epochs": 0,
                "fairness_status": "NORMAL",
            }
        )
        self._commit_calculus(state, reason)
        return deepcopy(obligation)
    def lock_obligation(
        self,
        record: LockRecord,
        *,
        reason: str = "calculus obligation locked",
    ):
        state = self._begin_calculus()
        obligation = state["obligations"].get(record.obligation_id)
        if obligation is None:
            raise KeyError(record.obligation_id)
        scope_id = scope_id_from(obligation)
        if scope_id == ROOT_SCOPE_ID and scope_id_from(record.to_dict()) == ROOT_SCOPE_ID:
            return super().lock_obligation(record, reason=reason)
        self._require_scope(state, scope_id)
        record.scope = with_scope(record.scope, scope_id)
        origin = state["decisions"].get(record.origin_decision_id)
        if origin is None:
            raise KeyError(record.origin_decision_id)
        if not scope_flow_allowed(state["scope_state"], scope_id_from(origin), scope_id):
            raise ValueError("lock origin decision cannot flow to the obligation scope")
        if not condition_holds(record.condition, effective_scope_values(state, scope_id)):
            raise ValueError("lock condition is not true under the effective scope model")
        if record.lock_id in state["locks"]:
            raise ValueError(f"lock already exists: {record.lock_id}")
        if obligation.get("status") in {
            "COMMITTED",
            "REJECTED",
            "SUPERSEDED",
            "IMPOSSIBLE",
        }:
            raise ValueError("terminal obligation cannot be locked")
        record.created_epoch = int(state["epoch"])
        state["locks"][record.lock_id] = record.to_dict()
        obligation["lock_ids"] = sorted(
            set(obligation.get("lock_ids", [])) | {record.lock_id}
        )
        obligation["status"] = "LOCKED"
        fairness = state["fairness"]["records"].setdefault(record.obligation_id, {})
        fairness["lock_count"] = int(fairness.get("lock_count", 0)) + 1
        fairness["current_lock_start_epoch"] = int(state["epoch"])
        self._commit_calculus(state, reason)
        return deepcopy(state["locks"][record.lock_id])
    def raise_conflict(
        self,
        record: ConflictRecord,
        *,
        reason: str = "calculus conflict raised",
    ):
        state = self._begin_calculus()
        scope_id = scope_id_from(record.to_dict())
        if record.observed_at_obligation_id:
            obligation = state["obligations"].get(record.observed_at_obligation_id)
            if obligation is None:
                raise KeyError(record.observed_at_obligation_id)
            if not (record.scope or {}).get("scope_id"):
                scope_id = scope_id_from(obligation)
        self._require_scope(state, scope_id)
        record.scope = with_scope(record.scope, scope_id)
        self._require_evidence_flow(state, record.evidence_ids, scope_id)
        if not record.active_model_snapshot:
            record.active_model_snapshot = canonical_active_snapshot(state, scope_id)
        return super().raise_conflict(record, reason=reason)
    def register_explanation(
        self,
        record: ExplanationRecord,
        *,
        reason: str = "calculus explanation registered",
    ):
        state = self._begin_calculus()
        conflict = state["conflicts"].get(record.conflict_id)
        if conflict is None:
            raise KeyError(record.conflict_id)
        scope_id = scope_id_from(conflict)
        if (record.scope or {}).get("scope_id") and scope_id_from(record.to_dict()) != scope_id:
            raise ValueError("explanation scope must match its conflict scope")
        record.scope = with_scope(record.scope, scope_id)
        self._require_evidence_flow(state, record.evidence_ids, scope_id)
        return super().register_explanation(record, reason=reason)


__all__ = ["ScopeActivationMixin"]
