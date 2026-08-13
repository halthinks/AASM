from copy import deepcopy as _deepcopy

from . import _public_v31 as _v31
from ._public_v31 import *  # noqa: F401,F403
from .runtime_v32 import AASMEngine, default_profile_registry
from .trace_conformance import (
    TRACE_CONTRACT_ID, TRACE_CONTRACT_VERSION, SEMANTIC_TRACE_CONTRACT_ID, SEMANTIC_TRACE_CONTRACT_VERSION,
    PROVENANCE_CONTRACT_ID, PROVENANCE_CONTRACT_VERSION, TraceIssue, trace_contract, project_trace,
    semantic_trace_check, build_trace_corpus, provenance_contract, export_provenance,
    verify_provenance_export, create_selective_provenance_export,
)

__version__ = "0.33.0"
REMOTE_PROTOCOL_NAME = "aasm.remote.v1"
REMOTE_PROTOCOL_VERSION = "0.19.0"

from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__

_NEW_IMPORTS = [
    "TRACE_CONTRACT_ID", "TRACE_CONTRACT_VERSION", "SEMANTIC_TRACE_CONTRACT_ID", "SEMANTIC_TRACE_CONTRACT_VERSION",
    "PROVENANCE_CONTRACT_ID", "PROVENANCE_CONTRACT_VERSION", "TraceIssue", "trace_contract", "project_trace",
    "semantic_trace_check", "build_trace_corpus", "provenance_contract", "export_provenance",
    "verify_provenance_export", "create_selective_provenance_export",
]
_NEW_METHODS = ["trace_projection", "semantic_trace_report", "provenance_export", "provenance_verify", "provenance_select"]
_NEW_COMMANDS = ["trace-project", "trace-check", "provenance-export", "provenance-verify", "provenance-select"]
_NEW_SURFACES = ["trace", "trace-semantic", "provenance"]

SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*_v31.SUPPORTED_PUBLIC_IMPORTS, *_NEW_IMPORTS]))
SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*_v31.SUPPORTED_ENGINE_METHODS, *_NEW_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([*_v31.SUPPORTED_CLI_COMMANDS, *_NEW_COMMANDS]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([*_v31.SUPPORTED_INSPECTION_SURFACES, *_NEW_SURFACES]))

PUBLIC_API_CONTRACT = _deepcopy(_v31.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({"contract_version": "0.9.0", "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS, "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS, "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES})
PUBLIC_API_CONTRACT["trace_conformance"] = {
    "contract_id": TRACE_CONTRACT_ID, "contract_version": TRACE_CONTRACT_VERSION,
    "semantic_contract_id": SEMANTIC_TRACE_CONTRACT_ID, "semantic_contract_version": SEMANTIC_TRACE_CONTRACT_VERSION,
    "source": "AUTHORITATIVE_DURABLE_EVENT_HISTORY", "unknown_transition_policy": "UNSUPPORTED_EXPLICIT",
    "snapshot_only_input": "REJECTED",
}
PUBLIC_API_CONTRACT["provenance"] = provenance_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["golden_path"] = list(dict.fromkeys([*PUBLIC_API_CONTRACT.get("golden_path", []),
    "export completed runs as content-addressed detached-signature packages and verify them offline"] ))


def public_api_contract() -> dict: return _deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    errors = []
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports: errors.append(f"missing public imports: {missing_imports}")
    if missing_methods: errors.append(f"missing AASMEngine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__: errors.append("runtime version mismatch")
    if (PUBLIC_API_CONTRACT.get("provenance") or {}).get("contract_id") != PROVENANCE_CONTRACT_ID: errors.append("provenance contract mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


__all__ = list(dict.fromkeys(["__version__", *getattr(_v31, "__all__", []), *_NEW_IMPORTS]))
