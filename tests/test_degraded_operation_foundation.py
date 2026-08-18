from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

from aasm.degraded_operation import (
    DEGRADED_ASSESSMENT_STATUSES,
    DEGRADED_OPERATION_MODES,
    DEPENDENCY_STATUSES,
    EFFECT_POLICIES,
    PREEMPTION_REQUIREMENTS,
    RECOVERY_INTENTS,
    REMOTE_DEPENDENCY_POLICIES,
    DegradedModeEnvelope,
    DegradedOperationAssessment,
    DegradedOperationContext,
    DegradedOperationPolicy,
    DependencyRequirement,
    DependencyState,
    ModeSelectionRule,
    degraded_operation_contract,
    evaluate_degraded_operation,
)
from aasm.effect_capability import EffectCapability


ROOT = Path(__file__).resolve().parents[1]


def capability(*, operations: tuple[str, ...] = ("drive", "hold", "return_safe", "shutdown"), problem_revision_id: str = "problem-revision-1") -> EffectCapability:
    return EffectCapability(
        domain_id="authority-domain-1",
        authority_lease_id="authority-lease-1",
        workspace_id="workspace-1",
        scope_id="control",
        subject_id="actuator-1",
        holder_principal_id="local-controller",
        issuer_principal_id="workspace-root",
        allowed_operations=operations,
        numeric_bounds={},
        valid_from=0.0,
        expires_at=100.0,
        authority_epoch=1,
        problem_revision_id=problem_revision_id,
    )


def envelopes(*, full_operations: tuple[str, ...] = ("drive", "hold", "return_safe", "shutdown"), emergency_operations: tuple[str, ...] = ("shutdown",)) -> tuple[DegradedModeEnvelope, ...]:
    return (
        DegradedModeEnvelope("FULL_OPERATION", full_operations),
        DegradedModeEnvelope("DEGRADED_OPERATION", ("drive", "hold")),
        DegradedModeEnvelope("LOCAL_ONLY", ("drive", "hold"), remote_dependency_policy="FORBID"),
        DegradedModeEnvelope("SAFE_HOLD", (), effect_policy="NO_NEW_EFFECTS", recovery_intent="HOLD"),
        DegradedModeEnvelope(
            "RETURN_TO_SAFE_STATE",
            ("hold", "return_safe"),
            preemption_requirement="EXPLICIT_EXISTING_PREEMPTION_REQUIRED",
            recovery_intent="RETURN_TO_SAFE_STATE",
        ),
        DegradedModeEnvelope(
            "EMERGENCY",
            emergency_operations,
            preemption_requirement="EXPLICIT_EXISTING_PREEMPTION_REQUIRED",
            recovery_intent="EMERGENCY_RESPONSE",
        ),
    )


def requirement(dependency_id: str, *statuses: str) -> DependencyRequirement:
    return DependencyRequirement(dependency_id, tuple(statuses))


def rule(rule_id: str, mode: str, upstream: tuple[str, ...], local: tuple[str, ...]) -> ModeSelectionRule:
    return ModeSelectionRule(
        rule_id,
        mode,
        (
            DependencyRequirement("local_control", local),
            DependencyRequirement("upstream_intelligence", upstream),
        ),
    )


def selection_rules() -> tuple[ModeSelectionRule, ...]:
    return (
        rule("nominal", "FULL_OPERATION", ("AVAILABLE",), ("AVAILABLE",)),
        rule("upstream-degraded", "DEGRADED_OPERATION", ("DEGRADED",), ("AVAILABLE",)),
        rule("upstream-lost", "LOCAL_ONLY", ("UNAVAILABLE",), ("AVAILABLE",)),
        rule("return-safe", "RETURN_TO_SAFE_STATE", ("UNAVAILABLE",), ("DEGRADED",)),
        rule("emergency-response", "EMERGENCY", ("DEGRADED",), ("DEGRADED",)),
        rule("hold", "SAFE_HOLD", ("UNAVAILABLE",), ("UNAVAILABLE",)),
    )


