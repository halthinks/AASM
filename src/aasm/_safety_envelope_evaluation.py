from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping, Sequence

from .quantity import ExactNumber, IntervalValue, MeasuredValue, Quantity, require_canonically_compatible
from .rule import EngineeringRule
from ._hybrid_state_records import HybridState
from ._safety_envelope_assessment_records import SafetyConstraintAssessment, SafetyEnvelopeAssessment
from ._safety_envelope_records import SafetyEnvelope
from ._safety_envelope_validation import _exact_quantity, _quantity_index, validate_hybrid_state, validate_safety_envelope

def _base_support(quantity: Quantity) -> tuple[Fraction, Fraction, bool, bool]:
    value = quantity.canonical_value
    if isinstance(value, ExactNumber):
        scalar = value.as_fraction
        return scalar, scalar, True, True
    if isinstance(value, IntervalValue):
        return (
            value.lower.as_fraction,
            value.upper.as_fraction,
            value.lower_inclusive,
            value.upper_inclusive,
        )
    if isinstance(value, MeasuredValue):
        interval = value.uncertainty_interval
        return (
            interval.lower.as_fraction,
            interval.upper.as_fraction,
            interval.lower_inclusive,
            interval.upper_inclusive,
        )
    raise TypeError("unsupported Quantity canonical value type in safety assessment")


def _observation_support(
    quantity: Quantity,
) -> tuple[Fraction, Fraction, bool, bool, tuple[str, ...]]:
    lower, upper, lower_inclusive, upper_inclusive = _base_support(quantity)
    diagnostics: list[str] = []
    tolerance = quantity.canonical_tolerance
    if tolerance.kind == "ABSOLUTE":
        assert tolerance.magnitude is not None
        magnitude = tolerance.magnitude.as_fraction
        lower -= magnitude
        upper += magnitude
        if magnitude:
            lower_inclusive = True
            upper_inclusive = True
    elif tolerance.kind == "ASYMMETRIC":
        assert tolerance.lower is not None and tolerance.upper is not None
        lower_magnitude = tolerance.lower.as_fraction
        upper_magnitude = tolerance.upper.as_fraction
        lower -= lower_magnitude
        upper += upper_magnitude
        if lower_magnitude:
            lower_inclusive = True
        if upper_magnitude:
            upper_inclusive = True
    elif tolerance.kind == "RELATIVE":
        assert tolerance.magnitude is not None
        ratio = tolerance.magnitude.as_fraction
        candidates = [lower, upper]
        if lower <= 0 <= upper:
            candidates.append(Fraction(0, 1))
        lower = min(value - abs(value) * ratio for value in candidates)
        upper = max(value + abs(value) * ratio for value in candidates)
        if ratio:
            lower_inclusive = True
            upper_inclusive = True
    if quantity.canonical_quantization is not None:
        quantization = quantity.canonical_quantization
        if quantization.rounding_rule != "EXACT":
            diagnostics.append(
                f"UNSUPPORTED_OBSERVATION_QUANTIZATION:{quantization.rounding_rule}"
            )
    return lower, upper, lower_inclusive, upper_inclusive, tuple(diagnostics)


def _interval_relation(
    observed: tuple[Fraction, Fraction, bool, bool],
    allowed: tuple[Fraction, Fraction, bool, bool],
) -> str:
    observed_lower, observed_upper, observed_lower_inclusive, observed_upper_inclusive = observed
    allowed_lower, allowed_upper, allowed_lower_inclusive, allowed_upper_inclusive = allowed

    lower_within = observed_lower > allowed_lower or (
        observed_lower == allowed_lower
        and (not observed_lower_inclusive or allowed_lower_inclusive)
    )
    upper_within = observed_upper < allowed_upper or (
        observed_upper == allowed_upper
        and (not observed_upper_inclusive or allowed_upper_inclusive)
    )
    if lower_within and upper_within:
        return "WITHIN"

    below = observed_upper < allowed_lower or (
        observed_upper == allowed_lower
        and not (observed_upper_inclusive and allowed_lower_inclusive)
    )
    above = observed_lower > allowed_upper or (
        observed_lower == allowed_upper
        and not (observed_lower_inclusive and allowed_upper_inclusive)
    )
    if below or above:
        return "OUTSIDE"
    return "OVERLAPS_BOUNDARY"


