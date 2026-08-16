from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import StateClaim
from .state_conflict import (
    STATE_CONFLICT_CONTRACT_ID,
    StateConflict,
    state_conflict_contract,
)


STATE_CONFLICT_RUNTIME_CONTRACT_ID = "aasm.state.conflict.runtime.v1"
STATE_CONFLICT_RUNTIME_CONTRACT_VERSION = "0.1.0"
STATE_CONFLICT_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
STATE_CONFLICT_CAPABILITIES = {"record": "state.conflict.record"}

_STATE_CONFLICT_RECORD_TYPE = "aasm_state_conflict_record_type"
_STATE_CONFLICT_DOCUMENT = "document"
_STATE_CONFLICT_RECORD = "STATE_CONFLICT"


def state_conflict_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": STATE_CONFLICT_RUNTIME_CONTRACT_ID,
        "contract_version": STATE_CONFLICT_RUNTIME_CONTRACT_VERSION,
        "stability": STATE_CONFLICT_RUNTIME_STABILITY,
        "semantic_contract": state_conflict_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "claim_source": "EXISTING_AASM_STATE_CLAIM_PROJECTION_ONLY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(STATE_CONFLICT_CAPABILITIES),
        "recording": "EXPLICIT_SCOPED_AUTHORITY_REQUIRED",
        "claim_mutation": "NONE",
        "machine_state_mutation": "NONE",
        "fact_authority_creation": "NONE",
        "effect_authority": "NONE",
        "observation_authority_elevation": "NONE",
        "resolution": "NONE_V1_IMMUTABLE_CONFLICT_EVIDENCE",
        "parallel_truth_table": "NONE",
        "parallel_dependency_graph": "NONE",
        "portable_identity": "SEMANTIC_OBJECT_EXCLUDES_RECORDER_AND_HOST_TIME",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_STATE_CONFLICT_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("state-conflict Evidence is missing canonical document")


def project_state_conflict_evidence(records) -> dict[str, Any]:
    conflicts: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        if metadata.get(_STATE_CONFLICT_RECORD_TYPE) != _STATE_CONFLICT_RECORD:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            item = StateConflict.from_dict(document)
            candidate = {"conflict": item.to_dict(), "evidence_id": evidence_id}
            prior = conflicts.get(item.conflict_id)
            if prior is not None and prior != candidate:
                raise ValueError(f"state conflict identity collision: {item.conflict_id}")
            if metadata.get("object_id") != item.conflict_id:
                raise ValueError(f"state-conflict metadata object_id mismatch: {item.conflict_id}")
            if metadata.get("object_fingerprint") != item.fingerprint:
                raise ValueError(f"state-conflict metadata fingerprint mismatch: {item.conflict_id}")
            conflicts[item.conflict_id] = candidate
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": _STATE_CONFLICT_RECORD,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "runtime_contract": state_conflict_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "conflicts": conflicts,
    }


