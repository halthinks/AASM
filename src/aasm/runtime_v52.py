from __future__ import annotations

from copy import deepcopy
from math import isinf
from typing import Any, Iterable, Mapping

from ._runtime_v52_resources import ResourceGovernanceRuntimeMixin, _capacity_from_dict
from .evidence import EvidenceRecord
from .multi_objective import (
    FRONTIER_CONTRACT_ID,
    MULTI_OBJECTIVE_CONTRACT_ID,
    MultiObjectiveProblem,
    solve_exact_finite_pareto_frontier,
    solve_lexicographic_finite,
)
from .resource_routing import (
    RESOURCE_ROUTING_CONTRACT_ID,
    ResourceAwareCandidate,
    ResourceRoutingPolicy,
    planning_allocatable,
    resource_candidate_objective_vector,
    resource_candidate_pareto_frontier,
)
from .runtime_v51 import AASMEngine as V51Engine
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .sii_v52 import (
    SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
    ResourceAwareStructuredProposal,
)


_RESOURCE_RECORD_TYPE = "aasm_resource_record_type"
_RESOURCE_DOCUMENT = "document"
_MULTI_OBJECTIVE_RECORD_TYPE = "aasm_multi_objective_record_type"
_MULTI_OBJECTIVE_DOCUMENT = "document"


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
        "prefer_lower_provider_quota_burn": policy.prefer_lower_provider_quota_burn,
        "prefer_lower_scarce_expert_usage": policy.prefer_lower_scarce_expert_usage,
        "prefer_lower_monetary_cost": policy.prefer_lower_monetary_cost,
        "prefer_lower_wall_time": policy.prefer_lower_wall_time,
        "constrain_with_observed_remaining": policy.constrain_with_observed_remaining,
        "accepted_measurement_authorities": list(policy.accepted_measurement_authorities),
        "min_observation_confidence": policy.min_observation_confidence,
        "max_observation_freshness_seconds": policy.max_observation_freshness_seconds,
        "objectives": [row.to_dict() for row in policy.objectives],
    }


