from __future__ import annotations

from copy import deepcopy
from math import isinf
from typing import Any, Iterable, Mapping

from ._runtime_v52_resources import ResourceGovernanceRuntimeMixin, _capacity_from_dict
from .resource_routing import (
    RESOURCE_ROUTING_CONTRACT_ID,
    ResourceAwareCandidate,
    ResourceRoutingPolicy,
    planning_allocatable,
)
from .runtime_v51 import AASMEngine as V51Engine
from .sii_v52 import (
    SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
    ResourceAwareStructuredProposal,
)


_RESOURCE_RECORD_TYPE = "aasm_resource_record_type"
_RESOURCE_DOCUMENT = "document"


def _finite_or_label(value: float | None) -> float | str | None:
    if value is None:
        return None
    if isinf(value):
        return "UNBOUNDED"
    return float(value)


def _routing_policy_document(policy: ResourceRoutingPolicy) -> dict[str, Any]:
    return {
        "min_correctness": policy.min_correctness,
        "min_evidence_quality": policy.min_evidence_quality,
        "min_expected_progress": policy.min_expected_progress,
        "preserve_protected_reserve": policy.preserve_protected_reserve,
        "prefer_lower_scarce_expert_usage": policy.prefer_lower_scarce_expert_usage,
        "prefer_lower_monetary_cost": policy.prefer_lower_monetary_cost,
        "prefer_lower_wall_time": policy.prefer_lower_wall_time,
        "constrain_with_observed_remaining": policy.constrain_with_observed_remaining,
        "accepted_measurement_authorities": list(policy.accepted_measurement_authorities),
        "min_observation_confidence": policy.min_observation_confidence,
        "max_observation_freshness_seconds": policy.max_observation_freshness_seconds,
    }


