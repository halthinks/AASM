from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from ._runtime_v52_resources import ResourceGovernanceRuntimeMixin
from .resource_routing import ResourceRoutingPolicy
from .runtime_v51 import AASMEngine as V51Engine
from .sii_v52 import (
    SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
    ResourceAwareStructuredProposal,
)


_RESOURCE_RECORD_TYPE = "aasm_resource_record_type"
_RESOURCE_DOCUMENT = "document"


class AASMEngine(ResourceGovernanceRuntimeMixin, V51Engine):
    """Experimental v0.52 resource-governed decision runtime over v0.51."""

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

        document = {
            "resource_aware_proposal_id": item.resource_aware_proposal_id,
            "workspace_id": workspace_id,
            "scope_id": effective_scope_id,
            "proposal": item.to_dict(),
        }
        evidence_id = self._record_resource_document(
            record_type="resource_aware_proposal",
            object_id=item.resource_aware_proposal_id,
            document=document,
            source=SII_RESOURCE_AWARE_PROPOSAL_CONTRACT_ID,
            derived_from=derived_from,
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
