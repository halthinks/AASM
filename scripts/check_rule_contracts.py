from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing required rule file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    model = text("src/aasm/rule.py")
    schema_text = text("schemas/rule.schema.json")
    tests = text("tests/test_rule_foundation.py")
    foundation = text("src/aasm/runtime_v56_foundation.py")
    public_parent = text("src/aasm/public_active_engineering_quantity.py")
    calculus = text("src/aasm/_calculus_model.py")
    decision_vector = text("src/aasm/decision_vector_ir.py")
    effect_capability = text("src/aasm/effect_capability.py")
    quantity = text("src/aasm/quantity.py")
    postcondition_runtime = text("src/aasm/external_machine_postcondition_runtime.py")
    numeric_tolerance_schema = text("schemas/numeric-tolerance.schema.json")

    schema = json.loads(schema_text)
    require(schema["properties"]["contract_id"]["const"] == "aasm.rule.v1", "rule schema contract ID drift")
    require(schema["properties"]["contract_version"]["const"] == "0.1.0", "rule schema contract version drift")
    require(schema.get("additionalProperties") is False, "rule schema must be top-level closed")
    for name in (
        "ruleClauseRef",
        "ruleSourceAuthorityRef",
        "ruleScopeSelector",
        "ruleApplicabilityPredicate",
        "ruleControlPolicy",
        "externalReference",
    ):
        require(schema["$defs"][name].get("additionalProperties") is False, f"rule schema nested object is not closed: {name}")

    required_model_tokens = (
        'RULE_CONTRACT_ID = "aasm.rule.v1"',
        'RULE_CONTRACT_VERSION = "0.1.0"',
        '"HARD_FLOOR"',
        '"HARD"',
        '"POLICY"',
        '"PREFERENCE"',
        '"ADVISORY"',
        '"APPLICABLE"',
        '"NOT_APPLICABLE"',
        '"INDETERMINATE"',
        '"EXACT"',
        '"DESCENDANT_OR_SELF"',
        '"ANY_IN_WORKSPACE"',
        '"FORBIDDEN"',
        '"EXPLICIT_AUTHORIZED"',
        '"STRICTLY_STRONGER_EXPLICIT"',
        '"SAME_OR_STRONGER_EXPLICIT"',
        "class RuleClauseRef",
        "class RuleSourceAuthorityRef",
        "class RuleScopeSelector",
        "class RuleApplicabilityPredicate",
        "class RuleControlPolicy",
        "class RuleApplicabilityContext",
        "class EngineeringRule",
        "class RuleApplicabilityAssessment",
        "def evaluate_rule_applicability",
        "def compare_rule_precedence",
        "def rule_waiver_structurally_eligible",
        "def rule_override_structurally_eligible",
        "def rule_contract",
        '"EXPLICIT_PORTABLE_CONTEXT_MATCH_TRI_STATE_FAIL_CLOSED"',
        '"STRENGTH_THEN_SPECIFICITY_THEN_PRIORITY_WITHIN_EXPLICIT_GROUP"',
        '"STRUCTURAL_ELIGIBILITY_ONLY_EXISTING_SCOPED_AUTHORITY_MUST_AUTHORIZE_LATER_RUNTIME_ACTION"',
        '"EXACT_EXISTING_SCOPED_AUTHORITY_GRANT_REFERENCE_ONLY_NOT_VERIFIED_BY_FOUNDATION"',
        '"DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT"',
        '"NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED"',
        '"parallel_rule_registry": "NONE"',
        '"current_rule_pointer": "NONE"',
        '"parallel_constraint_engine": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
        "duplicate external reference identity in rule contract",
        "cannot require and forbid the same attribute value",
    )
    for token in required_model_tokens:
        require(token in model, f"rule model contract missing token: {token}")

    banned_model_tokens = (
        "FactAuthority(",
        "StateClaim(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "authorize_scoped_request(",
        "UNIT_REGISTRY =",
        "GLOBAL_UNIT_REGISTRY",
        "register_rule(",
        "current_rule_store",
        "current_rule_state",
        "latest_rule",
        "datetime.now(",
        "time.time(",
        "Callable[",
        "eval(",
        "exec(",
    )
    for token in banned_model_tokens:
        require(token not in model, f"rule model violates source firewall with token: {token}")

    required_test_tokens = (
        "test_rule_round_trip_identity_and_external_evidence_order_are_deterministic",
        "test_rule_schema_is_closed_portable_and_accepts_canonical_rule",
        "test_binary_float_executable_predicates_and_portable_integer_overflow_fail_closed",
        "test_scope_and_subject_applicability_is_deterministic",
        "test_problem_revision_applicability_distinguishes_missing_mismatch_and_exact",
        "test_external_revision_applicability_distinguishes_missing_mismatch_and_exact",
        "test_duplicate_external_reference_identity_is_rejected_in_rule_and_context",
        "test_context_match_predicate_is_portable_tri_state_and_fail_closed",
        "test_precedence_is_strength_then_specificity_then_priority_only_within_group",
        "test_hard_floor_cannot_be_waived_or_overridden_even_by_control_policy",
        "test_waiver_structural_eligibility_requires_exact_capability_but_is_not_authority",
        "test_override_structural_eligibility_obeys_explicit_strength_policy_not_objective_priority",
        "test_source_authority_is_exact_reference_only_and_does_not_verify_or_mint_authority",
        "test_clause_authority_rule_and_context_tampering_fail_closed",
        "test_rule_foundation_is_distinct_from_formal_calculus_learned_constraints",
        "test_existing_decision_vector_hard_floor_remains_separate_and_unchanged",
        "test_rule_contract_firewalls_and_pre_admission_boundary_are_explicit",
        "test_rule_public_admission_does_not_imply_runtime_composition",
    )
    for token in required_test_tokens:
        require(token in tests, f"rule adversarial corpus missing test: {token}")

    # Runtime pre-admission remains strict even after qualified public semantic exposure.
    # The active package-root surface is checked separately by check_rule_public.py.
    for source, label in (
        (foundation, "runtime_v56_foundation"),
        (public_parent, "qualified 0.32.16 parent overlay"),
        (effect_capability, "effect capability"),
        (postcondition_runtime, "external machine postcondition runtime"),
        (quantity, "quantity foundation"),
    ):
        require("from .rule" not in source, f"rule leaked into {label}")
        require("EngineeringRule" not in source, f"EngineeringRule leaked into {label}")
        require("aasm.rule.v1" not in source, f"rule contract leaked into {label}")

    # Existing formal calculus remains HARD|SOFT only; Rule must not rewrite it.
    require('if self.strength not in {"HARD", "SOFT"}' in calculus, "learned-constraint strength vocabulary changed")
    require('raise ValueError("constraint strength must be HARD or SOFT")' in calculus, "learned-constraint fail-closed boundary changed")
    require("HARD_FLOOR" not in calculus, "engineering rule strength leaked into formal learned constraints")
    require("from .rule" not in calculus, "formal calculus imported engineering rule foundation")

    # Objective hard floors are an existing distinct optimization seam.
    require("class DecisionHardFloor" in decision_vector, "existing decision-vector hard-floor type missing")
    require('HARD_FLOOR_SENSES = ("<=", ">=", "==")' in decision_vector, "decision-vector hard-floor semantics drift")
    require("from .rule" not in decision_vector, "engineering rule foundation leaked into decision-vector IR")

    # Quantity and numeric tolerance remain independent qualified/existing semantics.
    require('QUANTITY_CONTRACT_ID = "aasm.quantity.v1"' in quantity, "qualified Quantity contract drift")
    require('"runtime_admission": "PRE_ADMISSION_ONLY"' in quantity, "Quantity runtime claim ceiling drift")
    require('"contract_id": {"const": "aasm.numeric.tolerance.v1"}' in numeric_tolerance_schema, "legacy solver numeric tolerance contract drift")
    require("aasm.rule.v1" not in numeric_tolerance_schema, "engineering rule semantics leaked into numeric tolerance schema")

    print("S4 aasm.rule.v1 foundation source contracts: PASS")


if __name__ == "__main__":
    main()
