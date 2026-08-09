from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import json
from typing import Any

from .profile_packages import canonical_hash


SEMANTIC_CLASSIFICATIONS = {
    "PASS",
    "LOCAL_DEFECT",
    "INFORMATION_GAP",
    "ASSUMPTION_CONFLICT",
    "EVIDENCE_CONFLICT",
    "POLICY_CONFLICT",
    "FATAL",
}
CONFLICT_CLASSIFICATIONS = {
    "ASSUMPTION_CONFLICT",
    "EVIDENCE_CONFLICT",
    "POLICY_CONFLICT",
}
PRODUCER_TYPES = {"adapter", "agent", "human", "service", "simulator", "tool", "validator", "other"}


@dataclass
class ProducerRef:
    producer_type: str
    producer_id: str
    version: str = ""
    authority: str = "UNSPECIFIED"
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.producer_type not in PRODUCER_TYPES:
            raise ValueError(f"invalid producer_type: {self.producer_type}")
        if not self.producer_id:
            raise ValueError("producer_id is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProducerRef":
        payload = deepcopy(data)
        if "type" in payload and "producer_type" not in payload:
            payload["producer_type"] = payload.pop("type")
        if "id" in payload and "producer_id" not in payload:
            payload["producer_id"] = payload.pop("id")
        return cls(**payload)


@dataclass
class SemanticResultEnvelope:
    result_id: str
    producer: ProducerRef
    subject_ids: list[str]
    classification: str
    summary: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    observations: list[dict[str, Any]] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[dict[str, Any]] = field(default_factory=list)
    proposed_conflict: dict[str, Any] | None = None
    confidence: float | None = None
    scope: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1

    def __post_init__(self):
        if not self.result_id or not self.summary.strip():
            raise ValueError("result_id and summary are required")
        if not isinstance(self.producer, ProducerRef):
            self.producer = ProducerRef.from_dict(self.producer)
        self.subject_ids = sorted(set(str(value) for value in self.subject_ids))
        if not self.subject_ids:
            raise ValueError("semantic result requires at least one subject_id")
        if self.classification not in SEMANTIC_CLASSIFICATIONS:
            raise ValueError(f"invalid semantic-result classification: {self.classification}")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        if self.schema_version != 1:
            raise ValueError("unsupported semantic-result schema_version")
        if self.classification in CONFLICT_CLASSIFICATIONS and not (
            self.proposed_conflict or self.evidence or self.observations
        ):
            raise ValueError(
                "conflict-classified semantic result requires a proposed conflict, evidence, or observations"
            )
        # Reject values that cannot survive event serialization before they
        # cross the AASM persistence boundary.
        try:
            json.dumps(self.to_dict(), sort_keys=True, default=None)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"semantic result is not JSON serializable: {exc}") from exc

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["producer"] = self.producer.to_dict()
        return out

    @property
    def fingerprint(self) -> str:
        return canonical_hash(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SemanticResultEnvelope":
        payload = deepcopy(data)
        payload["producer"] = ProducerRef.from_dict(payload["producer"])
        return cls(**payload)


def validate_semantic_result(data: SemanticResultEnvelope | dict[str, Any]) -> SemanticResultEnvelope:
    return data if isinstance(data, SemanticResultEnvelope) else SemanticResultEnvelope.from_dict(data)
