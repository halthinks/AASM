from __future__ import annotations

from copy import deepcopy

from . import public_active_uncertainty_scenario_trace as _base

# Preserve the complete qualified 0.32.19 public surface, then add only the
# independently qualified S4.5 degraded-operation semantic policy/assessment IR.
# This active additive public layer cannot activate a mode, preempt authority,
# authorize/dispatch effects, create a current-mode store, or expand an EffectCapability.
for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .degraded_operation import (
    DEGRADED_OPERATION_CONTRACT_ID,
    DEGRADED_OPERATION_CONTRACT_VERSION,
    DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID,
    DEGRADED_OPERATION_ASSESSMENT_CONTRACT_VERSION,
    DEGRADED_OPERATION_STABILITY,
    DEGRADED_OPERATION_MODES,
    DEPENDENCY_STATUSES,
    EFFECT_POLICIES,
    REMOTE_DEPENDENCY_POLICIES,
    PREEMPTION_REQUIREMENTS,
    RECOVERY_INTENTS,
    DEGRADED_ASSESSMENT_STATUSES,
    DependencyState,
    DependencyRequirement,
    DegradedModeEnvelope,
    ModeSelectionRule,
    DegradedOperationPolicy,
    DegradedOperationContext,
    DegradedOperationAssessment,
    evaluate_degraded_operation,
    degraded_operation_contract,
)
from .degraded_operation import __all__ as _DEGRADED_IMPORTS


__version__ = _base.__version__
PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY
REMOTE_PROTOCOL_NAME = _base.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _base.REMOTE_PROTOCOL_VERSION
AASMEngine = _base.AASMEngine

PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.20"
PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"
DEGRADED_OPERATION_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"

SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))
SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_PUBLIC_IMPORTS = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_DEGRADED_IMPORTS])
)
SUPPORTED_INSPECTION_SURFACES = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_INSPECTION_SURFACES", []), "degraded-operation"])
)

PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update(
    {
        "contract_version": PUBLIC_ADOPTION_CONTRACT_VERSION,
        "parent_contract_version": PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION,
        "runtime_version": __version__,
        "release_stability": PUBLIC_RELEASE_STABILITY,
        "description": (
            "0.32.20 active additive boundary: qualified 0.32.19 uncertainty/scenario/trace-property plus "
            "degraded-operation semantic policy/assessment IR; no degraded-operation runtime composition."
        ),
        "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
        "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
        "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
        "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
    }
)
_degraded = deepcopy(degraded_operation_contract())
_degraded.update(
    {
        "public_admission": DEGRADED_OPERATION_PUBLIC_ADMISSION,
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "engine_state_integration": "NONE_SEMANTIC_IR_ONLY",
        "active_root_status": "ACTIVE_QUALIFIED_PUBLIC_ROOT",
        "public_role": "CAPABILITY_NARROWING_POLICY_AND_ASSESSMENT_ONLY",
        "mode_activation": "NONE",
        "public_claim_ceiling": {
            "truth_authority": "NONE",
            "fact_authority": "NONE",
            "effect_authority": "NONE",
            "artifact_acceptance": "NONE",
            "proof_authority": "NONE",
            "objective_preference": "NONE",
            "reuse_admission": "NONE",
            "runtime_execution": "NONE",
        },
    }
)
PUBLIC_API_CONTRACT["degraded_operation"] = _degraded
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract() -> dict:
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    parent = _base.validate_public_api_contract()
    errors: list[str] = []
    if not parent.get("valid"):
        errors.append("qualified 0.32.19 parent is invalid")
    if _base.PUBLIC_API_CONTRACT.get("contract_version") != PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("0.32.19 parent public adoption drifted")
    if AASMEngine is not _base.AASMEngine:
        errors.append("degraded-operation active public layer forked AASMEngine")
    if PUBLIC_API_CONTRACT.get("contract_version") != PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("degraded-operation active public adoption version drift")
    if PUBLIC_API_CONTRACT.get("parent_contract_version") != PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("degraded-operation active public parent version drift")
    if PUBLIC_API_CONTRACT.get("supported_imports") != SUPPORTED_PUBLIC_IMPORTS:
        errors.append("degraded-operation active public import surface drift")
    if SUPPORTED_ENGINE_METHODS != list(getattr(_base, "SUPPORTED_ENGINE_METHODS", [])):
        errors.append("degraded-operation active public layer added engine methods")
    if SUPPORTED_CLI_COMMANDS != list(getattr(_base, "SUPPORTED_CLI_COMMANDS", [])):
        errors.append("degraded-operation active public layer changed CLI commands")
    if "degraded-operation" not in SUPPORTED_INSPECTION_SURFACES:
        errors.append("degraded-operation inspection surface missing")
    missing_imports = [name for name in _DEGRADED_IMPORTS if name not in globals()]
    if missing_imports:
        errors.append(f"missing degraded-operation public imports: {missing_imports}")

    value = PUBLIC_API_CONTRACT.get("degraded_operation") or {}
    required = {
        "contract_id": DEGRADED_OPERATION_CONTRACT_ID,
        "assessment_contract_id": DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID,
        "public_admission": DEGRADED_OPERATION_PUBLIC_ADMISSION,
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "engine_state_integration": "NONE_SEMANTIC_IR_ONLY",
        "active_root_status": "ACTIVE_QUALIFIED_PUBLIC_ROOT",
        "mode_activation": "NONE",
        "authority_ceiling": "EXACT_EXISTING_EFFECT_CAPABILITY_ID_AND_FINGERPRINT_ONLY_NEVER_AMPLIFIED",
        "hidden_current_mode": "NONE",
        "parallel_mode_store": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "parallel_dispatcher": "NONE",
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            errors.append(f"degraded-operation active public {key} drift")
    if any(entry != "NONE" for entry in (value.get("public_claim_ceiling") or {}).values()):
        errors.append("degraded-operation public claim ceiling drift")
    if value.get("mode_selection_grants_effect_authority") is not False:
        errors.append("degraded-operation mode selection authority drift")
    if value.get("assessment_is_authorization") is not False:
        errors.append("degraded-operation assessment authorization drift")
    if value.get("assessment_activates_mode") is not False:
        errors.append("degraded-operation assessment activation drift")
    if value.get("assessment_proves_safety") is not False:
        errors.append("degraded-operation safety-proof claim drift")

    return {
        "valid": not errors,
        "errors": errors,
        "contract": public_api_contract(),
        "contract_version": PUBLIC_ADOPTION_CONTRACT_VERSION,
        "parent_contract_version": PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION,
        "degraded_operation_contract_id": DEGRADED_OPERATION_CONTRACT_ID,
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "active_root_status": "ACTIVE_QUALIFIED_PUBLIC_ROOT",
    }


__all__ = tuple(
    dict.fromkeys(
        [
            *SUPPORTED_PUBLIC_IMPORTS,
            "AASMEngine",
            "PUBLIC_API_CONTRACT",
            "PUBLIC_ADOPTION_CONTRACT_VERSION",
            "PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION",
            "DEGRADED_OPERATION_PUBLIC_ADMISSION",
            "PUBLIC_RELEASE_STABILITY",
            "REMOTE_PROTOCOL_NAME",
            "REMOTE_PROTOCOL_VERSION",
            "SUPPORTED_PUBLIC_IMPORTS",
            "SUPPORTED_ENGINE_METHODS",
            "SUPPORTED_CLI_COMMANDS",
            "SUPPORTED_INSPECTION_SURFACES",
            "public_api_contract",
            "validate_public_api_contract",
            "__version__",
        ]
    )
)
