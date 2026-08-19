from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

import aasm
from aasm.quantity import (
    DimensionVector,
    ExactNumber,
    IntervalValue,
    MeasuredValue,
    Quantity,
    QuantizationSpec,
    ToleranceSpec,
    UnitBinding,
)
from aasm.rule import EngineeringRule, RuleApplicabilityPredicate, RuleClauseRef, RuleScopeSelector
from aasm.safety_envelope_hybrid_state import (
    CONSTRAINT_RELATIONS,
    HYBRID_OBSERVATION_STATUSES,
    SAFETY_ENVELOPE_ASSESSMENT_STATUSES,
    HybridQuantityObservation,
    HybridState,
    SafetyEnvelope,
    SafetyEnvelopeAssessment,
    SafetyEnvelopeConstraint,
    SafetyModeEnvelope,
    assess_safety_envelope,
    bind_safety_constraint,
    observe_hybrid_quantity,
    safety_envelope_hybrid_state_contract,
    unknown_hybrid_quantity,
    validate_hybrid_state,
    validate_safety_envelope,
)
from aasm.semantic_evolution import ExternalReference
from aasm.semantic_projection import SemanticSubjectRef


ROOT = Path(__file__).resolve().parents[1]
REVISION_ID = "problem-revision-s4-8"
REVISION_FINGERPRINT = "8" * 64


def external_ref(role: str = "observation") -> ExternalReference:
    return ExternalReference(
        "test.sensor",
        f"sensor-{role}",
        role,
        revision="calibration-1",
        source_fingerprint=hashlib.sha256(role.encode()).hexdigest(),
    )


def subject(object_id: str = "actuator-1") -> SemanticSubjectRef:
    return SemanticSubjectRef(
        "aasm.physical.subject.v1",
        object_id,
        hashlib.sha256(object_id.encode()).hexdigest(),
        REVISION_ID,
        REVISION_FINGERPRINT,
    )


def number(value: str) -> ExactNumber:
    return ExactNumber.decimal(value)


def dimension(name: str = "temperature") -> DimensionVector:
    return DimensionVector({name: 1})


def unit(name: str = "degC") -> UnitBinding:
    return UnitBinding(name, name)


def quantity_interval(
    lower: str,
    upper: str,
    *,
    dimension_name: str = "temperature",
    unit_name: str = "degC",
    tolerance: ToleranceSpec | None = None,
    quantization: QuantizationSpec | None = None,
) -> Quantity:
    return Quantity(
        "INTERVAL",
        IntervalValue(number(lower), number(upper)),
        dimension(dimension_name),
        unit(unit_name),
        tolerance=tolerance or ToleranceSpec(),
        quantization=quantization,
    )


def quantity_scalar(
    value: str,
    *,
    dimension_name: str = "temperature",
    unit_name: str = "degC",
    tolerance: ToleranceSpec | None = None,
    quantization: QuantizationSpec | None = None,
) -> Quantity:
    return Quantity(
        "DECIMAL",
        number(value),
        dimension(dimension_name),
        unit(unit_name),
        tolerance=tolerance or ToleranceSpec(),
        quantization=quantization,
    )


def measured_quantity(lower: str, nominal: str, upper: str) -> Quantity:
    ref = external_ref("measurement-uncertainty")
    return Quantity(
        "MEASURED",
        MeasuredValue(number(nominal), IntervalValue(number(lower), number(upper)), ref),
        dimension(),
        unit(),
        provenance_refs=(ref,),
    )


def rule(
    *,
    strength: str = "HARD_FLOOR",
    clause_kind: str = "SAFETY_INVARIANT",
    revision_id: str = REVISION_ID,
    revision_fingerprint: str = REVISION_FINGERPRINT,
) -> EngineeringRule:
    clause_id = f"temperature-envelope-{strength}-{clause_kind}"
    return EngineeringRule(
        "temperature-envelope",
        RuleClauseRef(
            "aasm.semantic.constraint.v1",
            clause_id,
            hashlib.sha256(clause_id.encode()).hexdigest(),
            clause_kind,
        ),
        strength,
        RuleScopeSelector("workspace-1", "control", "EXACT", ("actuator-1",)),
        RuleApplicabilityPredicate("ALWAYS"),
        "physical-safety",
        priority=100,
        specificity=10,
        severity="CRITICAL",
        problem_revision_id=revision_id,
        problem_revision_fingerprint=revision_fingerprint,
    )


