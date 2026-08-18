from __future__ import annotations

import aasm
import aasm.public_active_uncertainty_scenario_trace as parent
import aasm.public_active_degraded_operation as active


def capability() -> active.EffectCapability:
    return active.EffectCapability(
        domain_id="authority-domain-1",
        authority_lease_id="authority-lease-1",
        workspace_id="workspace-1",
        scope_id="control",
        subject_id="actuator-1",
        holder_principal_id="local-controller",
        issuer_principal_id="workspace-root",
        allowed_operations=("drive", "hold", "shutdown"),
        numeric_bounds={},
        valid_from=0.0,
        expires_at=100.0,
        authority_epoch=1,
        problem_revision_id="problem-revision-1",
    )


def envelopes(cap: active.EffectCapability) -> tuple[active.DegradedModeEnvelope, ...]:
    return (
        active.DegradedModeEnvelope("FULL_OPERATION", cap.allowed_operations),
        active.DegradedModeEnvelope("DEGRADED_OPERATION", ("drive", "hold")),
        active.DegradedModeEnvelope("LOCAL_ONLY", ("drive", "hold"), remote_dependency_policy="FORBID"),
        active.DegradedModeEnvelope("SAFE_HOLD", (), effect_policy="NO_NEW_EFFECTS", recovery_intent="HOLD"),
        active.DegradedModeEnvelope("RETURN_TO_SAFE_STATE", ("hold",), recovery_intent="RETURN_TO_SAFE_STATE"),
        active.DegradedModeEnvelope("EMERGENCY", ("shutdown",), recovery_intent="EMERGENCY_RESPONSE"),
    )


def requirement(dependency_id: str, status: str) -> active.DependencyRequirement:
    return active.DependencyRequirement(dependency_id, (status,))


def rules() -> tuple[active.ModeSelectionRule, ...]:
    return (
        active.ModeSelectionRule("nominal", "FULL_OPERATION", (requirement("local", "AVAILABLE"), requirement("upstream", "AVAILABLE"))),
        active.ModeSelectionRule("degraded", "DEGRADED_OPERATION", (requirement("local", "AVAILABLE"), requirement("upstream", "DEGRADED"))),
        active.ModeSelectionRule("local-only", "LOCAL_ONLY", (requirement("local", "AVAILABLE"), requirement("upstream", "UNAVAILABLE"))),
        active.ModeSelectionRule("return-safe", "RETURN_TO_SAFE_STATE", (requirement("local", "DEGRADED"), requirement("upstream", "UNAVAILABLE"))),
        active.ModeSelectionRule("emergency", "EMERGENCY", (requirement("local", "DEGRADED"), requirement("upstream", "DEGRADED"))),
        active.ModeSelectionRule("hold", "SAFE_HOLD", (requirement("local", "UNAVAILABLE"), requirement("upstream", "UNAVAILABLE"))),
    )


def policy(cap: active.EffectCapability) -> active.DegradedOperationPolicy:
    return active.DegradedOperationPolicy(
        "active-policy",
        cap.workspace_id,
        cap.scope_id,
        cap.subject_id,
        cap.capability_id,
        cap.fingerprint,
        "problem-revision-1",
        "1" * 64,
        ("upstream", "local"),
        envelopes(cap),
        rules(),
    )


def context(upstream: str, local: str) -> active.DegradedOperationContext:
    return active.DegradedOperationContext(
        "workspace-1",
        "control",
        "actuator-1",
        "problem-revision-1",
        "1" * 64,
        (active.DependencyState("upstream", upstream), active.DependencyState("local", local)),
    )


def test_degraded_operation_public_adoption_is_additive_over_qualified_03219_parent():
    assert parent.validate_public_api_contract()["valid"] is True
    assert active.validate_public_api_contract()["valid"] is True
    assert aasm.validate_public_api_contract()["valid"] is True
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert active.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert active.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert active.AASMEngine is parent.AASMEngine
    assert aasm.AASMEngine is active.AASMEngine


def test_degraded_public_adoption_preserves_complete_parent_surface_and_engine_identity():
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(active.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(active.SUPPORTED_INSPECTION_SURFACES)
    assert active.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert active.SUPPORTED_CLI_COMMANDS == parent.SUPPORTED_CLI_COMMANDS
    for name in parent.SUPPORTED_PUBLIC_IMPORTS:
        assert hasattr(aasm, name), name
    assert "degraded-operation" in aasm.SUPPORTED_INSPECTION_SURFACES


def test_degraded_public_adoption_exports_policy_assessment_ir_without_runtime_methods():
    for name in (
        "DegradedOperationPolicy", "DegradedOperationContext", "DegradedOperationAssessment",
        "DependencyState", "DependencyRequirement", "DegradedModeEnvelope", "ModeSelectionRule",
        "evaluate_degraded_operation", "degraded_operation_contract",
    ):
        assert getattr(aasm, name) is getattr(active, name)
        assert name in aasm.SUPPORTED_PUBLIC_IMPORTS
    assert aasm.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert not any(name.startswith(("degraded_", "activate_degraded")) for name in aasm.SUPPORTED_ENGINE_METHODS)


def test_degraded_public_adoption_preserves_non_amplification_and_claim_ceiling():
    value = aasm.public_api_contract()["degraded_operation"]
    assert value["contract_id"] == "aasm.degraded.operation.v1"
    assert value["assessment_contract_id"] == "aasm.degraded.operation.assessment.v1"
    assert value["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert value["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert value["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert value["active_root_status"] == "ACTIVE_QUALIFIED_PUBLIC_ROOT"
    assert value["mode_activation"] == "NONE"
    assert value["authority_ceiling"] == "EXACT_EXISTING_EFFECT_CAPABILITY_ID_AND_FINGERPRINT_ONLY_NEVER_AMPLIFIED"
    assert value["mode_selection_grants_effect_authority"] is False
    assert value["assessment_is_authorization"] is False
    assert value["assessment_activates_mode"] is False
    assert value["assessment_proves_safety"] is False
    assert value["hidden_current_mode"] == "NONE"
    assert value["parallel_mode_store"] == "NONE"
    assert value["parallel_authority_evaluator"] == "NONE"
    assert value["parallel_effect_lifecycle"] == "NONE"
    assert value["parallel_dispatcher"] == "NONE"
    assert all(entry == "NONE" for entry in value["public_claim_ceiling"].values())


def test_degraded_public_evaluator_narrows_existing_capability_and_fails_closed():
    cap = capability(); item = policy(cap)
    degraded = aasm.evaluate_degraded_operation(item, cap, context("DEGRADED", "AVAILABLE"))
    assert degraded.mode == "DEGRADED_OPERATION"
    assert set(degraded.allowed_operations) == {"drive", "hold"}
    assert degraded.effect_authority_granted is False
    assert degraded.mode_activation_performed is False
    unknown = aasm.evaluate_degraded_operation(item, cap, context("UNKNOWN", "AVAILABLE"))
    assert unknown.status == "FAIL_CLOSED"
    assert unknown.mode == "SAFE_HOLD"
    assert unknown.allowed_operations == ()
