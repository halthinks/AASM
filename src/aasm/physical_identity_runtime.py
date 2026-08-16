from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .physical_identity import (
    PHYSICAL_IDENTITY_CONTRACT_ID,
    PhysicalIdentity,
    physical_identity_contract,
)
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint


PHYSICAL_IDENTITY_RUNTIME_CONTRACT_ID = "aasm.physical.identity.runtime.v1"
PHYSICAL_IDENTITY_RUNTIME_CONTRACT_VERSION = "0.1.0"
PHYSICAL_IDENTITY_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
PHYSICAL_IDENTITY_CAPABILITIES = {"record": "physical.identity.record"}

_PHYSICAL_IDENTITY_RECORD_TYPE = "aasm_physical_identity_record_type"
_PHYSICAL_IDENTITY_DOCUMENT = "document"
_PHYSICAL_IDENTITY_RECORD = "PHYSICAL_IDENTITY"


def physical_identity_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": PHYSICAL_IDENTITY_RUNTIME_CONTRACT_ID,
        "contract_version": PHYSICAL_IDENTITY_RUNTIME_CONTRACT_VERSION,
        "stability": PHYSICAL_IDENTITY_RUNTIME_STABILITY,
        "semantic_contract": physical_identity_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(PHYSICAL_IDENTITY_CAPABILITIES),
        "same_context_divergence": "REJECTED_BEFORE_RECORDING_REQUIRE_EXPLICIT_REVISION_CHANGE",
        "machine_binding_mutation": "NONE",
        "state_claim_mutation": "NONE",
        "fact_authority_creation": "NONE",
        "effect_authority": "NONE",
        "source_trust": "NONE_IDENTITY_IS_ONLY_AN_EXACT_REFERENCE",
        "attestation": "NONE_REFERENCE_SEAM_ONLY",
        "parallel_identity_registry": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_PHYSICAL_IDENTITY_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("physical-identity Evidence is missing canonical document")


def project_physical_identity_evidence(records) -> dict[str, Any]:
    identities: dict[str, dict[str, Any]] = {}
    contexts: dict[str, str] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        if metadata.get(_PHYSICAL_IDENTITY_RECORD_TYPE) != _PHYSICAL_IDENTITY_RECORD:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            item = PhysicalIdentity.from_dict(document)
            candidate = {"identity": item.to_dict(), "evidence_id": evidence_id}
            prior = identities.get(item.identity_id)
            if prior is not None and prior != candidate:
                raise ValueError(f"physical identity identity collision: {item.identity_id}")
            prior_context = contexts.get(item.logical_context_fingerprint)
            if prior_context is not None and prior_context != item.identity_id:
                raise ValueError(
                    "physical identity logical context names multiple exact identities; revision advance required"
                )
            if metadata.get("object_id") != item.identity_id:
                raise ValueError(f"physical-identity metadata object_id mismatch: {item.identity_id}")
            if metadata.get("object_fingerprint") != item.fingerprint:
                raise ValueError(f"physical-identity metadata fingerprint mismatch: {item.identity_id}")
            if metadata.get("logical_context_fingerprint") != item.logical_context_fingerprint:
                raise ValueError(f"physical-identity metadata logical-context mismatch: {item.identity_id}")
            identities[item.identity_id] = candidate
            contexts[item.logical_context_fingerprint] = item.identity_id
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": _PHYSICAL_IDENTITY_RECORD,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {
        "runtime_contract": physical_identity_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "identities": identities,
        "contexts": contexts,
    }


