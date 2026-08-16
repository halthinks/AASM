from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .calibration import (
    CALIBRATION_CONTRACT_ID,
    CalibrationCertificate,
    CalibrationRevocation,
    calibration_contract,
)
from .evidence import EvidenceRecord
from .physical_identity import PhysicalIdentity
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint


CALIBRATION_RUNTIME_CONTRACT_ID = "aasm.calibration.runtime.v1"
CALIBRATION_RUNTIME_CONTRACT_VERSION = "0.1.0"
CALIBRATION_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
CALIBRATION_CAPABILITIES = {
    "record": "calibration.record",
    "revoke": "calibration.revoke",
}

_CALIBRATION_RECORD_TYPE = "aasm_calibration_record_type"
_CALIBRATION_DOCUMENT = "document"
_CALIBRATION_RECORD = "CALIBRATION_CERTIFICATE"
_CALIBRATION_REVOCATION_RECORD = "CALIBRATION_REVOCATION"


def calibration_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": CALIBRATION_RUNTIME_CONTRACT_ID,
        "contract_version": CALIBRATION_RUNTIME_CONTRACT_VERSION,
        "stability": CALIBRATION_RUNTIME_STABILITY,
        "semantic_contract": calibration_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(CALIBRATION_CAPABILITIES),
        "identity_source": "EXACT_EXISTING_PHYSICAL_IDENTITY_ONLY",
        "validity_reference": "EXPLICIT_CALLER_NANOSECOND_TIME_ONLY",
        "revocation": "APPEND_ONLY_ONE_EXACT_REVOCATION_PER_CALIBRATION",
        "selection": "EXPLICIT_CALIBRATION_ID_NO_LATEST_OR_CURRENT_POINTER",
        "transform_application": "NONE_S3_FOUNDATION",
        "observation_mutation": "NONE",
        "state_claim_mutation": "NONE",
        "fact_authority_creation": "NONE",
        "effect_authority": "NONE",
        "source_trust": "NONE_CALIBRATION_IS_ONLY_EVIDENCE_INPUT_TO_LATER_POLICY",
        "parallel_calibration_store": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_CALIBRATION_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("calibration Evidence is missing canonical document")


def project_calibration_evidence(records) -> dict[str, Any]:
    calibrations: dict[str, dict[str, Any]] = {}
    revocations: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_CALIBRATION_RECORD_TYPE)
        if record_type not in {_CALIBRATION_RECORD, _CALIBRATION_REVOCATION_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _CALIBRATION_RECORD:
                item = CalibrationCertificate.from_dict(document)
                object_id = item.calibration_id
                fingerprint = item.fingerprint
                candidate = {"calibration": item.to_dict(), "evidence_id": evidence_id}
                prior = calibrations.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"calibration identity collision: {object_id}")
                calibrations[object_id] = candidate
            else:
                item = CalibrationRevocation.from_dict(document)
                object_id = item.calibration_id
                fingerprint = item.fingerprint
                candidate = {"revocation": item.to_dict(), "evidence_id": evidence_id}
                prior = revocations.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"calibration has multiple non-identical revocations: {object_id}")
                revocations[object_id] = candidate
            if metadata.get("object_id") != object_id:
                raise ValueError(f"calibration metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"calibration metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for calibration_id, row in revocations.items():
        calibration = calibrations.get(calibration_id)
        if calibration is None:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _CALIBRATION_REVOCATION_RECORD,
                    "error": f"ValueError: calibration revocation references unknown calibration: {calibration_id}",
                }
            )
            continue
        if row["revocation"]["calibration_fingerprint"] != calibration["calibration"]["fingerprint"]:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _CALIBRATION_REVOCATION_RECORD,
                    "error": f"ValueError: calibration revocation fingerprint mismatch: {calibration_id}",
                }
            )
    return {
        "runtime_contract": calibration_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "calibrations": calibrations,
        "revocations": revocations,
    }


