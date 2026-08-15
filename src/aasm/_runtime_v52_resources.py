from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any, Iterable, Mapping

from .evidence import EvidenceRecord
from .resource_governance import (
    RESOURCE_CAPACITY_CONTRACT_ID,
    RESOURCE_OBSERVATION_CONTRACT_ID,
    CapacityWindowKind,
    MeasurementAuthority,
    ResourceCapacity,
    ResourceObservation,
)
from .resource_routing import (
    RESOURCE_ROUTING_CONTRACT_ID,
    ResourceAwareCandidate,
    ResourceReservation,
    ResourceRoutingDecision,
    ResourceRoutingPolicy,
    reserve_candidate_resources,
    select_resource_aware_candidate,
)
from .semantic_result import canonical_semantic_json, semantic_fingerprint


RESOURCE_RUNTIME_CONTRACT_ID = "aasm.resource.runtime.v1"
RESOURCE_RUNTIME_CONTRACT_VERSION = "0.1.0"
RESOURCE_RUNTIME_STABILITY = "FOUNDATION_EXPERIMENTAL"

_RESOURCE_RECORD_TYPE = "aasm_resource_record_type"
_RESOURCE_DOCUMENT = "document"


def _records(snapshot) -> list[dict[str, Any]]:
    return list(snapshot.evidence.get("records", []))


def _capacity_to_dict(capacity: ResourceCapacity) -> dict[str, Any]:
    observation = capacity.latest_observation
    return {
        "resource_id": capacity.resource_id,
        "resource_class": capacity.resource_class,
        "unit": capacity.unit,
        "owner_principal_id": capacity.owner_principal_id,
        "workspace_id": capacity.workspace_id,
        "scope_id": capacity.scope_id,
        "provider": capacity.provider,
        "window_kind": capacity.window_kind.value,
        "total": capacity.total,
        "consumed": capacity.consumed,
        "committed": capacity.committed,
        "protected_reserve": capacity.protected_reserve,
        "window_seconds": capacity.window_seconds,
        "resets_at": capacity.resets_at.isoformat() if capacity.resets_at else None,
        "refill_rate_per_second": capacity.refill_rate_per_second,
        "latest_observation": _observation_to_dict(observation) if observation else None,
        "metadata": deepcopy(capacity.metadata),
    }


def _capacity_from_dict(data: Mapping[str, Any]) -> ResourceCapacity:
    payload = dict(data)
    payload["window_kind"] = CapacityWindowKind(str(payload.get("window_kind", "UNKNOWN")))
    if payload.get("resets_at"):
        payload["resets_at"] = datetime.fromisoformat(str(payload["resets_at"]))
    if payload.get("latest_observation"):
        payload["latest_observation"] = _observation_from_dict(payload["latest_observation"])
    return ResourceCapacity(**payload)


def _observation_to_dict(observation: ResourceObservation) -> dict[str, Any]:
    return {
        "resource_id": observation.resource_id,
        "observed_at": observation.observed_at.isoformat(),
        "source": observation.source,
        "measurement_authority": observation.measurement_authority.value,
        "reported_capacity": observation.reported_capacity,
        "reported_consumed": observation.reported_consumed,
        "reported_remaining": observation.reported_remaining,
        "confidence": observation.confidence,
        "freshness_seconds": observation.freshness_seconds,
        "metadata": deepcopy(observation.metadata),
    }


def _observation_from_dict(data: Mapping[str, Any]) -> ResourceObservation:
    payload = dict(data)
    payload["observed_at"] = datetime.fromisoformat(str(payload["observed_at"]))
    payload["measurement_authority"] = MeasurementAuthority(str(payload["measurement_authority"]))
    return ResourceObservation(**payload)


def _candidate_to_dict(candidate: ResourceAwareCandidate) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "correctness": candidate.correctness,
        "evidence_quality": candidate.evidence_quality,
        "expected_progress": candidate.expected_progress,
        "wall_time_seconds": candidate.wall_time_seconds,
        "monetary_cost": candidate.monetary_cost,
        "scarce_expert_usage": candidate.scarce_expert_usage,
        "demands": [
            {
                "resource_class": row.resource_class,
                "amount": row.amount,
                "unit": row.unit,
                "resource_id": row.resource_id,
                "upper_bound": row.upper_bound,
                "confidence": row.confidence,
                "metadata": deepcopy(row.metadata),
            }
            for row in candidate.demands
        ],
        "metadata": deepcopy(candidate.metadata),
    }


def _decision_to_dict(decision: ResourceRoutingDecision) -> dict[str, Any]:
    return {
        "selected_candidate_id": decision.selected_candidate_id,
        "eligible_candidate_ids": list(decision.eligible_candidate_ids),
        "rejected": {key: list(value) for key, value in sorted(decision.rejected.items())},
        "reason": decision.reason,
        "contract_id": decision.contract_id,
        "contract_version": decision.contract_version,
    }


