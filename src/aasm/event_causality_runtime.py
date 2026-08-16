from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .event_causality import (
    EVENT_CAUSALITY_CONTRACT_ID,
    CausalEventIdentity,
    CausalRelation,
    event_causality_contract,
)
from .evidence import EvidenceRecord
from .external_machine import MachineBinding, MachineStateObservation
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import StateClaim


EVENT_CAUSALITY_RUNTIME_CONTRACT_ID = "aasm.event.causality.runtime.v1"
EVENT_CAUSALITY_RUNTIME_CONTRACT_VERSION = "0.1.0"
EVENT_CAUSALITY_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
EVENT_CAUSALITY_CAPABILITIES = {
    "record": "event.causality.record",
    "relate": "event.causality.relate",
}

_CAUSAL_RECORD_TYPE = "aasm_event_causality_record_type"
_CAUSAL_DOCUMENT = "document"
_CAUSAL_EVENT_RECORD = "CAUSAL_EVENT"
_CAUSAL_RELATION_RECORD = "CAUSAL_RELATION"


def event_causality_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": EVENT_CAUSALITY_RUNTIME_CONTRACT_ID,
        "contract_version": EVENT_CAUSALITY_RUNTIME_CONTRACT_VERSION,
        "stability": EVENT_CAUSALITY_RUNTIME_STABILITY,
        "semantic_contract": event_causality_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(EVENT_CAUSALITY_CAPABILITIES),
        "core_aasm_event_log": "UNCHANGED_AND_REMAINS_REPLAY_LEDGER",
        "causal_event_role": "EXTERNAL_SOURCE_COORDINATES_OVER_EXISTING_DURABLE_OBJECTS",
        "machine_observation_binding": "EXACT_EXISTING_MACHINE_STATE_OBSERVATION_AND_STATE_CLAIM_REQUIRED",
        "ingest_order": "MAY_DIFFER_FROM_SOURCE_SEQUENCE",
        "same_node_boot_order": "SEQUENCE_DEFINES_LOCAL_ORDER_INDEPENDENT_OF_INGEST_ORDER",
        "relation_consistency": "SAME_NODE_BOOT_RELATIONS_CANNOT_CONTRADICT_SEQUENCE_ORDER",
        "relation_inference": "NONE_BEYOND_EXPLICIT_LOCAL_SEQUENCE_CONSISTENCY",
        "fact_authority_creation": "NONE",
        "effect_authority": "NONE",
        "machine_state_mutation": "NONE",
        "parallel_event_ledger": "NONE",
        "parallel_truth_table": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_CAUSAL_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("causal Evidence is missing canonical document")


def project_event_causality_evidence(records) -> dict[str, Any]:
    events: dict[str, dict[str, Any]] = {}
    relations: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_CAUSAL_RECORD_TYPE)
        if record_type not in {_CAUSAL_EVENT_RECORD, _CAUSAL_RELATION_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _CAUSAL_EVENT_RECORD:
                item = CausalEventIdentity.from_dict(document)
                object_id = item.event_id
                fingerprint = item.fingerprint
                candidate = {"event": item.to_dict(), "evidence_id": evidence_id}
                prior = events.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"causal event identity collision: {object_id}")
                events[object_id] = candidate
            else:
                item = CausalRelation.from_dict(document)
                object_id = item.relation_id
                fingerprint = item.fingerprint
                candidate = {"relation": item.to_dict(), "evidence_id": evidence_id}
                prior = relations.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"causal relation identity collision: {object_id}")
                relations[object_id] = candidate
            if metadata.get("object_id") != object_id:
                raise ValueError(f"causal metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"causal metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for relation_id, row in relations.items():
        relation = CausalRelation.from_dict(row["relation"])
        subject = events.get(relation.subject_event_id)
        reference = events.get(relation.reference_event_id)
        if subject is None or reference is None:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _CAUSAL_RELATION_RECORD,
                    "error": f"ValueError: causal relation references missing event: {relation_id}",
                }
            )
            continue
        if subject["event"]["fingerprint"] != relation.subject_event_fingerprint:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _CAUSAL_RELATION_RECORD,
                    "error": f"ValueError: causal subject fingerprint mismatch: {relation_id}",
                }
            )
        if reference["event"]["fingerprint"] != relation.reference_event_fingerprint:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _CAUSAL_RELATION_RECORD,
                    "error": f"ValueError: causal reference fingerprint mismatch: {relation_id}",
                }
            )

    return {
        "runtime_contract": event_causality_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "events": events,
        "relations": relations,
    }


