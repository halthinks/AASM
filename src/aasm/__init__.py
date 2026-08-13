from copy import deepcopy as _deepcopy

from . import _public_v30 as _v30
from ._public_v30 import *  # noqa: F401,F403 - preserve the v0.30 public surface
from .runtime_v31 import AASMEngine, default_profile_registry
from .scopes import (
    SCOPE_CONTRACT_ID,
    SCOPE_CONTRACT_VERSION,
    ROOT_SCOPE_ID,
    DecisionScope,
    ScopeDependency,
    default_scope_state,
    normalize_scope_state,
    effective_scope_decisions,
    effective_scope_values,
    build_scope_report,
)

__version__ = "0.31.0"
REMOTE_PROTOCOL_NAME = "aasm.remote.v1"
REMOTE_PROTOCOL_VERSION = "0.19.0"

# Any v0.30 helper that captures the public engine is rebound to the current
# implementation. This does not create a second runtime; it preserves the
# existing helper path while replacing only the versioned engine class.
from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__

_SCOPE_IMPORTS = [
    "SCOPE_CONTRACT_ID",
    "SCOPE_CONTRACT_VERSION",
    "ROOT_SCOPE_ID",
    "DecisionScope",
    "ScopeDependency",
    "default_scope_state",
    "normalize_scope_state",
    "effective_scope_decisions",
    "effective_scope_values",
    "build_scope_report",
]
_SCOPE_METHODS = [
    "register_scope",
    "register_scope_dependency",
    "scope_report",
    "effective_scope_context",
    "restart_scope",
    "migrate_legacy_scopes",
]
_SCOPE_COMMANDS = [
    "scope-register",
    "scope-dependency",
    "scope-report",
    "scope-context",
    "scope-restart",
    "scope-migrate",
]
_SCOPE_SURFACES = ["scopes", "scope-hierarchy"]

SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*_v30.SUPPORTED_PUBLIC_IMPORTS, *_SCOPE_IMPORTS]))
SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*_v30.SUPPORTED_ENGINE_METHODS, *_SCOPE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([*_v30.SUPPORTED_CLI_COMMANDS, *_SCOPE_COMMANDS]))
SUPPORTED_INSPECTION_SURFACES = list(
    dict.fromkeys([*_v30.SUPPORTED_INSPECTION_SURFACES, *_SCOPE_SURFACES])
)

PUBLIC_API_CONTRACT = _deepcopy(_v30.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update(
    {
        "contract_version": "0.7.0",
        "runtime_version": __version__,
        "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
        "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
        "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
        "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
    }
)
PUBLIC_API_CONTRACT["supported_http_endpoints"] = list(
    dict.fromkeys(
        [
            *PUBLIC_API_CONTRACT.get("supported_http_endpoints", []),
            "/v1/machines/{machine_id}/scopes",
        ]
    )
)
PUBLIC_API_CONTRACT["scopes"] = {
    "contract_id": SCOPE_CONTRACT_ID,
    "contract_version": SCOPE_CONTRACT_VERSION,
    "support": "EXPERIMENTAL",
    "root_scope_id": ROOT_SCOPE_ID,
    "entry_points": [
        "AASMEngine.register_scope(...) ",
        "AASMEngine.register_scope_dependency(...) ",
        "AASMEngine.scope_report()",
        "aasm scope-report MACHINE_ID",
        "GET /v1/machines/{machine_id}/scopes",
    ],
    "authority": "ONE_AASM_MACHINE_ONE_EVENT_HISTORY",
    "non_goals": [
        "one machine per scope",
        "parallel scope event stores",
        "framework-private scope truth",
        "implicit sibling information flow",
    ],
}
PUBLIC_API_CONTRACT["distribution"].update({
    "version": __version__,
    "reproducible_builds": True,
    "source_distribution_self_test": True,
    "source_distribution_scope": "FULL_REPOSITORY_CONTRACT",
    "historical_release_policy": "REPORT_ONLY",
})
PUBLIC_API_CONTRACT["golden_path"] = list(
    dict.fromkeys(
        [
            *PUBLIC_API_CONTRACT.get("golden_path", []),
            "separate strategy, architecture, implementation, and workstreams inside one authoritative machine",
        ]
    )
)


def public_api_contract() -> dict:
    """Return the machine-readable canonical adoption surface."""

    return _deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    """Verify every supported import, engine method, and contract identity."""

    errors: list[str] = []
    missing_imports = [name for name in SUPPORTED_PUBLIC_IMPORTS if name not in globals()]
    missing_methods = [
        name
        for name in SUPPORTED_ENGINE_METHODS
        if not callable(getattr(AASMEngine, name, None))
    ]
    if missing_imports:
        errors.append(f"missing supported imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing supported AASMEngine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("public API contract runtime_version does not match __version__")
    if PUBLIC_API_CONTRACT.get("remote_protocol") != {
        "name": REMOTE_PROTOCOL_NAME,
        "version": REMOTE_PROTOCOL_VERSION,
    }:
        errors.append("public API contract remote protocol does not match package constants")
    if sorted(PUBLIC_API_CONTRACT.get("operator_runbooks") or []) != sorted(
        RUNBOOK_DEFINITIONS
    ):
        errors.append("public API contract operator runbooks do not match the registry")
    conformance = (PUBLIC_API_CONTRACT.get("integrations") or {}).get("conformance") or {}
    if conformance.get("contract_id") != ADAPTER_CONFORMANCE_ID:
        errors.append("public API contract conformance identity does not match package constants")
    if conformance.get("required_scenarios") != list(CONFORMANCE_SCENARIOS):
        errors.append("public API contract conformance scenarios do not match the kit")
    if not list_conformance_drivers():
        errors.append("no built-in adapter conformance drivers are registered")
    scopes = PUBLIC_API_CONTRACT.get("scopes") or {}
    if scopes.get("contract_id") != SCOPE_CONTRACT_ID:
        errors.append("public API contract scope identity does not match package constants")
    if scopes.get("contract_version") != SCOPE_CONTRACT_VERSION:
        errors.append("public API contract scope version does not match package constants")
    corpus = verify_research_corpus()
    if not corpus["valid"]:
        errors.append("packaged research reference corpus failed verification")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


__all__ = list(
    dict.fromkeys(
        ["__version__", *getattr(_v30, "__all__", []), *_SCOPE_IMPORTS]
    )
)
