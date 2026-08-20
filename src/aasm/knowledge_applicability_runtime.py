from __future__ import annotations

"""Durable S5.4 knowledge applicability/application runtime.

The runtime persists knowledge-stage records as canonical AASM Evidence and
binds application authority to canonical AASM PROPOSAL/AUTHORIZED events. It
creates no knowledge authority, applicability authority, shadow authority
store, verification mutation path, effect dispatcher, or resource plane.
"""

from copy import deepcopy
from dataclasses import asdict
import json
from typing import Any, Iterable, Mapping, Sequence

from .evidence import EvidenceRecord
from .model import AuthorizedAction, EventType, Proposal, now
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .knowledge_applicability import (
    KNOWLEDGE_APPLICABILITY_CONTRACT_ID,
    KNOWLEDGE_APPLICATION_CONTRACT_ID,
    KNOWLEDGE_VERIFICATION_EFFECTS,
    ApplicabilityCheck,
    KnowledgeApplication,
    KnowledgeItem,
    KnowledgeSelection,
)

KNOWLEDGE_APPLICABILITY_RUNTIME_CONTRACT_ID = "aasm.knowledge.applicability.runtime.v1"
KNOWLEDGE_APPLICABILITY_RUNTIME_CONTRACT_VERSION = "0.1.0"
KNOWLEDGE_APPLICABILITY_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

KNOWLEDGE_RECORD_TYPE = "aasm_knowledge_record_type"
KNOWLEDGE_DOCUMENT = "document"
KNOWLEDGE_ITEM_RECORD = "KNOWLEDGE_ITEM"
KNOWLEDGE_SELECTION_RECORD = "KNOWLEDGE_SELECTION"
KNOWLEDGE_APPLICABILITY_RECORD = "APPLICABILITY_CHECK"
KNOWLEDGE_APPLICATION_RECORD = "KNOWLEDGE_APPLICATION"
KNOWLEDGE_RECORD_TYPES = (
    KNOWLEDGE_ITEM_RECORD,
    KNOWLEDGE_SELECTION_RECORD,
    KNOWLEDGE_APPLICABILITY_RECORD,
    KNOWLEDGE_APPLICATION_RECORD,
)
KNOWLEDGE_APPLICATION_ACTION = "apply_knowledge"
KNOWLEDGE_AUTHORIZATION_PURPOSE = "KNOWLEDGE_APPLICATION"


def knowledge_applicability_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": KNOWLEDGE_APPLICABILITY_RUNTIME_CONTRACT_ID,
        "contract_version": KNOWLEDGE_APPLICABILITY_RUNTIME_CONTRACT_VERSION,
        "stability": KNOWLEDGE_APPLICABILITY_RUNTIME_STABILITY,
        "semantic_contract": KNOWLEDGE_APPLICABILITY_CONTRACT_ID,
        "application_contract": KNOWLEDGE_APPLICATION_CONTRACT_ID,
        "durability": "EXISTING_AASM_EVIDENCE_AND_EVENT_REPLAY",
        "records": list(KNOWLEDGE_RECORD_TYPES),
        "stage_order": "ITEM_THEN_SELECTION_THEN_APPLICABILITY_THEN_AUTHORIZED_APPLICATION",
        "selection_authority": "NONE",
        "applicability_authority": "NONE",
        "application_authority": "EXISTING_AASM_AUTHORITY_POLICY_AUTHORIZED_ACTION_ONLY",
        "authorization_audit": "EXISTING_AASM_AUTHORIZED_EVENT_REQUIRED",
        "source_authority_transfer": "NEVER",
        "target_binding": "EXACT_SCOPE_AND_SEMANTIC_FINGERPRINT",
        "failed_applicability": "BLOCK_APPLICATION",
        "inconclusive_applicability": "BLOCK_APPLICATION",
        "freshness": "RECHECKED_AT_AUTHORIZATION_AND_APPLICATION",
        "verification_effect_default": "NONE",
        "verification_relief": "EXPLICIT_AUTHORIZED_PROPOSAL_BINDING_REQUIRED",
        "verification_mutation": "NONE",
        "effect_dispatch": "NONE",
        "resource_reservation": "NONE",
        "problem_mutation": "NONE",
        "parallel_knowledge_store": "NONE",
        "parallel_applicability_store": "NONE",
        "parallel_authority_plane": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def knowledge_document(value: Mapping[str, Any]) -> str:
    return canonical_semantic_json(deepcopy(dict(value)))


