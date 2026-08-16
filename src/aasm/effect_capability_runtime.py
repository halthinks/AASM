from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Mapping, Sequence

from .effect_capability import (
    EFFECT_CAPABILITY_CONTRACT_ID,
    EffectCapability,
    effect_capability_contract,
    numeric_bounds_subset,
)
from .evidence import EvidenceRecord
from .physical_authority import AuthorityDomain, AuthorityLease
from .scoped_authority import AuthorityRequest
from .semantic_result import canonical_semantic_json, semantic_fingerprint


EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID = "aasm.effect.capability.runtime.v1"
EFFECT_CAPABILITY_RUNTIME_CONTRACT_VERSION = "0.1.0"
EFFECT_CAPABILITY_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

EFFECT_CAPABILITY_CAPABILITIES = {
    "issue": "physical.effect-capability.issue",
    "delegate": "physical.effect-capability.delegate",
    "revoke": "physical.effect-capability.revoke",
}

_EFFECT_CAPABILITY_RECORD_TYPE = "aasm_effect_capability_record_type"
_EFFECT_CAPABILITY_DOCUMENT = "document"
_EFFECT_CAPABILITY_RECORD = "EFFECT_CAPABILITY"
_EFFECT_CAPABILITY_REVOCATION_RECORD = "EFFECT_CAPABILITY_REVOCATION"


def effect_capability_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID,
        "contract_version": EFFECT_CAPABILITY_RUNTIME_CONTRACT_VERSION,
        "stability": EFFECT_CAPABILITY_RUNTIME_STABILITY,
        "semantic_contract": effect_capability_contract(),
        "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY",
        "capabilities": deepcopy(EFFECT_CAPABILITY_CAPABILITIES),
        "lease_source": "EXISTING_PR3A_PR3B_AUTHORITY_LEASE_ONLY",
        "root_issue": "ACTIVE_LEASE_HOLDER_PLUS_SCOPED_ISSUE_AUTHORITY_REQUIRED",
        "delegation": "ACTIVE_PARENT_HOLDER_PLUS_SCOPED_DELEGATE_AUTHORITY_REQUIRED",
        "non_amplification": "OPERATIONS_BOUNDS_VALIDITY_SCOPE_REVISION_EPOCH_AND_DEPTH_FAIL_CLOSED",
        "revocation": "APPEND_ONLY_GENERATION_INVALIDATES_CAPABILITY_AND_DESCENDANTS",
        "capability_existence_grants_effect_authority": False,
        "effect_authorization_integration": "NONE_PR3C_PR3D_FOUNDATION",
        "effect_dispatch": "NONE",
        "machine_state_mutation": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
    }


def _document(row: Mapping[str, Any]) -> dict[str, Any]:
    metadata = dict(row.get("metadata") or {})
    value = metadata.get(_EFFECT_CAPABILITY_DOCUMENT)
    if isinstance(value, Mapping):
        return deepcopy(dict(value))
    statement = row.get("statement")
    if isinstance(statement, str) and statement:
        parsed = json.loads(statement)
        if isinstance(parsed, Mapping):
            return deepcopy(dict(parsed))
    raise ValueError("effect-capability Evidence is missing canonical document")


