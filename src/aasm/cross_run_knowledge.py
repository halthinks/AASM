from __future__ import annotations

"""Cross-run certified knowledge contracts for AASM v0.48.

Foreign knowledge is immutable provenance plus evidence. It never imports source
run authority. The receiving run must validate applicability and independently
admit the envelope before it can be materialized into local governed memory or
registered as a reuse candidate.
"""

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import canonical_semantic_json, semantic_fingerprint


CROSS_RUN_KNOWLEDGE_CONTRACT_ID = "aasm.knowledge.cross-run.v1"
CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION = "0.1.0"
CROSS_RUN_ADMISSION_CONTRACT_ID = "aasm.knowledge.cross-run.admission.v1"
CROSS_RUN_ADMISSION_CONTRACT_VERSION = "0.1.0"
CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID = "aasm.principal.cross-run-map.v1"
CROSS_RUN_PRINCIPAL_MAP_CONTRACT_VERSION = "0.1.0"
CROSS_RUN_KNOWLEDGE_KINDS = (
    "SEMANTIC",
    "PROCEDURAL",
    "OBSERVATION",
    "REUSE_RESULT",
    "SII_REPUTATION",
    "SUMMARY",
)
CROSS_RUN_SIGNAL_ACTIONS = ("REVOKE", "SUPERSEDE")
CROSS_RUN_PRIVACY_LEVELS = ("AGENT", "USER", "SHARED", "PUBLIC")
_STRENGTH = {
    "": 0,
    None: 0,
    "SOLVER_VERDICT": 1,
    "MULTI_SOLVER_AGREEMENT": 2,
    "CHECKED_CERTIFICATE": 3,
    "TRUSTED_KERNEL": 4,
}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"cross-run value is not JSON serializable: {type(value)!r}")


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


