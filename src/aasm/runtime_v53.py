from __future__ import annotations

from typing import Iterable

from ._runtime_v53_authority import ScopedAuthorityRuntimeMixin
from .resource_governance import ResourceCapacity, ResourceObservation
from .resource_routing import ResourceAwareCandidate, ResourceRoutingPolicy
from .runtime_v52 import AASMEngine as V52Engine
from .scoped_authority import AuthorityRequest, SCOPED_AUTHORITY_CONTRACT_ID
from .semantic_result import semantic_fingerprint
from .sii_v52 import ResourceAwareStructuredProposal


RESOURCE_AUTHORITY_CAPABILITIES = {
    "capacity_register": "resource.capacity.register",
    "observe": "resource.observe",
    "reserve": "resource.reserve",
    "reestimate": "resource.reestimate",
    "release": "resource.release",
    "settle": "resource.settle",
}


class AASMEngine(ScopedAuthorityRuntimeMixin, V52Engine):
    """Experimental v0.53 runtime: scoped identity/authority enforced over v0.52."""

    def _authorize_resource_action(
        self,
        *,
        actor_principal_id: str | None,
        workspace_id: str | None,
        scope_id: str | None,
        capability: str,
        at_time: float,
    ) -> dict:
        if not actor_principal_id or not workspace_id or not scope_id:
            raise PermissionError(
                "v0.53 resource mutation requires actor_principal_id, workspace_id, and scope_id"
            )
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                workspace_id,
                scope_id,
                capability,
                at_time=at_time,
                machine_id=self.snapshot.machine_id,
            ),
            reason=f"v0.53 resource authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"v0.53 resource authority denied {capability}: {result['decision']['reason']}"
            )
        return result

    def _record_resource_authority_binding(
        self,
        *,
        action: str,
        actor_principal_id: str,
        workspace_id: str,
        scope_id: str,
        authority_decision_evidence_id: str,
        result_evidence_ids: Iterable[str],
    ) -> str:
        result_ids = tuple(sorted(set(map(str, result_evidence_ids))))
        document = {
            "action": action,
            "actor_principal_id": actor_principal_id,
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "authority_decision_evidence_id": authority_decision_evidence_id,
            "result_evidence_ids": list(result_ids),
            "resource_state_granted_authority": False,
        }
        object_id = f"resource-enforcement-{semantic_fingerprint(document)[:24]}"
        return self._record_authority_document(
            record_type="resource_enforcement",
            object_id=object_id,
            document=document,
            source=SCOPED_AUTHORITY_CONTRACT_ID,
            derived_from=[authority_decision_evidence_id, *result_ids],
            reason=f"v0.53 resource authority binding recorded: {action}",
        )

    def register_resource_capacity(
        self,
        capacity: ResourceCapacity,
        *,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ) -> dict:
        authorization = self._authorize_resource_action(
            actor_principal_id=actor_principal_id,
            workspace_id=capacity.workspace_id,
            scope_id=capacity.scope_id,
            capability=RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],
            at_time=at_time,
        )
        result = super().register_resource_capacity(capacity)
        binding_id = self._record_resource_authority_binding(
            action="capacity_register",
            actor_principal_id=str(actor_principal_id),
            workspace_id=str(capacity.workspace_id),
            scope_id=str(capacity.scope_id),
            authority_decision_evidence_id=authorization["evidence_id"],
            result_evidence_ids=[result["evidence_id"]],
        )
        return {
            **result,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "authority_binding_evidence_id": binding_id,
        }

    def record_resource_observation(
        self,
        observation: ResourceObservation,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ) -> dict:
        authorization = self._authorize_resource_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=RESOURCE_AUTHORITY_CAPABILITIES["observe"],
            at_time=at_time,
        )
        result = super().record_resource_observation(
            observation,
            workspace_id=workspace_id,
            scope_id=scope_id,
        )
        binding_id = self._record_resource_authority_binding(
            action="observe",
            actor_principal_id=str(actor_principal_id),
            workspace_id=str(workspace_id),
            scope_id=str(scope_id),
            authority_decision_evidence_id=authorization["evidence_id"],
            result_evidence_ids=[result["evidence_id"], result["capacity_evidence_id"]],
        )
        return {
            **result,
            "authority_decision_evidence_id": authorization["evidence_id"],
            "authority_binding_evidence_id": binding_id,
        }

    def select_and_reserve_resource_candidate(
        self,
        candidates: Iterable[ResourceAwareCandidate],
        policy: ResourceRoutingPolicy,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        derived_from=(),
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ) -> dict:
        authorization = self._authorize_resource_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=RESOURCE_AUTHORITY_CAPABILITIES["reserve"],
            at_time=at_time,
        )
        result = super().select_and_reserve_resource_candidate(
            candidates,
            policy,
            workspace_id=workspace_id,
            scope_id=scope_id,
            derived_from=tuple((*map(str, derived_from), authorization["evidence_id"])),
        )
        return {**result, "authority_decision_evidence_id": authorization["evidence_id"]}

    def settle_resource_reservation(
        self,
        reservation_id: str,
        actual_consumption,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        evidence_ids=(),
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ) -> dict:
        authorization = self._authorize_resource_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=RESOURCE_AUTHORITY_CAPABILITIES["settle"],
            at_time=at_time,
        )
        result = super().settle_resource_reservation(
            reservation_id,
            actual_consumption,
            workspace_id=workspace_id,
            scope_id=scope_id,
            evidence_ids=tuple((*map(str, evidence_ids), authorization["evidence_id"])),
        )
        return {**result, "authority_decision_evidence_id": authorization["evidence_id"]}

    def reestimate_resource_reservation(
        self,
        reservation_id: str,
        revised_allocations,
        policy: ResourceRoutingPolicy,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        evidence_ids=(),
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ) -> dict:
        authorization = self._authorize_resource_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=RESOURCE_AUTHORITY_CAPABILITIES["reestimate"],
            at_time=at_time,
        )
        result = super().reestimate_resource_reservation(
            reservation_id,
            revised_allocations,
            policy,
            workspace_id=workspace_id,
            scope_id=scope_id,
            evidence_ids=tuple((*map(str, evidence_ids), authorization["evidence_id"])),
        )
        return {**result, "authority_decision_evidence_id": authorization["evidence_id"]}

    def release_resource_reservation(
        self,
        reservation_id: str,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        evidence_ids=(),
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ) -> dict:
        authorization = self._authorize_resource_action(
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=RESOURCE_AUTHORITY_CAPABILITIES["release"],
            at_time=at_time,
        )
        result = super().release_resource_reservation(
            reservation_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            evidence_ids=tuple((*map(str, evidence_ids), authorization["evidence_id"])),
        )
        return {**result, "authority_decision_evidence_id": authorization["evidence_id"]}

    def route_resource_aware_sii_proposals(
        self,
        proposal_ids: Iterable[str],
        policy: ResourceRoutingPolicy,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        derived_from=(),
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ) -> dict:
        report = self.resource_aware_sii_proposal_report(
            workspace_id=workspace_id,
            scope_id=scope_id,
        )
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
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )
        return {
            **result,
            "proposal_ids": list(ids),
            "proposal_evidence_ids": proposal_evidence_ids,
        }


__all__ = ["AASMEngine", "RESOURCE_AUTHORITY_CAPABILITIES"]
