from __future__ import annotations

from copy import deepcopy

from . import public_v56 as _base

for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .effect_capability import (
    EFFECT_CAPABILITY_CONTRACT_ID,
    EFFECT_CAPABILITY_CONTRACT_VERSION,
    EFFECT_CAPABILITY_STABILITY,
    EffectCapability,
    NumericInterval,
    effect_capability_contract,
    normalize_numeric_bounds,
    numeric_bounds_subset,
)
from .effect_capability_runtime import (
    EFFECT_CAPABILITY_CAPABILITIES,
    EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID,
    EFFECT_CAPABILITY_RUNTIME_CONTRACT_VERSION,
    EFFECT_CAPABILITY_RUNTIME_STABILITY,
    effect_capability_runtime_contract,
    project_effect_capability_evidence,
)
from .effect_capability_use import (
    EFFECT_CAPABILITY_USE_CONTRACT_ID,
    EFFECT_CAPABILITY_USE_CONTRACT_VERSION,
    EFFECT_CAPABILITY_USE_STABILITY,
    EffectCapabilityUse,
    effect_capability_use_contract,
)
from .physical_control_fencing_runtime import (
    PHYSICAL_CONTROL_FENCING_CAPABILITIES,
    PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID,
    PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_VERSION,
    PHYSICAL_CONTROL_FENCING_RUNTIME_STABILITY,
    physical_control_fencing_runtime_contract,
    project_physical_control_fencing_evidence,
)
from .physical_effect_binding import (
    PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID,
    PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION,
    PHYSICAL_EFFECT_AUTHORITY_BINDING_STABILITY,
    PhysicalEffectAuthorityBinding,
    physical_effect_authority_binding_contract,
)
from .physical_effect_integration_runtime import (
    PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES,
    PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID,
    PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_VERSION,
    PHYSICAL_EFFECT_INTEGRATION_RUNTIME_STABILITY,
    physical_effect_integration_runtime_contract,
    project_physical_effect_integration_evidence,
)
from .physical_preemption import (
    AUTHORITY_PREEMPTION_CONTRACT_ID,
    AUTHORITY_PREEMPTION_CONTRACT_VERSION,
    AUTHORITY_PREEMPTION_STABILITY,
    AuthorityPreemption,
    authority_preemption_contract,
)
from .runtime_v56 import AASMEngine


__version__ = _base.__version__
PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY
REMOTE_PROTOCOL_NAME = _base.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _base.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "effect_capability_contract_report",
    "issue_effect_capability",
    "delegate_effect_capability",
    "revoke_effect_capability",
    "effect_capability_report",
    "effect_capabilities_report",
    "physical_control_fencing_contract_report",
    "validate_effect_capability_use",
    "preempt_authority_lease",
    "effect_capability_use_report",
    "authority_preemption_report",
    "physical_control_fencing_report",
    "physical_effect_integration_contract_report",
    "bind_physical_effect_authority",
    "physical_effect_binding_report",
    "physical_effect_integration_report",
]

