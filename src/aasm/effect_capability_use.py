from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .semantic_result import semantic_fingerprint


EFFECT_CAPABILITY_USE_CONTRACT_ID = "aasm.effect.capability-use.v1"
EFFECT_CAPABILITY_USE_CONTRACT_VERSION = "0.1.0"
EFFECT_CAPABILITY_USE_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _numeric_values(value: Mapping[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for raw_name, raw_value in sorted(value.items(), key=lambda pair: str(pair[0])):
        name = _required(str(raw_name), "numeric parameter name")
        if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
            raise TypeError(f"numeric parameter {name!r} must be int or float")
        result[name] = float(raw_value)
    return result


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"capability-use value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class EffectCapabilityUse:
    capability_id: str
    capability_fingerprint: str
    authority_lease_id: str
    authority_lease_fingerprint: str
    domain_id: str
    workspace_id: str
    scope_id: str
    subject_id: str
    actor_principal_id: str
    operation: str
    numeric_parameters: Mapping[str, Any]
    authority_epoch: int
    capability_revocation_generation: int
    at_time: float
    problem_revision_id: str = ""
    external_revision_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    use_id: str = ""
    contract_id: str = EFFECT_CAPABILITY_USE_CONTRACT_ID
    contract_version: str = EFFECT_CAPABILITY_USE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "capability_id",
            "capability_fingerprint",
            "authority_lease_id",
            "authority_lease_fingerprint",
            "domain_id",
            "workspace_id",
            "scope_id",
            "subject_id",
            "actor_principal_id",
            "operation",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != EFFECT_CAPABILITY_USE_CONTRACT_ID or self.contract_version != EFFECT_CAPABILITY_USE_CONTRACT_VERSION:
            raise ValueError("unsupported effect-capability-use contract")
        if int(self.authority_epoch) < 1:
            raise ValueError("capability use authority_epoch must be >= 1")
        object.__setattr__(self, "authority_epoch", int(self.authority_epoch))
        if int(self.capability_revocation_generation) < 0:
            raise ValueError("capability use revocation generation must be >= 0")
        object.__setattr__(self, "capability_revocation_generation", int(self.capability_revocation_generation))
        object.__setattr__(self, "at_time", float(self.at_time))
        object.__setattr__(self, "numeric_parameters", _numeric_values(self.numeric_parameters))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.use_id:
            object.__setattr__(self, "use_id", f"effect-capability-use-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "use_id", _required(self.use_id, "use_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "capability_id": self.capability_id,
            "capability_fingerprint": self.capability_fingerprint,
            "authority_lease_id": self.authority_lease_id,
            "authority_lease_fingerprint": self.authority_lease_fingerprint,
            "domain_id": self.domain_id,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "actor_principal_id": self.actor_principal_id,
            "operation": self.operation,
            "numeric_parameters": dict(self.numeric_parameters),
            "authority_epoch": self.authority_epoch,
            "capability_revocation_generation": self.capability_revocation_generation,
            "at_time": self.at_time,
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"use_id": self.use_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"use_id": self.use_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EffectCapabilityUse":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["numeric_parameters"] = dict(payload.get("numeric_parameters") or {})
        return cls(**payload)


def effect_capability_use_contract() -> dict[str, Any]:
    return {
        "contract_id": EFFECT_CAPABILITY_USE_CONTRACT_ID,
        "contract_version": EFFECT_CAPABILITY_USE_CONTRACT_VERSION,
        "stability": EFFECT_CAPABILITY_USE_STABILITY,
        "role": "POINT_IN_TIME_STALE_COMMAND_FENCE_NOT_DURABLE_EFFECT_AUTHORIZATION",
        "capability_identity": "EXACT_ID_AND_FINGERPRINT_REQUIRED",
        "lease_identity": "EXACT_ID_AND_FINGERPRINT_REQUIRED",
        "holder": "ACTOR_MUST_EQUAL_CURRENT_CAPABILITY_HOLDER",
        "operation": "MUST_BE_ALLOWED_BY_CURRENT_CAPABILITY",
        "numeric_parameters": "MUST_SATISFY_ALL_CURRENT_NAMED_CLOSED_BOUNDS",
        "numeric_units": "NOT_INTERPRETED_UNTIL_QUANTITY_CONTRACT",
        "epoch": "EXACT_CURRENT_AUTHORITY_EPOCH_REQUIRED",
        "revocation_generation": "EXACT_CURRENT_EFFECTIVE_CAPABILITY_GENERATION_REQUIRED",
        "validity": "CAPABILITY_AND_AUTHORITY_LEASE_MUST_BE_ACTIVE_AT_USE_TIME",
        "revision": "EXACT_CURRENT_CAPABILITY_DOMAIN_LEASE_REVISION_REQUIRED",
        "validation_grants_effect_authority": False,
        "validation_is_reusable_authorization_token": False,
        "required_recheck": "PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES",
        "effect_authorization_integration": "NOT_YET_PR3H",
        "effect_dispatch": "NONE",
    }


__all__ = [
    "EFFECT_CAPABILITY_USE_CONTRACT_ID",
    "EFFECT_CAPABILITY_USE_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_USE_STABILITY",
    "EffectCapabilityUse",
    "effect_capability_use_contract",
]
