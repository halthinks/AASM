from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .effect_capability import EffectCapability
from .effect_capability_use import (
    EFFECT_CAPABILITY_USE_CONTRACT_ID,
    EffectCapabilityUse,
    effect_capability_use_contract,
)
from .evidence import EvidenceRecord
from .physical_authority import AUTHORITY_LEASE_CONTRACT_ID, AuthorityDomain, AuthorityLease
from .physical_preemption import (
    AUTHORITY_PREEMPTION_CONTRACT_ID,
    AuthorityPreemption,
    authority_preemption_contract,
)
from .semantic_result import canonical_semantic_json, semantic_fingerprint


PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID = "aasm.physical.control-fencing.runtime.v1"
PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_VERSION = "0.1.0"
PHYSICAL_CONTROL_FENCING_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

PHYSICAL_CONTROL_FENCING_CAPABILITIES = {
    "preempt": "physical.authority.preempt",
}

_CONTROL_FENCING_RECORD_TYPE = "aasm_physical_control_fencing_record_type"
_CONTROL_FENCING_DOCUMENT = "document"
_CAPABILITY_USE_RECORD = "EFFECT_CAPABILITY_USE_VALIDATION"
_AUTHORITY_PREEMPTION_RECORD = "AUTHORITY_PREEMPTION"
_AUTHORITY_LEASE_REVOCATION_RECORD = "AUTHORITY_LEASE_REVOCATION"


def physical_control_fencing_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID,
        "contract_version": PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_VERSION,
        "stability": PHYSICAL_CONTROL_FENCING_RUNTIME_STABILITY,
        "capability_use_contract": effect_capability_use_contract(),
        "preemption_contract": authority_preemption_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(PHYSICAL_CONTROL_FENCING_CAPABILITIES),
        "use_validation": "POINT_IN_TIME_ONLY_REQUIRES_RECHECK_AT_PR3H_EFFECT_BOUNDARIES",
        "use_numeric_parameters": "EXACT_CAPABILITY_BOUND_NAME_SET_REQUIRED_FOUNDATION",
        "preemption": "LISTED_PREEMPTOR_PLUS_SCOPED_PREEMPT_AUTHORITY",
        "preemption_effect": "EXISTING_AUTHORITY_LEASE_REVOCATION_REPRESENTATION",
        "preemption_epoch": "NEXT_LEASE_EPOCH_NATURALLY_PREEMPTED_EPOCH_PLUS_ONE",
        "use_validation_grants_effect_authority": False,
        "preemption_grants_effect_authority": False,
        "effect_authorization_integration": "NONE_PR3E_PR3F_PR3G_FOUNDATION",
        "effect_dispatch": "NONE",
        "machine_state_mutation": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_CONTROL_FENCING_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("physical-control-fencing Evidence is missing canonical document")


