from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .state_authority import StateClaim


STATE_CONFLICT_CONTRACT_ID = "aasm.state.conflict.v1"
STATE_CONFLICT_CONTRACT_VERSION = "0.1.0"
STATE_CONFLICT_STABILITY = "FOUNDATION_EXPERIMENTAL"

STATE_CONFLICT_EXPECTATION_KINDS = (
    "DESIRED",
    "PREDICTED",
    "AUTHORITATIVE",
)
STATE_CONFLICT_ACTUAL_KINDS = (
    "OBSERVED",
    "AUTHORITATIVE",
)
STATE_CONFLICT_REASONS = (
    "VALUE_MISMATCH",
    "PROBLEM_REVISION_MISMATCH",
    "EXTERNAL_REVISION_MISMATCH",
)


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _portable_json(value: Any) -> Any:
    """Return the v1 portable JSON subset used in state-conflict identity.

    Non-finite floats are rejected because JSON spellings such as NaN/Infinity are
    not portable language-independent values. Mapping keys are canonical strings;
    sequence order is semantic and therefore preserved.
    """

    if hasattr(value, "to_dict"):
        return _portable_json(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _portable_json(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [_portable_json(item) for item in value]
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        if not isfinite(value):
            raise ValueError("state-conflict portable identity rejects non-finite floats")
        return value
    raise TypeError(f"state-conflict value is outside the portable JSON subset: {type(value)!r}")


def _canonical_value(value: Any) -> str:
    return canonical_semantic_json(_portable_json(value))


def state_conflict_reasons(expectation: StateClaim, actual: StateClaim) -> tuple[str, ...]:
    if expectation.claim_kind not in STATE_CONFLICT_EXPECTATION_KINDS:
        raise ValueError(
            f"state conflict expectation must be one of {STATE_CONFLICT_EXPECTATION_KINDS}, got {expectation.claim_kind}"
        )
    if actual.claim_kind not in STATE_CONFLICT_ACTUAL_KINDS:
        raise ValueError(
            f"state conflict actual claim must be one of {STATE_CONFLICT_ACTUAL_KINDS}, got {actual.claim_kind}"
        )
    for name in ("workspace_id", "scope_id", "subject_id", "state_namespace"):
        if getattr(expectation, name) != getattr(actual, name):
            raise ValueError(f"state conflict claims are not comparable: {name} mismatch")

    reasons: list[str] = []
    if _canonical_value(expectation.value) != _canonical_value(actual.value):
        reasons.append("VALUE_MISMATCH")
    if expectation.problem_revision_id != actual.problem_revision_id:
        reasons.append("PROBLEM_REVISION_MISMATCH")
    if expectation.external_revision_id != actual.external_revision_id:
        reasons.append("EXTERNAL_REVISION_MISMATCH")
    return tuple(reasons)


@dataclass(frozen=True)
class StateConflict:
    workspace_id: str
    scope_id: str
    subject_id: str
    state_namespace: str
    expectation_claim_id: str
    expectation_claim_fingerprint: str
    expectation_claim_kind: str
    actual_claim_id: str
    actual_claim_fingerprint: str
    actual_claim_kind: str
    expected_value: Any
    actual_value: Any
    expectation_problem_revision_id: str = ""
    actual_problem_revision_id: str = ""
    expectation_external_revision_id: str = ""
    actual_external_revision_id: str = ""
    reasons: tuple[str, ...] = ()
    conflict_id: str = ""
    contract_id: str = STATE_CONFLICT_CONTRACT_ID
    contract_version: str = STATE_CONFLICT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "state_namespace",
            "expectation_claim_id",
            "expectation_claim_fingerprint",
            "actual_claim_id",
            "actual_claim_fingerprint",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != STATE_CONFLICT_CONTRACT_ID or self.contract_version != STATE_CONFLICT_CONTRACT_VERSION:
            raise ValueError("unsupported state-conflict contract")
        if self.expectation_claim_kind not in STATE_CONFLICT_EXPECTATION_KINDS:
            raise ValueError(f"invalid expectation_claim_kind: {self.expectation_claim_kind}")
        if self.actual_claim_kind not in STATE_CONFLICT_ACTUAL_KINDS:
            raise ValueError(f"invalid actual_claim_kind: {self.actual_claim_kind}")
        if self.expectation_claim_id == self.actual_claim_id:
            raise ValueError("state conflict requires two distinct state claims")
        object.__setattr__(self, "expected_value", _portable_json(self.expected_value))
        object.__setattr__(self, "actual_value", _portable_json(self.actual_value))
        object.__setattr__(self, "expectation_problem_revision_id", str(self.expectation_problem_revision_id).strip())
        object.__setattr__(self, "actual_problem_revision_id", str(self.actual_problem_revision_id).strip())
        object.__setattr__(self, "expectation_external_revision_id", str(self.expectation_external_revision_id).strip())
        object.__setattr__(self, "actual_external_revision_id", str(self.actual_external_revision_id).strip())
        normalized_reasons = tuple(sorted({str(value).strip() for value in self.reasons if str(value).strip()}))
        if not normalized_reasons:
            raise ValueError("state conflict requires at least one conflict reason")
        unknown = sorted(set(normalized_reasons) - set(STATE_CONFLICT_REASONS))
        if unknown:
            raise ValueError(f"unknown state-conflict reasons: {unknown}")
        object.__setattr__(self, "reasons", normalized_reasons)
        if not self.conflict_id:
            object.__setattr__(self, "conflict_id", f"state-conflict-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "conflict_id", _required(self.conflict_id, "conflict_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "state_namespace": self.state_namespace,
            "expectation_claim_id": self.expectation_claim_id,
            "expectation_claim_fingerprint": self.expectation_claim_fingerprint,
            "expectation_claim_kind": self.expectation_claim_kind,
            "actual_claim_id": self.actual_claim_id,
            "actual_claim_fingerprint": self.actual_claim_fingerprint,
            "actual_claim_kind": self.actual_claim_kind,
            "expected_value": _portable_json(self.expected_value),
            "actual_value": _portable_json(self.actual_value),
            "expectation_problem_revision_id": self.expectation_problem_revision_id,
            "actual_problem_revision_id": self.actual_problem_revision_id,
            "expectation_external_revision_id": self.expectation_external_revision_id,
            "actual_external_revision_id": self.actual_external_revision_id,
            "reasons": list(self.reasons),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"conflict_id": self.conflict_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"conflict_id": self.conflict_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "StateConflict":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["reasons"] = tuple(payload.get("reasons") or ())
        return cls(**payload)

    @classmethod
    def from_claims(cls, expectation: StateClaim, actual: StateClaim) -> "StateConflict":
        reasons = state_conflict_reasons(expectation, actual)
        if not reasons:
            raise ValueError("state claims do not conflict under exact S3 foundation semantics")
        return cls(
            workspace_id=expectation.workspace_id,
            scope_id=expectation.scope_id,
            subject_id=expectation.subject_id,
            state_namespace=expectation.state_namespace,
            expectation_claim_id=expectation.claim_id,
            expectation_claim_fingerprint=expectation.fingerprint,
            expectation_claim_kind=expectation.claim_kind,
            actual_claim_id=actual.claim_id,
            actual_claim_fingerprint=actual.fingerprint,
            actual_claim_kind=actual.claim_kind,
            expected_value=expectation.value,
            actual_value=actual.value,
            expectation_problem_revision_id=expectation.problem_revision_id,
            actual_problem_revision_id=actual.problem_revision_id,
            expectation_external_revision_id=expectation.external_revision_id,
            actual_external_revision_id=actual.external_revision_id,
            reasons=reasons,
        )


def state_conflict_contract() -> dict[str, Any]:
    return {
        "contract_id": STATE_CONFLICT_CONTRACT_ID,
        "contract_version": STATE_CONFLICT_CONTRACT_VERSION,
        "stability": STATE_CONFLICT_STABILITY,
        "expectation_claim_kinds": list(STATE_CONFLICT_EXPECTATION_KINDS),
        "actual_claim_kinds": list(STATE_CONFLICT_ACTUAL_KINDS),
        "conflict_reasons": list(STATE_CONFLICT_REASONS),
        "comparison": "EXACT_CANONICAL_PORTABLE_JSON_VALUE_PLUS_EXACT_REVISION_IDENTITY",
        "quantity_tolerance": "RESERVED_FOR_S4_QUANTITY_SEMANTICS",
        "context": "EXACT_WORKSPACE_SCOPE_SUBJECT_NAMESPACE_REQUIRED",
        "revision_mismatch": "DURABLE_CONFLICT_REASON_NOT_SILENT_NONCOMPARABILITY",
        "history": "EXPECTATION_AND_ACTUAL_STATE_CLAIMS_REMAIN_UNCHANGED",
        "actual_observation_authority": "PRESERVE_SOURCE_CLAIM_KIND_NEVER_ELEVATE_OBSERVED_TO_AUTHORITATIVE",
        "conflict_grants_fact_authority": False,
        "conflict_grants_effect_authority": False,
        "conflict_mutates_machine_state": False,
        "conflict_mutates_state_claims": False,
        "resolution_lifecycle": "NOT_DEFINED_IN_V1_CONFLICT_EVIDENCE_IS_IMMUTABLE",
        "portable_identity": "CANONICAL_LANGUAGE_INDEPENDENT_JSON_SUBSET_AND_SORTED_REASON_ENUMS",
        "host_wall_clock_in_identity": False,
        "python_object_identity_in_identity": False,
        "parallel_truth_table": "NONE",
    }


__all__ = [
    "STATE_CONFLICT_CONTRACT_ID",
    "STATE_CONFLICT_CONTRACT_VERSION",
    "STATE_CONFLICT_STABILITY",
    "STATE_CONFLICT_EXPECTATION_KINDS",
    "STATE_CONFLICT_ACTUAL_KINDS",
    "STATE_CONFLICT_REASONS",
    "StateConflict",
    "state_conflict_reasons",
    "state_conflict_contract",
]
