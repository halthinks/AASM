from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


FACT_AUTHORITY_CONTRACT_ID = "aasm.fact.authority.v1"
FACT_AUTHORITY_CONTRACT_VERSION = "0.1.0"
STATE_CLAIM_CONTRACT_ID = "aasm.state.claim.v1"
STATE_CLAIM_CONTRACT_VERSION = "0.1.0"
STATE_AUTHORITY_STABILITY = "FOUNDATION_EXPERIMENTAL"

STATE_CLAIM_KINDS = (
    "DESIRED",
    "PREDICTED",
    "OBSERVED",
    "AUTHORITATIVE",
)


def _require(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


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
    raise TypeError(f"state-authority value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class FactAuthority:
    workspace_id: str
    scope_id: str
    subject_id: str
    state_namespace: str
    authority_principal_id: str
    valid_from: float = 0.0
    expires_at: float | None = None
    problem_revision_id: str = ""
    external_revision_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    authority_id: str = ""
    contract_id: str = FACT_AUTHORITY_CONTRACT_ID
    contract_version: str = FACT_AUTHORITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "state_namespace",
            "authority_principal_id",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != FACT_AUTHORITY_CONTRACT_ID or self.contract_version != FACT_AUTHORITY_CONTRACT_VERSION:
            raise ValueError("unsupported fact authority contract")
        valid_from = float(self.valid_from)
        if valid_from < 0:
            raise ValueError("valid_from must be non-negative")
        expires_at = None if self.expires_at is None else float(self.expires_at)
        if expires_at is not None and expires_at <= valid_from:
            raise ValueError("expires_at must be greater than valid_from")
        object.__setattr__(self, "valid_from", valid_from)
        object.__setattr__(self, "expires_at", expires_at)
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "external_revision_id", str(self.external_revision_id).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.authority_id:
            object.__setattr__(
                self,
                "authority_id",
                f"fact-authority-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "authority_id", _require(self.authority_id, "authority_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "state_namespace": self.state_namespace,
            "authority_principal_id": self.authority_principal_id,
            "valid_from": self.valid_from,
            "expires_at": self.expires_at,
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"authority_id": self.authority_id, **self.identity_payload()})

    def active_at(self, at_time: float) -> bool:
        when = float(at_time)
        if when < self.valid_from:
            return False
        return self.expires_at is None or when < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "authority_id": self.authority_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FactAuthority":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass(frozen=True)
class StateClaim:
    claim_kind: str
    workspace_id: str
    scope_id: str
    subject_id: str
    state_namespace: str
    value: Any
    source_principal_id: str
    problem_revision_id: str = ""
    external_revision_id: str = ""
    source_claim_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    claim_id: str = ""
    contract_id: str = STATE_CLAIM_CONTRACT_ID
    contract_version: str = STATE_CLAIM_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.claim_kind not in STATE_CLAIM_KINDS:
            raise ValueError(f"invalid state claim kind: {self.claim_kind}")
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "state_namespace",
            "source_principal_id",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != STATE_CLAIM_CONTRACT_ID or self.contract_version != STATE_CLAIM_CONTRACT_VERSION:
            raise ValueError("unsupported state claim contract")
        source_claim_ids = _uniq(self.source_claim_ids)
        evidence_ids = _uniq(self.evidence_ids)
        if self.claim_kind == "AUTHORITATIVE" and not source_claim_ids:
            raise ValueError("AUTHORITATIVE state claim requires at least one source_claim_id")
        object.__setattr__(self, "source_claim_ids", source_claim_ids)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "external_revision_id", str(self.external_revision_id).strip())
        object.__setattr__(self, "value", _jsonable(self.value))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.claim_id:
            object.__setattr__(
                self,
                "claim_id",
                f"state-claim-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "claim_id", _require(self.claim_id, "claim_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "claim_kind": self.claim_kind,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "state_namespace": self.state_namespace,
            "value": _jsonable(self.value),
            "source_principal_id": self.source_principal_id,
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "source_claim_ids": list(self.source_claim_ids),
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"claim_id": self.claim_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "claim_id": self.claim_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StateClaim":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["source_claim_ids"] = tuple(payload.get("source_claim_ids") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        return cls(**payload)


def fact_authority_matches_claim(authority: FactAuthority, claim: StateClaim, *, at_time: float) -> bool:
    if not authority.active_at(at_time):
        return False
    if authority.workspace_id != claim.workspace_id or authority.scope_id != claim.scope_id:
        return False
    if authority.subject_id != claim.subject_id or authority.state_namespace != claim.state_namespace:
        return False
    if authority.authority_principal_id != claim.source_principal_id:
        return False
    if authority.problem_revision_id and authority.problem_revision_id != claim.problem_revision_id:
        return False
    if authority.external_revision_id and authority.external_revision_id != claim.external_revision_id:
        return False
    return True


def state_authority_contract() -> dict[str, Any]:
    return {
        "fact_authority_contract_id": FACT_AUTHORITY_CONTRACT_ID,
        "fact_authority_contract_version": FACT_AUTHORITY_CONTRACT_VERSION,
        "state_claim_contract_id": STATE_CLAIM_CONTRACT_ID,
        "state_claim_contract_version": STATE_CLAIM_CONTRACT_VERSION,
        "stability": STATE_AUTHORITY_STABILITY,
        "claim_kinds": list(STATE_CLAIM_KINDS),
        "desired": "INTENT_ONLY_NEVER_OBSERVATION_OR_FACT_AUTHORITY",
        "predicted": "MODEL_EXPECTATION_ONLY_NEVER_OBSERVATION_OR_FACT_AUTHORITY",
        "observed": "EMPIRICAL_EVIDENCE_ONLY_NOT_AUTHORITATIVE_BY_EXISTENCE_OR_AGREEMENT",
        "authoritative": "EXPLICIT_MATCHING_FACT_AUTHORITY_AND_SOURCE_CLAIM_REQUIRED",
        "authority_matching": "EXACT_WORKSPACE_SCOPE_SUBJECT_NAMESPACE_PRINCIPAL_AND_BOUND_REVISIONS",
        "aggregation_grants_authority": False,
        "fact_authority_grants_effect_authority": False,
        "state_claim_grants_effect_authority": False,
        "machine_state_mutation": "NONE_BY_THIS_CONTRACT",
        "durability_target": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "cross_run_authority_transfer": "NEVER",
    }


__all__ = [
    "FACT_AUTHORITY_CONTRACT_ID",
    "FACT_AUTHORITY_CONTRACT_VERSION",
    "STATE_CLAIM_CONTRACT_ID",
    "STATE_CLAIM_CONTRACT_VERSION",
    "STATE_AUTHORITY_STABILITY",
    "STATE_CLAIM_KINDS",
    "FactAuthority",
    "StateClaim",
    "fact_authority_matches_claim",
    "state_authority_contract",
]
