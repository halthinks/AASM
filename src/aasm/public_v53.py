from __future__ import annotations

from copy import deepcopy

from . import public_v52 as _v52

for _name in dir(_v52):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v52, _name)

from ._runtime_v53_authority import (
    SCOPED_AUTHORITY_RUNTIME_CONTRACT_ID,
    SCOPED_AUTHORITY_RUNTIME_CONTRACT_VERSION,
    SCOPED_AUTHORITY_RUNTIME_STABILITY,
    scoped_authority_runtime_contract,
)
from ._runtime_v53_solver_learning import (
    SOLVER_LEARNING_AUTHORITY_CAPABILITIES,
    SOLVER_LEARNING_RUNTIME_CONTRACT_ID,
    SOLVER_LEARNING_RUNTIME_CONTRACT_VERSION,
    SOLVER_LEARNING_RUNTIME_STABILITY,
    solver_learning_runtime_contract,
)
from .runtime_v53_learning import AASMEngine, SOLVER_LEARNING_APPLY_CAPABILITY
from .scoped_authority import (
    AUTHORITY_EFFECTS,
    AUTHORITY_WILDCARD,
    PRINCIPAL_KINDS,
    SCOPED_AUTHORITY_CONTRACT_ID,
    SCOPED_AUTHORITY_CONTRACT_VERSION,
    SCOPED_AUTHORITY_STABILITY,
    SCOPED_IDENTITY_CONTRACT_ID,
    AuthorityDecision,
    AuthorityRequest,
    Principal,
    ScopedAuthorityGrant,
    Workspace,
    evaluate_scoped_authority,
    scoped_authority_contract,
    validate_grant_admission,
)
from .scoped_store import (
    SCOPED_STORE_CONTRACT_ID,
    SCOPED_STORE_CONTRACT_VERSION,
    SCOPED_STORE_STABILITY,
    STORE_CAPABILITIES,
    ScopedStoreAccess,
    ScopedStoreView,
    scoped_store_contract,
)
from .solver_learning import (
    CORRECTNESS_SENSITIVE_KINDS,
    PERFORMANCE_HINT_KINDS,
    SOLVER_LEARNING_APPLICATION_CLASSES,
    SOLVER_LEARNING_APPLICATION_CONTRACT_ID,
    SOLVER_LEARNING_APPLICATION_CONTRACT_VERSION,
    SOLVER_LEARNING_CHECKER_ID,
    SOLVER_LEARNING_CHECKER_VERSION,
    SOLVER_LEARNING_CONTRACT_ID,
    SOLVER_LEARNING_CONTRACT_VERSION,
    SOLVER_LEARNING_KINDS,
    SOLVER_LEARNING_STABILITY,
    SolverLearningApplication,
    SolverLearningArtifact,
    SolverLearningValidation,
    apply_solver_learning_to_optimization_request,
    build_solver_learning_application,
    revalidate_finite_solver_learning,
    solver_learning_application_contract,
    solver_learning_contract,
    validate_native_accelerator_hint,
)


__version__ = "0.53.0"
PUBLIC_RELEASE_STABILITY = "PRE_RELEASE"
REMOTE_PROTOCOL_NAME = _v52.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v52.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "scoped_authority_runtime_contract_report",
    "bootstrap_scoped_workspace",
    "evaluate_scoped_request",
    "authorize_scoped_request",
    "register_scoped_principal",
    "admit_scoped_authority_grant",
    "scoped_authority_report",
    "effect_authority_report",
    "solver_learning_contract_report",
    "solver_learning_runtime_contract_report",
    "record_solver_learning_artifact",
    "export_solver_learning_artifact",
    "admit_cross_run_solver_learning",
    "revalidate_solver_learning",
    "apply_solver_learning",
    "solver_learning_report",
]