class PhysicalIdentityRuntimeMixin:
    def physical_identity_contract_report(self) -> dict[str, Any]:
        return physical_identity_runtime_contract()

    def _physical_identity_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_physical_identity_evidence(records)

    def _require_valid_physical_identity_projection(self) -> dict[str, Any]:
        report = self._physical_identity_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable physical-identity projection: {report['issues']}")
        return report

    def _authorize_physical_identity_record(
        self,
        item: PhysicalIdentity,
        *,
        actor_principal_id: str,
        at_time: float,
        derived_from: Sequence[str],
    ) -> dict[str, Any]:
        if not actor_principal_id:
            raise PermissionError("physical identity recording requires actor_principal_id")
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                item.workspace_id,
                item.scope_id,
                PHYSICAL_IDENTITY_CAPABILITIES["record"],
                at_time=float(at_time),
                machine_id=self.snapshot.machine_id,
                metadata={
                    "identity_id": item.identity_id,
                    "subject_id": item.subject_id,
                    "identity_class": item.identity_class,
                    "identity_namespace": item.identity_namespace,
                    "stable_id": item.stable_id,
                    "external_revision_id": item.external_revision_id,
                },
            ),
            derived_from=tuple(derived_from),
            reason="physical-identity scoped authority evaluated",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"physical-identity denied {PHYSICAL_IDENTITY_CAPABILITIES['record']}: {result['decision']['reason']}"
            )
        return result

    def _record_physical_identity_document(
        self,
        item: PhysicalIdentity,
        *,
        actor_principal_id: str,
        at_time: float,
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = item.to_dict()
        identity = {
            "record_type": _PHYSICAL_IDENTITY_RECORD,
            "object_id": item.identity_id,
            "document": payload,
        }
        evidence_id = f"physical-identity-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_PHYSICAL_IDENTITY_RECORD_TYPE) != _PHYSICAL_IDENTITY_RECORD
                or metadata.get(_PHYSICAL_IDENTITY_DOCUMENT) != payload
                or metadata.get("object_id") != item.identity_id
                or metadata.get("object_fingerprint") != item.fingerprint
                or metadata.get("logical_context_fingerprint") != item.logical_context_fingerprint
            ):
                raise ValueError(f"physical-identity Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="physical_identity",
            statement=canonical_semantic_json(payload),
            source=PHYSICAL_IDENTITY_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _PHYSICAL_IDENTITY_RECORD_TYPE: _PHYSICAL_IDENTITY_RECORD,
                _PHYSICAL_IDENTITY_DOCUMENT: payload,
                "object_id": item.identity_id,
                "object_fingerprint": item.fingerprint,
                "logical_context_fingerprint": item.logical_context_fingerprint,
                "recorded_by_principal_id": actor_principal_id,
                "recorded_at_context_time": float(at_time),
                "semantic_identity_includes_recorder": False,
                "semantic_identity_includes_host_time": False,
                "machine_binding_mutation": "NONE",
                "state_claim_mutation": "NONE",
                "fact_authority_creation": "NONE",
                "effect_authority": "NONE",
                "source_trust": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def record_physical_identity(
        self,
        identity: PhysicalIdentity | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "physical identity recorded",
    ) -> dict[str, Any]:
        item = identity if isinstance(identity, PhysicalIdentity) else PhysicalIdentity.from_dict(identity)
        lineage = self._require_evidence_ids(tuple(map(str, evidence_ids)))
        projection = self._require_valid_physical_identity_projection()
        prior = projection["identities"].get(item.identity_id)
        if prior is not None:
            if prior["identity"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"physical identity identity collision: {item.identity_id}")
            return {
                **deepcopy(prior),
                "already_recorded": True,
                "fact_authority_created": False,
                "effect_authority_granted": False,
                "source_trust_granted": False,
                "machine_binding_mutated": False,
            }
        prior_context_id = projection["contexts"].get(item.logical_context_fingerprint)
        if prior_context_id is not None and prior_context_id != item.identity_id:
            prior_context = projection["identities"][prior_context_id]["identity"]
            raise ValueError(
                "physical identity changed inside the same logical context; advance problem/external revision before recording different instance/configuration: "
                f"existing={prior_context_id} existing_fingerprint={prior_context['fingerprint']} new={item.identity_id}"
            )
        authorization = self._authorize_physical_identity_record(
            item,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=lineage,
        )
        full_lineage = tuple(sorted(set((*lineage, str(authorization["evidence_id"])))))
        evidence_id = self._record_physical_identity_document(
            item,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
            derived_from=full_lineage,
            reason=reason,
        )
        return {
            "identity": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_recorded": False,
            "fact_authority_created": False,
            "effect_authority_granted": False,
            "source_trust_granted": False,
            "machine_binding_mutated": False,
        }

    def physical_identity_report(self, identity_id: str) -> dict[str, Any]:
        projection = self._require_valid_physical_identity_projection()
        try:
            return deepcopy(projection["identities"][str(identity_id)])
        except KeyError:
            raise KeyError(f"unknown physical identity: {identity_id}") from None

    def physical_identities_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        subject_id: str | None = None,
        identity_class: str | None = None,
    ) -> dict[str, Any]:
        projection = self._require_valid_physical_identity_projection()
        identities: dict[str, dict[str, Any]] = {}
        for identity_id, row in sorted(projection["identities"].items()):
            document = row["identity"]
            if workspace_id is not None and document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            if subject_id is not None and document.get("subject_id") != subject_id:
                continue
            if identity_class is not None and document.get("identity_class") != identity_class:
                continue
            identities[identity_id] = deepcopy(row)
        return {
            "runtime_contract": deepcopy(projection["runtime_contract"]),
            "valid": True,
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "subject_id": subject_id,
            "identity_class": identity_class,
            "identities": identities,
            "fact_authority_creation": "NONE",
            "effect_authority": "NONE",
            "source_trust": "NONE",
        }


__all__ = [
    "PHYSICAL_IDENTITY_RUNTIME_CONTRACT_ID",
    "PHYSICAL_IDENTITY_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_IDENTITY_RUNTIME_STABILITY",
    "PHYSICAL_IDENTITY_CAPABILITIES",
    "PhysicalIdentityRuntimeMixin",
    "project_physical_identity_evidence",
    "physical_identity_runtime_contract",
]
