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



class ScopeRecoveryMixin:
    def backjump_conflict(
        self,
        conflict_id: str,
        *,
        explanation_id: str | None = None,
        planner_id: str | None = None,
        reason: str = "calculus conflict backjumped",
    ) -> dict[str, Any]:
        self._require_planner_if_configured(planner_id)
        state = self._begin_calculus()
        plan = compute_backjump(state, conflict_id, explanation_id)
        if plan["pivot_decision_id"] is None:
            raise ValueError(
                "conflict has no revisable causal pivot; investigate, restart search, or fail"
            )
        pivot_id = str(plan["pivot_decision_id"])
        pivot_scope_id = scope_id_from(state["decisions"][pivot_id])
        scope_state = validate_scope_state(state["scope_state"])
        invalidated_scopes: set[str] = set()
        revalidation_scopes: set[str] = set()
        invalidated_decisions = set(plan.get("invalidated_decision_ids", []))
        if pivot_scope_id != ROOT_SCOPE_ID:
            invalidated_scopes, revalidation_scopes = dependency_impacted_scopes(
                scope_state, pivot_scope_id
            )
            invalidated_decisions.update(
                decision_id
                for decision_id, decision in state["decisions"].items()
                if decision.get("status") == "ACTIVE"
                and scope_id_from(decision) in invalidated_scopes
            )
        impacted_obligations = set(plan.get("impacted_obligation_ids", []))
        impacted_obligations.update(
            obligation_id
            for obligation_id, obligation in state["obligations"].items()
            if scope_id_from(obligation) in invalidated_scopes
            or scope_id_from(obligation) in revalidation_scopes
            or bool(
                set(obligation.get("decision_dependencies", []))
                & invalidated_decisions
            )
        )
        all_scopes = set(scope_state["records"])
        plan = {
            **deepcopy(plan),
            "pivot_scope_id": pivot_scope_id,
            "invalidated_scope_ids": sorted(invalidated_scopes),
            "revalidation_scope_ids": sorted(revalidation_scopes),
            "preserved_scope_ids": sorted(
                all_scopes - invalidated_scopes - revalidation_scopes
            ),
            "invalidated_decision_ids": sorted(invalidated_decisions),
            "impacted_obligation_ids": sorted(impacted_obligations),
        }
        state = apply_backjump(state, plan, sequence=self._sequence() + 1)
        for scope_id in plan["invalidated_scope_ids"]:
            if scope_id != ROOT_SCOPE_ID:
                scope = state["scope_state"]["records"][scope_id]
                scope["status"] = "NEEDS_REVALIDATION"
                scope["updated_sequence"] = self._sequence() + 1
        for scope_id in plan["revalidation_scope_ids"]:
            scope = state["scope_state"]["records"][scope_id]
            scope["status"] = "NEEDS_REVALIDATION"
            scope["updated_sequence"] = self._sequence() + 1
        state, broken = reevaluate_locks(state)
        state, fairness = audit_fairness(state)
        violations = violated_hard_constraints(state)
        if violations:
            raise ValueError(
                f"backjump did not remove all active hard-constraint violations: {violations}"
            )
        self._commit_calculus(state, reason)

        known = self._known_plan_nodes(self.snapshot)
        impacted_nodes = [
            node_id
            for node_id in plan.get("impacted_plan_node_ids", [])
            if node_id in known
        ]
        for node_id in impacted_nodes:
            node = next(
                (
                    item
                    for item in self.snapshot.graph.get("nodes", [])
                    if item.get("node_id") == node_id
                ),
                None,
            )
            if node is not None and node.get("status") not in {"pruned", "complete"}:
                self.plan_update_node(
                    node_id,
                    {"status": "needs_revalidation", "owner": None},
                    reason="scope backjump invalidated causal plan region",
                )
        impact = None
        if impacted_nodes:
            from .change_impact import ChangeKind, ChangeSignal

            impact = self.analyze_change(
                ChangeSignal(
                    ChangeKind.CONTRADICTION,
                    f"Conflict {conflict_id} invalidated causal scope {pivot_scope_id}",
                    seed_nodes=impacted_nodes,
                    evidence_ids=list(
                        state["conflicts"][conflict_id].get("evidence_ids", [])
                    ),
                    metadata={"conflict_id": conflict_id, "backjump": deepcopy(plan)},
                ),
                reason="scope backjump impact checkpoint created",
            )
        return {
            "backjump": plan,
            "broken_lock_ids": broken,
            "fairness": fairness,
            "impact": impact,
        }
    def restart_scope(
        self,
        scope_id: str,
        *,
        planner_id: str | None = None,
        reason: str = "calculus scope restarted",
    ) -> dict[str, Any]:
        self._require_planner_if_configured(planner_id)
        if scope_id == ROOT_SCOPE_ID:
            return self.restart_search(planner_id=planner_id, reason=reason)
        state = self._begin_calculus()
        self._require_scope(state, scope_id)
        target_scopes = scope_descendants(state["scope_state"], scope_id)
        suspended: list[str] = []
        retained: list[str] = []
        for decision_id, decision in state["decisions"].items():
            if decision.get("status") != "ACTIVE" or scope_id_from(decision) not in target_scopes:
                continue
            if decision.get("pinned") or decision.get("kind") in {"ROOT", "PINNED"}:
                retained.append(decision_id)
            else:
                decision["status"] = "SUSPENDED"
                suspended.append(decision_id)
        suspended_set = set(suspended)
        for target_scope_id in target_scopes:
            state["scope_active_models"][target_scope_id] = {
                subject: decision_id
                for subject, decision_id in state["scope_active_models"].get(
                    target_scope_id, {}
                ).items()
                if decision_id not in suspended_set
            }
        reopened: list[str] = []
        for obligation_id, obligation in state["obligations"].items():
            if scope_id_from(obligation) not in target_scopes:
                continue
            if obligation.get("status") not in {
                "REJECTED",
                "SUPERSEDED",
                "IMPOSSIBLE",
            }:
                obligation["status"] = "NEEDS_REVALIDATION"
                obligation["last_state_change_sequence"] = self._sequence() + 1
                reopened.append(obligation_id)
        state["scope_state"]["records"][scope_id].setdefault("metadata", {})[
            "last_restart"
        ] = {"sequence": self._sequence() + 1, "reason": reason}
        state["search_local"] = {}
        state["epoch"] = int(state.get("epoch", 0)) + 1
        state, broken = reevaluate_locks(state)
        state, fairness = audit_fairness(state)
        violations = violated_hard_constraints(state)
        if violations:
            raise ValueError(
                f"retained decisions violate learned hard constraints: {violations}"
            )
        self._commit_calculus(state, reason)
        return {
            "scope_id": scope_id,
            "restarted_scope_ids": sorted(target_scopes),
            "suspended_decision_ids": sorted(suspended),
            "retained_decision_ids": sorted(retained),
            "reopened_obligation_ids": sorted(reopened),
            "preserved_scope_ids": sorted(
                set(state["scope_state"]["records"]) - set(target_scopes)
            ),
            "retained_constraint_ids": sorted(
                constraint_id
                for constraint_id, constraint in state["constraints"].items()
                if constraint.get("status") in {"ACTIVE", "SOFT"}
            ),
            "broken_lock_ids": broken,
            "fairness": fairness,
        }
    def restart_search(
        self,
        *,
        planner_id: str | None = None,
        reason: str = "calculus search restarted",
    ):
        self._require_planner_if_configured(planner_id)
        state = self._begin_calculus()
        retained_models: dict[str, dict[str, str]] = {
            scope_id: {} for scope_id in state["scope_state"]["records"]
        }
        suspended: list[str] = []
        for scope_id, model in state["scope_active_models"].items():
            for subject, decision_id in model.items():
                decision = state["decisions"][decision_id]
                if decision.get("pinned") or decision.get("kind") in {"ROOT", "PINNED"}:
                    retained_models[scope_id][subject] = decision_id
                else:
                    decision["status"] = "SUSPENDED"
                    suspended.append(decision_id)
        state["scope_active_models"] = retained_models
        state["active_model"] = deepcopy(retained_models[ROOT_SCOPE_ID])
        state["search_local"] = {}
        state["epoch"] = int(state.get("epoch", 0)) + 1
        state, broken = reevaluate_locks(state)
        state, fairness = audit_fairness(state)
        violations = violated_hard_constraints(state)
        if violations:
            raise ValueError(
                f"pinned decisions violate learned hard constraints: {violations}"
            )
        self._commit_calculus(state, reason)
        return {
            "epoch": state["epoch"],
            "retained_model": deepcopy(retained_models[ROOT_SCOPE_ID]),
            "retained_scope_models": deepcopy(retained_models),
            "suspended_decision_ids": sorted(suspended),
            "retained_constraint_ids": sorted(
                constraint_id
                for constraint_id, constraint in state["constraints"].items()
                if constraint.get("status") in {"ACTIVE", "SOFT"}
            ),
            "broken_lock_ids": broken,
            "fairness": fairness,
        }


__all__ = ["ScopeRecoveryMixin"]
