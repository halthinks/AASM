from copy import deepcopy
from . import public_v50 as _v50

for _name in dir(_v50):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v50, _name)

from .solution_pool_conformance import run_solution_pool_conformance
from .solution_pools import (
    ENUMERATION_CHECKER_ID,
    ENUMERATION_CHECKER_VERSION,
    ENUMERATION_CONTRACT_ID,
    ENUMERATION_CONTRACT_VERSION,
    POOL_COMPLETENESS_STATUSES,
    SOLUTION_POOL_CONTRACT_ID,
    SOLUTION_POOL_CONTRACT_VERSION,
    SOLUTION_POOL_MODES,
    SOLUTION_POOL_STABILITY,
    EnumerationCompletenessCertificate,
    EnumerationCursor,
    EnumerationUnsupportedError,
    SolutionExclusion,
    SolutionPool,
    SolutionRecord,
    assignment_fingerprint,
    binary_overlap_models,
    certify_complete_finite_enumeration,
    enumerate_finite_step,
    enumerate_native_binary_backend,
    enumeration_contract,
    initial_enumeration_cursor,
    solution_pool_contract,
)
from .runtime_v51 import AASMEngine

__version__ = "0.51.0"
PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"
REMOTE_PROTOCOL_NAME = _v50.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v50.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "solution_pool_contract_report",
    "enumeration_contract_report",
    "solution_pool_report",
    "start_solution_pool",
    "admit_solution_to_pool",
    "advance_solution_pool",
    "enumerate_complete_solution_pool",
]
_NEW_IMPORTS = [
    "SOLUTION_POOL_CONTRACT_ID", "SOLUTION_POOL_CONTRACT_VERSION", "ENUMERATION_CONTRACT_ID",
    "ENUMERATION_CONTRACT_VERSION", "SOLUTION_POOL_STABILITY", "SOLUTION_POOL_MODES",
    "POOL_COMPLETENESS_STATUSES", "ENUMERATION_CHECKER_ID", "ENUMERATION_CHECKER_VERSION",
    "EnumerationUnsupportedError", "SolutionRecord", "SolutionExclusion", "EnumerationCursor",
    "SolutionPool", "EnumerationCompletenessCertificate", "solution_pool_contract", "enumeration_contract",
    "assignment_fingerprint", "initial_enumeration_cursor", "enumerate_finite_step",
    "certify_complete_finite_enumeration", "enumerate_native_binary_backend", "binary_overlap_models",
    "run_solution_pool_conformance",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v50, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v50, "SUPPORTED_CLI_COMMANDS", []),
    "solution-pool-contract", "enumeration-contract", "solution-pool-conformance",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v50, "SUPPORTED_INSPECTION_SURFACES", []),
    "solution-pools", "enumeration-cursors", "enumeration-completeness",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v50, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v50.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.27.0",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["solution_pool"] = solution_pool_contract()
PUBLIC_API_CONTRACT["enumeration"] = enumeration_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v50.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.50: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.51 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.51 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.27.0":
        errors.append("adoption contract mismatch")
    pool = PUBLIC_API_CONTRACT.get("solution_pool") or {}
    enumeration = PUBLIC_API_CONTRACT.get("enumeration") or {}
    if pool.get("contract_id") != SOLUTION_POOL_CONTRACT_ID or pool.get("contract_version") != SOLUTION_POOL_CONTRACT_VERSION:
        errors.append("solution pool contract identity mismatch")
    if enumeration.get("contract_id") != ENUMERATION_CONTRACT_ID or enumeration.get("contract_version") != ENUMERATION_CONTRACT_VERSION:
        errors.append("enumeration contract identity mismatch")
    if pool.get("complete_requires_independent_exhaustion_certificate") is not True:
        errors.append("complete pool must require independent exhaustion certificate")
    if pool.get("bounded_or_native_pool_implies_completeness") is not False:
        errors.append("bounded/native pool must not imply completeness")
    if enumeration.get("complete_claim_without_certificate") != "REJECTED":
        errors.append("uncertified completeness must be rejected")
    if pool.get("result_authority") != "EVIDENCE_ONLY" or pool.get("truth_authority") != "EXISTING_AASM_POLICY_ONLY":
        errors.append("solution-pool authority boundary mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
