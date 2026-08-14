from copy import deepcopy
from . import public_v49 as _v49

for _name in dir(_v49):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v49, _name)

from .proof_claim_conformance import run_solver_proof_conformance
from .proof_claims import (
    FINITE_DOMAIN_CHECKER_ID,
    FINITE_DOMAIN_CHECKER_VERSION,
    PROOF_CERTIFIABLE_CLAIMS,
    PROOF_VERIFICATION_LEVELS,
    SOLVER_CLAIM_TYPES,
    SOLVER_PROOF_CONTRACT_ID,
    SOLVER_PROOF_CONTRACT_VERSION,
    SOLVER_PROOF_STABILITY,
    ProofUnsupportedError,
    SolverClaim,
    SolverClaimCertificate,
    SolverProofArtifact,
    build_finite_domain_proof,
    certify_optimization_result,
    claim_from_optimization_result,
    solver_proof_contract,
    verify_finite_domain_proof,
)
from .runtime_v50 import AASMEngine

__version__ = "0.50.0"
PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"
REMOTE_PROTOCOL_NAME = _v49.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v49.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "solver_proof_contract_report",
    "solver_proof_claim_report",
    "certify_optimization_claim",
]
_NEW_IMPORTS = [
    "PUBLIC_RELEASE_STABILITY",
    "SOLVER_PROOF_CONTRACT_ID",
    "SOLVER_PROOF_CONTRACT_VERSION",
    "SOLVER_PROOF_STABILITY",
    "SOLVER_CLAIM_TYPES",
    "PROOF_VERIFICATION_LEVELS",
    "PROOF_CERTIFIABLE_CLAIMS",
    "FINITE_DOMAIN_CHECKER_ID",
    "FINITE_DOMAIN_CHECKER_VERSION",
    "ProofUnsupportedError",
    "SolverClaim",
    "SolverProofArtifact",
    "SolverClaimCertificate",
    "solver_proof_contract",
    "claim_from_optimization_result",
    "build_finite_domain_proof",
    "verify_finite_domain_proof",
    "certify_optimization_result",
    "run_solver_proof_conformance",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v49, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v49, "SUPPORTED_CLI_COMMANDS", []),
    "solver-proof-contract",
    "solver-proof-conformance",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v49, "SUPPORTED_INSPECTION_SURFACES", []),
    "solver-proof-claims",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v49, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v49.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.26.0",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["solver_proof_claims"] = solver_proof_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v49.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.49: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.50 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.50 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.26.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("release_stability") != PUBLIC_RELEASE_STABILITY:
        errors.append("release stability mismatch")
    proof = PUBLIC_API_CONTRACT.get("solver_proof_claims") or {}
    if proof.get("contract_id") != SOLVER_PROOF_CONTRACT_ID or proof.get("contract_version") != SOLVER_PROOF_CONTRACT_VERSION:
        errors.append("solver proof contract identity mismatch")
    if proof.get("solver_status_is_proof_grade") is not False:
        errors.append("solver status must not equal proof grade")
    if proof.get("proof_certified_requires_independent_checker") is not True:
        errors.append("proof certification independence requirement missing")
    if proof.get("certificate_authority") != "EVIDENCE_ONLY":
        errors.append("proof certificate authority boundary mismatch")
    if proof.get("truth_authority") != "EXISTING_AASM_POLICY_ONLY":
        errors.append("proof certificate truth boundary mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
