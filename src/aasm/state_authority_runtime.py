from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import (
    FACT_AUTHORITY_CONTRACT_ID,
    STATE_CLAIM_CONTRACT_ID,
    FactAuthority,
    StateClaim,
    fact_authority_matches_claim,
    state_authority_contract,
)


STATE_AUTHORITY_RUNTIME_CONTRACT_ID = "aasm.state.authority.runtime.v1"
STATE_AUTHORITY_RUNTIME_CONTRACT_VERSION = "0.1.0"
STATE_AUTHORITY_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

STATE_AUTHORITY_CAPABILITIES = {
    "fact_authority_register": "state.fact-authority.register",
    "fact_authority_revoke": "state.fact-authority.revoke",
    "claim_desired": "state.claim.desired",
    "claim_predicted": "state.claim.predicted",
    "claim_observed": "state.claim.observed",
    "claim_authoritative": "state.claim.authoritative",
}

_STATE_AUTHORITY_RECORD_TYPE = "aasm_state_authority_record_type"
_STATE_AUTHORITY_DOCUMENT = "document"

_FACT_AUTHORITY_RECORD = "FACT_AUTHORITY"
_FACT_AUTHORITY_REVOCATION_RECORD = "FACT_AUTHORITY_REVOCATION"
_STATE_CLAIM_RECORD = "STATE_CLAIM"


def state_authority_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": STATE_AUTHORITY_RUNTIME_CONTRACT_ID,
        "contract_version": STATE_AUTHORITY_RUNTIME_CONTRACT_VERSION,
        "stability": STATE_AUTHORITY_RUNTIME_STABILITY,
        "semantic_contract": state_authority_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(STATE_AUTHORITY_CAPABILITIES),
        "fact_authority_registration": "SCOPED_AUTHORITY_REQUIRED",
        "fact_authority_revocation": "SCOPED_AUTHORITY_REQUIRED_APPEND_ONLY_REVOCATION",
        "state_claim_recording": "SCOPED_AUTHORITY_REQUIRED",
        "authoritative_claim": "MATCHING_ACTIVE_FACT_AUTHORITY_AND_DURABLE_OBSERVED_SOURCE_REQUIRED",
        "source_principal": "ACTOR_MUST_EQUAL_DECLARED_SOURCE_PRINCIPAL",
        "parallel_truth_table": "NONE",
        "machine_state_mutation": "NONE",
        "effect_authority": "NONE",
        "aggregation_grants_authority": False,
        "cross_run_authority_transfer": "NEVER",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_STATE_AUTHORITY_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("state-authority Evidence is missing canonical document")


def project_state_authority_evidence(records) -> dict[str, Any]:
    authorities: dict[str, dict[str, Any]] = {}
    revocations: dict[str, dict[str, Any]] = {}
    claims: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []

    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_STATE_AUTHORITY_RECORD_TYPE)
        if record_type not in {
            _FACT_AUTHORITY_RECORD,
            _FACT_AUTHORITY_REVOCATION_RECORD,
            _STATE_CLAIM_RECORD,
        }:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _FACT_AUTHORITY_RECORD:
                item = FactAuthority.from_dict(document)
                object_id = item.authority_id
                fingerprint = item.fingerprint
                candidate = {"authority": item.to_dict(), "evidence_id": evidence_id}
                prior = authorities.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"fact authority identity collision: {object_id}")
                authorities[object_id] = candidate
            elif record_type == _FACT_AUTHORITY_REVOCATION_RECORD:
                object_id = str(document.get("authority_id") or "")
                if not object_id:
                    raise ValueError("fact authority revocation authority_id is required")
                fingerprint = str(document.get("authority_fingerprint") or "")
                if not fingerprint:
                    raise ValueError("fact authority revocation authority_fingerprint is required")
                candidate = {"revocation": document, "evidence_id": evidence_id}
                prior = revocations.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"fact authority has multiple non-identical revocations: {object_id}")
                revocations[object_id] = candidate
            else:
                item = StateClaim.from_dict(document)
                object_id = item.claim_id
                fingerprint = item.fingerprint
                candidate = {"claim": item.to_dict(), "evidence_id": evidence_id}
                prior = claims.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"state claim identity collision: {object_id}")
                claims[object_id] = candidate

            if metadata.get("object_id") != object_id:
                raise ValueError(f"state-authority metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"state-authority metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for authority_id, row in revocations.items():
        authority = authorities.get(authority_id)
        if authority is None:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _FACT_AUTHORITY_REVOCATION_RECORD,
                    "error": f"ValueError: revocation references unknown fact authority: {authority_id}",
                }
            )
            continue
        if row["revocation"].get("authority_fingerprint") != authority["authority"]["fingerprint"]:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _FACT_AUTHORITY_REVOCATION_RECORD,
                    "error": f"ValueError: revocation fingerprint mismatch: {authority_id}",
                }
            )

    return {
        "runtime_contract": state_authority_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "authorities": authorities,
        "revocations": revocations,
        "claims": claims,
    }


