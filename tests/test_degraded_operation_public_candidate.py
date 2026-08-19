from __future__ import annotations

import aasm
import aasm.public_active_uncertainty_scenario_trace as parent
import aasm.public_active_degraded_operation as promoted


def capability() -> promoted.EffectCapability:
    return promoted.EffectCapability(
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


def envelopes(cap: promoted.EffectCapability) -> tuple[promoted.DegradedModeEnvelope, ...]:
    return (
        promoted.DegradedModeEnvelope("FULL_OPERATION", cap.allowed_operations),
        promoted.DegradedModeEnvelope("DEGRADED_OPERATION", ("drive", "hold")),
        promoted.DegradedModeEnvelope("LOCAL_ONLY", ("drive", "hold"), remote_dependency_policy="FORBID"),
        promoted.DegradedModeEnvelope("SAFE_HOLD", (), effect_policy="NO_NEW_EFFECTS", recovery_intent="HOLD"),
        promoted.DegradedModeEnvelope("RETURN_TO_SAFE_STATE", ("hold",), recovery_intent="RETURN_TO_SAFE_STATE"),
        promoted.DegradedModeEnvelope("EMERGENCY", ("shutdown",), recovery_intent="EMERGENCY_RESPONSE"),
    )


def requirement(dependency_id: str, status: str) -> promoted.DependencyRequirement:
    return promoted.DependencyRequirement(dependency_id, (status,))


def rules() -> tuple[promoted.ModeSelectionRule, ...]:
    return (
        promoted.ModeSelectionRule("nominal", "FULL_OPERATION", (requirement("local", "AVAILABLE"), requirement("upstream", "AVAILABLE"))),
        promoted.ModeSelectionRule("degraded", "DEGRADED_OPERATION", (requirement("local", "AVAILABLE"), requirement("upstream", "DEGRADED"))),
        promoted.ModeSelectionRule("local-only", "LOCAL_ONLY", (requirement("local", "AVAILABLE"), requirement("upstream", "UNAVAILABLE"))),
        promoted.ModeSelectionRule("return-safe", "RETURN_TO_SAFE_STATE", (requirement("local", "DEGRADED"), requirement("upstream", "UNAVAILABLE"))),
        promoted.ModeSelectionRule("emergency", "EMERGENCY", (requirement("local", "DEGRADED"), requirement("upstream", "DEGRADED"))),
        promoted.ModeSelectionRule("hold", "SAFE_HOLD", (requirement("local", "UNAVAILABLE"), requirement("upstream", "UNAVAILABLE"))),
    )


def policy(cap: promoted.EffectCapability) -> promoted.DegradedOperationPolicy:
    return promoted.DegradedOperationPolicy(
        "post-promotion-policy",
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


def context(upstream: str, local: str) -> promoted.DegradedOperationContext:
    return promoted.DegradedOperationContext(
        "workspace-1",
        "control",
        "actuator-1",
        "problem-revision-1",
        "1" * 64,
        (
            promoted.DependencyState("upstream", upstream, evidence_ids=("evidence-upstream",)),
            promoted.DependencyState("local", local, evidence_ids=("evidence-local",)),
        ),
    )


def test_degraded_operation_candidate_overlay_is_now_qualified_active_root():
    parent_report = parent.validate_public_api_contract()
    promoted_report = promoted.validate_public_api_contract()
    root_report = aasm.validate_public_api_contract()
    assert parent_report["valid"], parent_report
    assert promoted_report["valid"], promoted_report
    assert root_report["valid"], root_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert promoted.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert promoted.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert aasm.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert "degraded_operation" in aasm.PUBLIC_API_CONTRACT


def test_active_package_root_is_03220_after_degraded_candidate_qualification():
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert aasm.AASMEngine is promoted.AASMEngine
    assert promoted.AASMEngine is parent.AASMEngine
    assert aasm.DegradedOperationPolicy is promoted.DegradedOperationPolicy
    assert aasm.DegradedOperationAssessment is promoted.DegradedOperationAssessment


def test_promoted_degraded_overlay_preserves_complete_parent_surface_and_engine_identity():
    assert promoted.AASMEngine is parent.AASMEngine
    assert promoted.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert promoted.SUPPORTED_CLI_COMMANDS == parent.SUPPORTED_CLI_COMMANDS
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(promoted.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(promoted.SUPPORTED_INSPECTION_SURFACES)
    assert "degraded-operation" in promoted.SUPPORTED_INSPECTION_SURFACES
    for name in parent.SUPPORTED_PUBLIC_IMPORTS:
        assert hasattr(promoted, name), name
        assert hasattr(aasm, name), name


def test_promoted_degraded_overlay_exports_policy_assessment_ir_without_engine_methods():
    expected = (
        "DEGRADED_OPERATION_CONTRACT_ID",
        "DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID",
        "DEGRADED_OPERATION_MODES",
        "DEPENDENCY_STATUSES",
        "DependencyState",
        "DependencyRequirement",
        "DegradedModeEnvelope",
        "ModeSelectionRule",
        "DegradedOperationPolicy",
        "DegradedOperationContext",
        "DegradedOperationAssessment",
        "evaluate_degraded_operation",
        "degraded_operation_contract",
    )
    for name in expected:
        assert hasattr(promoted, name), name
        assert name in promoted.SUPPORTED_PUBLIC_IMPORTS
        assert getattr(aasm, name) is getattr(promoted, name)
    assert promoted.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert not any(name.startswith("degraded_") for name in promoted.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("activate_degraded") for name in promoted.SUPPORTED_ENGINE_METHODS)


def test_promoted_degraded_contract_preserves_non_amplification_and_claim_ceiling():
    value = promoted.public_api_contract()["degraded_operation"]
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


def test_promoted_degraded_evaluator_narrows_existing_capability_and_never_authorizes():
    cap = capability()
    item = policy(cap)
    degraded = promoted.evaluate_degraded_operation(item, cap, context("DEGRADED", "AVAILABLE"))
    assert degraded.status == "SELECTED"
    assert degraded.mode == "DEGRADED_OPERATION"
    assert set(degraded.allowed_operations) == {"drive", "hold"}
    assert set(degraded.allowed_operations).issubset(cap.allowed_operations)
    assert degraded.effect_authority_granted is False
    assert degraded.reusable_authorization_token is False
    assert degraded.mode_activation_performed is False
    assert degraded.capability_liveness_checked is False

    unknown = promoted.evaluate_degraded_operation(item, cap, context("UNKNOWN", "AVAILABLE"))
    assert unknown.status == "FAIL_CLOSED"
    assert unknown.mode == "SAFE_HOLD"
    assert unknown.allowed_operations == ()
    assert unknown.effect_policy == "NO_NEW_EFFECTS"
