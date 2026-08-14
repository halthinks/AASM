from copy import deepcopy
from . import public_v48 as _v48

for _name in dir(_v48):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v48, _name)

from .semantic_solver_rc import (
    SEMANTIC_SOLVER_RC_CONTRACT_ID,
    SEMANTIC_SOLVER_RC_CONTRACT_VERSION,
    SEMANTIC_SOLVER_RC_STABILITY,
    build_semantic_solver_rc_freeze_manifest,
    run_claim_gate_audit,
    run_cross_backend_overlap_certification,
    run_rc_benchmarks,
    run_semantic_solver_rc_certification,
    run_upgrade_compatibility,
    semantic_solver_rc_contract,
)
from .runtime_v49 import AASMEngine

__version__ = "0.49.0"
PUBLIC_RELEASE_STABILITY = "RELEASE_CANDIDATE"
REMOTE_PROTOCOL_NAME = _v48.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v48.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "semantic_solver_rc_contract_report",
    "semantic_solver_rc_freeze_manifest",
    "semantic_solver_rc_upgrade_report",
    "semantic_solver_rc_cross_backend_report",
    "semantic_solver_rc_benchmark_report",
    "semantic_solver_rc_claim_audit",
    "semantic_solver_rc_certify",
]
_NEW_IMPORTS = [
    "PUBLIC_RELEASE_STABILITY",
    "SEMANTIC_SOLVER_RC_CONTRACT_ID",
    "SEMANTIC_SOLVER_RC_CONTRACT_VERSION",
    "SEMANTIC_SOLVER_RC_STABILITY",
    "semantic_solver_rc_contract",
    "build_semantic_solver_rc_freeze_manifest",
    "run_cross_backend_overlap_certification",
    "run_upgrade_compatibility",
    "run_rc_benchmarks",
    "run_claim_gate_audit",
    "run_semantic_solver_rc_certification",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v48, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v48, "SUPPORTED_CLI_COMMANDS", []),
    "semantic-solver-rc-contract",
    "semantic-solver-rc-freeze",
    "semantic-solver-rc-upgrade",
    "semantic-solver-rc-cross-backend",
    "semantic-solver-rc-benchmark",
    "semantic-solver-rc-claim-audit",
    "semantic-solver-rc-certify",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v48, "SUPPORTED_INSPECTION_SURFACES", []),
    "semantic-solver-rc-freeze",
    "semantic-solver-rc-upgrade",
    "semantic-solver-rc-benchmark",
    "semantic-solver-rc-certification",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v48, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v48.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.25.0",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["semantic_solver_rc"] = semantic_solver_rc_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v48.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.48: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.49 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.49 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.25.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("release_stability") != PUBLIC_RELEASE_STABILITY:
        errors.append("release stability mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("stability") != PUBLIC_RELEASE_STABILITY:
        errors.append("distribution stability mismatch")
    rc = PUBLIC_API_CONTRACT.get("semantic_solver_rc") or {}
    if rc.get("contract_id") != SEMANTIC_SOLVER_RC_CONTRACT_ID or rc.get("contract_version") != SEMANTIC_SOLVER_RC_CONTRACT_VERSION:
        errors.append("semantic solver RC contract identity mismatch")
    if rc.get("stability") != SEMANTIC_SOLVER_RC_STABILITY:
        errors.append("semantic solver RC stability mismatch")
    if rc.get("runtime_extension") != "THIN_V48_COMPOSITION_NO_NEW_KERNEL":
        errors.append("semantic solver RC kernel boundary mismatch")
    if rc.get("cross_backend_rule") != "AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE":
        errors.append("semantic solver RC cross-backend rule mismatch")
    if rc.get("native_solver_claim") != "AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS":
        errors.append("semantic solver RC performance-claim boundary mismatch")
    if rc.get("claim_policy") != "NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE":
        errors.append("semantic solver RC claim-gate policy mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
