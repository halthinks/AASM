from __future__ import annotations

from copy import deepcopy

from .public_active_engineering_rule import (
    AASMEngine,
    PUBLIC_ADOPTION_STABILITY,
    PUBLIC_ADOPTION_SUPPORT as _PARENT_SUPPORT,
    PUBLIC_API_CONTRACT as _PARENT_CONTRACT,
    SUPPORTED_ENGINE_METHODS,
    SUPPORTED_INSPECTION_SURFACES as _PARENT_INSPECTION,
    SUPPORTED_PUBLIC_IMPORTS as _PARENT_IMPORTS,
    __version__,
    public_api_contract as _parent_public_api_contract,
    validate_public_api_contract as _validate_parent_public_api_contract,
)
from .semantic_projection import *
from .semantic_projection import __all__ as _SEMANTIC_IMPORTS

PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"
PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.17"
SEMANTIC_PROJECTION_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"

SUPPORTED_PUBLIC_IMPORTS = tuple(dict.fromkeys(_PARENT_IMPORTS + tuple(_SEMANTIC_IMPORTS)))
SUPPORTED_INSPECTION_SURFACES = tuple(dict.fromkeys(_PARENT_INSPECTION + ("semantic-projection",)))

PUBLIC_API_CONTRACT = deepcopy(_PARENT_CONTRACT)
PUBLIC_API_CONTRACT["contract_version"] = PUBLIC_ADOPTION_CONTRACT_VERSION
PUBLIC_API_CONTRACT["parent_contract_version"] = PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION
PUBLIC_API_CONTRACT["description"] = "0.32.17 Rule boundary plus qualified semantic projection/equivalence/invariant IR; no runtime composition."
PUBLIC_API_CONTRACT["supported_public_imports"] = list(SUPPORTED_PUBLIC_IMPORTS)
PUBLIC_API_CONTRACT["supported_engine_methods"] = list(SUPPORTED_ENGINE_METHODS)
PUBLIC_API_CONTRACT["supported_inspection_surfaces"] = list(SUPPORTED_INSPECTION_SURFACES)

_semantic = deepcopy(semantic_projection_contract())
_semantic["public_admission"] = SEMANTIC_PROJECTION_PUBLIC_ADMISSION
_semantic["runtime_admission"] = "PRE_ADMISSION_ONLY"
_semantic["engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"
_semantic["active_root_status"] = "CANDIDATE_UNTIL_PACKAGE_ROOT_SWITCH"
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

PUBLIC_ADOPTION_SUPPORT = dict(_PARENT_SUPPORT)
PUBLIC_ADOPTION_SUPPORT.update({
    "semantic_projection": "QUALIFIED_SEMANTIC_IR_ONLY",
    "semantic_equivalence": "QUALIFIED_SEMANTIC_IR_ONLY",
    "invariant_classification": "QUALIFIED_SEMANTIC_IR_ONLY",
    "semantic_projection_runtime": "PRE_ADMISSION_ONLY",
})

def public_api_contract() -> dict:
    return deepcopy(PUBLIC_API_CONTRACT)

def validate_public_api_contract() -> dict:
    parent = _validate_parent_public_api_contract()
    if not parent.get("valid"):
        return {"valid": False, "reason": "parent_rule_public_contract_invalid", "parent": parent}
    if _parent_public_api_contract().get("contract_version") != PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION:
        return {"valid": False, "reason": "parent_rule_contract_version_drift"}
    if PUBLIC_API_CONTRACT.get("contract_version") != PUBLIC_ADOPTION_CONTRACT_VERSION:
        return {"valid": False, "reason": "semantic_projection_public_contract_version_drift"}
    if tuple(PUBLIC_API_CONTRACT.get("supported_engine_methods") or ()) != SUPPORTED_ENGINE_METHODS:
        return {"valid": False, "reason": "engine_method_surface_drift"}
    semantic = PUBLIC_API_CONTRACT.get("semantic_projection") or {}
    required = {
        "contract_id": SEMANTIC_PROJECTION_CONTRACT_ID,
        "equivalence_contract_id": SEMANTIC_EQUIVALENCE_CONTRACT_ID,
        "invariant_contract_id": INVARIANT_CONTRACT_ID,
        "public_admission": SEMANTIC_PROJECTION_PUBLIC_ADMISSION,
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "engine_state_integration": "NONE_SEMANTIC_IR_ONLY",
        "parallel_projection_registry": "NONE",
        "current_projection_pointer": "NONE",
    }
    for key, value in required.items():
        if semantic.get(key) != value:
            return {"valid": False, "reason": f"semantic_projection_{key}_drift"}
    if any(value != "NONE" for value in (semantic.get("public_claim_ceiling") or {}).values()):
        return {"valid": False, "reason": "semantic_projection_claim_ceiling_drift"}
    return {
        "valid": True,
        "contract_version": PUBLIC_ADOPTION_CONTRACT_VERSION,
        "parent_contract_version": PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION,
        "semantic_projection_contract_id": SEMANTIC_PROJECTION_CONTRACT_ID,
        "semantic_equivalence_contract_id": SEMANTIC_EQUIVALENCE_CONTRACT_ID,
        "invariant_contract_id": INVARIANT_CONTRACT_ID,
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "active_root_status": "CANDIDATE_UNTIL_PACKAGE_ROOT_SWITCH",
    }

__all__ = tuple(dict.fromkeys((
    "AASMEngine", "PUBLIC_API_CONTRACT", "PUBLIC_ADOPTION_CONTRACT_VERSION",
    "PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION", "PUBLIC_ADOPTION_STABILITY",
    "PUBLIC_ADOPTION_SUPPORT", "SUPPORTED_PUBLIC_IMPORTS", "SUPPORTED_ENGINE_METHODS",
    "SUPPORTED_INSPECTION_SURFACES", "public_api_contract", "validate_public_api_contract", "__version__",
) + tuple(_SEMANTIC_IMPORTS)))
