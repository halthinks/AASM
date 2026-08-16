from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .event_causality import PORTABLE_U63_MAX
from .semantic_result import semantic_fingerprint


SOURCE_TRUST_CONTRACT_ID = "aasm.source.trust.v1"
SOURCE_TRUST_CONTRACT_VERSION = "0.1.0"
SOURCE_TRUST_STABILITY = "FOUNDATION_EXPERIMENTAL"

SOURCE_KINDS = (
    "SENSOR",
    "DEVICE",
    "TOOL",
    "PROJECT_ENGINE",
    "MODEL",
    "IMPORT",
    "HUMAN",
)
SOURCE_TRUST_DISPOSITIONS = (
    "TRUSTED",
    "CONDITIONAL",
    "UNTRUSTED",
)


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _portable_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    parsed = int(value)
    if parsed < 0 or parsed > PORTABLE_U63_MAX:
        raise ValueError(f"{name} must be between 0 and {PORTABLE_U63_MAX}")
    return parsed


def _optional_portable_int(value: int | None, name: str) -> int | None:
    return None if value is None else _portable_int(value, name)


def _unique_strings(values: Sequence[str], name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    result = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
    if not result and not allow_empty:
        raise ValueError(f"{name} requires at least one value")
    return result


def _fingerprint_map(value: Mapping[str, str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, fingerprint in sorted(value.items(), key=lambda pair: str(pair[0])):
        calibration_id = str(key).strip()
        calibration_fingerprint = str(fingerprint).strip()
        if not calibration_id or not calibration_fingerprint:
            raise ValueError("required_calibrations must map non-empty calibration IDs to non-empty fingerprints")
        result[calibration_id] = calibration_fingerprint
    return result


@dataclass(frozen=True)
class SourceTrustAssertion:
    workspace_id: str
    scope_id: str
    subject_id: str
    source_principal_id: str
    source_kind: str
    trust_disposition: str
    state_namespaces: tuple[str, ...]
    valid_from_ns: int
    expires_at_ns: int | None = None
    physical_identity_id: str = ""
    physical_identity_fingerprint: str = ""
    required_calibrations: Mapping[str, str] = field(default_factory=dict)
    policy_basis_ids: tuple[str, ...] = ()
    problem_revision_id: str = ""
    external_revision_id: str = ""
    trust_id: str = ""
    contract_id: str = SOURCE_TRUST_CONTRACT_ID
    contract_version: str = SOURCE_TRUST_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("workspace_id", "scope_id", "subject_id", "source_principal_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.source_kind not in SOURCE_KINDS:
            raise ValueError(f"invalid source kind: {self.source_kind}")
        if self.trust_disposition not in SOURCE_TRUST_DISPOSITIONS:
            raise ValueError(f"invalid source trust disposition: {self.trust_disposition}")
        if self.contract_id != SOURCE_TRUST_CONTRACT_ID or self.contract_version != SOURCE_TRUST_CONTRACT_VERSION:
            raise ValueError("unsupported source-trust contract")
        object.__setattr__(self, "state_namespaces", _unique_strings(self.state_namespaces, "state_namespaces"))
        valid_from = _portable_int(self.valid_from_ns, "valid_from_ns")
        expires_at = _optional_portable_int(self.expires_at_ns, "expires_at_ns")
        if expires_at is not None and expires_at <= valid_from:
            raise ValueError("expires_at_ns must be greater than valid_from_ns")
        object.__setattr__(self, "valid_from_ns", valid_from)
        object.__setattr__(self, "expires_at_ns", expires_at)
        identity_id = _optional(self.physical_identity_id)
        identity_fingerprint = _optional(self.physical_identity_fingerprint)
        if bool(identity_id) != bool(identity_fingerprint):
            raise ValueError("physical identity ID and fingerprint must be supplied together")
        object.__setattr__(self, "physical_identity_id", identity_id)
        object.__setattr__(self, "physical_identity_fingerprint", identity_fingerprint)
        calibrations = _fingerprint_map(dict(self.required_calibrations))
        if calibrations and not identity_id:
            raise ValueError("required calibrations require an exact physical identity binding")
        object.__setattr__(self, "required_calibrations", calibrations)
        object.__setattr__(self, "policy_basis_ids", _unique_strings(self.policy_basis_ids, "policy_basis_ids", allow_empty=True))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        if not self.trust_id:
            object.__setattr__(self, "trust_id", f"source-trust-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "trust_id", _required(self.trust_id, "trust_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "source_principal_id": self.source_principal_id,
            "source_kind": self.source_kind,
            "trust_disposition": self.trust_disposition,
            "state_namespaces": list(self.state_namespaces),
            "valid_from_ns": self.valid_from_ns,
            "expires_at_ns": self.expires_at_ns,
            "physical_identity_id": self.physical_identity_id,
            "physical_identity_fingerprint": self.physical_identity_fingerprint,
            "required_calibrations": dict(self.required_calibrations),
            "policy_basis_ids": list(self.policy_basis_ids),
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"trust_id": self.trust_id, **self.identity_payload()})

    def active_at(self, reference_time_ns: int, revoked_at_ns: int | None = None) -> bool:
        moment = _portable_int(reference_time_ns, "reference_time_ns")
        if moment < self.valid_from_ns:
            return False
        if self.expires_at_ns is not None and moment >= self.expires_at_ns:
            return False
        if revoked_at_ns is not None and moment >= _portable_int(revoked_at_ns, "revoked_at_ns"):
            return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"trust_id": self.trust_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceTrustAssertion":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["state_namespaces"] = tuple(payload.get("state_namespaces") or ())
        payload["policy_basis_ids"] = tuple(payload.get("policy_basis_ids") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SourceTrustRevocation:
    trust_id: str
    trust_fingerprint: str
    revoked_at_ns: int
    reason_code: str
    revocation_id: str = ""
    contract_id: str = SOURCE_TRUST_CONTRACT_ID
    contract_version: str = SOURCE_TRUST_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("trust_id", "trust_fingerprint", "reason_code"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SOURCE_TRUST_CONTRACT_ID or self.contract_version != SOURCE_TRUST_CONTRACT_VERSION:
            raise ValueError("unsupported source-trust revocation contract")
        object.__setattr__(self, "revoked_at_ns", _portable_int(self.revoked_at_ns, "revoked_at_ns"))
        if not self.revocation_id:
            object.__setattr__(self, "revocation_id", f"source-trust-revocation-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "revocation_id", _required(self.revocation_id, "revocation_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "trust_id": self.trust_id,
            "trust_fingerprint": self.trust_fingerprint,
            "revoked_at_ns": self.revoked_at_ns,
            "reason_code": self.reason_code,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"revocation_id": self.revocation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"revocation_id": self.revocation_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SourceTrustRevocation":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


def source_trust_contract() -> dict[str, Any]:
    return {
        "contract_id": SOURCE_TRUST_CONTRACT_ID,
        "contract_version": SOURCE_TRUST_CONTRACT_VERSION,
        "stability": SOURCE_TRUST_STABILITY,
        "source_kinds": list(SOURCE_KINDS),
        "trust_dispositions": list(SOURCE_TRUST_DISPOSITIONS),
        "role": "EXPLICIT_POLICY_INPUT_ABOUT_A_SOURCE_NOT_FACT_AUTHORITY_OR_EFFECT_AUTHORITY",
        "selection": "EXPLICIT_TRUST_ASSERTION_ID_NO_HIDDEN_CURRENT_TRUST_OR_REPUTATION_SCORE",
        "identity_binding": "OPTIONAL_EXACT_PHYSICAL_IDENTITY_ID_AND_FINGERPRINT_PAIR",
        "calibration_binding": "OPTIONAL_EXACT_CALIBRATION_ID_TO_FINGERPRINT_MAP_REQUIRES_IDENTITY",
        "validity": "EXPLICIT_INTEGER_NANOSECOND_INTERVAL_NO_IMPLICIT_HOST_NOW",
        "revocation": "APPEND_ONLY_EXPLICIT_REVOCATION_EVIDENCE",
        "aggregation": "NONE_NO_TRUST_SCORE_NO_VOTING_NO_AUTOMATIC_LATEST_ASSERTION",
        "trusted_disposition_grants_fact_authority": False,
        "trusted_disposition_grants_effect_authority": False,
        "trusted_disposition_makes_claim_authoritative": False,
        "source_trust_mutates_fact_authority": False,
        "source_trust_mutates_state_claim": False,
        "source_trust_mutates_observation": False,
        "source_trust_is_universal_admission": False,
        "consumer_policy": "DOWNSTREAM_CONSUMER_MUST_NAME_EXACT_ASSERTION_AND_STILL_APPLY_FACT_AUTHORITY_VERIFICATION_AND_DOMAIN_POLICY",
        "portable_integer_range": f"0..{PORTABLE_U63_MAX}",
        "parallel_authority_evaluator": "NONE",
        "parallel_trust_registry": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
    }


__all__ = [
    "SOURCE_TRUST_CONTRACT_ID",
    "SOURCE_TRUST_CONTRACT_VERSION",
    "SOURCE_TRUST_STABILITY",
    "SOURCE_KINDS",
    "SOURCE_TRUST_DISPOSITIONS",
    "SourceTrustAssertion",
    "SourceTrustRevocation",
    "source_trust_contract",
]
