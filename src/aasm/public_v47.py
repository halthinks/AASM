from copy import deepcopy
from . import public_v46 as _v46

for _name in dir(_v46):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v46, _name)

from .certification_v47 import (
    CERTIFICATION_CONTRACT_ID,
    CERTIFICATION_CONTRACT_VERSION,
    CERTIFICATION_STATUSES,
    CERTIFICATION_TARGET_IDS,
    CERTIFICATION_TARGET_ALIASES,
    CertificationCheck,
    CertificationReport,
    certification_contract,
    run_certification,
)
from .sii_governance import (
    SII_GOVERNED_CONTRACT_ID,
    SII_GOVERNED_CONTRACT_VERSION,
    SII_GOVERNED_STABILITY,
    SIIPrincipalBinding,
    SIIResourceBudget,
    SIITierRule,
    SIIScoringPolicy,
    GovernedResourceLease,
    GovernedSymbioticFeedback,
    GovernedSymbioticIntelligenceInterface,
    default_sii_scoring_policy,
    governed_sii_contract,
    enforce_advanced_problem_budget,
    create_governed_sii,
)
from .runtime_v47 import AASMEngine

__version__ = "0.47.0"
REMOTE_PROTOCOL_NAME = _v46.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v46.REMOTE_PROTOCOL_VERSION

# Current SII contract aliases. The v0.43 preview types/create_sii remain
# available for compatibility, while v0.47's governed interface is canonical.
SII_CONTRACT_ID = SII_GOVERNED_CONTRACT_ID
SII_CONTRACT_VERSION = SII_GOVERNED_CONTRACT_VERSION
SII_STABILITY = SII_GOVERNED_STABILITY
sii_contract = governed_sii_contract

_NEW_ENGINE_METHODS = [
    "sii_governed_contract_report",
    "sii_governance_report",
    "bind_sii_principal",
    "admit_sii_scoring_policy",
    "activate_sii_scoring_policy",
    "install_default_sii_scoring_policy",
    "register_sii_proposer",
    "submit_sii_proposal",
    "measure_sii_outcome",
    "sii_performance",
    "sii_resource_lease",
    "sii_context",
    "request_sii_advanced_optimization",
    "request_sii_formal_verification",
]
_NEW_IMPORTS = [
    "CERTIFICATION_TARGET_ALIASES",
    "SIIPrincipalBinding",
    "SIIResourceBudget",
    "SIITierRule",
    "SIIScoringPolicy",
    "GovernedResourceLease",
    "GovernedSymbioticFeedback",
    "GovernedSymbioticIntelligenceInterface",
    "default_sii_scoring_policy",
    "governed_sii_contract",
    "enforce_advanced_problem_budget",
    "create_governed_sii",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v46, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v46, "SUPPORTED_CLI_COMMANDS", []),
    "sii-governance-contract",
    "sii-default-scoring-policy",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v46, "SUPPORTED_INSPECTION_SURFACES", []),
    "sii-governance",
    "sii-resource-leases",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v46, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v46.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.23.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["certification"] = certification_contract()
PUBLIC_API_CONTRACT["sii_governance"] = governed_sii_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v46.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.46: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing current imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.47 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.23.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    cert = PUBLIC_API_CONTRACT.get("certification") or {}
    if cert.get("contract_id") != CERTIFICATION_CONTRACT_ID or cert.get("contract_version") != CERTIFICATION_CONTRACT_VERSION:
        errors.append("v0.47 certification contract mismatch")
    if cert.get("sii_graduation") != "GOVERNED_V047_ENFORCEMENT_REQUIRED":
        errors.append("v0.47 SII certification graduation mismatch")
    sii = PUBLIC_API_CONTRACT.get("sii_governance") or {}
    if sii.get("contract_id") != SII_GOVERNED_CONTRACT_ID or sii.get("contract_version") != SII_GOVERNED_CONTRACT_VERSION:
        errors.append("governed SII contract identity mismatch")
    if sii.get("stability") != "GOVERNED_ENFORCED":
        errors.append("governed SII stability mismatch")
    if sii.get("measurement_identity_binding") != "RESOLVED_FROM_DURABLE_PRINCIPAL_BINDING":
        errors.append("SII measurement authority binding mismatch")
    if sii.get("resource_enforcement") != "EXISTING_CONTEXT_CAPABILITY_SCHEDULER_TASKLEASE_NATIVE_SOLVER_PATHS":
        errors.append("SII resource enforcement mismatch")
    if sii.get("mandatory_verification") != "NEVER_REDUCED_BY_SII":
        errors.append("SII mandatory verification boundary mismatch")
    if sii.get("authority_reward") != "NEVER":
        errors.append("SII authority reward boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
