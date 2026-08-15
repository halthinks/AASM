from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from .effects import EffectOutcome, EffectReconciliation, EffectStatus, EffectUnknownOutcome


EFFECT_RESOURCE_SETTLEMENT_CONTRACT_ID = "aasm.effect.resource-settlement.v1"
EFFECT_RESOURCE_SETTLEMENT_CONTRACT_VERSION = "0.1.0"
EFFECT_RESOURCE_SETTLEMENT_STABILITY = "FOUNDATION_EXPERIMENTAL"


def effect_resource_settlement_contract() -> dict[str, Any]:
    return {
        "contract_id": EFFECT_RESOURCE_SETTLEMENT_CONTRACT_ID,
        "contract_version": EFFECT_RESOURCE_SETTLEMENT_CONTRACT_VERSION,
        "stability": EFFECT_RESOURCE_SETTLEMENT_STABILITY,
        "resource_ledger": "EXISTING_AASM_RESOURCE_SETTLEMENT_ONLY",
        "authority": "EXISTING_RESOURCE_SETTLE_SCOPED_AUTHORITY",
        "outcome_gate": "CONFIRMED_OR_FAILED_RECONCILIATION_REQUIRED",
        "unknown_outcome": "SETTLEMENT_BLOCKED",
        "actual_consumption": "EXACT_RESOURCE_KEYS_PER_BOUND_RESERVATION",
        "observation_evidence": "LOCAL_EVIDENCE_IDS_ONLY",
        "multi_reservation_atomicity": "RECOVERABLE_IDEMPOTENT_PER_RESERVATION_NOT_ALL_OR_NOTHING",
        "completion": "SUMMARY_EVIDENCE_ONLY_AFTER_ALL_BOUND_RESERVATIONS_SETTLED",
        "truth_authority": "NONE",
        "resource_state_grants_authority": False,
    }


