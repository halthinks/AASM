from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from .effects import (
    EFFECT_DISPATCH_REQUEST_CONTRACT_ID,
    EFFECT_GOVERNANCE_CONTRACT_VERSION,
    EFFECT_GOVERNANCE_STABILITY,
    EFFECT_INTENT_CONTRACT_ID,
    EFFECT_OWNERSHIP_CONTRACT_ID,
    EFFECT_RECONCILIATION_CONTRACT_ID,
    EffectDispatchRequest,
    EffectIntent,
    EffectOutcome,
    EffectOwnership,
    EffectOwnershipRequest,
    EffectReconciliation,
    EffectStatus,
    bind_effect_reconciliation,
    effect_governance_contract,
)
from .evidence import EvidenceRecord
from .model import now
from .runtime_v53_learning import AASMEngine as V53Engine
from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .workers import LeaseStatus


EFFECT_GOVERNANCE_RUNTIME_CONTRACT_ID = "aasm.effect.governance.runtime.v1"
EFFECT_GOVERNANCE_RUNTIME_CONTRACT_VERSION = "0.1.0"
EFFECT_GOVERNANCE_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"
_EFFECT_GOVERNANCE_RECORD_TYPE = "aasm_effect_governance_record_type"
_EFFECT_GOVERNANCE_DOCUMENT = "document"


def effect_governance_runtime_contract() -> dict[str, Any]:
    return {
        "contract_id": EFFECT_GOVERNANCE_RUNTIME_CONTRACT_ID,
        "contract_version": EFFECT_GOVERNANCE_RUNTIME_CONTRACT_VERSION,
        "stability": EFFECT_GOVERNANCE_RUNTIME_STABILITY,
        "model_contract": effect_governance_contract(),
        "intent_contract_id": EFFECT_INTENT_CONTRACT_ID,
        "dispatch_request_contract_id": EFFECT_DISPATCH_REQUEST_CONTRACT_ID,
        "ownership_contract_id": EFFECT_OWNERSHIP_CONTRACT_ID,
        "reconciliation_contract_id": EFFECT_RECONCILIATION_CONTRACT_ID,
        "existing_effect_execution": "V08_ATOMIC_EFFECT_CLAIM_REUSED",
        "claim_atomicity": "EXISTING_STORE_EFFECT_CLAIM_TRANSACTION",
        "authority": "V53_SCOPED_EFFECT_EXECUTE_REQUIRED_EACH_ATTEMPT",
        "task_lease": "EXISTING_AASM_TASKLEASE_REQUIRED_FOR_V54_DISPATCH",
        "resource_reservation": "DECLARED_RESERVATIONS_MUST_REMAIN_ACTIVE_AT_AUTHORIZATION_AND_DISPATCH",
        "external_boundary": "DURABLE_OWNERSHIP_EVIDENCE_REQUIRED_BEFORE_EXECUTOR_CALL",
        "unknown_outcome": "RETRY_BLOCKED_UNTIL_EXPLICIT_RECONCILIATION",
        "resource_state_grants_authority": False,
        "truth_authority": "NONE_ADDED_BY_EFFECT_GOVERNANCE",
    }


