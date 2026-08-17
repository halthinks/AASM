from __future__ import annotations

from copy import deepcopy

from . import public_active_engineering_quantity as _base

# Preserve the complete qualified 0.32.16 public surface, then add only the
# independently qualified aasm.rule.v1 semantic foundation. No engine state,
# authority path, learned-constraint lowering, objective-priority rewrite, or
# runtime Rule registry is introduced by this overlay.
for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .rule import (
    RULE_APPLICABILITY_RESULTS,
    RULE_CLAUSE_KINDS,
    RULE_CONTRACT_ID,
    RULE_CONTRACT_VERSION,
    RULE_OVERRIDE_MODES,
    RULE_PREDICATE_KINDS,
    RULE_PRECEDENCE_RELATIONS,
    RULE_SCOPE_MATCH_POLICIES,
    RULE_SEVERITIES,
    RULE_STABILITY,
    RULE_STRENGTHS,
    RULE_WAIVER_MODES,
    EngineeringRule,
    RuleApplicabilityAssessment,
    RuleApplicabilityContext,
    RuleApplicabilityPredicate,
    RuleClauseRef,
    RuleControlPolicy,
    RuleScopeSelector,
    RuleSourceAuthorityRef,
    compare_rule_precedence,
    evaluate_rule_applicability,
    rule_contract,
    rule_override_structurally_eligible,
    rule_waiver_structurally_eligible,
)


__version__ = _base.__version__
PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY
REMOTE_PROTOCOL_NAME = _base.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _base.REMOTE_PROTOCOL_VERSION
AASMEngine = _base.AASMEngine

_RULE_IMPORTS = [
    "RULE_CONTRACT_ID",
    "RULE_CONTRACT_VERSION",
    "RULE_STABILITY",
    "RULE_STRENGTHS",
    "RULE_SEVERITIES",
    "RULE_SCOPE_MATCH_POLICIES",
    "RULE_PREDICATE_KINDS",
    "RULE_WAIVER_MODES",
    "RULE_OVERRIDE_MODES",
    "RULE_APPLICABILITY_RESULTS",
    "RULE_PRECEDENCE_RELATIONS",
    "RULE_CLAUSE_KINDS",
    "RuleClauseRef",
    "RuleSourceAuthorityRef",
    "RuleScopeSelector",
    "RuleApplicabilityPredicate",
    "RuleControlPolicy",
    "RuleApplicabilityContext",
    "EngineeringRule",
    "RuleApplicabilityAssessment",
    "evaluate_rule_applicability",
    "compare_rule_precedence",
    "rule_waiver_structurally_eligible",
    "rule_override_structurally_eligible",
    "rule_contract",
]

SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))
SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_INSPECTION_SURFACES = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_INSPECTION_SURFACES", []), "engineering-rule"])
)
SUPPORTED_PUBLIC_IMPORTS = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_RULE_IMPORTS])
)

PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update(
    {
        "contract_version": "0.32.17",
        "runtime_version": __version__,
        "release_stability": PUBLIC_RELEASE_STABILITY,
        "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
        "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
        "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
        "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
    }
)
PUBLIC_API_CONTRACT["engineering_rule"] = {
    **rule_contract(),
    "public_admission": "QUALIFIED",
    "engine_state_integration": "NONE_SEMANTIC_RULE_FOUNDATION_ONLY",
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _base.validate_public_api_contract()
    errors: list[str] = []
    if not parent["valid"]:
        errors.extend(f"active 0.32.16 parent: {error}" for error in parent["errors"])

    missing_imports = [name for name in _RULE_IMPORTS if name not in globals()]
    if missing_imports:
        errors.append(f"missing engineering-rule public imports: {missing_imports}")
    if AASMEngine is not _base.AASMEngine:
        errors.append("engineering rule overlay forked the active engine")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.17":
        errors.append("engineering rule adoption contract mismatch")
    if "engineering-rule" not in SUPPORTED_INSPECTION_SURFACES:
        errors.append("engineering-rule inspection surface missing")

    rule = PUBLIC_API_CONTRACT.get("engineering_rule", {})
    if rule.get("contract_id") != RULE_CONTRACT_ID:
        errors.append("engineering rule semantic contract missing")
    if rule.get("contract_version") != RULE_CONTRACT_VERSION:
        errors.append("engineering rule semantic contract version drift")
    if tuple(rule.get("strengths", ())) != RULE_STRENGTHS:
        errors.append("engineering rule strength set drift")
    if rule.get("applicability") != "EXPLICIT_PORTABLE_CONTEXT_MATCH_TRI_STATE_FAIL_CLOSED":
        errors.append("engineering rule applicability semantics drift")
    if rule.get("precedence") != "STRENGTH_THEN_SPECIFICITY_THEN_PRIORITY_WITHIN_EXPLICIT_GROUP":
        errors.append("engineering rule precedence semantics drift")
    if rule.get("precedence_is_objective_priority") is not False:
        errors.append("engineering rule precedence was conflated with objective priority")
    if rule.get("precedence_authorizes_override") is not False:
        errors.append("engineering rule precedence unexpectedly authorizes override")
    if rule.get("hard_floor_waiver") != "FORBIDDEN" or rule.get("hard_floor_override") != "FORBIDDEN":
        errors.append("engineering rule HARD_FLOOR control semantics weakened")
    if rule.get("waiver_override_authority") != "STRUCTURAL_ELIGIBILITY_ONLY_EXISTING_SCOPED_AUTHORITY_MUST_AUTHORIZE_LATER_RUNTIME_ACTION":
        errors.append("engineering rule waiver/override bypassed scoped authority")
    if rule.get("source_authority") != "EXACT_EXISTING_SCOPED_AUTHORITY_GRANT_REFERENCE_ONLY_NOT_VERIFIED_BY_FOUNDATION":
        errors.append("engineering rule source authority semantics drift")
    if rule.get("learned_constraint_relation") != "DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT":
        errors.append("engineering rule strength was conflated with learned constraints")
    if rule.get("rule_to_constraint_lowering") != "NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED":
        errors.append("engineering rule overlay introduced implicit rule-to-constraint lowering")
    if rule.get("runtime_admission") != "PRE_ADMISSION_ONLY":
        errors.append("engineering rule semantic foundation unexpectedly gained runtime admission")
    if rule.get("public_admission") != "QUALIFIED":
        errors.append("engineering rule public qualification status drift")
    if rule.get("engine_state_integration") != "NONE_SEMANTIC_RULE_FOUNDATION_ONLY":
        errors.append("engineering rule overlay introduced engine state")
    for key in (
        "rule_existence_grants_fact_authority",
        "rule_existence_grants_effect_authority",
        "rule_existence_grants_source_authority",
        "precedence_authorizes_override",
    ):
        if rule.get(key) is not False:
            errors.append(f"engineering rule authority firewall drift: {key}")
    for key in (
        "parallel_rule_registry",
        "current_rule_pointer",
        "parallel_constraint_engine",
        "parallel_authority_evaluator",
        "hidden_wall_clock",
    ):
        if rule.get(key) != "NONE":
            errors.append(f"engineering rule state/authority firewall drift: {key}")

    if SUPPORTED_ENGINE_METHODS != list(getattr(_base, "SUPPORTED_ENGINE_METHODS", [])):
        errors.append("engineering rule overlay added engine methods")

    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}
