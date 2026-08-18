from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing S4.5 degraded-operation file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    model = text("src/aasm/degraded_operation.py")
    policy_schema = json.loads(text("schemas/degraded-operation.schema.json"))
    assessment_schema = json.loads(text("schemas/degraded-operation-assessment.schema.json"))
    tests = text("tests/test_degraded_operation_foundation.py")
    workflow = text(".github/workflows/engineering-degraded-operation.yml")

    runtime = text("src/aasm/runtime_v56_foundation.py")
    public = text("src/aasm/public_active_uncertainty_scenario_trace.py")
    capability = text("src/aasm/effect_capability.py")
    physical_authority = text("src/aasm/physical_authority.py")
    preemption = text("src/aasm/physical_preemption.py")
    fencing = text("src/aasm/physical_control_fencing_runtime.py")
    effect_integration = text("src/aasm/physical_effect_integration_runtime.py")

    for token in (
        'DEGRADED_OPERATION_CONTRACT_ID = "aasm.degraded.operation.v1"',
        'DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID = "aasm.degraded.operation.assessment.v1"',
        '"FULL_OPERATION"',
        '"DEGRADED_OPERATION"',
        '"LOCAL_ONLY"',
        '"SAFE_HOLD"',
        '"RETURN_TO_SAFE_STATE"',
        '"EMERGENCY"',
        '"AVAILABLE"',
        '"DEGRADED"',
        '"UNAVAILABLE"',
        '"UNKNOWN"',
        "class DependencyState",
        "class DependencyRequirement",
        "class DegradedModeEnvelope",
        "class ModeSelectionRule",
        "class DegradedOperationPolicy",
        "class DegradedOperationContext",
        "class DegradedOperationAssessment",
        "def evaluate_degraded_operation",
        "def degraded_operation_contract",
        '"EXACT_EXISTING_EFFECT_CAPABILITY_ID_AND_FINGERPRINT_ONLY_NEVER_AMPLIFIED"',
        '"EXISTING_AASM_AUTHORIZE_EFFECT_REMAINS_REQUIRED"',
        '"EXISTING_AASM_EXECUTE_EFFECT_REMAINS_REQUIRED"',
        '"EXISTING_AUTHORITY_DOMAIN_LEASE_EPOCH_REVOCATION_REMAIN_AUTHORITATIVE"',
        '"REQUIREMENT_ONLY_USES_EXISTING_AASM_AUTHORITY_PREEMPTION_PATH_NO_DIRECT_REVOCATION"',
        '"FAIL_CLOSED_TO_SAFE_HOLD_WITH_NO_NEW_EFFECTS"',
        '"POLICY_LABEL_FOR_NO_NEW_EFFECTS_NOT_EMPIRICAL_PROOF_OF_PHYSICAL_SAFETY"',
        '"EMERGENCY_RESPONSE_INTENT_ONLY_NEVER_CREATES_OR_EXPANDS_AUTHORITY"',
        '"assessment_is_authorization": False',
        '"assessment_is_reusable_authorization_token": False',
        '"assessment_activates_mode": False',
        '"assessment_proves_safety": False',
        '"hidden_current_mode": "NONE"',
        '"parallel_mode_store": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
        '"parallel_effect_lifecycle": "NONE"',
        '"parallel_dispatcher": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
    ):
        require(token in model, f"S4.5 degraded-operation foundation missing token: {token}")

    for token in (
        "FactAuthority(",
        "StateClaim(",
        "authorize_scoped_request(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "preempt_authority_lease(",
        "register_degraded_mode(",
        "activate_degraded_mode(",
        "DEGRADED_MODE_REGISTRY =",
        "CURRENT_DEGRADED_MODE =",
        "current_degraded_mode_store",
        "datetime.now(",
        "time.time(",
        "random.",
        "eval(",
        "exec(",
    ):
        require(token not in model, f"S4.5 degraded-operation foundation violates firewall: {token}")

    require('from .effect_capability import EFFECT_CAPABILITY_CONTRACT_ID, EffectCapability' in model, "degraded-operation foundation does not reuse existing EffectCapability")
    require('EFFECT_CAPABILITY_CONTRACT_ID = "aasm.effect.capability.v1"' in capability, "existing EffectCapability substrate drift")
    require('"capability_existence_grants_effect_authority": False' in capability, "EffectCapability authority firewall drift")
    require('AUTHORITY_DOMAIN_CONTRACT_ID = "aasm.authority.domain.v1"' in physical_authority, "physical authority domain substrate drift")
    require('AUTHORITY_LEASE_CONTRACT_ID = "aasm.authority.lease.v1"' in physical_authority, "physical authority lease substrate drift")
    require('"lease_existence_grants_effect_authority": False' in physical_authority, "physical lease authority firewall drift")
    require('AUTHORITY_PREEMPTION_CONTRACT_ID = "aasm.authority.preemption.v1"' in preemption, "authority preemption substrate drift")
    require('"preemption_grants_new_effect_authority": False' in preemption, "preemption authority firewall drift")
    require('"use_validation_grants_effect_authority": False' in fencing, "physical fencing use-validation firewall drift")
    require('"prior_use_validation": "EVIDENCE_ONLY_NEVER_REUSABLE_AUTHORIZATION"' in effect_integration, "physical point-of-use authorization boundary drift")
    require('"task_lease": "EXISTING_V54_TASKLEASE_UNCHANGED"' in effect_integration, "TaskLease integration drift")
    require('"resource_governance": "EXISTING_V54_RESOURCE_RESERVATIONS_UNCHANGED"' in effect_integration, "resource-governance integration drift")
    require('"unknown_and_reconciliation": "EXISTING_V54_UNKNOWN_AND_RECONCILIATION_UNCHANGED"' in effect_integration, "effect unknown/reconciliation boundary drift")

    for source, label in ((runtime, "runtime_v56_foundation"), (public, "active 0.32.19 public root")):
        require("from .degraded_operation" not in source, f"S4.5 foundation leaked into {label} before admission")
        require("DegradedOperationPolicy" not in source, f"S4.5 policy leaked into {label} before admission")
        require("aasm.degraded.operation.v1" not in source, f"S4.5 contract leaked into {label} before admission")

    require(policy_schema.get("additionalProperties") is False, "degraded-operation policy schema is not closed")
    require(assessment_schema.get("additionalProperties") is False, "degraded-operation assessment schema is not closed")
    require(policy_schema["properties"]["contract_id"]["const"] == "aasm.degraded.operation.v1", "degraded-operation policy schema ID drift")
    require(assessment_schema["properties"]["contract_id"]["const"] == "aasm.degraded.operation.assessment.v1", "degraded-operation assessment schema ID drift")
    require(policy_schema["properties"]["fallback_mode"]["const"] == "SAFE_HOLD", "degraded-operation fallback schema drift")
    require(assessment_schema["properties"]["effect_authority_granted"]["const"] is False, "degraded assessment authority schema drift")
    require(assessment_schema["properties"]["reusable_authorization_token"]["const"] is False, "degraded assessment token schema drift")
    require(assessment_schema["properties"]["mode_activation_performed"]["const"] is False, "degraded assessment activation schema drift")
    require(assessment_schema["properties"]["capability_liveness_checked"]["const"] is False, "degraded assessment liveness schema drift")

    for token in (
        "test_degraded_operation_vocabularies_are_exact_and_pre_admission",
        "test_policy_identity_is_deterministic_round_trips_and_requires_all_modes",
        "test_nominal_full_operation_requires_every_dependency_available_and_exact_base_operations",
        "test_degraded_and_local_modes_only_reduce_existing_capability",
        "test_unknown_dependency_fails_closed_to_safe_hold_with_no_new_effects",
        "test_overlapping_or_unmatched_rules_fail_closed_without_choosing_by_priority",
        "test_safe_hold_return_and_emergency_are_intents_not_safety_or_authority_claims",
        "test_capability_scope_fingerprint_and_revision_mismatches_fail_closed",
        "test_context_requires_exact_dependency_set_and_unknown_cannot_select_a_rule",
        "test_policy_rules_must_cover_exact_dependency_vector_and_nominal_rule_is_unique",
        "test_degraded_assessment_is_not_authorization_activation_or_liveness_check",
        "test_existing_authority_effect_preemption_and_resource_planes_remain_authoritative",
        "test_binary_float_metadata_and_tampering_fail_closed",
        "test_degraded_operation_schemas_are_closed_and_accept_canonical_policy_and_assessment",
    ):
        require(token in tests, f"S4.5 degraded-operation adversarial corpus missing test: {token}")

    for token in (
        "check_degraded_operation_contracts.py",
        "tests/test_degraded_operation_foundation.py",
        "schemas/degraded-operation.schema.json",
        "schemas/degraded-operation-assessment.schema.json",
        "context='aasm/engineering-degraded-operation'",
    ):
        require(token in workflow, f"S4.5 degraded-operation workflow missing token: {token}")

    print("S4.5 degraded-operation pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
