from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .calibration import CalibrationCertificate
from .evidence import EvidenceRecord
from .physical_identity import PhysicalIdentity
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .source_trust import (
    SOURCE_TRUST_CONTRACT_ID,
    SourceTrustAssertion,
    SourceTrustRevocation,
    source_trust_contract,
)


SOURCE_TRUST_RUNTIME_CONTRACT_ID = "aasm.source.trust.runtime.v1"
SOURCE_TRUST_RUNTIME_CONTRACT_VERSION = "0.1.0"
SOURCE_TRUST_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
SOURCE_TRUST_CAPABILITIES = {
    "record": "source.trust.record",
    "revoke": "source.trust.revoke",
}

_SOURCE_TRUST_RECORD_TYPE = "aasm_source_trust_record_type"
_SOURCE_TRUST_DOCUMENT = "document"
_SOURCE_TRUST_RECORD = "SOURCE_TRUST_ASSERTION"
_SOURCE_TRUST_REVOCATION_RECORD = "SOURCE_TRUST_REVOCATION"


def source_trust_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": SOURCE_TRUST_RUNTIME_CONTRACT_ID,
        "contract_version": SOURCE_TRUST_RUNTIME_CONTRACT_VERSION,
        "stability": SOURCE_TRUST_RUNTIME_STABILITY,
        "semantic_contract": source_trust_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORD_REVOKE_NOT_TRUST_EVALUATION",
        "capabilities": deepcopy(SOURCE_TRUST_CAPABILITIES),
        "source_principal": "MUST_EXIST_IN_EXISTING_SCOPED_IDENTITY_PROJECTION",
        "physical_identity": "OPTIONAL_EXACT_EXISTING_PHYSICAL_IDENTITY",
        "required_calibrations": "OPTIONAL_EXACT_EXISTING_CALIBRATIONS_WITH_INTERVAL_CONTAINMENT",
        "evaluation_time": "EXPLICIT_CALLER_NANOSECOND_TIME_ONLY",
        "selection": "EXPLICIT_TRUST_ID_NO_LATEST_REPUTATION_OR_AGGREGATION",
        "fact_authority": "EXISTING_FACT_AUTHORITY_REMAINS_SEPARATE_AND_REQUIRED",
        "trusted_claim_admission": "NONE",
        "effect_authority": "NONE",
        "state_claim_mutation": "NONE",
        "observation_mutation": "NONE",
        "reputation_score": "NONE",
        "aggregation": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_trust_registry": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_SOURCE_TRUST_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("source-trust Evidence is missing canonical document")


def project_source_trust_evidence(records) -> dict[str, Any]:
    assertions: dict[str, dict[str, Any]] = {}
    revocations: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_SOURCE_TRUST_RECORD_TYPE)
        if record_type not in {_SOURCE_TRUST_RECORD, _SOURCE_TRUST_REVOCATION_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _SOURCE_TRUST_RECORD:
                item = SourceTrustAssertion.from_dict(document)
                object_id = item.trust_id
                fingerprint = item.fingerprint
                candidate = {"assertion": item.to_dict(), "evidence_id": evidence_id}
                prior = assertions.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"source trust identity collision: {object_id}")
                assertions[object_id] = candidate
            else:
                item = SourceTrustRevocation.from_dict(document)
                object_id = item.trust_id
                fingerprint = item.fingerprint
                candidate = {"revocation": item.to_dict(), "evidence_id": evidence_id}
                prior = revocations.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"source trust assertion has multiple non-identical revocations: {object_id}")
                revocations[object_id] = candidate
            if metadata.get("object_id") != object_id:
                raise ValueError(f"source-trust metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"source-trust metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for trust_id, row in revocations.items():
        assertion = assertions.get(trust_id)
        if assertion is None:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _SOURCE_TRUST_REVOCATION_RECORD,
                    "error": f"ValueError: source trust revocation references unknown assertion: {trust_id}",
                }
            )
            continue
        if row["revocation"]["trust_fingerprint"] != assertion["assertion"]["fingerprint"]:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _SOURCE_TRUST_REVOCATION_RECORD,
                    "error": f"ValueError: source trust revocation fingerprint mismatch: {trust_id}",
                }
            )
    return {
        "runtime_contract": source_trust_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "assertions": assertions,
        "revocations": revocations,
    }


