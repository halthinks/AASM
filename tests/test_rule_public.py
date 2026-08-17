from __future__ import annotations

import aasm
from aasm import public_active_engineering_quantity as parent
from aasm import public_active_engineering_rule as candidate
from aasm._calculus_model import LearnedConstraint


def test_rule_public_candidate_is_additive_over_qualified_quantity_parent():
    parent_report = parent.validate_public_api_contract()
    candidate_report = candidate.validate_public_api_contract()
    root_report = aasm.validate_public_api_contract()
    assert parent_report["valid"], parent_report
    assert candidate_report["valid"], candidate_report
    assert root_report["valid"], root_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.16"
    assert candidate.PUBLIC_API_CONTRACT["contract_version"] == "0.32.17"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.16"
    assert candidate.AASMEngine is parent.AASMEngine
    assert candidate.AASMEngine is aasm.AASMEngine
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(candidate.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(candidate.SUPPORTED_INSPECTION_SURFACES)
    assert candidate.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert not hasattr(aasm, "EngineeringRule")


def test_rule_public_candidate_exports_exact_rule_contract_and_firewalls():
    contract = candidate.public_api_contract()["engineering_rule"]
    assert contract["contract_id"] == "aasm.rule.v1"
    assert contract["contract_version"] == "0.1.0"
    assert contract["strengths"] == ["HARD_FLOOR", "HARD", "POLICY", "PREFERENCE", "ADVISORY"]
    assert contract["applicability"] == "EXPLICIT_PORTABLE_CONTEXT_MATCH_TRI_STATE_FAIL_CLOSED"
    assert contract["precedence"] == "STRENGTH_THEN_SPECIFICITY_THEN_PRIORITY_WITHIN_EXPLICIT_GROUP"
    assert contract["precedence_is_objective_priority"] is False
    assert contract["precedence_authorizes_override"] is False
    assert contract["hard_floor_waiver"] == "FORBIDDEN"
    assert contract["hard_floor_override"] == "FORBIDDEN"
    assert contract["learned_constraint_relation"] == "DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT"
    assert contract["rule_to_constraint_lowering"] == "NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "CANDIDATE_PRE_ADMISSION"
    assert contract["engine_state_integration"] == "NONE_SEMANTIC_RULE_FOUNDATION_ONLY"
    assert contract["parallel_rule_registry"] == "NONE"
    assert contract["current_rule_pointer"] == "NONE"
    assert contract["parallel_constraint_engine"] == "NONE"
    assert contract["parallel_authority_evaluator"] == "NONE"
    assert contract["hidden_wall_clock"] == "NONE"
    assert contract["rule_existence_grants_fact_authority"] is False
    assert contract["rule_existence_grants_effect_authority"] is False
    assert contract["rule_existence_grants_source_authority"] is False


def test_rule_public_candidate_exposes_real_rule_value_types_without_engine_state():
    clause = candidate.RuleClauseRef(
        "aasm.semantic.constraint.v1",
        "clearance-min",
        "c" * 64,
        "CONSTRAINT",
    )
    rule = candidate.EngineeringRule(
        "pcb-clearance",
        clause,
        "HARD",
        candidate.RuleScopeSelector("w", "layout", "EXACT", ("board",)),
        candidate.RuleApplicabilityPredicate("ALWAYS"),
        "pcb-clearance",
        priority=10,
        specificity=2,
        severity="HIGH",
    )
    context = candidate.RuleApplicabilityContext("w", "layout", "board")
    assessment = candidate.evaluate_rule_applicability(rule, context)
    assert assessment.result == "APPLICABLE"
    assert candidate.EngineeringRule.from_dict(rule.to_dict()).fingerprint == rule.fingerprint
    assert "engineering-rule" in candidate.SUPPORTED_INSPECTION_SURFACES
    assert not any(name.startswith("rule_") for name in candidate.SUPPORTED_ENGINE_METHODS)


def test_rule_public_candidate_preserves_learned_constraint_and_objective_separation():
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
    contract = candidate.PUBLIC_API_CONTRACT["engineering_rule"]
    assert contract["learned_constraint_relation"] == "DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT"
    assert contract["precedence_is_objective_priority"] is False
    assert contract["rule_to_constraint_lowering"] == "NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED"


def test_rule_public_candidate_does_not_add_engine_methods_or_runtime_state():
    assert candidate.AASMEngine is parent.AASMEngine
    assert candidate.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    contract = candidate.PUBLIC_API_CONTRACT["engineering_rule"]
    assert contract["engine_state_integration"] == "NONE_SEMANTIC_RULE_FOUNDATION_ONLY"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.16"
