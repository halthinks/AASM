from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing active engineering Rule public file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    active = text("src/aasm/public_active_engineering_rule.py")
    parent = text("src/aasm/public_active_engineering_quantity.py")
    semantic_parent = text("src/aasm/public_active_semantic_projection.py")
    s44_child = text("src/aasm/public_active_uncertainty_scenario_trace.py")
    package_init = text("src/aasm/__init__.py")
    foundation = text("src/aasm/runtime_v56_foundation.py")
    rule_model = text("src/aasm/rule.py")
    calculus = text("src/aasm/_calculus_model.py")
    decision_vector = text("src/aasm/decision_vector_ir.py")
    tests = text("tests/test_rule_public.py")

    require('"contract_version": "0.32.17"' in active, "engineering Rule adoption version drift")
    for token in (
        "RULE_CONTRACT_ID",
        "RULE_CONTRACT_VERSION",
        "RULE_STRENGTHS",
        "EngineeringRule",
        "RuleApplicabilityContext",
        "RuleApplicabilityPredicate",
        "RuleClauseRef",
        "RuleControlPolicy",
        "RuleScopeSelector",
        "RuleSourceAuthorityRef",
        "RuleApplicabilityAssessment",
        "evaluate_rule_applicability",
        "compare_rule_precedence",
        "rule_waiver_structurally_eligible",
        "rule_override_structurally_eligible",
        "rule_contract",
        '"engineering-rule"',
        '"engineering_rule"',
        '"public_admission": "QUALIFIED"',
        '"engine_state_integration": "NONE_SEMANTIC_RULE_FOUNDATION_ONLY"',
        '"PRE_ADMISSION_ONLY"',
        '"DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT"',
        '"NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED"',
    ):
        require(token in active, f"engineering Rule public surface missing token: {token}")

    require("from . import public_active_engineering_quantity as _base" in active, "engineering Rule surface does not inherit qualified 0.32.16 parent")
    require("AASMEngine = _base.AASMEngine" in active, "engineering Rule surface forked AASMEngine")
    require('SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))' in active, "engineering Rule surface changed engine method set")

    # Rule remains independently qualified beneath the additive 0.32.18 -> 0.32.19 chain.
    require('from . import public_active_engineering_rule as _base' in semantic_parent, "qualified 0.32.18 surface does not inherit Rule parent")
    require('PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.17"' in semantic_parent, "semantic projection parent version drift")
    require('from . import public_active_semantic_projection as _base' in s44_child, "active 0.32.19 surface does not inherit qualified 0.32.18 parent")
    require('PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"' in s44_child, "active S4.4 parent version drift")
    require('from .public_active_uncertainty_scenario_trace import *' in package_init, "qualified 0.32.19 S4.4 surface is not package root")
    require('from .public_active_uncertainty_scenario_trace import __version__, AASMEngine' in package_init, "package root does not bind qualified 0.32.19 helpers")
    require("from .rule" not in parent, "Rule leaked backward into qualified 0.32.16 parent")
    require("aasm.rule.v1" not in parent, "Rule contract leaked backward into qualified 0.32.16 parent")

    # Public semantic admission still does not imply runtime state composition.
    require("from .rule" not in foundation, "Rule semantic foundation was composed into runtime_v56 engine state")
    require("EngineeringRule" not in foundation, "EngineeringRule leaked into runtime_v56 foundation")
    require('"runtime_admission": "PRE_ADMISSION_ONLY"' in rule_model, "Rule foundation runtime claim ceiling drift")

    # Existing formal learned constraints and optimization hard floors remain separate.
    require('if self.strength not in {"HARD", "SOFT"}' in calculus, "learned-constraint strength vocabulary changed")
    require("HARD_FLOOR" not in calculus, "engineering Rule strength leaked into learned constraints")
    require("from .rule" not in calculus, "formal calculus imported engineering Rule foundation")
    require("class DecisionHardFloor" in decision_vector, "existing decision-vector hard-floor type missing")
    require("from .rule" not in decision_vector, "engineering Rule foundation leaked into decision-vector IR")

    for token in (
        "FactAuthority(",
        "StateClaim(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "register_rule(",
        "current_rule_store",
        "latest_rule",
    ):
        require(token not in active, f"engineering Rule public surface violates firewall with token: {token}")

    for token in (
        "test_rule_public_adoption_is_additive_over_qualified_quantity_parent",
        "test_rule_public_adoption_exports_exact_rule_contract_and_firewalls",
        "test_rule_public_adoption_exposes_real_rule_value_types_without_engine_state",
        "test_rule_public_adoption_preserves_learned_constraint_and_objective_separation",
        "test_rule_public_adoption_does_not_add_engine_methods_or_runtime_state",
    ):
        require(token in tests, f"engineering Rule public corpus missing test: {token}")

    print("S4 aasm.rule.v1 qualified 0.32.17 parent beneath active 0.32.19 chain: PASS")


if __name__ == "__main__":
    main()
