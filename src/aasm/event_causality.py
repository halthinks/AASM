from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

from .semantic_result import semantic_fingerprint


EVENT_CAUSALITY_CONTRACT_ID = "aasm.event.causality.v1"
EVENT_CAUSALITY_CONTRACT_VERSION = "0.1.0"
EVENT_CAUSALITY_STABILITY = "FOUNDATION_EXPERIMENTAL"
PORTABLE_U63_MAX = (1 << 63) - 1

CLOCK_QUALITIES = (
    "UNKNOWN",
    "UNSYNCHRONIZED",
    "MONOTONIC_LOCAL",
    "SYNCHRONIZED",
    "TRACEABLE",
)
CLOCK_QUALITY_RANK = {name: index for index, name in enumerate(CLOCK_QUALITIES)}
CAUSAL_RELATIONS = (
    "CAUSED_BY",
    "HAPPENS_BEFORE",
    "CONCURRENT_WITH",
    "ORDER_UNKNOWN",
)
_SYMMETRIC_RELATIONS = {"CONCURRENT_WITH", "ORDER_UNKNOWN"}


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


def _optional_ns(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    return _portable_int(value, name)


@dataclass(frozen=True)
class CausalEventIdentity:
    workspace_id: str
    scope_id: str
    subject_id: str
    node_id: str
    boot_epoch: int
    sequence: int
    event_kind: str
    object_kind: str
    object_id: str
    source_time_ns: int | None = None
    source_clock_id: str = ""
    source_clock_quality: str = "UNKNOWN"
    source_clock_uncertainty_ns: int | None = None
    receipt_time_ns: int | None = None
    receipt_clock_id: str = ""
    problem_revision_id: str = ""
    external_revision_id: str = ""
    event_id: str = ""
    contract_id: str = EVENT_CAUSALITY_CONTRACT_ID
    contract_version: str = EVENT_CAUSALITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "node_id",
            "event_kind",
            "object_kind",
            "object_id",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != EVENT_CAUSALITY_CONTRACT_ID or self.contract_version != EVENT_CAUSALITY_CONTRACT_VERSION:
            raise ValueError("unsupported causal-event contract")
        object.__setattr__(self, "boot_epoch", _portable_int(self.boot_epoch, "boot_epoch", minimum=1))
        object.__setattr__(self, "sequence", _portable_int(self.sequence, "sequence"))
        if self.source_clock_quality not in CLOCK_QUALITIES:
            raise ValueError(f"invalid source_clock_quality: {self.source_clock_quality}")
        source_time = _optional_ns(self.source_time_ns, "source_time_ns")
        receipt_time = _optional_ns(self.receipt_time_ns, "receipt_time_ns")
        uncertainty = _optional_ns(self.source_clock_uncertainty_ns, "source_clock_uncertainty_ns")
        object.__setattr__(self, "source_time_ns", source_time)
        object.__setattr__(self, "receipt_time_ns", receipt_time)
        object.__setattr__(self, "source_clock_uncertainty_ns", uncertainty)
        object.__setattr__(self, "source_clock_id", _optional(self.source_clock_id))
        object.__setattr__(self, "receipt_clock_id", _optional(self.receipt_clock_id))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        if source_time is not None and not self.source_clock_id:
            raise ValueError("source_clock_id is required when source_time_ns is present")
        if uncertainty is not None and source_time is None:
            raise ValueError("source_clock_uncertainty_ns requires source_time_ns")
        if receipt_time is not None and not self.receipt_clock_id:
            raise ValueError("receipt_clock_id is required when receipt_time_ns is present")
        if not self.event_id:
            object.__setattr__(self, "event_id", f"causal-event-{semantic_fingerprint(self.local_identity_payload())[:24]}")
        else:
            object.__setattr__(self, "event_id", _required(self.event_id, "event_id"))

    def local_identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "node_id": self.node_id,
            "boot_epoch": self.boot_epoch,
            "sequence": self.sequence,
        }

    def identity_payload(self) -> dict[str, Any]:
        return {
            **self.local_identity_payload(),
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "event_kind": self.event_kind,
            "object_kind": self.object_kind,
            "object_id": self.object_id,
            "source_time_ns": self.source_time_ns,
            "source_clock_id": self.source_clock_id,
            "source_clock_quality": self.source_clock_quality,
            "source_clock_uncertainty_ns": self.source_clock_uncertainty_ns,
            "receipt_time_ns": self.receipt_time_ns,
            "receipt_clock_id": self.receipt_clock_id,
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"event_id": self.event_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"event_id": self.event_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CausalEventIdentity":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass(frozen=True)
class CausalRelation:
    relation: str
    subject_event_id: str
    subject_event_fingerprint: str
    reference_event_id: str
    reference_event_fingerprint: str
    relation_id: str = ""
    contract_id: str = EVENT_CAUSALITY_CONTRACT_ID
    contract_version: str = EVENT_CAUSALITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != EVENT_CAUSALITY_CONTRACT_ID or self.contract_version != EVENT_CAUSALITY_CONTRACT_VERSION:
            raise ValueError("unsupported causal-relation contract")
        if self.relation not in CAUSAL_RELATIONS:
            raise ValueError(f"invalid causal relation: {self.relation}")
        for name in (
            "subject_event_id",
            "subject_event_fingerprint",
            "reference_event_id",
            "reference_event_fingerprint",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.subject_event_id == self.reference_event_id:
            raise ValueError("causal relation cannot relate an event to itself")
        if self.relation in _SYMMETRIC_RELATIONS and self.reference_event_id < self.subject_event_id:
            subject_id = self.subject_event_id
            subject_fp = self.subject_event_fingerprint
            object.__setattr__(self, "subject_event_id", self.reference_event_id)
            object.__setattr__(self, "subject_event_fingerprint", self.reference_event_fingerprint)
            object.__setattr__(self, "reference_event_id", subject_id)
            object.__setattr__(self, "reference_event_fingerprint", subject_fp)
        if not self.relation_id:
            object.__setattr__(self, "relation_id", f"causal-relation-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "relation_id", _required(self.relation_id, "relation_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "relation": self.relation,
            "subject_event_id": self.subject_event_id,
            "subject_event_fingerprint": self.subject_event_fingerprint,
            "reference_event_id": self.reference_event_id,
            "reference_event_fingerprint": self.reference_event_fingerprint,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"relation_id": self.relation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"relation_id": self.relation_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CausalRelation":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


def event_causality_contract() -> dict[str, Any]:
    return {
        "contract_id": EVENT_CAUSALITY_CONTRACT_ID,
        "contract_version": EVENT_CAUSALITY_CONTRACT_VERSION,
        "stability": EVENT_CAUSALITY_STABILITY,
        "clock_qualities": list(CLOCK_QUALITIES),
        "relations": list(CAUSAL_RELATIONS),
        "portable_integer_range": f"0..{PORTABLE_U63_MAX}",
        "local_event_identity": "NODE_ID_PLUS_BOOT_EPOCH_PLUS_MONOTONIC_LOCAL_SEQUENCE",
        "event_fingerprint": "LOCAL_IDENTITY_PLUS_EXACT_OBJECT_CONTEXT_TIME_AND_REVISION_FIELDS",
        "boot_epoch": "EXPLICIT_REBOOT_FENCE_SEQUENCE_MAY_RESTART_ONLY_UNDER_NEW_BOOT_EPOCH",
        "sequence": "LOCAL_MONOTONIC_IDENTITY_NOT_GLOBAL_TOTAL_ORDER",
        "source_time": "EXPLICIT_INTEGER_NANOSECONDS_WITH_CLOCK_ID_AND_QUALITY",
        "receipt_time": "EXPLICIT_INTEGER_NANOSECONDS_CONTEXT_ONLY_NOT_SOURCE_ORDER",
        "host_wall_clock": "NOT_UNIVERSAL_TRUTH_AND_NEVER_IMPLICITLY_CAPTURED",
        "receipt_order_implies_source_order": False,
        "relation_transitive_closure": "NOT_INFERRED_BY_V1_FOUNDATION",
        "relation_grants_fact_authority": False,
        "relation_grants_effect_authority": False,
        "event_identity_grants_authority": False,
        "event_log_role": "CAUSAL_IDENTITY_OVER_EXISTING_DURABLE_OBJECTS_NOT_SECOND_AASM_EVENT_LEDGER",
        "portable_time": "NONNEGATIVE_INTEGER_NANOSECONDS_WITH_63_BIT_MAXIMUM",
        "portable_identity": "EXPLICIT_ENUMS_AND_LANGUAGE_INDEPENDENT_SEMANTIC_FINGERPRINTS",
        "python_object_identity_in_identity": False,
        "host_wall_clock_in_identity": False,
        "parallel_event_ledger": "NONE",
        "parallel_truth_table": "NONE",
    }


__all__ = [
    "EVENT_CAUSALITY_CONTRACT_ID",
    "EVENT_CAUSALITY_CONTRACT_VERSION",
    "EVENT_CAUSALITY_STABILITY",
    "PORTABLE_U63_MAX",
    "CLOCK_QUALITIES",
    "CLOCK_QUALITY_RANK",
    "CAUSAL_RELATIONS",
    "CausalEventIdentity",
    "CausalRelation",
    "event_causality_contract",
]