def policy(*, cap: EffectCapability | None = None, mode_envelopes=None, rules=None, **overrides) -> DegradedOperationPolicy:
    cap = cap or capability()
    payload = {
        "policy_name": "robot degraded-operation policy",
        "workspace_id": cap.workspace_id,
        "scope_id": cap.scope_id,
        "subject_id": cap.subject_id,
        "base_capability_id": cap.capability_id,
        "base_capability_fingerprint": cap.fingerprint,
        "problem_revision_id": "problem-revision-1",
        "problem_revision_fingerprint": "1" * 64,
        "dependency_ids": ("upstream_intelligence", "local_control"),
        "mode_envelopes": mode_envelopes or envelopes(full_operations=cap.allowed_operations),
        "selection_rules": rules or selection_rules(),
        "fallback_mode": "SAFE_HOLD",
    }
    payload.update(overrides)
    return DegradedOperationPolicy(**payload)


def context(upstream: str, local: str, **overrides) -> DegradedOperationContext:
    payload = {
        "workspace_id": "workspace-1",
        "scope_id": "control",
        "subject_id": "actuator-1",
        "problem_revision_id": "problem-revision-1",
        "problem_revision_fingerprint": "1" * 64,
        "dependency_states": (
            DependencyState("upstream_intelligence", upstream, evidence_ids=("evidence-upstream",)),
            DependencyState("local_control", local, evidence_ids=("evidence-local",)),
        ),
    }
    payload.update(overrides)
    return DegradedOperationContext(**payload)


def test_degraded_operation_vocabularies_are_exact_and_pre_admission():
    assert DEGRADED_OPERATION_MODES == (
        "FULL_OPERATION",
        "DEGRADED_OPERATION",
        "LOCAL_ONLY",
        "SAFE_HOLD",
        "RETURN_TO_SAFE_STATE",
        "EMERGENCY",
    )
    assert DEPENDENCY_STATUSES == ("AVAILABLE", "DEGRADED", "UNAVAILABLE", "UNKNOWN")
    assert EFFECT_POLICIES == ("EXISTING_CAPABILITY_SUBSET_ONLY", "NO_NEW_EFFECTS")
    assert REMOTE_DEPENDENCY_POLICIES == ("ALLOW", "FORBID")
    assert PREEMPTION_REQUIREMENTS == ("NONE", "EXPLICIT_EXISTING_PREEMPTION_REQUIRED")
    assert RECOVERY_INTENTS == ("NONE", "HOLD", "RETURN_TO_SAFE_STATE", "EMERGENCY_RESPONSE")
    assert DEGRADED_ASSESSMENT_STATUSES == ("SELECTED", "FAIL_CLOSED")
    contract = degraded_operation_contract()
    assert contract["contract_id"] == "aasm.degraded.operation.v1"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


def test_policy_identity_is_deterministic_round_trips_and_requires_all_modes():
    item = policy()
    restored = DegradedOperationPolicy.from_dict(item.to_dict())
    assert restored == item
    assert restored.fingerprint == item.fingerprint
    assert [row.mode for row in item.mode_envelopes] == list(DEGRADED_OPERATION_MODES)

    with pytest.raises(ValueError, match="every mode"):
        policy(mode_envelopes=envelopes()[:-1])
    with pytest.raises(ValueError, match="fallback mode must be SAFE_HOLD"):
        policy(fallback_mode="DEGRADED_OPERATION")


def test_nominal_full_operation_requires_every_dependency_available_and_exact_base_operations():
    cap = capability()
    item = policy(cap=cap)
    assessment = evaluate_degraded_operation(item, cap, context("AVAILABLE", "AVAILABLE"))
    assert assessment.status == "SELECTED"
    assert assessment.mode == "FULL_OPERATION"
    assert assessment.allowed_operations == tuple(sorted(cap.allowed_operations))
    assert assessment.matched_rule_id == "nominal"

    bad_full_rule = rule("bad-nominal", "FULL_OPERATION", ("AVAILABLE", "DEGRADED"), ("AVAILABLE",))
    with pytest.raises(ValueError, match="FULL_OPERATION may be selected only"):
        policy(rules=(bad_full_rule, *selection_rules()[1:]))

    narrowed_full = list(envelopes())
    narrowed_full[0] = DegradedModeEnvelope("FULL_OPERATION", ("drive", "hold"))
    with pytest.raises(ValueError, match="FULL_OPERATION envelope must preserve"):
        evaluate_degraded_operation(policy(cap=cap, mode_envelopes=tuple(narrowed_full)), cap, context("AVAILABLE", "AVAILABLE"))


