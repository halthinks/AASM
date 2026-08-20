from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

import aasm
from aasm.calculus import (
    ObligationRecord,
    default_calculus_state,
    normalize_calculus_state,
)
from aasm.degraded_operation import degraded_operation_contract
from aasm.epistemic_debt_manual_override import (
    OverrideValidityWindow,
    bind_manual_override,
    evaluate_manual_override,
    project_epistemic_debt,
)
from aasm.quantity import (
    DimensionVector,
    ExactNumber,
    IntervalValue,
    Quantity,
    QuantizationSpec,
    ToleranceSpec,
    UnitBinding,
    require_dimensionally_compatible,
)
from aasm.risk_irreversibility import (
    EffectIrreversibility,
    HazardObservation,
    HazardRef,
    IrreversibilityAssurancePolicy,
    RiskAssessment,
    RiskEnvelope,
    evaluate_risk,
    risk_irreversibility_contract,
)
from aasm.rule import (
    EngineeringRule,
    RuleApplicabilityPredicate,
    RuleClauseRef,
    RuleControlPolicy,
    RuleScopeSelector,
    RuleSourceAuthorityRef,
)
from aasm.safety_envelope_hybrid_state import (
    HybridState,
    SafetyEnvelope,
    SafetyModeEnvelope,
    assess_safety_envelope,
    bind_safety_constraint,
    observe_hybrid_quantity,
)
from aasm.semantic_projection import SemanticSubjectRef
from aasm.semantic_result import semantic_fingerprint
from aasm.uncertainty_scenario_trace import Scenario, ScenarioBinding


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "fixtures/textpcb/s4-safety-governance-fixtures.json"
REVISION_ID = "problem-revision-textpcb-s4"
REVISION_FINGERPRINT = "4" * 64


def number(value: str) -> ExactNumber:
    return ExactNumber.decimal(value)


def length_dimension() -> DimensionVector:
    return DimensionVector({"length": 1})


def subject() -> SemanticSubjectRef:
    return SemanticSubjectRef(
        "aasm.textpcb.design.v1",
        "textpcb-board-1",
        "d" * 64,
        REVISION_ID,
        REVISION_FINGERPRINT,
    )


def rule(
    rule_id: str,
    *,
    strength: str,
    clause_kind: str = "CONSTRAINT",
    waivable: bool = False,
) -> EngineeringRule:
    clause_id = f"{rule_id}-{strength}-{clause_kind}"
    control = (
        RuleControlPolicy("EXPLICIT_AUTHORIZED", "FORBIDDEN", "rule.waive")
        if waivable
        else RuleControlPolicy()
    )
    return EngineeringRule(
        rule_id,
        RuleClauseRef(
            "aasm.semantic.constraint.v1",
            clause_id,
            hashlib.sha256(clause_id.encode()).hexdigest(),
            clause_kind,
        ),
        strength,
        RuleScopeSelector("workspace-textpcb", "board", "EXACT", ("textpcb-board-1",)),
        RuleApplicabilityPredicate("ALWAYS"),
        "textpcb-safety",
        priority=100,
        specificity=10,
        control_policy=control,
        severity="CRITICAL" if strength == "HARD_FLOOR" else "MEDIUM",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )


def state_with(record: ObligationRecord) -> dict:
    state = default_calculus_state()
    state["obligations"][record.obligation_id] = record.to_dict()
    return normalize_calculus_state(state)