class StateAuthorityRuntimeMixin:
    def state_authority_contract_report(self) -> dict[str, Any]:
        return state_authority_runtime_contract()

    def _state_authority_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_state_authority_evidence(records)

    def _require_valid_state_authority_projection(self) -> dict[str, Any]:
        report = self._state_authority_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable state-authority projection: {report['issues']}")
        return report

    def _record_state_authority_document(
        self,
        *,
        record_type: str,
        object_id: str,
        object_fingerprint: str,
        document: Mapping[str, Any],
        source: str,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"state-authority-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_STATE_AUTHORITY_RECORD_TYPE) != record_type
                or metadata.get(_STATE_AUTHORITY_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"state-authority Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="state_authority",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                _STATE_AUTHORITY_RECORD_TYPE: record_type,
                _STATE_AUTHORITY_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "machine_state_mutation": "NONE",
                "effect_authority": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(
            record,
            expected_machine_version=self.snapshot.version,
            reason=reason,
        )
        return evidence_id

    def _authorize_state_authority_action(
        self,
        *,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        capability: str,
        at_time: float,
        metadata: Mapping[str, Any] | None = None,
        derived_from: Sequence[str] = (),
    ) -> dict[str, Any]:
        if not actor_principal_id:
            raise PermissionError("state-authority mutation requires actor_principal_id")
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                capability,
                at_time=float(at_time),
                machine_id=self.snapshot.machine_id,
                metadata=deepcopy(dict(metadata or {})),
            ),
            derived_from=tuple(derived_from),
            reason=f"state-authority scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"state-authority denied {capability}: {result['decision']['reason']}"
            )
        return result

    def register_fact_authority(
        self,
        authority: FactAuthority | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "fact authority registered",
    ) -> dict[str, Any]:
        item = authority if isinstance(authority, FactAuthority) else FactAuthority.from_dict(authority)
        principals, _, _ = self._workspace_authority_inputs(item.workspace_id)
        if item.authority_principal_id not in {row.principal_id for row in principals}:
            raise KeyError(f"unknown fact-authority principal in workspace: {item.authority_principal_id}")
        authorization = self._authorize_state_authority_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=STATE_AUTHORITY_CAPABILITIES["fact_authority_register"],
            at_time=at_time,
            metadata={"authority_id": item.authority_id, "authority_principal_id": item.authority_principal_id},
            derived_from=tuple(evidence_ids),
        )
        projection = self._require_valid_state_authority_projection()
        prior = projection["authorities"].get(item.authority_id)
        if prior is not None:
            if prior["authority"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"fact authority identity collision: {item.authority_id}")
            return {**deepcopy(prior), "already_registered": True}
        lineage = tuple(sorted(set((*map(str, evidence_ids), str(authorization["evidence_id"])))))
        evidence_id = self._record_state_authority_document(
            record_type=_FACT_AUTHORITY_RECORD,
            object_id=item.authority_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=FACT_AUTHORITY_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "authority": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_registered": False,
        }

    def revoke_fact_authority(
        self,
        authority_id: str,
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "fact authority revoked",
    ) -> dict[str, Any]:
        projection = self._require_valid_state_authority_projection()
        try:
            row = projection["authorities"][authority_id]
        except KeyError:
            raise KeyError(f"unknown fact authority: {authority_id}") from None
        prior_revocation = projection["revocations"].get(authority_id)
        if prior_revocation is not None:
            return {**deepcopy(prior_revocation), "already_revoked": True}
        item = FactAuthority.from_dict(row["authority"])
        authorization = self._authorize_state_authority_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=STATE_AUTHORITY_CAPABILITIES["fact_authority_revoke"],
            at_time=at_time,
            metadata={"authority_id": item.authority_id},
            derived_from=tuple(evidence_ids),
        )
        document = {
            "authority_id": item.authority_id,
            "authority_fingerprint": item.fingerprint,
            "revoked_by_principal_id": actor_principal_id,
            "revoked_at": float(at_time),
            "reason": str(reason),
        }
        object_fingerprint = semantic_fingerprint(document)
        lineage = tuple(
            sorted(
                set(
                    (
                        str(row["evidence_id"]),
                        str(authorization["evidence_id"]),
                        *map(str, evidence_ids),
                    )
                )
            )
        )
        evidence_id = self._record_state_authority_document(
            record_type=_FACT_AUTHORITY_REVOCATION_RECORD,
            object_id=item.authority_id,
            object_fingerprint=object_fingerprint,
            document=document,
            source=FACT_AUTHORITY_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "revocation": document,
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_revoked": False,
        }

    def _source_state_claim_rows(self, claim: StateClaim, projection: Mapping[str, Any]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for source_claim_id in claim.source_claim_ids:
            try:
                row = deepcopy(projection["claims"][source_claim_id])
            except KeyError:
                raise KeyError(f"unknown durable source state claim: {source_claim_id}") from None
            source = StateClaim.from_dict(row["claim"])
            if (
                source.workspace_id != claim.workspace_id
                or source.scope_id != claim.scope_id
                or source.subject_id != claim.subject_id
                or source.state_namespace != claim.state_namespace
            ):
                raise ValueError("source state claim context does not match target claim")
            if claim.problem_revision_id and source.problem_revision_id and source.problem_revision_id != claim.problem_revision_id:
                raise ValueError("source state claim problem revision mismatch")
            if claim.external_revision_id and source.external_revision_id and source.external_revision_id != claim.external_revision_id:
                raise ValueError("source state claim external revision mismatch")
            rows.append(row)
        return rows

    def _matching_active_fact_authority(
        self,
        claim: StateClaim,
        projection: Mapping[str, Any],
        *,
        at_time: float,
    ) -> tuple[FactAuthority, dict[str, Any]]:
        for authority_id, row in sorted(projection["authorities"].items()):
            if authority_id in projection["revocations"]:
                continue
            authority = FactAuthority.from_dict(row["authority"])
            if fact_authority_matches_claim(authority, claim, at_time=at_time):
                return authority, deepcopy(row)
        raise PermissionError("no active matching fact authority for AUTHORITATIVE state claim")

    def record_state_claim(
        self,
        claim: StateClaim | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        reason: str = "state claim recorded",
    ) -> dict[str, Any]:
        item = claim if isinstance(claim, StateClaim) else StateClaim.from_dict(claim)
        if actor_principal_id != item.source_principal_id:
            raise PermissionError("state claim actor must equal source_principal_id")
        capability = STATE_AUTHORITY_CAPABILITIES[f"claim_{item.claim_kind.lower()}"]
        projection = self._require_valid_state_authority_projection()
        source_rows = self._source_state_claim_rows(item, projection)
        authority_row: dict[str, Any] | None = None
        authority: FactAuthority | None = None
        if item.claim_kind == "AUTHORITATIVE":
            if not any(StateClaim.from_dict(row["claim"]).claim_kind == "OBSERVED" for row in source_rows):
                raise ValueError("AUTHORITATIVE state claim requires at least one OBSERVED source claim")
            authority, authority_row = self._matching_active_fact_authority(item, projection, at_time=at_time)

        authorization = self._authorize_state_authority_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=capability,
            at_time=at_time,
            metadata={"claim_id": item.claim_id, "claim_kind": item.claim_kind},
            derived_from=item.evidence_ids,
        )

        prior = projection["claims"].get(item.claim_id)
        if prior is not None:
            if prior["claim"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"state claim identity collision: {item.claim_id}")
            return {**deepcopy(prior), "already_recorded": True}

        lineage = set(map(str, item.evidence_ids))
        lineage.add(str(authorization["evidence_id"]))
        lineage.update(str(row["evidence_id"]) for row in source_rows)
        if authority_row is not None:
            lineage.add(str(authority_row["evidence_id"]))

        evidence_id = self._record_state_authority_document(
            record_type=_STATE_CLAIM_RECORD,
            object_id=item.claim_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=STATE_CLAIM_CONTRACT_ID,
            derived_from=tuple(sorted(lineage)),
            reason=reason,
        )
        return {
            "claim": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "fact_authority_id": "" if authority is None else authority.authority_id,
            "already_recorded": False,
        }

    def state_claim_report(self, claim_id: str) -> dict[str, Any]:
        projection = self._require_valid_state_authority_projection()
        try:
            return deepcopy(projection["claims"][claim_id])
        except KeyError:
            raise KeyError(f"unknown durable state claim: {claim_id}") from None

    def state_authority_report(self, *, at_time: float = 0.0) -> dict[str, Any]:
        projection = self._require_valid_state_authority_projection()
        authorities: dict[str, dict[str, Any]] = {}
        for authority_id, raw in projection["authorities"].items():
            row = deepcopy(raw)
            item = FactAuthority.from_dict(row["authority"])
            if authority_id in projection["revocations"]:
                status = "REVOKED"
            elif float(at_time) < item.valid_from:
                status = "NOT_YET_VALID"
            elif item.expires_at is not None and float(at_time) >= item.expires_at:
                status = "EXPIRED"
            else:
                status = "ACTIVE"
            row["status"] = status
            if authority_id in projection["revocations"]:
                row["revocation"] = deepcopy(projection["revocations"][authority_id])
            authorities[authority_id] = row
        return {
            "runtime_contract": state_authority_runtime_contract(),
            "valid": True,
            "at_time": float(at_time),
            "authorities": authorities,
            "claims": deepcopy(projection["claims"]),
            "machine_state_mutation": "NONE",
            "effect_authority": "NONE",
        }


__all__ = [
    "STATE_AUTHORITY_RUNTIME_CONTRACT_ID",
    "STATE_AUTHORITY_RUNTIME_CONTRACT_VERSION",
    "STATE_AUTHORITY_RUNTIME_STABILITY",
    "STATE_AUTHORITY_CAPABILITIES",
    "StateAuthorityRuntimeMixin",
    "project_state_authority_evidence",
    "state_authority_runtime_contract",
]
