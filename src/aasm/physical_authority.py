from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


AUTHORITY_DOMAIN_CONTRACT_ID = "aasm.authority.domain.v1"
AUTHORITY_LEASE_CONTRACT_ID = "aasm.authority.lease.v1"
PHYSICAL_AUTHORITY_CONTRACT_VERSION = "0.1.0"
PHYSICAL_AUTHORITY_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _unique(values: Sequence[str], name: str, *, allow_empty: bool = False) -> tuple[str, ...]:
    normalized = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
    if not normalized and not allow_empty:
        raise ValueError(f"{name} requires at least one value")
    return normalized


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"physical-authority value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class AuthorityDomain:
    workspace_id: str
    scope_id: str
    domain_name: str
    subject_id: str
    permitted_effect_classes: tuple[str, ...]
    preemptor_principal_ids: tuple[str, ...] = ()
    problem_revision_id: str = ""
    external_revision_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    domain_id: str = ""
    contract_id: str = AUTHORITY_DOMAIN_CONTRACT_ID
    contract_version: str = PHYSICAL_AUTHORITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("workspace_id", "scope_id", "domain_name", "subject_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != AUTHORITY_DOMAIN_CONTRACT_ID or self.contract_version != PHYSICAL_AUTHORITY_CONTRACT_VERSION:
            raise ValueError("unsupported authority-domain contract")
        object.__setattr__(self, "permitted_effect_classes", _unique(self.permitted_effect_classes, "permitted_effect_classes"))
        object.__setattr__(self, "preemptor_principal_ids", _unique(self.preemptor_principal_ids, "preemptor_principal_ids", allow_empty=True))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.domain_id:
            object.__setattr__(self, "domain_id", f"authority-domain-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "domain_id", _required(self.domain_id, "domain_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "domain_name": self.domain_name,
            "subject_id": self.subject_id,
            "permitted_effect_classes": list(self.permitted_effect_classes),
            "preemptor_principal_ids": list(self.preemptor_principal_ids),
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"domain_id": self.domain_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"domain_id": self.domain_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuthorityDomain":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["permitted_effect_classes"] = tuple(payload.get("permitted_effect_classes") or ())
        payload["preemptor_principal_ids"] = tuple(payload.get("preemptor_principal_ids") or ())
        return cls(**payload)


@dataclass(frozen=True)
class AuthorityLease:
    domain_id: str
    workspace_id: str
    scope_id: str
    holder_principal_id: str
    issuer_principal_id: str
    epoch: int
    valid_from: float
    expires_at: float
    permitted_effect_classes: tuple[str, ...]
    problem_revision_id: str = ""
    external_revision_id: str = ""
    revocation_generation: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    lease_id: str = ""
    contract_id: str = AUTHORITY_LEASE_CONTRACT_ID
    contract_version: str = PHYSICAL_AUTHORITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "domain_id",
            "workspace_id",
            "scope_id",
            "holder_principal_id",
            "issuer_principal_id",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != AUTHORITY_LEASE_CONTRACT_ID or self.contract_version != PHYSICAL_AUTHORITY_CONTRACT_VERSION:
            raise ValueError("unsupported authority-lease contract")
        if int(self.epoch) < 1:
            raise ValueError("authority lease epoch must be >= 1")
        object.__setattr__(self, "epoch", int(self.epoch))
        object.__setattr__(self, "valid_from", float(self.valid_from))
        object.__setattr__(self, "expires_at", float(self.expires_at))
        if self.expires_at <= self.valid_from:
            raise ValueError("authority lease expires_at must be greater than valid_from")
        if int(self.revocation_generation) < 0:
            raise ValueError("authority lease revocation_generation must be >= 0")
        object.__setattr__(self, "revocation_generation", int(self.revocation_generation))
        object.__setattr__(self, "permitted_effect_classes", _unique(self.permitted_effect_classes, "permitted_effect_classes"))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.lease_id:
            object.__setattr__(self, "lease_id", f"authority-lease-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "lease_id", _required(self.lease_id, "lease_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "domain_id": self.domain_id,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "holder_principal_id": self.holder_principal_id,
            "issuer_principal_id": self.issuer_principal_id,
            "epoch": self.epoch,
            "valid_from": self.valid_from,
            "expires_at": self.expires_at,
            "permitted_effect_classes": list(self.permitted_effect_classes),
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "revocation_generation": self.revocation_generation,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"lease_id": self.lease_id, **self.identity_payload()})

    def active_at(self, at_time: float) -> bool:
        moment = float(at_time)
        return self.valid_from <= moment < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {"lease_id": self.lease_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuthorityLease":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["permitted_effect_classes"] = tuple(payload.get("permitted_effect_classes") or ())
        return cls(**payload)


def physical_authority_contract() -> dict[str, Any]:
    return {
        "domain_contract_id": AUTHORITY_DOMAIN_CONTRACT_ID,
        "lease_contract_id": AUTHORITY_LEASE_CONTRACT_ID,
        "contract_version": PHYSICAL_AUTHORITY_CONTRACT_VERSION,
        "stability": PHYSICAL_AUTHORITY_STABILITY,
        "domain_role": "BOUNDED_EFFECT_AUTHORITY_NAMESPACE_NOT_AUTHORITY_GRANT",
        "lease_role": "EXCLUSIVE_TIME_BOUNDED_DOMAIN_HOLDER_NOT_EFFECT_PERMISSION_BY_EXISTENCE",
        "domain_effect_classes": "LEASE_EFFECT_CLASSES_MUST_BE_SUBSET_OF_DOMAIN",
        "lease_exclusivity": "AT_MOST_ONE_ACTIVE_LEASE_PER_DOMAIN",
        "authority_epoch": "STRICTLY_MONOTONIC_PER_DOMAIN",
        "revocation": "APPEND_ONLY_REVOCATION_WITH_GENERATION_IDENTITY",
        "resource_availability_grants_authority": False,
        "fact_authority_grants_effect_authority": False,
        "domain_existence_grants_effect_authority": False,
        "lease_existence_grants_effect_authority": False,
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "effect_authorization_integration": "NOT_YET_PR3H",
        "bounded_effect_capability": "RESERVED_PR3C_PR3D",
        "semantic_preemption": "RESERVED_PR3G",
    }


__all__ = [
    "AUTHORITY_DOMAIN_CONTRACT_ID",
    "AUTHORITY_LEASE_CONTRACT_ID",
    "PHYSICAL_AUTHORITY_CONTRACT_VERSION",
    "PHYSICAL_AUTHORITY_STABILITY",
    "AuthorityDomain",
    "AuthorityLease",
    "physical_authority_contract",
]
