from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .event_causality import (
    CLOCK_QUALITIES,
    CLOCK_QUALITY_RANK,
    PORTABLE_U63_MAX,
    CausalEventIdentity,
)
from .semantic_result import semantic_fingerprint


OBSERVATION_FRESHNESS_CONTRACT_ID = "aasm.observation.freshness.v1"
OBSERVATION_FRESHNESS_CONTRACT_VERSION = "0.1.0"
OBSERVATION_FRESHNESS_STABILITY = "FOUNDATION_EXPERIMENTAL"

FRESHNESS_STATUSES = ("FRESH", "STALE", "UNKNOWN")
FRESHNESS_AGE_BASES = ("SOURCE_TIME", "RECEIPT_TIME", "UNRESOLVED")
FRESHNESS_REASONS = (
    "AGE_UNRESOLVED",
    "BOOT_EPOCH_MISMATCH",
    "CLOCK_QUALITY_INSUFFICIENT",
    "CLOCK_UNCERTAINTY_EXCEEDED",
    "CLOCK_UNCERTAINTY_UNKNOWN",
    "EXTERNAL_REVISION_MISMATCH",
    "MAX_AGE_EXCEEDED",
    "NEGATIVE_AGE",
    "PROBLEM_REVISION_MISMATCH",
    "RECEIPT_CLOCK_MISMATCH",
    "RECEIPT_FALLBACK_USED",
    "RECEIPT_TIME_MISSING",
    "SOURCE_CLOCK_MISMATCH",
    "SOURCE_TIME_MISSING",
)


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _portable_int(value: int, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    parsed = int(value)
    if parsed < minimum or parsed > PORTABLE_U63_MAX:
        raise ValueError(f"{name} must be between {minimum} and {PORTABLE_U63_MAX}")
    return parsed


def _optional_portable_int(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    return _portable_int(value, name)


@dataclass(frozen=True)
class ObservationFreshnessAssessment:
    workspace_id: str
    scope_id: str
    subject_id: str
    state_namespace: str
    observation_id: str
    observation_fingerprint: str
    state_claim_id: str
    state_claim_fingerprint: str
    causal_event_id: str
    causal_event_fingerprint: str
    actual_boot_epoch: int
    expected_boot_epoch: int
    actual_problem_revision_id: str
    expected_problem_revision_id: str
    actual_external_revision_id: str
    expected_external_revision_id: str
    reference_time_ns: int
    reference_clock_id: str
    max_age_ns: int
    minimum_source_clock_quality: str = "MONOTONIC_LOCAL"
    max_source_clock_uncertainty_ns: int | None = None
    allow_receipt_time_fallback: bool = False
    age_basis: str = "UNRESOLVED"
    age_ns: int | None = None
    status: str = "UNKNOWN"
    reasons: tuple[str, ...] = ()
    assessment_id: str = ""
    contract_id: str = OBSERVATION_FRESHNESS_CONTRACT_ID
    contract_version: str = OBSERVATION_FRESHNESS_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "state_namespace",
            "observation_id",
            "observation_fingerprint",
            "state_claim_id",
            "state_claim_fingerprint",
            "causal_event_id",
            "causal_event_fingerprint",
            "reference_clock_id",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != OBSERVATION_FRESHNESS_CONTRACT_ID or self.contract_version != OBSERVATION_FRESHNESS_CONTRACT_VERSION:
            raise ValueError("unsupported observation-freshness contract")
        object.__setattr__(self, "actual_boot_epoch", _portable_int(self.actual_boot_epoch, "actual_boot_epoch", minimum=1))
        object.__setattr__(self, "expected_boot_epoch", _portable_int(self.expected_boot_epoch, "expected_boot_epoch", minimum=1))
        object.__setattr__(self, "reference_time_ns", _portable_int(self.reference_time_ns, "reference_time_ns"))
        object.__setattr__(self, "max_age_ns", _portable_int(self.max_age_ns, "max_age_ns"))
        object.__setattr__(
            self,
            "max_source_clock_uncertainty_ns",
            _optional_portable_int(self.max_source_clock_uncertainty_ns, "max_source_clock_uncertainty_ns"),
        )
        object.__setattr__(self, "actual_problem_revision_id", _optional(self.actual_problem_revision_id))
        object.__setattr__(self, "expected_problem_revision_id", _optional(self.expected_problem_revision_id))
        object.__setattr__(self, "actual_external_revision_id", _optional(self.actual_external_revision_id))
        object.__setattr__(self, "expected_external_revision_id", _optional(self.expected_external_revision_id))
        if self.minimum_source_clock_quality not in CLOCK_QUALITIES:
            raise ValueError(f"invalid minimum_source_clock_quality: {self.minimum_source_clock_quality}")
        if self.age_basis not in FRESHNESS_AGE_BASES:
            raise ValueError(f"invalid age_basis: {self.age_basis}")
        if self.status not in FRESHNESS_STATUSES:
            raise ValueError(f"invalid freshness status: {self.status}")
        age = _optional_portable_int(self.age_ns, "age_ns")
        object.__setattr__(self, "age_ns", age)
        normalized_reasons = tuple(sorted({str(value).strip() for value in self.reasons if str(value).strip()}))
        unknown = sorted(set(normalized_reasons) - set(FRESHNESS_REASONS))
        if unknown:
            raise ValueError(f"unknown freshness reasons: {unknown}")
        object.__setattr__(self, "reasons", normalized_reasons)
        if self.age_basis == "UNRESOLVED" and age is not None:
            raise ValueError("UNRESOLVED age_basis cannot carry age_ns")
        if self.age_basis != "UNRESOLVED" and age is None:
            raise ValueError("resolved age_basis requires age_ns")
        if self.status == "FRESH" and (age is None or age > self.max_age_ns):
            raise ValueError("FRESH assessment requires a resolved age within max_age_ns")
        if not self.assessment_id:
            object.__setattr__(
                self,
                "assessment_id",
                f"observation-freshness-{semantic_fingerprint(self.request_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "assessment_id", _required(self.assessment_id, "assessment_id"))

    def request_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "state_namespace": self.state_namespace,
            "observation_id": self.observation_id,
            "observation_fingerprint": self.observation_fingerprint,
            "state_claim_id": self.state_claim_id,
            "state_claim_fingerprint": self.state_claim_fingerprint,
            "causal_event_id": self.causal_event_id,
            "causal_event_fingerprint": self.causal_event_fingerprint,
            "actual_boot_epoch": self.actual_boot_epoch,
            "expected_boot_epoch": self.expected_boot_epoch,
            "actual_problem_revision_id": self.actual_problem_revision_id,
            "expected_problem_revision_id": self.expected_problem_revision_id,
            "actual_external_revision_id": self.actual_external_revision_id,
            "expected_external_revision_id": self.expected_external_revision_id,
            "reference_time_ns": self.reference_time_ns,
            "reference_clock_id": self.reference_clock_id,
            "max_age_ns": self.max_age_ns,
            "minimum_source_clock_quality": self.minimum_source_clock_quality,
            "max_source_clock_uncertainty_ns": self.max_source_clock_uncertainty_ns,
            "allow_receipt_time_fallback": bool(self.allow_receipt_time_fallback),
        }

    def identity_payload(self) -> dict[str, Any]:
        return {
            **self.request_payload(),
            "age_basis": self.age_basis,
            "age_ns": self.age_ns,
            "status": self.status,
            "reasons": list(self.reasons),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assessment_id": self.assessment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"assessment_id": self.assessment_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObservationFreshnessAssessment":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["reasons"] = tuple(payload.get("reasons") or ())
        return cls(**payload)


def assess_freshness(
    event: CausalEventIdentity,
    *,
    workspace_id: str,
    scope_id: str,
    subject_id: str,
    state_namespace: str,
    observation_id: str,
    observation_fingerprint: str,
    state_claim_id: str,
    state_claim_fingerprint: str,
    actual_problem_revision_id: str,
    expected_problem_revision_id: str,
    actual_external_revision_id: str,
    expected_external_revision_id: str,
    expected_boot_epoch: int,
    reference_time_ns: int,
    reference_clock_id: str,
    max_age_ns: int,
    minimum_source_clock_quality: str = "MONOTONIC_LOCAL",
    max_source_clock_uncertainty_ns: int | None = None,
    allow_receipt_time_fallback: bool = False,
) -> ObservationFreshnessAssessment:
    if minimum_source_clock_quality not in CLOCK_QUALITIES:
        raise ValueError(f"invalid minimum_source_clock_quality: {minimum_source_clock_quality}")
    reference_time = _portable_int(reference_time_ns, "reference_time_ns")
    maximum_age = _portable_int(max_age_ns, "max_age_ns")
    expected_epoch = _portable_int(expected_boot_epoch, "expected_boot_epoch", minimum=1)
    max_uncertainty = _optional_portable_int(max_source_clock_uncertainty_ns, "max_source_clock_uncertainty_ns")
    reference_clock = _required(reference_clock_id, "reference_clock_id")

    reasons: set[str] = set()
    stale_reasons: set[str] = set()
    if event.boot_epoch != expected_epoch:
        reasons.add("BOOT_EPOCH_MISMATCH")
        stale_reasons.add("BOOT_EPOCH_MISMATCH")
    if expected_problem_revision_id and actual_problem_revision_id != expected_problem_revision_id:
        reasons.add("PROBLEM_REVISION_MISMATCH")
        stale_reasons.add("PROBLEM_REVISION_MISMATCH")
    if expected_external_revision_id and actual_external_revision_id != expected_external_revision_id:
        reasons.add("EXTERNAL_REVISION_MISMATCH")
        stale_reasons.add("EXTERNAL_REVISION_MISMATCH")

    source_usable = True
    if event.source_time_ns is None:
        reasons.add("SOURCE_TIME_MISSING")
        source_usable = False
    elif event.source_clock_id != reference_clock:
        reasons.add("SOURCE_CLOCK_MISMATCH")
        source_usable = False
    if CLOCK_QUALITY_RANK[event.source_clock_quality] < CLOCK_QUALITY_RANK[minimum_source_clock_quality]:
        reasons.add("CLOCK_QUALITY_INSUFFICIENT")
        source_usable = False
    if max_uncertainty is not None:
        if event.source_clock_uncertainty_ns is None:
            reasons.add("CLOCK_UNCERTAINTY_UNKNOWN")
            source_usable = False
        elif event.source_clock_uncertainty_ns > max_uncertainty:
            reasons.add("CLOCK_UNCERTAINTY_EXCEEDED")
            source_usable = False

    age_basis = "UNRESOLVED"
    age: int | None = None
    if source_usable and event.source_time_ns is not None:
        delta = reference_time - event.source_time_ns
        if delta < 0:
            reasons.add("NEGATIVE_AGE")
        else:
            age_basis = "SOURCE_TIME"
            age = delta
    elif allow_receipt_time_fallback:
        if event.receipt_time_ns is None:
            reasons.add("RECEIPT_TIME_MISSING")
        elif event.receipt_clock_id != reference_clock:
            reasons.add("RECEIPT_CLOCK_MISMATCH")
        else:
            delta = reference_time - event.receipt_time_ns
            if delta < 0:
                reasons.add("NEGATIVE_AGE")
            else:
                reasons.add("RECEIPT_FALLBACK_USED")
                age_basis = "RECEIPT_TIME"
                age = delta

    if age is not None and age > maximum_age:
        reasons.add("MAX_AGE_EXCEEDED")
        stale_reasons.add("MAX_AGE_EXCEEDED")
    if age is None:
        reasons.add("AGE_UNRESOLVED")

    if stale_reasons:
        status = "STALE"
    elif age is None:
        status = "UNKNOWN"
    else:
        status = "FRESH"

    return ObservationFreshnessAssessment(
        workspace_id=workspace_id,
        scope_id=scope_id,
        subject_id=subject_id,
        state_namespace=state_namespace,
        observation_id=observation_id,
        observation_fingerprint=observation_fingerprint,
        state_claim_id=state_claim_id,
        state_claim_fingerprint=state_claim_fingerprint,
        causal_event_id=event.event_id,
        causal_event_fingerprint=event.fingerprint,
        actual_boot_epoch=event.boot_epoch,
        expected_boot_epoch=expected_epoch,
        actual_problem_revision_id=actual_problem_revision_id,
        expected_problem_revision_id=expected_problem_revision_id,
        actual_external_revision_id=actual_external_revision_id,
        expected_external_revision_id=expected_external_revision_id,
        reference_time_ns=reference_time,
        reference_clock_id=reference_clock,
        max_age_ns=maximum_age,
        minimum_source_clock_quality=minimum_source_clock_quality,
        max_source_clock_uncertainty_ns=max_uncertainty,
        allow_receipt_time_fallback=bool(allow_receipt_time_fallback),
        age_basis=age_basis,
        age_ns=age,
        status=status,
        reasons=tuple(sorted(reasons)),
    )


def observation_freshness_contract() -> dict[str, Any]:
    return {
        "contract_id": OBSERVATION_FRESHNESS_CONTRACT_ID,
        "contract_version": OBSERVATION_FRESHNESS_CONTRACT_VERSION,
        "stability": OBSERVATION_FRESHNESS_STABILITY,
        "statuses": list(FRESHNESS_STATUSES),
        "age_bases": list(FRESHNESS_AGE_BASES),
        "reasons": list(FRESHNESS_REASONS),
        "reference_time": "EXPLICIT_INTEGER_NANOSECONDS_NEVER_IMPLICIT_HOST_NOW",
        "source_age": "REQUIRES_EXACT_REFERENCE_CLOCK_ID_AND_MINIMUM_CLOCK_QUALITY",
        "clock_uncertainty": "OPTIONAL_EXPLICIT_MAXIMUM_POLICY_FAILS_SOURCE_AGE_WHEN_UNKNOWN_OR_EXCEEDED",
        "receipt_fallback": "OPTIONAL_AND_EXPLICITLY_MARKED_WEAKER_AGE_BASIS",
        "boot_epoch": "EXPECTED_EPOCH_MISMATCH_IS_STALE",
        "problem_revision": "EXPECTED_NONEMPTY_REVISION_MISMATCH_IS_STALE",
        "external_revision": "EXPECTED_NONEMPTY_REVISION_MISMATCH_IS_STALE",
        "negative_age": "UNKNOWN_UNLESS_AN_INDEPENDENT_DEFINITIVE_STALE_REASON_EXISTS",
        "unresolved_age": "UNKNOWN_UNLESS_AN_INDEPENDENT_DEFINITIVE_STALE_REASON_EXISTS",
        "freshness_grants_fact_authority": False,
        "freshness_grants_effect_authority": False,
        "freshness_elevates_observation_authority": False,
        "freshness_mutates_observation": False,
        "freshness_mutates_state_claim": False,
        "freshness_is_universal_admission": False,
        "consumer_policy": "DOWNSTREAM_CONSUMERS_MUST_EXPLICITLY_REQUIRE_AND_INTERPRET_ASSESSMENT",
        "assessment_id": "EXACT_INPUT_POLICY_AND_REFERENCE_CONTEXT",
        "assessment_fingerprint": "ASSESSMENT_ID_PLUS_COMPUTED_STATUS_AGE_BASIS_AGE_AND_REASONS",
        "portable_integer_range": f"0..{PORTABLE_U63_MAX}",
        "parallel_truth_table": "NONE",
    }


__all__ = [
    "OBSERVATION_FRESHNESS_CONTRACT_ID",
    "OBSERVATION_FRESHNESS_CONTRACT_VERSION",
    "OBSERVATION_FRESHNESS_STABILITY",
    "FRESHNESS_STATUSES",
    "FRESHNESS_AGE_BASES",
    "FRESHNESS_REASONS",
    "ObservationFreshnessAssessment",
    "assess_freshness",
    "observation_freshness_contract",
]
