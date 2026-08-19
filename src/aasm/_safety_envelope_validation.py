from __future__ import annotations

from typing import Any, Mapping, Sequence

from .quantity import Quantity
from .rule import EngineeringRule
from .semantic_evolution import ExternalReference
from ._hybrid_state_records import HybridQuantityObservation, HybridState
from ._safety_envelope_records import SafetyEnvelope, SafetyEnvelopeConstraint

def bind_safety_constraint(
    constraint_id: str,
    variable_id: str,
    rule: EngineeringRule,
    allowed_quantity: Quantity,
    *,
    evidence_ids: Sequence[str] = (),
    external_references: Sequence[ExternalReference | Mapping[str, Any]] = (),
    metadata: Mapping[str, Any] | None = None,
) -> SafetyEnvelopeConstraint:
    if not isinstance(rule, EngineeringRule) or not isinstance(allowed_quantity, Quantity):
        raise TypeError("bind_safety_constraint requires exact EngineeringRule and Quantity objects")
    return SafetyEnvelopeConstraint(
        constraint_id=constraint_id,
        variable_id=variable_id,
        rule_revision_id=rule.rule_revision_id,
        rule_fingerprint=rule.fingerprint,
        allowed_quantity_id=allowed_quantity.quantity_id,
        allowed_quantity_fingerprint=allowed_quantity.fingerprint,
        allowed_projection_fingerprint=allowed_quantity.canonical_projection_fingerprint,
        evidence_ids=tuple(evidence_ids),
        external_references=tuple(external_references),
        metadata=dict(metadata or {}),
    )


def observe_hybrid_quantity(
    variable_id: str,
    quantity: Quantity,
    *,
    evidence_ids: Sequence[str] = (),
    external_references: Sequence[ExternalReference | Mapping[str, Any]] = (),
    metadata: Mapping[str, Any] | None = None,
) -> HybridQuantityObservation:
    if not isinstance(quantity, Quantity):
        raise TypeError("observe_hybrid_quantity requires an exact Quantity object")
    return HybridQuantityObservation(
        variable_id=variable_id,
        status="OBSERVED",
        quantity_id=quantity.quantity_id,
        quantity_fingerprint=quantity.fingerprint,
        canonical_projection_fingerprint=quantity.canonical_projection_fingerprint,
        evidence_ids=tuple(evidence_ids),
        external_references=tuple(external_references),
        metadata=dict(metadata or {}),
    )


def unknown_hybrid_quantity(
    variable_id: str,
    *,
    evidence_ids: Sequence[str] = (),
    external_references: Sequence[ExternalReference | Mapping[str, Any]] = (),
    metadata: Mapping[str, Any] | None = None,
) -> HybridQuantityObservation:
    return HybridQuantityObservation(
        variable_id=variable_id,
        status="UNKNOWN",
        evidence_ids=tuple(evidence_ids),
        external_references=tuple(external_references),
        metadata=dict(metadata or {}),
    )


def _rule_index(rules: Sequence[EngineeringRule]) -> dict[str, EngineeringRule]:
    rows = tuple(rules)
    if any(not isinstance(rule, EngineeringRule) for rule in rows):
        raise TypeError("safety envelope validation requires exact EngineeringRule objects")
    index = {rule.rule_revision_id: rule for rule in rows}
    if len(index) != len(rows):
        raise ValueError("safety envelope rules must have unique rule_revision_id")
    return index


def _quantity_index(quantities: Sequence[Quantity]) -> dict[str, Quantity]:
    rows = tuple(quantities)
    if any(not isinstance(quantity, Quantity) for quantity in rows):
        raise TypeError("safety-envelope/hybrid-state validation requires exact Quantity objects")
    index = {quantity.quantity_id: quantity for quantity in rows}
    if len(index) != len(rows):
        raise ValueError("safety-envelope/hybrid-state quantities must have unique quantity_id")
    return index


