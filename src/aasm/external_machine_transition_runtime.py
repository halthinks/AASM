from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .effects import EffectIntent, EffectSpec, EffectStatus, RetryPolicy
from .evidence import EvidenceRecord
from .external_machine import MachineBinding
from .external_machine_transition import (
    MACHINE_TRANSITION_CONTRACT_ID,
    MachineTransitionIntent,
    machine_transition_contract,
)
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import StateClaim


MACHINE_TRANSITION_RUNTIME_CONTRACT_ID = "aasm.machine.transition.runtime.v1"
MACHINE_TRANSITION_RUNTIME_CONTRACT_VERSION = "0.1.0"
MACHINE_TRANSITION_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

MACHINE_TRANSITION_CAPABILITIES = {
    "transition_propose": "machine.transition.propose",
}

_MACHINE_TRANSITION_RECORD_TYPE = "aasm_machine_transition_record_type"
_MACHINE_TRANSITION_DOCUMENT = "document"
_MACHINE_TRANSITION_INTENT_RECORD = "MACHINE_TRANSITION_INTENT"


def machine_transition_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": MACHINE_TRANSITION_RUNTIME_CONTRACT_ID,
        "contract_version": MACHINE_TRANSITION_RUNTIME_CONTRACT_VERSION,
        "stability": MACHINE_TRANSITION_RUNTIME_STABILITY,
        "semantic_contract": machine_transition_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(MACHINE_TRANSITION_CAPABILITIES),
        "effect_proposal_path": "EXISTING_AASM_PROPOSE_EFFECT_ONLY",
        "effect_intent_path": "EXISTING_V054_EFFECT_INTENT_ONLY",
        "effect_authorization": "NOT_PERFORMED_USE_EXISTING_AUTHORIZE_EFFECT",
        "effect_dispatch": "NOT_PERFORMED_USE_EXISTING_EXECUTE_EFFECT",
        "effect_ownership": "NOT_CREATED_BY_THIS_RUNTIME",
        "effect_reconciliation": "NOT_CREATED_BY_THIS_RUNTIME",
        "transition_status_store": "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD",
        "parallel_dispatcher": "NONE",
        "parallel_effect_store": "NONE",
        "machine_state_mutation": "NONE",
        "postcondition_verification": "NOT_IMPLEMENTED_PR2B_RESERVED_FOR_PR2C",
        "command_success_is_achievement": False,
        "transition_proposal_grants_effect_authority": False,
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_MACHINE_TRANSITION_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("machine-transition Evidence is missing canonical document")


def project_machine_transition_evidence(records) -> dict[str, Any]:
    transitions: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        if metadata.get(_MACHINE_TRANSITION_RECORD_TYPE) != _MACHINE_TRANSITION_INTENT_RECORD:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            item = MachineTransitionIntent.from_dict(_document(row))
            if metadata.get("object_id") != item.transition_id:
                raise ValueError(f"machine-transition metadata object_id mismatch: {item.transition_id}")
            if metadata.get("object_fingerprint") != item.fingerprint:
                raise ValueError(f"machine-transition metadata fingerprint mismatch: {item.transition_id}")
            candidate = {"transition": item.to_dict(), "evidence_id": evidence_id}
            prior = transitions.get(item.transition_id)
            if prior is not None and prior != candidate:
                raise ValueError(f"machine transition identity collision: {item.transition_id}")
            transitions[item.transition_id] = candidate
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": _MACHINE_TRANSITION_INTENT_RECORD,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "runtime_contract": machine_transition_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "transitions": transitions,
    }


def _claim_condition(claim: StateClaim) -> dict[str, Any]:
    return {
        "contract_id": "aasm.machine.transition.state-condition.v1",
        "claim_id": claim.claim_id,
        "claim_fingerprint": claim.fingerprint,
        "claim_kind": claim.claim_kind,
        "workspace_id": claim.workspace_id,
        "scope_id": claim.scope_id,
        "subject_id": claim.subject_id,
        "state_namespace": claim.state_namespace,
        "value": deepcopy(claim.value),
        "problem_revision_id": claim.problem_revision_id,
        "external_revision_id": claim.external_revision_id,
    }


