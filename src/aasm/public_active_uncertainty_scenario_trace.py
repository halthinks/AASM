from __future__ import annotations

from copy import deepcopy

from . import public_active_semantic_projection as _base

# Preserve the complete qualified 0.32.18 public surface, then add only the
# independently qualified S4.4 uncertainty/scenario/trace-property semantic IR.
# This active overlay does not compose new engine state, select/activate scenarios,
# create registries, or grant truth, authority, proof, preference, acceptance,
# or reuse admission.
for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .uncertainty_scenario_trace import (
    UNCERTAINTY_CONTRACT_ID,
    UNCERTAINTY_CONTRACT_VERSION,
    SCENARIO_CONTRACT_ID,
    SCENARIO_CONTRACT_VERSION,
    TRACE_PROPERTY_CONTRACT_ID,
    TRACE_PROPERTY_CONTRACT_VERSION,
    TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID,
    TRACE_PROPERTY_ASSESSMENT_CONTRACT_VERSION,
    UNCERTAINTY_SCENARIO_TRACE_STABILITY,
    UNCERTAINTY_FORMS,
    SCENARIO_BINDING_KINDS,
    TRACE_PROPERTY_KINDS,
    TRACE_COMPLETENESS,
    TRACE_PROPERTY_STATUSES,
    TRACE_INVARIANT_CLASSIFICATION,
    ScenarioBinding,
    Scenario,
    UncertaintySpec,
    TraceEventPattern,
    TraceProperty,
    TraceEvaluationContext,
    TracePropertyAssessment,
    evaluate_trace_property,
    uncertainty_contract,
    scenario_contract,
    trace_property_contract,
)
from .uncertainty_scenario_trace import __all__ as _UST_IMPORTS


__version__ = _base.__version__
PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY
REMOTE_PROTOCOL_NAME = _base.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _base.REMOTE_PROTOCOL_VERSION
AASMEngine = _base.AASMEngine

PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"
PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"
UNCERTAINTY_SCENARIO_TRACE_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"

SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))
SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_PUBLIC_IMPORTS = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_UST_IMPORTS])
)
SUPPORTED_INSPECTION_SURFACES = list(
    dict.fromkeys(
        [
            *getattr(_base, "SUPPORTED_INSPECTION_SURFACES", []),
            "uncertainty-scenario-trace",
        ]
    )
)


