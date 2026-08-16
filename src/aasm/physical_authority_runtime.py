from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .physical_authority import (
    AUTHORITY_DOMAIN_CONTRACT_ID,
    AUTHORITY_LEASE_CONTRACT_ID,
    AuthorityDomain,
    AuthorityLease,
    physical_authority_contract,
)
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint


PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_ID = "aasm.physical.authority.runtime.v1"
PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_VERSION = "0.1.0"
PHYSICAL_AUTHORITY_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

PHYSICAL_AUTHORITY_CAPABILITIES = {
    "domain_register": "physical.authority.domain.register",
    "lease_grant": "physical.authority.lease.grant",
    "lease_revoke": "physical.authority.lease.revoke",
}

_PHYSICAL_AUTHORITY_RECORD_TYPE = "aasm_physical_authority_record_type"
_PHYSICAL_AUTHORITY_DOCUMENT = "document"
_AUTHORITY_DOMAIN_RECORD = "AUTHORITY_DOMAIN"
_AUTHORITY_LEASE_RECORD = "AUTHORITY_LEASE"
_AUTHORITY_LEASE_REVOCATION_RECORD = "AUTHORITY_LEASE_REVOCATION"


def physical_authority_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_ID,
        "contract_version": PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_VERSION,
        "stability": PHYSICAL_AUTHORITY_RUNTIME_STABILITY,
        "semantic_contract": physical_authority_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(PHYSICAL_AUTHORITY_CAPABILITIES),
        "lease_exclusivity": "NON_OVERLAPPING_EFFECTIVE_INTERVALS_PER_DOMAIN",
        "authority_epoch": "EXPLICIT_NEXT_MONOTONIC_EPOCH_REQUIRED",
        "revocation": "APPEND_ONLY_SCOPED_AUTHORITY_REQUIRED",
        "preemptor_reference_grants_authority": False,
        "domain_existence_grants_effect_authority": False,
        "lease_existence_grants_effect_authority": False,
        "effect_authorization_integration": "NONE_PR3A_PR3B_FOUNDATION",
        "effect_dispatch": "NONE",
        "machine_state_mutation": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_PHYSICAL_AUTHORITY_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("physical-authority Evidence is missing canonical document")


def project_physical_authority_evidence(records) -> dict[str, Any]:
    domains: dict[str, dict[str, Any]] = {}
    leases: dict[str, dict[str, Any]] = {}
    revocations: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []

    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_PHYSICAL_AUTHORITY_RECORD_TYPE)
        if record_type not in {
            _AUTHORITY_DOMAIN_RECORD,
            _AUTHORITY_LEASE_RECORD,
            _AUTHORITY_LEASE_REVOCATION_RECORD,
        }:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _AUTHORITY_DOMAIN_RECORD:
                item = AuthorityDomain.from_dict(document)
                object_id = item.domain_id
                fingerprint = item.fingerprint
                candidate = {"domain": item.to_dict(), "evidence_id": evidence_id}
                prior = domains.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"authority domain identity collision: {object_id}")
                domains[object_id] = candidate
            elif record_type == _AUTHORITY_LEASE_RECORD:
                item = AuthorityLease.from_dict(document)
                object_id = item.lease_id
                fingerprint = item.fingerprint
                candidate = {"lease": item.to_dict(), "evidence_id": evidence_id}
                prior = leases.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"authority lease identity collision: {object_id}")
                leases[object_id] = candidate
            else:
                object_id = str(document.get("lease_id") or "")
                if not object_id:
                    raise ValueError("authority lease revocation lease_id is required")
                if not str(document.get("lease_fingerprint") or ""):
                    raise ValueError("authority lease revocation lease_fingerprint is required")
                if int(document.get("revocation_generation", -1)) < 1:
                    raise ValueError("authority lease revocation_generation must be >= 1")
                fingerprint = semantic_fingerprint(document)
                candidate = {"revocation": document, "evidence_id": evidence_id}
                prior = revocations.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"authority lease has multiple non-identical revocations: {object_id}")
                revocations[object_id] = candidate

            if metadata.get("object_id") != object_id:
                raise ValueError(f"physical-authority metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"physical-authority metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for lease_id, row in leases.items():
        lease = AuthorityLease.from_dict(row["lease"])
        domain = domains.get(lease.domain_id)
        if domain is None:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _AUTHORITY_LEASE_RECORD,
                    "error": f"ValueError: authority lease references unknown domain: {lease.domain_id}",
                }
            )
            continue
        domain_item = AuthorityDomain.from_dict(domain["domain"])
        if lease.workspace_id != domain_item.workspace_id or lease.scope_id != domain_item.scope_id:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _AUTHORITY_LEASE_RECORD,
                    "error": f"ValueError: authority lease crosses domain workspace/scope: {lease_id}",
                }
            )
        if not set(lease.permitted_effect_classes).issubset(domain_item.permitted_effect_classes):
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _AUTHORITY_LEASE_RECORD,
                    "error": f"ValueError: authority lease amplifies domain effect classes: {lease_id}",
                }
            )
        if domain_item.problem_revision_id and lease.problem_revision_id != domain_item.problem_revision_id:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _AUTHORITY_LEASE_RECORD,
                    "error": f"ValueError: authority lease problem revision mismatch: {lease_id}",
                }
            )
        if domain_item.external_revision_id and lease.external_revision_id != domain_item.external_revision_id:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _AUTHORITY_LEASE_RECORD,
                    "error": f"ValueError: authority lease external revision mismatch: {lease_id}",
                }
            )

    for lease_id, row in revocations.items():
        lease = leases.get(lease_id)
        if lease is None:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _AUTHORITY_LEASE_REVOCATION_RECORD,
                    "error": f"ValueError: revocation references unknown authority lease: {lease_id}",
                }
            )
            continue
        if row["revocation"].get("lease_fingerprint") != lease["lease"]["fingerprint"]:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _AUTHORITY_LEASE_REVOCATION_RECORD,
                    "error": f"ValueError: authority lease revocation fingerprint mismatch: {lease_id}",
                }
            )

    return {
        "runtime_contract": physical_authority_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "domains": domains,
        "leases": leases,
        "revocations": revocations,
    }