class AASMEngine(ResourceGovernanceRuntimeMixin, V51Engine):
    """Experimental v0.52 resource-governed and multi-objective runtime over v0.51."""

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
        candidate_objectives = {
            row.candidate_id: resource_candidate_objective_vector(row)
            for row in sorted(rows, key=lambda value: value.candidate_id)
        }
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
            "candidate_objectives": candidate_objectives,
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

    def record_resource_candidate_pareto_frontier(
        self,
        candidates: Iterable[ResourceAwareCandidate],
        policy: ResourceRoutingPolicy,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        derived_from=(),
    ) -> dict[str, Any]:
        report = self.resource_governance_report(workspace_id=workspace_id, scope_id=scope_id)
        capacities = [_capacity_from_dict(document) for _, document in sorted(report["capacities"].items())]
        rows = tuple(candidates)
        if not rows:
            raise ValueError("at least one resource-aware candidate is required")
        frontier = resource_candidate_pareto_frontier(rows, capacities, policy)
        seed = {
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "policy": _routing_policy_document(policy),
            "candidate_vectors": {
                row.candidate_id: resource_candidate_objective_vector(row)
                for row in sorted(rows, key=lambda value: value.candidate_id)
            },
            "frontier": deepcopy(frontier),
        }
        frontier_id = f"resource-candidate-frontier-{semantic_fingerprint(seed)[:20]}"
        document = {"frontier_id": frontier_id, **seed}
        evidence_id = self._record_resource_document(
            record_type="candidate_pareto_frontier",
            object_id=frontier_id,
            document=document,
            source=RESOURCE_ROUTING_CONTRACT_ID,
            derived_from=derived_from,
        )
        return {
            "frontier": document,
            "evidence_id": evidence_id,
            "authority": "EVIDENCE_ONLY",
        }

    def resource_candidate_pareto_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate_resource_context(workspace_id=workspace_id, scope_id=scope_id)
        frontiers: dict[str, dict[str, Any]] = {}
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_RESOURCE_RECORD_TYPE) != "candidate_pareto_frontier":
                continue
            document = metadata.get(_RESOURCE_DOCUMENT)
            if not isinstance(document, dict):
                continue
            if document.get("workspace_id") != workspace_id or document.get("scope_id") != scope_id:
                continue
            frontier_id = str(document["frontier_id"])
            frontiers[frontier_id] = {
                "document": deepcopy(document),
                "evidence_id": row.get("evidence_id"),
                "derived_from": list(row.get("derived_from") or []),
            }
        return {
            "contract_id": RESOURCE_ROUTING_CONTRACT_ID,
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "frontiers": frontiers,
            "authority": "EVIDENCE_ONLY",
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

    def pareto_resource_aware_sii_proposals(
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
        result = self.record_resource_candidate_pareto_frontier(
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

    def _record_multi_objective_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        workspace_id: str | None,
        scope_id: str | None,
        derived_from=(),
    ) -> str:
        self._validate_resource_context(workspace_id=workspace_id, scope_id=scope_id)
        payload = deepcopy(dict(document))
        payload["workspace_id"] = workspace_id
        payload["scope_id"] = scope_id
        evidence_id = f"multi-objective-evidence-{semantic_fingerprint({'record_type': record_type, 'object_id': object_id, 'document': payload})[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_MULTI_OBJECTIVE_RECORD_TYPE) != record_type or metadata.get(_MULTI_OBJECTIVE_DOCUMENT) != payload:
                raise ValueError(f"multi-objective evidence collision: {evidence_id}")
            return evidence_id
        self.add_evidence(
            EvidenceRecord(
                kind="optimization_result",
                statement=canonical_semantic_json(payload),
                source=source,
                derived_from=list(sorted(set(map(str, derived_from)))),
                metadata={
                    _MULTI_OBJECTIVE_RECORD_TYPE: record_type,
                    "object_id": object_id,
                    _MULTI_OBJECTIVE_DOCUMENT: payload,
                    "authority": "EVIDENCE_ONLY",
                },
                evidence_id=evidence_id,
            ),
            reason=f"v0.52 multi-objective {record_type} recorded",
        )
        return evidence_id

    def _persist_multi_objective_basis(
        self,
        problem: MultiObjectiveProblem,
        solved: Mapping[str, Any],
        *,
        workspace_id: str | None,
        scope_id: str | None,
        derived_from=(),
    ) -> dict[str, str]:
        problem_evidence_id = self._record_multi_objective_document(
            record_type="problem",
            object_id=problem.problem_id,
            document={"problem": problem.to_dict()},
            source=MULTI_OBJECTIVE_CONTRACT_ID,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=derived_from,
        )
        pool = solved["pool"]
        pool_evidence_id = self._record_multi_objective_document(
            record_type="complete_feasible_pool",
            object_id=pool.pool_id,
            document={"pool": pool.to_dict()},
            source=MULTI_OBJECTIVE_CONTRACT_ID,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=[problem_evidence_id],
        )
        certificate = solved["enumeration_certificate"]
        if certificate.status != "PASS":
            raise ValueError("multi-objective result requires a passing finite enumeration certificate")
        enumeration_evidence_id = self._record_multi_objective_document(
            record_type="enumeration_certificate",
            object_id=certificate.certificate_id,
            document={"certificate": certificate.to_dict()},
            source=MULTI_OBJECTIVE_CONTRACT_ID,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=[pool_evidence_id],
        )
        return {
            "problem_evidence_id": problem_evidence_id,
            "pool_evidence_id": pool_evidence_id,
            "enumeration_evidence_id": enumeration_evidence_id,
        }

    def solve_lexicographic_multi_objective(
        self,
        problem: MultiObjectiveProblem,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        derived_from=(),
        max_total_states: int = 100_000,
        max_states_per_step: int = 1_000,
    ) -> dict[str, Any]:
        solved = solve_lexicographic_finite(
            problem,
            max_total_states=max_total_states,
            max_states_per_step=max_states_per_step,
        )
        result = solved["result"]
        verification = solved["verification"]
        if result.verification_status != "PASS" or verification.get("status") != "PASS":
            raise ValueError("uncertified lexicographic result is not durable-admissible")
        lineage = self._persist_multi_objective_basis(
            problem,
            solved,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=derived_from,
        )
        result_evidence_id = self._record_multi_objective_document(
            record_type="lexicographic_result",
            object_id=result.result_id,
            document={
                "problem_fingerprint": problem.fingerprint,
                "result": result.to_dict(),
                "verification": deepcopy(verification),
            },
            source=MULTI_OBJECTIVE_CONTRACT_ID,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=[lineage["enumeration_evidence_id"]],
        )
        return {
            **solved,
            **lineage,
            "result_evidence_id": result_evidence_id,
            "authority": "EVIDENCE_ONLY",
        }

    def solve_exact_pareto_multi_objective(
        self,
        problem: MultiObjectiveProblem,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        derived_from=(),
        max_total_states: int = 100_000,
        max_states_per_step: int = 1_000,
    ) -> dict[str, Any]:
        solved = solve_exact_finite_pareto_frontier(
            problem,
            max_total_states=max_total_states,
            max_states_per_step=max_states_per_step,
        )
        frontier = solved["frontier"]
        certificate = solved["certificate"]
        if (
            frontier.completeness_status != "COMPLETE"
            or certificate.status != "PASS"
            or not certificate.pairwise_nondominant
            or not certificate.exact_solution_set_match
        ):
            raise ValueError("uncertified exact Pareto frontier is not durable-admissible")
        lineage = self._persist_multi_objective_basis(
            problem,
            solved,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=derived_from,
        )
        certificate_evidence_id = self._record_multi_objective_document(
            record_type="pareto_certificate",
            object_id=certificate.certificate_id,
            document={"certificate": certificate.to_dict()},
            source=FRONTIER_CONTRACT_ID,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=[lineage["enumeration_evidence_id"]],
        )
        frontier_evidence_id = self._record_multi_objective_document(
            record_type="pareto_frontier",
            object_id=frontier.frontier_id,
            document={
                "problem_fingerprint": problem.fingerprint,
                "frontier": frontier.to_dict(),
            },
            source=FRONTIER_CONTRACT_ID,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=[certificate_evidence_id],
        )
        return {
            **solved,
            **lineage,
            "certificate_evidence_id": certificate_evidence_id,
            "frontier_evidence_id": frontier_evidence_id,
            "authority": "EVIDENCE_ONLY",
        }

    def multi_objective_report(
        self,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
    ) -> dict[str, Any]:
        self._validate_resource_context(workspace_id=workspace_id, scope_id=scope_id)
        groups: dict[str, dict[str, Any]] = {
            "problems": {},
            "complete_feasible_pools": {},
            "enumeration_certificates": {},
            "lexicographic_results": {},
            "pareto_certificates": {},
            "pareto_frontiers": {},
        }
        mapping = {
            "problem": "problems",
            "complete_feasible_pool": "complete_feasible_pools",
            "enumeration_certificate": "enumeration_certificates",
            "lexicographic_result": "lexicographic_results",
            "pareto_certificate": "pareto_certificates",
            "pareto_frontier": "pareto_frontiers",
        }
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            record_type = metadata.get(_MULTI_OBJECTIVE_RECORD_TYPE)
            bucket = mapping.get(str(record_type))
            if bucket is None:
                continue
            document = metadata.get(_MULTI_OBJECTIVE_DOCUMENT)
            if not isinstance(document, dict):
                continue
            if document.get("workspace_id") != workspace_id or document.get("scope_id") != scope_id:
                continue
            object_id = str(metadata.get("object_id") or row.get("evidence_id") or "")
            groups[bucket][object_id] = {
                "document": deepcopy(document),
                "evidence_id": row.get("evidence_id"),
                "derived_from": list(row.get("derived_from") or []),
            }
        return {
            "contract_id": MULTI_OBJECTIVE_CONTRACT_ID,
            "frontier_contract_id": FRONTIER_CONTRACT_ID,
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "authority": "EVIDENCE_ONLY",
            **groups,
        }


__all__ = ["AASMEngine"]
