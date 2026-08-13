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



class ScopeSearchMixin:
    def _candidate_assignment_key(self, decision: dict[str, Any]) -> str:
        return scoped_subject_key(scope_id_from(decision), str(decision["subject"]))
    def validate_candidate_model(
        self, candidate: CandidateModel | dict[str, Any]
    ) -> CandidateValidationReport:
        item = candidate if isinstance(candidate, CandidateModel) else CandidateModel.from_dict(candidate)
        state = self._begin_calculus()
        errors: list[str] = []
        warnings: list[str] = []
        assignments = deepcopy(item.assignments)
        decisions = state["decisions"]
        root_only = all(
            decision_id in decisions
            and scope_id_from(decisions[decision_id]) == ROOT_SCOPE_ID
            for _key, decision_id in assignments.items()
        )
        if root_only:
            return super().validate_candidate_model(item)
        binding = self._profile_binding()
        namespaces = set(
            (binding.get("profile_snapshot") or {}).get("decision_namespaces", [])
        )
        for key, decision_id in sorted(assignments.items()):
            decision = decisions.get(decision_id)
            if decision is None:
                errors.append(f"unknown decision {decision_id} for assignment {key}")
                continue
            expected = self._candidate_assignment_key(decision)
            if key != expected:
                errors.append(
                    f"candidate assignment key {key} must be {expected} for decision {decision_id}"
                )
                continue
            if decision.get("status") in {"INVALIDATED", "REJECTED", "HISTORICAL"}:
                errors.append(
                    f"decision {decision_id} is not selectable from status {decision.get('status')}"
                )
            namespace = str(decision["subject"]).split(".", 1)[0].split(":", 1)[0]
            if namespaces and "*" not in namespaces and namespace not in namespaces:
                errors.append(
                    f"decision subject {decision['subject']} is outside profile namespaces {sorted(namespaces)}"
                )
        for scope_id, model in state["scope_active_models"].items():
            for subject, active_id in model.items():
                active = decisions.get(active_id, {})
                if not active.get("pinned"):
                    continue
                key = scoped_subject_key(scope_id, subject)
                if key in assignments and assignments[key] != active_id:
                    errors.append(f"candidate attempts to replace pinned decision {active_id}")
                assignments.setdefault(key, active_id)
        activation = None
        if not errors:
            try:
                staged, activation = self._stage_candidate_activation(
                    state,
                    assignments,
                    sequence=self._sequence() + 1,
                )
                violations = violated_hard_constraints(staged)
            except (KeyError, ValueError) as exc:
                errors.append(str(exc))
                violations = []
        else:
            violations = []
        return CandidateValidationReport(
            candidate_id=item.candidate_id,
            valid=not errors,
            errors=errors,
            warnings=warnings,
            violated_constraint_ids=violations,
            overdue_obligation_ids=(activation or {}).get("fairness", {}).get(
                "overdue", []
            ),
            normalized_assignments=assignments,
        )
    def _stage_candidate_activation(
        self,
        calculus: dict[str, Any],
        assignments: dict[str, str],
        *,
        sequence: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        staged, initial_fairness = audit_fairness(
            normalize_calculus_state(calculus)
        )
        decisions = staged["decisions"]
        scope_state = validate_scope_state(staged["scope_state"])
        previous_by_scope = {
            scope_id: effective_scope_values(staged, scope_id)
            for scope_id in scope_state["records"]
        }
        target_ids = set(assignments.values())
        target_rows: list[tuple[str, str, str, str]] = []
        for key, decision_id in sorted(assignments.items()):
            decision = decisions.get(decision_id)
            if decision is None:
                raise KeyError(decision_id)
            scope_id = scope_id_from(decision)
            expected = scoped_subject_key(scope_id, str(decision["subject"]))
            if key != expected:
                raise ValueError(
                    f"candidate assignment key {key} does not match {expected}"
                )
            scope = scope_state["records"].get(scope_id)
            if scope is None or scope.get("status") != "ACTIVE":
                raise ValueError(f"decision {decision_id} belongs to inactive scope {scope_id}")
            if decision.get("status") not in {"PROPOSED", "SUSPENDED", "ACTIVE"}:
                raise ValueError(
                    f"decision {decision_id} cannot activate from {decision.get('status')}"
                )
            inactive_antecedents = sorted(
                constraint_id
                for constraint_id in decision.get("antecedent_constraint_ids", [])
                if staged["constraints"].get(constraint_id, {}).get("status")
                not in {"ACTIVE", "SOFT"}
            )
            if inactive_antecedents:
                raise ValueError(
                    f"decision antecedent constraints are inactive: {inactive_antecedents}"
                )
            target_rows.append((key, decision_id, scope_id, str(decision["subject"])))

        suspended_dependents: set[str] = set()
        superseded_decisions: set[str] = set()
        for _key, decision_id, scope_id, subject in target_rows:
            decision = decisions[decision_id]
            local_model = staged["scope_active_models"].setdefault(scope_id, {})
            current_id = local_model.get(subject)
            effective = effective_scope_decisions(staged, scope_id)
            inherited_id = effective.get(subject) if current_id is None else None
            scope = scope_state["records"][scope_id]
            if inherited_id and inherited_id != decision_id:
                if scope.get("override_policy") == "DENY":
                    raise ValueError(f"scope {scope_id} denies override of {subject}")
                if not bool((decision.get("scope") or {}).get("override")):
                    raise ValueError(
                        f"decision {decision_id} requires explicit scope override for {subject}"
                    )
            if not current_id or current_id == decision_id:
                continue
            current = decisions[current_id]
            if current.get("pinned"):
                raise ValueError(f"pinned decision cannot be superseded: {current_id}")
            current["status"] = "SUPERSEDED"
            current["superseded_by"] = decision_id
            superseded_decisions.add(current_id)
            descendants = decision_descendants(staged, current_id) - {current_id}
            for dependent_id in descendants:
                dependent = decisions.get(dependent_id)
                if dependent is not None and dependent.get("status") == "ACTIVE":
                    dependent["status"] = "SUSPENDED"
                    suspended_dependents.add(dependent_id)
            removed = descendants | {current_id}
            for model in staged["scope_active_models"].values():
                for active_subject, active_id in list(model.items()):
                    if active_id in removed:
                        del model[active_subject]

        ordered = sorted(
            target_rows,
            key=lambda row: (
                scope_depth(scope_state, row[2]),
                int(decisions[row[1]].get("level", 0)),
                row[0],
                row[1],
            ),
        )
        for _key, decision_id, scope_id, subject in ordered:
            decision = decisions[decision_id]
            inactive_parents = sorted(
                parent_id
                for parent_id in decision.get("parent_ids", [])
                if decisions.get(parent_id, {}).get("status") != "ACTIVE"
                and parent_id not in target_ids
            )
            if inactive_parents:
                raise ValueError(
                    f"decision parents inactive: {inactive_parents}"
                )
            decision["status"] = "ACTIVE"
            decision["activated_sequence"] = sequence
            staged["scope_active_models"].setdefault(scope_id, {})[subject] = decision_id
            suspended_dependents.discard(decision_id)

        for _key, decision_id, _scope_id, _subject in ordered:
            inactive_parents = sorted(
                parent_id
                for parent_id in decisions[decision_id].get("parent_ids", [])
                if decisions.get(parent_id, {}).get("status") != "ACTIVE"
            )
            if inactive_parents:
                raise ValueError(
                    "candidate activation left decision parents inactive: "
                    f"{inactive_parents}"
                )

        staged["active_model"] = deepcopy(
            staged["scope_active_models"].get(ROOT_SCOPE_ID, {})
        )
        violations = violated_hard_constraints(staged)
        if violations:
            raise ValueError(
                f"candidate model violates learned hard constraints: {violations}"
            )
        policy = FairnessPolicy(**deepcopy(staged["fairness"]["policy"]))
        if initial_fairness["overdue"] and policy.enforcement == "BLOCK_PLANNING":
            exposed = any(
                candidate_exposes_overdue(
                    staged,
                    effective_scope_values(staged, scope_id),
                    previous_values=previous_by_scope[scope_id],
                )
                for scope_id in scope_state["records"]
            )
            if not exposed:
                raise ValueError(
                    "fairness blocks model selection until overdue obligations are "
                    f"exposed or dispositioned: {initial_fairness['overdue']}"
                )
        staged["epoch"] = int(staged.get("epoch", 0)) + 1
        staged, broken = reevaluate_locks(staged)
        staged, fairness = audit_fairness(staged)
        return staged, {
            "broken_lock_ids": broken,
            "suspended_dependent_decision_ids": sorted(suspended_dependents),
            "superseded_decision_ids": sorted(superseded_decisions),
            "fairness": fairness,
            "scope_active_models": deepcopy(staged["scope_active_models"]),
        }


__all__ = ["ScopeSearchMixin"]