class EventCausalityRuntimeMixin:
    def event_causality_contract_report(self) -> dict[str, Any]:
        return event_causality_runtime_contract()

    def _event_causality_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_event_causality_evidence(records)

    def _require_valid_event_causality_projection(self) -> dict[str, Any]:
        report = self._event_causality_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable event-causality projection: {report['issues']}")
        return report

    def _authorize_event_causality_action(
        self,
        *,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        capability: str,
        at_time: float,
        metadata: Mapping[str, Any],
        derived_from: Sequence[str],
    ) -> dict[str, Any]:
        if not actor_principal_id:
            raise PermissionError("event-causality mutation requires actor_principal_id")
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                capability,
                at_time=float(at_time),
                machine_id=self.snapshot.machine_id,
                metadata=deepcopy(dict(metadata)),
            ),
            derived_from=tuple(derived_from),
            reason=f"event-causality scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"event-causality denied {capability}: {result['decision']['reason']}")
        return result

    def _record_event_causality_document(
        self,
        *,
        record_type: str,
        object_id: str,
        object_fingerprint: str,
        document: Mapping[str, Any],
        derived_from: Sequence[str],
        actor_principal_id: str,
        at_time: float,
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"event-causality-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_CAUSAL_RECORD_TYPE) != record_type
                or metadata.get(_CAUSAL_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"event-causality Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="event_causality",
            statement=canonical_semantic_json(payload),
            source=EVENT_CAUSALITY_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _CAUSAL_RECORD_TYPE: record_type,
                _CAUSAL_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "recorded_by_principal_id": actor_principal_id,
                "recorded_at_context_time": float(at_time),
                "host_context_time_grants_order": False,
                "fact_authority_creation": "NONE",
                "effect_authority": "NONE",
                "machine_state_mutation": "NONE",
                "parallel_event_ledger": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def record_causal_event(
        self,
        event: CausalEventIdentity | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "causal event identity recorded",
    ) -> dict[str, Any]:
        item = event if isinstance(event, CausalEventIdentity) else CausalEventIdentity.from_dict(event)
        lineage = self._require_evidence_ids(tuple(map(str, evidence_ids)))
        projection = self._require_valid_event_causality_projection()
        prior = projection["events"].get(item.event_id)
        if prior is not None:
            if prior["event"]["fingerprint"] != item.fingerprint:
                raise ValueError(
                    "causal event local identity collision: node_id/boot_epoch/sequence already names a different event"
                )
            return {
                **deepcopy(prior),
                "already_recorded": True,
                "fact_authority_created": False,
                "effect_authority_granted": False,
                "machine_state_mutated": False,
            }
        authorization = self._authorize_event_causality_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=EVENT_CAUSALITY_CAPABILITIES["record"],
            at_time=at_time,
            metadata={
                "event_id": item.event_id,
                "node_id": item.node_id,
                "boot_epoch": item.boot_epoch,
                "sequence": item.sequence,
                "object_kind": item.object_kind,
                "object_id": item.object_id,
            },
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_event_causality_document(
            record_type=_CAUSAL_EVENT_RECORD,
            object_id=item.event_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            derived_from=full_lineage,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            reason=reason,
        )
        return {
            "event": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "machine_state_mutated": False,
        }

    def record_machine_observation_causal_event(
        self,
        observation_id: str,
        event: CausalEventIdentity | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "machine observation causal identity recorded",
    ) -> dict[str, Any]:
        item = event if isinstance(event, CausalEventIdentity) else CausalEventIdentity.from_dict(event)
        observation_row = self.machine_state_observation_report(str(observation_id))
        observation = MachineStateObservation.from_dict(observation_row["observation"])
        binding_row = self.machine_binding_report(observation.binding_id)
        binding = MachineBinding.from_dict(binding_row["binding"])
        state_row = self.state_claim_report(observation.state_claim_id)
        claim = StateClaim.from_dict(state_row["claim"])
        if item.event_kind != "OBSERVATION_EMITTED":
            raise ValueError("machine observation causal event requires event_kind OBSERVATION_EMITTED")
        if item.object_kind != "MACHINE_STATE_OBSERVATION" or item.object_id != observation.observation_id:
            raise ValueError("causal event does not bind the exact durable machine state observation")
        if item.workspace_id != claim.workspace_id or item.scope_id != claim.scope_id:
            raise ValueError("causal event workspace/scope does not match machine observation claim")
        if item.subject_id != claim.subject_id or item.subject_id != binding.subject_id:
            raise ValueError("causal event subject does not match machine observation subject")
        if item.problem_revision_id != claim.problem_revision_id:
            raise ValueError("causal event problem revision does not match machine observation claim")
        if item.external_revision_id != observation.external_revision_id or item.external_revision_id != claim.external_revision_id:
            raise ValueError("causal event external revision does not match machine observation")
        lineage = tuple(
            sorted(
                set(
                    (
                        *map(str, evidence_ids),
                        str(observation_row["evidence_id"]),
                        str(binding_row["evidence_id"]),
                        str(state_row["evidence_id"]),
                    )
                )
            )
        )
        return self.record_causal_event(
            item,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            evidence_ids=lineage,
            reason=reason,
        )

    def _validate_relation_local_order(
        self,
        relation: CausalRelation,
        subject: CausalEventIdentity,
        reference: CausalEventIdentity,
    ) -> None:
        same_local_stream = subject.node_id == reference.node_id and subject.boot_epoch == reference.boot_epoch
        if not same_local_stream:
            return
        if subject.sequence == reference.sequence:
            raise ValueError("distinct causal events in one node/boot epoch cannot share a local sequence")
        if relation.relation == "HAPPENS_BEFORE" and not subject.sequence < reference.sequence:
            raise ValueError("HAPPENS_BEFORE contradicts same-node/boot local sequence")
        if relation.relation == "CAUSED_BY" and not reference.sequence < subject.sequence:
            raise ValueError("CAUSED_BY contradicts same-node/boot local sequence")
        if relation.relation in {"CONCURRENT_WITH", "ORDER_UNKNOWN"}:
            raise ValueError(f"{relation.relation} contradicts known same-node/boot local sequence order")

    def record_causal_relation(
        self,
        relation: CausalRelation | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "causal relation recorded",
    ) -> dict[str, Any]:
        item = relation if isinstance(relation, CausalRelation) else CausalRelation.from_dict(relation)
        projection = self._require_valid_event_causality_projection()
        try:
            subject_row = projection["events"][item.subject_event_id]
            reference_row = projection["events"][item.reference_event_id]
        except KeyError as exc:
            raise KeyError(f"causal relation references unknown event: {exc.args[0]}") from None
        subject = CausalEventIdentity.from_dict(subject_row["event"])
        reference = CausalEventIdentity.from_dict(reference_row["event"])
        if subject.fingerprint != item.subject_event_fingerprint:
            raise ValueError("causal relation subject fingerprint does not match durable event")
        if reference.fingerprint != item.reference_event_fingerprint:
            raise ValueError("causal relation reference fingerprint does not match durable event")
        if subject.workspace_id != reference.workspace_id or subject.scope_id != reference.scope_id:
            raise ValueError("v1 causal relation requires events in the same workspace/scope")
        self._validate_relation_local_order(item, subject, reference)
        prior = projection["relations"].get(item.relation_id)
        if prior is not None:
            if prior["relation"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"causal relation identity collision: {item.relation_id}")
            return {
                **deepcopy(prior),
                "already_recorded": True,
                "fact_authority_created": False,
                "effect_authority_granted": False,
            }
        lineage = self._require_evidence_ids(
            tuple(
                sorted(
                    set(
                        (
                            *map(str, evidence_ids),
                            str(subject_row["evidence_id"]),
                            str(reference_row["evidence_id"]),
                        )
                    )
                )
            )
        )
        authorization = self._authorize_event_causality_action(
            actor_principal_id=actor_principal_id,
            workspace_id=subject.workspace_id,
            scope_id=subject.scope_id,
            capability=EVENT_CAUSALITY_CAPABILITIES["relate"],
            at_time=at_time,
            metadata={
                "relation_id": item.relation_id,
                "relation": item.relation,
                "subject_event_id": item.subject_event_id,
                "reference_event_id": item.reference_event_id,
            },
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_event_causality_document(
            record_type=_CAUSAL_RELATION_RECORD,
            object_id=item.relation_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            derived_from=full_lineage,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            reason=reason,
        )
        return {
            "relation": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
        }

    def causal_event_report(self, event_id: str) -> dict[str, Any]:
        projection = self._require_valid_event_causality_projection()
        try:
            return deepcopy(projection["events"][str(event_id)])
        except KeyError:
            raise KeyError(f"unknown causal event: {event_id}") from None

    def causal_relation_report(self, relation_id: str) -> dict[str, Any]:
        projection = self._require_valid_event_causality_projection()
        try:
            return deepcopy(projection["relations"][str(relation_id)])
        except KeyError:
            raise KeyError(f"unknown causal relation: {relation_id}") from None

    def event_causality_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_event_causality_projection()
        events: dict[str, dict[str, Any]] = {}
        for event_id, row in sorted(projection["events"].items()):
            document = row["event"]
            if workspace_id is not None and document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            events[event_id] = deepcopy(row)
        relations = {
            relation_id: deepcopy(row)
            for relation_id, row in sorted(projection["relations"].items())
            if row["relation"]["subject_event_id"] in events and row["relation"]["reference_event_id"] in events
        }
        return {
            "runtime_contract": deepcopy(projection["runtime_contract"]),
            "valid": True,
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "events": events,
            "relations": relations,
            "core_aasm_event_log": "UNCHANGED",
            "fact_authority_creation": "NONE",
            "effect_authority": "NONE",
            "machine_state_mutation": "NONE",
        }


__all__ = [
    "EVENT_CAUSALITY_RUNTIME_CONTRACT_ID",
    "EVENT_CAUSALITY_RUNTIME_CONTRACT_VERSION",
    "EVENT_CAUSALITY_RUNTIME_STABILITY",
    "EVENT_CAUSALITY_CAPABILITIES",
    "EventCausalityRuntimeMixin",
    "project_event_causality_evidence",
    "event_causality_runtime_contract",
]