class AASMEngine(V53Engine):
    """Experimental v0.54 effect-governance runtime over the full v0.53 composition.

    This layer does not replace the historical effect executor, TaskLease,
    resource reservation, scoped authority, or solver-learning planes. It binds
    them into one explicit intent -> dispatch -> ownership -> outcome lifecycle.
    """

    def effect_governance_runtime_contract_report(self) -> dict[str, Any]:
        return effect_governance_runtime_contract()

    def _record_effect_governance_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from=(),
        reason: str,
    ) -> str:
        payload = deepcopy(dict(document))
        identity = {"record_type": record_type, "object_id": object_id, "document": payload}
        evidence_id = f"effect-governance-evidence-{semantic_fingerprint(identity)[:24]}"
        for row in self.snapshot.evidence.get("records", []):
            if row.get("evidence_id") != evidence_id:
                continue
            metadata = row.get("metadata") or {}
            if metadata.get(_EFFECT_GOVERNANCE_RECORD_TYPE) != record_type or metadata.get(_EFFECT_GOVERNANCE_DOCUMENT) != payload:
                raise ValueError(f"effect governance Evidence collision: {evidence_id}")
            return evidence_id
        record = EvidenceRecord(
            kind="effect_governance",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=list(sorted(set(map(str, derived_from)))),
            metadata={
                _EFFECT_GOVERNANCE_RECORD_TYPE: record_type,
                "object_id": object_id,
                _EFFECT_GOVERNANCE_DOCUMENT: payload,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        )
        guarded = getattr(self, "add_evidence_guarded", None)
        if guarded is not None:
            guarded(
                record,
                expected_machine_version=self.snapshot.version,
                reason=reason,
            )
        else:
            self.add_evidence(record, reason=reason)
        return evidence_id

    def _effect_governance_rows(
        self,
        *,
        workspace_id: str,
        scope_id: str | None = None,
        record_types: Iterable[str] | None = None,
        effect_id: str | None = None,
    ) -> list[dict[str, Any]]:
        allowed = None if record_types is None else set(map(str, record_types))
        rows = []
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            record_type = metadata.get(_EFFECT_GOVERNANCE_RECORD_TYPE)
            if not record_type or (allowed is not None and record_type not in allowed):
                continue
            document = metadata.get(_EFFECT_GOVERNANCE_DOCUMENT)
            if not isinstance(document, dict) or document.get("workspace_id") != workspace_id:
                continue
            if scope_id is not None and document.get("scope_id") != scope_id:
                continue
            if effect_id is not None and document.get("effect_id") != effect_id:
                continue
            rows.append(
                {
                    "record_type": record_type,
                    "evidence_id": row.get("evidence_id"),
                    "document": deepcopy(document),
                    "derived_from": list(row.get("derived_from") or []),
                }
            )
        return rows

    def _reservation_context(
        self,
        reservation_ids: Iterable[str],
        *,
        workspace_id: str,
        scope_id: str,
        require_active: bool = True,
    ) -> dict[str, dict[str, Any]]:
        ids = tuple(sorted(set(map(str, reservation_ids))))
        if not ids:
            return {}
        report = self.resource_governance_report(workspace_id=workspace_id, scope_id=scope_id)
        out = {}
        for reservation_id in ids:
            try:
                reservation = report["reservations"][reservation_id]
            except KeyError:
                raise KeyError(f"effect references unknown or inaccessible resource reservation: {reservation_id}") from None
            if require_active and reservation.get("status") != "ACTIVE":
                raise ValueError(f"effect resource reservation is not ACTIVE: {reservation_id}")
            out[reservation_id] = deepcopy(reservation)
        return out

    def _resource_reservation_evidence_ids(self, reservation_ids: Iterable[str]) -> list[str]:
        wanted = set(map(str, reservation_ids))
        if not wanted:
            return []
        found = []
        for row in self.snapshot.evidence.get("records", []):
            metadata = row.get("metadata") or {}
            if metadata.get("aasm_resource_record_type") != "routing_transaction":
                continue
            document = metadata.get("document")
            if not isinstance(document, dict):
                continue
            reservation = document.get("reservation")
            if isinstance(reservation, dict) and reservation.get("reservation_id") in wanted:
                found.append(str(row.get("evidence_id")))
        return sorted(set(found))

    def _require_v54_intent(self, effect_id: str, workspace_id: str, scope_id: str) -> EffectIntent:
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.intent is None:
            raise PermissionError(
                "effect has no v0.54 EffectIntent; explicit intent migration is required before v0.54 authorization or dispatch"
            )
        intent = EffectIntent.from_dict(record.intent)
        if intent.workspace_id != workspace_id or intent.scope_id != scope_id:
            raise PermissionError("effect intent crosses workspace/scope boundary")
        self._require_effect_context(effect_id, workspace_id, scope_id)
        return intent

    def propose_effect(
        self,
        spec,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        proposer_principal_id: str | None = None,
        resource_reservation_ids=(),
        intent_metadata: Mapping[str, Any] | None = None,
    ):
        if not workspace_id or not scope_id:
            raise PermissionError("v0.54 effect proposal requires workspace_id and scope_id")
        reservation_ids = tuple(sorted(set(map(str, resource_reservation_ids))))
        self._reservation_context(
            reservation_ids,
            workspace_id=workspace_id,
            scope_id=scope_id,
            require_active=True,
        )
        record = super().propose_effect(
            spec,
            workspace_id=workspace_id,
            scope_id=scope_id,
            proposer_principal_id=proposer_principal_id,
        )
        intent = EffectIntent.from_spec(
            record.spec,
            workspace_id=workspace_id,
            scope_id=scope_id,
            resource_reservation_ids=reservation_ids,
            proposer_principal_id=proposer_principal_id,
            metadata=intent_metadata,
        )
        if record.intent is not None:
            existing = EffectIntent.from_dict(record.intent)
            if existing.fingerprint != intent.fingerprint:
                raise ValueError("idempotent effect reuse conflicts with the existing v0.54 EffectIntent")
            return record
        if record.status != EffectStatus.PROPOSED.value:
            raise PermissionError("existing pre-v0.54 effect must be explicitly migrated before attaching an EffectIntent")
        record.intent = intent.to_dict()
        self.store.save_effect(record)
        proposal_context = self._effect_context(record.spec.effect_id)
        lineage = [proposal_context["evidence_id"], *self._resource_reservation_evidence_ids(reservation_ids)]
        evidence_id = self._record_effect_governance_document(
            record_type="effect_intent",
            object_id=intent.intent_id,
            document=intent.to_dict(),
            source=EFFECT_INTENT_CONTRACT_ID,
            derived_from=lineage,
            reason="v0.54 EffectIntent recorded",
        )
        record = self.store.load_effect(self.snapshot.machine_id, record.spec.effect_id)
        if evidence_id not in record.evidence:
            record.evidence.append(evidence_id)
            self.store.save_effect(record)
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
        if not workspace_id or not scope_id:
            raise PermissionError("v0.54 effect authorization requires workspace_id and scope_id")
        intent = self._require_v54_intent(effect_id, workspace_id, scope_id)
        self._reservation_context(
            intent.resource_reservation_ids,
            workspace_id=workspace_id,
            scope_id=scope_id,
            require_active=True,
        )
        return super().authorize_effect(
            effect_id,
            authority=authority,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )

    def _active_effect_lease(self, lease_id: str, owner_worker_id: str) -> dict[str, Any]:
        lease = next((deepcopy(row) for row in self.list_leases() if row.get("lease_id") == lease_id), None)
        if lease is None:
            raise KeyError(f"unknown TaskLease for effect dispatch: {lease_id}")
        if lease.get("status") != LeaseStatus.ACTIVE.value:
            raise ValueError(f"effect dispatch TaskLease is not ACTIVE: {lease_id}")
        if lease.get("worker_id") != owner_worker_id:
            raise PermissionError("effect dispatch worker does not own the supplied TaskLease")
        if float(lease.get("expires_at", 0)) <= now():
            raise ValueError(f"effect dispatch TaskLease is expired: {lease_id}")
        worker = next((row for row in self.list_workers() if row.get("worker_id") == owner_worker_id), None)
        if worker is None or worker.get("status") != "ACTIVE":
            raise ValueError(f"effect dispatch worker is not ACTIVE: {owner_worker_id}")
        if (lease.get("metadata") or {}).get("effect_id") not in {None, "", lease.get("metadata", {}).get("effect_id")}:
            raise ValueError("invalid effect TaskLease metadata")
        return lease

    def _bind_dispatch_request(
        self,
        effect_id: str,
        *,
        workspace_id: str,
        scope_id: str,
        owner_worker_id: str,
        task_lease_id: str,
        owner_principal_id: str | None,
        metadata: Mapping[str, Any] | None,
    ) -> EffectDispatchRequest:
        intent = self._require_v54_intent(effect_id, workspace_id, scope_id)
        self._reservation_context(
            intent.resource_reservation_ids,
            workspace_id=workspace_id,
            scope_id=scope_id,
            require_active=True,
        )
        lease = self._active_effect_lease(task_lease_id, owner_worker_id)
        lease_effect_id = str((lease.get("metadata") or {}).get("effect_id") or "")
        if lease_effect_id and lease_effect_id != effect_id:
            raise PermissionError("TaskLease metadata binds it to a different effect")
        dispatch = EffectDispatchRequest.from_intent(
            intent,
            owner_worker_id=owner_worker_id,
            task_lease_id=task_lease_id,
            owner_principal_id=owner_principal_id,
            metadata={"task_id": lease.get("task_id"), **dict(metadata or {})},
        )
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.status in {EffectStatus.RUNNING.value, EffectStatus.UNKNOWN.value}:
            raise ValueError(f"effect cannot accept a new dispatch request from status {record.status}")
        if record.dispatch_request is not None:
            current = EffectDispatchRequest.from_dict(record.dispatch_request)
            if current.fingerprint == dispatch.fingerprint:
                return current
        record.dispatch_request = dispatch.to_dict()
        if not any(row.get("dispatch_request_id") == dispatch.dispatch_request_id for row in record.dispatch_history):
            record.dispatch_history.append(dispatch.to_dict())
        self.store.save_effect(record)
        intent_rows = self._effect_governance_rows(
            workspace_id=workspace_id,
            scope_id=scope_id,
            record_types=("effect_intent",),
            effect_id=effect_id,
        )
        authorization = self._latest_effect_authorization(effect_id, workspace_id, scope_id)
        lineage = [authorization["evidence_id"], *[row["evidence_id"] for row in intent_rows]]
        evidence_id = self._record_effect_governance_document(
            record_type="effect_dispatch_request",
            object_id=dispatch.dispatch_request_id,
            document=dispatch.to_dict(),
            source=EFFECT_DISPATCH_REQUEST_CONTRACT_ID,
            derived_from=lineage,
            reason="v0.54 effect dispatch request recorded",
        )
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if evidence_id not in record.evidence:
            record.evidence.append(evidence_id)
            self.store.save_effect(record)
        return dispatch

    def execute_effect(
        self,
        effect_id,
        executor,
        *,
        workspace_id: str | None = None,
        scope_id: str | None = None,
        actor_principal_id: str | None = None,
        owner_worker_id: str | None = None,
        task_lease_id: str | None = None,
        at_time: float = 0.0,
        dispatch_metadata: Mapping[str, Any] | None = None,
    ):
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.status == EffectStatus.SUCCEEDED.value:
            return self._ensure_terminal_reconciliation(record)
        if not workspace_id or not scope_id or not owner_worker_id or not task_lease_id:
            raise PermissionError(
                "v0.54 effect dispatch requires workspace_id, scope_id, owner_worker_id, and task_lease_id"
            )
        self._bind_dispatch_request(
            effect_id,
            workspace_id=workspace_id,
            scope_id=scope_id,
            owner_worker_id=owner_worker_id,
            task_lease_id=task_lease_id,
            owner_principal_id=actor_principal_id,
            metadata=dispatch_metadata,
        )
        result = super().execute_effect(
            effect_id,
            executor,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )
        return self._ensure_terminal_reconciliation(result)

    def _effect_ownership_request_for_claim(self, effect_id):
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.intent is None or record.dispatch_request is None:
            raise PermissionError("v0.54 execution claim requires durable EffectIntent and EffectDispatchRequest")
        intent = EffectIntent.from_dict(record.intent)
        dispatch = EffectDispatchRequest.from_dict(record.dispatch_request)
        if dispatch.intent_id != intent.intent_id:
            raise ValueError("effect dispatch no longer matches durable EffectIntent")
        self._reservation_context(
            intent.resource_reservation_ids,
            workspace_id=intent.workspace_id,
            scope_id=intent.scope_id,
            require_active=True,
        )
        self._active_effect_lease(dispatch.task_lease_id, dispatch.owner_worker_id)
        rows = [
            row
            for row in self._effect_authority_rows("effect_execution_authority", effect_id)
            if row["document"].get("workspace_id") == intent.workspace_id
            and row["document"].get("scope_id") == intent.scope_id
        ]
        if not rows:
            raise PermissionError("v0.54 ownership requires the fresh v0.53 effect.execute authority decision")
        latest = rows[-1]
        authority_decision_evidence_id = str(latest["document"].get("authority_decision_evidence_id") or "")
        if not authority_decision_evidence_id:
            raise ValueError("effect execution authority binding lacks decision Evidence")
        return EffectOwnershipRequest.from_dispatch(
            dispatch,
            authority_decision_evidence_id=authority_decision_evidence_id,
            metadata={"execution_authority_binding_evidence_id": latest["evidence_id"]},
        )

    def _after_effect_claim(self, record):
        if record.ownership is None:
            raise PermissionError("v0.54 external dispatch is blocked without durable EffectOwnership")
        ownership = EffectOwnership.from_dict(record.ownership)
        if ownership.execution_id != record.execution_id:
            raise ValueError("EffectOwnership execution_id does not match the atomic effect claim")
        intent = EffectIntent.from_dict(record.intent)
        self._reservation_context(
            ownership.resource_reservation_ids,
            workspace_id=ownership.workspace_id,
            scope_id=ownership.scope_id,
            require_active=True,
        )
        self._active_effect_lease(ownership.task_lease_id or "", ownership.owner_worker_id)
        dispatch_rows = self._effect_governance_rows(
            workspace_id=ownership.workspace_id,
            scope_id=ownership.scope_id,
            record_types=("effect_dispatch_request",),
            effect_id=ownership.effect_id,
        )
        execution_binding = str(ownership.metadata.get("execution_authority_binding_evidence_id") or "")
        lineage = [
            ownership.authority_decision_evidence_id,
            execution_binding,
            *[row["evidence_id"] for row in dispatch_rows],
            *self._resource_reservation_evidence_ids(intent.resource_reservation_ids),
        ]
        evidence_id = self._record_effect_governance_document(
            record_type="effect_ownership",
            object_id=ownership.ownership_id,
            document=ownership.to_dict(),
            source=EFFECT_OWNERSHIP_CONTRACT_ID,
            derived_from=[row for row in lineage if row],
            reason="v0.54 atomic EffectOwnership recorded before external dispatch",
        )
        if evidence_id not in record.evidence:
            record.evidence.append(evidence_id)
            self.store.save_effect(record)
        return evidence_id

    def _record_reconciliation_evidence(
        self,
        record,
        reconciliation: EffectReconciliation,
        *,
        derived_from=(),
        reason: str,
    ) -> str:
        evidence_id = self._record_effect_governance_document(
            record_type="effect_reconciliation",
            object_id=reconciliation.reconciliation_id,
            document=reconciliation.to_dict(),
            source=EFFECT_RECONCILIATION_CONTRACT_ID,
            derived_from=derived_from,
            reason=reason,
        )
        current = self.store.load_effect(self.snapshot.machine_id, record.spec.effect_id)
        if evidence_id not in current.evidence:
            current.evidence.append(evidence_id)
            self.store.save_effect(current)
        return evidence_id

    def _ensure_terminal_reconciliation(self, record):
        if record.status not in {EffectStatus.SUCCEEDED.value, EffectStatus.FAILED.value}:
            return record
        current = self.store.load_effect(self.snapshot.machine_id, record.spec.effect_id)
        if current.ownership is None:
            return current
        ownership = EffectOwnership.from_dict(current.ownership)
        expected_outcome = EffectOutcome.CONFIRMED.value if current.status == EffectStatus.SUCCEEDED.value else EffectOutcome.FAILED.value
        existing = EffectReconciliation.from_dict(current.reconciliation) if current.reconciliation is not None else None
        if existing is not None and existing.outcome == expected_outcome and existing.ownership_id == ownership.ownership_id:
            reconciliation = existing
        else:
            reconciliation = EffectReconciliation(
                effect_id=current.spec.effect_id,
                outcome=expected_outcome,
                evidence_ids=tuple(current.evidence),
                ownership_id=ownership.ownership_id,
                reconciled_by_principal_id=ownership.owner_principal_id,
                authority_decision_evidence_id=ownership.authority_decision_evidence_id,
                result=deepcopy(current.result),
                error=current.error,
                metadata={"source": "executor_finalization", "execution_id": ownership.execution_id},
            )
            bind_effect_reconciliation(current, reconciliation)
            self.store.save_effect(current)
        ownership_rows = self._effect_governance_rows(
            workspace_id=ownership.workspace_id,
            scope_id=ownership.scope_id,
            record_types=("effect_ownership",),
            effect_id=ownership.effect_id,
        )
        self._record_reconciliation_evidence(
            current,
            reconciliation,
            derived_from=[ownership.authority_decision_evidence_id, *[row["evidence_id"] for row in ownership_rows]],
            reason="v0.54 effect terminal outcome recorded",
        )
        return self.store.load_effect(self.snapshot.machine_id, current.spec.effect_id)

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
        if not workspace_id or not scope_id:
            raise PermissionError("v0.54 effect reconciliation requires workspace_id and scope_id")
        intent = self._require_v54_intent(effect_id, workspace_id, scope_id)
        before = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if before.status != EffectStatus.UNKNOWN.value:
            raise ValueError("v0.54 explicit reconciliation is only valid for UNKNOWN effects")
        merged_evidence = list(before.evidence)
        for evidence_id in evidence or []:
            if evidence_id not in merged_evidence:
                merged_evidence.append(evidence_id)
        reconciled = super().reconcile_effect(
            effect_id,
            succeeded=succeeded,
            result=result,
            evidence=merged_evidence,
            error=error,
            workspace_id=workspace_id,
            scope_id=scope_id,
            actor_principal_id=actor_principal_id,
            at_time=at_time,
        )
        authority_rows = [
            row
            for row in self._effect_authority_rows("effect_reconcile_authority", effect_id)
            if row["document"].get("workspace_id") == workspace_id
            and row["document"].get("scope_id") == scope_id
        ]
        if not authority_rows:
            raise ValueError("v0.54 reconciliation completed without a scoped reconciliation authority binding")
        latest = authority_rows[-1]
        decision_evidence_id = str(latest["document"].get("authority_decision_evidence_id") or "")
        current = self.store.load_effect(self.snapshot.machine_id, effect_id)
        ownership = EffectOwnership.from_dict(current.ownership) if current.ownership is not None else None
        reconciliation = EffectReconciliation(
            effect_id=effect_id,
            outcome=EffectOutcome.CONFIRMED.value if succeeded else EffectOutcome.FAILED.value,
            evidence_ids=tuple(current.evidence),
            ownership_id=None if ownership is None else ownership.ownership_id,
            reconciled_by_principal_id=actor_principal_id,
            authority_decision_evidence_id=decision_evidence_id,
            result=deepcopy(current.result),
            error=current.error,
            metadata={"source": "explicit_unknown_reconciliation"},
        )
        bind_effect_reconciliation(current, reconciliation)
        self.store.save_effect(current)
        self._record_reconciliation_evidence(
            current,
            reconciliation,
            derived_from=[latest["evidence_id"], decision_evidence_id, *reconciliation.evidence_ids],
            reason="v0.54 UNKNOWN effect explicitly reconciled",
        )
        self._reservation_context(
            intent.resource_reservation_ids,
            workspace_id=workspace_id,
            scope_id=scope_id,
            require_active=False,
        )
        return self.store.load_effect(self.snapshot.machine_id, effect_id)

    def effect_governance_report(self, *, workspace_id: str, scope_id: str | None = None) -> dict[str, Any]:
        self._workspace_authority_inputs(workspace_id)
        effects = {}
        intents = {}
        dispatches = {}
        ownerships = {}
        reconciliations = {}
        for record in self.store.list_effects(self.snapshot.machine_id):
            if record.intent is None:
                continue
            intent = EffectIntent.from_dict(record.intent)
            if intent.workspace_id != workspace_id or (scope_id is not None and intent.scope_id != scope_id):
                continue
            effect_id = record.spec.effect_id
            effects[effect_id] = {
                "status": record.status,
                "attempts": record.attempts,
                "execution_id": record.execution_id,
                "intent_id": intent.intent_id,
                "dispatch_request_id": None if record.dispatch_request is None else record.dispatch_request.get("dispatch_request_id"),
                "ownership_id": None if record.ownership is None else record.ownership.get("ownership_id"),
                "reconciliation_id": None if record.reconciliation is None else record.reconciliation.get("reconciliation_id"),
                "evidence": list(record.evidence),
            }
            intents[intent.intent_id] = intent.to_dict()
            for row in record.dispatch_history:
                dispatches[str(row["dispatch_request_id"])] = deepcopy(row)
            for row in record.ownership_history:
                ownerships[str(row["ownership_id"])] = deepcopy(row)
            for row in record.reconciliation_history:
                reconciliations[str(row["reconciliation_id"])] = deepcopy(row)
        evidence_rows = self._effect_governance_rows(
            workspace_id=workspace_id,
            scope_id=scope_id,
        )
        return {
            "contract": self.effect_governance_runtime_contract_report(),
            "access_context": {"workspace_id": workspace_id, "scope_id": scope_id},
            "effects": effects,
            "intents": intents,
            "dispatches": dispatches,
            "ownerships": ownerships,
            "reconciliations": reconciliations,
            "evidence_records": evidence_rows,
        }


__all__ = [
    "AASMEngine",
    "EFFECT_GOVERNANCE_RUNTIME_CONTRACT_ID",
    "EFFECT_GOVERNANCE_RUNTIME_CONTRACT_VERSION",
    "EFFECT_GOVERNANCE_RUNTIME_STABILITY",
    "effect_governance_runtime_contract",
]