def test_degraded_and_local_modes_only_reduce_existing_capability():
    cap = capability()
    item = policy(cap=cap)
    degraded = evaluate_degraded_operation(item, cap, context("DEGRADED", "AVAILABLE"))
    assert degraded.mode == "DEGRADED_OPERATION"
    assert set(degraded.allowed_operations) == {"drive", "hold"}
    assert set(degraded.allowed_operations).issubset(cap.allowed_operations)

    local = evaluate_degraded_operation(item, cap, context("UNAVAILABLE", "AVAILABLE"))
    assert local.mode == "LOCAL_ONLY"
    assert local.remote_dependency_policy == "FORBID"
    assert set(local.allowed_operations).issubset(cap.allowed_operations)

    amplified = list(envelopes())
    amplified[-1] = DegradedModeEnvelope(
        "EMERGENCY",
        ("shutdown", "invented-superuser-operation"),
        recovery_intent="EMERGENCY_RESPONSE",
    )
    with pytest.raises(ValueError, match="amplifies base EffectCapability operations"):
        evaluate_degraded_operation(policy(cap=cap, mode_envelopes=tuple(amplified)), cap, context("AVAILABLE", "AVAILABLE"))


def test_unknown_dependency_fails_closed_to_safe_hold_with_no_new_effects():
    cap = capability()
    assessment = evaluate_degraded_operation(policy(cap=cap), cap, context("UNKNOWN", "AVAILABLE"))
    assert assessment.status == "FAIL_CLOSED"
    assert assessment.mode == "SAFE_HOLD"
    assert assessment.effect_policy == "NO_NEW_EFFECTS"
    assert assessment.allowed_operations == ()
    assert "UNKNOWN_DEPENDENCY:upstream_intelligence" in assessment.diagnostics


def test_overlapping_or_unmatched_rules_fail_closed_without_choosing_by_priority():
    cap = capability()
    overlap = ModeSelectionRule(
        "overlap",
        "DEGRADED_OPERATION",
        (
            requirement("local_control", "AVAILABLE"),
            requirement("upstream_intelligence", "DEGRADED", "UNAVAILABLE"),
        ),
    )
    item = policy(cap=cap, rules=(*selection_rules(), overlap))
    ambiguous = evaluate_degraded_operation(item, cap, context("UNAVAILABLE", "AVAILABLE"))
    assert ambiguous.status == "FAIL_CLOSED"
    assert ambiguous.mode == "SAFE_HOLD"
    assert ambiguous.allowed_operations == ()
    assert "MULTIPLE_SELECTION_RULES_MATCHED" in ambiguous.diagnostics

    reduced_rules = tuple(row for row in selection_rules() if row.rule_id != "upstream-degraded")
    no_match = evaluate_degraded_operation(policy(cap=cap, rules=reduced_rules), cap, context("DEGRADED", "AVAILABLE"))
    assert no_match.status == "FAIL_CLOSED"
    assert no_match.mode == "SAFE_HOLD"
    assert no_match.diagnostics == ("NO_SELECTION_RULE_MATCHED",)