def assess_safety_envelope(
    envelope: SafetyEnvelope | Mapping[str, Any],
    state: HybridState | Mapping[str, Any],
    rules: Sequence[EngineeringRule],
    quantities: Sequence[Quantity],
) -> SafetyEnvelopeAssessment:
    envelope_item = envelope if isinstance(envelope, SafetyEnvelope) else SafetyEnvelope.from_dict(envelope)
    state_item = state if isinstance(state, HybridState) else HybridState.from_dict(state)
    if envelope_item.subject != state_item.subject:
        raise ValueError("safety envelope and hybrid state must bind the exact same semantic subject")
    if (
        envelope_item.problem_revision_id != state_item.problem_revision_id
        or envelope_item.problem_revision_fingerprint
        != state_item.problem_revision_fingerprint
    ):
        raise ValueError("safety envelope and hybrid state ProblemRevision mismatch")
    validate_safety_envelope(envelope_item, rules, quantities)
    validate_hybrid_state(state_item, quantities)
    quantities_by_id = _quantity_index(quantities)
    mode = next(
        (value for value in envelope_item.modes if value.mode_id == state_item.mode_id),
        None,
    )
    if mode is None:
        return SafetyEnvelopeAssessment(
            envelope_id=envelope_item.envelope_id,
            envelope_fingerprint=envelope_item.fingerprint,
            hybrid_state_id=state_item.state_id,
            hybrid_state_fingerprint=state_item.fingerprint,
            mode_id=state_item.mode_id,
            problem_revision_id=state_item.problem_revision_id,
            problem_revision_fingerprint=state_item.problem_revision_fingerprint,
            status="MODE_UNCOVERED",
            constraint_assessments=(),
            diagnostics=(f"MODE_UNCOVERED:{state_item.mode_id}",),
        )

    observations = {value.variable_id: value for value in state_item.observations}
    assessments: list[SafetyConstraintAssessment] = []
    violating: list[str] = []
    indeterminate: list[str] = []
    missing: list[str] = []
    diagnostics: list[str] = []

    for constraint in mode.constraints:
        allowed = _exact_quantity(
            quantities_by_id,
            quantity_id=constraint.allowed_quantity_id,
            quantity_fingerprint=constraint.allowed_quantity_fingerprint,
            projection_fingerprint=constraint.allowed_projection_fingerprint,
            label=f"safety constraint {constraint.constraint_id} allowed bound",
        )
        observation = observations.get(constraint.variable_id)
        if observation is None:
            relation = "UNKNOWN"
            row_diagnostics = ("MISSING_OBSERVATION",)
            observed_id = ""
            observed_fingerprint = ""
            missing.append(constraint.variable_id)
        elif observation.status == "UNKNOWN":
            relation = "UNKNOWN"
            row_diagnostics = ("EXPLICIT_UNKNOWN_OBSERVATION",)
            observed_id = ""
            observed_fingerprint = ""
        else:
            observed = _exact_quantity(
                quantities_by_id,
                quantity_id=observation.quantity_id,
                quantity_fingerprint=observation.quantity_fingerprint,
                projection_fingerprint=observation.canonical_projection_fingerprint,
                label=f"hybrid observation {observation.variable_id}",
            )
            require_canonically_compatible(observed, allowed)
            support = _observation_support(observed)
            row_diagnostics = support[4]
            observed_id = observed.quantity_id
            observed_fingerprint = observed.fingerprint
            if row_diagnostics:
                relation = "UNSUPPORTED"
            else:
                relation = _interval_relation(support[:4], _base_support(allowed))
        assessment = SafetyConstraintAssessment(
            constraint_id=constraint.constraint_id,
            variable_id=constraint.variable_id,
            relation=relation,
            rule_revision_id=constraint.rule_revision_id,
            rule_fingerprint=constraint.rule_fingerprint,
            allowed_quantity_id=constraint.allowed_quantity_id,
            allowed_quantity_fingerprint=constraint.allowed_quantity_fingerprint,
            observed_quantity_id=observed_id,
            observed_quantity_fingerprint=observed_fingerprint,
            diagnostics=row_diagnostics,
        )
        assessments.append(assessment)
        diagnostics.extend(
            f"{constraint.constraint_id}:{diagnostic}"
            for diagnostic in row_diagnostics
        )
        if relation == "OUTSIDE":
            violating.append(constraint.constraint_id)
        elif relation in {"OVERLAPS_BOUNDARY", "UNKNOWN", "UNSUPPORTED"}:
            indeterminate.append(constraint.constraint_id)

    if violating:
        status = "VIOLATED"
    elif indeterminate:
        status = "INDETERMINATE"
    else:
        status = "SATISFIED"
    unconstrained = sorted(set(observations) - {value.variable_id for value in mode.constraints})
    diagnostics.extend(f"UNCONSTRAINED_OBSERVATION:{value}" for value in unconstrained)

    return SafetyEnvelopeAssessment(
        envelope_id=envelope_item.envelope_id,
        envelope_fingerprint=envelope_item.fingerprint,
        hybrid_state_id=state_item.state_id,
        hybrid_state_fingerprint=state_item.fingerprint,
        mode_id=state_item.mode_id,
        problem_revision_id=state_item.problem_revision_id,
        problem_revision_fingerprint=state_item.problem_revision_fingerprint,
        status=status,
        constraint_assessments=tuple(assessments),
        violating_constraint_ids=tuple(violating),
        indeterminate_constraint_ids=tuple(indeterminate),
        missing_variable_ids=tuple(missing),
        diagnostics=tuple(diagnostics),
    )


