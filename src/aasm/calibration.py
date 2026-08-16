from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .event_causality import PORTABLE_U63_MAX
from .semantic_result import semantic_fingerprint


CALIBRATION_CONTRACT_ID = "aasm.calibration.v1"
CALIBRATION_CONTRACT_VERSION = "0.1.0"
CALIBRATION_STABILITY = "FOUNDATION_EXPERIMENTAL"

CALIBRATION_KINDS = (
    "MEASUREMENT",
    "TIMING",
    "ACTUATION",
    "TOOL",
    "MODEL",
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


@dataclass(frozen=True)
class CalibrationCertificate:
    workspace_id: str
    scope_id: str
    subject_id: str
    physical_identity_id: str
    physical_identity_fingerprint: str
    calibration_kind: str
    state_namespace: str
    calibration_revision_id: str
    procedure_id: str
    certificate_reference: str
    valid_from_ns: int
    expires_at_ns: int | None = None
    problem_revision_id: str = ""
    external_revision_id: str = ""
    calibration_id: str = ""
    contract_id: str = CALIBRATION_CONTRACT_ID
    contract_version: str = CALIBRATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "physical_identity_id",
            "physical_identity_fingerprint",
            "state_namespace",
            "calibration_revision_id",
            "procedure_id",
            "certificate_reference",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.calibration_kind not in CALIBRATION_KINDS:
            raise ValueError(f"invalid calibration kind: {self.calibration_kind}")
        if self.contract_id != CALIBRATION_CONTRACT_ID or self.contract_version != CALIBRATION_CONTRACT_VERSION:
            raise ValueError("unsupported calibration contract")
        valid_from = _portable_int(self.valid_from_ns, "valid_from_ns")
        expires_at = _optional_portable_int(self.expires_at_ns, "expires_at_ns")
        if expires_at is not None and expires_at <= valid_from:
            raise ValueError("expires_at_ns must be greater than valid_from_ns")
        object.__setattr__(self, "valid_from_ns", valid_from)
        object.__setattr__(self, "expires_at_ns", expires_at)
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        if not self.calibration_id:
            object.__setattr__(self, "calibration_id", f"calibration-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "calibration_id", _required(self.calibration_id, "calibration_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "physical_identity_id": self.physical_identity_id,
            "physical_identity_fingerprint": self.physical_identity_fingerprint,
            "calibration_kind": self.calibration_kind,
            "state_namespace": self.state_namespace,
            "calibration_revision_id": self.calibration_revision_id,
            "procedure_id": self.procedure_id,
            "certificate_reference": self.certificate_reference,
            "valid_from_ns": self.valid_from_ns,
            "expires_at_ns": self.expires_at_ns,
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"calibration_id": self.calibration_id, **self.identity_payload()})

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
        return {"calibration_id": self.calibration_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CalibrationCertificate":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass(frozen=True)
class CalibrationRevocation:
    calibration_id: str
    calibration_fingerprint: str
    revoked_at_ns: int
    reason_code: str
    revocation_id: str = ""
    contract_id: str = CALIBRATION_CONTRACT_ID
    contract_version: str = CALIBRATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("calibration_id", "calibration_fingerprint", "reason_code"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != CALIBRATION_CONTRACT_ID or self.contract_version != CALIBRATION_CONTRACT_VERSION:
            raise ValueError("unsupported calibration revocation contract")
        object.__setattr__(self, "revoked_at_ns", _portable_int(self.revoked_at_ns, "revoked_at_ns"))
        if not self.revocation_id:
            object.__setattr__(self, "revocation_id", f"calibration-revocation-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "revocation_id", _required(self.revocation_id, "revocation_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "calibration_id": self.calibration_id,
            "calibration_fingerprint": self.calibration_fingerprint,
            "revoked_at_ns": self.revoked_at_ns,
            "reason_code": self.reason_code,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"revocation_id": self.revocation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"revocation_id": self.revocation_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CalibrationRevocation":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


def calibration_contract() -> dict[str, Any]:
    return {
        "contract_id": CALIBRATION_CONTRACT_ID,
        "contract_version": CALIBRATION_CONTRACT_VERSION,
        "stability": CALIBRATION_STABILITY,
        "calibration_kinds": list(CALIBRATION_KINDS),
        "identity_binding": "EXACT_PHYSICAL_IDENTITY_ID_AND_FINGERPRINT_REQUIRED",
        "namespace_binding": "EXACT_STATE_OR_TOOL_NAMESPACE_REFERENCE",
        "validity": "EXPLICIT_INTEGER_NANOSECOND_INTERVAL_NO_IMPLICIT_HOST_NOW",
        "revocation": "APPEND_ONLY_EXPLICIT_REVOCATION_EVIDENCE",
        "selection": "EXPLICIT_CALIBRATION_ID_NO_HIDDEN_CURRENT_CALIBRATION_POINTER",
        "transform_application": "NOT_IMPLEMENTED_IN_S3_FOUNDATION",
        "calibration_existence_grants_fact_authority": False,
        "calibration_existence_grants_effect_authority": False,
        "calibration_existence_grants_source_trust": False,
        "calibration_mutates_observation": False,
        "calibration_mutates_state_claim": False,
        "calibration_mutates_physical_identity": False,
        "portable_integer_range": f"0..{PORTABLE_U63_MAX}",
        "host_wall_clock_in_identity": False,
        "parallel_calibration_store": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
    }


__all__ = [
    "CALIBRATION_CONTRACT_ID",
    "CALIBRATION_CONTRACT_VERSION",
    "CALIBRATION_STABILITY",
    "CALIBRATION_KINDS",
    "CalibrationCertificate",
    "CalibrationRevocation",
    "calibration_contract",
]
