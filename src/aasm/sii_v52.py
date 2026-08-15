from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .resource_governance import ResourceDemandEstimate
from .resource_routing import ResourceAwareCandidate
from .semantic_result import semantic_fingerprint
from .sii import StructuredProposal


SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID = "aasm.sii.resource-aware-proposal.v1"
SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_VERSION = "0.1.0"
SII_RESOURCE_AWARE_PROPOSAL_STABILITY = "FOUNDATION_EXPERIMENTAL"


@dataclass(frozen=True)
class ResourceAwareStructuredProposal:
    """v0.52 successor envelope over the frozen SII StructuredProposal.

    The parent proposal remains byte/semantic compatible with v0.47-v0.51.
    Resource-aware identity is additive: the v0.52 fingerprint binds the exact
    parent proposal fingerprint plus resource bids and decision-quality claims.
    """

    proposal: StructuredProposal | Mapping[str, Any]
    resource_demands: tuple[ResourceDemandEstimate | Mapping[str, Any], ...] = ()
    expected_correctness: float | None = None
    expected_evidence_quality: float | None = None
    expected_progress: float | None = None
    expected_wall_time_seconds: float | None = None
    expected_monetary_cost: float | None = None
    expected_scarce_expert_usage: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        parent = self.proposal if isinstance(self.proposal, StructuredProposal) else StructuredProposal.from_dict(self.proposal)
        demands = tuple(
            item if isinstance(item, ResourceDemandEstimate) else ResourceDemandEstimate(**dict(item))
            for item in self.resource_demands
        )
        object.__setattr__(self, "proposal", parent)
        object.__setattr__(self, "resource_demands", demands)

        for name in ("expected_correctness", "expected_evidence_quality", "expected_progress"):
            value = getattr(self, name)
            if value is not None and not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be between 0 and 1")
        for name in ("expected_wall_time_seconds", "expected_monetary_cost", "expected_scarce_expert_usage"):
            value = getattr(self, name)
            if value is not None and float(value) < 0:
                raise ValueError(f"{name} must be non-negative")

    @property
    def proposer_id(self) -> str:
        return self.proposal.proposer_id

    @property
    def scope_id(self) -> str:
        return self.proposal.scope_id

    @property
    def parent_proposal_id(self) -> str:
        return self.proposal.proposal_id

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
            "contract_version": SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_VERSION,
            "parent_proposal_id": self.proposal.proposal_id,
            "parent_proposal_fingerprint": self.proposal.fingerprint,
            "resource_demands": [
                {
                    "resource_class": row.resource_class,
                    "resource_id": row.resource_id,
                    "amount": row.amount,
                    "upper_bound": row.upper_bound,
                    "unit": row.unit,
                    "confidence": row.confidence,
                    "metadata": dict(row.metadata),
                }
                for row in self.resource_demands
            ],
            "expected_correctness": self.expected_correctness,
            "expected_evidence_quality": self.expected_evidence_quality,
            "expected_progress": self.expected_progress,
            "expected_wall_time_seconds": self.expected_wall_time_seconds,
            "expected_monetary_cost": self.expected_monetary_cost,
            "expected_scarce_expert_usage": self.expected_scarce_expert_usage,
            "metadata": dict(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def resource_aware_proposal_id(self) -> str:
        return f"sii-v52-proposal-{self.fingerprint[:20]}"

    def to_routing_candidate(self) -> ResourceAwareCandidate:
        """Compile the proposal into the deterministic resource-routing IR.

        Missing quality estimates fail closed to zero rather than being inferred
        from proposer confidence. Resource routing must not silently equate
        confidence with correctness, evidence quality, or expected progress.
        """

        return ResourceAwareCandidate(
            candidate_id=self.resource_aware_proposal_id,
            correctness=float(self.expected_correctness or 0.0),
            evidence_quality=float(self.expected_evidence_quality or 0.0),
            expected_progress=float(self.expected_progress or 0.0),
            wall_time_seconds=float(self.expected_wall_time_seconds or 0.0),
            monetary_cost=float(self.expected_monetary_cost or 0.0),
            scarce_expert_usage=float(self.expected_scarce_expert_usage or 0.0),
            demands=tuple(self.resource_demands),
            metadata={
                "parent_proposal_id": self.parent_proposal_id,
                "parent_proposal_fingerprint": self.proposal.fingerprint,
                "proposer_id": self.proposer_id,
                "scope_id": self.scope_id,
                **dict(self.metadata),
            },
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_aware_proposal_id": self.resource_aware_proposal_id,
            "proposal": self.proposal.to_dict(),
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ResourceAwareStructuredProposal":
        payload = dict(data)
        payload.pop("resource_aware_proposal_id", None)
        payload.pop("fingerprint", None)
        payload.pop("contract_id", None)
        payload.pop("contract_version", None)
        payload.pop("parent_proposal_id", None)
        payload.pop("parent_proposal_fingerprint", None)
        return cls(**payload)


__all__ = [
    "SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID",
    "SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_VERSION",
    "SII_RESOURCE_AWARE_PROPOSAL_STABILITY",
    "ResourceAwareStructuredProposal",
]