def project_effect_capability_evidence(records) -> dict[str, Any]:
    capabilities: dict[str, dict[str, Any]] = {}
    revocations: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []

    for index, raw in enumerate(records):
        row = deepcopy(dict(raw))
        if row.get("status", "active") != "active":
            continue
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get(_EFFECT_CAPABILITY_RECORD_TYPE)
        if record_type not in {_EFFECT_CAPABILITY_RECORD, _EFFECT_CAPABILITY_REVOCATION_RECORD}:
            continue
        evidence_id = str(row.get("evidence_id") or "")
        try:
            document = _document(row)
            if record_type == _EFFECT_CAPABILITY_RECORD:
                item = EffectCapability.from_dict(document)
                object_id = item.capability_id
                fingerprint = item.fingerprint
                candidate = {"capability": item.to_dict(), "evidence_id": evidence_id}
                prior = capabilities.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"effect capability identity collision: {object_id}")
                capabilities[object_id] = candidate
            else:
                object_id = str(document.get("capability_id") or "")
                if not object_id:
                    raise ValueError("effect capability revocation capability_id is required")
                if not str(document.get("capability_fingerprint") or ""):
                    raise ValueError("effect capability revocation capability_fingerprint is required")
                if int(document.get("revocation_generation", -1)) < 1:
                    raise ValueError("effect capability revocation_generation must be >= 1")
                fingerprint = semantic_fingerprint(document)
                candidate = {"revocation": document, "evidence_id": evidence_id}
                prior = revocations.get(object_id)
                if prior is not None and prior != candidate:
                    raise ValueError(f"effect capability has multiple non-identical revocations: {object_id}")
                revocations[object_id] = candidate

            if metadata.get("object_id") != object_id:
                raise ValueError(f"effect-capability metadata object_id mismatch: {object_id}")
            if metadata.get("object_fingerprint") != fingerprint:
                raise ValueError(f"effect-capability metadata fingerprint mismatch: {object_id}")
        except Exception as exc:
            issues.append(
                {
                    "index": index,
                    "evidence_id": evidence_id,
                    "record_type": record_type,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    for capability_id, row in revocations.items():
        capability = capabilities.get(capability_id)
        if capability is None:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _EFFECT_CAPABILITY_REVOCATION_RECORD,
                    "error": f"ValueError: revocation references unknown effect capability: {capability_id}",
                }
            )
            continue
        if row["revocation"].get("capability_fingerprint") != capability["capability"]["fingerprint"]:
            issues.append(
                {
                    "index": -1,
                    "evidence_id": row["evidence_id"],
                    "record_type": _EFFECT_CAPABILITY_REVOCATION_RECORD,
                    "error": f"ValueError: effect capability revocation fingerprint mismatch: {capability_id}",
                }
            )

    return {
        "runtime_contract": effect_capability_runtime_contract(),
        "valid": not issues,
        "issues": issues,
        "capabilities": capabilities,
        "revocations": revocations,
    }