@dataclass(frozen=True)
class CrossRunKnowledgeEnvelope:
    source_run_id: str
    source_machine_id: str
    source_scope_id: str
    knowledge_kind: str
    content: Any
    source_memory_ids: tuple[str, ...] = ()
    source_evidence_ids: tuple[str, ...] = ()
    source_artifact_ids: tuple[str, ...] = ()
    source_fingerprints: dict[str, str] = field(default_factory=dict)
    source_authority_provenance: dict[str, Any] = field(default_factory=dict)
    applicability_scope_ids: tuple[str, ...] = ("root",)
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    verification_strength: str = ""
    privacy_level: str = "PUBLIC"
    privacy_principal_id: str = ""
    retention_policy: str = "permanent"
    freshness_seconds: float | None = None
    created_at: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    envelope_id: str = ""

    def __post_init__(self):
        if not self.source_run_id or not self.source_machine_id or not self.source_scope_id:
            raise ValueError("cross-run envelope requires source run/machine/scope identity")
        if self.knowledge_kind not in CROSS_RUN_KNOWLEDGE_KINDS:
            raise ValueError(f"invalid cross-run knowledge kind: {self.knowledge_kind}")
        if self.privacy_level not in CROSS_RUN_PRIVACY_LEVELS:
            raise ValueError(f"invalid cross-run privacy level: {self.privacy_level}")
        if self.privacy_level in {"AGENT", "USER"} and not self.privacy_principal_id:
            raise ValueError("private cross-run knowledge requires privacy_principal_id")
        if self.verification_strength not in _STRENGTH:
            raise ValueError(f"unknown verification strength: {self.verification_strength}")
        if self.freshness_seconds is not None and float(self.freshness_seconds) < 0:
            raise ValueError("cross-run freshness_seconds must be non-negative")
        if self.retention_policy not in {"permanent", "forgettable"} and not self.retention_policy.startswith("ttl:"):
            raise ValueError("cross-run retention_policy must be permanent, forgettable, or ttl:<seconds>")
        if self.retention_policy.startswith("ttl:"):
            try:
                seconds = int(self.retention_policy.split(":", 1)[1])
            except Exception as exc:
                raise ValueError("cross-run ttl retention must be ttl:<positive-seconds>") from exc
            if seconds <= 0:
                raise ValueError("cross-run ttl retention must be positive")
        object.__setattr__(self, "source_memory_ids", _uniq(self.source_memory_ids))
        object.__setattr__(self, "source_evidence_ids", _uniq(self.source_evidence_ids))
        object.__setattr__(self, "source_artifact_ids", _uniq(self.source_artifact_ids))
        object.__setattr__(self, "applicability_scope_ids", _uniq(self.applicability_scope_ids))
        object.__setattr__(self, "dependency_fingerprints", _uniq(self.dependency_fingerprints))
        if not self.applicability_scope_ids:
            raise ValueError("cross-run knowledge requires at least one applicable receiving scope")
        _jsonable(self.content)
        _jsonable(self.source_authority_provenance)
        _jsonable(self.metadata)
        if not self.envelope_id:
            object.__setattr__(self, "envelope_id", f"cross-run-envelope-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source_run_id": self.source_run_id,
            "source_machine_id": self.source_machine_id,
            "source_scope_id": self.source_scope_id,
            "knowledge_kind": self.knowledge_kind,
            "content": _jsonable(self.content),
            "source_memory_ids": list(self.source_memory_ids),
            "source_evidence_ids": list(self.source_evidence_ids),
            "source_artifact_ids": list(self.source_artifact_ids),
            "source_fingerprints": {str(k): str(v) for k, v in sorted(self.source_fingerprints.items())},
            "source_authority_provenance": _jsonable(self.source_authority_provenance),
            "applicability_scope_ids": list(self.applicability_scope_ids),
            "environment_fingerprint": self.environment_fingerprint,
            "dependency_fingerprints": list(self.dependency_fingerprints),
            "verification_strength": self.verification_strength,
            "privacy_level": self.privacy_level,
            "privacy_principal_id": self.privacy_principal_id,
            "retention_policy": self.retention_policy,
            "freshness_seconds": self.freshness_seconds,
            "created_at": float(self.created_at),
            "metadata": _jsonable(self.metadata),
            "authority_transfer": "NEVER",
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"envelope_id": self.envelope_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"envelope_id": self.envelope_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CrossRunKnowledgeEnvelope":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload.pop("authority_transfer", None)
        for key in ("source_memory_ids", "source_evidence_ids", "source_artifact_ids", "applicability_scope_ids", "dependency_fingerprints"):
            payload[key] = tuple(payload.get(key) or ())
        return cls(**payload)


@dataclass(frozen=True)
class CrossRunKnowledgeSignal:
    source_run_id: str
    envelope_id: str
    envelope_fingerprint: str
    action: str
    reason: str
    superseded_by_envelope_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    signal_id: str = ""

    def __post_init__(self):
        if not self.source_run_id or not self.envelope_id or not self.envelope_fingerprint or not self.reason.strip():
            raise ValueError("cross-run signal requires source/envelope identity and reason")
        if self.action not in CROSS_RUN_SIGNAL_ACTIONS:
            raise ValueError(f"invalid cross-run signal action: {self.action}")
        if self.action == "SUPERSEDE" and not self.superseded_by_envelope_id:
            raise ValueError("SUPERSEDE signal requires superseded_by_envelope_id")
        _jsonable(self.metadata)
        if not self.signal_id:
            object.__setattr__(self, "signal_id", f"cross-run-signal-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source_run_id": self.source_run_id,
            "envelope_id": self.envelope_id,
            "envelope_fingerprint": self.envelope_fingerprint,
            "action": self.action,
            "reason": self.reason,
            "superseded_by_envelope_id": self.superseded_by_envelope_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"signal_id": self.signal_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"signal_id": self.signal_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CrossRunKnowledgeSignal":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class CrossRunKnowledgeBundle:
    source_run_id: str
    envelopes: tuple[CrossRunKnowledgeEnvelope | Mapping[str, Any], ...] = ()
    signals: tuple[CrossRunKnowledgeSignal | Mapping[str, Any], ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    bundle_id: str = ""

    def __post_init__(self):
        if not self.source_run_id:
            raise ValueError("cross-run bundle requires source_run_id")
        envelopes = tuple(row if isinstance(row, CrossRunKnowledgeEnvelope) else CrossRunKnowledgeEnvelope.from_dict(row) for row in self.envelopes)
        signals = tuple(row if isinstance(row, CrossRunKnowledgeSignal) else CrossRunKnowledgeSignal.from_dict(row) for row in self.signals)
        if any(row.source_run_id != self.source_run_id for row in envelopes):
            raise ValueError("bundle envelope source_run_id mismatch")
        if any(row.source_run_id != self.source_run_id for row in signals):
            raise ValueError("bundle signal source_run_id mismatch")
        if len({row.envelope_id for row in envelopes}) != len(envelopes):
            raise ValueError("duplicate cross-run envelope ID in bundle")
        object.__setattr__(self, "envelopes", tuple(sorted(envelopes, key=lambda row: row.envelope_id)))
        object.__setattr__(self, "signals", tuple(sorted(signals, key=lambda row: row.signal_id)))
        _jsonable(self.metadata)
        if not self.bundle_id:
            object.__setattr__(self, "bundle_id", f"cross-run-bundle-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source_run_id": self.source_run_id,
            "envelopes": [row.to_dict() for row in self.envelopes],
            "signals": [row.to_dict() for row in self.signals],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"bundle_id": self.bundle_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"bundle_id": self.bundle_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CrossRunKnowledgeBundle":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["envelopes"] = tuple(payload.get("envelopes") or ())
        payload["signals"] = tuple(payload.get("signals") or ())
        return cls(**payload)


@dataclass(frozen=True)
class CrossRunAdmissionContext:
    receiving_run_id: str
    target_scope_id: str
    privacy_principal_id: str = ""
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    required_strength: str = ""
    as_of: float = 0.0
    validator_id: str = "aasm.cross-run.validator"
    validator_version: str = "0.1.0"

    def __post_init__(self):
        if not self.receiving_run_id or not self.target_scope_id or not self.validator_id or not self.validator_version:
            raise ValueError("cross-run admission context identity fields are required")
        if self.required_strength not in _STRENGTH:
            raise ValueError(f"unknown required verification strength: {self.required_strength}")
        object.__setattr__(self, "dependency_fingerprints", _uniq(self.dependency_fingerprints))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "dependency_fingerprints": list(self.dependency_fingerprints)}


@dataclass(frozen=True)
class CrossRunAdmissionCertificate:
    envelope_id: str
    envelope_fingerprint: str
    receiving_run_id: str
    target_scope_id: str
    validator_id: str
    validator_version: str
    checks: dict[str, bool]
    reasons: tuple[str, ...] = ()
    valid: bool = False
    certificate_id: str = ""

    def __post_init__(self):
        if not all((self.envelope_id, self.envelope_fingerprint, self.receiving_run_id, self.target_scope_id, self.validator_id, self.validator_version)):
            raise ValueError("cross-run admission certificate identity fields are required")
        object.__setattr__(self, "reasons", tuple(map(str, self.reasons)))
        if bool(self.valid) != all(bool(value) for value in self.checks.values()):
            raise ValueError("cross-run admission certificate validity must equal all checks")
        if not self.certificate_id:
            object.__setattr__(self, "certificate_id", f"cross-run-admission-cert-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "envelope_fingerprint": self.envelope_fingerprint,
            "receiving_run_id": self.receiving_run_id,
            "target_scope_id": self.target_scope_id,
            "validator_id": self.validator_id,
            "validator_version": self.validator_version,
            "checks": {str(k): bool(v) for k, v in sorted(self.checks.items())},
            "reasons": list(self.reasons),
            "valid": bool(self.valid),
            "authority_inherited": False,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"certificate_id": self.certificate_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"certificate_id": self.certificate_id, **self.identity_payload(), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class CrossRunPrincipalMap:
    source_run_id: str
    source_principal_id: str
    local_principal_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    mapping_id: str = ""

    def __post_init__(self):
        if not self.source_run_id or not self.source_principal_id or not self.local_principal_id:
            raise ValueError("cross-run principal map requires source/local identity")
        _jsonable(self.metadata)
        if not self.mapping_id:
            object.__setattr__(self, "mapping_id", f"cross-run-principal-map-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source_run_id": self.source_run_id,
            "source_principal_id": self.source_principal_id,
            "local_principal_id": self.local_principal_id,
            "metadata": _jsonable(self.metadata),
            "authority_transfer": "NEVER",
            "resource_entitlement_transfer": "NEVER",
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"mapping_id": self.mapping_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"mapping_id": self.mapping_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CrossRunPrincipalMap":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); payload.pop("authority_transfer", None); payload.pop("resource_entitlement_transfer", None); return cls(**payload)


def validate_cross_run_envelope(envelope: CrossRunKnowledgeEnvelope | Mapping[str, Any], context: CrossRunAdmissionContext | Mapping[str, Any]) -> CrossRunAdmissionCertificate:
    envelope = envelope if isinstance(envelope, CrossRunKnowledgeEnvelope) else CrossRunKnowledgeEnvelope.from_dict(envelope)
    context = context if isinstance(context, CrossRunAdmissionContext) else CrossRunAdmissionContext(**deepcopy(dict(context)))
    dependencies = set(context.dependency_fingerprints)
    now = float(context.as_of)
    retention_expired = False
    if envelope.retention_policy.startswith("ttl:"):
        retention_expired = now > float(envelope.created_at) + int(envelope.retention_policy.split(":", 1)[1])
    freshness_expired = envelope.freshness_seconds is not None and now > float(envelope.created_at) + float(envelope.freshness_seconds)
    privacy_ok = envelope.privacy_level not in {"AGENT", "USER"} or envelope.privacy_principal_id == context.privacy_principal_id
    environment_ok = not envelope.environment_fingerprint or envelope.environment_fingerprint == context.environment_fingerprint
    dependency_ok = set(envelope.dependency_fingerprints).issubset(dependencies)
    strength_ok = _STRENGTH.get(envelope.verification_strength, 0) >= _STRENGTH.get(context.required_strength, 0)
    checks = {
        "foreign_source_run": envelope.source_run_id != context.receiving_run_id,
        "scope_applicable": context.target_scope_id in envelope.applicability_scope_ids,
        "privacy_compatible": privacy_ok,
        "environment_compatible": environment_ok,
        "dependencies_available": dependency_ok,
        "fresh": not freshness_expired,
        "retention_active": not retention_expired,
        "verification_strength_sufficient": strength_ok,
        "source_authority_not_inherited": True,
    }
    reasons = tuple(name for name, passed in checks.items() if not passed)
    return CrossRunAdmissionCertificate(
        envelope_id=envelope.envelope_id,
        envelope_fingerprint=envelope.fingerprint,
        receiving_run_id=context.receiving_run_id,
        target_scope_id=context.target_scope_id,
        validator_id=context.validator_id,
        validator_version=context.validator_version,
        checks=checks,
        reasons=reasons,
        valid=not reasons,
    )


def cross_run_knowledge_contract() -> dict[str, Any]:
    return {
        "contract_id": CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
        "contract_version": CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION,
        "admission_contract_id": CROSS_RUN_ADMISSION_CONTRACT_ID,
        "admission_contract_version": CROSS_RUN_ADMISSION_CONTRACT_VERSION,
        "principal_map_contract_id": CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID,
        "principal_map_contract_version": CROSS_RUN_PRINCIPAL_MAP_CONTRACT_VERSION,
        "knowledge_kinds": list(CROSS_RUN_KNOWLEDGE_KINDS),
        "source_authority": "PROVENANCE_ONLY_NEVER_INHERITED",
        "receiving_admission": "POLICY_OR_CONTROLLER_REQUIRED",
        "semantic_materialization": "LOCAL_AUTHORIZED_REASONING_REQUIRED",
        "reuse": "EXISTING_V41_REUSE_CERTIFICATE_REQUIRED",
        "revocation": "SOURCE_SIGNAL_PLUS_RECEIVING_ADMISSION",
        "privacy": "EXPLICIT_PRINCIPAL_AND_SCOPE_COMPATIBILITY",
        "freshness": "EXPLICIT_RECEIVING_RUN_CHECK",
        "environment": "EXACT_WHEN_DECLARED",
        "dependencies": "DECLARED_FINGERPRINTS_REQUIRED",
        "sii_reputation": "ACCOUNTING_ONLY_NEVER_AUTHORITY_OR_RESOURCE_ENTITLEMENT",
        "transport_authentication": "EXTERNAL_OR_SIGNED_PROVENANCE_REQUIRED_FOR_UNTRUSTED_TRANSPORT",
    }


def cross_run_document(value: Any) -> str:
    return canonical_semantic_json(value.to_dict() if hasattr(value, "to_dict") else value)


__all__ = [
    "CROSS_RUN_KNOWLEDGE_CONTRACT_ID",
    "CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION",
    "CROSS_RUN_ADMISSION_CONTRACT_ID",
    "CROSS_RUN_ADMISSION_CONTRACT_VERSION",
    "CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID",
    "CROSS_RUN_PRINCIPAL_MAP_CONTRACT_VERSION",
    "CROSS_RUN_KNOWLEDGE_KINDS",
    "CrossRunKnowledgeEnvelope",
    "CrossRunKnowledgeSignal",
    "CrossRunKnowledgeBundle",
    "CrossRunAdmissionContext",
    "CrossRunAdmissionCertificate",
    "CrossRunPrincipalMap",
    "validate_cross_run_envelope",
    "cross_run_knowledge_contract",
    "cross_run_document",
]
