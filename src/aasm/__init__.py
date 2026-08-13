from __future__ import annotations

from copy import deepcopy as _deepcopy

from . import _public_v39 as _v39

# Preserve the entire released v0.39 public module surface verbatim, then layer
# v0.40 memory/context contracts on top. This avoids rewriting or shadowing any
# earlier public symbol while letting the current runtime advance independently.
for _name in dir(_v39):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v39, _name)

from .runtime_v40 import AASMEngine, default_profile_registry
from .hierarchical_memory import (
    HIERARCHICAL_MEMORY_CONTRACT_ID, HIERARCHICAL_MEMORY_CONTRACT_VERSION,
    MEMORY_INDEX_CONTRACT_ID, MEMORY_INDEX_CONTRACT_VERSION,
    REASONING_FRONTIER_CONTRACT_ID, REASONING_FRONTIER_CONTRACT_VERSION,
    CONTEXT_PROJECTION_CONTRACT_ID, CONTEXT_PROJECTION_CONTRACT_VERSION,
    MEMORY_KINDS, MEMORY_SUBSTRATES, MEMORY_OPERATIONS, MEMORY_PRIVACY_LEVELS,
    MEMORY_INDEX_KINDS, MemoryObject, MemoryTombstone, MemoryIndexEntry,
    ContextProjectionRequest, hierarchical_memory_contract, memory_document,
    project_memory_evidence, select_memory_context, project_reasoning_frontier,
    project_context,
)
from .memory_operations import MemoryOperationDecision, MemoryOperationObligation
from .memory_conformance import run_hierarchical_memory_conformance

__version__ = "0.40.0"
REMOTE_PROTOCOL_NAME = _v39.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v39.REMOTE_PROTOCOL_VERSION

from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__

_MEMORY_IMPORTS = [
    "HIERARCHICAL_MEMORY_CONTRACT_ID", "HIERARCHICAL_MEMORY_CONTRACT_VERSION",
    "MEMORY_INDEX_CONTRACT_ID", "MEMORY_INDEX_CONTRACT_VERSION",
    "REASONING_FRONTIER_CONTRACT_ID", "REASONING_FRONTIER_CONTRACT_VERSION",
    "CONTEXT_PROJECTION_CONTRACT_ID", "CONTEXT_PROJECTION_CONTRACT_VERSION",
    "MEMORY_KINDS", "MEMORY_SUBSTRATES", "MEMORY_OPERATIONS", "MEMORY_PRIVACY_LEVELS",
    "MEMORY_INDEX_KINDS", "MemoryObject", "MemoryTombstone", "MemoryIndexEntry",
    "ContextProjectionRequest", "hierarchical_memory_contract", "memory_document",
    "project_memory_evidence", "select_memory_context", "project_reasoning_frontier",
    "project_context", "MemoryOperationDecision", "MemoryOperationObligation",
    "run_hierarchical_memory_conformance",
]
_MEMORY_METHODS = [
    "hierarchical_memory_contract_report", "hierarchical_memory_report",
    "propose_memory_operation", "propose_memory_forget", "authorize_memory_operation",
    "commit_memory_operation", "admit_memory_index", "reasoning_frontier",
    "context_projection", "record_context_projection",
]
_MEMORY_COMMANDS = [
    "hierarchical-memory-contract", "hierarchical-memory-conformance", "memory-report",
    "memory-propose", "memory-authorize", "memory-commit", "memory-forget",
    "memory-index-add", "reasoning-frontier", "context-project", "context-record",
]
_MEMORY_SURFACES = [
    "hierarchical-memory", "memory-hierarchy", "reasoning-frontier", "context-projection",
    "hierarchical-memory-contract", "context-projection-contract",
]

SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v39, "SUPPORTED_PUBLIC_IMPORTS", []), *_MEMORY_IMPORTS]))
SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v39, "SUPPORTED_ENGINE_METHODS", []), *_MEMORY_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([*getattr(_v39, "SUPPORTED_CLI_COMMANDS", []), *_MEMORY_COMMANDS]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([*getattr(_v39, "SUPPORTED_INSPECTION_SURFACES", []), *_MEMORY_SURFACES]))

PUBLIC_API_CONTRACT = _deepcopy(_v39.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.16.0",
    "runtime_version": __version__,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["hierarchical_memory"] = hierarchical_memory_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["golden_path"] = list(dict.fromkeys([
    *PUBLIC_API_CONTRACT.get("golden_path", []),
    "propose memory changes as decisions, authorize them into obligations, and commit only the exact approved memory object as Evidence",
    "project context through scope, principal privacy, semantic validity, deterministic relevance, and hard item/character budgets",
    "keep embeddings and other retrieval indexes derived from canonical memory identity rather than part of machine truth",
]))


def public_api_contract() -> dict:
    return _deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    inherited = _v39.validate_public_api_contract()
    errors = list(inherited.get("errors", []))
    missing_imports = [name for name in _MEMORY_IMPORTS if name not in globals()]
    missing_methods = [name for name in _MEMORY_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.40 public imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.40 AASMEngine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("v0.40 runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.16.0":
        errors.append("v0.40 adoption contract version mismatch")
    memory = PUBLIC_API_CONTRACT.get("hierarchical_memory") or {}
    if memory.get("contract_id") != HIERARCHICAL_MEMORY_CONTRACT_ID:
        errors.append("hierarchical memory contract mismatch")
    if memory.get("mutation_path") != "DECISION_TO_OBLIGATION_TO_EVIDENCE":
        errors.append("hierarchical memory authority path mismatch")
    if memory.get("semantic_memory_truth") != "REFERENCES_V37_ADMITTED_REASONING":
        errors.append("semantic memory truth boundary mismatch")
    if memory.get("embeddings") != "DERIVED_INDEX_ONLY":
        errors.append("memory index identity boundary mismatch")
    if memory.get("forgetting") != "TOMBSTONE_NOT_HISTORY_DELETION":
        errors.append("memory forgetting provenance boundary mismatch")
    if memory.get("stale_default") != "EXCLUDED":
        errors.append("stale memory context boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


__all__ = list(dict.fromkeys(["__version__", *getattr(_v39, "__all__", []), *_MEMORY_IMPORTS]))