def _reservation_to_dict(reservation: ResourceReservation, reservation_id: str, *, status: str = "ACTIVE") -> dict[str, Any]:
    return {
        "reservation_id": reservation_id,
        "candidate_id": reservation.candidate_id,
        "allocations": [[resource_id, amount] for resource_id, amount in reservation.allocations],
        "total_reserved": reservation.total_reserved,
        "status": status,
        "contract_id": reservation.contract_id,
        "contract_version": reservation.contract_version,
    }


def _project(snapshot) -> dict[str, Any]:
    capacities: dict[str, dict[str, Any]] = {}
    observations: dict[str, dict[str, Any]] = {}
    decisions: dict[str, dict[str, Any]] = {}
    reservations: dict[str, dict[str, Any]] = {}
    settlements: dict[str, dict[str, Any]] = {}

    for row in _records(snapshot):
        if row.get("status", "active") != "active":
            continue
        metadata = row.get("metadata") or {}
        record_type = metadata.get(_RESOURCE_RECORD_TYPE)
        document = metadata.get(_RESOURCE_DOCUMENT)
        if not record_type or not isinstance(document, dict):
            continue
        document = deepcopy(document)
        if record_type == "capacity":
            capacities[str(document["resource_id"])] = document
        elif record_type == "observation":
            observations[str(metadata.get("object_id") or row.get("evidence_id"))] = document
        elif record_type == "routing_transaction":
            tx_id = str(document["transaction_id"])
            decisions[tx_id] = document["decision"]
            reservation = document.get("reservation")
            if reservation:
                reservations[str(reservation["reservation_id"])] = reservation
            for resource_id, capacity_document in (document.get("post_capacities") or {}).items():
                capacities[str(resource_id)] = deepcopy(capacity_document)
        elif record_type == "settlement_transaction":
            settlement_id = str(document["settlement_id"])
            settlements[settlement_id] = document
            reservation_id = str(document["reservation_id"])
            if reservation_id in reservations:
                reservations[reservation_id] = {**reservations[reservation_id], "status": "SETTLED", "settlement_id": settlement_id}
            for resource_id, capacity_document in (document.get("post_capacities") or {}).items():
                capacities[str(resource_id)] = deepcopy(capacity_document)

    return {
        "capacities": capacities,
        "observations": observations,
        "decisions": decisions,
        "reservations": reservations,
        "settlements": settlements,
    }


