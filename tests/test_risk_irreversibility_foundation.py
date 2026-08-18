from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

from aasm.risk_irreversibility import (
    ASSURANCE_LEVELS,
    HAZARD_SEVERITIES,
    HAZARD_STATUSES,
    HAZARD_TREATMENTS,
    IRREVERSIBILITY_CLASSES,
    RISK_ASSESSMENT_STATUSES,
    EffectIrreversibility,
    HazardObservation,
    HazardRef,
    IrreversibilityAssurancePolicy,
    RiskAssessment,
    RiskEnvelope,
    evaluate_risk,
    risk_irreversibility_contract,
)
from aasm.rule import EngineeringRule, RuleApplicabilityPredicate, RuleClauseRef, RuleScopeSelector
from aasm.semantic_projection import SemanticSubjectRef


ROOT = Path(__file__).resolve().parents[1]


def subject() -> SemanticSubjectRef:
    return SemanticSubjectRef(
        "aasm.physical.subject.v1",
        "actuator-1",
        "a" * 64,
        "problem-revision-1",
        "1" * 64,
    )


def rule(*, rule_id: str, strength: str, clause_id: str) -> EngineeringRule:
    return EngineeringRule(
        rule_id,
        RuleClauseRef(
            "aasm.semantic.constraint.v1",
            clause_id,
            hashlib.sha256(clause_id.encode("utf-8")).hexdigest(),
            "CONSTRAINT",
        ),
        strength,
        RuleScopeSelector("workspace-1", "control", "EXACT", ("actuator-1",)),
        RuleApplicabilityPredicate("ALWAYS"),
        "safety-hazards",
        priority=100,
        specificity=10,
        severity="CRITICAL",
        problem_revision_id="problem-revision-1",
        problem_revision_fingerprint="1" * 64,
    )


def hard_rule() -> EngineeringRule:
    return rule(rule_id="no-overpressure", strength="HARD_FLOOR", clause_id="overpressure")


def mitigation_rule() -> EngineeringRule:
    return rule(rule_id="guard-required", strength="HARD", clause_id="guard")


def acceptance_rule() -> EngineeringRule:
    return rule(rule_id="operator-acceptance", strength="POLICY", clause_id="operator")


def advisory_rule() -> EngineeringRule:
    return rule(rule_id="wear-advisory", strength="ADVISORY", clause_id="wear")


def hazard(rule_obj: EngineeringRule, hazard_id: str, treatment: str, severity: str = "SEVERE") -> HazardRef:
    return HazardRef(
        hazard_id,
        rule_obj.rule_revision_id,
        rule_obj.fingerprint,
        severity,
        treatment,
        evidence_ids=(f"evidence-{hazard_id}",),
    )


def envelope(*hazards: HazardRef) -> RiskEnvelope:
    return RiskEnvelope(
        "actuator-risk-envelope",
        subject(),
        "problem-revision-1",
        "1" * 64,
        tuple(hazards),
    )


def irreversibility(classification: str = "REVERSIBLE", *, recovery: tuple[str, ...] = ("restore",)) -> EffectIrreversibility:
    return EffectIrreversibility(
        "drive",
        subject(),
        classification,
        recovery_operations=recovery,
        evidence_ids=("evidence-irreversibility",),
    )


def assurance_policy(**overrides: str) -> IrreversibilityAssurancePolicy:
    levels = {
        "REVERSIBLE": "BASELINE",
        "CONDITIONALLY_REVERSIBLE": "ELEVATED",
        "COSTLY_TO_REVERSE": "STRONG",
        "IRREVERSIBLE": "MAXIMUM",
        "UNKNOWN": "MAXIMUM",
    }
    levels.update(overrides)
    return IrreversibilityAssurancePolicy(levels)


def observations(**statuses: str) -> tuple[HazardObservation, ...]:
    return tuple(HazardObservation(hazard_id, status, evidence_ids=(f"obs-{hazard_id}",)) for hazard_id, status in sorted(statuses.items()))