def envelope_for(allowed: Quantity, rule_obj: EngineeringRule | None = None) -> SafetyEnvelope:
    rule_obj = rule_obj or rule()
    constraint = bind_safety_constraint(
        "temperature-safe",
        "temperature",
        rule_obj,
        allowed,
        evidence_ids=("evidence-safety-rule",),
    )
    return SafetyEnvelope(
        "actuator-operating-envelope",
        subject(),
        REVISION_ID,
        REVISION_FINGERPRINT,
        (SafetyModeEnvelope("NORMAL", (constraint,), evidence_ids=("evidence-mode-definition",)),),
        evidence_ids=("evidence-envelope-definition",),
    )


def state_for(
    observations: tuple[HybridQuantityObservation, ...],
    *,
    mode_id: str = "NORMAL",
    state_subject: SemanticSubjectRef | None = None,
) -> HybridState:
    return HybridState(
        "observed-actuator-state",
        state_subject or subject(),
        mode_id,
        REVISION_ID,
        REVISION_FINGERPRINT,
        observations,
        mode_evidence_ids=("evidence-mode-observation",),
    )


def assess(allowed: Quantity, observed: Quantity) -> SafetyEnvelopeAssessment:
    rule_obj = rule()
    envelope = envelope_for(allowed, rule_obj)
    state = state_for((observe_hybrid_quantity("temperature", observed, evidence_ids=("evidence-temperature",)),))
    return assess_safety_envelope(envelope, state, (rule_obj,), (allowed, observed))


def test_vocabularies_and_contract_claim_ceiling_are_exact():
    assert HYBRID_OBSERVATION_STATUSES == ("OBSERVED", "UNKNOWN")
    assert CONSTRAINT_RELATIONS == ("WITHIN", "OUTSIDE", "OVERLAPS_BOUNDARY", "UNKNOWN", "UNSUPPORTED")
    assert SAFETY_ENVELOPE_ASSESSMENT_STATUSES == ("SATISFIED", "VIOLATED", "INDETERMINATE", "MODE_UNCOVERED")
    contract = safety_envelope_hybrid_state_contract()
    assert contract["safety_envelope_contract_id"] == "aasm.safety.envelope.v1"
    assert contract["hybrid_state_contract_id"] == "aasm.hybrid.state.v1"
    assert contract["assessment_contract_id"] == "aasm.safety.envelope.assessment.v1"
    assert contract["ode_solver"] == "NONE"
    assert contract["physics_solver"] == "NONE"
    assert contract["controller_synthesis"] == "NONE"
    assert contract["parallel_safety_state_machine"] == "NONE"
    assert contract["assessment_is_authorization"] is False
    assert contract["assessment_is_empirical_safety_proof"] is False
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


def test_records_are_deterministic_and_round_trip():
    allowed = quantity_interval("0", "10")
    rule_obj = rule()
    envelope = envelope_for(allowed, rule_obj)
    observed = quantity_scalar("5")
    state = state_for((observe_hybrid_quantity("temperature", observed, external_references=(external_ref(),)),))
    assessment = assess_safety_envelope(envelope, state, (rule_obj,), (allowed, observed))
    assert SafetyEnvelope.from_dict(envelope.to_dict()) == envelope
    assert HybridState.from_dict(state.to_dict()) == state
    assert SafetyEnvelopeAssessment.from_dict(assessment.to_dict()) == assessment
    assert assessment.status == "SATISFIED"


def test_exact_hard_floor_safety_invariant_rule_and_interval_quantity_are_required():
    allowed = quantity_interval("0", "10")
    non_floor = rule(strength="HARD")
    with pytest.raises(ValueError, match="HARD_FLOOR"):
        validate_safety_envelope(envelope_for(allowed, non_floor), (non_floor,), (allowed,))
    wrong_kind = rule(clause_kind="CONSTRAINT")
    with pytest.raises(ValueError, match="SAFETY_INVARIANT"):
        validate_safety_envelope(envelope_for(allowed, wrong_kind), (wrong_kind,), (allowed,))
    scalar_bound = quantity_scalar("10")
    floor = rule()
    with pytest.raises(ValueError, match="INTERVAL representation"):
        validate_safety_envelope(envelope_for(scalar_bound, floor), (floor,), (scalar_bound,))


def test_allowed_interval_rejects_tolerance_and_quantization():
    floor = rule()
    tolerance_bound = quantity_interval("0", "10", tolerance=ToleranceSpec("ABSOLUTE", number("1")))
    with pytest.raises(ValueError, match="cannot carry tolerance"):
        validate_safety_envelope(envelope_for(tolerance_bound, floor), (floor,), (tolerance_bound,))
    quantized_bound = quantity_interval("0", "10", quantization=QuantizationSpec(number("1")))
    with pytest.raises(ValueError, match="cannot carry quantization"):
        validate_safety_envelope(envelope_for(quantized_bound, floor), (floor,), (quantized_bound,))