class MachineTransitionRuntimeMixin:
    def machine_transition_contract_report(self) -> dict[str, Any]:
        return machine_transition_runtime_contract()

    def _machine_transition_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_machine_transition_evidence(records)

    def _require_valid_machine_transition_projection(self) -> dict[str, Any]:
        report = self._machine_transition_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable machine-transition projection: {report['issues']}")
        return report

    def _record_machine_transition_document(
        self,
        item: MachineTransitionIntent,
        *,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = item.to_dict()
        evidence_id = f"machine-transition-evidence-{semantic_fingerprint(payload)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_MACHINE_TRANSITION_RECORD_TYPE) != _MACHINE_TRANSITION_INTENT_RECORD
                or metadata.get(_MACHINE_TRANSITION_DOCUMENT) != payload
                or metadata.get("object_id") != item.transition_id
                or metadata.get("object_fingerprint") != item.fingerprint
            ):
                raise ValueError(f"machine-transition Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="machine_transition",
            statement=canonical_semantic_json(payload),
            source=MACHINE_TRANSITION_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _MACHINE_TRANSITION_RECORD_TYPE: _MACHINE_TRANSITION_INTENT_RECORD,
                _MACHINE_TRANSITION_DOCUMENT: payload,
                "object_id": item.transition_id,
                "object_fingerprint": item.fingerprint,
                "effect_id": item.effect_id,
                "effect_intent_id": item.effect_intent_id,
                "effect_authorization": "NOT_PERFORMED",
                "effect_dispatch": "NOT_PERFORMED",
                "effect_ownership": "NOT_CREATED",
                "machine_state_mutation": "NONE",
                "postcondition_verification": "NOT_IMPLEMENTED_PR2B",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(
            record,
            expected_machine_version=self.snapshot.version,
            reason=reason,
        )
        return evidence_id

    def _transition_claim_rows(
        self,
        claim_ids: Sequence[str],
        *,
        binding: MachineBinding,
        required_kind: str,
    ) -> list[tuple[StateClaim, dict[str, Any]]]:
        rows: list[tuple[StateClaim, dict[str, Any]]] = []
        seen_namespaces: set[str] = set()
        for claim_id in tuple(sorted(set(map(str, claim_ids)))):
            row = self.state_claim_report(claim_id)
            claim = StateClaim.from_dict(row["claim"])
            if claim.claim_kind != required_kind:
                raise ValueError(
                    f"machine transition {required_kind} state requires {required_kind} claim, got {claim.claim_kind}"
                )
            if claim.workspace_id != binding.workspace_id or claim.scope_id != binding.scope_id:
                raise ValueError("machine transition state claim workspace/scope does not match binding")
            if claim.subject_id != binding.subject_id:
                raise ValueError("machine transition state claim subject does not match binding")
            if claim.state_namespace not in binding.state_namespaces:
                raise ValueError("machine transition state claim namespace is not supported by binding")
            if claim.external_revision_id != binding.external_revision_id:
                raise ValueError("machine transition state claim external revision does not match binding")
            if binding.problem_revision_id and claim.problem_revision_id != binding.problem_revision_id:
                raise ValueError("machine transition state claim problem revision does not match binding")
            if claim.state_namespace in seen_namespaces:
                raise ValueError(
                    f"machine transition contains multiple {required_kind} claims for namespace {claim.state_namespace}"
                )
            seen_namespaces.add(claim.state_namespace)
            rows.append((claim, row))
        if not rows:
            raise ValueError(f"machine transition requires at least one {required_kind} state claim")
        return rows

    def propose_machine_transition(
        self,
        binding_id: str,
        *,
        operation: str,
        expected_state_claim_ids: Sequence[str],
        target_state_claim_ids: Sequence[str],
        external_revision_id: str,
        proposer_principal_id: str,
        payload: Mapping[str, Any] | None = None,
        resource_reservation_ids: Sequence[str] = (),
        reversible: bool = False,
        compensation: Mapping[str, Any] | None = None,
        metadata: Mapping[str, Any] | None = None,
        at_time: float = 0.0,
        reason: str = "machine transition proposed",
    ) -> dict[str, Any]:
        binding_row = self.machine_binding_report(binding_id)
        binding = MachineBinding.from_dict(binding_row["binding"])
        if str(external_revision_id).strip() != binding.external_revision_id:
            raise ValueError("machine transition external revision does not match binding")
        if not str(operation).strip():
            raise ValueError("machine transition operation is required")
        if not str(proposer_principal_id).strip():
            raise PermissionError("machine transition proposer_principal_id is required")

        expected = self._transition_claim_rows(
            expected_state_claim_ids,
            binding=binding,
            required_kind="AUTHORITATIVE",
        )
        targets = self._transition_claim_rows(
            target_state_claim_ids,
            binding=binding,
            required_kind="DESIRED",
        )
        expected_namespaces = {claim.state_namespace for claim, _ in expected}
        target_namespaces = {claim.state_namespace for claim, _ in targets}
        if not target_namespaces.issubset(expected_namespaces):
            raise ValueError("machine transition target namespaces require corresponding authoritative pre-state claims")

        reservations = tuple(sorted({str(value).strip() for value in resource_reservation_ids if str(value).strip()}))
        request_payload = {
            "binding_id": binding.binding_id,
            "binding_fingerprint": binding.fingerprint,
            "operation": str(operation).strip(),
            "expected_state_claims": [
                {"claim_id": claim.claim_id, "fingerprint": claim.fingerprint}
                for claim, _ in expected
            ],
            "target_state_claims": [
                {"claim_id": claim.claim_id, "fingerprint": claim.fingerprint}
                for claim, _ in targets
            ],
            "external_revision_id": binding.external_revision_id,
            "executor_capability_id": binding.executor_capability_id,
            "payload": deepcopy(dict(payload or {})),
            "resource_reservation_ids": list(reservations),
            "reversible": bool(reversible),
            "compensation": None if compensation is None else deepcopy(dict(compensation)),
            "proposer_principal_id": proposer_principal_id,
            "metadata": deepcopy(dict(metadata or {})),
        }
        request_fingerprint = semantic_fingerprint(request_payload)
        authorization = self._authorize_external_machine_action(
            actor_principal_id=proposer_principal_id,
            workspace_id=binding.workspace_id,
            scope_id=binding.scope_id,
            capability=MACHINE_TRANSITION_CAPABILITIES["transition_propose"],
            at_time=at_time,
            metadata={
                "binding_id": binding.binding_id,
                "operation": str(operation).strip(),
                "transition_request_fingerprint": request_fingerprint,
            },
            derived_from=tuple(
                sorted(
                    {
                        str(binding_row["evidence_id"]),
                        *[str(row["evidence_id"]) for _, row in expected],
                        *[str(row["evidence_id"]) for _, row in targets],
                    }
                )
            ),
        )

        effect_id = f"effect-machine-transition-{request_fingerprint[:24]}"
        idempotency_key = f"machine-transition-{request_fingerprint}"
        spec = EffectSpec(
            "machine.transition",
            payload={
                "binding_id": binding.binding_id,
                "external_machine_id": binding.external_machine_id,
                "subject_id": binding.subject_id,
                "operation": str(operation).strip(),
                "external_revision_id": binding.external_revision_id,
                "executor_capability_id": binding.executor_capability_id,
                "command": deepcopy(dict(payload or {})),
            },
            idempotency_key=idempotency_key,
            preconditions=[_claim_condition(claim) for claim, _ in expected],
            postconditions=[_claim_condition(claim) for claim, _ in targets],
            retry_policy=RetryPolicy(max_attempts=1, retry_on_failure=False, retry_on_unknown=False),
            reversible=bool(reversible),
            compensation=None if compensation is None else deepcopy(dict(compensation)),
            effect_id=effect_id,
        )
        effect_record = self.propose_effect(
            spec,
            workspace_id=binding.workspace_id,
            scope_id=binding.scope_id,
            proposer_principal_id=proposer_principal_id,
            resource_reservation_ids=reservations,
            intent_metadata={
                "machine_transition_contract_id": MACHINE_TRANSITION_CONTRACT_ID,
                "machine_transition_request_fingerprint": request_fingerprint,
                "machine_binding_id": binding.binding_id,
                "machine_binding_fingerprint": binding.fingerprint,
                "external_revision_id": binding.external_revision_id,
                "executor_capability_id": binding.executor_capability_id,
                "transition_proposal_authority_evidence_id": authorization["evidence_id"],
            },
        )
        if effect_record.status != EffectStatus.PROPOSED.value:
            raise RuntimeError("machine transition proposal unexpectedly advanced existing effect lifecycle")
        if effect_record.intent is None:
            raise RuntimeError("existing propose_effect path did not produce a durable EffectIntent")
        if effect_record.authorization_id or effect_record.dispatch_request or effect_record.ownership or effect_record.reconciliation:
            raise RuntimeError("machine transition proposal crossed authorization/dispatch/ownership boundary")
        effect_intent = EffectIntent.from_dict(effect_record.intent)

        item = MachineTransitionIntent(
            workspace_id=binding.workspace_id,
            scope_id=binding.scope_id,
            binding_id=binding.binding_id,
            operation=str(operation).strip(),
            expected_state_claim_ids=tuple(claim.claim_id for claim, _ in expected),
            target_state_claim_ids=tuple(claim.claim_id for claim, _ in targets),
            external_revision_id=binding.external_revision_id,
            effect_id=effect_record.spec.effect_id,
            effect_intent_id=effect_intent.intent_id,
            effect_intent_fingerprint=effect_intent.fingerprint,
            proposer_principal_id=proposer_principal_id,
            resource_reservation_ids=reservations,
            metadata={
                "request_fingerprint": request_fingerprint,
                "executor_capability_id": binding.executor_capability_id,
                **deepcopy(dict(metadata or {})),
            },
        )
        projection = self._require_valid_machine_transition_projection()
        prior = projection["transitions"].get(item.transition_id)
        if prior is not None:
            if prior["transition"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"machine transition identity collision: {item.transition_id}")
            return {
                **deepcopy(prior),
                "effect": self._machine_transition_effect_projection(item),
                "already_proposed": True,
            }

        lineage = {
            str(binding_row["evidence_id"]),
            str(authorization["evidence_id"]),
            *[str(row["evidence_id"]) for _, row in expected],
            *[str(row["evidence_id"]) for _, row in targets],
            *map(str, effect_record.evidence),
        }
        evidence_id = self._record_machine_transition_document(
            item,
            derived_from=tuple(sorted(lineage)),
            reason=reason,
        )
        return {
            "transition": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "effect": self._machine_transition_effect_projection(item),
            "already_proposed": False,
            "effect_authority_granted": False,
            "effect_authorized": False,
            "effect_dispatched": False,
            "effect_ownership_created": False,
            "postcondition_verified": False,
        }

    def _machine_transition_effect_projection(self, item: MachineTransitionIntent) -> dict[str, Any]:
        record = self.store.load_effect(self.snapshot.machine_id, item.effect_id)
        if record.intent is None:
            raise RuntimeError("machine transition effect lost durable EffectIntent")
        intent = EffectIntent.from_dict(record.intent)
        if intent.intent_id != item.effect_intent_id or intent.fingerprint != item.effect_intent_fingerprint:
            raise RuntimeError("machine transition no longer matches durable EffectIntent")
        return {
            "effect_id": record.spec.effect_id,
            "effect_status": record.status,
            "effect_intent": deepcopy(record.intent),
            "authorization_id": record.authorization_id,
            "dispatch_request": deepcopy(record.dispatch_request),
            "ownership": deepcopy(record.ownership),
            "reconciliation": deepcopy(record.reconciliation),
            "status_source": "EXISTING_AASM_EFFECT_RECORD",
        }

    def machine_transition_report(self, transition_id: str) -> dict[str, Any]:
        projection = self._require_valid_machine_transition_projection()
        try:
            row = deepcopy(projection["transitions"][transition_id])
        except KeyError:
            raise KeyError(f"unknown machine transition: {transition_id}") from None
        item = MachineTransitionIntent.from_dict(row["transition"])
        row["effect"] = self._machine_transition_effect_projection(item)
        row["runtime_contract"] = machine_transition_runtime_contract()
        return row

    def machine_transitions_report(self) -> dict[str, Any]:
        projection = self._require_valid_machine_transition_projection()
        transitions: dict[str, Any] = {}
        for transition_id, raw in projection["transitions"].items():
            row = deepcopy(raw)
            row["effect"] = self._machine_transition_effect_projection(
                MachineTransitionIntent.from_dict(row["transition"])
            )
            transitions[transition_id] = row
        return {
            "runtime_contract": machine_transition_runtime_contract(),
            "valid": True,
            "transitions": transitions,
            "transition_status_store": "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD",
            "parallel_dispatcher": "NONE",
            "machine_state_mutation": "NONE",
            "postcondition_verification": "NOT_IMPLEMENTED_PR2B_RESERVED_FOR_PR2C",
        }


__all__ = [
    "MACHINE_TRANSITION_RUNTIME_CONTRACT_ID",
    "MACHINE_TRANSITION_RUNTIME_CONTRACT_VERSION",
    "MACHINE_TRANSITION_RUNTIME_STABILITY",
    "MACHINE_TRANSITION_CAPABILITIES",
    "MachineTransitionRuntimeMixin",
    "project_machine_transition_evidence",
    "machine_transition_runtime_contract",
]
