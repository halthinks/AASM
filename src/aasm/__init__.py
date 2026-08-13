from copy import deepcopy as _deepcopy

from . import _public_v31 as _v31
from ._public_v31 import *  # noqa: F401,F403 - preserve v0.31 public surface
from .runtime_v32 import AASMEngine, default_profile_registry
from .trace_conformance import (
    TRACE_CONTRACT_ID,
    TRACE_CONTRACT_VERSION,
    SEMANTIC_TRACE_CONTRACT_ID,
    SEMANTIC_TRACE_CONTRACT_VERSION,
    TraceIssue,
    trace_contract,
    project_trace,
    semantic_trace_check,
    build_trace_corpus,
)

__version__ = "0.32.0"
REMOTE_PROTOCOL_NAME = "aasm.remote.v1"
REMOTE_PROTOCOL_VERSION = "0.19.0"

from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__

_TRACE_IMPORTS = [
    "TRACE_CONTRACT_ID", "TRACE_CONTRACT_VERSION", "SEMANTIC_TRACE_CONTRACT_ID",
    "SEMANTIC_TRACE_CONTRACT_VERSION", "TraceIssue", "trace_contract", "project_trace",
    "semantic_trace_check", "build_trace_corpus",
]
_TRACE_METHODS = ["trace_projection", "semantic_trace_report"]
_TRACE_COMMANDS = ["trace-project", "trace-check"]
_TRACE_SURFACES = ["trace", "trace-semantic"]

SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*_v31.SUPPORTED_PUBLIC_IMPORTS, *_TRACE_IMPORTS]))
SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*_v31.SUPPORTED_ENGINE_METHODS, *_TRACE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([*_v31.SUPPORTED_CLI_COMMANDS, *_TRACE_COMMANDS]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([*_v31.SUPPORTED_INSPECTION_SURFACES, *_TRACE_SURFACES]))

PUBLIC_API_CONTRACT = _deepcopy(_v31.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.8.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["trace_conformance"] = {
    "contract_id": TRACE_CONTRACT_ID,
    "contract_version": TRACE_CONTRACT_VERSION,
    "semantic_contract_id": SEMANTIC_TRACE_CONTRACT_ID,
    "semantic_contract_version": SEMANTIC_TRACE_CONTRACT_VERSION,
    "source": "AUTHORITATIVE_DURABLE_EVENT_HISTORY",
    "unknown_transition_policy": "UNSUPPORTED_EXPLICIT",
    "snapshot_only_input": "REJECTED",
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["golden_path"] = list(dict.fromkeys([
    *PUBLIC_API_CONTRACT.get("golden_path", []),
    "project production durable events into a lossless versioned formal trace before conformance claims",
]))


def public_api_contract() -> dict:
    return _deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    baseline = _v31.validate_public_api_contract()
    errors = list(baseline.get("errors") or [])
    missing_imports = [name for name in _TRACE_IMPORTS if name not in globals()]
    missing_methods = [name for name in _TRACE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing trace imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing trace engine methods: {missing_methods}")
    trace = PUBLIC_API_CONTRACT.get("trace_conformance") or {}
    if trace.get("contract_id") != TRACE_CONTRACT_ID or trace.get("contract_version") != TRACE_CONTRACT_VERSION:
        errors.append("trace contract identity does not match package constants")
    if trace.get("semantic_contract_id") != SEMANTIC_TRACE_CONTRACT_ID:
        errors.append("semantic trace contract identity does not match package constants")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("public API contract runtime_version does not match __version__")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


__all__ = list(dict.fromkeys(["__version__", *getattr(_v31, "__all__", []), *_TRACE_IMPORTS]))