class CalibrationRuntimeMixin:
    def calibration_contract_report(self) -> dict[str, Any]:
        return calibration_runtime_contract()

    def _calibration_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_calibration_evidence(records)

    def _require_valid_calibration_projection(self) -> dict[str, Any]:
        report = self._calibration_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable calibration projection: {report['issues']}")
        return report

    def _authorize_calibration_action(
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
            raise PermissionError("calibration mutation requires actor_principal_id")
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
            reason=f"calibration scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"calibration denied {capability}: {result['decision']['reason']}")
        return result

    def _record_calibration_document(
        self,
        *,
        record_type: str,
        object_id: str,
        object_fingerprint: str,
        document: Mapping[str, Any],
        actor_principal_id: str,
        at_time: float,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"calibration-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_CALIBRATION_RECORD_TYPE) != record_type
                or metadata.get(_CALIBRATION_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"calibration Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="calibration",
            statement=canonical_semantic_json(payload),
            source=CALIBRATION_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _CALIBRATION_RECORD_TYPE: record_type,
                _CALIBRATION_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "recorded_by_principal_id": actor_principal_id,
                "recorded_at_context_time": float(at_time),
                "host_context_time_is_calibration_validity_time": False,
                "observation_mutation": "NONE",
                "state_claim_mutation": "NONE",
                "fact_authority_creation": "NONE",
                "effect_authority": "NONE",
                "source_trust": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def record_calibration(
        self,
        calibration: CalibrationCertificate | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "calibration certificate recorded",
    ) -> dict[str, Any]:
        item = calibration if isinstance(calibration, CalibrationCertificate) else CalibrationCertificate.from_dict(calibration)
        identity_row = self.physical_identity_report(item.physical_identity_id)
        identity = PhysicalIdentity.from_dict(identity_row["identity"])
        if identity.fingerprint != item.physical_identity_fingerprint:
            raise ValueError("calibration physical identity fingerprint mismatch")
        if item.workspace_id != identity.workspace_id or item.scope_id != identity.scope_id:
            raise ValueError("calibration workspace/scope does not match physical identity")
        if item.subject_id != identity.subject_id:
            raise ValueError("calibration subject does not match physical identity")
        if item.problem_revision_id != identity.problem_revision_id:
            raise ValueError("calibration problem revision must exactly match physical identity")
        if item.external_revision_id != identity.external_revision_id:
            raise ValueError("calibration external revision must exactly match physical identity")

        projection = self._require_valid_calibration_projection()
        prior = projection["calibrations"].get(item.calibration_id)
        if prior is not None:
            if prior["calibration"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"calibration identity collision: {item.calibration_id}")
            return {
                **deepcopy(prior),
                "already_recorded": True,
                "fact_authority_created": False,
                "effect_authority_granted": False,
                "source_trust_granted": False,
                "observation_mutated": False,
            }
        lineage = self._require_evidence_ids(
            tuple(sorted(set((*map(str, evidence_ids), str(identity_row["evidence_id"])))) )
        )
        authorization = self._authorize_calibration_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=CALIBRATION_CAPABILITIES["record"],
            at_time=at_time,
            metadata={
                "calibration_id": item.calibration_id,
                "physical_identity_id": item.physical_identity_id,
                "state_namespace": item.state_namespace,
                "calibration_kind": item.calibration_kind,
            },
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_calibration_document(
            record_type=_CALIBRATION_RECORD,
            object_id=item.calibration_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "calibration": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "source_trust_granted": False,
            "observation_mutated": False,
        }

    def revoke_calibration(
        self,
        calibration_id: str,
        *,
        revoked_at_ns: int,
        reason_code: str,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "calibration revoked",
    ) -> dict[str, Any]:
        projection = self._require_valid_calibration_projection()
        row = projection["calibrations"].get(str(calibration_id))
        if row is None:
            raise KeyError(f"unknown calibration: {calibration_id}")
        item = CalibrationCertificate.from_dict(row["calibration"])
        revocation = CalibrationRevocation(item.calibration_id, item.fingerprint, revoked_at_ns, reason_code)
        prior = projection["revocations"].get(item.calibration_id)
        if prior is not None:
            if prior["revocation"]["fingerprint"] != revocation.fingerprint:
                raise ValueError("calibration already has a different durable revocation")
            return {
                **deepcopy(prior),
                "already_revoked": True,
                "fact_authority_created": False,
                "effect_authority_granted": False,
            }
        lineage = self._require_evidence_ids(
            tuple(sorted(set((*map(str, evidence_ids), str(row["evidence_id"])))) )
        )
        authorization = self._authorize_calibration_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=CALIBRATION_CAPABILITIES["revoke"],
            at_time=at_time,
            metadata={
                "calibration_id": item.calibration_id,
                "revocation_id": revocation.revocation_id,
                "revoked_at_ns": revocation.revoked_at_ns,
            },
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_calibration_document(
            record_type=_CALIBRATION_REVOCATION_RECORD,
            object_id=item.calibration_id,
            object_fingerprint=revocation.fingerprint,
            document=revocation.to_dict(),
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "revocation": revocation.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_revoked": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
        }

    def calibration_report(self, calibration_id: str, *, reference_time_ns: int) -> dict[str, Any]:
        projection = self._require_valid_calibration_projection()
        row = projection["calibrations"].get(str(calibration_id))
        if row is None:
            raise KeyError(f"unknown calibration: {calibration_id}")
        item = CalibrationCertificate.from_dict(row["calibration"])
        revocation_row = projection["revocations"].get(item.calibration_id)
        revoked_at_ns = None
        if revocation_row is not None:
            revoked_at_ns = CalibrationRevocation.from_dict(revocation_row["revocation"]).revoked_at_ns
        return {
            **deepcopy(row),
            "revocation": None if revocation_row is None else deepcopy(revocation_row),
            "reference_time_ns": int(reference_time_ns),
            "active_at_reference_time": item.active_at(reference_time_ns, revoked_at_ns),
            "fact_authority_granted": False,
            "effect_authority_granted": False,
            "source_trust_granted": False,
        }

    def calibrations_report(
        self,
        *,
        reference_time_ns: int,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        physical_identity_id: str | None = None,
        state_namespace: str | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_calibration_projection()
        rows: dict[str, dict[str, Any]] = {}
        for calibration_id, row in sorted(projection["calibrations"].items()):
            document = row["calibration"]
            if workspace_id is not None and document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            if physical_identity_id is not None and document.get("physical_identity_id") != physical_identity_id:
                continue
            if state_namespace is not None and document.get("state_namespace") != state_namespace:
                continue
            rows[calibration_id] = self.calibration_report(calibration_id, reference_time_ns=reference_time_ns)
        return {
            "runtime_contract": deepcopy(projection["runtime_contract"]),
            "reference_time_ns": int(reference_time_ns),
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "physical_identity_id": physical_identity_id,
            "state_namespace": state_namespace,
            "calibrations": rows,
            "revocations": deepcopy(projection["revocations"]),
        }


__all__ = [
    "CALIBRATION_RUNTIME_CONTRACT_ID",
    "CALIBRATION_RUNTIME_CONTRACT_VERSION",
    "CALIBRATION_RUNTIME_STABILITY",
    "CALIBRATION_CAPABILITIES",
    "CalibrationRuntimeMixin",
    "project_calibration_evidence",
    "calibration_runtime_contract",
]