def test_forged_rule_and_quantity_bindings_fail_closed():
    allowed = quantity_interval("0", "10")
    floor = rule()
    envelope = envelope_for(allowed, floor)
    original = envelope.modes[0].constraints[0]
    forged_rule = SafetyEnvelopeConstraint(
        original.constraint_id, original.variable_id, original.rule_revision_id, "0" * 64,
        original.allowed_quantity_id, original.allowed_quantity_fingerprint, original.allowed_projection_fingerprint,
    )
    forged_envelope = SafetyEnvelope(
        envelope.envelope_name, envelope.subject, envelope.problem_revision_id, envelope.problem_revision_fingerprint,
        (SafetyModeEnvelope("NORMAL", (forged_rule,)),),
    )
    with pytest.raises(ValueError, match="exact supplied EngineeringRule"):
        validate_safety_envelope(forged_envelope, (floor,), (allowed,))
    forged_quantity = SafetyEnvelopeConstraint(
        original.constraint_id, original.variable_id, original.rule_revision_id, original.rule_fingerprint,
        original.allowed_quantity_id, "0" * 64, original.allowed_projection_fingerprint,
    )
    forged_envelope = SafetyEnvelope(
        envelope.envelope_name, envelope.subject, envelope.problem_revision_id, envelope.problem_revision_fingerprint,
        (SafetyModeEnvelope("NORMAL", (forged_quantity,)),),
    )
    with pytest.raises(ValueError, match="Quantity fingerprint mismatch"):
        validate_safety_envelope(forged_envelope, (floor,), (allowed,))


def test_within_outside_and_boundary_overlap_relations_are_conservative():
    allowed = quantity_interval("0", "10")
    assert assess(allowed, quantity_scalar("5")).status == "SATISFIED"
    outside = assess(allowed, quantity_interval("11", "12"))
    assert outside.status == "VIOLATED"
    assert outside.constraint_assessments[0].relation == "OUTSIDE"
    overlap = assess(allowed, quantity_interval("9", "11"))
    assert overlap.status == "INDETERMINATE"
    assert overlap.constraint_assessments[0].relation == "OVERLAPS_BOUNDARY"


def test_measured_support_and_tolerance_are_expanded_exactly():
    allowed = quantity_interval("0", "10")
    assert assess(allowed, measured_quantity("4", "5", "6")).status == "SATISFIED"
    absolute = quantity_scalar("9.5", tolerance=ToleranceSpec("ABSOLUTE", number("1")))
    assert assess(allowed, absolute).status == "INDETERMINATE"
    relative = quantity_scalar("9.5", tolerance=ToleranceSpec("RELATIVE", number("0.1")))
    assert assess(allowed, relative).status == "INDETERMINATE"


def test_unknown_missing_and_uncovered_mode_fail_closed():
    allowed = quantity_interval("0", "10")
    floor = rule()
    envelope = envelope_for(allowed, floor)
    explicit_unknown = state_for((unknown_hybrid_quantity("temperature", evidence_ids=("evidence-sensor-fault",)),))
    unknown_result = assess_safety_envelope(envelope, explicit_unknown, (floor,), (allowed,))
    assert unknown_result.status == "INDETERMINATE"
    assert unknown_result.constraint_assessments[0].relation == "UNKNOWN"
    missing_state = state_for(())
    missing_result = assess_safety_envelope(envelope, missing_state, (floor,), (allowed,))
    assert missing_result.status == "INDETERMINATE"
    assert missing_result.missing_variable_ids == ("temperature",)
    uncovered_state = state_for((), mode_id="SERVICE")
    uncovered = assess_safety_envelope(envelope, uncovered_state, (floor,), (allowed,))
    assert uncovered.status == "MODE_UNCOVERED"
    assert uncovered.constraint_assessments == ()


def test_non_exact_quantization_is_unsupported_not_assumed_safe():
    allowed = quantity_interval("0", "10")
    observed = quantity_scalar("5", quantization=QuantizationSpec(number("1"), rounding_rule="HALF_UP"))
    result = assess(allowed, observed)
    assert result.status == "INDETERMINATE"
    assert result.constraint_assessments[0].relation == "UNSUPPORTED"
    assert "UNSUPPORTED_OBSERVATION_QUANTIZATION:HALF_UP" in result.constraint_assessments[0].diagnostics


def test_dimension_and_canonical_unit_mismatch_fail_closed():
    allowed = quantity_interval("0", "10")
    with pytest.raises(ValueError, match="dimensionally inconsistent"):
        assess(allowed, quantity_scalar("5", dimension_name="pressure"))
    with pytest.raises(ValueError, match="different canonical units"):
        assess(allowed, quantity_scalar("5", unit_name="kelvin"))