def _exact_quantity(
    index: Mapping[str, Quantity],
    *,
    quantity_id: str,
    quantity_fingerprint: str,
    projection_fingerprint: str,
    label: str,
) -> Quantity:
    quantity = index.get(quantity_id)
    if quantity is None:
        raise ValueError(f"{label} does not bind a supplied Quantity")
    if quantity.fingerprint != quantity_fingerprint:
        raise ValueError(f"{label} Quantity fingerprint mismatch")
    if quantity.canonical_projection_fingerprint != projection_fingerprint:
        raise ValueError(f"{label} canonical projection fingerprint mismatch")
    return quantity


def validate_safety_envelope(
    envelope: SafetyEnvelope | Mapping[str, Any],
    rules: Sequence[EngineeringRule],
    quantities: Sequence[Quantity],
) -> dict[str, Any]:
    item = envelope if isinstance(envelope, SafetyEnvelope) else SafetyEnvelope.from_dict(envelope)
    rules_by_id = _rule_index(rules)
    quantities_by_id = _quantity_index(quantities)
    constraint_count = 0
    for mode in item.modes:
        for constraint in mode.constraints:
            constraint_count += 1
            rule = rules_by_id.get(constraint.rule_revision_id)
            if rule is None or rule.fingerprint != constraint.rule_fingerprint:
                raise ValueError(
                    f"safety constraint {constraint.constraint_id} does not bind an exact supplied EngineeringRule"
                )
            if rule.strength != "HARD_FLOOR":
                raise ValueError(
                    "safety envelope constraints must reuse exact HARD_FLOOR EngineeringRule semantics"
                )
            if rule.clause.clause_kind != "SAFETY_INVARIANT":
                raise ValueError(
                    "safety envelope constraints require an exact SAFETY_INVARIANT Rule clause"
                )
            if rule.problem_revision_id and (
                rule.problem_revision_id != item.problem_revision_id
                or rule.problem_revision_fingerprint != item.problem_revision_fingerprint
            ):
                raise ValueError(
                    f"safety constraint {constraint.constraint_id} EngineeringRule problem revision mismatch"
                )
            allowed = _exact_quantity(
                quantities_by_id,
                quantity_id=constraint.allowed_quantity_id,
                quantity_fingerprint=constraint.allowed_quantity_fingerprint,
                projection_fingerprint=constraint.allowed_projection_fingerprint,
                label=f"safety constraint {constraint.constraint_id} allowed bound",
            )
            if allowed.representation != "INTERVAL":
                raise ValueError("safety envelope allowed quantities must use INTERVAL representation")
            if allowed.tolerance.kind != "NONE":
                raise ValueError("safety envelope allowed interval cannot carry tolerance")
            if allowed.quantization is not None:
                raise ValueError("safety envelope allowed interval cannot carry quantization")
    return {
        "valid": True,
        "envelope_id": item.envelope_id,
        "envelope_fingerprint": item.fingerprint,
        "mode_count": len(item.modes),
        "constraint_count": constraint_count,
        "rule_contract_id": "aasm.rule.v1",
        "quantity_contract_id": "aasm.quantity.v1",
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


def validate_hybrid_state(
    state: HybridState | Mapping[str, Any],
    quantities: Sequence[Quantity],
) -> dict[str, Any]:
    item = state if isinstance(state, HybridState) else HybridState.from_dict(state)
    quantities_by_id = _quantity_index(quantities)
    observed = 0
    unknown = 0
    for observation in item.observations:
        if observation.status == "UNKNOWN":
            unknown += 1
            continue
        observed += 1
        _exact_quantity(
            quantities_by_id,
            quantity_id=observation.quantity_id,
            quantity_fingerprint=observation.quantity_fingerprint,
            projection_fingerprint=observation.canonical_projection_fingerprint,
            label=f"hybrid observation {observation.variable_id}",
        )
    return {
        "valid": True,
        "state_id": item.state_id,
        "state_fingerprint": item.fingerprint,
        "mode_id": item.mode_id,
        "observed_quantity_count": observed,
        "unknown_quantity_count": unknown,
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


