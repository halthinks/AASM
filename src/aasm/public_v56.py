from __future__ import annotations

from copy import deepcopy

from . import public_v55 as _v55

for _name in dir(_v55):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v55, _name)

from ._runtime_v56_solver_outcome import (
    SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID,
    SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION,
    SOLVER_OUTCOME_V2_RUNTIME_STABILITY,
    solver_outcome_v2_runtime_contract,
)
from .provider_status_v2 import (
    PROVIDER_STATUS_MAP_CONTRACT_ID,
    PROVIDER_STATUS_MAP_CONTRACT_VERSION,
    ProviderStatusMap,
    ProviderStatusMapping,
    ProviderStatusRule,
    default_provider_status_map,
    highs_status_map,
    map_provider_status,
    map_provider_termination,
    ortools_cp_sat_status_map,
    provider_status_map_contract,
    pysat_cadical_status_map,
)
from .runtime_v56 import AASMEngine
from .solver_outcome_v2 import (
    SOLVER_EVIDENCE_GRADE_CONTRACT_ID,
    SOLVER_LEGACY_PROJECTION_CONTRACT_ID,
    SOLVER_OUTCOME_V2_CONTRACT_ID,
    SOLVER_OUTCOME_V2_CONTRACT_VERSION,
    SOLVER_STATUS_V2_CONTRACT_ID,
    SOLVER_STATUS_V2_CONTRACT_VERSION,
    SOLVER_TERMINATION_V2_CONTRACT_ID,
    INCUMBENT_VALIDATION_STATUSES,
    NORMALIZED_STATUSES,
    LegacyStatusProjection,
    ProviderTermination,
    SolverEvidenceGrade,
    SolverOutcomeV2,
    legacy_termination,
    normalize_optimization_result_v2,
    project_v2_to_legacy_status,
    solver_outcome_v2_contract,
)


__version__ = "0.56.0"
PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"
REMOTE_PROTOCOL_NAME = _v55.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v55.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "solver_outcome_v2_runtime_contract_report",
    "record_solver_outcome_v2",
    "solver_outcome_v2_report",
]

_NEW_IMPORTS = [
    "SOLVER_OUTCOME_V2_CONTRACT_ID", "SOLVER_OUTCOME_V2_CONTRACT_VERSION",
    "SOLVER_STATUS_V2_CONTRACT_ID", "SOLVER_STATUS_V2_CONTRACT_VERSION",
    "SOLVER_TERMINATION_V2_CONTRACT_ID", "SOLVER_EVIDENCE_GRADE_CONTRACT_ID",
    "SOLVER_LEGACY_PROJECTION_CONTRACT_ID", "NORMALIZED_STATUSES", "INCUMBENT_VALIDATION_STATUSES",
    "ProviderTermination", "SolverEvidenceGrade", "LegacyStatusProjection", "SolverOutcomeV2",
    "legacy_termination", "project_v2_to_legacy_status", "normalize_optimization_result_v2",
    "solver_outcome_v2_contract", "PROVIDER_STATUS_MAP_CONTRACT_ID", "PROVIDER_STATUS_MAP_CONTRACT_VERSION",
    "ProviderStatusRule", "ProviderStatusMap", "ProviderStatusMapping", "map_provider_status",
    "map_provider_termination", "ortools_cp_sat_status_map", "highs_status_map",
    "pysat_cadical_status_map", "default_provider_status_map", "provider_status_map_contract",
    "SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_ID", "SOLVER_OUTCOME_V2_RUNTIME_CONTRACT_VERSION",
    "SOLVER_OUTCOME_V2_RUNTIME_STABILITY", "solver_outcome_v2_runtime_contract",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v55, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(getattr(_v55, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([*getattr(_v55, "SUPPORTED_INSPECTION_SURFACES", []), "solver-outcome-v2"]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v55, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v55.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.32.0",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["solver_outcome_v2"] = {
    **solver_outcome_v2_contract(),
    "provider_status_map": provider_status_map_contract(),
    "runtime": solver_outcome_v2_runtime_contract(),
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v55.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.55: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.56 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.56 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("v0.56 runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.0":
        errors.append("v0.56 adoption contract mismatch")
    if PUBLIC_RELEASE_STABILITY != "ACTIVE_DEVELOPMENT":
        errors.append("v0.56 active release stability mismatch")
    outcome = PUBLIC_API_CONTRACT.get("solver_outcome_v2", {})
    if outcome.get("authoritative_detailed_status") != "normalized_status":
        errors.append("solver outcome v2 authoritative status boundary mismatch")
    if outcome.get("legacy_projection") != "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED":
        errors.append("solver outcome v2 legacy compatibility projection mismatch")
    if outcome.get("provider_status_map", {}).get("substring_inference") != "FORBIDDEN":
        errors.append("provider status mapping substring-inference boundary mismatch")
    if outcome.get("runtime", {}).get("parallel_result_table") != "NONE":
        errors.append("solver outcome runtime parallel-result boundary mismatch")
    if outcome.get("truth_authority") != "NONE":
        errors.append("solver outcome v2 authority boundary mismatch")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}


from . import demo_stack as _demo_stack
_demo_stack.AASMEngine = AASMEngine
_demo_stack._runtime_version = lambda: __version__