class EffectResourceSettlementMixin:
    def effect_resource_settlement_contract_report(self) -> dict[str, Any]:
        return effect_resource_settlement_contract()

    def _resource_settlement_evidence(self, settlement_id: str) -> tuple[dict[str, Any], str]:
        for row in self.snapshot.evidence.get("records", []):
            if row.get("status", "active") != "active":
                continue
            metadata = row.get("metadata") or {}
            if metadata.get("aasm_resource_record_type") != "settlement_transaction":
                continue
            document = metadata.get("document")
            if isinstance(document, dict) and document.get("settlement_id") == settlement_id:
                return deepcopy(document), str(row["evidence_id"])
        raise KeyError(f"resource settlement Evidence not found: {settlement_id}")

    def _effect_reconciliation_evidence_id(self, effect_id: str, workspace_id: str, scope_id: str, reconciliation_id: str) -> str:
        rows = self._effect_governance_rows(
            workspace_id=workspace_id,
            scope_id=scope_id,
            record_types=("effect_reconciliation",),
            effect_id=effect_id,
        )
        matches = [row for row in rows if row["document"].get("reconciliation_id") == reconciliation_id]
        if len(matches) != 1:
            raise ValueError("effect resource settlement requires one durable reconciliation Evidence record")
        return str(matches[0]["evidence_id"])

    def settle_effect_resources(
        self,
        effect_id: str,
        actual_consumption_by_reservation: Mapping[str, Mapping[str, float]],
        *,
        workspace_id: str,
        scope_id: str,
        actor_principal_id: str,
        observation_evidence_ids=(),
        at_time: float = 0.0,
    ) -> dict[str, Any]:
        intent = self._require_v54_intent(effect_id, workspace_id, scope_id)
        record = self.store.load_effect(self.snapshot.machine_id, effect_id)
        if record.status == EffectStatus.UNKNOWN.value:
            raise EffectUnknownOutcome("effect resource settlement is blocked while the external outcome is UNKNOWN")
        if record.status not in {EffectStatus.SUCCEEDED.value, EffectStatus.FAILED.value}:
            raise ValueError("effect resource settlement requires a terminal observed effect outcome")
        if record.reconciliation is None:
            raise ValueError("effect resource settlement requires durable reconciliation")
        reconciliation = EffectReconciliation.from_dict(record.reconciliation)
        if reconciliation.outcome not in {EffectOutcome.CONFIRMED.value, EffectOutcome.FAILED.value} or reconciliation.retry_blocked:
            raise ValueError("effect resource settlement requires CONFIRMED or FAILED reconciliation")

        reservation_ids = tuple(intent.resource_reservation_ids)
        supplied = {
            str(reservation_id): {str(resource_id): float(amount) for resource_id, amount in values.items()}
            for reservation_id, values in actual_consumption_by_reservation.items()
        }
        if set(supplied) != set(reservation_ids):
            raise ValueError("effect actual consumption must cover exactly the EffectIntent resource reservations")
        observations = self._require_local_evidence_ids(observation_evidence_ids)
        reconciliation_evidence_id = self._effect_reconciliation_evidence_id(
            effect_id,
            workspace_id,
            scope_id,
            reconciliation.reconciliation_id,
        )

        report = self.resource_governance_report(workspace_id=workspace_id, scope_id=scope_id)
        pending: list[str] = []
        completed: dict[str, dict[str, Any]] = {}
        for reservation_id in reservation_ids:
            try:
                reservation = report["reservations"][reservation_id]
            except KeyError:
                raise KeyError(f"effect references unknown or inaccessible resource reservation: {reservation_id}") from None
            expected_keys = {str(resource_id) for resource_id, _ in reservation.get("allocations", [])}
            actual = supplied[reservation_id]
            if set(actual) != expected_keys:
                raise ValueError(f"actual consumption keys do not match bound reservation: {reservation_id}")
            if any(value < 0 for value in actual.values()):
                raise ValueError("effect actual consumption must be non-negative")
            status = reservation.get("status")
            if status == "ACTIVE":
                pending.append(reservation_id)
                continue
            if status != "SETTLED":
                raise ValueError(f"effect bound reservation cannot settle from status {status}: {reservation_id}")
            settlement_id = str(reservation.get("settlement_id") or "")
            settlement, evidence_id = self._resource_settlement_evidence(settlement_id)
            existing_actual = {str(key): float(value) for key, value in settlement.get("actual_consumption", {}).items()}
            if existing_actual != actual:
                raise ValueError(f"effect settlement retry conflicts with durable actual consumption: {reservation_id}")
            completed[reservation_id] = {
                "settlement": settlement,
                "evidence_id": evidence_id,
            }

        for reservation_id in pending:
            settled = self.settle_resource_reservation(
                reservation_id,
                supplied[reservation_id],
                workspace_id=workspace_id,
                scope_id=scope_id,
                evidence_ids=(reconciliation_evidence_id, *observations),
                actor_principal_id=actor_principal_id,
                at_time=at_time,
            )
            completed[reservation_id] = {
                "settlement": deepcopy(settled["settlement"]),
                "evidence_id": str(settled["evidence_id"]),
                "authority_decision_evidence_id": str(settled["authority_decision_evidence_id"]),
            }

        if set(completed) != set(reservation_ids):
            raise RuntimeError("effect resource settlement did not settle every bound reservation")
        settlement_rows = [
            {
                "reservation_id": reservation_id,
                "settlement_id": completed[reservation_id]["settlement"]["settlement_id"],
                "settlement_evidence_id": completed[reservation_id]["evidence_id"],
                "actual_consumption": deepcopy(completed[reservation_id]["settlement"]["actual_consumption"]),
            }
            for reservation_id in sorted(completed)
        ]
        document = {
            "contract_id": EFFECT_RESOURCE_SETTLEMENT_CONTRACT_ID,
            "contract_version": EFFECT_RESOURCE_SETTLEMENT_CONTRACT_VERSION,
            "workspace_id": workspace_id,
            "scope_id": scope_id,
            "effect_id": effect_id,
            "intent_id": intent.intent_id,
            "reconciliation_id": reconciliation.reconciliation_id,
            "outcome": reconciliation.outcome,
            "actor_principal_id": actor_principal_id,
            "observation_evidence_ids": list(observations),
            "settlements": settlement_rows,
            "truth_authority": "NONE",
        }
        summary_id = f"effect-resource-settlement-{__import__('aasm.semantic_result', fromlist=['semantic_fingerprint']).semantic_fingerprint(document)[:24]}"
        evidence_id = self._record_effect_governance_document(
            record_type="effect_resource_settlement",
            object_id=summary_id,
            document=document,
            source=EFFECT_RESOURCE_SETTLEMENT_CONTRACT_ID,
            derived_from=[
                reconciliation_evidence_id,
                *observations,
                *[row["settlement_evidence_id"] for row in settlement_rows],
            ],
            reason="v0.54 effect actual resource consumption reconciled",
        )
        return {
            "contract": effect_resource_settlement_contract(),
            "summary_id": summary_id,
            "settlement": document,
            "evidence_id": evidence_id,
            "settled_reservation_ids": sorted(completed),
        }


__all__ = [
    "EFFECT_RESOURCE_SETTLEMENT_CONTRACT_ID",
    "EFFECT_RESOURCE_SETTLEMENT_CONTRACT_VERSION",
    "EFFECT_RESOURCE_SETTLEMENT_STABILITY",
    "effect_resource_settlement_contract",
    "EffectResourceSettlementMixin",
]
