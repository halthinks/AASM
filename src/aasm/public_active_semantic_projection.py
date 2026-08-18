from __future__ import annotations

from copy import deepcopy

from . import public_active_engineering_rule as _base

# Preserve the complete qualified 0.32.17 public surface, then add only the
# independently qualified semantic projection/equivalence/invariant IR. This
# active overlay does not compose projection state into AASMEngine, create a
# registry, or grant truth, authority, proof, preference, artifact acceptance,
# entity identity, or reuse admission.
for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .semantic_projection import (
    SEMANTIC_PROJECTION_CONTRACT_ID,
    SEMANTIC_PROJECTION_CONTRACT_VERSION,
    SEMANTIC_EQUIVALENCE_CONTRACT_ID,
    SEMANTIC_EQUIVALENCE_CONTRACT_VERSION,
    INVARIANT_CONTRACT_ID,
    INVARIANT_CONTRACT_VERSION,
    SEMANTIC_PROJECTION_STABILITY,
    INVARIANT_CLASSIFICATIONS,
    INVARIANT_TREATMENTS,
    PROJECTION_FIDELITIES,
    PROJECTION_STATUSES,
    REVISION_POLICIES,
    EQUIVALENCE_RELATIONS,
    REVISION_RELATIONS,
    InvariantRef,
    SemanticSubjectRef,
    SemanticProjectionDefinition,
    SemanticProjectionResult,
    SemanticEquivalenceAssessment,
    assess_semantic_equivalence,
    invariant_contract,
    semantic_projection_contract,
)
from .semantic_projection import __all__ as _SEMANTIC_IMPORTS


__version__ = _base.__version__
PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY
REMOTE_PROTOCOL_NAME = _base.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _base.REMOTE_PROTOCOL_VERSION
AASMEngine = _base.AASMEngine

PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"
PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.17"
SEMANTIC_PROJECTION_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"

SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))
SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_PUBLIC_IMPORTS = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_SEMANTIC_IMPORTS])
)
SUPPORTED_INSPECTION_SURFACES = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_INSPECTION_SURFACES", []), "semantic-projection"])
)

PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update(
    {
        "contract_version": PUBLIC_ADOPTION_CONTRACT_VERSION,
        "parent_contract_version": PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION,
        "runtime_version": __version__,
        "release_stability": PUBLIC_RELEASE_STABILITY,
        "description": "0.32.18 active public boundary: Rule plus qualified semantic projection/equivalence/invariant IR; no projection runtime composition.",
        "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
        "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
        "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
        "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
    }
)

_semantic = deepcopy(semantic_projection_contract())
_semantic["public_admission"] = SEMANTIC_PROJECTION_PUBLIC_ADMISSION
_semantic["runtime_admission"] = "PRE_ADMISSION_ONLY"
_semantic["engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"
_semantic["active_root_status"] = "ACTIVE_QUALIFIED_PUBLIC_ROOT"
_semantic["invariant_contract"] = invariant_contract()
_semantic["public_claim_ceiling"] = {
    "truth_authority": "NONE",
    "fact_authority": "NONE",
    "effect_authority": "NONE",
    "artifact_acceptance": "NONE",
    "entity_identity_authority": "NONE",
    "proof_authority": "NONE",
    "objective_preference": "NONE",
    "reuse_admission": "NONE",
    "runtime_execution": "NONE",
}
PUBLIC_API_CONTRACT["semantic_projection"] = _semantic
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract() -> dict:
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract() -> dict:
    parent = _base.validate_public_api_contract()
    errors: list[str] = []
    if not parent.get("valid"):
        errors.append("qualified 0.32.17 Rule parent is invalid")

    if _base.PUBLIC_API_CONTRACT.get("contract_version") != PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("Rule parent public adoption drifted")
    if AASMEngine is not _base.AASMEngine:
        errors.append("semantic projection overlay forked AASMEngine")
    if PUBLIC_API_CONTRACT.get("contract_version") != PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("semantic projection public adoption version drift")
    if PUBLIC_API_CONTRACT.get("parent_contract_version") != PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION:
        errors.append("semantic projection parent adoption version drift")
    if PUBLIC_API_CONTRACT.get("supported_imports") != SUPPORTED_PUBLIC_IMPORTS:
        errors.append("semantic projection public import surface drift")
    if PUBLIC_API_CONTRACT.get("supported_engine_methods") != SUPPORTED_ENGINE_METHODS:
        errors.append("semantic projection engine method surface drift")
    if SUPPORTED_ENGINE_METHODS != list(getattr(_base, "SUPPORTED_ENGINE_METHODS", [])):
        errors.append("semantic projection overlay added engine methods")
    if "semantic-projection" not in SUPPORTED_INSPECTION_SURFACES:
        errors.append("semantic projection inspection surface missing")

    missing_imports = [name for name in _SEMANTIC_IMPORTS if name not in globals()]
    if missing_imports:
        errors.append(f"missing semantic projection public imports: {missing_imports}")

    semantic = PUBLIC_API_CONTRACT.get("semantic_projection") or {}
    required = {
        "contract_id": SEMANTIC_PROJECTION_CONTRACT_ID,
        "equivalence_contract_id": SEMANTIC_EQUIVALENCE_CONTRACT_ID,
        "invariant_contract_id": INVARIANT_CONTRACT_ID,
        "public_admission": SEMANTIC_PROJECTION_PUBLIC_ADMISSION,
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "engine_state_integration": "NONE_SEMANTIC_IR_ONLY",
        "active_root_status": "ACTIVE_QUALIFIED_PUBLIC_ROOT",
        "parallel_projection_registry": "NONE",
        "current_projection_pointer": "NONE",
    }
    for key, value in required.items():
        if semantic.get(key) != value:
            errors.append(f"semantic projection {key} drift")
    if any(value != "NONE" for value in (semantic.get("public_claim_ceiling") or {}).values()):
        errors.append("semantic projection public claim ceiling drift")

    return {
        "valid": not errors,
        "errors": errors,
        "contract": public_api_contract(),
        "contract_version": PUBLIC_ADOPTION_CONTRACT_VERSION,
        "parent_contract_version": PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION,
        "semantic_projection_contract_id": SEMANTIC_PROJECTION_CONTRACT_ID,
        "semantic_equivalence_contract_id": SEMANTIC_EQUIVALENCE_CONTRACT_ID,
        "invariant_contract_id": INVARIANT_CONTRACT_ID,
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "active_root_status": "ACTIVE_QUALIFIED_PUBLIC_ROOT",
    }


__all__ = tuple(
    dict.fromkeys(
        [
            *SUPPORTED_PUBLIC_IMPORTS,
            "AASMEngine",
            "PUBLIC_API_CONTRACT",
            "PUBLIC_ADOPTION_CONTRACT_VERSION",
            "PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION",
            "SEMANTIC_PROJECTION_PUBLIC_ADMISSION",
            "PUBLIC_RELEASE_STABILITY",
            "REMOTE_PROTOCOL_NAME",
            "REMOTE_PROTOCOL_VERSION",
            "SUPPORTED_PUBLIC_IMPORTS",
            "SUPPORTED_ENGINE_METHODS",
            "SUPPORTED_CLI_COMMANDS",
            "SUPPORTED_INSPECTION_SURFACES",
            "public_api_contract",
            "validate_public_api_contract",
            "__version__",
        ]
    )
)
