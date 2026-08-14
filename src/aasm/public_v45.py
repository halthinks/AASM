from copy import deepcopy
from . import public_v44 as _v44

for _name in dir(_v44):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v44, _name)

from .convex_optimization import (
    CONVEX_OPTIMIZATION_CONTRACT_ID,
    CONVEX_OPTIMIZATION_CONTRACT_VERSION,
    CONVEX_CAPABILITY_ID,
    ConvexVariable,
    ConvexLinearConstraint,
    SecondOrderConeConstraint,
    ConvexObjective,
    ConvexOptimizationModel,
    ConvexOptimizationRequest,
    ConvexSolverIdentity,
    ConvexOptimizationResult,
    convex_optimization_contract,
    default_convex_capability_contract,
    default_cvxpy_provider,
    validate_convex_solution,
    validate_convex_result,
    solve_convex_request,
    reference_convex_models,
)
from .pulp_adapter import (
    PULP_ADAPTER_CONTRACT_ID,
    PULP_ADAPTER_CONTRACT_VERSION,
    pulp_adapter_contract,
    pulp_problem_to_optimization_model,
    pulp_import_report,
)
from .modeling_conformance import run_modeling_conformance
from .runtime_v45 import AASMEngine

__version__ = "0.45.0"
REMOTE_PROTOCOL_NAME = _v44.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v44.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "convex_optimization_contract_report",
    "install_default_convex_capability_contract",
    "register_default_cvxpy_provider_runtime",
    "convex_model_report",
    "admit_convex_model",
    "convex_request_report",
    "convex_result_report",
    "request_convex_optimization",
    "commit_convex_result",
    "execute_convex_lease",
    "convex_reuse_request",
    "import_pulp_problem",
]
_NEW_IMPORTS = [
    "CONVEX_OPTIMIZATION_CONTRACT_ID",
    "CONVEX_OPTIMIZATION_CONTRACT_VERSION",
    "CONVEX_CAPABILITY_ID",
    "ConvexVariable",
    "ConvexLinearConstraint",
    "SecondOrderConeConstraint",
    "ConvexObjective",
    "ConvexOptimizationModel",
    "ConvexOptimizationRequest",
    "ConvexSolverIdentity",
    "ConvexOptimizationResult",
    "convex_optimization_contract",
    "default_convex_capability_contract",
    "default_cvxpy_provider",
    "validate_convex_solution",
    "validate_convex_result",
    "solve_convex_request",
    "reference_convex_models",
    "PULP_ADAPTER_CONTRACT_ID",
    "PULP_ADAPTER_CONTRACT_VERSION",
    "pulp_adapter_contract",
    "pulp_problem_to_optimization_model",
    "pulp_import_report",
    "run_modeling_conformance",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v44, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v44, "SUPPORTED_CLI_COMMANDS", []),
    "convex-optimization-contract",
    "pulp-adapter-contract",
    "modeling-conformance",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v44, "SUPPORTED_INSPECTION_SURFACES", []),
    "convex-models",
    "convex-results",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v44, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v44.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.21.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["convex_optimization"] = convex_optimization_contract()
PUBLIC_API_CONTRACT["pulp_adapter"] = pulp_adapter_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v44.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.44: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing current imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.45 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.21.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    convex = PUBLIC_API_CONTRACT.get("convex_optimization") or {}
    if convex.get("contract_id") != CONVEX_OPTIMIZATION_CONTRACT_ID:
        errors.append("convex optimization contract mismatch")
    if convex.get("contract_version") != CONVEX_OPTIMIZATION_CONTRACT_VERSION:
        errors.append("convex optimization version mismatch")
    if convex.get("scheduler") != "EXISTING_AASM_RESOURCE_WORKER_LEASE":
        errors.append("convex scheduler boundary mismatch")
    if convex.get("result_authority") != "EVIDENCE_ONLY":
        errors.append("convex result authority mismatch")
    if convex.get("direct_native_v44_paths_preserved") != ["cadical", "ortools-cp-sat", "highs"]:
        errors.append("native v0.44 path preservation mismatch")
    pulp = PUBLIC_API_CONTRACT.get("pulp_adapter") or {}
    if pulp.get("contract_id") != PULP_ADAPTER_CONTRACT_ID:
        errors.append("PuLP adapter contract mismatch")
    if pulp.get("authority") != "TRANSLATION_ONLY" or pulp.get("solver_execution") != "NEVER":
        errors.append("PuLP authority boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
