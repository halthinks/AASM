from copy import deepcopy
from . import public_v42 as _v42

for _name in dir(_v42):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v42, _name)

from .certification import (
    CERTIFICATION_CONTRACT_ID,
    CERTIFICATION_CONTRACT_VERSION,
    CERTIFICATION_STATUSES,
    CERTIFICATION_TARGET_IDS,
    CertificationCheck,
    CertificationReport,
    certification_contract,
    run_certification,
)
from .sii import (
    SII_CONTRACT_ID,
    SII_CONTRACT_VERSION,
    SII_STABILITY,
    ArtifactProposal,
    ResourceLease,
    StructuredProposal,
    SymbioticIntelligenceInterface,
    create_sii,
    sii_contract,
)
from .runtime_v41 import AASMEngine

__version__ = "0.43.0"
REMOTE_PROTOCOL_NAME = _v42.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v42.REMOTE_PROTOCOL_VERSION

SUPPORTED_ENGINE_METHODS = list(getattr(_v42, "SUPPORTED_ENGINE_METHODS", []))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v42, "SUPPORTED_CLI_COMMANDS", []),
    "certification-contract",
    "certify",
    "sii-contract",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v42, "SUPPORTED_INSPECTION_SURFACES", []),
    "certification",
    "sii-preview-contract",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([
    *getattr(_v42, "SUPPORTED_PUBLIC_IMPORTS", []),
    "CERTIFICATION_STATUSES",
    "CERTIFICATION_TARGET_IDS",
    "CertificationCheck",
    "CertificationReport",
    "certification_contract",
    "run_certification",
    "ArtifactProposal",
    "ResourceLease",
    "StructuredProposal",
    "SymbioticIntelligenceInterface",
    "create_sii",
    "sii_contract",
]))

PUBLIC_API_CONTRACT = deepcopy(_v42.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.19.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["certification"] = certification_contract()
PUBLIC_API_CONTRACT["sii_preview"] = sii_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v42.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.42: {error}" for error in parent["errors"])

    current_imports = [
        "CERTIFICATION_STATUSES",
        "CERTIFICATION_TARGET_IDS",
        "CertificationCheck",
        "CertificationReport",
        "certification_contract",
        "run_certification",
        "ArtifactProposal",
        "ResourceLease",
        "StructuredProposal",
        "SymbioticIntelligenceInterface",
        "create_sii",
        "sii_contract",
    ]
    missing_imports = [name for name in current_imports if name not in globals()]
    if missing_imports:
        errors.append(f"missing current imports: {missing_imports}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.19.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")

    certification = PUBLIC_API_CONTRACT.get("certification") or {}
    if certification.get("contract_id") != CERTIFICATION_CONTRACT_ID:
        errors.append("certification contract mismatch")
    if certification.get("contract_version") != CERTIFICATION_CONTRACT_VERSION:
        errors.append("certification contract version mismatch")
    if certification.get("statuses") != list(CERTIFICATION_STATUSES):
        errors.append("certification status contract mismatch")
    if certification.get("authority") != "CERTIFICATION_HARNESS_ONLY":
        errors.append("certification authority mismatch")
    if certification.get("kernel_changes") != "NONE":
        errors.append("certification kernel boundary mismatch")

    sii = PUBLIC_API_CONTRACT.get("sii_preview") or {}
    if sii.get("contract_id") != SII_CONTRACT_ID:
        errors.append("SII contract mismatch")
    if sii.get("contract_version") != SII_CONTRACT_VERSION:
        errors.append("SII contract version mismatch")
    if sii.get("stability") != SII_STABILITY:
        errors.append("SII stability mismatch")
    if sii.get("authority_reward") != "NEVER":
        errors.append("SII authority boundary mismatch")
    if sii.get("kernel_runtime") != "V0.41_ENGINE_UNCHANGED":
        errors.append("SII kernel boundary mismatch")

    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
