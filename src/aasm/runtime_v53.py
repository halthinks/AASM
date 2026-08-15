from __future__ import annotations

from copy import deepcopy
from typing import Iterable

from ._runtime_v53_authority import ScopedAuthorityRuntimeMixin
from .effects import EffectStatus
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

EFFECT_AUTHORITY_CAPABILITIES = {
    "authorize": "effect.authorize",
    "execute": "effect.execute",
    "reconcile": "effect.reconcile",
}

_AUTHORITY_RECORD_TYPE = "aasm_scoped_authority_record_type"
_AUTHORITY_DOCUMENT = "document"


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

    # ------------------------------------------------------------------
    # Scoped external-effect authority
    # ------------------------------------------------------------------

    def _validate_effect_scope_context(self, workspace_id: str | None, scope_id: str | None) -> None:
        if not workspace_id or not scope_id:
            raise PermissionError("v0.53 effect operations require workspace_id and scope_id")
        self._workspace_authority_inputs(workspace_id)
        scope_state = self._scope_state_for_authority()
        record = scope_state["records"].get(scope_id)
        if not record or record.get("status") != "ACTIVE":
            raise PermissionError(f"effect scope is not active: {scope_id}")

    def _effect_authority_rows(self, record_type: str, effect_id: str) -> list[dict]:
        rows = []
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_AUTHORITY_RECORD_TYPE) != record_type:
                continue
            document = metadata.get(_AUTHORITY_DOCUMENT)
            if isinstance(document, dict) and document.get("effect_id") == effect_id:
                rows.append({"evidence_id": row.get("evidence_id"), "document": deepcopy(document), "derived_from": list(row.get("derived_from") or [])})
        return rows

    def _effect_context(self, effect_id: str) -> dict:
        rows = self._effect_authority_rows("effect_proposal", effect_id)
        if not rows:
            raise PermissionError(
                "effect is not bound to a v0.53 workspace/scope; explicit migration is required"
            )
        contexts = {(row["document"]["workspace_id"], row["document"]["scope_id"]) for row in rows}
        if len(contexts) != 1:
            raise ValueError(f"effect has conflicting scoped proposal bindings: {effect_id}")
        return rows[-1]

    def _require_effect_context(self, effect_id: str, workspace_id: str | None, scope_id: str | None) -> dict:
        self._validate_effect_scope_context(workspace_id, scope_id)
        row = self._effect_context(effect_id)
        if row["document"]["workspace_id"] != workspace_id or row["document"]["scope_id"] != scope_id:
            raise PermissionError("effect operation crosses workspace/scope boundary")
        return row

    def _latest_effect_authorization(self, effect_id: str, workspace_id: str, scope_id: str) -> dict:
        rows = [
            row for row in self._effect_authority_rows("effect_authorization", effect_id)
            if row["document"]["workspace_id"] == workspace_id and row["document"]["scope_id"] == scope_id
        ]
        if not rows:
            raise PermissionError("effect has no v0.53 scoped authorization binding")
        return rows[-1]

    def _authorize_effect_action(
        self,
        *,
        effect_id: str,
        actor_principal_id: str | None,
        workspace_id: str | None,
        scope_id: str | None,
        capability: str,
        at_time: float,
    ) -> dict:
        if not actor_principal_id:
            raise PermissionError("v0.53 effect authority requires actor_principal_id")
        self._require_effect_context(effect_id, workspace_id, scope_id)
        result = self.authorize_scoped_request(
            AuthorityRequest(
                actor_principal_id,
                str(workspace_id),
                str(scope_id),
                capability,
                at_time=at_time,
                machine_id=self.snapshot.machine_id,
                metadata={"effect_id": effect_id},
            ),
            reason=f"v0.53 effect authority evaluated: {capability}",
        )
        if not result["decision"]["allowed"]:
            raise PermissionError(
                f"v0.53 effect authority denied {capability}: {result['decision']['reason']}"
            )
        return result

    def _record_effect_authority_binding(
        self,
        *,
        record_type: str,
        effect_id: str,
        actor_principal_id: str | None,
        workspace_id: str,
        scope_id: str,
        authority_decision_evidence_id: str | None = None,
        derived_from=(),
        metadata: dict | None = None,
    ) -> str:
        document = {
            "effect_id": effect_id,
            "actor_principal_id": actor_principal_id,
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "authority_decision_evidence_id": authority_decision_evidence_id,
            "metadata": deepcopy(metadata or {}),
        }
        lineage = list(map(str, derived_from))
        if authority_decision_evidence_id:
            lineage.append(authority_decision_evidence_id)
        object_id = f"{record_type}-{semantic_fingerprint(document)[:24]}"
        return self._record_authority_document(
            record_type=record_type,
            object_id=object_id,
            document=document,
            source=SCOPED_AUTHORITY_CONTRACT_ID,
            derived_from=lineage,
            reason=f"v0.53 {record_type} binding recorded",
        )

    def propose_effect(
        self,
        spec,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        proposer_principal_id: str | None = None,
    ):
        self._validate_effect_scope_context(workspace_id, scope_id)
        existing = self.store.find_effect_by_idempotency(self.snapshot.machine_id, spec.idempotency_key)
        if existing is not None:
            context = self._effect_context(existing.spec.effect_id)
            if context["document"]["workspace_id"] != workspace_id or context["document"]["scope_id"] != scope_id:
                raise PermissionError("idempotent effect reuse crosses workspace/scope boundary")
            return existing
        record = super().propose_effect(spec)
        self._record_effect_authority_binding(
            record_type="effect_proposal",
            effect_id=record.spec.effect_id,
            actor_principal_id=proposer_principal_id,
            workspace_id=str(workspace_id),
            scope_id=str(scope_id),
            metadata={
                "effect_type": record.spec.effect_type,
                "idempotency_key": record.spec.idempotency_key,
            },
        )
        return record

    def authorize_effect(
        self,
        effect_id,
        authority="controller",
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ):
        context = self._require_effect_context(effect_id, workspace_id, scope_id)
        authorization = self._authorize_effect_action(
            effect_id=effect_id,
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=EFFECT_AUTHORITY_CAPABILITIES["authorize"],
            at_time=at_time,
        )
        record = super().authorize_effect(effect_id, authority=f"scoped:{authorization['evidence_id']}")
        binding_id = self._record_effect_authority_binding(
            record_type="effect_authorization",
            effect_id=effect_id,
            actor_principal_id=actor_principal_id,
            workspace_id=str(workspace_id),
            scope_id=str(scope_id),
            authority_decision_evidence_id=authorization["evidence_id"],
            derived_from=[context["evidence_id"]],
            metadata={"effect_authorization_id": record.authorization_id},
        )
        if binding_id not in record.evidence:
            record.evidence.append(binding_id)
            self.store.save_effect(record)
        return record

    def execute_effect(
        self,
        effect_id,
        executor,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ):
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.status == EffectStatus.SUCCEEDED.value:
            return record
        context = self._require_effect_context(effect_id, workspace_id, scope_id)
        prior_authorization = self._latest_effect_authorization(effect_id, str(workspace_id), str(scope_id))
        authorization = self._authorize_effect_action(
            effect_id=effect_id,
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=EFFECT_AUTHORITY_CAPABILITIES["execute"],
            at_time=at_time,
        )
        binding_id = self._record_effect_authority_binding(
            record_type="effect_execution_authority",
            effect_id=effect_id,
            actor_principal_id=actor_principal_id,
            workspace_id=str(workspace_id),
            scope_id=str(scope_id),
            authority_decision_evidence_id=authorization["evidence_id"],
            derived_from=[context["evidence_id"], prior_authorization["evidence_id"]],
            metadata={"status_before_execution": record.status, "attempts_before_execution": record.attempts},
        )
        if binding_id not in record.evidence:
            record.evidence.append(binding_id)
            self.store.save_effect(record)
        return super().execute_effect(effect_id, executor)

    def reconcile_effect(
        self,
        effect_id,
        *,
        succeeded,
        result=None,
        evidence=None,
        error=None,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        at_time: float = 0.0,
    ):
        context = self._require_effect_context(effect_id, workspace_id, scope_id)
        authorization = self._authorize_effect_action(
            effect_id=effect_id,
            actor_principal_id=actor_principal_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            capability=EFFECT_AUTHORITY_CAPABILITIES["reconcile"],
            at_time=at_time,
        )
        binding_id = self._record_effect_authority_binding(
            record_type="effect_reconcile_authority",
            effect_id=effect_id,
            actor_principal_id=actor_principal_id,
            workspace_id=str(workspace_id),
            scope_id=str(scope_id),
            authority_decision_evidence_id=authorization["evidence_id"],
            derived_from=[context["evidence_id"]],
            metadata={"succeeded": bool(succeeded)},
        )
        merged_evidence = list(evidence or [])
        if binding_id not in merged_evidence:
            merged_evidence.append(binding_id)
        return super().reconcile_effect(
            effect_id,
            succeeded=succeeded,
            result=result,
            evidence=merged_evidence,
            error=error,
        )

    def effect_authority_report(
        self,
        *,
        workspace_id: str,
        scope_id: str | None = None,
    ) -> dict:
        groups = {
            "proposals": {},
            "authorizations": {},
            "execution_authorities": {},
            "reconcile_authorities": {},
        }
        mapping = {
            "effect_proposal": "proposals",
            "effect_authorization": "authorizations",
            "effect_execution_authority": "execution_authorities",
            "effect_reconcile_authority": "reconcile_authorities",
        }
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            bucket = mapping.get(metadata.get(_AUTHORITY_RECORD_TYPE))
            if bucket is None:
                continue
            document = metadata.get(_AUTHORITY_DOCUMENT)
            if not isinstance(document, dict) or document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            groups[bucket][str(row["evidence_id"])] = {
                "document": deepcopy(document),
                "derived_from": list(row.get("derived_from") or []),
            }
        return {
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "capabilities": deepcopy(EFFECT_AUTHORITY_CAPABILITIES),
            **groups,
        }


__all__ = [
    "AASMEngine",
    "RESOURCE_AUTHORITY_CAPABILITIES",
    "EFFECT_AUTHORITY_CAPABILITIES",
]