def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_fixture_manifest_is_closed_fingerprinted_and_complete():
    document = manifest()
    schema = json.loads(
        (ROOT / "schemas/textpcb-s4-safety-fixture.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    validate(document, schema)
    payload = deepcopy(document)
    supplied = payload.pop("suite_fingerprint")
    assert supplied == semantic_fingerprint(payload)
    changed = deepcopy(document)
    changed["unknown_field"] = True
    with pytest.raises(ValidationError):
        validate(changed, schema)
    required = {
        "dimensional-mismatch",
        "trace-width-clearance-manufacturing",
        "drc-erc-hard-vs-preference",
        "controlled-waiver-provenance",
        "thermal-power-signal-scenarios",
        "tolerance-quantization",
        "production-alternative-equivalence-diversity",
        "degraded-dependency-loss",
        "degraded-unknown",
        "hard-hazard-dominance",
        "irreversibility-assurance",
        "scarcity-cannot-relax-floor",
    }
    assert {case["fixture_id"] for case in document["cases"]} == required


def test_dimensional_mismatch_fixture_fails_before_solving():
    width = Quantity(
        "DECIMAL",
        number("0.2"),
        length_dimension(),
        UnitBinding("mm", "mm"),
    )
    current = Quantity(
        "DECIMAL",
        number("1.0"),
        DimensionVector({"electric_current": 1}),
        UnitBinding("A", "A"),
    )
    with pytest.raises(ValueError, match="dimensionally inconsistent"):
        require_dimensionally_compatible(width, current)


def test_trace_width_clearance_and_drc_erc_hard_floor_dominate_preferences():
    width = Quantity(
        "DECIMAL",
        number("0.15"),
        length_dimension(),
        UnitBinding("mm", "mm"),
    )
    clearance = Quantity(
        "DECIMAL",
        number("0.1"),
        length_dimension(),
        UnitBinding("mm", "mm"),
    )
    require_dimensionally_compatible(width, clearance)
    drc = rule("minimum-clearance", strength="HARD_FLOOR")
    routing = rule("short-route-preference", strength="PREFERENCE")
    assert drc.precedence_key > routing.precedence_key
    assert drc.control_policy.waiver_mode == "FORBIDDEN"
    assert routing.strength == "PREFERENCE"


def test_controlled_waiver_provenance_is_review_only_and_creates_debt():
    policy = rule("approved-fab-exception", strength="POLICY", waivable=True)
    risk = RiskAssessment(
        envelope_id="risk-envelope-textpcb",
        envelope_fingerprint="a" * 64,
        irreversibility_profile_id="profile-textpcb",
        irreversibility_fingerprint="b" * 64,
        status="REQUIRES_EXPLICIT_ACCEPTANCE",
        required_assurance_level="ELEVATED",
        available_assurance_level="STRONG",
        acceptance_hazard_ids=("reduced-manufacturing-margin",),
    )
    obligation = ObligationRecord(
        "O-post-fab-inspection",
        "Perform post-fabrication inspection and attach evidence",
        status="AVAILABLE",
        required_evidence_types=["inspection-report"],
        scope={"scope_id": "board"},
    )
    state = state_with(obligation)
    authority = RuleSourceAuthorityRef(
        "principal-textpcb",
        "authority-grant-textpcb",
        "c" * 64,
        "rule.waive",
    )
    override = bind_manual_override(
        policy,
        risk,
        (state["obligations"][obligation.obligation_id],),
        principal_id="principal-textpcb",
        authority=authority,
        reason="Use the qualified alternate fabricator for this exact revision",
        validity=OverrideValidityWindow("textpcb-sequence", 100, 120),
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
        authority_evidence_ids=("evidence-authority-textpcb",),
        evidence_ids=("evidence-fab-qualification",),
    )
    assessment = evaluate_manual_override(
        override,
        (policy,),
        (risk,),
        state,
        clock_id="textpcb-sequence",
        sequence=110,
    )
    assert assessment.status == "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW"
    assert assessment.waiver_performed is False
    assert assessment.authority_granted is False
    assert assessment.history_deleted is False
    debt = project_epistemic_debt(
        state,
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    assert tuple(value.obligation_id for value in debt.items) == (
        "O-post-fab-inspection",
    )


def test_thermal_power_and_signal_scenarios_are_explicit_and_distinct():
    scenarios = tuple(
        Scenario(
            f"TextPCB {domain.title()} Analysis",
            REVISION_ID,
            REVISION_FINGERPRINT,
            (ScenarioBinding("analysis_domain", "LITERAL", literal_value=domain),),
            tags=(domain.lower(), "textpcb"),
        )
        for domain in ("THERMAL", "POWER", "SIGNAL")
    )
    assert len({value.scenario_id for value in scenarios}) == 3
    assert len({value.fingerprint for value in scenarios}) == 3
    assert {value.bindings[0].literal_value for value in scenarios} == {
        "THERMAL",
        "POWER",
        "SIGNAL",
    }


def test_tolerance_and_quantization_are_conservative_at_safety_boundary():
    safety_rule = rule(
        "maximum-board-temperature",
        strength="HARD_FLOOR",
        clause_kind="SAFETY_INVARIANT",
    )
    allowed = Quantity(
        "INTERVAL",
        IntervalValue(number("0"), number("100")),
        DimensionVector({"temperature": 1}),
        UnitBinding("degC", "degC"),
    )
    observed = Quantity(
        "DECIMAL",
        number("99.5"),
        DimensionVector({"temperature": 1}),
        UnitBinding("degC", "degC"),
        tolerance=ToleranceSpec("ABSOLUTE", number("1")),
    )
    envelope = SafetyEnvelope(
        "TextPCB thermal envelope",
        subject(),
        REVISION_ID,
        REVISION_FINGERPRINT,
        (
            SafetyModeEnvelope(
                "THERMAL_TEST",
                (
                    bind_safety_constraint(
                        "board-temperature",
                        "temperature",
                        safety_rule,
                        allowed,
                        evidence_ids=("evidence-thermal-rule",),
                    ),
                ),
            ),
        ),
    )
    state = HybridState(
        "TextPCB observed thermal state",
        subject(),
        "THERMAL_TEST",
        REVISION_ID,
        REVISION_FINGERPRINT,
        (
            observe_hybrid_quantity(
                "temperature",
                observed,
                evidence_ids=("evidence-temperature",),
            ),
        ),
        mode_evidence_ids=("evidence-mode",),
    )
    result = assess_safety_envelope(
        envelope,
        state,
        (safety_rule,),
        (allowed, observed),
    )
    assert result.status == "INDETERMINATE"
    quantized = Quantity(
        "DECIMAL",
        number("95"),
        DimensionVector({"temperature": 1}),
        UnitBinding("degC", "degC"),
        quantization=QuantizationSpec(number("1"), rounding_rule="HALF_UP"),
    )
    quantized_state = HybridState(
        "TextPCB quantized thermal state",
        subject(),
        "THERMAL_TEST",
        REVISION_ID,
        REVISION_FINGERPRINT,
        (
            observe_hybrid_quantity(
                "temperature",
                quantized,
                evidence_ids=("evidence-quantized-temperature",),
            ),
        ),
        mode_evidence_ids=("evidence-mode",),
    )
    result = assess_safety_envelope(
        envelope,
        quantized_state,
        (safety_rule,),
        (allowed, quantized),
    )
    assert result.status == "INDETERMINATE"
    assert result.constraint_assessments[0].relation == "UNSUPPORTED"


def test_production_alternatives_are_projection_equivalent_but_identity_diverse():
    millimetres = Quantity(
        "DECIMAL",
        number("10"),
        length_dimension(),
        UnitBinding(
            "mm",
            "m",
            ExactNumber.rational(1, 1000),
            ExactNumber.integer(0),
        ),
        metadata={"fabricator": "A"},
    )
    metres = Quantity(
        "DECIMAL",
        number("0.01"),
        length_dimension(),
        UnitBinding("m", "m"),
        metadata={"fabricator": "B"},
    )
    assert millimetres.fingerprint != metres.fingerprint
    assert (
        millimetres.canonical_projection_fingerprint
        == metres.canonical_projection_fingerprint
    )
    assert millimetres.quantity_id != metres.quantity_id


def test_degraded_dependency_loss_and_unknown_never_amplify_authority():
    contract = degraded_operation_contract()
    serialized = json.dumps(contract, sort_keys=True)
    assert "FAIL_CLOSED_TO_SAFE_HOLD_WITH_NO_NEW_EFFECTS" in serialized
    assert (
        "EMERGENCY_RESPONSE_INTENT_ONLY_NEVER_CREATES_OR_EXPANDS_AUTHORITY"
        in serialized
    )
    assert contract["assessment_is_authorization"] is False
    assert contract["assessment_activates_mode"] is False
    assert contract["assessment_proves_safety"] is False
    assert contract["parallel_mode_store"] == "NONE"


def risk_fixture() -> tuple[
    EngineeringRule,
    RiskEnvelope,
    EffectIrreversibility,
    IrreversibilityAssurancePolicy,
]:
    hard = rule(
        "no-overtemperature-fabrication",
        strength="HARD_FLOOR",
        clause_kind="SAFETY_INVARIANT",
    )
    envelope = RiskEnvelope(
        "TextPCB fabrication risk envelope",
        subject(),
        REVISION_ID,
        REVISION_FINGERPRINT,
        (
            HazardRef(
                "overtemperature",
                hard.rule_revision_id,
                hard.fingerprint,
                "CATASTROPHIC",
                "PROHIBITED",
                evidence_ids=("evidence-hazard-rule",),
            ),
        ),
    )
    policy = IrreversibilityAssurancePolicy(
        {
            "REVERSIBLE": "BASELINE",
            "CONDITIONALLY_REVERSIBLE": "ELEVATED",
            "COSTLY_TO_REVERSE": "STRONG",
            "IRREVERSIBLE": "MAXIMUM",
            "UNKNOWN": "MAXIMUM",
        }
    )
    return (
        hard,
        envelope,
        EffectIrreversibility(
            "fabricate",
            subject(),
            "REVERSIBLE",
            recovery_operations=("discard-unfabricated-order",),
            evidence_ids=("evidence-irreversibility",),
        ),
        policy,
    )


def test_present_and_unknown_hard_hazards_dominate_all_assurance():
    hard, envelope, reversible, policy = risk_fixture()
    present = evaluate_risk(
        envelope,
        (hard,),
        (HazardObservation("overtemperature", "PRESENT", ("obs-present",)),),
        reversible,
        policy,
        available_assurance_level="MAXIMUM",
    )
    assert present.status == "BLOCKED_HARD_HAZARD"
    unknown = evaluate_risk(
        envelope,
        (hard,),
        (HazardObservation("overtemperature", "UNKNOWN", ("obs-unknown",)),),
        reversible,
        policy,
        available_assurance_level="MAXIMUM",
    )
    assert unknown.status == "BLOCKED_INDETERMINATE_HAZARD"
    assert present.effect_authority_granted is False
    assert present.resource_override_performed is False
    assert present.objective_override_performed is False


def test_irreversibility_escalates_assurance_and_scarcity_never_relaxes_floor():
    hard, envelope, _, policy = risk_fixture()
    irreversible = EffectIrreversibility(
        "fabricate",
        subject(),
        "IRREVERSIBLE",
        recovery_operations=(),
        evidence_ids=("evidence-irreversible",),
    )
    result = evaluate_risk(
        envelope,
        (hard,),
        (HazardObservation("overtemperature", "ABSENT", ("obs-absent",)),),
        irreversible,
        policy,
        available_assurance_level="BASELINE",
    )
    assert result.status == "REQUIRES_ADDITIONAL_ASSURANCE"
    contract = risk_irreversibility_contract()
    assert (
        contract["resource_relation"]
        == "RESOURCE_SCARCITY_CANNOT_RELAX_HARD_HAZARD_OR_ASSURANCE_REQUIREMENT"
    )
    assert (
        contract["optimization_relation"]
        == "OBJECTIVE_IMPROVEMENT_CANNOT_OVERRIDE_PRESENT_OR_UNKNOWN_HARD_HAZARD"
    )


def test_fixture_suite_creates_no_public_or_runtime_surface():
    assert not hasattr(aasm, "TextPCBSafetyFixture")
    assert not any(
        name.startswith(("textpcb_", "safety_governance_"))
        for name in aasm.SUPPORTED_ENGINE_METHODS
    )
    document = manifest()
    assert document["runtime_admission"] == "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE"