def test_risk_irreversibility_vocabularies_and_contract_are_exact():
    assert HAZARD_SEVERITIES == ("MINOR", "MAJOR", "SEVERE", "CATASTROPHIC")
    assert HAZARD_TREATMENTS == ("PROHIBITED", "MITIGATION_REQUIRED", "EXPLICIT_ACCEPTANCE_REQUIRED", "ADVISORY")
    assert HAZARD_STATUSES == ("PRESENT", "ABSENT", "UNKNOWN")
    assert IRREVERSIBILITY_CLASSES == ("REVERSIBLE", "CONDITIONALLY_REVERSIBLE", "COSTLY_TO_REVERSE", "IRREVERSIBLE", "UNKNOWN")
    assert ASSURANCE_LEVELS == ("BASELINE", "ELEVATED", "STRONG", "MAXIMUM")
    assert RISK_ASSESSMENT_STATUSES == (
        "ADMISSIBLE_FOR_PROPOSAL", "BLOCKED_HARD_HAZARD", "BLOCKED_INDETERMINATE_HAZARD",
        "REQUIRES_MITIGATION", "REQUIRES_EXPLICIT_ACCEPTANCE", "REQUIRES_ADDITIONAL_ASSURANCE",
    )
    contract = risk_irreversibility_contract()
    assert contract["risk_contract_id"] == "aasm.risk.envelope.v1"
    assert contract["irreversibility_contract_id"] == "aasm.effect.irreversibility.v1"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


def test_risk_envelope_and_irreversibility_identity_are_deterministic_and_round_trip():
    hard = hard_rule()
    item = envelope(hazard(hard, "overpressure", "PROHIBITED", "CATASTROPHIC"))
    restored = RiskEnvelope.from_dict(item.to_dict())
    assert restored == item
    assert restored.fingerprint == item.fingerprint
    profile = irreversibility("CONDITIONALLY_REVERSIBLE")
    assert EffectIrreversibility.from_dict(profile.to_dict()) == profile


def test_present_hard_floor_hazard_blocks_even_with_maximum_assurance():
    hard = hard_rule()
    item = envelope(hazard(hard, "overpressure", "PROHIBITED", "CATASTROPHIC"))
    result = evaluate_risk(
        item,
        (hard,),
        observations(overpressure="PRESENT"),
        irreversibility("REVERSIBLE"),
        assurance_policy(),
        available_assurance_level="MAXIMUM",
    )
    assert result.status == "BLOCKED_HARD_HAZARD"
    assert result.blocking_hazard_ids == ("overpressure",)
    assert result.effect_authority_granted is False
    assert result.objective_override_performed is False
    assert result.resource_override_performed is False


def test_unknown_hard_floor_hazard_fails_closed_not_absent():
    hard = hard_rule()
    result = evaluate_risk(
        envelope(hazard(hard, "overpressure", "PROHIBITED")),
        (hard,),
        observations(overpressure="UNKNOWN"),
        irreversibility("REVERSIBLE"),
        assurance_policy(),
        available_assurance_level="MAXIMUM",
    )
    assert result.status == "BLOCKED_INDETERMINATE_HAZARD"
    assert result.blocking_hazard_ids == ("overpressure",)


def test_prohibited_hazard_must_reuse_exact_existing_hard_floor_rule():
    preference = rule(rule_id="preference", strength="PREFERENCE", clause_id="pref")
    item = envelope(hazard(preference, "fake-hard-hazard", "PROHIBITED"))
    with pytest.raises(ValueError, match="HARD_FLOOR"):
        evaluate_risk(
            item,
            (preference,),
            observations(**{"fake-hard-hazard": "PRESENT"}),
            irreversibility("REVERSIBLE"),
            assurance_policy(),
            available_assurance_level="MAXIMUM",
        )


