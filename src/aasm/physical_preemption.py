from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .semantic_result import semantic_fingerprint


AUTHORITY_PREEMPTION_CONTRACT_ID = "aasm.authority.preemption.v1"
AUTHORITY_PREEMPTION_CONTRACT_VERSION = "0.1.0"
AUTHORITY_PREEMPTION_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"authority-preemption value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class AuthorityPreemption:
    domain_id: str
    authority_lease_id: str
    authority_lease_fingerprint: str
    workspace_id: str
    scope_id: str
    preemptor_principal_id: str
    preempted_holder_principal_id: str
    authority_epoch: int
    required_next_epoch: int
    preempted_at: float
    reason_code: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    preemption_id: str = ""
    contract_id: str = AUTHORITY_PREEMPTION_CONTRACT_ID
    contract_version: str = AUTHORITY_PREEMPTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "domain_id", "authority_lease_id", "authority_lease_fingerprint",
            "workspace_id", "scope_id", "preemptor_principal_id",
            "preempted_holder_principal_id", "reason_code",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != AUTHORITY_PREEMPTION_CONTRACT_ID or self.contract_version != AUTHORITY_PREEMPTION_CONTRACT_VERSION:
            raise ValueError("unsupported authority-preemption contract")
        if int(self.authority_epoch) < 1:
            raise ValueError("preempted authority_epoch must be >= 1")
        object.__setattr__(self, "authority_epoch", int(self.authority_epoch))
        object.__setattr__(self, "required_next_epoch", int(self.required_next_epoch))
        if self.required_next_epoch != self.authority_epoch + 1:
            raise ValueError("required_next_epoch must equal preempted authority_epoch + 1")
        object.__setattr__(self, "preempted_at", float(self.preempted_at))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.preemption_id:
            object.__setattr__(self, "preemption_id", f"authority-preemption-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "preemption_id", _required(self.preemption_id, "preemption_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "domain_id": self.domain_id,
            "authority_lease_id": self.authority_lease_id,
            "authority_lease_fingerprint": self.authority_lease_fingerprint,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "preemptor_principal_id": self.preemptor_principal_id,
            "preempted_holder_principal_id": self.preempted_holder_principal_id,
            "authority_epoch": self.authority_epoch,
            "required_next_epoch": self.required_next_epoch,
            "preempted_at": self.preempted_at,
            "reason_code": self.reason_code,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"preemption_id": self.preemption_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"preemption_id": self.preemption_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuthorityPreemption":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


def authority_preemption_contract() -> dict[str, Any]:
    return {
        "contract_id": AUTHORITY_PREEMPTION_CONTRACT_ID,
        "contract_version": AUTHORITY_PREEMPTION_CONTRACT_VERSION,
        "stability": AUTHORITY_PREEMPTION_STABILITY,
        "identity_reference": "PREEMPTOR_MUST_BE_LISTED_BY_AUTHORITY_DOMAIN",
        "identity_reference_grants_authority": False,
        "authorization": "EXISTING_SCOPED_PHYSICAL_AUTHORITY_PREEMPT_REQUIRED",
        "target": "EXACT_ACTIVE_AUTHORITY_LEASE_ID_FINGERPRINT_AND_EPOCH_REQUIRED",
        "effect": "CANONICAL_AUTHORITY_LEASE_REVOCATION_PLUS_PREEMPTION_EVIDENCE",
        "epoch": "REQUIRED_NEXT_EPOCH_EQUALS_PREEMPTED_EPOCH_PLUS_ONE",
        "history": "APPEND_ONLY_NO_EFFECT_HISTORY_REWRITE",
        "preemption_grants_new_effect_authority": False,
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "effect_authorization_integration": "NOT_YET_PR3H",
    }


__all__ = [
    "AUTHORITY_PREEMPTION_CONTRACT_ID", "AUTHORITY_PREEMPTION_CONTRACT_VERSION",
    "AUTHORITY_PREEMPTION_STABILITY", "AuthorityPreemption", "authority_preemption_contract",
]