def _effective_end(lease: AuthorityLease, revocation: Mapping[str, Any] | None) -> float:
    end = float(lease.expires_at)
    if revocation is not None:
        revoked_at = float(revocation.get("revoked_at", end))
        end = min(end, revoked_at)
    return end


def _intervals_overlap(left_start: float, left_end: float, right_start: float, right_end: float) -> bool:
    return max(float(left_start), float(right_start)) < min(float(left_end), float(right_end))


class PhysicalAuthorityRuntimeMixin:
    def physical_authority_contract_report(self) -> dict[str, Any]:
        return physical_authority_runtime_contract()

    def _physical_authority_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_physical_authority_evidence(records)

    def _require_valid_physical_authority_projection(self) -> dict[str, Any]:
        report = self._physical_authority_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable physical-authority projection: {report['issues']}")
        return report

    def _authorize_physical_authority_action(
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
            raise PermissionError("physical-authority mutation requires actor_principal_id")
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
            reason=f"physical-authority scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"physical-authority denied {capability}: {result['decision']['reason']}"
            )
        return result

    def _record_physical_authority_document(
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
        evidence_id = f"physical-authority-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_PHYSICAL_AUTHORITY_RECORD_TYPE) != record_type
                or metadata.get(_PHYSICAL_AUTHORITY_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"physical-authority Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="physical_authority",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=lineage,
            metadata={
                _PHYSICAL_AUTHORITY_RECORD_TYPE: record_type,
                _PHYSICAL_AUTHORITY_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "machine_state_mutation": "NONE",
                "effect_authority": "NONE_PR3A_PR3B_FOUNDATION",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(
            record,
            expected_machine_version=self.snapshot.version,
            reason=reason,
        )
        return evidence_id

    def register_authority_domain(
        self,
        domain: AuthorityDomain | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "authority domain registered",
    ) -> dict[str, Any]:
        item = domain if isinstance(domain, AuthorityDomain) else AuthorityDomain.from_dict(domain)
        principals, _, _ = self._workspace_authority_inputs(item.workspace_id)
        principal_ids = {row.principal_id for row in principals}
        unknown_preemptors = sorted(set(item.preemptor_principal_ids) - principal_ids)
        if unknown_preemptors:
            raise KeyError(f"unknown authority-domain preemptor principals: {unknown_preemptors}")
        authorization = self._authorize_physical_authority_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=PHYSICAL_AUTHORITY_CAPABILITIES["domain_register"],
            at_time=at_time,
            metadata={"domain_id": item.domain_id, "domain_name": item.domain_name, "subject_id": item.subject_id},
            derived_from=tuple(evidence_ids),
        )
        projection = self._require_valid_physical_authority_projection()
        prior = projection["domains"].get(item.domain_id)
        if prior is not None:
            if prior["domain"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"authority domain identity collision: {item.domain_id}")
            return {**deepcopy(prior), "already_registered": True}
        lineage = tuple(sorted(set((*map(str, evidence_ids), str(authorization["evidence_id"])))))
        evidence_id = self._record_physical_authority_document(
            record_type=_AUTHORITY_DOMAIN_RECORD,
            object_id=item.domain_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=AUTHORITY_DOMAIN_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "domain": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_registered": False,
            "effect_authority_granted": False,
        }

    def grant_authority_lease(
        self,
        lease: AuthorityLease | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float = 0.0,
        evidence_ids: Sequence[str] = (),
        reason: str = "authority lease granted",
    ) -> dict[str, Any]:
        item = lease if isinstance(lease, AuthorityLease) else AuthorityLease.from_dict(lease)
        if actor_principal_id != item.issuer_principal_id:
            raise PermissionError("authority lease actor must equal issuer_principal_id")
        projection = self._require_valid_physical_authority_projection()
        domain_row = projection["domains"].get(item.domain_id)
        if domain_row is None:
            raise KeyError(f"unknown authority domain: {item.domain_id}")
        domain = AuthorityDomain.from_dict(domain_row["domain"])
        if item.workspace_id != domain.workspace_id or item.scope_id != domain.scope_id:
            raise ValueError("authority lease workspace/scope must exactly match domain")
        if not set(item.permitted_effect_classes).issubset(domain.permitted_effect_classes):
            raise ValueError("authority lease permitted effect classes must be a subset of domain")
        if domain.problem_revision_id and item.problem_revision_id != domain.problem_revision_id:
            raise ValueError("authority lease problem revision must match domain")
        if domain.external_revision_id and item.external_revision_id != domain.external_revision_id:
            raise ValueError("authority lease external revision must match domain")

        principals, _, _ = self._workspace_authority_inputs(item.workspace_id)
        principal_ids = {row.principal_id for row in principals}
        if item.holder_principal_id not in principal_ids:
            raise KeyError(f"unknown authority-lease holder principal: {item.holder_principal_id}")
        if item.issuer_principal_id not in principal_ids:
            raise KeyError(f"unknown authority-lease issuer principal: {item.issuer_principal_id}")

        authorization = self._authorize_physical_authority_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=PHYSICAL_AUTHORITY_CAPABILITIES["lease_grant"],
            at_time=at_time,
            metadata={"lease_id": item.lease_id, "domain_id": item.domain_id, "epoch": item.epoch},
            derived_from=tuple(sorted(set((*map(str, evidence_ids), str(domain_row["evidence_id"]))))),
        )

        projection = self._require_valid_physical_authority_projection()
        prior = projection["leases"].get(item.lease_id)
        if prior is not None:
            if prior["lease"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"authority lease identity collision: {item.lease_id}")
            return {**deepcopy(prior), "already_granted": True, "effect_authority_granted": False}

        domain_leases = [
            AuthorityLease.from_dict(row["lease"])
            for row in projection["leases"].values()
            if row["lease"].get("domain_id") == item.domain_id
        ]
        max_epoch = max((lease_item.epoch for lease_item in domain_leases), default=0)
        expected_epoch = max_epoch + 1
        if item.epoch != expected_epoch:
            raise ValueError(
                f"authority lease epoch must be the next monotonic domain epoch: expected {expected_epoch}, got {item.epoch}"
            )

        for existing in domain_leases:
            revocation_row = projection["revocations"].get(existing.lease_id)
            revocation = None if revocation_row is None else revocation_row["revocation"]
            existing_end = _effective_end(existing, revocation)
            if _intervals_overlap(item.valid_from, item.expires_at, existing.valid_from, existing_end):
                raise ValueError(
                    f"authority lease interval overlaps existing domain lease: {existing.lease_id}"
                )

        lineage = tuple(
            sorted(
                set(
                    (
                        *map(str, evidence_ids),
                        str(domain_row["evidence_id"]),
                        str(authorization["evidence_id"]),
                    )
                )
            )
        )
        evidence_id = self._record_physical_authority_document(
            record_type=_AUTHORITY_LEASE_RECORD,
            object_id=item.lease_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            source=AUTHORITY_LEASE_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "lease": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_granted": False,
            "effect_authority_granted": False,
        }

    def revoke_authority_lease(
        self,
        lease_id: str,
        *,
        actor_principal_id: str,
        at_time: float,
        evidence_ids: Sequence[str] = (),
        reason: str = "authority lease revoked",
    ) -> dict[str, Any]:
        projection = self._require_valid_physical_authority_projection()
        lease_row = projection["leases"].get(str(lease_id))
        if lease_row is None:
            raise KeyError(f"unknown authority lease: {lease_id}")
        lease = AuthorityLease.from_dict(lease_row["lease"])
        prior = projection["revocations"].get(lease.lease_id)
        if prior is not None:
            return {**deepcopy(prior), "already_revoked": True, "effect_history_rewritten": False}
        authorization = self._authorize_physical_authority_action(
            actor_principal_id=actor_principal_id,
            workspace_id=lease.workspace_id,
            scope_id=lease.scope_id,
            capability=PHYSICAL_AUTHORITY_CAPABILITIES["lease_revoke"],
            at_time=at_time,
            metadata={"lease_id": lease.lease_id, "domain_id": lease.domain_id, "epoch": lease.epoch},
            derived_from=tuple(sorted(set((*map(str, evidence_ids), str(lease_row["evidence_id"]))))),
        )
        revoked_at = float(at_time)
        if revoked_at < lease.valid_from:
            raise ValueError("authority lease cannot be revoked before valid_from")
        document = {
            "contract_id": AUTHORITY_LEASE_CONTRACT_ID,
            "contract_version": lease.contract_version,
            "lease_id": lease.lease_id,
            "lease_fingerprint": lease.fingerprint,
            "domain_id": lease.domain_id,
            "epoch": lease.epoch,
            "revocation_generation": lease.revocation_generation + 1,
            "revoked_by_principal_id": actor_principal_id,
            "revoked_at": revoked_at,
            "reason": str(reason),
        }
        fingerprint = semantic_fingerprint(document)
        lineage = tuple(
            sorted(
                set(
                    (
                        *map(str, evidence_ids),
                        str(lease_row["evidence_id"]),
                        str(authorization["evidence_id"]),
                    )
                )
            )
        )
        evidence_id = self._record_physical_authority_document(
            record_type=_AUTHORITY_LEASE_REVOCATION_RECORD,
            object_id=lease.lease_id,
            object_fingerprint=fingerprint,
            document=document,
            source=AUTHORITY_LEASE_CONTRACT_ID,
            derived_from=lineage,
            reason=reason,
        )
        return {
            "revocation": document,
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_revoked": False,
            "effect_history_rewritten": False,
            "effect_authority_granted": False,
        }

    def authority_domain_report(self, domain_id: str) -> dict[str, Any]:
        report = self._require_valid_physical_authority_projection()
        row = report["domains"].get(str(domain_id))
        if row is None:
            raise KeyError(f"unknown authority domain: {domain_id}")
        return deepcopy(row)

    def authority_lease_report(self, lease_id: str, *, at_time: float = 0.0) -> dict[str, Any]:
        report = self._require_valid_physical_authority_projection()
        row = report["leases"].get(str(lease_id))
        if row is None:
            raise KeyError(f"unknown authority lease: {lease_id}")
        lease = AuthorityLease.from_dict(row["lease"])
        revocation_row = report["revocations"].get(lease.lease_id)
        revocation = None if revocation_row is None else revocation_row["revocation"]
        effective_end = _effective_end(lease, revocation)
        active = lease.valid_from <= float(at_time) < effective_end
        return {
            **deepcopy(row),
            "revocation": None if revocation_row is None else deepcopy(revocation_row),
            "active_at_time": bool(active),
            "effective_end": effective_end,
            "effect_authority_granted": False,
        }

    def physical_authority_report(self, *, at_time: float = 0.0) -> dict[str, Any]:
        report = self._require_valid_physical_authority_projection()
        leases: dict[str, dict[str, Any]] = {}
        for lease_id in sorted(report["leases"]):
            leases[lease_id] = self.authority_lease_report(lease_id, at_time=at_time)
        return {
            "runtime_contract": deepcopy(report["runtime_contract"]),
            "domains": deepcopy(report["domains"]),
            "leases": leases,
            "revocations": deepcopy(report["revocations"]),
        }


__all__ = [
    "PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_ID",
    "PHYSICAL_AUTHORITY_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_AUTHORITY_RUNTIME_STABILITY",
    "PHYSICAL_AUTHORITY_CAPABILITIES",
    "project_physical_authority_evidence",
    "physical_authority_runtime_contract",
    "PhysicalAuthorityRuntimeMixin",
]