def test_revision_and_subject_mismatch_fail_closed():
    allowed = quantity_interval("0", "10")
    wrong_revision_rule = rule(revision_id="problem-revision-other", revision_fingerprint="9" * 64)
    with pytest.raises(ValueError, match="problem revision mismatch"):
        validate_safety_envelope(envelope_for(allowed, wrong_revision_rule), (wrong_revision_rule,), (allowed,))
    floor = rule()
    envelope = envelope_for(allowed, floor)
    observed = quantity_scalar("5")
    wrong_subject_state = state_for(
        (observe_hybrid_quantity("temperature", observed, evidence_ids=("evidence-temperature",)),),
        state_subject=subject("actuator-2"),
    )
    with pytest.raises(ValueError, match="exact same semantic subject"):
        assess_safety_envelope(envelope, wrong_subject_state, (floor,), (allowed, observed))


def test_observation_and_mode_provenance_are_mandatory():
    observed = quantity_scalar("5")
    with pytest.raises(ValueError, match="explicit Evidence or external reference provenance"):
        observe_hybrid_quantity("temperature", observed)
    with pytest.raises(ValueError, match="discrete mode requires explicit Evidence"):
        HybridState("state", subject(), "NORMAL", REVISION_ID, REVISION_FINGERPRINT, ())


def test_binary_float_metadata_and_identity_tampering_fail_closed():
    allowed = quantity_interval("0", "10")
    floor = rule()
    with pytest.raises(TypeError, match="binary floating-point"):
        bind_safety_constraint("c", "temperature", floor, allowed, metadata={"confidence": 0.9})
    envelope = envelope_for(allowed, floor)
    changed = deepcopy(envelope.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        SafetyEnvelope.from_dict(changed)


def test_assessment_is_pure_and_cannot_claim_authority_or_solver_execution():
    allowed = quantity_interval("0", "10")
    floor = rule()
    envelope = envelope_for(allowed, floor)
    observed = quantity_scalar("5")
    state = state_for((observe_hybrid_quantity("temperature", observed, evidence_ids=("evidence-temperature",)),))
    before_envelope = deepcopy(envelope.to_dict())
    before_state = deepcopy(state.to_dict())
    result = assess_safety_envelope(envelope, state, (floor,), (allowed, observed))
    assert envelope.to_dict() == before_envelope
    assert state.to_dict() == before_state
    for name in (
        "fact_authority_granted", "physical_state_authority_granted", "effect_authority_granted",
        "operational_mode_activated", "artifact_acceptance_granted", "dispatch_performed",
        "solver_executed", "dynamics_integrated",
    ):
        assert getattr(result, name) is False
    payload = result.to_dict(); payload["effect_authority_granted"] = True; payload.pop("fingerprint")
    with pytest.raises(ValueError, match="cannot set effect_authority_granted=True"):
        SafetyEnvelopeAssessment.from_dict(payload)


def test_hybrid_state_validation_accepts_explicit_all_missing_observations():
    report = validate_hybrid_state(state_for(()), ())
    assert report["valid"] is True
    assert report["observed_quantity_count"] == 0
    assert report["unknown_quantity_count"] == 0


def test_foundation_is_not_public_root_or_runtime_composition():
    assert not hasattr(aasm, "SafetyEnvelope")
    assert not hasattr(aasm, "HybridState")
    runtime_source = (ROOT / "src/aasm/runtime_v56_foundation.py").read_text(encoding="utf-8")
    assert "from .safety_envelope_hybrid_state" not in runtime_source
    assert "SafetyEnvelope" not in runtime_source
    assert "HybridState" not in runtime_source


def test_schemas_are_closed_and_accept_canonical_documents():
    allowed = quantity_interval("0", "10")
    floor = rule()
    envelope = envelope_for(allowed, floor)
    observed = quantity_scalar("5")
    state = state_for((observe_hybrid_quantity("temperature", observed, evidence_ids=("evidence-temperature",)),))
    assessment = assess_safety_envelope(envelope, state, (floor,), (allowed, observed))
    docs = (
        ("safety-envelope.schema.json", envelope.to_dict()),
        ("hybrid-state.schema.json", state.to_dict()),
        ("safety-envelope-assessment.schema.json", assessment.to_dict()),
    )
    for filename, document in docs:
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        validate(document, schema)
        changed = deepcopy(document); changed["unknown_field"] = True
        with pytest.raises(ValidationError):
            validate(changed, schema)
