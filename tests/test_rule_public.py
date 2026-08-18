from __future__ import annotations

import aasm
from aasm import public_active_engineering_quantity as parent
from aasm import public_active_engineering_rule as active
from aasm._calculus_model import LearnedConstraint


def test_rule_public_adoption_is_additive_over_qualified_quantity_parent():
    parent_report = parent.validate_public_api_contract()
    active_report = active.validate_public_api_contract()
    root_report = aasm.validate_public_api_contract()
    assert parent_report["valid"], parent_report
    assert active_report["valid"], active_report
    assert root_report["valid"], root_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.16"
    assert active.PUBLIC_API_CONTRACT["contract_version"] == "0.32.17"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert active.AASMEngine is parent.AASMEngine
    assert active.AASMEngine is aasm.AASMEngine
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(active.SUPPORTED_PUBLIC_IMPORTS)
    assert set(active.SUPPORTED_PUBLIC_IMPORTS).issubset(aasm.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(active.SUPPORTED_INSPECTION_SURFACES)
    assert active.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert aasm.SUPPORTED_ENGINE_METHODS == active.SUPPORTED_ENGINE_METHODS
    assert aasm.EngineeringRule is active.EngineeringRule
    assert aasm.PUBLIC_API_CONTRACT["degraded_operation"]["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert aasm.PUBLIC_API_CONTRACT["degraded_operation"]["mode_activation"] == "NONE"


def test_rule_public_adoption_exports_exact_rule_contract_and_firewalls():
    contract = aasm.public_api_contract()["engineering_rule"]
    assert contract["contract_id"] == "aasm.rule.v1"
    assert contract["contract_version"] == "0.1.0"
    assert contract["strengths"] == ["HARD_FLOOR", "HARD", "POLICY", "PREFERENCE", "ADVISORY"]
    assert contract["applicability"] == "EXPLICIT_PORTABLE_CONTEXT_MATCH_TRI_STATE_FAIL_CLOSED"
    assert contract["precedence"] == "STRENGTH_THEN_SPECIFICITY_THEN_PRIORITY_WITHIN_EXPLICIT_GROUP"
    assert contract["precedence_is_objective_priority"] is False
    assert contract["precedence_authorizes_override"] is False
    assert contract["hard_floor_waiver"] == "FORBIDDEN"
    assert contract["hard_floor_override"] == "FORBIDDEN"
    assert contract["waiver_override_authority"] == "STRUCTURAL_ELIGIBILITY_ONLY_EXISTING_SCOPED_AUTHORITY_MUST_AUTHORIZE_LATER_RUNTIME_ACTION"
    assert contract["source_authority"] == "EXACT_EXISTING_SCOPED_AUTHORITY_GRANT_REFERENCE_ONLY_NOT_VERIFIED_BY_FOUNDATION"
    assert contract["learned_constraint_relation"] == "DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT"
    assert contract["rule_to_constraint_lowering"] == "NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "QUALIFIED"
    assert contract["engine_state_integration"] == "NONE_SEMANTIC_RULE_FOUNDATION_ONLY"
    assert contract["parallel_rule_registry"] == "NONE"
    assert contract["current_rule_pointer"] == "NONE"
    assert contract["parallel_constraint_engine"] == "NONE"
    assert contract["parallel_authority_evaluator"] == "NONE"
    assert contract["hidden_wall_clock"] == "NONE"
    assert contract["rule_existence_grants_fact_authority"] is False
    assert contract["rule_existence_grants_effect_authority"] is False
    assert contract["rule_existence_grants_source_authority"] is False


def test_rule_public_adoption_exposes_real_rule_value_types_without_engine_state():
    clause = aasm.RuleClauseRef(
        "aasm.semantic.constraint.v1",
        "clearance-min",
        "c" * 64,
        "CONSTRAINT",
    )
    rule = aasm.EngineeringRule(
        "pcb-clearance",
        clause,
        "HARD",
        aasm.RuleScopeSelector("w", "layout", "EXACT", ("board",)),
        aasm.RuleApplicabilityPredicate("ALWAYS"),
        "pcb-clearance",
        priority=10,
        specificity=2,
        severity="HIGH",
    )
    context = aasm.RuleApplicabilityContext("w", "layout", "board")
    assessment = aasm.evaluate_rule_applicability(rule, context)
    assert assessment.result == "APPLICABLE"
    assert aasm.EngineeringRule.from_dict(rule.to_dict()).fingerprint == rule.fingerprint
    assert "engineering-rule" in active.SUPPORTED_INSPECTION_SURFACES
    assert "engineering-rule" in aasm.SUPPORTED_INSPECTION_SURFACES
    assert not any(name.startswith("rule_") for name in active.SUPPORTED_ENGINE_METHODS)


def test_rule_public_adoption_preserves_learned_constraint_and_objective_separation():
    hard = LearnedConstraint(
        "learned-hard",
        [{"subject": "route", "op": "EQ", "value": "A"}],
        "conflict-1",
        "explanation-1",
        ["evidence-1"],
        strength="HARD",
    )
    soft = LearnedConstraint(
        "learned-soft",
        [{"subject": "route", "op": "EQ", "value": "B"}],
        "conflict-2",
        "explanation-2",
        ["evidence-2"],
        strength="SOFT",
    )
    assert hard.strength == "HARD"
    assert soft.strength == "SOFT"
    contract = aasm.PUBLIC_API_CONTRACT["engineering_rule"]
    assert contract["learned_constraint_relation"] == "DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT"
    assert contract["precedence_is_objective_priority"] is False
    assert contract["rule_to_constraint_lowering"] == "NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED"


def test_rule_public_adoption_does_not_add_engine_methods_or_runtime_state():
    assert aasm.AASMEngine is active.AASMEngine
    assert active.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert aasm.SUPPORTED_ENGINE_METHODS == active.SUPPORTED_ENGINE_METHODS
    contract = aasm.PUBLIC_API_CONTRACT["engineering_rule"]
    assert contract["engine_state_integration"] == "NONE_SEMANTIC_RULE_FOUNDATION_ONLY"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert active.PUBLIC_API_CONTRACT["contract_version"] == "0.32.17"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert aasm.PUBLIC_API_CONTRACT["degraded_operation"]["runtime_admission"] == "PRE_ADMISSION_ONLY"
