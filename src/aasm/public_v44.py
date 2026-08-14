from copy import deepcopy
from . import public_v43 as _v43

for _name in dir(_v43):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v43, _name)

from .optimization import (
    OPTIMIZATION_CONTRACT_ID,
    OPTIMIZATION_CONTRACT_VERSION,
    OPTIMIZATION_FAMILIES,
    OPTIMIZATION_STATUSES,
    OPTIMIZATION_CAPABILITIES,
    BooleanLiteral,
    OptimizationVariable,
    OptimizationConstraint,
    OptimizationObjective,
    OptimizationModel,
    OptimizationRequest,
    OptimizationSolverIdentity,
    OptimizationResult,
    optimization_contract,
    optimization_blueprint,
    default_optimization_capability_contracts,
    default_optimization_providers,
    infer_solver_family,
    validate_optimization_solution,
    validate_optimization_result,
    solve_optimization_request,
    reference_optimization_models,
)
from .runtime_v44 import AASMEngine

__version__ = "0.44.0"
REMOTE_PROTOCOL_NAME = _v43.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v43.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "optimization_contract_report",
    "optimization_blueprint",
    "install_default_optimization_capability_contracts",
    "register_optimization_provider_runtime",
    "optimization_model_report",
    "admit_optimization_model",
    "optimization_request_report",
    "optimization_result_report",
    "request_optimization",
    "commit_optimization_result",
    "execute_optimization_lease",
    "optimization_reuse_request",
]
_NEW_IMPORTS = [
    "OPTIMIZATION_FAMILIES",
    "OPTIMIZATION_STATUSES",
    "OPTIMIZATION_CAPABILITIES",
    "BooleanLiteral",
    "OptimizationVariable",
    "OptimizationConstraint",
    "OptimizationObjective",
    "OptimizationModel",
    "OptimizationRequest",
    "OptimizationSolverIdentity",
    "OptimizationResult",
    "optimization_contract",
    "optimization_blueprint",
    "default_optimization_capability_contracts",
    "default_optimization_providers",
    "infer_solver_family",
    "validate_optimization_solution",
    "validate_optimization_result",
    "solve_optimization_request",
    "reference_optimization_models",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v43, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v43, "SUPPORTED_CLI_COMMANDS", []),
    "optimization-contract",
    "optimization-blueprint",
    "optimization-conformance",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v43, "SUPPORTED_INSPECTION_SURFACES", []),
    "optimization-portfolio",
    "optimization-models",
    "optimization-results",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v43, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v43.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.20.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["optimization"] = optimization_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v43.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.43: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing current imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing optimization engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.20.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    optimization = PUBLIC_API_CONTRACT.get("optimization") or {}
    if optimization.get("contract_id") != OPTIMIZATION_CONTRACT_ID:
        errors.append("optimization contract mismatch")
    if optimization.get("contract_version") != OPTIMIZATION_CONTRACT_VERSION:
        errors.append("optimization contract version mismatch")
    if optimization.get("scheduler") != "EXISTING_AASM_RESOURCE_WORKER_LEASE":
        errors.append("optimization scheduler boundary mismatch")
    if optimization.get("result_authority") != "EVIDENCE_ONLY":
        errors.append("optimization result authority mismatch")
    if optimization.get("formal_providers_preserved") != ["z3", "cvc5", "vampire", "lean4"]:
        errors.append("formal provider preservation mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
