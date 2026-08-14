from copy import deepcopy
from . import public_v47 as _v47

for _name in dir(_v47):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v47, _name)

from .cross_run_knowledge import (
    CROSS_RUN_KNOWLEDGE_CONTRACT_ID,
    CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION,
    CROSS_RUN_ADMISSION_CONTRACT_ID,
    CROSS_RUN_ADMISSION_CONTRACT_VERSION,
    CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID,
    CROSS_RUN_PRINCIPAL_MAP_CONTRACT_VERSION,
    CrossRunKnowledgeEnvelope,
    CrossRunKnowledgeSignal,
    CrossRunKnowledgeBundle,
    CrossRunAdmissionContext,
    CrossRunAdmissionCertificate,
    CrossRunPrincipalMap,
    validate_cross_run_envelope,
    cross_run_knowledge_contract,
)
from .cross_run_conformance import run_cross_run_knowledge_conformance
from .runtime_v48 import AASMEngine

__version__ = "0.48.0"
REMOTE_PROTOCOL_NAME = _v47.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v47.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "cross_run_knowledge_contract_report",
    "export_cross_run_knowledge",
    "export_cross_run_delta",
    "make_cross_run_signal",
    "inspect_cross_run_envelope",
    "propose_cross_run_admission",
    "authorize_cross_run_admission",
    "commit_cross_run_admission",
    "cross_run_knowledge_report",
    "apply_cross_run_signal",
    "materialize_cross_run_knowledge",
    "register_cross_run_reuse_candidate",
    "map_cross_run_principal",
    "admit_cross_run_sii_reputation",
]
_NEW_IMPORTS = [
    "CROSS_RUN_KNOWLEDGE_CONTRACT_ID",
    "CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION",
    "CROSS_RUN_ADMISSION_CONTRACT_ID",
    "CROSS_RUN_ADMISSION_CONTRACT_VERSION",
    "CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID",
    "CROSS_RUN_PRINCIPAL_MAP_CONTRACT_VERSION",
    "CrossRunKnowledgeEnvelope",
    "CrossRunKnowledgeSignal",
    "CrossRunKnowledgeBundle",
    "CrossRunAdmissionContext",
    "CrossRunAdmissionCertificate",
    "CrossRunPrincipalMap",
    "validate_cross_run_envelope",
    "cross_run_knowledge_contract",
    "run_cross_run_knowledge_conformance",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v47, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([*getattr(_v47, "SUPPORTED_CLI_COMMANDS", []), "cross-run-knowledge-contract", "cross-run-knowledge-conformance"]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([*getattr(_v47, "SUPPORTED_INSPECTION_SURFACES", []), "cross-run-knowledge", "cross-run-principal-maps", "cross-run-sii-reputation"]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v47, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v47.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.24.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["cross_run_knowledge"] = cross_run_knowledge_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v47.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.47: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.48 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.48 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.24.0":
        errors.append("adoption contract mismatch")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    cross = PUBLIC_API_CONTRACT.get("cross_run_knowledge") or {}
    if cross.get("contract_id") != CROSS_RUN_KNOWLEDGE_CONTRACT_ID or cross.get("contract_version") != CROSS_RUN_KNOWLEDGE_CONTRACT_VERSION:
        errors.append("cross-run knowledge contract identity mismatch")
    if cross.get("admission_contract_id") != CROSS_RUN_ADMISSION_CONTRACT_ID or cross.get("admission_contract_version") != CROSS_RUN_ADMISSION_CONTRACT_VERSION:
        errors.append("cross-run admission contract identity mismatch")
    if cross.get("principal_map_contract_id") != CROSS_RUN_PRINCIPAL_MAP_CONTRACT_ID or cross.get("principal_map_contract_version") != CROSS_RUN_PRINCIPAL_MAP_CONTRACT_VERSION:
        errors.append("cross-run principal map contract identity mismatch")
    if cross.get("source_authority") != "PROVENANCE_ONLY_NEVER_INHERITED":
        errors.append("cross-run authority inheritance boundary mismatch")
    if cross.get("semantic_materialization") != "LOCAL_AUTHORIZED_REASONING_REQUIRED":
        errors.append("cross-run semantic admission boundary mismatch")
    if cross.get("reuse") != "EXISTING_V41_REUSE_CERTIFICATE_REQUIRED":
        errors.append("cross-run reuse boundary mismatch")
    if cross.get("sii_reputation") != "ACCOUNTING_ONLY_NEVER_AUTHORITY_OR_RESOURCE_ENTITLEMENT":
        errors.append("cross-run SII reputation boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