def _qualified_semantic_contract(contract: dict, *, extra: dict | None = None) -> dict:
    value = deepcopy(contract)
    value["public_admission"] = UNCERTAINTY_SCENARIO_TRACE_PUBLIC_ADMISSION
    value["runtime_admission"] = "PRE_ADMISSION_ONLY"
    value["engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"
    value["active_root_status"] = "ACTIVE_QUALIFIED_PUBLIC_ROOT"
    value["public_claim_ceiling"] = {
        "truth_authority": "NONE",
        "fact_authority": "NONE",
        "effect_authority": "NONE",
        "artifact_acceptance": "NONE",
        "proof_authority": "NONE",
        "objective_preference": "NONE",
        "reuse_admission": "NONE",
        "runtime_execution": "NONE",
    }
    if extra:
        value.update(extra)
    return value


PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update(
    {
        "contract_version": PUBLIC_ADOPTION_CONTRACT_VERSION,
        "parent_contract_version": PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION,
        "runtime_version": __version__,
        "release_stability": PUBLIC_RELEASE_STABILITY,
        "description": (
            "0.32.19 active public boundary: qualified 0.32.18 Projection/Equivalence plus "
            "qualified uncertainty/scenario/trace-property semantic IR; no S4.4 runtime composition."
        ),
        "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
        "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
        "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
        "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
    }
)
PUBLIC_API_CONTRACT["uncertainty"] = _qualified_semantic_contract(
    uncertainty_contract(),
    extra={"public_role": "EPISTEMIC_UNCERTAINTY_DESCRIPTION_ONLY"},
)
PUBLIC_API_CONTRACT["scenario"] = _qualified_semantic_contract(
    scenario_contract(),
    extra={
        "public_role": "REVISION_BOUND_HYPOTHETICAL_CONTEXT_ONLY",
        "scenario_activation": "NONE_FOUNDATION_ONLY",
    },
)
PUBLIC_API_CONTRACT["trace_property"] = _qualified_semantic_contract(
    trace_property_contract(),
    extra={
        "public_role": "DYNAMIC_TRACE_PREDICATE_AND_ASSESSMENT_ONLY",
        "static_constraint_lowering": "NONE",
    },
)
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract() -> dict:
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    parent = _base.validate_public_api_contract()
    errors: list[str] = []
    if not parent.get("valid"):
        errors.append("qualified 0.32.18 semantic projection parent is invalid")

    if _base.PUBLIC_API_CONTRACT.get("contract_version") != PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("0.32.18 parent public adoption drifted")
    if AASMEngine is not _base.AASMEngine:
        errors.append("S4.4 public overlay forked AASMEngine")
    if PUBLIC_API_CONTRACT.get("contract_version") != PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("S4.4 public adoption version drift")
    if PUBLIC_API_CONTRACT.get("parent_contract_version") != PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("S4.4 public parent version drift")
    if PUBLIC_API_CONTRACT.get("supported_imports") != SUPPORTED_PUBLIC_IMPORTS:
        errors.append("S4.4 public import surface drift")
    if PUBLIC_API_CONTRACT.get("supported_engine_methods") != SUPPORTED_ENGINE_METHODS:
        errors.append("S4.4 public engine method surface drift")
    if SUPPORTED_ENGINE_METHODS != list(getattr(_base, "SUPPORTED_ENGINE_METHODS", [])):
        errors.append("S4.4 public overlay added engine methods")
    if SUPPORTED_CLI_COMMANDS != list(getattr(_base, "SUPPORTED_CLI_COMMANDS", [])):
        errors.append("S4.4 public overlay changed CLI commands")
    if "uncertainty-scenario-trace" not in SUPPORTED_INSPECTION_SURFACES:
        errors.append("S4.4 inspection surface missing")

    missing_imports = [name for name in _UST_IMPORTS if name not in globals()]
    if missing_imports:
        errors.append(f"missing S4.4 public imports: {missing_imports}")

    expected = {
        "uncertainty": UNCERTAINTY_CONTRACT_ID,
        "scenario": SCENARIO_CONTRACT_ID,
        "trace_property": TRACE_PROPERTY_CONTRACT_ID,
    }
    for key, contract_id in expected.items():
        value = PUBLIC_API_CONTRACT.get(key) or {}
        if value.get("contract_id") != contract_id:
            errors.append(f"S4.4 {key} contract identity drift")
        if value.get("public_admission") != UNCERTAINTY_SCENARIO_TRACE_PUBLIC_ADMISSION:
            errors.append(f"S4.4 {key} public admission drift")
        if value.get("runtime_admission") != "PRE_ADMISSION_ONLY":
            errors.append(f"S4.4 {key} runtime admission drift")
        if value.get("engine_state_integration") != "NONE_SEMANTIC_IR_ONLY":
            errors.append(f"S4.4 {key} engine-state boundary drift")
        if value.get("active_root_status") != "ACTIVE_QUALIFIED_PUBLIC_ROOT":
            errors.append(f"S4.4 {key} active-root status drift")
        if any(item != "NONE" for item in (value.get("public_claim_ceiling") or {}).values()):
            errors.append(f"S4.4 {key} public claim ceiling drift")

    uncertainty = PUBLIC_API_CONTRACT.get("uncertainty") or {}
    scenario = PUBLIC_API_CONTRACT.get("scenario") or {}
    trace = PUBLIC_API_CONTRACT.get("trace_property") or {}
    if uncertainty.get("parallel_uncertainty_registry") != "NONE" or uncertainty.get("current_uncertainty_pointer") != "NONE":
        errors.append("uncertainty registry/current-pointer firewall drift")
    if scenario.get("parallel_scenario_registry") != "NONE" or scenario.get("hidden_current_scenario") != "NONE":
        errors.append("scenario registry/current-pointer firewall drift")
    if scenario.get("scenario_activation") != "NONE_FOUNDATION_ONLY":
        errors.append("scenario activation claim drift")
    if trace.get("parallel_trace_store") != "NONE" or trace.get("parallel_property_registry") != "NONE":
        errors.append("trace/property parallel-store firewall drift")
    if trace.get("static_constraint_lowering") != "NONE":
        errors.append("trace-property static-lowering firewall drift")
    if trace.get("invariant_classification") != "DYNAMIC_KERNEL":
        errors.append("trace-property invariant classification drift")

    return {
        "valid": not errors,
        "errors": errors,
        "contract": public_api_contract(),
        "contract_version": PUBLIC_ADOPTION_CONTRACT_VERSION,
        "parent_contract_version": PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION,
        "uncertainty_contract_id": UNCERTAINTY_CONTRACT_ID,
        "scenario_contract_id": SCENARIO_CONTRACT_ID,
        "trace_property_contract_id": TRACE_PROPERTY_CONTRACT_ID,
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
            "UNCERTAINTY_SCENARIO_TRACE_PUBLIC_ADMISSION",
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
