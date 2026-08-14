from copy import deepcopy
from . import public_v45 as _v45

for _name in dir(_v45):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v45, _name)

from .advanced_optimization import (
    ADVANCED_OPTIMIZATION_CONTRACT_ID,
    ADVANCED_OPTIMIZATION_CONTRACT_VERSION,
    ADVANCED_KINDS,
    ADVANCED_CAPABILITIES,
    ADVANCED_PROVIDERS,
    FastSATProblem,
    IncrementalSATProblem,
    SchedulingInterval,
    NoOverlapConstraint,
    CumulativeConstraint,
    CPSATSchedulingProblem,
    AdvancedMILPProblem,
    AffineExpression,
    QuadraticFactor,
    AffineSOCConstraint,
    AdvancedConvexObjective,
    AdvancedConvexProblem,
    AdvancedSolverRequest,
    AdvancedSolverIdentity,
    AdvancedSolverResult,
    advanced_problem_from_dict,
    advanced_optimization_contract,
    default_advanced_capability_contracts,
    default_advanced_providers,
    advanced_optimization_blueprint,
    validate_advanced_result,
    advanced_result_satisfies_request,
    clear_incremental_sat_sessions,
    reference_advanced_problems,
)
from .advanced_execution import solve_advanced_request
from .advanced_optimization_conformance import run_advanced_optimization_conformance
from .runtime_v46 import AASMEngine

__version__ = "0.46.0"
REMOTE_PROTOCOL_NAME = _v45.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v45.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "advanced_optimization_contract_report",
    "advanced_optimization_blueprint",
    "install_default_advanced_optimization_capabilities",
    "register_advanced_optimization_provider_runtime",
    "install_default_advanced_optimization_providers",
    "advanced_problem_report",
    "admit_advanced_problem",
    "advanced_request_report",
    "advanced_result_report",
    "request_advanced_optimization",
    "commit_advanced_optimization_result",
    "execute_advanced_optimization_lease",
    "advanced_optimization_reuse_request",
]
_NEW_IMPORTS = [
    "ADVANCED_OPTIMIZATION_CONTRACT_ID",
    "ADVANCED_OPTIMIZATION_CONTRACT_VERSION",
    "ADVANCED_KINDS",
    "ADVANCED_CAPABILITIES",
    "ADVANCED_PROVIDERS",
    "FastSATProblem",
    "IncrementalSATProblem",
    "SchedulingInterval",
    "NoOverlapConstraint",
    "CumulativeConstraint",
    "CPSATSchedulingProblem",
    "AdvancedMILPProblem",
    "AffineExpression",
    "QuadraticFactor",
    "AffineSOCConstraint",
    "AdvancedConvexObjective",
    "AdvancedConvexProblem",
    "AdvancedSolverRequest",
    "AdvancedSolverIdentity",
    "AdvancedSolverResult",
    "advanced_problem_from_dict",
    "advanced_optimization_contract",
    "default_advanced_capability_contracts",
    "default_advanced_providers",
    "advanced_optimization_blueprint",
    "validate_advanced_result",
    "advanced_result_satisfies_request",
    "solve_advanced_request",
    "clear_incremental_sat_sessions",
    "reference_advanced_problems",
    "run_advanced_optimization_conformance",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v45, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v45, "SUPPORTED_CLI_COMMANDS", []),
    "advanced-optimization-contract",
    "advanced-optimization-blueprint",
    "advanced-optimization-conformance",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v45, "SUPPORTED_INSPECTION_SURFACES", []),
    "advanced-optimization-problems",
    "advanced-optimization-results",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v45, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v45.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.22.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["advanced_optimization"] = advanced_optimization_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v45.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.45: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing current imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.46 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.22.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    advanced = PUBLIC_API_CONTRACT.get("advanced_optimization") or {}
    if advanced.get("contract_id") != ADVANCED_OPTIMIZATION_CONTRACT_ID:
        errors.append("advanced optimization contract mismatch")
    if advanced.get("contract_version") != ADVANCED_OPTIMIZATION_CONTRACT_VERSION:
        errors.append("advanced optimization version mismatch")
    if advanced.get("scheduler") != "EXISTING_AASM_RESOURCE_WORKER_LEASE":
        errors.append("advanced optimization scheduler boundary mismatch")
    if advanced.get("result_authority") != "EVIDENCE_ONLY":
        errors.append("advanced optimization result authority mismatch")
    if advanced.get("truth_rule") != "SEARCH_STATE_NEVER_PROMOTES_TRUTH":
        errors.append("advanced search-state truth boundary mismatch")
    if advanced.get("incremental_sat", {}).get("learned_state") != "EPHEMERAL_PERFORMANCE_ONLY":
        errors.append("incremental SAT learned-state boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