class StateConflictRuntimeMixin:
    def state_conflict_contract_report(self) -> dict[str, Any]:
        return state_conflict_runtime_contract()

    def _state_conflict_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_state_conflict_evidence(records)

    def _require_valid_state_conflict_projection(self) -> dict[str, Any]:
        report = self._state_conflict_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable state-conflict projection: {report['issues']}")
        return report

    def _record_state_conflict_document(
        self,
        item: StateConflict,
        *,
        actor_principal_id: str,
        at_time: float,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = item.to_dict()
        identity = {
            "record_type": _STATE_CONFLICT_RECORD,
            "object_id": item.conflict_id,
            "document": payload,
        }
        evidence_id = f"state-conflict-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_STATE_CONFLICT_RECORD_TYPE) != _STATE_CONFLICT_RECORD
                or metadata.get(_STATE_CONFLICT_DOCUMENT) != payload
                or metadata.get("object_id") != item.conflict_id
                or metadata.get("object_fingerprint") != item.fingerprint
            ):
                raise ValueError(f"state-conflict Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="state_conflict",
            statement=canonical_semantic_json(payload),
            source=STATE_CONFLICT_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _STATE_CONFLICT_RECORD_TYPE: _STATE_CONFLICT_RECORD,
                _STATE_CONFLICT_DOCUMENT: payload,
                "object_id": item.conflict_id,
                "object_fingerprint": item.fingerprint,
                "recorded_by_principal_id": actor_principal_id,
                "recorded_at_context_time": float(at_time),
                "semantic_identity_includes_recorder": False,
                "semantic_identity_includes_host_time": False,
                "claim_mutation": "NONE",
                "machine_state_mutation": "NONE",
                "fact_authority_creation": "NONE",
                "effect_authority": "NONE",
                "observation_authority_elevation": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(
            record,
            expected_machine_version=self.snapshot.version,
            reason=reason,
        )
        return evidence_id

    def _authorize_state_conflict_record(
        self,
        item: StateConflict,
        *,
        actor_principal_id: str,
        at_time: float,
        derived_from: Sequence[str],
    ) -> dict[str, Any]:
        if not actor_principal_id:
            raise PermissionError("state-conflict recording requires actor_principal_id")
        authorization = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                item.workspace_id,
                item.scope_id,
                STATE_CONFLICT_CAPABILITIES["record"],
                at_time=float(at_time),
                machine_id=self.snapshot.machine_id,
                metadata={
                    "conflict_id": item.conflict_id,
                    "expectation_claim_id": item.expectation_claim_id,
                    "actual_claim_id": item.actual_claim_id,
                },
            ),
            derived_from=tuple(derived_from),
            reason="state-conflict scoped authority evaluated",
        )
        if not authorization["decision"]["allowed"]:
            raise PermissionError(
                f"state-conflict denied {STATE_CONFLICT_CAPABILITIES['record']}: {authorization['decision']['reason']}"
            )
        return authorization

    def build_state_conflict(self, expectation_claim_id: str, actual_claim_id: str) -> StateConflict:
        expectation_row = self.state_claim_report(str(expectation_claim_id))
        actual_row = self.state_claim_report(str(actual_claim_id))
        expectation = StateClaim.from_dict(expectation_row["claim"])
        actual = StateClaim.from_dict(actual_row["claim"])
        return StateConflict.from_claims(expectation, actual)

    def record_state_conflict(
        self,
        expectation_claim_id: str,
        actual_claim_id: str,
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "state expectation conflict recorded",
    ) -> dict[str, Any]:
        expectation_row = self.state_claim_report(str(expectation_claim_id))
        actual_row = self.state_claim_report(str(actual_claim_id))
        expectation = StateClaim.from_dict(expectation_row["claim"])
        actual = StateClaim.from_dict(actual_row["claim"])
        item = StateConflict.from_claims(expectation, actual)

        claim_evidence = (
            str(expectation_row["evidence_id"]),
            str(actual_row["evidence_id"]),
        )
        requested_evidence = tuple(map(str, evidence_ids))
        base_lineage = tuple(sorted(set((*claim_evidence, *requested_evidence))))
        self._require_evidence_ids(base_lineage)

        projection = self._require_valid_state_conflict_projection()
        prior = projection["conflicts"].get(item.conflict_id)
        if prior is not None:
            if prior["conflict"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"state conflict identity collision: {item.conflict_id}")
            return {
                **deepcopy(prior),
                "already_recorded": True,
                "claim_mutation": False,
                "machine_state_mutation": False,
                "fact_authority_created": False,
                "effect_authority_granted": False,
                "observation_authority_elevated": False,
            }

        authorization = self._authorize_state_conflict_record(
            item,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=base_lineage,
        )
        lineage = tuple(sorted(set((*base_lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_state_conflict_document(
            item,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "conflict": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "claim_mutation": False,
            "machine_state_mutation": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "observation_authority_elevated": False,
        }

    def state_conflict_report(self, conflict_id: str) -> dict[str, Any]:
        projection = self._require_valid_state_conflict_projection()
        try:
            return deepcopy(projection["conflicts"][str(conflict_id)])
        except KeyError:
            raise KeyError(f"unknown durable state conflict: {conflict_id}") from None

    def state_conflicts_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_state_conflict_projection()
        conflicts: dict[str, dict[str, Any]] = {}
        for conflict_id, row in sorted(projection["conflicts"].items()):
            document = row["conflict"]
            if workspace_id is not None and document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            conflicts[conflict_id] = deepcopy(row)
        return {
            "runtime_contract": deepcopy(projection["runtime_contract"]),
            "valid": True,
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "conflicts": conflicts,
            "claim_mutation": "NONE",
            "machine_state_mutation": "NONE",
            "fact_authority_creation": "NONE",
            "effect_authority": "NONE",
        }


__all__ = [
    "STATE_CONFLICT_RUNTIME_CONTRACT_ID",
    "STATE_CONFLICT_RUNTIME_CONTRACT_VERSION",
    "STATE_CONFLICT_RUNTIME_STABILITY",
    "STATE_CONFLICT_CAPABILITIES",
    "StateConflictRuntimeMixin",
    "project_state_conflict_evidence",
    "state_conflict_runtime_contract",
]
