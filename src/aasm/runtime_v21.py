from __future__ import annotations

from copy import deepcopy
from typing import Any

from .calculus import (
    ConflictRecord,
    DecisionRecord,
    ExplanationRecord,
    FairnessPolicy,
    LearnedConstraint,
    LockRecord,
    ObligationRecord,
    OBLIGATION_TRANSITIONS,
    RecoveryDecision,
    apply_backjump,
    assert_calculus_invariants,
    audit_fairness,
    candidate_exposes_overdue,
    compute_backjump,
    condition_holds,
    decision_descendants,
    decision_values,
    default_calculus_state,
    normalize_calculus_state,
    project_constraint,
    reevaluate_locks,
    validate_explanation,
    violated_hard_constraints,
)
from .change_impact import ChangeKind, ChangeSignal
from .model import MachineState
from .runtime_v19 import AASMEngine as V19Engine
from .team_protocol import PlannerBuilderVerifierPolicy, TeamRole


class AASMEngine(V19Engine):
    """v0.21 runtime: formal decision/obligation calculus and conflict learning.

    Calculus state is part of the ordinary MachineSnapshot and is committed by
    the existing SNAPSHOT_PATCHED event/reducer path. This preserves replay,
    SQLite/PostgreSQL parity, historical forks, and every v0.19 public API.
    """

    def _sequence(self) -> int:
        getter = getattr(self, "current_sequence", None)
        if getter is not None:
            return int(getter())
        if self.events:
            return int(self.events[-1].sequence)
        return 0

    def _calculus(self) -> dict[str, Any]:
        return normalize_calculus_state(getattr(self.snapshot, "calculus", None))

    def _begin_calculus(self) -> dict[str, Any]:
        refresh = getattr(self, "_refresh_canonical_snapshot", None)
        if refresh is not None:
            refresh()
        return self._calculus()

    def _commit_calculus(self, state: dict[str, Any], reason: str):
        state = normalize_calculus_state(state)
        assert_calculus_invariants(state)
        self.patch_snapshot({"calculus": state}, reason)
        return deepcopy(state)

    @staticmethod
    def _evidence_ids(snapshot) -> set[str]:
        return {
            str(record.get("evidence_id"))
            for record in snapshot.evidence.get("records", [])
            if record.get("evidence_id")
        }

    @staticmethod
    def _known_plan_nodes(snapshot) -> set[str]:
        return {
            str(node.get("node_id"))
            for node in snapshot.graph.get("nodes", [])
            if node.get("node_id")
        }

    def calculus_report(self) -> dict[str, Any]:
        state = self._begin_calculus()
        values = decision_values(state)
        return {
            "schema_version": state["schema_version"],
            "epoch": state["epoch"],
            "active_model": deepcopy(state["active_model"]),
            "active_values": values,
            "decisions": deepcopy(state["decisions"]),
            "obligations": deepcopy(state["obligations"]),
            "locks": deepcopy(state["locks"]),
            "conflicts": deepcopy(state["conflicts"]),
            "explanations": deepcopy(state["explanations"]),
            "constraints": deepcopy(state["constraints"]),
            "fairness": deepcopy(state["fairness"]),
            "violated_hard_constraints": violated_hard_constraints(state, values),
        }

    def configure_calculus_fairness(self, policy: FairnessPolicy, *, reason="calculus fairness policy configured"):
        state = self._begin_calculus()
        state["fairness"]["policy"] = policy.to_dict()
        state, report = audit_fairness(state)
        self._commit_calculus(state, reason)
        return {"policy": policy.to_dict(), **report}

    def register_decision(self, record: DecisionRecord, *, reason="calculus decision registered"):
        state = self._begin_calculus()
        if record.decision_id in state["decisions"]:
            raise ValueError(f"decision already exists: {record.decision_id}")
        missing = sorted(set(record.parent_ids) - set(state["decisions"]))
        if missing:
            raise KeyError(f"unknown parent decisions: {missing}")
        missing_evidence = sorted(set(record.evidence_ids) - self._evidence_ids(self.snapshot))
        if missing_evidence:
            raise KeyError(f"unknown evidence IDs: {missing_evidence}")
        missing_constraints = sorted(set(record.antecedent_constraint_ids) - set(state["constraints"]))
        if missing_constraints:
            raise KeyError(f"unknown antecedent constraints: {missing_constraints}")
        if record.level == 0 and record.kind not in {"ROOT", "PINNED"}:
            parent_levels = [int(state["decisions"][parent].get("level", 0)) for parent in record.parent_ids]
            active_levels = [
                int(item.get("level", 0))
                for item in state["decisions"].values()
                if item.get("status") == "ACTIVE"
            ]
            record.level = 1 + max(parent_levels or active_levels or [0])
        record.created_sequence = self._sequence() + 1
        state["decisions"][record.decision_id] = record.to_dict()
        for parent_id in record.parent_ids:
            edge = {"src": parent_id, "dst": record.decision_id, "relation": "DERIVES" if record.kind == "DERIVED" else "DEPENDS_ON"}
            if edge not in state["decision_edges"]:
                state["decision_edges"].append(edge)
        self._commit_calculus(state, reason)
        return deepcopy(state["decisions"][record.decision_id])

    def activate_decision(
        self,
        decision_id: str,
        *,
        supersede_decision_id: str | None = None,
        reason="calculus decision activated",
    ):
        state, fairness = audit_fairness(self._begin_calculus())
        decision = state["decisions"].get(decision_id)
        if decision is None:
            raise KeyError(decision_id)
        if decision.get("status") not in {"PROPOSED", "SUSPENDED"}:
            raise ValueError(f"decision {decision_id} cannot activate from {decision.get('status')}")
        inactive_parents = sorted(
            parent_id for parent_id in decision.get("parent_ids", [])
            if state["decisions"].get(parent_id, {}).get("status") != "ACTIVE"
        )
        if inactive_parents:
            raise ValueError(f"decision parents are not active: {inactive_parents}")
        inactive_antecedents = sorted(
            constraint_id for constraint_id in decision.get("antecedent_constraint_ids", [])
            if state["constraints"].get(constraint_id, {}).get("status") not in {"ACTIVE", "SOFT"}
        )
        if inactive_antecedents:
            raise ValueError(f"decision antecedent constraints are inactive: {inactive_antecedents}")
        previous_values = decision_values(state)
        subject = decision["subject"]
        current_id = state["active_model"].get(subject)
        suspended_dependents: list[str] = []
        if current_id and current_id != decision_id:
            if supersede_decision_id != current_id:
                raise ValueError(f"subject {subject} already has active decision {current_id}; explicit supersession required")
            if state["decisions"][current_id].get("pinned"):
                raise ValueError(f"pinned decision cannot be superseded: {current_id}")
            state["decisions"][current_id]["status"] = "SUPERSEDED"
            state["decisions"][current_id]["superseded_by"] = decision_id
            descendants = decision_descendants(state, current_id) - {current_id}
            for dependent_id in sorted(descendants):
                dependent = state["decisions"].get(dependent_id)
                if dependent is not None and dependent.get("status") == "ACTIVE":
                    dependent["status"] = "SUSPENDED"
                    suspended_dependents.append(dependent_id)
            state["active_model"] = {
                active_subject: active_id
                for active_subject, active_id in state["active_model"].items()
                if active_id not in set(suspended_dependents)
            }
        candidate_model = deepcopy(state["active_model"])
        candidate_model[subject] = decision_id
        decision["status"] = "ACTIVE"
        decision["activated_sequence"] = self._sequence() + 1
        state["active_model"] = candidate_model
        values = decision_values(state)
        violations = violated_hard_constraints(state, values)
        if violations:
            raise ValueError(f"candidate model violates learned hard constraints: {violations}")
        policy = FairnessPolicy(**deepcopy(state["fairness"]["policy"]))
        if fairness["overdue"] and policy.enforcement == "BLOCK_PLANNING" and not candidate_exposes_overdue(
            state, values, previous_values=previous_values
        ):
            raise ValueError(f"fairness blocks model selection until overdue obligations are exposed or dispositioned: {fairness['overdue']}")
        state["epoch"] = int(state.get("epoch", 0)) + 1
        state, broken = reevaluate_locks(state)
        state, report = audit_fairness(state)
        self._commit_calculus(state, reason)
        return {
            "decision": deepcopy(state["decisions"][decision_id]),
            "active_model": deepcopy(state["active_model"]),
            "broken_lock_ids": broken,
            "suspended_dependent_decision_ids": suspended_dependents,
            "fairness": report,
        }

    def register_obligation(self, record: ObligationRecord, *, reason="calculus obligation registered"):
        state = self._begin_calculus()
        if record.obligation_id in state["obligations"]:
            raise ValueError(f"obligation already exists: {record.obligation_id}")
        missing_decisions = sorted(set(record.decision_dependencies) - set(state["decisions"]))
        if missing_decisions:
            raise KeyError(f"unknown decision dependencies: {missing_decisions}")
        missing_obligations = sorted(set(record.dependencies) - set(state["obligations"]))
        if missing_obligations:
            raise KeyError(f"unknown obligation dependencies: {missing_obligations}")
        unknown_nodes = sorted(set(record.plan_node_ids) - self._known_plan_nodes(self.snapshot))
        if unknown_nodes:
            raise KeyError(f"unknown plan nodes: {unknown_nodes}")
        record.created_sequence = self._sequence() + 1
        record.last_state_change_sequence = record.created_sequence
        state["obligations"][record.obligation_id] = record.to_dict()
        for dependency in record.dependencies:
            state["obligation_edges"].append({"src": dependency, "dst": record.obligation_id, "relation": "REQUIRES"})
        state["fairness"]["records"][record.obligation_id] = {
            "created_epoch": int(state["epoch"]),
            "last_considered_epoch": int(state["epoch"]),
            "last_enabled_epoch": None,
            "last_reviewed_epoch": None,
            "current_lock_start_epoch": None,
            "lock_count": 0,
            "hidden_epochs": 0,
            "continuous_lock_epochs": 0,
            "fairness_status": "NORMAL",
            "explicit_deferral_until_epoch": None,
        }
        self._commit_calculus(state, reason)
        return deepcopy(state["obligations"][record.obligation_id])

    def enable_obligation(self, obligation_id: str, *, reason="calculus obligation enabled"):
        state = self._begin_calculus()
        obligation = state["obligations"].get(obligation_id)
        if obligation is None:
            raise KeyError(obligation_id)
        if obligation.get("status") not in {"AVAILABLE", "BLOCKED", "NEEDS_REVALIDATION"}:
            raise ValueError(f"obligation {obligation_id} cannot enable from {obligation.get('status')}")
        values = decision_values(state)
        if not condition_holds(obligation.get("activation_condition"), values):
            raise ValueError("obligation activation condition is false under the active model")
        active_locks = [
            lock_id for lock_id in obligation.get("lock_ids", [])
            if state["locks"].get(lock_id, {}).get("status") == "ACTIVE"
        ]
        if active_locks:
            raise ValueError(f"obligation is locked: {active_locks}")
        incomplete = [
            dependency for dependency in obligation.get("dependencies", [])
            if state["obligations"].get(dependency, {}).get("status") not in {"VERIFIED", "COMMITTED"}
        ]
        if incomplete:
            raise ValueError(f"obligation dependencies are incomplete: {incomplete}")
        obligation["status"] = "ENABLED"
        obligation["last_state_change_sequence"] = self._sequence() + 1
        fairness = state["fairness"]["records"].setdefault(obligation_id, {})
        fairness["last_enabled_epoch"] = int(state["epoch"])
        fairness["last_considered_epoch"] = int(state["epoch"])
        fairness["hidden_epochs"] = 0
        fairness["fairness_status"] = "NORMAL"
        self._commit_calculus(state, reason)
        return deepcopy(obligation)

    def set_obligation_status(
        self,
        obligation_id: str,
        status: str,
        *,
        evidence_ids: list[str] | None = None,
        disposition_reason: str | None = None,
        reason="calculus obligation status changed",
    ):
        state = self._begin_calculus()
        obligation = state["obligations"].get(obligation_id)
        if obligation is None:
            raise KeyError(obligation_id)
        if status not in {
            "AVAILABLE", "ENABLED", "IN_PROGRESS", "VERIFYING", "VERIFIED", "COMMITTED",
            "BLOCKED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE",
        }:
            raise ValueError(f"invalid obligation status: {status}")
        current_status = obligation.get("status")
        if status != current_status and status not in OBLIGATION_TRANSITIONS.get(current_status, set()):
            raise ValueError(f"illegal obligation transition {current_status}->{status}")
        if status == current_status:
            return deepcopy(obligation)
        evidence_ids = list(evidence_ids or [])
        missing = sorted(set(evidence_ids) - self._evidence_ids(self.snapshot))
        if missing:
            raise KeyError(f"unknown evidence IDs: {missing}")
        if status in {"REJECTED", "SUPERSEDED", "IMPOSSIBLE"} and not disposition_reason:
            raise ValueError(f"{status} requires disposition_reason")
        if status in {"VERIFIED", "COMMITTED"}:
            selected_ids = set(evidence_ids or obligation.get("evidence_ids", []))
            available_types: set[str] = set()
            for record in self.snapshot.evidence.get("records", []):
                if record.get("evidence_id") not in selected_ids or record.get("status", "active") != "active":
                    continue
                if record.get("kind"):
                    available_types.add(str(record["kind"]))
                metadata = record.get("metadata") or {}
                if metadata.get("evidence_type"):
                    available_types.add(str(metadata["evidence_type"]))
            missing_types = sorted(set(obligation.get("required_evidence_types", [])) - available_types)
            if missing_types:
                raise ValueError(f"evidence contract incomplete: {missing_types}")
        obligation["status"] = status
        obligation["evidence_ids"] = sorted(set(obligation.get("evidence_ids", [])) | set(evidence_ids))
        obligation["disposition_reason"] = disposition_reason
        obligation["last_state_change_sequence"] = self._sequence() + 1
        if status == "IN_PROGRESS":
            obligation["attempt_count"] = int(obligation.get("attempt_count", 0)) + 1
        record = state["fairness"]["records"].setdefault(obligation_id, {})
        record["last_considered_epoch"] = int(state["epoch"])
        record["last_reviewed_epoch"] = int(state["epoch"])
        record["fairness_status"] = "NORMAL"
        self._commit_calculus(state, reason)
        return deepcopy(obligation)

    def lock_obligation(self, record: LockRecord, *, reason="calculus obligation locked"):
        state = self._begin_calculus()
        if record.lock_id in state["locks"]:
            raise ValueError(f"lock already exists: {record.lock_id}")
        obligation = state["obligations"].get(record.obligation_id)
        if obligation is None:
            raise KeyError(record.obligation_id)
        if obligation.get("status") in {"COMMITTED", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}:
            raise ValueError("terminal obligation cannot be locked")
        if record.origin_decision_id not in state["decisions"]:
            raise KeyError(record.origin_decision_id)
        if not condition_holds(record.condition, decision_values(state)):
            raise ValueError("lock condition is not true under the active model")
        record.created_epoch = int(state["epoch"])
        state["locks"][record.lock_id] = record.to_dict()
        obligation["lock_ids"] = sorted(set(obligation.get("lock_ids", [])) | {record.lock_id})
        obligation["status"] = "LOCKED"
        fairness = state["fairness"]["records"].setdefault(record.obligation_id, {})
        fairness["lock_count"] = int(fairness.get("lock_count", 0)) + 1
        fairness["current_lock_start_epoch"] = int(state["epoch"])
        self._commit_calculus(state, reason)
        return deepcopy(state["locks"][record.lock_id])

    def unlock_obligation(self, lock_id: str, *, reason="calculus obligation unlocked"):
        state = self._begin_calculus()
        lock = state["locks"].get(lock_id)
        if lock is None:
            raise KeyError(lock_id)
        if lock.get("status") != "ACTIVE":
            return deepcopy(lock)
        lock["status"] = "BROKEN"
        lock["broken_epoch"] = int(state["epoch"])
        state, _ = reevaluate_locks(state)
        self._commit_calculus(state, reason)
        return deepcopy(lock)

    def raise_conflict(self, record: ConflictRecord, *, reason="calculus conflict raised"):
        state = self._begin_calculus()
        if record.conflict_id in state["conflicts"]:
            raise ValueError(f"conflict already exists: {record.conflict_id}")
        missing_evidence = sorted(set(record.evidence_ids) - self._evidence_ids(self.snapshot))
        if missing_evidence:
            raise KeyError(f"unknown evidence IDs: {missing_evidence}")
        if record.observed_at_obligation_id and record.observed_at_obligation_id not in state["obligations"]:
            raise KeyError(record.observed_at_obligation_id)
        if not record.active_model_snapshot:
            record.active_model_snapshot = deepcopy(state["active_model"])
        if not record.decision_levels:
            record.decision_levels = {
                decision_id: int(state["decisions"][decision_id].get("level", 0))
                for decision_id in record.active_model_snapshot.values()
                if decision_id in state["decisions"]
            }
        missing_decisions = sorted(set(record.implicated_decision_ids) - set(state["decisions"]))
        if missing_decisions:
            raise KeyError(f"unknown implicated decisions: {missing_decisions}")
        record.created_sequence = self._sequence() + 1
        state["conflicts"][record.conflict_id] = record.to_dict()
        self._commit_calculus(state, reason)
        return deepcopy(state["conflicts"][record.conflict_id])

    def register_explanation(self, record: ExplanationRecord, *, reason="calculus explanation registered"):
        state = self._begin_calculus()
        if record.explanation_id in state["explanations"]:
            raise ValueError(f"explanation already exists: {record.explanation_id}")
        record.created_sequence = self._sequence() + 1
        raw = record.to_dict()
        validate_explanation(state, raw)
        state["explanations"][record.explanation_id] = raw
        conflict = state["conflicts"][record.conflict_id]
        conflict["explanation_ids"] = sorted(set(conflict.get("explanation_ids", [])) | {record.explanation_id})
        conflict["status"] = "EXPLAINED" if record.status in {"VALIDATED", "PROVEN"} else conflict.get("status", "OPEN")
        self._commit_calculus(state, reason)
        return deepcopy(raw)

    def learn_constraint(
        self,
        explanation_id: str,
        constraint_id: str,
        *,
        strength="HARD",
        reason="calculus constraint learned",
    ):
        state = self._begin_calculus()
        if constraint_id in state["constraints"]:
            raise ValueError(f"constraint already exists: {constraint_id}")
        explanation = state["explanations"].get(explanation_id)
        if explanation is None:
            raise KeyError(explanation_id)
        constraint = project_constraint(
            state,
            explanation,
            constraint_id,
            requested_strength=strength,
            created_sequence=self._sequence() + 1,
        )
        # Same-guard hard no-good subsumption: a smaller body is stronger.
        body_keys = {
            (item["subject"], item["op"], repr(item.get("value")))
            for item in constraint["body"]
        }
        for existing_id, existing in state["constraints"].items():
            if existing.get("status") not in {"ACTIVE", "SOFT"}:
                continue
            if existing.get("strength") != constraint.get("strength") or existing.get("guard") != constraint.get("guard"):
                continue
            existing_keys = {
                (item["subject"], item["op"], repr(item.get("value")))
                for item in existing.get("body", [])
            }
            if existing_keys.issubset(body_keys):
                constraint["status"] = "SUPERSEDED"
                constraint["superseded_by"] = existing_id
                break
            if body_keys < existing_keys:
                existing["status"] = "SUPERSEDED"
                existing["superseded_by"] = constraint_id
        state["constraints"][constraint_id] = constraint
        conflict = state["conflicts"][constraint["source_conflict_id"]]
        conflict["learned_constraint_ids"] = sorted(set(conflict.get("learned_constraint_ids", [])) | {constraint_id})
        conflict["status"] = "LEARNED"
        self._commit_calculus(state, reason)
        return deepcopy(constraint)

    def backjump_conflict(
        self,
        conflict_id: str,
        *,
        explanation_id: str | None = None,
        planner_id: str | None = None,
        reason="calculus conflict backjumped",
    ):
        self._require_planner_if_configured(planner_id)
        state = self._begin_calculus()
        plan = compute_backjump(state, conflict_id, explanation_id)
        if plan["pivot_decision_id"] is None:
            raise ValueError("conflict has no revisable causal pivot; investigate, restart search, or fail")
        state = apply_backjump(state, plan, sequence=self._sequence() + 1)
        state, broken = reevaluate_locks(state)
        state, fairness = audit_fairness(state)
        violations = violated_hard_constraints(state, decision_values(state))
        if violations:
            raise ValueError(f"backjump did not remove all active hard-constraint violations: {violations}")
        self._commit_calculus(state, reason)

        known = self._known_plan_nodes(self.snapshot)
        impacted_nodes = [node_id for node_id in plan["impacted_plan_node_ids"] if node_id in known]
        for node_id in impacted_nodes:
            node = next((item for item in self.snapshot.graph.get("nodes", []) if item.get("node_id") == node_id), None)
            if node is not None and node.get("status") not in {"pruned", "complete"}:
                self.plan_update_node(node_id, {"status": "needs_revalidation", "owner": None}, reason="backjump invalidated causal plan region")
        impact = None
        if impacted_nodes:
            impact = self.analyze_change(
                ChangeSignal(
                    ChangeKind.CONTRADICTION,
                    f"Conflict {conflict_id} invalidated causal decision {plan['pivot_decision_id']}",
                    seed_nodes=impacted_nodes,
                    evidence_ids=list(state["conflicts"][conflict_id].get("evidence_ids", [])),
                    metadata={"conflict_id": conflict_id, "backjump": deepcopy(plan)},
                ),
                reason="backjump impact checkpoint created",
            )
        return {"backjump": plan, "broken_lock_ids": broken, "fairness": fairness, "impact": impact}

    def restart_search(self, *, planner_id: str | None = None, reason="calculus search restarted"):
        self._require_planner_if_configured(planner_id)
        state = self._begin_calculus()
        retained_model: dict[str, str] = {}
        for subject, decision_id in state["active_model"].items():
            decision = state["decisions"][decision_id]
            if decision.get("pinned") or decision.get("kind") in {"ROOT", "PINNED"}:
                retained_model[subject] = decision_id
            else:
                decision["status"] = "SUSPENDED"
        state["active_model"] = retained_model
        state["search_local"] = {}
        state["epoch"] = int(state.get("epoch", 0)) + 1
        state, broken = reevaluate_locks(state)
        state, fairness = audit_fairness(state)
        violations = violated_hard_constraints(state, decision_values(state))
        if violations:
            raise ValueError(f"pinned decisions violate learned hard constraints: {violations}")
        self._commit_calculus(state, reason)
        return {
            "epoch": state["epoch"],
            "retained_model": deepcopy(retained_model),
            "retained_constraint_ids": sorted(
                constraint_id
                for constraint_id, constraint in state["constraints"].items()
                if constraint.get("status") in {"ACTIVE", "SOFT"}
            ),
            "broken_lock_ids": broken,
            "fairness": fairness,
        }

    def audit_calculus_fairness(self, *, reason="calculus fairness audited"):
        state, report = audit_fairness(self._begin_calculus())
        self._commit_calculus(state, reason)
        return report

    def review_calculus_fairness(
        self,
        obligation_id: str,
        *,
        planner_id: str | None = None,
        defer_epochs: int | None = None,
        disposition_status: str | None = None,
        disposition_reason: str | None = None,
        evidence_ids: list[str] | None = None,
        reason="calculus fairness reviewed",
    ):
        self._require_planner_if_configured(planner_id)
        state = self._begin_calculus()
        if obligation_id not in state["obligations"]:
            raise KeyError(obligation_id)
        record = state["fairness"]["records"].setdefault(obligation_id, {})
        policy = FairnessPolicy(**deepcopy(state["fairness"]["policy"]))
        if defer_epochs is not None:
            if defer_epochs < 1 or defer_epochs > policy.max_deferral_epochs:
                raise ValueError(f"defer_epochs must be between 1 and {policy.max_deferral_epochs}")
            record["explicit_deferral_until_epoch"] = int(state["epoch"]) + int(defer_epochs)
        if disposition_status is not None:
            if disposition_status not in {"REJECTED", "SUPERSEDED", "IMPOSSIBLE"}:
                raise ValueError("fairness disposition must be REJECTED, SUPERSEDED, or IMPOSSIBLE")
            if not disposition_reason:
                raise ValueError("fairness disposition requires a reason")
            missing = sorted(set(evidence_ids or []) - self._evidence_ids(self.snapshot))
            if missing:
                raise KeyError(f"unknown evidence IDs: {missing}")
            obligation = state["obligations"][obligation_id]
            obligation["status"] = disposition_status
            obligation["disposition_reason"] = disposition_reason
            obligation["evidence_ids"] = sorted(set(obligation.get("evidence_ids", [])) | set(evidence_ids or []))
        if defer_epochs is None and disposition_status is None:
            raise ValueError("fairness review requires bounded deferral or terminal disposition")
        record["last_reviewed_epoch"] = int(state["epoch"])
        record["last_considered_epoch"] = int(state["epoch"])
        record["fairness_status"] = "NORMAL"
        state, report = audit_fairness(state)
        self._commit_calculus(state, reason)
        return {"obligation": deepcopy(state["obligations"][obligation_id]), "fairness": report}

    def invalidate_evidence(self, evidence_id: str, reason: str):
        record = super().invalidate_evidence(evidence_id, reason)
        state = self._begin_calculus()
        changed = False
        for explanation in state["explanations"].values():
            if evidence_id in explanation.get("evidence_ids", []) and explanation.get("status") in {"VALIDATED", "PROVEN"}:
                explanation["status"] = "REJECTED"
                explanation["invalidated_by_evidence_id"] = evidence_id
                changed = True
        for constraint in state["constraints"].values():
            if evidence_id in constraint.get("evidence_ids", []) and constraint.get("status") in {"ACTIVE", "SOFT"}:
                constraint["status"] = "EXPIRED"
                constraint["expired_by_evidence_id"] = evidence_id
                changed = True
        for conflict in state["conflicts"].values():
            if evidence_id in conflict.get("evidence_ids", []) and conflict.get("status") not in {"RESOLVED", "REJECTED"}:
                conflict["status"] = "REJECTED"
                conflict["rejected_by_evidence_id"] = evidence_id
                changed = True
        if changed:
            self._commit_calculus(state, "calculus knowledge expired after evidence invalidation")
        return record

    def _require_planner_if_configured(self, planner_id: str | None):
        team = self.snapshot.resources.get("team_protocol")
        if not team:
            return
        if not planner_id:
            raise PermissionError("configured PBV recovery requires planner_id")
        PlannerBuilderVerifierPolicy.require_role(team["members"], planner_id, TeamRole.PLANNER.value)
        if planner_id != team.get("planner_id"):
            raise PermissionError("only the authoritative Planner may recover calculus search")

    def planner_recover(self, decision: RecoveryDecision):
        self._require_planner_if_configured(decision.planner_id)
        if decision.action == "BACKJUMP":
            return self.backjump_conflict(
                decision.conflict_id,
                planner_id=decision.planner_id,
                reason=decision.reason,
            )
        return self.restart_search(planner_id=decision.planner_id, reason=decision.reason)

    def transition(self, to, reason, evidence=None, data=None):
        target = to.value if isinstance(to, MachineState) else str(to)
        if target == MachineState.COMPLETE.value:
            self._begin_calculus()
            unresolved = sorted(
                obligation_id
                for obligation_id, obligation in self._calculus()["obligations"].items()
                if obligation.get("persistent", True)
                and obligation.get("mandatory", True)
                and obligation.get("status") not in {"COMMITTED", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
            )
            if unresolved:
                raise ValueError(f"cannot COMPLETE with unresolved mandatory obligations: {unresolved}")
        return super().transition(to, reason, evidence=evidence, data=data)

    def dashboard(self):
        out = super().dashboard()
        state = self._calculus()
        out["calculus"] = {
            "epoch": state["epoch"],
            "active_model": deepcopy(state["active_model"]),
            "decision_count": len(state["decisions"]),
            "obligation_count": len(state["obligations"]),
            "open_conflicts": sorted(
                conflict_id for conflict_id, conflict in state["conflicts"].items()
                if conflict.get("status") not in {"RESOLVED", "REJECTED"}
            ),
            "active_constraints": sorted(
                constraint_id for constraint_id, constraint in state["constraints"].items()
                if constraint.get("status") in {"ACTIVE", "SOFT"}
            ),
            "fairness": deepcopy(state["fairness"]),
        }
        return out