def test_safe_hold_return_and_emergency_are_intents_not_safety_or_authority_claims():
    cap = capability()
    item = policy(cap=cap)

    hold = evaluate_degraded_operation(item, cap, context("UNAVAILABLE", "UNAVAILABLE"))
    assert hold.mode == "SAFE_HOLD"
    assert hold.effect_policy == "NO_NEW_EFFECTS"
    assert hold.recovery_intent == "HOLD"

    return_safe = evaluate_degraded_operation(item, cap, context("UNAVAILABLE", "DEGRADED"))
    assert return_safe.mode == "RETURN_TO_SAFE_STATE"
    assert return_safe.recovery_intent == "RETURN_TO_SAFE_STATE"
    assert return_safe.preemption_requirement == "EXPLICIT_EXISTING_PREEMPTION_REQUIRED"

    emergency = evaluate_degraded_operation(item, cap, context("DEGRADED", "DEGRADED"))
    assert emergency.mode == "EMERGENCY"
    assert emergency.recovery_intent == "EMERGENCY_RESPONSE"
    assert emergency.allowed_operations == ("shutdown",)
    for assessment in (hold, return_safe, emergency):
        assert assessment.effect_authority_granted is False
        assert assessment.reusable_authorization_token is False
        assert assessment.mode_activation_performed is False
        assert assessment.capability_liveness_checked is False

    contract = degraded_operation_contract()
    assert contract["safe_hold_meaning"] == "POLICY_LABEL_FOR_NO_NEW_EFFECTS_NOT_EMPIRICAL_PROOF_OF_PHYSICAL_SAFETY"
    assert contract["return_to_safe_state_meaning"] == "RECOVERY_INTENT_ONLY_REQUIRES_EXISTING_AUTHORITY_EFFECT_LIFECYCLE_AND_POSTCONDITION_VERIFICATION"
    assert contract["emergency_meaning"] == "EMERGENCY_RESPONSE_INTENT_ONLY_NEVER_CREATES_OR_EXPANDS_AUTHORITY"
    assert contract["assessment_proves_safety"] is False


def test_capability_scope_fingerprint_and_revision_mismatches_fail_closed():
    cap = capability()
    item = policy(cap=cap)
    other_cap = capability(operations=("hold", "shutdown"))
    with pytest.raises(ValueError, match="exact supplied EffectCapability"):
        evaluate_degraded_operation(item, other_cap, context("AVAILABLE", "AVAILABLE"))

    with pytest.raises(ValueError, match="context workspace_id"):
        evaluate_degraded_operation(
            item,
            cap,
            context("AVAILABLE", "AVAILABLE", workspace_id="other-workspace"),
        )

    with pytest.raises(ValueError, match="context problem revision"):
        evaluate_degraded_operation(
            item,
            cap,
            context(
                "AVAILABLE",
                "AVAILABLE",
                problem_revision_id="problem-revision-2",
                problem_revision_fingerprint="2" * 64,
            ),
        )

    stale_capability = capability(problem_revision_id="problem-revision-old")
    stale_policy = policy(cap=stale_capability)
    with pytest.raises(ValueError, match="base capability problem revision"):
        evaluate_degraded_operation(stale_policy, stale_capability, context("AVAILABLE", "AVAILABLE"))


def test_context_requires_exact_dependency_set_and_unknown_cannot_select_a_rule():
    cap = capability()
    item = policy(cap=cap)
    missing = DegradedOperationContext(
        "workspace-1",
        "control",
        "actuator-1",
        "problem-revision-1",
        "1" * 64,
        (DependencyState("upstream_intelligence", "AVAILABLE"),),
    )
    with pytest.raises(ValueError, match="exact policy dependency set"):
        evaluate_degraded_operation(item, cap, missing)
    with pytest.raises(ValueError, match="UNKNOWN dependency status cannot authorize"):
        DependencyRequirement("upstream_intelligence", ("UNKNOWN",))


def test_policy_rules_must_cover_exact_dependency_vector_and_nominal_rule_is_unique():
    partial = ModeSelectionRule(
        "partial",
        "DEGRADED_OPERATION",
        (requirement("upstream_intelligence", "DEGRADED"),),
    )
    with pytest.raises(ValueError, match="exact policy dependency set"):
        policy(rules=(selection_rules()[0], partial))

    duplicate_nominal = rule("nominal-2", "FULL_OPERATION", ("AVAILABLE",), ("AVAILABLE",))
    with pytest.raises(ValueError, match="exactly one nominal FULL_OPERATION"):
        policy(rules=(*selection_rules(), duplicate_nominal))