def _record_document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    document = metadata.get(KNOWLEDGE_DOCUMENT)
    if isinstance(document, Mapping):
        return deepcopy(dict(document))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        value = json.loads(statement)
        if isinstance(value, Mapping):
            return deepcopy(dict(value))
    raise ValueError("knowledge Evidence is missing its canonical document")


def _evidence_map(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in records:
        row = deepcopy(dict(raw))
        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            out[evidence_id] = row
    return out


def _active_evidence(evidence: Mapping[str, Mapping[str, Any]], evidence_ids: Sequence[str]) -> tuple[bool, list[str]]:
    stale = sorted(
        str(eid)
        for eid in evidence_ids
        if str(eid) not in evidence or str(evidence[str(eid)].get("status", "active")) != "active"
    )
    return not stale, stale


def _event_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    if hasattr(value, "__dataclass_fields__"):
        return asdict(value)
    raise TypeError(f"knowledge runtime cannot project event type {type(value)!r}")


def _authorization_events(events: Iterable[Any]) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    out: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        row = _event_mapping(event)
        if str(row.get("event_type") or "") != EventType.AUTHORIZED.value:
            continue
        data = dict(row.get("data") or {})
        if data.get("purpose") != KNOWLEDGE_AUTHORIZATION_PURPOSE:
            continue
        authorization_id = str(data.get("authorization_id") or "")
        if not authorization_id:
            issues.append({"index": index, "record_type": "AUTHORIZED", "error": "KNOWLEDGE_AUTHORIZATION_ID_MISSING"})
            continue
        prior = out.get(authorization_id)
        if prior is not None and prior != row:
            issues.append({"index": index, "record_type": "AUTHORIZED", "error": f"KNOWLEDGE_AUTHORIZATION_ID_COLLISION: {authorization_id}"})
            continue
        out[authorization_id] = row
    return out, issues


def knowledge_application_payload(
    item: KnowledgeItem,
    selection: KnowledgeSelection,
    check: ApplicabilityCheck,
    *,
    application_kind: str,
    verification_effect: str = "NONE",
) -> dict[str, Any]:
    kind = str(application_kind).strip().upper()
    if not kind:
        raise ValueError("knowledge application_kind is required")
    effect = str(verification_effect).strip().upper()
    if effect not in KNOWLEDGE_VERIFICATION_EFFECTS:
        raise ValueError(f"unsupported knowledge verification effect: {effect}")
    if item.knowledge_id != check.knowledge_id or item.fingerprint != check.knowledge_fingerprint:
        raise ValueError("knowledge application payload item/applicability binding mismatch")
    if selection.selection_id != check.selection_id or selection.fingerprint != check.selection_fingerprint:
        raise ValueError("knowledge application payload selection/applicability binding mismatch")
    if selection.target_scope_id != check.target_scope_id or selection.target_semantic_fingerprint != check.target_semantic_fingerprint:
        raise ValueError("knowledge application payload target binding mismatch")
    return {
        "contract_id": KNOWLEDGE_APPLICATION_CONTRACT_ID,
        "knowledge_id": item.knowledge_id,
        "knowledge_fingerprint": item.fingerprint,
        "selection_id": selection.selection_id,
        "selection_fingerprint": selection.fingerprint,
        "applicability_id": check.applicability_id,
        "applicability_fingerprint": check.fingerprint,
        "target_scope_id": selection.target_scope_id,
        "target_semantic_fingerprint": selection.target_semantic_fingerprint,
        "application_kind": kind,
        "verification_effect": effect,
        "source_authority_transfer": "NEVER",
    }


def knowledge_proposal_fingerprint(proposal: Proposal | Mapping[str, Any]) -> str:
    payload = asdict(proposal) if isinstance(proposal, Proposal) else deepcopy(dict(proposal))
    return semantic_fingerprint(payload)


def project_knowledge_applicability_history(
    records: Iterable[Mapping[str, Any]],
    events: Iterable[Any] = (),
) -> dict[str, Any]:
    rows = [deepcopy(dict(row)) for row in records]
    evidence = _evidence_map(rows)
    authorization_events, issues = _authorization_events(events)
    items: dict[str, dict[str, Any]] = {}
    selections: dict[str, dict[str, Any]] = {}
    checks: dict[str, dict[str, Any]] = {}
    applications: dict[str, dict[str, Any]] = {}
    active_check_by_selection: dict[str, str] = {}
    application_by_authorization: dict[str, str] = {}

    for index, row in enumerate(rows):
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(KNOWLEDGE_RECORD_TYPE)
        if record_type not in KNOWLEDGE_RECORD_TYPES:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        active = str(row.get("status", "active")) == "active"
        try:
            document = _record_document(row)
            if record_type == KNOWLEDGE_ITEM_RECORD:
                item = KnowledgeItem.from_dict(document["knowledge_item"])
                missing = sorted(set(item.source_evidence_ids) - set(evidence))
                if missing:
                    raise ValueError(f"KNOWLEDGE_ITEM_SOURCE_EVIDENCE_MISSING: {missing}")
                prior = items.get(item.knowledge_id)
                if prior is not None and prior["knowledge_item"]["fingerprint"] != item.fingerprint:
                    raise ValueError(f"KNOWLEDGE_ITEM_IDENTITY_COLLISION: {item.knowledge_id}")
                items[item.knowledge_id] = {"knowledge_item": item.to_dict(), "evidence_id": evidence_id, "active": active}

            elif record_type == KNOWLEDGE_SELECTION_RECORD:
                selection = KnowledgeSelection.from_dict(document["selection"])
                item_row = items.get(selection.knowledge_id)
                if item_row is None:
                    raise ValueError(f"KNOWLEDGE_SELECTION_UNKNOWN_ITEM: {selection.knowledge_id}")
                item = KnowledgeItem.from_dict(item_row["knowledge_item"])
                if selection.knowledge_fingerprint != item.fingerprint:
                    raise ValueError("KNOWLEDGE_SELECTION_ITEM_FINGERPRINT_MISMATCH")
                if selection.target_scope_id not in item.applicability_scope_ids:
                    raise ValueError("KNOWLEDGE_SELECTION_SCOPE_NOT_APPLICABLE")
                missing = sorted(set(selection.selection_evidence_ids) - set(evidence))
                if missing:
                    raise ValueError(f"KNOWLEDGE_SELECTION_EVIDENCE_MISSING: {missing}")
                prior = selections.get(selection.selection_id)
                if prior is not None and prior["selection"]["fingerprint"] != selection.fingerprint:
                    raise ValueError(f"KNOWLEDGE_SELECTION_IDENTITY_COLLISION: {selection.selection_id}")
                selections[selection.selection_id] = {"selection": selection.to_dict(), "evidence_id": evidence_id, "active": active}

            elif record_type == KNOWLEDGE_APPLICABILITY_RECORD:
                check = ApplicabilityCheck.from_dict(document["applicability"])
                item_row = items.get(check.knowledge_id)
                selection_row = selections.get(check.selection_id)
                if item_row is None or selection_row is None:
                    raise ValueError("KNOWLEDGE_APPLICABILITY_UNKNOWN_PARENT")
                item = KnowledgeItem.from_dict(item_row["knowledge_item"])
                selection = KnowledgeSelection.from_dict(selection_row["selection"])
                if check.knowledge_fingerprint != item.fingerprint or check.selection_fingerprint != selection.fingerprint:
                    raise ValueError("KNOWLEDGE_APPLICABILITY_PARENT_FINGERPRINT_MISMATCH")
                if check.target_scope_id != selection.target_scope_id or check.target_semantic_fingerprint != selection.target_semantic_fingerprint:
                    raise ValueError("KNOWLEDGE_APPLICABILITY_TARGET_MISMATCH")
                if {result.predicate for result in check.predicate_results} != set(item.applicability_predicates):
                    raise ValueError("KNOWLEDGE_APPLICABILITY_PREDICATE_SET_MISMATCH")
                if not set(item.invalidation_triggers).issubset(set(check.invalidation_triggers)):
                    raise ValueError("KNOWLEDGE_APPLICABILITY_INVALIDATION_WEAKENED")
                missing = sorted(set(check.evidence_ids) - set(evidence))
                if missing:
                    raise ValueError(f"KNOWLEDGE_APPLICABILITY_EVIDENCE_MISSING: {missing}")
                prior = checks.get(check.applicability_id)
                if prior is not None and prior["applicability"]["fingerprint"] != check.fingerprint:
                    raise ValueError(f"KNOWLEDGE_APPLICABILITY_IDENTITY_COLLISION: {check.applicability_id}")
                if active:
                    active_prior = active_check_by_selection.get(check.selection_id)
                    if active_prior is not None and active_prior != check.applicability_id:
                        prior_row = checks.get(active_prior)
                        if prior_row is not None and prior_row["active"]:
                            raise ValueError("KNOWLEDGE_APPLICABILITY_ACTIVE_SELECTION_CONFLICT")
                    active_check_by_selection[check.selection_id] = check.applicability_id
                checks[check.applicability_id] = {"applicability": check.to_dict(), "evidence_id": evidence_id, "active": active}
                if not active and active_check_by_selection.get(check.selection_id) == check.applicability_id:
                    active_check_by_selection.pop(check.selection_id, None)

            else:
                application = KnowledgeApplication.from_dict(document["application"])
                item_row = items.get(application.knowledge_id)
                selection_row = selections.get(application.selection_id)
                check_row = checks.get(application.applicability_id)
                if item_row is None or selection_row is None or check_row is None:
                    raise ValueError("KNOWLEDGE_APPLICATION_UNKNOWN_PARENT")
                item = KnowledgeItem.from_dict(item_row["knowledge_item"])
                selection = KnowledgeSelection.from_dict(selection_row["selection"])
                check = ApplicabilityCheck.from_dict(check_row["applicability"])
                if application.knowledge_fingerprint != item.fingerprint or application.selection_fingerprint != selection.fingerprint or application.applicability_fingerprint != check.fingerprint:
                    raise ValueError("KNOWLEDGE_APPLICATION_PARENT_FINGERPRINT_MISMATCH")
                if check.status != "APPLICABLE":
                    raise ValueError(f"KNOWLEDGE_APPLICATION_NON_APPLICABLE_CHECK: {check.status}")
                if application.target_scope_id != selection.target_scope_id or application.target_semantic_fingerprint != selection.target_semantic_fingerprint:
                    raise ValueError("KNOWLEDGE_APPLICATION_TARGET_MISMATCH")
                missing = sorted(set(application.application_evidence_ids) - set(evidence))
                if missing:
                    raise ValueError(f"KNOWLEDGE_APPLICATION_EVIDENCE_MISSING: {missing}")
                auth_event = authorization_events.get(application.authorization_id)
                if auth_event is None:
                    raise ValueError(f"KNOWLEDGE_APPLICATION_AUTHORIZED_EVENT_MISSING: {application.authorization_id}")
                auth_data = dict(auth_event.get("data") or {})
                if str(auth_event.get("event_id") or "") != application.authorization_event_id:
                    raise ValueError("KNOWLEDGE_APPLICATION_AUTHORIZED_EVENT_ID_MISMATCH")
                if str(auth_data.get("authority") or "") != application.authority:
                    raise ValueError("KNOWLEDGE_APPLICATION_AUTHORITY_MISMATCH")
                proposal = dict(auth_data.get("proposal") or {})
                proposal_fp = knowledge_proposal_fingerprint(proposal)
                if proposal_fp != application.authorized_proposal_fingerprint or str(auth_data.get("proposal_fingerprint") or "") != proposal_fp:
                    raise ValueError("KNOWLEDGE_APPLICATION_PROPOSAL_FINGERPRINT_MISMATCH")
                if str(proposal.get("action") or "") != KNOWLEDGE_APPLICATION_ACTION:
                    raise ValueError("KNOWLEDGE_APPLICATION_WRONG_AUTHORIZED_ACTION")
                expected = knowledge_application_payload(item, selection, check, application_kind=application.application_kind, verification_effect=application.verification_effect)
                if dict(proposal.get("payload") or {}) != expected:
                    raise ValueError("KNOWLEDGE_APPLICATION_AUTHORIZED_PAYLOAD_MISMATCH")
                prior_auth = application_by_authorization.get(application.authorization_id)
                if prior_auth is not None and prior_auth != application.application_id:
                    raise ValueError("KNOWLEDGE_APPLICATION_AUTHORIZATION_REUSED")
                prior = applications.get(application.application_id)
                if prior is not None and prior["application"]["fingerprint"] != application.fingerprint:
                    raise ValueError(f"KNOWLEDGE_APPLICATION_IDENTITY_COLLISION: {application.application_id}")
                application_by_authorization[application.authorization_id] = application.application_id
                applications[application.application_id] = {"application": application.to_dict(), "evidence_id": evidence_id, "active": active}

        except Exception as exc:
            issues.append({"index": index, "evidence_id": evidence_id, "record_type": record_type, "error": str(exc)})

    return {
        "contract_id": KNOWLEDGE_APPLICABILITY_RUNTIME_CONTRACT_ID,
        "valid": not issues,
        "issues": issues,
        "knowledge_items": items,
        "selections": selections,
        "applicability_checks": checks,
        "applications": applications,
        "active_check_by_selection": active_check_by_selection,
        "authorization_events": authorization_events,
        "application_by_authorization": application_by_authorization,
        "authority_plane": "EXISTING_AASM_ONLY",
        "source_authority_transfer": "NEVER",
    }


class KnowledgeApplicabilityRuntimeMixin:
    def knowledge_applicability_runtime_contract_report(self) -> dict[str, Any]:
        return knowledge_applicability_runtime_contract()

    def _knowledge_records(self) -> list[dict[str, Any]]:
        evidence = self.snapshot.evidence or {}
        return [deepcopy(dict(row)) for row in evidence.get("records", [])]

    def _knowledge_projection(self) -> dict[str, Any]:
        return project_knowledge_applicability_history(self._knowledge_records(), self.events)

    def _require_valid_knowledge_projection(self) -> dict[str, Any]:
        projection = self._knowledge_projection()
        if not projection["valid"]:
            raise ValueError(f"invalid durable knowledge applicability history: {projection['issues']}")
        return projection

    def _knowledge_require_active_evidence(self, evidence_ids: Sequence[str]) -> tuple[str, ...]:
        ids = tuple(sorted(set(map(str, evidence_ids))))
        evidence = _evidence_map(self._knowledge_records())
        missing = [eid for eid in ids if eid not in evidence]
        if missing:
            raise KeyError(f"unknown knowledge support Evidence: {missing}")
        stale = [eid for eid in ids if str(evidence[eid].get("status", "active")) != "active"]
        if stale:
            raise ValueError(f"inactive knowledge support Evidence: {stale}")
        return ids

    def _record_knowledge_document(self, *, record_type: str, object_id: str, document: Mapping[str, Any], source: str, derived_from: Sequence[str], reason: str) -> str:
        if record_type not in KNOWLEDGE_RECORD_TYPES:
            raise ValueError(f"unsupported knowledge Evidence record type: {record_type}")
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": str(object_id), "document": payload}
        evidence_id = f"knowledge-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self._knowledge_records():
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = dict(row.get("metadata") or {})
            if metadata.get(KNOWLEDGE_RECORD_TYPE) != record_type or metadata.get(KNOWLEDGE_DOCUMENT) != payload:
                raise ValueError(f"knowledge Evidence collision: {evidence_id}")
            return evidence_id
        lineage = self._knowledge_require_active_evidence(tuple(derived_from))
        record = EvidenceRecord(
            kind="knowledge_governance",
            statement=knowledge_document(payload),
            source=source,
            derived_from=list(lineage),
            metadata={
                KNOWLEDGE_RECORD_TYPE: record_type,
                "object_id": str(object_id),
                KNOWLEDGE_DOCUMENT: payload,
                "authority": "EXISTING_AASM_AUTHORIZED_ACTION_BOUND" if record_type == KNOWLEDGE_APPLICATION_RECORD else "NO_AUTHORITY_CONFERRED",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def record_knowledge_item(self, item: KnowledgeItem | Mapping[str, Any], *, reason: str = "knowledge item recorded") -> dict[str, Any]:
        value = item if isinstance(item, KnowledgeItem) else KnowledgeItem.from_dict(item)
        self._knowledge_require_active_evidence(value.source_evidence_ids)
        projection = self._require_valid_knowledge_projection()
        existing = projection["knowledge_items"].get(value.knowledge_id)
        if existing is not None:
            if existing["knowledge_item"]["fingerprint"] != value.fingerprint:
                raise ValueError(f"knowledge item identity collision: {value.knowledge_id}")
            return {"knowledge_item": deepcopy(existing["knowledge_item"]), "evidence_id": existing["evidence_id"], "already_recorded": True}
        evidence_id = self._record_knowledge_document(record_type=KNOWLEDGE_ITEM_RECORD, object_id=value.knowledge_id, document={"knowledge_item": value.to_dict()}, source=KNOWLEDGE_APPLICABILITY_CONTRACT_ID, derived_from=value.source_evidence_ids, reason=reason)
        return {"knowledge_item": value.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def record_knowledge_selection(self, selection: KnowledgeSelection | Mapping[str, Any], *, reason: str = "knowledge selection recorded") -> dict[str, Any]:
        value = selection if isinstance(selection, KnowledgeSelection) else KnowledgeSelection.from_dict(selection)
        projection = self._require_valid_knowledge_projection()
        item_row = projection["knowledge_items"].get(value.knowledge_id)
        if item_row is None or not item_row["active"]:
            raise KeyError(f"unknown or inactive KnowledgeItem: {value.knowledge_id}")
        item = KnowledgeItem.from_dict(item_row["knowledge_item"])
        if item.fingerprint != value.knowledge_fingerprint:
            raise ValueError("knowledge selection does not bind exact KnowledgeItem fingerprint")
        if value.target_scope_id not in item.applicability_scope_ids:
            raise PermissionError("KNOWLEDGE_SELECTION_SCOPE_NOT_APPLICABLE")
        self._knowledge_require_active_evidence((*item.source_evidence_ids, *value.selection_evidence_ids))
        existing = projection["selections"].get(value.selection_id)
        if existing is not None:
            if existing["selection"]["fingerprint"] != value.fingerprint:
                raise ValueError(f"knowledge selection identity collision: {value.selection_id}")
            return {"selection": deepcopy(existing["selection"]), "evidence_id": existing["evidence_id"], "already_recorded": True}
        evidence_id = self._record_knowledge_document(record_type=KNOWLEDGE_SELECTION_RECORD, object_id=value.selection_id, document={"selection": value.to_dict()}, source=KNOWLEDGE_APPLICABILITY_CONTRACT_ID, derived_from=(item_row["evidence_id"], *value.selection_evidence_ids), reason=reason)
        return {"selection": value.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def record_applicability_check(self, check: ApplicabilityCheck | Mapping[str, Any], *, reason: str = "knowledge applicability check recorded") -> dict[str, Any]:
        value = check if isinstance(check, ApplicabilityCheck) else ApplicabilityCheck.from_dict(check)
        projection = self._require_valid_knowledge_projection()
        item_row = projection["knowledge_items"].get(value.knowledge_id)
        selection_row = projection["selections"].get(value.selection_id)
        if item_row is None or selection_row is None or not item_row["active"] or not selection_row["active"]:
            raise KeyError("knowledge applicability requires active item and selection")
        item = KnowledgeItem.from_dict(item_row["knowledge_item"])
        selection = KnowledgeSelection.from_dict(selection_row["selection"])
        if item.fingerprint != value.knowledge_fingerprint or selection.fingerprint != value.selection_fingerprint:
            raise ValueError("knowledge applicability does not bind exact item/selection fingerprints")
        if value.target_scope_id != selection.target_scope_id or value.target_semantic_fingerprint != selection.target_semantic_fingerprint:
            raise ValueError("knowledge applicability does not bind exact selection target")
        if {row.predicate for row in value.predicate_results} != set(item.applicability_predicates):
            raise ValueError("knowledge applicability must assess every declared item predicate exactly once")
        if not set(item.invalidation_triggers).issubset(set(value.invalidation_triggers)):
            raise ValueError("knowledge applicability cannot weaken KnowledgeItem invalidation triggers")
        self._knowledge_require_active_evidence(value.evidence_ids)
        prior_id = projection["active_check_by_selection"].get(value.selection_id)
        if prior_id is not None and prior_id != value.applicability_id:
            raise ValueError("KNOWLEDGE_APPLICABILITY_ACTIVE_SELECTION_CONFLICT: invalidate prior applicability Evidence before reassessment")
        existing = projection["applicability_checks"].get(value.applicability_id)
        if existing is not None:
            if existing["applicability"]["fingerprint"] != value.fingerprint:
                raise ValueError(f"knowledge applicability identity collision: {value.applicability_id}")
            return {"applicability": deepcopy(existing["applicability"]), "evidence_id": existing["evidence_id"], "already_recorded": True}
        evidence_id = self._record_knowledge_document(record_type=KNOWLEDGE_APPLICABILITY_RECORD, object_id=value.applicability_id, document={"applicability": value.to_dict()}, source=KNOWLEDGE_APPLICABILITY_CONTRACT_ID, derived_from=(item_row["evidence_id"], selection_row["evidence_id"], *value.evidence_ids), reason=reason)
        return {"applicability": value.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def knowledge_applicability_current_report(self, applicability_id: str, *, current_target_fingerprint: str, as_of: float | None = None) -> dict[str, Any]:
        projection = self._require_valid_knowledge_projection()
        check_row = projection["applicability_checks"].get(str(applicability_id))
        if check_row is None:
            raise KeyError(f"unknown knowledge applicability check: {applicability_id}")
        check = ApplicabilityCheck.from_dict(check_row["applicability"])
        selection_row = projection["selections"].get(check.selection_id)
        item_row = projection["knowledge_items"].get(check.knowledge_id)
        if selection_row is None or item_row is None:
            raise RuntimeError("knowledge applicability lost its durable parents")
        selection = KnowledgeSelection.from_dict(selection_row["selection"])
        item = KnowledgeItem.from_dict(item_row["knowledge_item"])
        when = now() if as_of is None else float(as_of)
        evidence = _evidence_map(self._knowledge_records())
        source_ok, stale_source = _active_evidence(evidence, item.source_evidence_ids)
        selection_ok, stale_selection = _active_evidence(evidence, selection.selection_evidence_ids)
        assessment_ok, stale_assessment = _active_evidence(evidence, check.evidence_ids)
        reasons: list[str] = []
        if not item_row["active"]: reasons.append("KNOWLEDGE_ITEM_INACTIVE")
        if not selection_row["active"]: reasons.append("KNOWLEDGE_SELECTION_INACTIVE")
        if not check_row["active"]: reasons.append("APPLICABILITY_CHECK_INACTIVE")
        if check.status != "APPLICABLE": reasons.append(f"APPLICABILITY_{check.status}")
        if selection.target_scope_id not in item.applicability_scope_ids: reasons.append("TARGET_SCOPE_NO_LONGER_DECLARED_APPLICABLE")
        if str(current_target_fingerprint) != selection.target_semantic_fingerprint: reasons.append("TARGET_SEMANTIC_FINGERPRINT_DRIFT")
        if not item.is_fresh(when): reasons.append("KNOWLEDGE_ITEM_STALE")
        if not source_ok: reasons.append(f"KNOWLEDGE_SOURCE_EVIDENCE_STALE:{stale_source}")
        if not selection_ok: reasons.append(f"KNOWLEDGE_SELECTION_EVIDENCE_STALE:{stale_selection}")
        if not assessment_ok: reasons.append(f"KNOWLEDGE_APPLICABILITY_EVIDENCE_STALE:{stale_assessment}")
        return {
            "applicability_id": check.applicability_id, "status": check.status, "current": not reasons, "reasons": reasons,
            "knowledge_id": item.knowledge_id, "selection_id": selection.selection_id,
            "target_scope_id": selection.target_scope_id, "target_semantic_fingerprint": selection.target_semantic_fingerprint,
            "as_of": when, "invalidation_triggers": list(check.invalidation_triggers), "authority": "NONE",
        }

    def authorize_knowledge_application(self, applicability_id: str, *, current_target_fingerprint: str, application_kind: str, verification_effect: str = "NONE", agent_id: str = "aasm.knowledge.runtime", votes: Mapping[str, bool] | None = None, reason: str = "knowledge application authorized") -> AuthorizedAction:
        projection = self._require_valid_knowledge_projection()
        check_row = projection["applicability_checks"].get(str(applicability_id))
        if check_row is None or not check_row["active"]:
            raise KeyError(f"unknown or inactive applicability check: {applicability_id}")
        check = ApplicabilityCheck.from_dict(check_row["applicability"])
        current = self.knowledge_applicability_current_report(check.applicability_id, current_target_fingerprint=current_target_fingerprint)
        if not current["current"]:
            raise PermissionError(f"KNOWLEDGE_APPLICATION_APPLICABILITY_NOT_CURRENT: {current['reasons']}")
        item = KnowledgeItem.from_dict(projection["knowledge_items"][check.knowledge_id]["knowledge_item"])
        selection = KnowledgeSelection.from_dict(projection["selections"][check.selection_id]["selection"])
        payload = knowledge_application_payload(item, selection, check, application_kind=application_kind, verification_effect=verification_effect)
        proposal = Proposal(agent_id=str(agent_id), action=KNOWLEDGE_APPLICATION_ACTION, payload=payload, rationale=reason, reversible=payload["verification_effect"] == "NONE")
        self.emit(EventType.PROPOSAL.value, self.state_value, self.state_value, "knowledge application proposed", data={**asdict(proposal), "purpose": KNOWLEDGE_AUTHORIZATION_PURPOSE})
        auth = self.authority.authorize(proposal, votes=dict(votes or {}))
        proposal_fingerprint = knowledge_proposal_fingerprint(proposal)
        event = self.emit(EventType.AUTHORIZED.value, self.state_value, self.state_value, reason, data={
            "purpose": KNOWLEDGE_AUTHORIZATION_PURPOSE,
            "authorization_id": auth.authorization_id,
            "authority": auth.authority,
            "proposal": asdict(proposal),
            "proposal_fingerprint": proposal_fingerprint,
            "source_authority_transfer": "NEVER",
        })
        if not getattr(event, "event_id", ""):
            raise RuntimeError("knowledge authorization did not produce a durable AUTHORIZED event")
        return auth

    def record_knowledge_application(self, authorized: AuthorizedAction, *, current_target_fingerprint: str, application_evidence_ids: Sequence[str], applied_by: str, metadata: Mapping[str, Any] | None = None, reason: str = "authorized knowledge application recorded") -> dict[str, Any]:
        if not isinstance(authorized, AuthorizedAction):
            raise TypeError("knowledge application requires existing AASM AuthorizedAction")
        if authorized.proposal.action != KNOWLEDGE_APPLICATION_ACTION:
            raise PermissionError("KNOWLEDGE_APPLICATION_WRONG_AUTHORIZED_ACTION")
        projection = self._require_valid_knowledge_projection()
        auth_event = projection["authorization_events"].get(authorized.authorization_id)
        if auth_event is None:
            raise PermissionError("KNOWLEDGE_APPLICATION_AUTHORIZED_EVENT_MISSING")
        auth_data = dict(auth_event.get("data") or {})
        proposal_fingerprint = knowledge_proposal_fingerprint(authorized.proposal)
        if str(auth_data.get("authority") or "") != authorized.authority or str(auth_data.get("proposal_fingerprint") or "") != proposal_fingerprint or dict(auth_data.get("proposal") or {}) != asdict(authorized.proposal):
            raise PermissionError("KNOWLEDGE_APPLICATION_AUTHORIZATION_BINDING_MISMATCH")
        payload = dict(authorized.proposal.payload or {})
        applicability_id = str(payload.get("applicability_id") or "")
        check_row = projection["applicability_checks"].get(applicability_id)
        if check_row is None or not check_row["active"]:
            raise PermissionError("KNOWLEDGE_APPLICATION_APPLICABILITY_MISSING_OR_INACTIVE")
        check = ApplicabilityCheck.from_dict(check_row["applicability"])
        current = self.knowledge_applicability_current_report(check.applicability_id, current_target_fingerprint=current_target_fingerprint)
        if not current["current"]:
            raise PermissionError(f"KNOWLEDGE_APPLICATION_APPLICABILITY_NOT_CURRENT: {current['reasons']}")
        item_row = projection["knowledge_items"][check.knowledge_id]
        selection_row = projection["selections"][check.selection_id]
        item = KnowledgeItem.from_dict(item_row["knowledge_item"])
        selection = KnowledgeSelection.from_dict(selection_row["selection"])
        expected_payload = knowledge_application_payload(item, selection, check, application_kind=str(payload.get("application_kind") or ""), verification_effect=str(payload.get("verification_effect") or ""))
        if payload != expected_payload:
            raise PermissionError("KNOWLEDGE_APPLICATION_AUTHORIZED_PAYLOAD_MISMATCH")
        application_support = self._knowledge_require_active_evidence(tuple(application_evidence_ids))
        when = now()
        if not item.is_fresh(when):
            raise PermissionError("KNOWLEDGE_APPLICATION_ITEM_EXPIRED_AFTER_AUTHORIZATION")
        existing_application = projection["application_by_authorization"].get(authorized.authorization_id)
        if existing_application is not None:
            prior = projection["applications"][existing_application]
            return {"application": deepcopy(prior["application"]), "evidence_id": prior["evidence_id"], "already_recorded": True}
        application = KnowledgeApplication(
            item.knowledge_id, item.fingerprint, selection.selection_id, selection.fingerprint,
            check.applicability_id, check.fingerprint, selection.target_scope_id, selection.target_semantic_fingerprint,
            expected_payload["application_kind"], expected_payload["verification_effect"], application_support,
            authorized.authorization_id, authorized.authority, proposal_fingerprint, str(auth_event.get("event_id") or ""),
            str(applied_by), when, metadata or {},
        )
        evidence_id = self._record_knowledge_document(record_type=KNOWLEDGE_APPLICATION_RECORD, object_id=application.application_id, document={"application": application.to_dict()}, source=KNOWLEDGE_APPLICATION_CONTRACT_ID, derived_from=(item_row["evidence_id"], selection_row["evidence_id"], check_row["evidence_id"], *application.application_evidence_ids), reason=reason)
        return {"application": application.to_dict(), "evidence_id": evidence_id, "already_recorded": False}

    def knowledge_applicability_history_report(self) -> dict[str, Any]:
        return self._knowledge_projection()


__all__ = [
    "KNOWLEDGE_APPLICABILITY_RUNTIME_CONTRACT_ID", "KNOWLEDGE_APPLICABILITY_RUNTIME_CONTRACT_VERSION", "KNOWLEDGE_APPLICABILITY_RUNTIME_STABILITY",
    "KNOWLEDGE_RECORD_TYPE", "KNOWLEDGE_DOCUMENT", "KNOWLEDGE_ITEM_RECORD", "KNOWLEDGE_SELECTION_RECORD", "KNOWLEDGE_APPLICABILITY_RECORD", "KNOWLEDGE_APPLICATION_RECORD", "KNOWLEDGE_RECORD_TYPES",
    "KNOWLEDGE_APPLICATION_ACTION", "KNOWLEDGE_AUTHORIZATION_PURPOSE", "knowledge_applicability_runtime_contract", "knowledge_document", "knowledge_application_payload", "knowledge_proposal_fingerprint", "project_knowledge_applicability_history", "KnowledgeApplicabilityRuntimeMixin",
]