def test_mitigation_and_explicit_acceptance_are_requirements_not_waivers_or_authority():
    mitigation = mitigation_rule(); acceptance = acceptance_rule()
    item = envelope(
        hazard(mitigation, "guard-missing", "MITIGATION_REQUIRED"),
        hazard(acceptance, "operator-acceptance", "EXPLICIT_ACCEPTANCE_REQUIRED"),
    )
    result = evaluate_risk(
        item,
        (mitigation, acceptance),
        observations(**{"guard-missing": "PRESENT", "operator-acceptance": "PRESENT"}),
        irreversibility("REVERSIBLE"),
        assurance_policy(),
        available_assurance_level="MAXIMUM",
    )
    assert result.status == "REQUIRES_MITIGATION"
    assert result.mitigation_hazard_ids == ("guard-missing",)
    assert result.acceptance_hazard_ids == ("operator-acceptance",)
    assert result.rule_waiver_performed is False
    assert result.effect_authority_granted is False
    assert result.artifact_acceptance_granted is False


def test_irreversibility_assurance_is_explicit_monotonic_and_unknown_requires_maximum():
    policy = assurance_policy()
    assert policy.required_level("REVERSIBLE") == "BASELINE"
    assert policy.required_level("CONDITIONALLY_REVERSIBLE") == "ELEVATED"
    assert policy.required_level("COSTLY_TO_REVERSE") == "STRONG"
    assert policy.required_level("IRREVERSIBLE") == "MAXIMUM"
    assert policy.required_level("UNKNOWN") == "MAXIMUM"
    with pytest.raises(ValueError, match="monotonic"):
        assurance_policy(CONDITIONALLY_REVERSIBLE="MAXIMUM", COSTLY_TO_REVERSE="ELEVATED")
    with pytest.raises(ValueError, match="UNKNOWN"):
        assurance_policy(UNKNOWN="STRONG")


def test_irreversible_effect_requires_stronger_assurance_but_does_not_create_authority():
    advisory = advisory_rule()
    item = envelope(hazard(advisory, "wear", "ADVISORY", "MINOR"))
    profile = irreversibility("IRREVERSIBLE", recovery=())
    low = evaluate_risk(
        item, (advisory,), observations(wear="ABSENT"), profile, assurance_policy(),
        available_assurance_level="BASELINE",
    )
    assert low.status == "REQUIRES_ADDITIONAL_ASSURANCE"
    assert low.required_assurance_level == "MAXIMUM"
    high = evaluate_risk(
        item, (advisory,), observations(wear="ABSENT"), profile, assurance_policy(),
        available_assurance_level="MAXIMUM",
    )
    assert high.status == "ADMISSIBLE_FOR_PROPOSAL"
    assert high.effect_authority_granted is False


def test_irreversible_profile_cannot_claim_recovery_operation():
    with pytest.raises(ValueError, match="cannot claim recovery"):
        irreversibility("IRREVERSIBLE", recovery=("restore",))


def test_risk_evaluation_requires_exact_rule_fingerprint_and_exact_hazard_observation_set():
    hard = hard_rule(); item = envelope(hazard(hard, "overpressure", "PROHIBITED"))
    wrong = rule(rule_id="different", strength="HARD_FLOOR", clause_id="different")
    with pytest.raises(ValueError, match="exact supplied EngineeringRule"):
        evaluate_risk(item, (wrong,), observations(overpressure="PRESENT"), irreversibility(), assurance_policy(), available_assurance_level="MAXIMUM")
    with pytest.raises(ValueError, match="exactly one observation"):
        evaluate_risk(item, (hard,), (), irreversibility(), assurance_policy(), available_assurance_level="MAXIMUM")