class SourceTrustRuntimeMixin:
    def source_trust_contract_report(self) -> dict[str, Any]:
        return source_trust_runtime_contract()

    def _source_trust_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_source_trust_evidence(records)

    def _require_valid_source_trust_projection(self) -> dict[str, Any]:
        report = self._source_trust_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable source-trust projection: {report['issues']}")
        return report

    def _require_known_source_principal(self, workspace_id: str, principal_id: str) -> None:
        principals, _, _ = self._workspace_authority_inputs(workspace_id)
        known = {row.principal_id for row in principals}
        if principal_id not in known:
            raise KeyError(f"unknown source principal in workspace: {principal_id}")

    def _authorize_source_trust_action(
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
            raise PermissionError("source-trust mutation requires actor_principal_id")
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
            reason=f"source-trust scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"source-trust denied {capability}: {result['decision']['reason']}")
        return result

    def _record_source_trust_document(
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
        evidence_id = f"source-trust-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_SOURCE_TRUST_RECORD_TYPE) != record_type
                or metadata.get(_SOURCE_TRUST_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"source-trust Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="source_trust",
            statement=canonical_semantic_json(payload),
            source=SOURCE_TRUST_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _SOURCE_TRUST_RECORD_TYPE: record_type,
                _SOURCE_TRUST_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "recorded_by_principal_id": actor_principal_id,
                "recorded_at_context_time": float(at_time),
                "host_context_time_is_trust_validity_time": False,
                "fact_authority_creation": "NONE",
                "effect_authority": "NONE",
                "trusted_claim_admission": "NONE",
                "state_claim_mutation": "NONE",
                "observation_mutation": "NONE",
                "reputation_score": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def _validate_source_trust_dependencies(
        self,
        item: SourceTrustAssertion,
    ) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]], tuple[str, ...]]:
        self._require_known_source_principal(item.workspace_id, item.source_principal_id)
        lineage: set[str] = set()
        identity_row = None
        identity = None
        if item.physical_identity_id:
            identity_row = self.physical_identity_report(item.physical_identity_id)
            identity = PhysicalIdentity.from_dict(identity_row["identity"])
            if identity.fingerprint != item.physical_identity_fingerprint:
                raise ValueError("source trust physical identity fingerprint mismatch")
            if identity.workspace_id != item.workspace_id or identity.scope_id != item.scope_id:
                raise ValueError("source trust workspace/scope does not match physical identity")
            if identity.subject_id != item.subject_id:
                raise ValueError("source trust subject does not match physical identity")
            if identity.problem_revision_id != item.problem_revision_id:
                raise ValueError("source trust problem revision must exactly match physical identity")
            if identity.external_revision_id != item.external_revision_id:
                raise ValueError("source trust external revision must exactly match physical identity")
            lineage.add(str(identity_row["evidence_id"]))

        calibration_rows: dict[str, dict[str, Any]] = {}
        for calibration_id, expected_fingerprint in item.required_calibrations.items():
            report = self.calibration_report(calibration_id, reference_time_ns=item.valid_from_ns)
            calibration = CalibrationCertificate.from_dict(report["calibration"])
            if calibration.fingerprint != expected_fingerprint:
                raise ValueError(f"source trust calibration fingerprint mismatch: {calibration_id}")
            if identity is None:
                raise ValueError("source trust required calibration lacks physical identity binding")
            if calibration.physical_identity_id != identity.identity_id or calibration.physical_identity_fingerprint != identity.fingerprint:
                raise ValueError(f"source trust calibration belongs to a different physical identity: {calibration_id}")
            if calibration.workspace_id != item.workspace_id or calibration.scope_id != item.scope_id:
                raise ValueError(f"source trust calibration workspace/scope mismatch: {calibration_id}")
            if calibration.subject_id != item.subject_id:
                raise ValueError(f"source trust calibration subject mismatch: {calibration_id}")
            if calibration.state_namespace not in item.state_namespaces:
                raise ValueError(f"source trust calibration namespace is outside assertion namespaces: {calibration_id}")
            if calibration.problem_revision_id != item.problem_revision_id or calibration.external_revision_id != item.external_revision_id:
                raise ValueError(f"source trust calibration revision mismatch: {calibration_id}")
            if calibration.valid_from_ns > item.valid_from_ns:
                raise ValueError(f"source trust starts before required calibration becomes valid: {calibration_id}")
            if item.expires_at_ns is None:
                if calibration.expires_at_ns is not None:
                    raise ValueError(f"unbounded source trust cannot depend on finite calibration validity: {calibration_id}")
            elif calibration.expires_at_ns is not None and item.expires_at_ns > calibration.expires_at_ns:
                raise ValueError(f"source trust validity exceeds required calibration validity: {calibration_id}")
            revocation = report.get("revocation")
            if revocation is not None:
                revoked_at_ns = int(revocation["revocation"]["revoked_at_ns"])
                if revoked_at_ns <= item.valid_from_ns:
                    raise ValueError(f"source trust depends on calibration revoked before trust validity: {calibration_id}")
                if item.expires_at_ns is None or item.expires_at_ns > revoked_at_ns:
                    raise ValueError(f"source trust validity crosses known calibration revocation: {calibration_id}")
                lineage.add(str(revocation["evidence_id"]))
            lineage.add(str(report["evidence_id"]))
            calibration_rows[calibration_id] = report
        return identity_row, calibration_rows, tuple(sorted(lineage))

    def record_source_trust(
        self,
        assertion: SourceTrustAssertion | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "source trust assertion recorded",
    ) -> dict[str, Any]:
        item = assertion if isinstance(assertion, SourceTrustAssertion) else SourceTrustAssertion.from_dict(assertion)
        identity_row, calibration_rows, dependency_lineage = self._validate_source_trust_dependencies(item)
        projection = self._require_valid_source_trust_projection()
        prior = projection["assertions"].get(item.trust_id)
        if prior is not None:
            if prior["assertion"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"source trust identity collision: {item.trust_id}")
            return {
                **deepcopy(prior),
                "already_recorded": True,
                "fact_authority_created": False,
                "effect_authority_granted": False,
                "claim_admitted": False,
                "reputation_score_created": False,
            }
        lineage = self._require_evidence_ids(
            tuple(sorted(set((*map(str, evidence_ids), *dependency_lineage))))
        )
        authorization = self._authorize_source_trust_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=SOURCE_TRUST_CAPABILITIES["record"],
            at_time=at_time,
            metadata={
                "trust_id": item.trust_id,
                "source_principal_id": item.source_principal_id,
                "subject_id": item.subject_id,
                "trust_disposition": item.trust_disposition,
                "physical_identity_id": item.physical_identity_id,
            },
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_source_trust_document(
            record_type=_SOURCE_TRUST_RECORD,
            object_id=item.trust_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "assertion": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "physical_identity_evidence_id": None if identity_row is None else identity_row["evidence_id"],
            "calibration_evidence_ids": {key: row["evidence_id"] for key, row in calibration_rows.items()},
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "claim_admitted": False,
            "reputation_score_created": False,
        }

    def revoke_source_trust(
        self,
        trust_id: str,
        *,
        revoked_at_ns: int,
        reason_code: str,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "source trust assertion revoked",
    ) -> dict[str, Any]:
        projection = self._require_valid_source_trust_projection()
        row = projection["assertions"].get(str(trust_id))
        if row is None:
            raise KeyError(f"unknown source trust assertion: {trust_id}")
        item = SourceTrustAssertion.from_dict(row["assertion"])
        revocation = SourceTrustRevocation(item.trust_id, item.fingerprint, revoked_at_ns, reason_code)
        prior = projection["revocations"].get(item.trust_id)
        if prior is not None:
            if prior["revocation"]["fingerprint"] != revocation.fingerprint:
                raise ValueError("source trust assertion already has a different durable revocation")
            return {
                **deepcopy(prior),
                "already_revoked": True,
                "fact_authority_created": False,
                "effect_authority_granted": False,
            }
        lineage = self._require_evidence_ids(
            tuple(sorted(set((*map(str, evidence_ids), str(row["evidence_id"])))) )
        )
        authorization = self._authorize_source_trust_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=SOURCE_TRUST_CAPABILITIES["revoke"],
            at_time=at_time,
            metadata={
                "trust_id": item.trust_id,
                "revocation_id": revocation.revocation_id,
                "revoked_at_ns": revocation.revoked_at_ns,
            },
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_source_trust_document(
            record_type=_SOURCE_TRUST_REVOCATION_RECORD,
            object_id=item.trust_id,
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

    def source_trust_report(self, trust_id: str, *, reference_time_ns: int) -> dict[str, Any]:
        projection = self._require_valid_source_trust_projection()
        row = projection["assertions"].get(str(trust_id))
        if row is None:
            raise KeyError(f"unknown source trust assertion: {trust_id}")
        item = SourceTrustAssertion.from_dict(row["assertion"])
        revocation_row = projection["revocations"].get(item.trust_id)
        revoked_at_ns = None
        if revocation_row is not None:
            revoked_at_ns = SourceTrustRevocation.from_dict(revocation_row["revocation"]).revoked_at_ns
        assertion_effective = item.active_at(reference_time_ns, revoked_at_ns)

        identity_exact = True
        identity_row = None
        if item.physical_identity_id:
            identity_row = self.physical_identity_report(item.physical_identity_id)
            identity = PhysicalIdentity.from_dict(identity_row["identity"])
            identity_exact = identity.fingerprint == item.physical_identity_fingerprint

        calibrations: dict[str, dict[str, Any]] = {}
        calibrations_active = True
        for calibration_id, expected_fingerprint in item.required_calibrations.items():
            report = self.calibration_report(calibration_id, reference_time_ns=reference_time_ns)
            calibrations[calibration_id] = report
            if report["calibration"]["fingerprint"] != expected_fingerprint or not report["active_at_reference_time"]:
                calibrations_active = False

        policy_input_effective = bool(assertion_effective and identity_exact and calibrations_active)
        return {
            **deepcopy(row),
            "revocation": None if revocation_row is None else deepcopy(revocation_row),
            "reference_time_ns": int(reference_time_ns),
            "assertion_effective_at_reference_time": assertion_effective,
            "physical_identity_exact": identity_exact,
            "physical_identity": None if identity_row is None else deepcopy(identity_row),
            "required_calibrations": calibrations,
            "required_calibrations_active": calibrations_active,
            "policy_input_effective_at_reference_time": policy_input_effective,
            "trust_disposition": item.trust_disposition,
            "fact_authority_granted": False,
            "effect_authority_granted": False,
            "claim_admitted": False,
            "reputation_score": None,
            "universal_admission": False,
        }

    def source_trust_assertions_report(
        self,
        *,
        reference_time_ns: int,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        source_principal_id: str | None = None,
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_source_trust_projection()
        assertions: dict[str, dict[str, Any]] = {}
        for trust_id, row in sorted(projection["assertions"].items()):
            document = row["assertion"]
            if workspace_id is not None and document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            if source_principal_id is not None and document.get("source_principal_id") != source_principal_id:
                continue
            if subject_id is not None and document.get("subject_id") != subject_id:
                continue
            assertions[trust_id] = self.source_trust_report(trust_id, reference_time_ns=reference_time_ns)
        return {
            "runtime_contract": deepcopy(projection["runtime_contract"]),
            "reference_time_ns": int(reference_time_ns),
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "source_principal_id": source_principal_id,
            "subject_id": subject_id,
            "assertions": assertions,
            "revocations": deepcopy(projection["revocations"]),
            "fact_authority": "EXISTING_SEPARATE_SYSTEM_UNCHANGED",
            "effect_authority": "NONE",
            "reputation_score": "NONE",
            "aggregation": "NONE",
        }


__all__ = [
    "SOURCE_TRUST_RUNTIME_CONTRACT_ID",
    "SOURCE_TRUST_RUNTIME_CONTRACT_VERSION",
    "SOURCE_TRUST_RUNTIME_STABILITY",
    "SOURCE_TRUST_CAPABILITIES",
    "SourceTrustRuntimeMixin",
    "project_source_trust_evidence",
    "source_trust_runtime_contract",
]