def test_degraded_assessment_is_not_authorization_activation_or_liveness_check():
    cap = capability()
    assessment = evaluate_degraded_operation(policy(cap=cap), cap, context("DEGRADED", "AVAILABLE"))
    assert assessment.effect_authority_granted is False
    assert assessment.reusable_authorization_token is False
    assert assessment.mode_activation_performed is False
    assert assessment.capability_liveness_checked is False
    assert DegradedOperationAssessment(**{
        key: value
        for key, value in assessment.to_dict().items()
        if key not in {"fingerprint"}
    }).fingerprint == assessment.fingerprint
    contract = degraded_operation_contract()
    assert contract["assessment_is_authorization"] is False
    assert contract["assessment_is_reusable_authorization_token"] is False
    assert contract["assessment_activates_mode"] is False
    assert contract["capability_liveness"] == "NOT_ESTABLISHED_BY_FOUNDATION_EXISTING_POINT_OF_USE_RECHECK_REMAINS_MANDATORY"


def test_existing_authority_effect_preemption_and_resource_planes_remain_authoritative():
    contract = degraded_operation_contract()
    assert contract["authority_ceiling"] == "EXACT_EXISTING_EFFECT_CAPABILITY_ID_AND_FINGERPRINT_ONLY_NEVER_AMPLIFIED"
    assert contract["effect_authorization"] == "EXISTING_AASM_AUTHORIZE_EFFECT_REMAINS_REQUIRED"
    assert contract["effect_dispatch"] == "EXISTING_AASM_EXECUTE_EFFECT_REMAINS_REQUIRED"
    assert contract["physical_authority"] == "EXISTING_AUTHORITY_DOMAIN_LEASE_EPOCH_REVOCATION_REMAIN_AUTHORITATIVE"
    assert contract["preemption"] == "REQUIREMENT_ONLY_USES_EXISTING_AASM_AUTHORITY_PREEMPTION_PATH_NO_DIRECT_REVOCATION"
    assert contract["task_lease"] == "EXISTING_V54_TASKLEASE_UNCHANGED"
    assert contract["resource_governance"] == "EXISTING_V54_RESOURCE_RESERVATIONS_UNCHANGED"
    assert contract["unknown_and_reconciliation"] == "EXISTING_V54_EFFECT_UNKNOWN_AND_RECONCILIATION_UNCHANGED"
    assert contract["parallel_mode_store"] == "NONE"
    assert contract["parallel_authority_evaluator"] == "NONE"
    assert contract["parallel_effect_lifecycle"] == "NONE"
    assert contract["parallel_dispatcher"] == "NONE"


def test_binary_float_metadata_and_tampering_fail_closed():
    cap = capability()
    with pytest.raises(TypeError, match="binary floating-point"):
        policy(cap=cap, metadata={"confidence": 0.5})
    with pytest.raises(TypeError, match="binary floating-point"):
        DependencyState("upstream", "AVAILABLE", metadata={"score": 0.5})
    with pytest.raises(TypeError, match="binary floating-point"):
        DegradedModeEnvelope("DEGRADED_OPERATION", ("hold",), metadata={"weight": 0.5})

    item = policy(cap=cap)
    changed = deepcopy(item.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="policy fingerprint mismatch"):
        DegradedOperationPolicy.from_dict(changed)
    changed = deepcopy(item.to_dict())
    changed["policy_id"] = "degraded-operation-policy-" + "0" * 24
    with pytest.raises(ValueError, match="policy_id"):
        DegradedOperationPolicy.from_dict(changed)


def test_degraded_operation_schemas_are_closed_and_accept_canonical_policy_and_assessment():
    cap = capability()
    item = policy(cap=cap)
    assessment = evaluate_degraded_operation(item, cap, context("DEGRADED", "AVAILABLE"))
    rows = (
        ("degraded-operation.schema.json", item.to_dict()),
        ("degraded-operation-assessment.schema.json", assessment.to_dict()),
    )
    for filename, document in rows:
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        validate(document, schema)
        changed = deepcopy(document)
        changed["unknown_field"] = True
        with pytest.raises(ValidationError):
            validate(changed, schema)