def test_risk_and_irreversibility_subjects_are_exact_revision_bound():
    hard = hard_rule()
    with pytest.raises(ValueError, match="subject revision"):
        RiskEnvelope(
            "bad-revision",
            SemanticSubjectRef("aasm.physical.subject.v1", "actuator-1", "a" * 64, "problem-revision-2", "2" * 64),
            "problem-revision-1",
            "1" * 64,
            (hazard(hard, "overpressure", "PROHIBITED"),),
        )
    other_subject = SemanticSubjectRef("aasm.physical.subject.v1", "actuator-2", "b" * 64, "problem-revision-1", "1" * 64)
    with pytest.raises(ValueError, match="exact same semantic subject"):
        evaluate_risk(
            envelope(hazard(hard, "overpressure", "PROHIBITED")),
            (hard,), observations(overpressure="ABSENT"),
            EffectIrreversibility("drive", other_subject, "REVERSIBLE", recovery_operations=("restore",)),
            assurance_policy(), available_assurance_level="MAXIMUM",
        )


def test_risk_contract_separates_resource_cost_objective_and_authority_planes():
    contract = risk_irreversibility_contract()
    assert contract["hard_hazard_legality"] == "EXACT_EXISTING_AASM_RULE_V1_HARD_FLOOR_REFERENCE_ONLY_NO_SECOND_HARD_FLOOR_SYSTEM"
    assert contract["risk_cost_relation"] == "RISK_IS_NOT_RESOURCE_OR_MONETARY_COST_AND_HAS_NO_SCALAR_COST_COLLAPSE"
    assert contract["optimization_relation"] == "OBJECTIVE_IMPROVEMENT_CANNOT_OVERRIDE_PRESENT_OR_UNKNOWN_HARD_HAZARD"
    assert contract["resource_relation"] == "RESOURCE_SCARCITY_CANNOT_RELAX_HARD_HAZARD_OR_ASSURANCE_REQUIREMENT"
    assert contract["explicit_acceptance"] == "REQUIREMENT_ONLY_NO_WAIVER_OR_AUTHORIZATION_PERFORMED_BY_FOUNDATION"
    assert contract["risk_assessment_is_effect_authority"] is False
    assert contract["risk_assessment_is_rule_waiver"] is False
    assert contract["risk_assessment_is_artifact_acceptance"] is False
    assert contract["risk_assessment_proves_empirical_safety"] is False
    assert contract["parallel_risk_registry"] == "NONE"
    assert contract["parallel_hazard_truth_table"] == "NONE"
    assert contract["parallel_authority_evaluator"] == "NONE"
    assert contract["parallel_resource_plane"] == "NONE"
    assert contract["parallel_objective_plane"] == "NONE"


def test_binary_float_metadata_and_identity_tampering_fail_closed():
    hard = hard_rule()
    with pytest.raises(TypeError, match="binary floating-point"):
        HazardRef("h", hard.rule_revision_id, hard.fingerprint, "SEVERE", "PROHIBITED", metadata={"probability": 0.1})
    with pytest.raises(TypeError, match="binary floating-point"):
        EffectIrreversibility("drive", subject(), "REVERSIBLE", metadata={"confidence": 0.9})
    item = envelope(hazard(hard, "overpressure", "PROHIBITED"))
    changed = deepcopy(item.to_dict()); changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        RiskEnvelope.from_dict(changed)


def test_risk_schemas_are_closed_and_accept_canonical_documents():
    hard = hard_rule(); item = envelope(hazard(hard, "overpressure", "PROHIBITED"))
    profile = irreversibility("CONDITIONALLY_REVERSIBLE")
    policy = assurance_policy()
    assessment = evaluate_risk(
        item, (hard,), observations(overpressure="ABSENT"), profile, policy,
        available_assurance_level="ELEVATED",
    )
    docs = (
        ("risk-envelope.schema.json", item.to_dict()),
        ("effect-irreversibility.schema.json", profile.to_dict()),
        ("irreversibility-assurance-policy.schema.json", policy.to_dict()),
        ("risk-assessment.schema.json", assessment.to_dict()),
    )
    for filename, document in docs:
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        validate(document, schema)
        changed = deepcopy(document); changed["unknown_field"] = True
        with pytest.raises(ValidationError):
            validate(changed, schema)