_NEW_IMPORTS = [
    "EFFECT_CAPABILITY_CONTRACT_ID",
    "EFFECT_CAPABILITY_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_STABILITY",
    "NumericInterval",
    "EffectCapability",
    "normalize_numeric_bounds",
    "numeric_bounds_subset",
    "effect_capability_contract",
    "EFFECT_CAPABILITY_RUNTIME_CONTRACT_ID",
    "EFFECT_CAPABILITY_RUNTIME_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_RUNTIME_STABILITY",
    "EFFECT_CAPABILITY_CAPABILITIES",
    "project_effect_capability_evidence",
    "effect_capability_runtime_contract",
    "EFFECT_CAPABILITY_USE_CONTRACT_ID",
    "EFFECT_CAPABILITY_USE_CONTRACT_VERSION",
    "EFFECT_CAPABILITY_USE_STABILITY",
    "EffectCapabilityUse",
    "effect_capability_use_contract",
    "AUTHORITY_PREEMPTION_CONTRACT_ID",
    "AUTHORITY_PREEMPTION_CONTRACT_VERSION",
    "AUTHORITY_PREEMPTION_STABILITY",
    "AuthorityPreemption",
    "authority_preemption_contract",
    "PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_ID",
    "PHYSICAL_CONTROL_FENCING_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_CONTROL_FENCING_RUNTIME_STABILITY",
    "PHYSICAL_CONTROL_FENCING_CAPABILITIES",
    "project_physical_control_fencing_evidence",
    "physical_control_fencing_runtime_contract",
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID",
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_VERSION",
    "PHYSICAL_EFFECT_AUTHORITY_BINDING_STABILITY",
    "PhysicalEffectAuthorityBinding",
    "physical_effect_authority_binding_contract",
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID",
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_VERSION",
    "PHYSICAL_EFFECT_INTEGRATION_RUNTIME_STABILITY",
    "PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES",
    "project_physical_effect_integration_evidence",
    "physical_effect_integration_runtime_contract",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_base, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_base, "SUPPORTED_INSPECTION_SURFACES", []),
    "effect-capability",
    "physical-control-fencing",
    "physical-effect-integration",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.32.8",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["effect_capability"] = {
    **effect_capability_contract(),
    "runtime": effect_capability_runtime_contract(),
    "dependent_effect_integration": "aasm.effect.physical-authority-integration.runtime.v1",
}
PUBLIC_API_CONTRACT["physical_control_fencing"] = {
    **physical_control_fencing_runtime_contract(),
    "effect_capability_use": effect_capability_use_contract(),
    "authority_preemption": authority_preemption_contract(),
    "preemption_recovery": "EXISTING_EVIDENCE_REPLAY_REPAIRS_MISSING_CANONICAL_LEASE_REVOCATION",
    "dependent_effect_integration": "aasm.effect.physical-authority-integration.runtime.v1",
}
PUBLIC_API_CONTRACT["physical_effect_integration"] = {
    **physical_effect_authority_binding_contract(),
    "runtime": physical_effect_integration_runtime_contract(),
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _base.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.56 base: {error}" for error in parent["errors"])

    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing active PR-3 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing active PR-3 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("active runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.8":
        errors.append("active adoption contract mismatch")

    capability = PUBLIC_API_CONTRACT.get("effect_capability", {})
    if capability.get("capability_existence_grants_effect_authority") is not False:
        errors.append("effect capability existence incorrectly grants effect authority")
    if capability.get("effect_authorization_integration") != "NOT_YET_PR3H":
        errors.append("PR-3C/3D child contract boundary drift")
    if capability.get("dependent_effect_integration") != PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID:
        errors.append("effect capability missing PR-3H dependent integration reference")
    cap_runtime = capability.get("runtime", {})
    if cap_runtime.get("authority") != "EXISTING_AASM_SCOPED_AUTHORITY_ONLY":
        errors.append("effect capability introduced parallel authority evaluator")
    if cap_runtime.get("effect_authorization_integration") != "NONE_PR3C_PR3D_FOUNDATION":
        errors.append("PR-3C/3D runtime child boundary drift")
    if cap_runtime.get("effect_dispatch") != "NONE":
        errors.append("effect capability runtime introduced dispatch")
    if cap_runtime.get("parallel_effect_lifecycle") != "NONE":
        errors.append("effect capability runtime introduced parallel effect lifecycle")

    fencing = PUBLIC_API_CONTRACT.get("physical_control_fencing", {})
    if fencing.get("use_validation_grants_effect_authority") is not False:
        errors.append("capability-use validation incorrectly grants effect authority")
    if fencing.get("preemption_grants_effect_authority") is not False:
        errors.append("preemption incorrectly grants effect authority")
    if fencing.get("effect_authorization_integration") != "NONE_PR3E_PR3F_PR3G_FOUNDATION":
        errors.append("PR-3E/F/G child runtime boundary drift")
    if fencing.get("dependent_effect_integration") != PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID:
        errors.append("physical control fencing missing PR-3H dependent integration reference")
    if fencing.get("effect_dispatch") != "NONE":
        errors.append("physical control fencing introduced dispatch")
    if fencing.get("parallel_authority_evaluator") != "NONE":
        errors.append("physical control fencing introduced parallel authority evaluator")
    if fencing.get("parallel_effect_lifecycle") != "NONE":
        errors.append("physical control fencing introduced parallel effect lifecycle")
    use = fencing.get("effect_capability_use", {})
    if use.get("validation_is_reusable_authorization_token") is not False:
        errors.append("capability-use validation became reusable authorization token")
    if use.get("required_recheck") != "PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES":
        errors.append("PR-3H recheck boundary missing")
    preemption = fencing.get("authority_preemption", {})
    if preemption.get("identity_reference_grants_authority") is not False:
        errors.append("preemptor listing incorrectly grants authority")
    if preemption.get("preemption_grants_new_effect_authority") is not False:
        errors.append("preemption incorrectly grants new effect authority")

    integration = PUBLIC_API_CONTRACT.get("physical_effect_integration", {})
    if integration.get("contract_id") != PHYSICAL_EFFECT_AUTHORITY_BINDING_CONTRACT_ID:
        errors.append("physical effect binding contract missing")
    if integration.get("authorization_recheck") != "MANDATORY_AT_EXISTING_AUTHORIZE_EFFECT_BOUNDARY":
        errors.append("physical effect authorization recheck missing")
    if integration.get("execution_recheck") != "MANDATORY_AT_EXISTING_EXECUTE_EFFECT_BOUNDARY":
        errors.append("physical effect execution recheck missing")
    if integration.get("binding_existence_grants_effect_authority") is not False:
        errors.append("physical effect binding incorrectly grants effect authority")
    if integration.get("prior_use_validation_is_authorization") is not False:
        errors.append("prior capability-use validation became authorization")
    integration_runtime = integration.get("runtime", {})
    if integration_runtime.get("contract_id") != PHYSICAL_EFFECT_INTEGRATION_RUNTIME_CONTRACT_ID:
        errors.append("physical effect integration runtime contract missing")
    if integration_runtime.get("effect_authority") != "EXISTING_V53_EFFECT_AUTHORIZE_AND_EFFECT_EXECUTE_REMAIN_REQUIRED":
        errors.append("physical effect integration replaced scoped effect authority")
    if integration_runtime.get("task_lease") != "EXISTING_V54_TASKLEASE_UNCHANGED":
        errors.append("physical effect integration replaced TaskLease")
    if integration_runtime.get("ownership") != "EXISTING_V54_EFFECT_OWNERSHIP_UNCHANGED":
        errors.append("physical effect integration replaced EffectOwnership")
    if integration_runtime.get("unknown_and_reconciliation") != "EXISTING_V54_UNKNOWN_AND_RECONCILIATION_UNCHANGED":
        errors.append("physical effect integration replaced UNKNOWN/reconciliation")
    if integration_runtime.get("parallel_authority_evaluator") != "NONE":
        errors.append("physical effect integration introduced parallel authority evaluator")
    if integration_runtime.get("parallel_effect_store") != "NONE":
        errors.append("physical effect integration introduced parallel effect store")
    if integration_runtime.get("parallel_effect_lifecycle") != "NONE":
        errors.append("physical effect integration introduced parallel effect lifecycle")
    if integration_runtime.get("parallel_dispatcher") != "NONE":
        errors.append("physical effect integration introduced parallel dispatcher")

    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