class AASMEngine(ResourceGovernanceRuntimeMixin, V51Engine):
    """Experimental v0.52 resource-governed decision runtime over v0.51."""

    def _durable_parent_sii_proposal(self, item: ResourceAwareStructuredProposal) -> dict[str, Any]:
        projection = self._governed_sii().legacy.projection()
        try:
            parent = projection["proposals"][item.parent_proposal_id]
        except KeyError:
            raise KeyError(
                f"resource-aware proposal requires an already durable governed parent SII proposal: {item.parent_proposal_id}"
            ) from None
        durable = parent["proposal"]
        if durable.get("fingerprint") != item.proposal.fingerprint:
            raise ValueError("resource-aware proposal parent fingerprint does not match durable SII proposal")
        if durable.get("proposer_id") != item.proposer_id:
            raise ValueError("resource-aware proposal proposer does not match durable SII proposal")
        if durable.get("scope_id") != item.scope_id:
            raise ValueError("resource-aware proposal scope does not match durable SII proposal")
        return parent

    def submit_resource_aware_sii_proposal(
        self,
        proposal: ResourceAwareStructuredProposal | Mapping[str, Any],
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        derived_from=(),
    ) -> dict[str, Any]:
        item = proposal if isinstance(proposal, ResourceAwareStructuredProposal) else ResourceAwareStructuredProposal.from_dict(proposal)
        effective_scope_id = scope_id or item.scope_id
        self._validate_resource_context(workspace_id=workspace_id, scope_id=effective_scope_id)
        if item.scope_id != effective_scope_id:
            raise PermissionError("resource-aware proposal scope does not match submission scope")
        parent = self._durable_parent_sii_proposal(item)

        document = {
            "resource_aware_proposal_id": item.resource_aware_proposal_id,
            "workspace_id": workspace_id,
            "scope_id": effective_scope_id,
            "parent_proposal_id": item.parent_proposal_id,
            "parent_proposal_evidence_id": parent["evidence_id"],
            "proposal": item.to_dict(),
        }
        lineage = tuple(sorted(set((*map(str, derived_from), str(parent["evidence_id"])))))
        evidence_id = self._record_resource_document(
            record_type="resource_aware_proposal",
            object_id=item.resource_aware_proposal_id,
            document=document,
            source=SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
            derived_from=lineage,
        )
        return {"proposal": deepcopy(document), "evidence_id": evidence_id}

    def resource_aware_sii_proposal_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate_resource_context(workspace_id=workspace_id, scope_id=scope_id)
        proposals: dict[str, dict[str, Any]] = {}
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_RESOURCE_RECORD_TYPE) != "resource_aware_proposal":
                continue
            document = metadata.get(_RESOURCE_DOCUMENT)
            if not isinstance(document, dict):
                continue
            if document.get("workspace_id") != workspace_id or document.get("scope_id") != scope_id:
                continue
            proposal_id = str(document.get("resource_aware_proposal_id") or metadata.get("object_id") or "")
            proposals[proposal_id] = {
                "document": deepcopy(document),
                "evidence_id": row.get("evidence_id"),
            }
        return {
            "contract_id": SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "proposals": proposals,
        }

    def select_and_reserve_resource_candidate(
        self,
        candidates: Iterable[ResourceAwareCandidate],
        policy: ResourceRoutingPolicy,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        derived_from=(),
    ) -> dict[str, Any]:
        before = self.resource_governance_report(workspace_id=workspace_id, scope_id=scope_id)
        capacity_snapshot: dict[str, dict[str, Any]] = {}
        for resource_id, document in sorted(before["capacities"].items()):
            capacity = _capacity_from_dict(document)
            observation = document.get("latest_observation")
            capacity_snapshot[resource_id] = {
                "resource_class": capacity.resource_class,
                "unit": capacity.unit,
                "provider": capacity.provider,
                "window_kind": capacity.window_kind.value,
                "declared_total": capacity.total,
                "consumed": capacity.consumed,
                "committed": capacity.committed,
                "protected_reserve": capacity.protected_reserve,
                "declared_allocatable": _finite_or_label(capacity.allocatable),
                "planning_allocatable": _finite_or_label(planning_allocatable(capacity, policy)),
                "resets_at": document.get("resets_at"),
                "latest_observation": deepcopy(observation),
            }

        rows = tuple(candidates)
        result = super().select_and_reserve_resource_candidate(
            rows,
            policy,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=derived_from,
        )
        transaction = result["transaction"]
        explanation = {
            "transaction_id": transaction["transaction_id"],
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "policy": _routing_policy_document(policy),
            "capacity_snapshot": capacity_snapshot,
            "decision": deepcopy(transaction["decision"]),
            "reservation": deepcopy(transaction["reservation"]),
        }
        planning_evidence_id = self._record_resource_document(
            record_type="routing_explanation",
            object_id=transaction["transaction_id"],
            document=explanation,
            source=RESOURCE_ROUTING_CONTRACT_ID,
            derived_from=[result["evidence_id"]],
        )
        return {
            **result,
            "planning_evidence_id": planning_evidence_id,
        }

    def resource_routing_explanation_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate_resource_context(workspace_id=workspace_id, scope_id=scope_id)
        explanations: dict[str, dict[str, Any]] = {}
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_RESOURCE_RECORD_TYPE) != "routing_explanation":
                continue
            document = metadata.get(_RESOURCE_DOCUMENT)
            if not isinstance(document, dict):
                continue
            if document.get("workspace_id") != workspace_id or document.get("scope_id") != scope_id:
                continue
            transaction_id = str(document["transaction_id"])
            explanations[transaction_id] = {
                "document": deepcopy(document),
                "evidence_id": row.get("evidence_id"),
                "derived_from": list(row.get("derived_from") or []),
            }
        return {
            "contract_id": RESOURCE_ROUTING_CONTRACT_ID,
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "explanations": explanations,
        }

    def resource_consumption_calibration_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        report = self.resource_governance_report(workspace_id=workspace_id, scope_id=scope_id)
        aggregates: dict[str, dict[str, float | int]] = {}
        samples: list[dict[str, Any]] = []
        for settlement_id, settlement in sorted(report["settlements"].items()):
            reservation_id = str(settlement["reservation_id"])
            reservation = report["reservations"].get(reservation_id)
            if reservation is None:
                continue
            reserved = {str(resource_id): float(amount) for resource_id, amount in reservation.get("allocations", [])}
            actual = {str(resource_id): float(amount) for resource_id, amount in settlement.get("actual_consumption", {}).items()}
            for resource_id in sorted(set(reserved) & set(actual)):
                expected = reserved[resource_id]
                observed = actual[resource_id]
                error = observed - expected
                sample = {
                    "settlement_id": settlement_id,
                    "reservation_id": reservation_id,
                    "resource_id": resource_id,
                    "reserved": expected,
                    "actual": observed,
                    "signed_error": error,
                    "absolute_error": abs(error),
                }
                samples.append(sample)
                bucket = aggregates.setdefault(resource_id, {
                    "samples": 0,
                    "reserved_total": 0.0,
                    "actual_total": 0.0,
                    "signed_error_total": 0.0,
                    "absolute_error_total": 0.0,
                })
                bucket["samples"] = int(bucket["samples"]) + 1
                bucket["reserved_total"] = float(bucket["reserved_total"]) + expected
                bucket["actual_total"] = float(bucket["actual_total"]) + observed
                bucket["signed_error_total"] = float(bucket["signed_error_total"]) + error
                bucket["absolute_error_total"] = float(bucket["absolute_error_total"]) + abs(error)

        resources: dict[str, dict[str, Any]] = {}
        for resource_id, bucket in sorted(aggregates.items()):
            count = int(bucket["samples"])
            reserved_total = float(bucket["reserved_total"])
            resources[resource_id] = {
                **bucket,
                "mean_signed_error": float(bucket["signed_error_total"]) / count if count else 0.0,
                "mean_absolute_error": float(bucket["absolute_error_total"]) / count if count else 0.0,
                "actual_to_reserved_ratio": float(bucket["actual_total"]) / reserved_total if reserved_total else None,
            }
        return {
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "samples": samples,
            "resources": resources,
            "authority": "PERFORMANCE_EVIDENCE_ONLY",
        }

    def route_resource_aware_sii_proposals(
        self,
        proposal_ids: Iterable[str],
        policy: ResourceRoutingPolicy,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        derived_from=(),
    ) -> dict[str, Any]:
        report = self.resource_aware_sii_proposal_report(workspace_id=workspace_id, scope_id=scope_id)
        ids = tuple(sorted(set(map(str, proposal_ids))))
        if not ids:
            raise ValueError("at least one durable resource-aware proposal is required")

        candidates = []
        proposal_evidence_ids = []
        for proposal_id in ids:
            try:
                row = report["proposals"][proposal_id]
            except KeyError:
                raise KeyError(f"unknown resource-aware proposal in access context: {proposal_id}") from None
            item = ResourceAwareStructuredProposal.from_dict(row["document"]["proposal"])
            self._durable_parent_sii_proposal(item)
            candidates.append(item.to_routing_candidate())
            proposal_evidence_ids.append(str(row["evidence_id"]))

        lineage = tuple(sorted(set((*map(str, derived_from), *proposal_evidence_ids))))
        result = self.select_and_reserve_resource_candidate(
            candidates,
            policy,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=lineage,
        )
        return {
            **result,
            "proposal_ids": list(ids),
            "proposal_evidence_ids": proposal_evidence_ids,
        }


__all__ = ["AASMEngine"]