class EffectCapabilityRuntimeMixin:
    def effect_capability_contract_report(self) -> dict[str, Any]:
        return effect_capability_runtime_contract()

    def _effect_capability_projection(self) -> dict[str, Any]:
        records = self.snapshot.evidence.get("records", []) if isinstance(self.snapshot.evidence, dict) else []
        return project_effect_capability_evidence(records)

    def _require_valid_effect_capability_projection(self) -> dict[str, Any]:
        report = self._effect_capability_projection()
        if not report["valid"]:
            raise RuntimeError(f"invalid durable effect-capability projection: {report['issues']}")
        return report

    def _authorize_effect_capability_action(
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
            raise PermissionError("effect-capability mutation requires actor_principal_id")
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
            reason=f"effect-capability scoped authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(f"effect-capability denied {capability}: {result['decision']['reason']}")
        return result

    def _record_effect_capability_document(
        self,
        *,
        record_type: str,
        object_id: str,
        object_fingerprint: str,
        document: Mapping[str, Any],
        derived_from: Sequence[str],
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"effect-capability-evidence-{semantic_fingerprint(identity)[:24]}"
        lineage = self._require_evidence_ids(tuple(derived_from))
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if (
                metadata.get(_EFFECT_CAPABILITY_RECORD_TYPE) != record_type
                or metadata.get(_EFFECT_CAPABILITY_DOCUMENT) != payload
                or metadata.get("object_id") != object_id
                or metadata.get("object_fingerprint") != object_fingerprint
            ):
                raise ValueError(f"effect-capability Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="effect_capability",
            statement=canonical_semantic_json(payload),
            source=EFFECT_CAPABILITY_CONTRACT_ID,
            derived_from=lineage,
            metadata={
                _EFFECT_CAPABILITY_RECORD_TYPE: record_type,
                _EFFECT_CAPABILITY_DOCUMENT: payload,
                "object_id": object_id,
                "object_fingerprint": object_fingerprint,
                "machine_state_mutation": "NONE",
                "effect_authority": "NONE_PR3C_PR3D_FOUNDATION",
            },
            evidence_id=evidence_id,
        )
        self.add_evidence_guarded(record, expected_machine_version=self.snapshot.version, reason=reason)
        return evidence_id

    def _known_principal_ids(self, workspace_id: str) -> set[str]:
        principals, _, _ = self._workspace_authority_inputs(workspace_id)
        return {row.principal_id for row in principals}

    def _capability_revocation_generation(
        self,
        capability: EffectCapability,
        projection: Mapping[str, Any],
    ) -> int:
        row = projection["revocations"].get(capability.capability_id)
        if row is None:
            return capability.revocation_generation
        return int(row["revocation"]["revocation_generation"])

    def _validate_root_capability(
        self,
        item: EffectCapability,
        *,
        at_time: float,
    ) -> tuple[AuthorityDomain, AuthorityLease, dict[str, Any], dict[str, Any]]:
        if item.parent_capability_id or item.parent_capability_fingerprint:
            raise ValueError("root effect capability must not declare a parent capability")
        domain_row = self.authority_domain_report(item.domain_id)
        domain = AuthorityDomain.from_dict(domain_row["domain"])
        lease_row = self.authority_lease_report(item.authority_lease_id, at_time=at_time)
        lease = AuthorityLease.from_dict(lease_row["lease"])
        if lease.domain_id != domain.domain_id:
            raise ValueError("effect capability authority lease does not belong to domain")
        if not lease_row["active_at_time"]:
            raise ValueError("root effect capability requires an active authority lease")
        if item.issuer_principal_id != lease.holder_principal_id:
            raise PermissionError("root effect capability issuer must equal active authority-lease holder")
        if item.workspace_id != domain.workspace_id or item.scope_id != domain.scope_id:
            raise ValueError("effect capability workspace/scope must exactly match authority domain")
        if item.subject_id != domain.subject_id:
            raise ValueError("effect capability subject must exactly match authority domain")
        if item.authority_epoch != lease.epoch:
            raise ValueError("effect capability authority_epoch must exactly match active authority lease epoch")
        if item.valid_from < lease.valid_from or item.expires_at > float(lease_row["effective_end"]):
            raise ValueError("effect capability validity must be contained by active authority lease")
        if not set(item.allowed_operations).issubset(lease.permitted_effect_classes):
            raise ValueError("effect capability operations must be a subset of authority lease effect classes")
        if item.problem_revision_id != lease.problem_revision_id or item.problem_revision_id != domain.problem_revision_id:
            raise ValueError("effect capability problem revision must exactly match domain and authority lease")
        if item.external_revision_id != lease.external_revision_id or item.external_revision_id != domain.external_revision_id:
            raise ValueError("effect capability external revision must exactly match domain and authority lease")
        if item.revocation_generation != 0 or item.parent_revocation_generation != 0:
            raise ValueError("new root effect capability revocation generations must be zero")
        return domain, lease, domain_row, lease_row

    def issue_effect_capability(
        self,
        capability: EffectCapability | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float,
        evidence_ids: Sequence[str] = (),
        reason: str = "bounded effect capability issued",
    ) -> dict[str, Any]:
        item = capability if isinstance(capability, EffectCapability) else EffectCapability.from_dict(capability)
        domain, lease, domain_row, lease_row = self._validate_root_capability(item, at_time=at_time)
        if actor_principal_id != item.issuer_principal_id:
            raise PermissionError("effect capability actor must equal issuer_principal_id")
        principal_ids = self._known_principal_ids(item.workspace_id)
        if item.holder_principal_id not in principal_ids:
            raise KeyError(f"unknown effect-capability holder principal: {item.holder_principal_id}")
        authorization = self._authorize_effect_capability_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=EFFECT_CAPABILITY_CAPABILITIES["issue"],
            at_time=at_time,
            metadata={
                "capability_id": item.capability_id,
                "domain_id": domain.domain_id,
                "authority_lease_id": lease.lease_id,
                "authority_epoch": item.authority_epoch,
            },
            derived_from=tuple(
                sorted(
                    set(
                        (
                            *map(str, evidence_ids),
                            str(domain_row["evidence_id"]),
                            str(lease_row["evidence_id"]),
                        )
                    )
                )
            ),
        )
        projection = self._require_valid_effect_capability_projection()
        prior = projection["capabilities"].get(item.capability_id)
        if prior is not None:
            if prior["capability"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"effect capability identity collision: {item.capability_id}")
            return {**deepcopy(prior), "already_issued": True, "effect_authority_granted": False}
        lineage = tuple(
            sorted(
                set(
                    (
                        *map(str, evidence_ids),
                        str(domain_row["evidence_id"]),
                        str(lease_row["evidence_id"]),
                        str(authorization["evidence_id"]),
                    )
                )
            )
        )
        evidence_id = self._record_effect_capability_document(
            record_type=_EFFECT_CAPABILITY_RECORD,
            object_id=item.capability_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            derived_from=lineage,
            reason=reason,
        )
        return {
            "capability": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_issued": False,
            "effect_authority_granted": False,
        }

    def delegate_effect_capability(
        self,
        capability: EffectCapability | Mapping[str, Any],
        *,
        actor_principal_id: str,
        at_time: float,
        evidence_ids: Sequence[str] = (),
        reason: str = "bounded effect capability delegated",
    ) -> dict[str, Any]:
        item = capability if isinstance(capability, EffectCapability) else EffectCapability.from_dict(capability)
        if not item.parent_capability_id:
            raise ValueError("delegated effect capability requires parent capability identity")
        parent_row = self.effect_capability_report(item.parent_capability_id, at_time=at_time)
        parent = EffectCapability.from_dict(parent_row["capability"])
        if not parent_row["active_at_time"]:
            raise ValueError("delegated effect capability requires active parent capability")
        if item.parent_capability_fingerprint != parent.fingerprint:
            raise ValueError("delegated effect capability parent fingerprint mismatch")
        if item.parent_revocation_generation != int(parent_row["effective_revocation_generation"]):
            raise ValueError("delegated effect capability parent revocation generation is stale")
        if actor_principal_id != item.issuer_principal_id or item.issuer_principal_id != parent.holder_principal_id:
            raise PermissionError("delegated effect capability issuer must be active parent holder and actor")
        if parent.remaining_delegation_depth < 1:
            raise PermissionError("parent effect capability has no remaining delegation depth")
        if item.remaining_delegation_depth > parent.remaining_delegation_depth - 1:
            raise ValueError("delegated effect capability must decrease remaining delegation depth")
        for name in (
            "domain_id",
            "authority_lease_id",
            "workspace_id",
            "scope_id",
            "subject_id",
            "authority_epoch",
            "problem_revision_id",
            "external_revision_id",
        ):
            if getattr(item, name) != getattr(parent, name):
                raise ValueError(f"delegated effect capability {name} must exactly match parent")
        if not set(item.allowed_operations).issubset(parent.allowed_operations):
            raise ValueError("delegated effect capability operations must be a subset of parent")
        if not numeric_bounds_subset(item.numeric_bounds, parent.numeric_bounds):
            raise ValueError("delegated effect capability numeric bounds must preserve or narrow every parent bound")
        if item.valid_from < parent.valid_from or item.expires_at > parent.expires_at:
            raise ValueError("delegated effect capability validity must be contained by parent")
        if item.revocation_generation != 0:
            raise ValueError("new delegated effect capability revocation_generation must be zero")
        if item.holder_principal_id not in self._known_principal_ids(item.workspace_id):
            raise KeyError(f"unknown effect-capability holder principal: {item.holder_principal_id}")

        authorization = self._authorize_effect_capability_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=EFFECT_CAPABILITY_CAPABILITIES["delegate"],
            at_time=at_time,
            metadata={
                "capability_id": item.capability_id,
                "parent_capability_id": parent.capability_id,
                "authority_epoch": item.authority_epoch,
            },
            derived_from=tuple(sorted(set((*map(str, evidence_ids), str(parent_row["evidence_id"]))))),
        )
        projection = self._require_valid_effect_capability_projection()
        prior = projection["capabilities"].get(item.capability_id)
        if prior is not None:
            if prior["capability"]["fingerprint"] != item.fingerprint:
                raise ValueError(f"effect capability identity collision: {item.capability_id}")
            return {**deepcopy(prior), "already_issued": True, "effect_authority_granted": False}
        lineage = tuple(
            sorted(
                set(
                    (
                        *map(str, evidence_ids),
                        str(parent_row["evidence_id"]),
                        str(authorization["evidence_id"]),
                    )
                )
            )
        )
        evidence_id = self._record_effect_capability_document(
            record_type=_EFFECT_CAPABILITY_RECORD,
            object_id=item.capability_id,
            object_fingerprint=item.fingerprint,
            document=item.to_dict(),
            derived_from=lineage,
            reason=reason,
        )
        return {
            "capability": item.to_dict(),
            "evidence_id": evidence_id,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "already_issued": False,
            "effect_authority_granted": False,
        }

    def revoke_effect_capability(
        self,
        capability_id: str,
        *,
        actor_principal_id: str,
        at_time: float,
        evidence_ids: Sequence[str] = (),
        reason: str = "bounded effect capability revoked",
    ) -> dict[str, Any]:
        projection = self._require_valid_effect_capability_projection()
        row = projection["capabilities"].get(str(capability_id))
        if row is None:
            raise KeyError(f"unknown effect capability: {capability_id}")
        item = EffectCapability.from_dict(row["capability"])
        prior = projection["revocations"].get(item.capability_id)
        if prior is not None:
            return {**deepcopy(prior), "already_revoked": True, "effect_history_rewritten": False}
        if actor_principal_id not in {item.issuer_principal_id, item.holder_principal_id}:
            # A different principal may still hold explicit scoped revoke authority,
            # so identity alone is not used as an implicit grant.
            pass
        authorization = self._authorize_effect_capability_action(
            actor_principal_id=actor_principal_id,
            workspace_id=item.workspace_id,
            scope_id=item.scope_id,
            capability=EFFECT_CAPABILITY_CAPABILITIES["revoke"],
            at_time=at_time,
            metadata={"capability_id": item.capability_id, "authority_epoch": item.authority_epoch},
            derived_from=tuple(sorted(set((*map(str, evidence_ids), str(row["evidence_id"]))))),
        )
        document = {
            "contract_id": EFFECT_CAPABILITY_CONTRACT_ID,
            "contract_version": item.contract_version,
            "capability_id": item.capability_id,
            "capability_fingerprint": item.fingerprint,
            "domain_id": item.domain_id,
            "authority_lease_id": item.authority_lease_id,
            "authority_epoch": item.authority_epoch,
            "revocation_generation": item.revocation_generation + 1,
            "revoked_by_principal_id": actor_principal_id,
            "revoked_at": float(at_time),
            "reason": str(reason),
        }
        fingerprint = semantic_fingerprint(document)
        lineage = tuple(
            sorted(
                set(
                    (
                        *map(str, evidence_ids),
                        str(row["evidence_id"]),
                        str(authorization["evidence_id"]),
                    )
                )
            )
        )
        evidence_id = self._record_effect_capability_document(
            record_type=_EFFECT_CAPABILITY_REVOCATION_RECORD,
            object_id=item.capability_id,
            object_fingerprint=fingerprint,
            document=document,
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

    def effect_capability_report(
        self,
        capability_id: str,
        *,
        at_time: float,
        _seen: frozenset[str] = frozenset(),
    ) -> dict[str, Any]:
        projection = self._require_valid_effect_capability_projection()
        row = projection["capabilities"].get(str(capability_id))
        if row is None:
            raise KeyError(f"unknown effect capability: {capability_id}")
        item = EffectCapability.from_dict(row["capability"])
        if item.capability_id in _seen:
            raise RuntimeError(f"effect capability parent cycle detected: {item.capability_id}")
        revocation_row = projection["revocations"].get(item.capability_id)
        effective_generation = self._capability_revocation_generation(item, projection)
        own_revoked = False
        revoked_at = None
        if revocation_row is not None:
            revoked_at = float(revocation_row["revocation"]["revoked_at"])
            own_revoked = float(at_time) >= revoked_at

        lease_row = self.authority_lease_report(item.authority_lease_id, at_time=at_time)
        lease = AuthorityLease.from_dict(lease_row["lease"])
        lease_valid = (
            lease.domain_id == item.domain_id
            and lease.epoch == item.authority_epoch
            and lease_row["active_at_time"]
        )
        own_interval_active = item.active_at(at_time)

        parent_active = True
        parent_current_generation = 0
        parent_row = None
        if item.parent_capability_id:
            parent_row = self.effect_capability_report(
                item.parent_capability_id,
                at_time=at_time,
                _seen=frozenset((*_seen, item.capability_id)),
            )
            parent_current_generation = int(parent_row["effective_revocation_generation"])
            parent_active = (
                parent_row["active_at_time"]
                and item.parent_capability_fingerprint == parent_row["capability"]["fingerprint"]
                and item.parent_revocation_generation == parent_current_generation
            )

        active = bool(own_interval_active and not own_revoked and lease_valid and parent_active)
        return {
            **deepcopy(row),
            "revocation": None if revocation_row is None else deepcopy(revocation_row),
            "effective_revocation_generation": effective_generation,
            "parent_effective_revocation_generation": parent_current_generation,
            "lease_active_at_time": bool(lease_valid),
            "parent_active_at_time": bool(parent_active),
            "active_at_time": active,
            "revoked_at": revoked_at,
            "effect_authority_granted": False,
        }

    def effect_capabilities_report(self, *, at_time: float) -> dict[str, Any]:
        projection = self._require_valid_effect_capability_projection()
        capabilities: dict[str, dict[str, Any]] = {}
        for capability_id in sorted(projection["capabilities"]):
            capabilities[capability_id] = self.effect_capability_report(capability_id, at_time=at_time)
        return {
            "runtime_contract": deepcopy(projection["runtime_contract"]),
            "capabilities": capabilities,
            "revocations": deepcopy(projection["revocations"]),
        }


__all__ = [
    "EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID",
    "EFFECT_CAPABILITY_RUNTIME_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_RUNTIME_STABILITY",
    "EFFECT_CAPABILITY_CAPABILITIES",
    "project_effect_capability_evidence",
    "effect_capability_runtime_contract",
    "EffectCapabilityRuntimeMixin",
]
