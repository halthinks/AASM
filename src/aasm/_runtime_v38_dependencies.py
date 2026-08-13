from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from typing import Any, Mapping, Sequence

from .calculus import OBLIGATION_TRANSITIONS, reevaluate_locks
from .evidence import EvidenceRecord
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .semantic_dependencies import (
    CAUSAL_DECISION_CONTRACT_ID,
    REACTIVE_OBLIGATION_CONTRACT_ID,
    SEMANTIC_DEPENDENCY_CONTRACT_ID,
    TRUTH_MAINTENANCE_CONTRACT_ID,
    CausalDecisionRecord,
    ReactiveObligationRecord,
    ReactiveObligationRule,
    SemanticDependency,
    SemanticNodeRef,
    TruthMaintenancePlan,
    build_semantic_dependency_graph,
    dependency_impact_report,
    dependency_lineage_report,
    dependency_memory_signals,
    explicit_dependency_edges,
    reactive_rules_from_evidence,
    semantic_dependency_contract,
    semantic_dependency_document,
    truth_records_from_evidence,
)


class SemanticDependencyRuntimeMixin:
    """v0.38 semantic dependency, causal decision, and truth-maintenance runtime."""

    def semantic_dependency_contract_report(self) -> dict[str, Any]:
        return semantic_dependency_contract()

    def _dependency_inputs(self) -> dict[str, Any]:
        try:
            effects = self.list_effects()
        except Exception:
            effects = []
        return {
            "reasoning": self.reasoning_report(),
            "calculus": self.calculus_report(),
            "semantic_problem": self.semantic_problem_report(),
            "evidence_records": deepcopy(self.snapshot.evidence.get("records", [])),
            "events": list(self.events),
            "effects": effects,
        }

    def semantic_dependency_graph(self, *, explicit_edges: Sequence[SemanticDependency | Mapping[str, Any]] = ()) -> dict[str, Any]:
        return build_semantic_dependency_graph(**self._dependency_inputs(), explicit_edges=explicit_edges)

    def semantic_dependency_impact(self, node_type: str, node_id: str) -> dict[str, Any]:
        return dependency_impact_report(self.semantic_dependency_graph(), SemanticNodeRef(node_type, node_id))

    def semantic_dependency_lineage(self, node_type: str, node_id: str) -> dict[str, Any]:
        return dependency_lineage_report(self.semantic_dependency_graph(), SemanticNodeRef(node_type, node_id))

    def semantic_memory_projection_signals(self) -> dict[str, Any]:
        return dependency_memory_signals(self.semantic_dependency_graph())

    def register_semantic_dependency(self, dependency: SemanticDependency | Mapping[str, Any], *, authority_id: str, authority_class: str, reason: str = "semantic dependency admitted") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("semantic dependency admission requires POLICY or CONTROLLER authority")
        if not authority_id:
            raise ValueError("authority_id is required")
        dependency = dependency if isinstance(dependency, SemanticDependency) else SemanticDependency.from_dict(dependency)
        graph = self.semantic_dependency_graph()
        if not graph["valid"]:
            raise RuntimeError(f"current semantic dependency graph is invalid: {graph['issues']}")
        for endpoint in (dependency.source.key, dependency.target.key):
            if endpoint not in graph["nodes"]:
                raise KeyError(f"unknown semantic dependency endpoint: {endpoint}")
        existing = {row.dependency_id: row for row in explicit_dependency_edges(self.snapshot.evidence.get("records", []))}
        if dependency.dependency_id in existing:
            prior = existing[dependency.dependency_id]
            if prior.fingerprint != dependency.fingerprint:
                raise ValueError(f"semantic dependency ID collision: {dependency.dependency_id}")
            return {"contract": semantic_dependency_contract(), "dependency": prior.to_dict(), "already_admitted": True, "graph_fingerprint": graph["graph_fingerprint"]}
        candidate = self.semantic_dependency_graph(explicit_edges=[dependency])
        if not candidate["valid"]:
            raise ValueError(f"semantic dependency rejected: {candidate['issues']}")
        stored = self.add_evidence(EvidenceRecord(
            kind="semantic_dependency",
            statement=semantic_dependency_document(dependency),
            source=SEMANTIC_DEPENDENCY_CONTRACT_ID,
            metadata={"semantic_dependency_record_type": "EDGE", "semantic_dependency_contract_id": SEMANTIC_DEPENDENCY_CONTRACT_ID, "dependency_id": dependency.dependency_id, "dependency_fingerprint": dependency.fingerprint, "authority_id": authority_id, "authority_class": authority_class, "scope_id": dependency.scope_id},
        ), reason=reason)
        result_graph = self.semantic_dependency_graph()
        if not result_graph["valid"]:
            raise RuntimeError(f"admitted dependency produced invalid graph: {result_graph['issues']}")
        return {"contract": semantic_dependency_contract(), "dependency": dependency.to_dict(), "evidence_id": stored.evidence_id, "already_admitted": False, "graph_fingerprint": result_graph["graph_fingerprint"]}

    def register_causal_decision(self, record: CausalDecisionRecord | Mapping[str, Any], *, reason: str = "causal decision registered") -> dict[str, Any]:
        record = record if isinstance(record, CausalDecisionRecord) else CausalDecisionRecord(**deepcopy(dict(record)))
        known_events = {str(event.event_id) for event in self.events}
        missing_events = sorted(set(record.caused_by_event_ids) - known_events)
        if missing_events:
            raise KeyError(f"unknown causal event IDs: {missing_events}")
        known_artifacts = set(self.reasoning_report().get("artifacts", {}))
        missing_artifacts = sorted(set(record.caused_by_artifact_ids) - known_artifacts)
        if missing_artifacts:
            raise KeyError(f"unknown causal artifact IDs: {missing_artifacts}")
        registered = self.register_decision(record, reason=reason)
        return {"contract_id": CAUSAL_DECISION_CONTRACT_ID, "decision": registered, "causal_fingerprint": record.causal_fingerprint}

    def register_reactive_obligation_rule(self, rule: ReactiveObligationRule | Mapping[str, Any], *, authority_id: str, authority_class: str, reason: str = "reactive obligation rule admitted") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("reactive rule admission requires POLICY or CONTROLLER authority")
        if not authority_id:
            raise ValueError("authority_id is required")
        rule = rule if isinstance(rule, ReactiveObligationRule) else ReactiveObligationRule.from_dict(rule)
        calculus = self.calculus_report()
        missing_decisions = sorted(set(rule.decision_dependencies) - set(calculus["decisions"]))
        if missing_decisions:
            raise KeyError(f"unknown reactive rule decision dependencies: {missing_decisions}")
        existing = {item.rule_id: (item, evidence_id) for item, evidence_id in reactive_rules_from_evidence(self.snapshot.evidence.get("records", []))}
        if rule.rule_id in existing:
            prior, evidence_id = existing[rule.rule_id]
            if prior.fingerprint != rule.fingerprint:
                raise ValueError(f"reactive rule ID collision: {rule.rule_id}")
            return {"contract_id": REACTIVE_OBLIGATION_CONTRACT_ID, "rule": prior.to_dict(), "evidence_id": evidence_id, "already_admitted": True}
        stored = self.add_evidence(EvidenceRecord(
            kind="reactive_obligation_rule",
            statement=semantic_dependency_document(rule),
            source=REACTIVE_OBLIGATION_CONTRACT_ID,
            metadata={"semantic_dependency_record_type": "REACTIVE_RULE", "reactive_contract_id": REACTIVE_OBLIGATION_CONTRACT_ID, "rule_id": rule.rule_id, "rule_fingerprint": rule.fingerprint, "authority_id": authority_id, "authority_class": authority_class, "scope_id": rule.scope_id},
        ), reason=reason)
        return {"contract_id": REACTIVE_OBLIGATION_CONTRACT_ID, "rule": rule.to_dict(), "evidence_id": stored.evidence_id, "already_admitted": False}

    @staticmethod
    def _event_matches_reactive_rule(event: Any, rule: ReactiveObligationRule) -> bool:
        if str(getattr(event, "event_type", "")) not in set(rule.watch_event_types):
            return False
        data = getattr(event, "data", {}) or {}
        return all(data.get(key) == value for key, value in rule.event_data_equals.items())

    @staticmethod
    def _reactive_obligation_id(rule_id: str, event_id: str) -> str:
        return "reactive-obligation-" + semantic_fingerprint({"rule_id": rule_id, "event_id": event_id})[:20]

    def reactive_obligation_report(self) -> dict[str, Any]:
        rules = reactive_rules_from_evidence(self.snapshot.evidence.get("records", []))
        obligations = self.calculus_report()["obligations"]
        reactive = {obligation_id: deepcopy(row) for obligation_id, row in obligations.items() if row.get("reactive_rule_id")}
        return {"contract_id": REACTIVE_OBLIGATION_CONTRACT_ID, "rules": {rule.rule_id: {"rule": rule.to_dict(), "evidence_id": evidence_id} for rule, evidence_id in rules}, "obligations": reactive, "handler_execution": "NONE"}

    def derive_reactive_obligations(self, *, from_sequence: int = 0, reason: str = "reactive obligation derived") -> dict[str, Any]:
        if from_sequence < 0:
            raise ValueError("from_sequence must be non-negative")
        rules = reactive_rules_from_evidence(self.snapshot.evidence.get("records", []))
        existing = self.calculus_report()["obligations"]
        created, skipped = [], []
        for rule, rule_evidence_id in sorted(rules, key=lambda item: item[0].rule_id):
            prior_for_rule = [row for row in existing.values() if row.get("reactive_rule_id") == rule.rule_id]
            if rule.once and prior_for_rule:
                skipped.append({"rule_id": rule.rule_id, "reason": "once_rule_already_derived"})
                continue
            for event in sorted(self.events, key=lambda row: int(row.sequence or 0)):
                sequence = int(event.sequence or 0)
                if sequence < from_sequence or not self._event_matches_reactive_rule(event, rule):
                    continue
                obligation_id = self._reactive_obligation_id(rule.rule_id, str(event.event_id))
                if obligation_id in existing:
                    skipped.append({"rule_id": rule.rule_id, "event_id": event.event_id, "obligation_id": obligation_id, "reason": "already_derived"})
                    if rule.once:
                        break
                    continue
                record = ReactiveObligationRecord(
                    obligation_id=obligation_id,
                    statement=rule.statement,
                    status="AVAILABLE",
                    decision_dependencies=list(rule.decision_dependencies),
                    required_evidence_types=list(rule.required_evidence_types),
                    scope={"scope_id": rule.scope_id},
                    reactive_rule_id=rule.rule_id,
                    trigger_event_id=str(event.event_id),
                    trigger_event_type=str(event.event_type),
                    handler_name=rule.handler_name,
                )
                registered = self.register_obligation(record, reason=reason)
                derived_evidence = self.add_evidence(EvidenceRecord(
                    kind="reactive_obligation_derived",
                    statement=canonical_semantic_json({"rule_id": rule.rule_id, "rule_fingerprint": rule.fingerprint, "trigger_event_id": event.event_id, "trigger_event_type": event.event_type, "trigger_sequence": event.sequence, "obligation_id": obligation_id, "handler_name": rule.handler_name, "handler_execution": "NONE"}),
                    source=REACTIVE_OBLIGATION_CONTRACT_ID,
                    derived_from=[rule_evidence_id] if rule_evidence_id else [],
                    metadata={"semantic_dependency_record_type": "REACTIVE_DERIVATION", "reactive_contract_id": REACTIVE_OBLIGATION_CONTRACT_ID, "rule_id": rule.rule_id, "obligation_id": obligation_id, "trigger_event_id": event.event_id, "handler_execution": "NONE"},
                ), reason=reason)
                created.append({"rule": rule.to_dict(), "obligation": registered, "derivation_evidence_id": derived_evidence.evidence_id, "handler_execution": "NONE"})
                existing[obligation_id] = deepcopy(registered)
                if rule.once:
                    break
        return {"contract_id": REACTIVE_OBLIGATION_CONTRACT_ID, "created": created, "skipped": skipped, "handler_execution": "NONE"}

    def truth_maintenance_report(self) -> dict[str, Any]:
        return {"contract_id": TRUTH_MAINTENANCE_CONTRACT_ID, **truth_records_from_evidence(self.snapshot.evidence.get("records", []))}

    def _find_matching_truth_plan(self, root: SemanticNodeRef, *, reason: str, authority_id: str, authority_class: str, evidence_ids: Sequence[str]) -> tuple[TruthMaintenancePlan, str] | None:
        records = truth_records_from_evidence(self.snapshot.evidence.get("records", []))
        normalized_evidence = tuple(sorted(set(str(value) for value in evidence_ids)))
        for row in records["plans"].values():
            plan = TruthMaintenancePlan.from_dict(row["plan"])
            if plan.root.key == root.key and plan.reason == reason and plan.authority_id == authority_id and plan.authority_class == authority_class and tuple(plan.evidence_ids) == normalized_evidence:
                return plan, str(row["evidence_id"])
        return None

    def _apply_truth_plan(self, plan: TruthMaintenancePlan, *, plan_evidence_id: str, reason: str = "truth maintenance applied") -> dict[str, Any]:
        records = truth_records_from_evidence(self.snapshot.evidence.get("records", []))
        if plan.plan_id in records["applied"]:
            row = records["applied"][plan.plan_id]
            return {"contract_id": TRUTH_MAINTENANCE_CONTRACT_ID, "plan": plan.to_dict(), "already_applied": True, "application": deepcopy(row["result"]), "application_evidence_id": row["evidence_id"]}
        current_graph = self.semantic_dependency_graph()
        if not current_graph["valid"]:
            raise RuntimeError(f"cannot apply truth maintenance on invalid graph: {current_graph['issues']}")
        generated_evidence_ids, stale_artifacts, preserved_terminal_artifacts = [], [], []
        affected_decisions, reopened_obligations, preserved_obligations = [], [], []
        for ref in plan.affected_nodes:
            if ref.node_type != "ARTIFACT":
                continue
            try:
                entry = self.reasoning_report(ref.node_id)
            except KeyError:
                continue
            state = entry["state"]
            if state == "STALE":
                stale_artifacts.append(ref.node_id); continue
            if state in {"REFUTED", "REJECTED"}:
                preserved_terminal_artifacts.append(ref.node_id); continue
            result = self.mark_stale(ref.node_id, reason=plan.reason, authority_id=plan.authority_id, authority_class=plan.authority_class, evidence_ids=list(plan.evidence_ids))
            stale_artifacts.append(ref.node_id)
            if result.get("transition_evidence_id"):
                generated_evidence_ids.append(str(result["transition_evidence_id"]))
        calculus = self._begin_calculus()
        calculus_changed = False
        affected_keys = {ref.key for ref in plan.affected_nodes}
        decisions, obligations = calculus.get("decisions", {}), calculus.get("obligations", {})
        for decision_id, decision in decisions.items():
            if f"DECISION:{decision_id}" not in affected_keys or decision.get("status") in {"INVALIDATED", "SUPERSEDED", "REJECTED", "HISTORICAL"}:
                continue
            decision["status"] = "INVALIDATED"
            decision["invalidated_by_dependency_id"] = plan.plan_id
            decision["invalidation_reason"] = plan.reason
            affected_decisions.append(decision_id); calculus_changed = True
        invalidated = set(affected_decisions)
        if invalidated:
            for scope_id, model in list(calculus.get("scope_active_models", {}).items()):
                calculus["scope_active_models"][scope_id] = {subject: decision_id for subject, decision_id in model.items() if decision_id not in invalidated}
            calculus["active_model"] = deepcopy(calculus.get("scope_active_models", {}).get("root", {}))
        for obligation_id, obligation in obligations.items():
            if f"OBLIGATION:{obligation_id}" not in affected_keys:
                continue
            status = obligation.get("status")
            if status in {"REJECTED", "SUPERSEDED", "IMPOSSIBLE"}:
                preserved_obligations.append(obligation_id); continue
            if status == "NEEDS_REVALIDATION":
                reopened_obligations.append(obligation_id); continue
            if "NEEDS_REVALIDATION" in OBLIGATION_TRANSITIONS.get(status, set()):
                obligation["status"] = "NEEDS_REVALIDATION"
                obligation["last_state_change_sequence"] = self._sequence() + 1
                obligation["disposition_reason"] = f"truth maintenance {plan.plan_id}: {plan.reason}"
                reopened_obligations.append(obligation_id); calculus_changed = True
            else:
                preserved_obligations.append(obligation_id)
        calculus, broken_locks = reevaluate_locks(calculus)
        if broken_locks:
            calculus_changed = True
        if calculus_changed:
            self._commit_calculus(calculus, f"truth maintenance calculus update: {plan.plan_id}")
        result = {"plan_id": plan.plan_id, "root": plan.root.to_dict(), "reason": plan.reason, "stale_artifact_ids": sorted(set(stale_artifacts)), "preserved_terminal_artifact_ids": sorted(set(preserved_terminal_artifacts)), "invalidated_decision_ids": sorted(set(affected_decisions)), "reopened_obligation_ids": sorted(set(reopened_obligations)), "preserved_obligation_ids": sorted(set(preserved_obligations)), "broken_lock_ids": sorted(set(broken_locks)), "handler_execution": "NONE"}
        stored = self.add_evidence(EvidenceRecord(
            kind="truth_maintenance_applied",
            statement=canonical_semantic_json(result),
            source=TRUTH_MAINTENANCE_CONTRACT_ID,
            derived_from=sorted(set([plan_evidence_id, *plan.evidence_ids, *generated_evidence_ids])),
            metadata={"semantic_dependency_record_type": "TRUTH_APPLIED", "truth_contract_id": TRUTH_MAINTENANCE_CONTRACT_ID, "plan_id": plan.plan_id, "result_fingerprint": semantic_fingerprint(result), "authority_id": plan.authority_id, "authority_class": plan.authority_class, "handler_execution": "NONE"},
        ), reason=reason)
        return {"contract_id": TRUTH_MAINTENANCE_CONTRACT_ID, "plan": plan.to_dict(), "already_applied": False, "application": result, "application_evidence_id": stored.evidence_id}

    def apply_truth_change(self, node_type: str, node_id: str, *, reason: str, authority_id: str, authority_class: str, evidence_ids: Sequence[str] = ()) -> dict[str, Any]:
        if authority_class not in {"VERIFIER", "POLICY", "CONTROLLER"}:
            raise PermissionError("truth maintenance requires VERIFIER, POLICY, or CONTROLLER authority")
        if not authority_id:
            raise ValueError("authority_id is required")
        evidence_ids = self._require_evidence_ids(evidence_ids)
        root = SemanticNodeRef(node_type, node_id)
        existing = self._find_matching_truth_plan(root, reason=reason, authority_id=authority_id, authority_class=authority_class, evidence_ids=evidence_ids)
        if existing is not None:
            plan, evidence_id = existing
            return self._apply_truth_plan(plan, plan_evidence_id=evidence_id)
        graph = self.semantic_dependency_graph()
        impact = dependency_impact_report(graph, root)
        plan = TruthMaintenancePlan(
            root=root,
            affected_nodes=tuple(SemanticNodeRef(row["node_type"], row["node_id"]) for row in impact["affected_nodes"]),
            reason=reason,
            authority_id=authority_id,
            authority_class=authority_class,
            graph_fingerprint=graph["graph_fingerprint"],
            evidence_ids=tuple(evidence_ids),
        )
        stored = self.add_evidence(EvidenceRecord(
            kind="truth_maintenance_plan",
            statement=semantic_dependency_document(plan),
            source=TRUTH_MAINTENANCE_CONTRACT_ID,
            derived_from=list(evidence_ids),
            metadata={"semantic_dependency_record_type": "TRUTH_PLAN", "truth_contract_id": TRUTH_MAINTENANCE_CONTRACT_ID, "plan_id": plan.plan_id, "plan_fingerprint": plan.fingerprint, "root_key": root.key, "authority_id": authority_id, "authority_class": authority_class},
        ), reason=f"truth maintenance plan recorded: {reason}")
        return self._apply_truth_plan(plan, plan_evidence_id=stored.evidence_id)

    def resume_truth_maintenance(self, plan_id: str) -> dict[str, Any]:
        records = truth_records_from_evidence(self.snapshot.evidence.get("records", []))
        if plan_id in records["applied"]:
            row = records["applied"][plan_id]; plan_row = records["plans"].get(plan_id)
            return {"contract_id": TRUTH_MAINTENANCE_CONTRACT_ID, "plan": deepcopy(plan_row["plan"]) if plan_row else None, "already_applied": True, "application": deepcopy(row["result"]), "application_evidence_id": row["evidence_id"]}
        try:
            row = records["plans"][plan_id]
        except KeyError:
            raise KeyError(plan_id) from None
        return self._apply_truth_plan(TruthMaintenancePlan.from_dict(row["plan"]), plan_evidence_id=str(row["evidence_id"]), reason="truth maintenance resumed")


__all__ = ["SemanticDependencyRuntimeMixin"]
