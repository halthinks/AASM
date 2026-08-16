from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


EFFECT_CAPABILITY_CONTRACT_ID = "aasm.effect.capability.v1"
EFFECT_CAPABILITY_CONTRACT_VERSION = "0.1.0"
EFFECT_CAPABILITY_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _unique(values: Sequence[str], name: str) -> tuple[str, ...]:
    normalized = tuple(sorted({str(value).strip() for value in values if str(value).strip()}))
    if not normalized:
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
    raise TypeError(f"effect-capability value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class NumericInterval:
    minimum: float
    maximum: float

    def __post_init__(self) -> None:
        minimum = float(self.minimum)
        maximum = float(self.maximum)
        if maximum < minimum:
            raise ValueError("numeric interval maximum must be >= minimum")
        object.__setattr__(self, "minimum", minimum)
        object.__setattr__(self, "maximum", maximum)

    def contains_interval(self, other: "NumericInterval") -> bool:
        return self.minimum <= other.minimum and other.maximum <= self.maximum

    def contains_value(self, value: float) -> bool:
        numeric = float(value)
        return self.minimum <= numeric <= self.maximum

    def to_dict(self) -> dict[str, float]:
        return {"minimum": self.minimum, "maximum": self.maximum}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NumericInterval":
        return cls(value["minimum"], value["maximum"])


def normalize_numeric_bounds(value: Mapping[str, Mapping[str, Any] | NumericInterval]) -> dict[str, NumericInterval]:
    result: dict[str, NumericInterval] = {}
    for raw_name, raw_interval in sorted(value.items(), key=lambda pair: str(pair[0])):
        name = _required(str(raw_name), "numeric bound name")
        interval = raw_interval if isinstance(raw_interval, NumericInterval) else NumericInterval.from_dict(raw_interval)
        result[name] = interval
    return result


def numeric_bounds_subset(
    child: Mapping[str, NumericInterval],
    parent: Mapping[str, NumericInterval],
) -> bool:
    # Every parent constraint must remain present and be equal or narrower in
    # the child. A child may add additional named constraints, which narrows
    # rather than amplifies the parent capability.
    for name, parent_interval in parent.items():
        child_interval = child.get(name)
        if child_interval is None or not parent_interval.contains_interval(child_interval):
            return False
    return True


@dataclass(frozen=True)
class EffectCapability:
    domain_id: str
    authority_lease_id: str
    workspace_id: str
    scope_id: str
    subject_id: str
    holder_principal_id: str
    issuer_principal_id: str
    allowed_operations: tuple[str, ...]
    numeric_bounds: Mapping[str, Mapping[str, Any] | NumericInterval]
    valid_from: float
    expires_at: float
    authority_epoch: int
    problem_revision_id: str = ""
    external_revision_id: str = ""
    remaining_delegation_depth: int = 0
    revocation_generation: int = 0
    parent_capability_id: str = ""
    parent_capability_fingerprint: str = ""
    parent_revocation_generation: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    capability_id: str = ""
    contract_id: str = EFFECT_CAPABILITY_CONTRACT_ID
    contract_version: str = EFFECT_CAPABILITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "domain_id",
            "authority_lease_id",
            "workspace_id",
            "scope_id",
            "subject_id",
            "holder_principal_id",
            "issuer_principal_id",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != EFFECT_CAPABILITY_CONTRACT_ID or self.contract_version != EFFECT_CAPABILITY_CONTRACT_VERSION:
            raise ValueError("unsupported effect-capability contract")
        object.__setattr__(self, "allowed_operations", _unique(self.allowed_operations, "allowed_operations"))
        object.__setattr__(self, "numeric_bounds", normalize_numeric_bounds(self.numeric_bounds))
        object.__setattr__(self, "valid_from", float(self.valid_from))
        object.__setattr__(self, "expires_at", float(self.expires_at))
        if self.expires_at <= self.valid_from:
            raise ValueError("effect capability expires_at must be greater than valid_from")
        if int(self.authority_epoch) < 1:
            raise ValueError("effect capability authority_epoch must be >= 1")
        object.__setattr__(self, "authority_epoch", int(self.authority_epoch))
        if int(self.remaining_delegation_depth) < 0:
            raise ValueError("remaining_delegation_depth must be >= 0")
        object.__setattr__(self, "remaining_delegation_depth", int(self.remaining_delegation_depth))
        if int(self.revocation_generation) < 0 or int(self.parent_revocation_generation) < 0:
            raise ValueError("revocation generations must be >= 0")
        object.__setattr__(self, "revocation_generation", int(self.revocation_generation))
        object.__setattr__(self, "parent_revocation_generation", int(self.parent_revocation_generation))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        object.__setattr__(self, "parent_capability_id", _optional(self.parent_capability_id))
        object.__setattr__(self, "parent_capability_fingerprint", _optional(self.parent_capability_fingerprint))
        if bool(self.parent_capability_id) != bool(self.parent_capability_fingerprint):
            raise ValueError("parent capability id and fingerprint must be supplied together")
        if not self.parent_capability_id and self.parent_revocation_generation != 0:
            raise ValueError("root capability parent_revocation_generation must be zero")
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.capability_id:
            object.__setattr__(self, "capability_id", f"effect-capability-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "capability_id", _required(self.capability_id, "capability_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "domain_id": self.domain_id,
            "authority_lease_id": self.authority_lease_id,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "holder_principal_id": self.holder_principal_id,
            "issuer_principal_id": self.issuer_principal_id,
            "allowed_operations": list(self.allowed_operations),
            "numeric_bounds": {
                name: interval.to_dict() for name, interval in sorted(self.numeric_bounds.items())
            },
            "valid_from": self.valid_from,
            "expires_at": self.expires_at,
            "authority_epoch": self.authority_epoch,
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "remaining_delegation_depth": self.remaining_delegation_depth,
            "revocation_generation": self.revocation_generation,
            "parent_capability_id": self.parent_capability_id,
            "parent_capability_fingerprint": self.parent_capability_fingerprint,
            "parent_revocation_generation": self.parent_revocation_generation,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"capability_id": self.capability_id, **self.identity_payload()})

    def active_at(self, at_time: float) -> bool:
        moment = float(at_time)
        return self.valid_from <= moment < self.expires_at

    def allows_operation(self, operation: str) -> bool:
        return str(operation).strip() in self.allowed_operations

    def bounds_allow(self, values: Mapping[str, float]) -> bool:
        for name, interval in self.numeric_bounds.items():
            if name not in values or not interval.contains_value(values[name]):
                return False
        return True

    def to_dict(self) -> dict[str, Any]:
        return {"capability_id": self.capability_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EffectCapability":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["allowed_operations"] = tuple(payload.get("allowed_operations") or ())
        payload["numeric_bounds"] = dict(payload.get("numeric_bounds") or {})
        return cls(**payload)


def effect_capability_contract() -> dict[str, Any]:
    return {
        "contract_id": EFFECT_CAPABILITY_CONTRACT_ID,
        "contract_version": EFFECT_CAPABILITY_CONTRACT_VERSION,
        "stability": EFFECT_CAPABILITY_STABILITY,
        "authority_source": "EXISTING_ACTIVE_AUTHORITY_LEASE_REQUIRED",
        "root_issuer": "ACTIVE_AUTHORITY_LEASE_HOLDER_ONLY",
        "operation_bound": "CAPABILITY_OPERATIONS_SUBSET_OF_LEASE_OR_PARENT",
        "numeric_bound": "NAMED_CLOSED_NUMERIC_INTERVALS_ONLY",
        "numeric_units": "NOT_INTERPRETED_UNTIL_QUANTITY_CONTRACT",
        "validity_bound": "CAPABILITY_INTERVAL_SUBSET_OF_LEASE_OR_PARENT",
        "scope_bound": "EXACT_DOMAIN_LEASE_SCOPE_FOUNDATION",
        "epoch_bound": "EXACT_AUTHORITY_LEASE_EPOCH",
        "revision_bound": "EXACT_DOMAIN_LEASE_REVISION",
        "delegation": "CHILD_RIGHTS_MUST_BE_SUBSET_AND_DEPTH_MUST_DECREASE",
        "parent_revocation": "CHILD_CAPTURES_PARENT_FINGERPRINT_AND_REVOCATION_GENERATION",
        "revocation": "APPEND_ONLY_GENERATION_FENCES_CAPABILITY_AND_DESCENDANTS",
        "capability_existence_grants_effect_authority": False,
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "effect_authorization_integration": "NOT_YET_PR3H",
        "semantic_preemption": "RESERVED_PR3G",
    }


__all__ = [
    "EFFECT_CAPABILITY_CONTRACT_ID",
    "EFFECT_CAPABILITY_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_STABILITY",
    "NumericInterval",
    "EffectCapability",
    "normalize_numeric_bounds",
    "numeric_bounds_subset",
    "effect_capability_contract",
]
