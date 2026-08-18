from __future__ import annotations

import aasm
import aasm.public_active_uncertainty_scenario_trace as parent
import aasm.public_active_degraded_operation as candidate


def capability() -> candidate.EffectCapability:
    return candidate.EffectCapability(
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


def envelopes(cap: candidate.EffectCapability) -> tuple[candidate.DegradedModeEnvelope, ...]:
    return (
        candidate.DegradedModeEnvelope("FULL_OPERATION", cap.allowed_operations),
        candidate.DegradedModeEnvelope("DEGRADED_OPERATION", ("drive", "hold")),
        candidate.DegradedModeEnvelope("LOCAL_ONLY", ("drive", "hold"), remote_dependency_policy="FORBID"),
        candidate.DegradedModeEnvelope("SAFE_HOLD", (), effect_policy="NO_NEW_EFFECTS", recovery_intent="HOLD"),
        candidate.DegradedModeEnvelope("RETURN_TO_SAFE_STATE", ("hold",), recovery_intent="RETURN_TO_SAFE_STATE"),
        candidate.DegradedModeEnvelope("EMERGENCY", ("shutdown",), recovery_intent="EMERGENCY_RESPONSE"),
    )


def requirement(dependency_id: str, status: str) -> candidate.DependencyRequirement:
    return candidate.DependencyRequirement(dependency_id, (status,))


def rules() -> tuple[candidate.ModeSelectionRule, ...]:
    return (
        candidate.ModeSelectionRule("nominal", "FULL_OPERATION", (requirement("local", "AVAILABLE"), requirement("upstream", "AVAILABLE"))),
        candidate.ModeSelectionRule("degraded", "DEGRADED_OPERATION", (requirement("local", "AVAILABLE"), requirement("upstream", "DEGRADED"))),
        candidate.ModeSelectionRule("local-only", "LOCAL_ONLY", (requirement("local", "AVAILABLE"), requirement("upstream", "UNAVAILABLE"))),
        candidate.ModeSelectionRule("return-safe", "RETURN_TO_SAFE_STATE", (requirement("local", "DEGRADED"), requirement("upstream", "UNAVAILABLE"))),
        candidate.ModeSelectionRule("emergency", "EMERGENCY", (requirement("local", "DEGRADED"), requirement("upstream", "DEGRADED"))),
        candidate.ModeSelectionRule("hold", "SAFE_HOLD", (requirement("local", "UNAVAILABLE"), requirement("upstream", "UNAVAILABLE"))),
    )


def policy(cap: candidate.EffectCapability) -> candidate.DegradedOperationPolicy:
    return candidate.DegradedOperationPolicy(
        "candidate-policy",
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


def context(upstream: str, local: str) -> candidate.DegradedOperationContext:
    return candidate.DegradedOperationContext(
        "workspace-1",
        "control",
        "actuator-1",
        "problem-revision-1",
        "1" * 64,
        (
            candidate.DependencyState("upstream", upstream, evidence_ids=("evidence-upstream",)),
            candidate.DependencyState("local", local, evidence_ids=("evidence-local",)),
        ),
    )


def test_degraded_operation_public_candidate_advances_only_candidate_overlay():
    parent_report = parent.validate_public_api_contract()
    candidate_report = candidate.validate_public_api_contract()
    root_report = aasm.validate_public_api_contract()
    assert parent_report["valid"], parent_report
    assert candidate_report["valid"], candidate_report
    assert root_report["valid"], root_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert candidate.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20"
    assert candidate.PUBLIC_API_CONTRACT["parent_contract_version"] == "0.32.19"
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert "degraded_operation" not in aasm.PUBLIC_API_CONTRACT


def test_active_package_root_remains_03219_until_degraded_candidate_is_qualified():
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.19"
    assert aasm.AASMEngine is parent.AASMEngine
    assert not hasattr(aasm, "DegradedOperationPolicy")
    assert not hasattr(aasm, "DegradedOperationAssessment")


def test_degraded_candidate_preserves_complete_parent_surface_and_engine_identity():
    assert candidate.AASMEngine is parent.AASMEngine
    assert candidate.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert candidate.SUPPORTED_CLI_COMMANDS == parent.SUPPORTED_CLI_COMMANDS
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(candidate.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(candidate.SUPPORTED_INSPECTION_SURFACES)
    assert "degraded-operation" in candidate.SUPPORTED_INSPECTION_SURFACES
    for name in parent.SUPPORTED_PUBLIC_IMPORTS:
        assert hasattr(candidate, name), name


def test_degraded_candidate_exports_policy_assessment_ir_without_engine_methods():
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
        assert hasattr(candidate, name), name
        assert name in candidate.SUPPORTED_PUBLIC_IMPORTS
    assert candidate.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS
    assert not any(name.startswith("degraded_") for name in candidate.SUPPORTED_ENGINE_METHODS)
    assert not any(name.startswith("activate_degraded") for name in candidate.SUPPORTED_ENGINE_METHODS)


def test_degraded_candidate_contract_preserves_non_amplification_and_claim_ceiling():
    value = candidate.public_api_contract()["degraded_operation"]
    assert value["contract_id"] == "aasm.degraded.operation.v1"
    assert value["assessment_contract_id"] == "aasm.degraded.operation.assessment.v1"
    assert value["public_admission"] == "QUALIFIED_SEMANTIC_IR_ONLY"
    assert value["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert value["engine_state_integration"] == "NONE_SEMANTIC_IR_ONLY"
    assert value["active_root_status"] == "CANDIDATE_UNTIL_PACKAGE_ROOT_SWITCH"
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


def test_degraded_candidate_evaluator_narrows_existing_capability_and_never_authorizes():
    cap = capability()
    item = policy(cap)
    degraded = candidate.evaluate_degraded_operation(item, cap, context("DEGRADED", "AVAILABLE"))
    assert degraded.status == "SELECTED"
    assert degraded.mode == "DEGRADED_OPERATION"
    assert set(degraded.allowed_operations) == {"drive", "hold"}
    assert set(degraded.allowed_operations).issubset(cap.allowed_operations)
    assert degraded.effect_authority_granted is False
    assert degraded.reusable_authorization_token is False
    assert degraded.mode_activation_performed is False
    assert degraded.capability_liveness_checked is False

    unknown = candidate.evaluate_degraded_operation(item, cap, context("UNKNOWN", "AVAILABLE"))
    assert unknown.status == "FAIL_CLOSED"
    assert unknown.mode == "SAFE_HOLD"
    assert unknown.allowed_operations == ()
    assert unknown.effect_policy == "NO_NEW_EFFECTS"