class ResourceGovernanceRuntimeMixin:
    """Durable v0.52 resource selection/reservation/settlement over Evidence/events."""

    def resource_runtime_contract_report(self) -> dict[str, Any]:
        return {
            "contract_id": RESOURCE_RUNTIME_CONTRACT_ID,
            "contract_version": RESOURCE_RUNTIME_CONTRACT_VERSION,
            "stability": RESOURCE_RUNTIME_STABILITY,
            "capacity_contract_id": RESOURCE_CAPACITY_CONTRACT_ID,
            "observation_contract_id": RESOURCE_OBSERVATION_CONTRACT_ID,
            "routing_contract_id": RESOURCE_ROUTING_CONTRACT_ID,
            "durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
            "selection_and_reservation": "ONE_DURABLE_TRANSACTION_RECORD",
            "settlement": "ONE_DURABLE_TRANSACTION_RECORD",
            "authority": "RESOURCE_STATE_NEVER_GRANTS_AUTHORITY",
            "truth": "RESOURCE_OBSERVATIONS_REMAIN_EVIDENCE",
        }

    def _record_resource_document(
        self,
        *,
        record_type: str,
        object_id: str,
        document: Mapping[str, Any],
        source: str,
        derived_from=(),
    ) -> str:
        payload = deepcopy(dict(document))
        evidence_id = f"resource-evidence-{semantic_fingerprint({'record_type': record_type, 'object_id': object_id, 'document': payload})[:24]}"
        for row in _records(self.snapshot):
            if row.get("evidence_id") == evidence_id:
                metadata = row.get("metadata") or {}
                if metadata.get(_RESOURCE_RECORD_TYPE) != record_type or metadata.get(_RESOURCE_DOCUMENT) != payload:
                    raise ValueError(f"resource evidence collision: {evidence_id}")
                return evidence_id
        self.add_evidence(EvidenceRecord(
            kind="observation" if record_type == "observation" else "resource_state",
            statement=canonical_semantic_json(payload),
            source=source,
            derived_from=list(derived_from),
            metadata={
                _RESOURCE_RECORD_TYPE: record_type,
                "object_id": object_id,
                _RESOURCE_DOCUMENT: payload,
                "authority": "EVIDENCE_ONLY",
            },
            evidence_id=evidence_id,
        ), reason=f"resource {record_type} recorded")
        return evidence_id

    def register_resource_capacity(self, capacity: ResourceCapacity) -> dict[str, Any]:
        projection = _project(self.snapshot)
        existing = projection["capacities"].get(capacity.resource_id)
        document = _capacity_to_dict(capacity)
        if existing is not None and existing != document:
            raise ValueError("resource capacity already exists with different durable definition")
        evidence_id = self._record_resource_document(
            record_type="capacity",
            object_id=capacity.resource_id,
            document=document,
            source=RESOURCE_CAPACITY_CONTRACT_ID,
        )
        return {"capacity": document, "evidence_id": evidence_id, "already_exists": existing is not None}

    def record_resource_observation(self, observation: ResourceObservation) -> dict[str, Any]:
        projection = _project(self.snapshot)
        if observation.resource_id not in projection["capacities"]:
            raise KeyError(observation.resource_id)
        document = _observation_to_dict(observation)
        observation_id = f"resource-observation-{semantic_fingerprint(document)[:20]}"
        evidence_id = self._record_resource_document(
            record_type="observation",
            object_id=observation_id,
            document=document,
            source=RESOURCE_OBSERVATION_CONTRACT_ID,
        )
        return {"observation_id": observation_id, "observation": document, "evidence_id": evidence_id}

    def resource_governance_report(self) -> dict[str, Any]:
        projection = _project(self.snapshot)
        return {"contract": self.resource_runtime_contract_report(), **projection}

    def select_and_reserve_resource_candidate(
        self,
        candidates: Iterable[ResourceAwareCandidate],
        policy: ResourceRoutingPolicy,
        *,
        derived_from=(),
    ) -> dict[str, Any]:
        rows = tuple(candidates)
        if not rows:
            raise ValueError("at least one resource-aware candidate is required")
        projection = _project(self.snapshot)
        capacities = [_capacity_from_dict(value) for _, value in sorted(projection["capacities"].items())]
        decision = select_resource_aware_candidate(rows, capacities, policy)
        selected = next((row for row in rows if row.candidate_id == decision.selected_candidate_id), None)

        reservation_document = None
        post_capacities: dict[str, dict[str, Any]] = {}
        if selected is not None:
            reservation = reserve_candidate_resources(selected, capacities)
            reservation_seed = {
                "candidate_id": reservation.candidate_id,
                "allocations": [[resource_id, amount] for resource_id, amount in reservation.allocations],
            }
            reservation_id = f"resource-reservation-{semantic_fingerprint(reservation_seed)[:20]}"
            if reservation_id in projection["reservations"] and projection["reservations"][reservation_id].get("status") == "ACTIVE":
                raise ValueError("resource reservation already active")
            reservation_document = _reservation_to_dict(reservation, reservation_id)
            touched = {resource_id for resource_id, _ in reservation.allocations}
            post_capacities = {
                row.resource_id: _capacity_to_dict(row)
                for row in capacities
                if row.resource_id in touched
            }

        transaction_seed = {
            "candidates": [_candidate_to_dict(row) for row in sorted(rows, key=lambda value: value.candidate_id)],
            "decision": _decision_to_dict(decision),
            "reservation": reservation_document,
            "post_capacities": post_capacities,
        }
        transaction_id = f"resource-routing-tx-{semantic_fingerprint(transaction_seed)[:20]}"
        document = {"transaction_id": transaction_id, **transaction_seed}
        evidence_id = self._record_resource_document(
            record_type="routing_transaction",
            object_id=transaction_id,
            document=document,
            source=RESOURCE_ROUTING_CONTRACT_ID,
            derived_from=derived_from,
        )
        return {"transaction": document, "evidence_id": evidence_id}

    def settle_resource_reservation(
        self,
        reservation_id: str,
        actual_consumption: Mapping[str, float],
        *,
        evidence_ids=(),
    ) -> dict[str, Any]:
        projection = _project(self.snapshot)
        try:
            reservation = projection["reservations"][reservation_id]
        except KeyError:
            raise KeyError(reservation_id) from None
        if reservation.get("status") != "ACTIVE":
            raise ValueError("resource reservation is not active")

        expected = {str(resource_id): float(amount) for resource_id, amount in reservation.get("allocations", [])}
        actual = {str(key): float(value) for key, value in actual_consumption.items()}
        if set(actual) != set(expected):
            raise ValueError("actual consumption keys must exactly match reserved resources")
        if any(value < 0 for value in actual.values()):
            raise ValueError("actual consumption must be non-negative")

        capacities = {
            key: _capacity_from_dict(value)
            for key, value in projection["capacities"].items()
        }
        post_capacities: dict[str, dict[str, Any]] = {}
        for resource_id in sorted(expected):
            capacity = capacities[resource_id]
            capacity.settle(expected[resource_id], actual[resource_id])
            post_capacities[resource_id] = _capacity_to_dict(capacity)

        settlement_seed = {
            "reservation_id": reservation_id,
            "actual_consumption": dict(sorted(actual.items())),
            "post_capacities": post_capacities,
        }
        settlement_id = f"resource-settlement-{semantic_fingerprint(settlement_seed)[:20]}"
        document = {"settlement_id": settlement_id, **settlement_seed}
        evidence_id = self._record_resource_document(
            record_type="settlement_transaction",
            object_id=settlement_id,
            document=document,
            source=RESOURCE_RUNTIME_CONTRACT_ID,
            derived_from=evidence_ids,
        )
        return {"settlement": document, "evidence_id": evidence_id}


__all__ = [
    "RESOURCE_RUNTIME_CONTRACT_ID",
    "RESOURCE_RUNTIME_CONTRACT_VERSION",
    "RESOURCE_RUNTIME_STABILITY",
    "ResourceGovernanceRuntimeMixin",
]
