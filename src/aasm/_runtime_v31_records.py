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



class ScopeRecordMixin:
    def _require_scope(self, state: dict[str, Any], scope_id: str) -> dict[str, Any]:
        scope_state = validate_scope_state(state["scope_state"])
        scope = scope_state["records"].get(scope_id)
        if scope is None:
            raise KeyError(scope_id)
        if scope.get("status") != "ACTIVE":
            raise ValueError(f"scope {scope_id} is not active")
        return scope
    def _evidence_scope(self, evidence_id: str) -> str:
        for record in self.snapshot.evidence.get("records", []):
            if record.get("evidence_id") == evidence_id:
                return str((record.get("metadata") or {}).get("scope_id") or ROOT_SCOPE_ID)
        raise KeyError(evidence_id)
    def _require_evidence_flow(
        self,
        state: dict[str, Any],
        evidence_ids: list[str],
        target_scope_id: str,
    ) -> None:
        for evidence_id in evidence_ids:
            source_scope_id = self._evidence_scope(evidence_id)
            if not scope_flow_allowed(
                state["scope_state"], source_scope_id, target_scope_id
            ):
                raise ValueError(
                    f"evidence {evidence_id} cannot flow from scope "
                    f"{source_scope_id} to {target_scope_id} without hierarchy or dependency"
                )
    def add_evidence(
        self,
        record: EvidenceRecord,
        *,
        reason: str = "evidence recorded",
    ):
        state = self._begin_calculus()
        scope_id = str((record.metadata or {}).get("scope_id") or ROOT_SCOPE_ID)
        self._require_scope(state, scope_id)
        record.metadata = deepcopy(record.metadata or {})
        record.metadata["scope_id"] = scope_id
        return super().add_evidence(record, reason=reason)
    def register_decision(
        self,
        record: DecisionRecord,
        *,
        reason: str = "calculus decision registered",
    ):
        state = self._begin_calculus()
        scope_id = scope_id_from(record.to_dict())
        self._require_scope(state, scope_id)
        for parent_id in record.parent_ids:
            parent = state["decisions"].get(parent_id)
            if parent is not None and not scope_flow_allowed(
                state["scope_state"], scope_id_from(parent), scope_id
            ):
                raise ValueError(
                    f"decision {record.decision_id} has illegal cross-scope parent {parent_id}"
                )
        self._require_evidence_flow(state, record.evidence_ids, scope_id)
        record.scope = with_scope(record.scope, scope_id)
        return super().register_decision(record, reason=reason)
    def register_obligation(
        self,
        record: ObligationRecord,
        *,
        reason: str = "calculus obligation registered",
    ):
        state = self._begin_calculus()
        scope_id = scope_id_from(record.to_dict())
        self._require_scope(state, scope_id)
        for decision_id in record.decision_dependencies:
            decision = state["decisions"].get(decision_id)
            if decision is not None and not scope_flow_allowed(
                state["scope_state"], scope_id_from(decision), scope_id
            ):
                raise ValueError(
                    f"obligation {record.obligation_id} has illegal cross-scope decision dependency {decision_id}"
                )
        record.scope = with_scope(record.scope, scope_id)
        return super().register_obligation(record, reason=reason)
    def set_obligation_status(
        self,
        obligation_id: str,
        status: str,
        *,
        evidence_ids: list[str] | None = None,
        disposition_reason: str | None = None,
        reason: str = "calculus obligation status changed",
    ):
        state = self._begin_calculus()
        obligation = state["obligations"].get(obligation_id)
        if obligation is None:
            raise KeyError(obligation_id)
        selected = list(evidence_ids or [])
        if status in {"VERIFIED", "COMMITTED"} and not selected:
            selected = list(obligation.get("evidence_ids", []))
        self._require_evidence_flow(state, selected, scope_id_from(obligation))
        return super().set_obligation_status(
            obligation_id,
            status,
            evidence_ids=evidence_ids,
            disposition_reason=disposition_reason,
            reason=reason,
        )


__all__ = ["ScopeRecordMixin"]
