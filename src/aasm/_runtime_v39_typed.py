from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .calculus import ObligationRecord
from .evidence import EvidenceRecord
from .semantic_dependencies import CausalDecisionRecord
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .typed_capabilities import TYPED_PROTOCOL_CONTRACT_ID, PatternMachine, typed_protocol_contract, capability_abi_contract, formal_verification_contract, pattern_document


def _records(snapshot, kind: str):
    return [deepcopy(row) for row in snapshot.evidence.get("records", []) if row.get("kind") == kind and row.get("status", "active") == "active"]


def _document(row):
    import json
    return json.loads(str(row["statement"]))


class TypedProtocolRuntimeMixin:
    def typed_protocol_contract_report(self) -> dict[str, Any]: return typed_protocol_contract()
    def capability_abi_contract_report(self) -> dict[str, Any]: return capability_abi_contract()
    def formal_verification_contract_report(self) -> dict[str, Any]: return formal_verification_contract()

    def typed_pattern_report(self, pattern_id: str | None = None) -> dict[str, Any]:
        patterns = {}
        for row in _records(self.snapshot, "typed_pattern"):
            pattern = PatternMachine.from_dict(_document(row))
            patterns[pattern.pattern_id] = {"pattern": pattern.to_dict(), "evidence_id": row["evidence_id"], "authority_id": (row.get("metadata") or {}).get("authority_id"), "authority_class": (row.get("metadata") or {}).get("authority_class")}
        if pattern_id is not None:
            if pattern_id not in patterns: raise KeyError(pattern_id)
            return {"contract": typed_protocol_contract(), **deepcopy(patterns[pattern_id])}
        return {"contract": typed_protocol_contract(), "patterns": patterns}

    def admit_typed_pattern(self, pattern: PatternMachine | Mapping[str, Any], *, authority_id: str, authority_class: str, reason: str = "typed pattern admitted") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}: raise PermissionError("typed pattern admission requires POLICY or CONTROLLER authority")
        if not authority_id: raise ValueError("authority_id is required")
        pattern = pattern if isinstance(pattern, PatternMachine) else PatternMachine.from_dict(pattern)
        scope_records = (self._begin_calculus().get("scope_state") or {}).get("records") or {}
        if pattern.scope_id not in scope_records:
            raise KeyError(f"unknown typed pattern scope: {pattern.scope_id}")
        existing = self.typed_pattern_report()["patterns"]
        if pattern.pattern_id in existing:
            prior = PatternMachine.from_dict(existing[pattern.pattern_id]["pattern"])
            if prior.fingerprint != pattern.fingerprint: raise ValueError(f"typed pattern ID collision: {pattern.pattern_id}")
            return {"contract": typed_protocol_contract(), **existing[pattern.pattern_id], "already_admitted": True}
        stored = self.add_evidence(EvidenceRecord(kind="typed_pattern", statement=pattern_document(pattern), source=TYPED_PROTOCOL_CONTRACT_ID, metadata={"typed_protocol_record_type": "PATTERN", "typed_protocol_contract_id": TYPED_PROTOCOL_CONTRACT_ID, "pattern_id": pattern.pattern_id, "pattern_version": pattern.version, "pattern_fingerprint": pattern.fingerprint, "authority_id": authority_id, "authority_class": authority_class, "scope_id": pattern.scope_id}), reason=reason)
        return {"contract": typed_protocol_contract(), "pattern": pattern.to_dict(), "evidence_id": stored.evidence_id, "already_admitted": False}

    def _typed_transition_proposals(self):
        out = {}
        for row in _records(self.snapshot, "typed_transition_proposal"):
            raw = _document(row); out[str(raw["decision_id"])] = {"proposal": raw, "evidence_id": row["evidence_id"]}
        return out

    def typed_transition_report(self, decision_id: str | None = None) -> dict[str, Any]:
        proposals = self._typed_transition_proposals()
        if decision_id is not None:
            if decision_id not in proposals: raise KeyError(decision_id)
            return {"contract": typed_protocol_contract(), **deepcopy(proposals[decision_id])}
        return {"contract": typed_protocol_contract(), "proposals": deepcopy(proposals)}

    @staticmethod
    def _typed_state_subject(pattern: PatternMachine) -> str: return f"typed.pattern.{pattern.pattern_id}.state"

    def _typed_current_state(self, pattern: PatternMachine) -> tuple[str, str | None]:
        calculus = self._begin_calculus(); subject = self._typed_state_subject(pattern)
        model = (calculus.get("scope_active_models", {}) or {}).get(pattern.scope_id, {}) or {}
        if pattern.scope_id == "root" and not model: model = calculus.get("active_model", {}) or {}
        current_id = model.get(subject)
        if current_id:
            decision = calculus["decisions"].get(current_id)
            if decision and decision.get("status") == "ACTIVE": return str(decision.get("value")), str(current_id)
        return pattern.initial_state, None

    def propose_typed_transition(self, pattern_id: str, event_name: str, payload: Mapping[str, Any], *, proposer_id: str, evidence_ids: Sequence[str] = (), reason: str = "typed transition proposed") -> dict[str, Any]:
        pattern = PatternMachine.from_dict(self.typed_pattern_report(pattern_id)["pattern"]); event_schema = pattern.event_schema(event_name); event_schema.validate(dict(payload))
        missing = sorted(set(map(str, evidence_ids)) - set(self._evidence_ids(self.snapshot)))
        if missing: raise KeyError(f"unknown evidence IDs: {missing}")
        current_state, current_decision_id = self._typed_current_state(pattern); transition = pattern.transition_for(current_state, event_name)
        event_payload = {"pattern_id": pattern.pattern_id, "pattern_version": pattern.version, "pattern_fingerprint": pattern.fingerprint, "event_schema_id": event_schema.schema_id, "event_schema_fingerprint": event_schema.fingerprint, "event_name": event_name, "payload": deepcopy(dict(payload)), "from_state": current_state}
        event_evidence = self.add_evidence(EvidenceRecord(kind="typed_event", statement=canonical_semantic_json(event_payload), source=TYPED_PROTOCOL_CONTRACT_ID, derived_from=sorted(set(map(str, evidence_ids))), metadata={"typed_protocol_record_type": "EVENT", "typed_protocol_contract_id": TYPED_PROTOCOL_CONTRACT_ID, "pattern_id": pattern.pattern_id, "event_name": event_name, "event_schema_id": event_schema.schema_id, "event_schema_fingerprint": event_schema.fingerprint, "scope_id": pattern.scope_id}), reason=reason)
        causal_event_id = str(self.events[-1].event_id) if self.events else ""
        decision_id = "typed-decision-" + semantic_fingerprint({"pattern_id": pattern.pattern_id, "transition_id": transition.transition_id, "event_evidence_id": event_evidence.evidence_id})[:20]
        record = CausalDecisionRecord(decision_id=decision_id, subject=self._typed_state_subject(pattern), value=transition.to_state, kind="EXPLICIT", status="PROPOSED", evidence_ids=[event_evidence.evidence_id, *map(str, evidence_ids)], scope={"scope_id": pattern.scope_id}, rejected_alternatives=[], confidence=1.0, reasoning=f"typed transition {transition.from_state} --{event_name}--> {transition.to_state}", caused_by_event_ids=[causal_event_id] if causal_event_id else [])
        registered = self.register_causal_decision(record, reason=reason)
        obligation_specs = [(f"guard:{g}", (), g) for g in event_schema.guards]
        required_types = tuple(sorted(set([*event_schema.required_evidence_types, *transition.evidence_required])))
        if required_types: obligation_specs.append(("evidence_contract", required_types, "typed transition evidence contract"))
        obligation_specs.extend((f"transition:{s}", (), s) for s in transition.obligations_created)
        obligation_ids = []
        for index, (kind, required, statement) in enumerate(obligation_specs):
            obligation_id = "typed-obligation-" + semantic_fingerprint({"decision_id": decision_id, "index": index, "kind": kind, "statement": statement})[:20]
            if obligation_id not in self.calculus_report()["obligations"]:
                self.register_obligation(ObligationRecord(obligation_id=obligation_id, statement=statement, status="AVAILABLE", decision_dependencies=[decision_id], required_evidence_types=list(required), scope={"scope_id": pattern.scope_id}), reason="typed transition guard/evidence obligation registered")
            obligation_ids.append(obligation_id)
        proposal = {"decision_id": decision_id, "pattern_id": pattern.pattern_id, "pattern_version": pattern.version, "pattern_fingerprint": pattern.fingerprint, "transition_id": transition.transition_id, "transition_fingerprint": transition.fingerprint, "event_name": event_name, "event_evidence_id": event_evidence.evidence_id, "from_state": current_state, "to_state": transition.to_state, "prior_state_decision_id": current_decision_id, "obligation_ids": sorted(obligation_ids), "proposer_id": proposer_id, "activation": "POLICY_OR_CONTROLLER_ONLY"}
        proposal_evidence = self.add_evidence(EvidenceRecord(kind="typed_transition_proposal", statement=canonical_semantic_json(proposal), source=TYPED_PROTOCOL_CONTRACT_ID, derived_from=[event_evidence.evidence_id], metadata={"typed_protocol_record_type": "TRANSITION_PROPOSAL", "typed_protocol_contract_id": TYPED_PROTOCOL_CONTRACT_ID, "pattern_id": pattern.pattern_id, "decision_id": decision_id, "transition_id": transition.transition_id, "proposer_id": proposer_id, "scope_id": pattern.scope_id}), reason=reason)
        return {"contract": typed_protocol_contract(), "proposal": proposal, "decision": registered, "proposal_evidence_id": proposal_evidence.evidence_id}

    def authorize_typed_transition(self, decision_id: str, *, authority_id: str, authority_class: str, reason: str = "typed transition authorized") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}: raise PermissionError("typed transition activation requires POLICY or CONTROLLER authority")
        if not authority_id: raise ValueError("authority_id is required")
        proposal_row = self.typed_transition_report(decision_id); proposal = proposal_row["proposal"]; pattern = PatternMachine.from_dict(self.typed_pattern_report(proposal["pattern_id"])["pattern"])
        current_state, current_decision_id = self._typed_current_state(pattern)
        if current_state != proposal["from_state"]: raise ValueError(f"typed transition proposal is stale: expected {proposal['from_state']} but current state is {current_state}")
        calculus = self.calculus_report(); incomplete = [oid for oid in proposal["obligation_ids"] if calculus["obligations"].get(oid, {}).get("status") not in {"VERIFIED", "COMMITTED"}]
        if incomplete: raise ValueError(f"typed transition obligations are incomplete: {sorted(incomplete)}")
        activation = self.activate_decision(decision_id, supersede_decision_id=current_decision_id, reason=reason)
        parents = [proposal_row["evidence_id"]]
        for oid in proposal["obligation_ids"]: parents.extend(calculus["obligations"].get(oid, {}).get("evidence_ids", []))
        stored = self.add_evidence(EvidenceRecord(kind="typed_transition_authorized", statement=canonical_semantic_json({"decision_id": decision_id, "pattern_id": pattern.pattern_id, "from_state": proposal["from_state"], "to_state": proposal["to_state"], "authority_id": authority_id, "authority_class": authority_class}), source=TYPED_PROTOCOL_CONTRACT_ID, derived_from=sorted(set(parents)), metadata={"typed_protocol_record_type": "TRANSITION_AUTHORIZED", "typed_protocol_contract_id": TYPED_PROTOCOL_CONTRACT_ID, "pattern_id": pattern.pattern_id, "decision_id": decision_id, "authority_id": authority_id, "authority_class": authority_class}), reason=reason)
        return {"contract": typed_protocol_contract(), "activation": activation, "authorization_evidence_id": stored.evidence_id}