def project_physical_control_fencing_evidence(records) -> dict[str, Any]:
    uses: dict[str, dict[str, Any]] = {}
    preemptions: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_CONTROL_FENCING_RECORD_TYPE)
        if record_type not in {_CAPABILITY_USE_RECORD, _AUTHORITY_PREEMPTION_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _CAPABILITY_USE_RECORD:
                item = EffectCapabilityUse.from_dict(document)
                object_id = item.use_id
                fingerprint = item.fingerprint
                candidate = {"use": item.to_dict(), "evidence_id": evidence_id}
                prior = uses.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"effect capability use identity collision: {object_id}")
                uses[object_id] = candidate
            else:
                item = AuthorityPreemption.from_dict(document)
                object_id = item.preemption_id
                fingerprint = item.fingerprint
                candidate = {"preemption": item.to_dict(), "evidence_id": evidence_id}
                prior = preemptions.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"authority preemption identity collision: {object_id}")
                preemptions[object_id] = candidate
            if metadata.get("object_id") != object_id:
                raise ValueError(f"control-fencing metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"control-fencing metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append({
                "index": index,
                "evidence_id": evidence_id,
                "record_type": record_type,
                "error": f"{type(exc).__name__}: {exc}",
            })
    return {
        "runtime_contract": physical_control_fencing_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "uses": uses,
        "preemptions": preemptions,
    }


class PhysicalControlFencingRuntimeMixin:
    def physical_control_fencing_contract_report(self) -> dict[str, Any]:
        return physical_control_fencing_runtime_contract()

    def _physical_control_fencing_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_physical_control_fencing_evidence(records)

    def _require_valid_physical_control_fencing_projection(self) -> dict[str, Any]:
        report = self._physical_control_fencing_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable physical-control-fencing projection: {report['issues']}")
        return report

    def _record_control_fencing_document(
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
        evidence_id = f"physical-control-fence-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_CONTROL_FENCING_RECORD_TYPE) != record_type
                or metadata.get(_CONTROL_FENCING_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"physical-control-fencing Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="physical_control_fence",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                _CONTROL_FENCING_RECORD_TYPE: record_type,
                _CONTROL_FENCING_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "effect_authority": "NONE_PR3E_PR3F_PR3G_FOUNDATION",
                "machine_state_mutation": "NONE",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def validate_effect_capability_use(
        self,
        use: EffectCapabilityUse | Mapping[str, Any],
        *,
        evidence_ids: Sequence[str] = (),
        reason: str = "bounded effect capability use fenced",
    ) -> dict[str, Any]:
        item = use if isinstance(use, EffectCapabilityUse) else EffectCapabilityUse.from_dict(use)
        capability_row = self.effect_capability_report(item.capability_id, at_time=item.at_time)
        capability = EffectCapability.from_dict(capability_row["capability"])
        if not capability_row["active_at_time"]:
            raise PermissionError("effect capability is not active at command-use time")
        if item.capability_fingerprint != capability.fingerprint:
            raise PermissionError("effect capability use fingerprint is stale or mismatched")
        if item.actor_principal_id != capability.holder_principal_id:
            raise PermissionError("effect capability use actor must equal current capability holder")
        if item.authority_lease_id != capability.authority_lease_id:
            raise PermissionError("effect capability use authority lease identity mismatch")
        lease_row = self.authority_lease_report(item.authority_lease_id, at_time=item.at_time)
        lease = AuthorityLease.from_dict(lease_row["lease"])
        if not lease_row["active_at_time"]:
            raise PermissionError("effect capability use authority lease is not active")
        if item.authority_lease_fingerprint != lease.fingerprint:
            raise PermissionError("effect capability use authority lease fingerprint is stale or mismatched")
        domain_row = self.authority_domain_report(item.domain_id)
        domain = AuthorityDomain.from_dict(domain_row["domain"])
        for name in ("domain_id", "workspace_id", "scope_id", "subject_id", "problem_revision_id", "external_revision_id"):
            if getattr(item, name) != getattr(capability, name):
                raise PermissionError(f"effect capability use {name} does not match current capability")
        if domain.domain_id != item.domain_id or domain.workspace_id != item.workspace_id or domain.scope_id != item.scope_id or domain.subject_id != item.subject_id:
            raise PermissionError("effect capability use does not match current authority domain")
        if item.authority_epoch != capability.authority_epoch or item.authority_epoch != lease.epoch:
            raise PermissionError("effect capability use authority epoch is stale")
        current_generation = int(capability_row["effective_revocation_generation"])
        if item.capability_revocation_generation != current_generation:
            raise PermissionError("effect capability use revocation generation is stale")
        if not capability.allows_operation(item.operation):
            raise PermissionError("effect capability use operation is outside capability allow-list")
        if set(item.numeric_parameters) != set(capability.numeric_bounds):
            raise PermissionError("effect capability use numeric parameter names must exactly match current capability bounds")
        if not capability.bounds_allow(item.numeric_parameters):
            raise PermissionError("effect capability use numeric parameters exceed capability bounds")

        projection = self._require_valid_physical_control_fencing_projection()
        prior = projection["uses"].get(item.use_id)
        if prior is not None:
            if prior["use"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"effect capability use identity collision: {item.use_id}")
            return {
                **deepcopy(prior),
                "already_validated": True,
                "effect_authority_granted": False,
                "reusable_authorization_token": False,
            }
        lineage = tuple(sorted(set((
            *map(str, evidence_ids),
            str(capability_row["evidence_id"]),
            str(lease_row["evidence_id"]),
            str(domain_row["evidence_id"]),
        ))))
        evidence_id = self._record_control_fencing_document(
            record_type=_CAPABILITY_USE_RECORD,
            object_id=item.use_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=EFFECT_CAPABILITY_USE_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "use": item.to_dict(),
            "evidence_id": evidence_id,
            "already_validated": False,
            "effect_authority_granted": False,
            "reusable_authorization_token": False,
            "required_recheck": "PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES",
        }

    def preempt_authority_lease(
        self,
        lease_id: str,
        *,
        authority_lease_fingerprint: str,
        authority_epoch: int,
        actor_principal_id: str,
        at_time: float,
        reason_code: str,
        evidence_ids: Sequence[str] = (),
        reason: str = "authority lease semantically preempted",
    ) -> dict[str, Any]:
        projection = self._require_valid_physical_control_fencing_projection()
        for row in projection["preemptions"].values():
            document = row["preemption"]
            if document["authority_lease_id"] == str(lease_id):
                item = AuthorityPreemption.from_dict(document)
                if (
                    item.authority_lease_fingerprint == str(authority_lease_fingerprint)
                    and item.authority_epoch == int(authority_epoch)
                    and item.preemptor_principal_id == actor_principal_id
                    and item.preempted_at == float(at_time)
                    and item.reason_code == str(reason_code)
                ):
                    return {**deepcopy(row), "already_preempted": True, "effect_authority_granted": False}
                raise ValueError(f"authority lease already has a non-identical preemption: {lease_id}")

        lease_row = self.authority_lease_report(str(lease_id), at_time=float(at_time))
        lease = AuthorityLease.from_dict(lease_row["lease"])
        if not lease_row["active_at_time"]:
            raise PermissionError("authority preemption requires an active authority lease")
        if lease.fingerprint != str(authority_lease_fingerprint):
            raise PermissionError("authority preemption lease fingerprint is stale or mismatched")
        if lease.epoch != int(authority_epoch):
            raise PermissionError("authority preemption authority epoch is stale")
        domain_row = self.authority_domain_report(lease.domain_id)
        domain = AuthorityDomain.from_dict(domain_row["domain"])
        if actor_principal_id not in domain.preemptor_principal_ids:
            raise PermissionError("actor is not listed as an authority-domain preemptor")

        authorization = self._authorize_physical_authority_action(
            actor_principal_id=actor_principal_id,
            workspace_id=lease.workspace_id,
            scope_id=lease.scope_id,
            capability=PHYSICAL_CONTROL_FENCING_CAPABILITIES["preempt"],
            at_time=float(at_time),
            metadata={"lease_id": lease.lease_id, "domain_id": lease.domain_id, "authority_epoch": lease.epoch},
            derived_from=tuple(sorted(set((
                *map(str, evidence_ids),
                str(lease_row["evidence_id"]),
                str(domain_row["evidence_id"]),
            )))),
        )
        item = AuthorityPreemption(
            domain_id=lease.domain_id,
            authority_lease_id=lease.lease_id,
            authority_lease_fingerprint=lease.fingerprint,
            workspace_id=lease.workspace_id,
            scope_id=lease.scope_id,
            preemptor_principal_id=actor_principal_id,
            preempted_holder_principal_id=lease.holder_principal_id,
            authority_epoch=lease.epoch,
            required_next_epoch=lease.epoch + 1,
            preempted_at=float(at_time),
            reason_code=str(reason_code),
        )
        preemption_evidence_id = self._record_control_fencing_document(
            record_type=_AUTHORITY_PREEMPTION_RECORD,
            object_id=item.preemption_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=AUTHORITY_PREEMPTION_CONTRACT_ID,
            derived_from=tuple(sorted(set((
                *map(str, evidence_ids),
                str(lease_row["evidence_id"]),
                str(domain_row["evidence_id"]),
                str(authorization["evidence_id"]),
            )))),
            reason=reason,
        )

        # Use the canonical AuthorityLease revocation representation so all
        # existing lease/capability reports immediately observe preemption.
        revocation_document = {
            "contract_id": AUTHORITY_LEASE_CONTRACT_ID,
            "contract_version": lease.contract_version,
            "lease_id": lease.lease_id,
            "lease_fingerprint": lease.fingerprint,
            "domain_id": lease.domain_id,
            "epoch": lease.epoch,
            "revocation_generation": lease.revocation_generation + 1,
            "revoked_by_principal_id": actor_principal_id,
            "revoked_at": float(at_time),
            "reason": f"PREEMPTION:{reason_code}",
        }
        revocation_fingerprint = semantic_fingerprint(revocation_document)
        revocation_evidence_id = self._record_physical_authority_document(
            record_type=_AUTHORITY_LEASE_REVOCATION_RECORD,
            object_id=lease.lease_id,
            object_fingerprint=revocation_fingerprint,
            document=revocation_document,
            source=AUTHORITY_PREEMPTION_CONTRACT_ID,
            derived_from=tuple(sorted(set((
                str(preemption_evidence_id),
                str(authorization["evidence_id"]),
                str(lease_row["evidence_id"]),
            )))),
            reason=reason,
        )
        return {
            "preemption": item.to_dict(),
            "evidence_id": preemption_evidence_id,
            "lease_revocation_evidence_id": revocation_evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_preempted": False,
            "effect_authority_granted": False,
            "required_next_epoch": item.required_next_epoch,
        }

    def effect_capability_use_report(self, use_id: str) -> dict[str, Any]:
        report = self._require_valid_physical_control_fencing_projection()
        row = report["uses"].get(str(use_id))
        if row is None:
            raise KeyError(f"unknown effect capability use validation: {use_id}")
        return deepcopy(row)

    def authority_preemption_report(self, preemption_id: str) -> dict[str, Any]:
        report = self._require_valid_physical_control_fencing_projection()
        row = report["preemptions"].get(str(preemption_id))
        if row is None:
            raise KeyError(f"unknown authority preemption: {preemption_id}")
        return deepcopy(row)

    def physical_control_fencing_report(self) -> dict[str, Any]:
        report = self._require_valid_physical_control_fencing_projection()
        return {
            "runtime_contract": deepcopy(report["runtime_contract"]),
            "uses": deepcopy(report["uses"]),
            "preemptions": deepcopy(report["preemptions"]),
        }


__all__ = [
    "PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID",
    "PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_CONTROL_FENCING_RUNTIME_STABILITY",
    "PHYSICAL_CONTROL_FENCING_CAPABILITIES",
    "project_physical_control_fencing_evidence",
    "physical_control_fencing_runtime_contract",
    "PhysicalControlFencingRuntimeMixin",
]
