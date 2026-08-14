from copy import deepcopy
from . import public_v41 as _v41

for _name in dir(_v41):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v41, _name)

from .reference_domains import (
    REFERENCE_DOMAIN_CONTRACT_ID,
    REFERENCE_DOMAIN_CONTRACT_VERSION,
    REFERENCE_DOMAIN_IDS,
    ReferenceDomainResult,
    reference_domain_contract,
    run_reference_domain_stress,
)
from .runtime_v41 import AASMEngine

__version__ = "0.42.0"
REMOTE_PROTOCOL_NAME = _v41.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v41.REMOTE_PROTOCOL_VERSION

SUPPORTED_ENGINE_METHODS = list(getattr(_v41, "SUPPORTED_ENGINE_METHODS", []))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v41, "SUPPORTED_CLI_COMMANDS", []),
    "reference-domain-contract",
    "reference-domain-stress",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v41, "SUPPORTED_INSPECTION_SURFACES", []),
    "reference-domain-stress",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([
    *getattr(_v41, "SUPPORTED_PUBLIC_IMPORTS", []),
    "REFERENCE_DOMAIN_IDS",
    "ReferenceDomainResult",
    "reference_domain_contract",
    "run_reference_domain_stress",
]))

PUBLIC_API_CONTRACT = deepcopy(_v41.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.18.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["reference_domains"] = reference_domain_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v41.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.41: {error}" for error in parent["errors"])
    current_imports = [
        "REFERENCE_DOMAIN_IDS",
        "ReferenceDomainResult",
        "reference_domain_contract",
        "run_reference_domain_stress",
    ]
    missing_imports = [name for name in current_imports if name not in globals()]
    if missing_imports:
        errors.append(f"missing current imports: {missing_imports}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.18.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    reference = PUBLIC_API_CONTRACT.get("reference_domains") or {}
    if reference.get("contract_id") != REFERENCE_DOMAIN_CONTRACT_ID:
        errors.append("reference-domain contract mismatch")
    if reference.get("contract_version") != REFERENCE_DOMAIN_CONTRACT_VERSION:
        errors.append("reference-domain contract version mismatch")
    if reference.get("authority") != "REFERENCE_HARNESS_ONLY":
        errors.append("reference-domain authority mismatch")
    if reference.get("kernel_changes") != "NONE":
        errors.append("reference-domain kernel boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
