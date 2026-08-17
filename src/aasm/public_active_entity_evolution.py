from __future__ import annotations

from copy import deepcopy

from . import public_active as _base

# Preserve the full additive 0.32.14 public surface exactly, then add only the
# qualified entity-evolution semantic/runtime surface. This keeps the previous
# public contract available as a stable parent rather than rewriting it in place.
for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .entity_evolution import (
    ENTITY_EVOLUTION_CONTRACT_ID,
    ENTITY_EVOLUTION_CONTRACT_VERSION,
    ENTITY_EVOLUTION_RELATIONS,
    ENTITY_EVOLUTION_STABILITY,
    EntityEvolution,
    EntityRepresentationRef,
    entity_evolution_contract,
)
from .entity_evolution_runtime import (
    ENTITY_EVOLUTION_CAPABILITIES,
    ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID,
    ENTITY_EVOLUTION_RUNTIME_CONTRACT_VERSION,
    ENTITY_EVOLUTION_RUNTIME_STABILITY,
    entity_evolution_runtime_contract,
    project_entity_evolution_evidence,
)
from .runtime_v56 import AASMEngine


__version__ = _base.__version__
PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY
REMOTE_PROTOCOL_NAME = _base.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _base.REMOTE_PROTOCOL_VERSION

_ENTITY_ENGINE_METHODS = [
    "entity_evolution_runtime_contract_report",
    "record_entity_evolution",
    "entity_evolution_event_report",
    "entity_evolution_report",
    "entity_evolutions_report",
]

_ENTITY_IMPORTS = [
    "ENTITY_EVOLUTION_CONTRACT_ID",
    "ENTITY_EVOLUTION_CONTRACT_VERSION",
    "ENTITY_EVOLUTION_STABILITY",
    "ENTITY_EVOLUTION_RELATIONS",
    "EntityRepresentationRef",
    "EntityEvolution",
    "entity_evolution_contract",
    "ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID",
    "ENTITY_EVOLUTION_RUNTIME_CONTRACT_VERSION",
    "ENTITY_EVOLUTION_RUNTIME_STABILITY",
    "ENTITY_EVOLUTION_CAPABILITIES",
    "project_entity_evolution_evidence",
    "entity_evolution_runtime_contract",
]

SUPPORTED_ENGINE_METHODS = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_ENGINE_METHODS", []), *_ENTITY_ENGINE_METHODS])
)
SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_INSPECTION_SURFACES = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_INSPECTION_SURFACES", []), "entity-evolution"])
)
SUPPORTED_PUBLIC_IMPORTS = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_ENTITY_IMPORTS])
)

PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update(
    {
        "contract_version": "0.32.15",
        "runtime_version": __version__,
        "release_stability": PUBLIC_RELEASE_STABILITY,
        "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
        "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
        "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
        "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
    }
)
PUBLIC_API_CONTRACT["entity_evolution"] = {
    **entity_evolution_contract(),
    "runtime": entity_evolution_runtime_contract(),
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _base.validate_public_api_contract()
    errors: list[str] = []
    if not parent["valid"]:
        errors.extend(f"active 0.32.14 parent: {error}" for error in parent["errors"])

    missing_imports = [name for name in _ENTITY_IMPORTS if name not in globals()]
    missing_methods = [name for name in _ENTITY_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing entity-evolution public imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing entity-evolution engine methods: {missing_methods}")
    if AASMEngine is not _base.AASMEngine:
        errors.append("entity evolution public candidate forked the active engine")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("entity evolution runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.15":
        errors.append("entity evolution adoption contract mismatch")
    if "entity-evolution" not in SUPPORTED_INSPECTION_SURFACES:
        errors.append("entity-evolution inspection surface missing")

    entity = PUBLIC_API_CONTRACT.get("entity_evolution", {})
    runtime = entity.get("runtime", {})
    if entity.get("contract_id") != ENTITY_EVOLUTION_CONTRACT_ID:
        errors.append("entity evolution semantic contract missing")
    if tuple(entity.get("relations", ())) != ENTITY_EVOLUTION_RELATIONS:
        errors.append("entity evolution relation set drift")
    if entity.get("entity_identity") != "EXPLICIT_STABLE_ID_NEVER_REWRITTEN_BY_ARTIFACT_RECENCY":
        errors.append("entity identity became artifact-recency derived")
    if entity.get("representation_identity") != "EXACT_ARTIFACT_REVISION_ID_FINGERPRINT_AND_REPRESENTATION_FINGERPRINT":
        errors.append("entity representation lost exact artifact binding")
    if entity.get("ambiguous_mapping") != "FAIL_CLOSED_FOR_HARD_REUSE_OR_AUTOMATIC_IDENTITY_TRANSFER":
        errors.append("ambiguous entity mapping no longer fails closed")
    for key in (
        "artifact_authority",
        "physical_state_authority",
        "external_state_authority",
        "fact_authority_creation",
        "source_trust_creation",
        "effect_authorization",
        "effect_dispatch",
        "current_entity_state_pointer",
    ):
        if entity.get(key) != "NONE":
            errors.append(f"entity evolution semantic authority firewall drift: {key}")
    if entity.get("parallel_entity_registry") != "NONE_EVIDENCE_PROJECTION_ONLY":
        errors.append("entity evolution introduced a semantic entity registry")
    if entity.get("hidden_wall_clock") != "NONE":
        errors.append("entity evolution introduced hidden wall-clock semantics")

    if runtime.get("contract_id") != ENTITY_EVOLUTION_RUNTIME_CONTRACT_ID:
        errors.append("entity evolution runtime contract missing")
    if runtime.get("durability") != "EXISTING_AASM_EVIDENCE_EVENT_REPLAY":
        errors.append("entity evolution bypassed existing Evidence/replay durability")
    if runtime.get("recording_authority") != "EXISTING_AASM_SCOPED_AUTHORITY_ONLY":
        errors.append("entity evolution introduced parallel recording authority")
    if runtime.get("artifact_revision_source") != "EXISTING_ARTIFACT_LINEAGE_PROJECTION_ONLY":
        errors.append("entity evolution introduced a second artifact lineage source")
    if runtime.get("artifact_revision_binding") != "EXACT_ID_AND_FINGERPRINT_REQUIRED":
        errors.append("entity evolution artifact binding became inexact")
    if runtime.get("ambiguity") != "RECORDED_EXPLICITLY_AND_FAIL_CLOSED_FOR_HARD_AUTOMATIC_REUSE":
        errors.append("entity evolution runtime ambiguity no longer fails closed")
    if runtime.get("heads") != "QUERY_PROJECTION_ONLY_NEVER_CURRENT_STATE_OR_AUTHORITY":
        errors.append("entity evolution heads acquired current-state semantics")
    for key in (
        "artifact_authority",
        "physical_state_authority",
        "external_state_authority",
        "fact_authority_creation",
        "source_trust_creation",
        "effect_authorization",
        "effect_dispatch",
        "state_claim_creation",
        "current_entity_state_pointer",
    ):
        if runtime.get(key) != "NONE":
            errors.append(f"entity evolution runtime authority firewall drift: {key}")
    if runtime.get("parallel_entity_registry") != "NONE_EVIDENCE_PROJECTION_ONLY":
        errors.append("entity evolution runtime introduced a parallel entity registry")
    if runtime.get("parallel_current_state_store") != "NONE":
        errors.append("entity evolution runtime introduced a current-state store")
    if runtime.get("hidden_wall_clock") != "NONE":
        errors.append("entity evolution runtime introduced hidden wall-clock semantics")
    if runtime.get("runtime_admission") != "ACTIVE_ENGINE_QUALIFIED":
        errors.append("entity evolution public candidate does not expose the qualified candidate runtime boundary")

    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}