_NEW_IMPORTS = [
    "SCOPED_IDENTITY_CONTRACT_ID",
    "SCOPED_AUTHORITY_CONTRACT_ID",
    "SCOPED_AUTHORITY_CONTRACT_VERSION",
    "SCOPED_AUTHORITY_STABILITY",
    "SCOPED_AUTHORITY_RUNTIME_CONTRACT_ID",
    "SCOPED_AUTHORITY_RUNTIME_CONTRACT_VERSION",
    "SCOPED_AUTHORITY_RUNTIME_STABILITY",
    "PRINCIPAL_KINDS",
    "AUTHORITY_EFFECTS",
    "AUTHORITY_WILDCARD",
    "Principal",
    "Workspace",
    "ScopedAuthorityGrant",
    "AuthorityRequest",
    "AuthorityDecision",
    "scoped_authority_contract",
    "scoped_authority_runtime_contract",
    "evaluate_scoped_authority",
    "validate_grant_admission",
    "SCOPED_STORE_CONTRACT_ID",
    "SCOPED_STORE_CONTRACT_VERSION",
    "SCOPED_STORE_STABILITY",
    "STORE_CAPABILITIES",
    "ScopedStoreAccess",
    "ScopedStoreView",
    "scoped_store_contract",
    "SOLVER_LEARNING_CONTRACT_ID",
    "SOLVER_LEARNING_CONTRACT_VERSION",
    "SOLVER_LEARNING_STABILITY",
    "SOLVER_LEARNING_CHECKER_ID",
    "SOLVER_LEARNING_CHECKER_VERSION",
    "SOLVER_LEARNING_KINDS",
    "CORRECTNESS_SENSITIVE_KINDS",
    "PERFORMANCE_HINT_KINDS",
    "SolverLearningArtifact",
    "SolverLearningValidation",
    "solver_learning_contract",
    "revalidate_finite_solver_learning",
    "validate_native_accelerator_hint",
    "SOLVER_LEARNING_APPLICATION_CONTRACT_ID",
    "SOLVER_LEARNING_APPLICATION_CONTRACT_VERSION",
    "SOLVER_LEARNING_APPLICATION_CLASSES",
    "SolverLearningApplication",
    "solver_learning_application_contract",
    "build_solver_learning_application",
    "apply_solver_learning_to_optimization_request",
    "SOLVER_LEARNING_RUNTIME_CONTRACT_ID",
    "SOLVER_LEARNING_RUNTIME_CONTRACT_VERSION",
    "SOLVER_LEARNING_RUNTIME_STABILITY",
    "SOLVER_LEARNING_AUTHORITY_CAPABILITIES",
    "SOLVER_LEARNING_APPLY_CAPABILITY",
    "solver_learning_runtime_contract",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v52, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v52, "SUPPORTED_CLI_COMMANDS", []),
    "scoped-authority-contract",
    "scoped-authority-runtime-contract",
    "scoped-store-contract",
    "solver-learning-contract",
    "solver-learning-runtime-contract",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v52, "SUPPORTED_INSPECTION_SURFACES", []),
    "scoped-authority",
    "scoped-store",
    "effect-authority",
    "solver-learning",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v52, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v52.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.29.0",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["scoped_identity_authority"] = {
    **scoped_authority_contract(),
    "runtime": scoped_authority_runtime_contract(),
}
PUBLIC_API_CONTRACT["scoped_store"] = scoped_store_contract()
PUBLIC_API_CONTRACT["solver_learning"] = {
    **solver_learning_contract(),
    "application_contract": solver_learning_application_contract(),
    "runtime": solver_learning_runtime_contract(),
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v52.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.52: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.53 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.53 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.29.0":
        errors.append("adoption contract mismatch")
    authority = PUBLIC_API_CONTRACT.get("scoped_identity_authority") or {}
    authority_runtime = authority.get("runtime") or {}
    store_contract = PUBLIC_API_CONTRACT.get("scoped_store") or {}
    solver_learning = PUBLIC_API_CONTRACT.get("solver_learning") or {}
    solver_application = solver_learning.get("application_contract") or {}
    solver_runtime = solver_learning.get("runtime") or {}
    if authority.get("contract_id") != SCOPED_AUTHORITY_CONTRACT_ID:
        errors.append("scoped authority contract identity mismatch")
    if authority.get("default") != "DENY" or authority.get("cross_run_authority_transfer") != "NEVER":
        errors.append("scoped authority fail-closed boundary mismatch")
    if authority.get("resource_state_grants_authority") is not False:
        errors.append("resource state must not grant scoped authority")
    if authority_runtime.get("contract_id") != SCOPED_AUTHORITY_RUNTIME_CONTRACT_ID:
        errors.append("scoped authority runtime contract identity mismatch")
    if store_contract.get("contract_id") != SCOPED_STORE_CONTRACT_ID:
        errors.append("scoped store contract identity mismatch")
    if store_contract.get("raw_snapshot_access") != "ROOT_SCOPE_SINGLE_WORKSPACE_ONLY":
        errors.append("scoped store raw snapshot boundary mismatch")
    if store_contract.get("multi_workspace_raw_access") != "FAIL_CLOSED_USE_SCOPED_PROJECTIONS":
        errors.append("scoped store multi-workspace boundary mismatch")
    if store_contract.get("direct_store_write") != "FORBIDDEN_USE_GOVERNED_RUNTIME_TRANSITIONS":
        errors.append("scoped store write boundary mismatch")
    if solver_learning.get("contract_id") != SOLVER_LEARNING_CONTRACT_ID:
        errors.append("solver learning contract identity mismatch")
    if solver_learning.get("cross_run_transport") != "EXISTING_AASM_V48_REUSE_RESULT_ENVELOPE":
        errors.append("solver learning transport boundary mismatch")
    if solver_learning.get("cross_run_authority_transfer") != "NEVER":
        errors.append("solver learning must not transfer authority")
    if solver_learning.get("cross_run_admission_implies_truth") is not False:
        errors.append("cross-run solver learning admission must not imply truth")
    if solver_learning.get("pruning_application") != "LOCAL_REVALIDATION_REQUIRED":
        errors.append("correctness-sensitive solver learning must require local revalidation")
    if solver_learning.get("application") != "EXPLICIT_VALIDATED_ADAPTER_APPLICATION_ONLY":
        errors.append("solver learning application declaration mismatch")
    if solver_learning.get("application_truth_authority") != "NONE" or solver_learning.get("application_policy_authority") != "NONE":
        errors.append("solver learning application must carry no truth or policy authority")
    if solver_application.get("contract_id") != SOLVER_LEARNING_APPLICATION_CONTRACT_ID:
        errors.append("solver learning application contract identity mismatch")
    if solver_application.get("validation_required") != "PASS_EXACT_ARTIFACT_AND_MODEL":
        errors.append("solver learning application validation boundary mismatch")
    if solver_application.get("truth_authority") != "NONE" or solver_application.get("policy_authority") != "NONE":
        errors.append("solver learning application contract must carry no authority")
    if solver_runtime.get("contract_id") != SOLVER_LEARNING_RUNTIME_CONTRACT_ID:
        errors.append("solver learning runtime contract identity mismatch")
    if solver_runtime.get("application") != "EXPLICIT_VALIDATED_ADAPTER_APPLICATION_ONLY":
        errors.append("solver learning runtime application boundary mismatch")
    if solver_runtime.get("apply_authority") != "SCOPED_SOLVER_LEARNING_APPLY_REQUIRED":
        errors.append("solver learning apply authority boundary mismatch")
    if solver_runtime.get("truth_authority") != "NONE" or solver_runtime.get("policy_authority") != "NONE":
        errors.append("solver learning runtime must not grant truth or policy authority")
    if solver_runtime.get("solver_execution") != "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY":
        errors.append("solver learning execution path mismatch")
    if SOLVER_LEARNING_AUTHORITY_CAPABILITIES.get("apply") != SOLVER_LEARNING_APPLY_CAPABILITY:
        errors.append("solver learning apply capability mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    if PUBLIC_RELEASE_STABILITY != "PRE_RELEASE":
        errors.append("v0.53 must remain PRE_RELEASE before promotion")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}
