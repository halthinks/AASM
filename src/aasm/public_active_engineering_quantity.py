from __future__ import annotations

from copy import deepcopy

from . import public_active_entity_evolution as _base

# Preserve the complete qualified 0.32.15 public surface, then add only the
# independently qualified aasm.quantity.v1 semantic foundation. No engine
# state, authority path, unit registry, solver tolerance reinterpretation, or
# EffectCapability reinterpretation is introduced by this overlay.
for _name in dir(_base):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_base, _name)

from .quantity import (
    MEASUREMENT_KINDS,
    PRECISION_KINDS,
    QUANTITY_CONTRACT_ID,
    QUANTITY_CONTRACT_VERSION,
    QUANTITY_REPRESENTATIONS,
    QUANTITY_STABILITY,
    ROUNDING_RULES,
    TOLERANCE_KINDS,
    DimensionVector,
    ExactNumber,
    IntervalValue,
    MeasuredValue,
    PrecisionSpec,
    QuantizationSpec,
    Quantity,
    ToleranceSpec,
    UnitBinding,
    quantity_contract,
    require_canonically_compatible,
    require_dimensionally_compatible,
)


__version__ = _base.__version__
PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY
REMOTE_PROTOCOL_NAME = _base.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _base.REMOTE_PROTOCOL_VERSION
AASMEngine = _base.AASMEngine

_QUANTITY_IMPORTS = [
    "QUANTITY_CONTRACT_ID",
    "QUANTITY_CONTRACT_VERSION",
    "QUANTITY_STABILITY",
    "QUANTITY_REPRESENTATIONS",
    "MEASUREMENT_KINDS",
    "TOLERANCE_KINDS",
    "ROUNDING_RULES",
    "PRECISION_KINDS",
    "ExactNumber",
    "DimensionVector",
    "UnitBinding",
    "IntervalValue",
    "MeasuredValue",
    "ToleranceSpec",
    "QuantizationSpec",
    "PrecisionSpec",
    "Quantity",
    "require_dimensionally_compatible",
    "require_canonically_compatible",
    "quantity_contract",
]

SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))
SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))
SUPPORTED_INSPECTION_SURFACES = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_INSPECTION_SURFACES", []), "engineering-quantity"])
)
SUPPORTED_PUBLIC_IMPORTS = list(
    dict.fromkeys([*getattr(_base, "SUPPORTED_PUBLIC_IMPORTS", []), *_QUANTITY_IMPORTS])
)

PUBLIC_API_CONTRACT = deepcopy(_base.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update(
    {
        "contract_version": "0.32.16",
        "runtime_version": __version__,
        "release_stability": PUBLIC_RELEASE_STABILITY,
        "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
        "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
        "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
        "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
    }
)
PUBLIC_API_CONTRACT["engineering_quantity"] = {
    **quantity_contract(),
    "public_admission": "QUALIFIED",
    "engine_state_integration": "NONE_SEMANTIC_VALUE_FOUNDATION_ONLY",
}
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _base.validate_public_api_contract()
    errors: list[str] = []
    if not parent["valid"]:
        errors.extend(f"active 0.32.15 parent: {error}" for error in parent["errors"])

    missing_imports = [name for name in _QUANTITY_IMPORTS if name not in globals()]
    if missing_imports:
        errors.append(f"missing engineering-quantity public imports: {missing_imports}")
    if AASMEngine is not _base.AASMEngine:
        errors.append("engineering quantity overlay forked the active engine")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.32.16":
        errors.append("engineering quantity adoption contract mismatch")
    if "engineering-quantity" not in SUPPORTED_INSPECTION_SURFACES:
        errors.append("engineering-quantity inspection surface missing")

    quantity = PUBLIC_API_CONTRACT.get("engineering_quantity", {})
    if quantity.get("contract_id") != QUANTITY_CONTRACT_ID:
        errors.append("engineering quantity semantic contract missing")
    if quantity.get("contract_version") != QUANTITY_CONTRACT_VERSION:
        errors.append("engineering quantity semantic contract version drift")
    if tuple(quantity.get("representations", ())) != QUANTITY_REPRESENTATIONS:
        errors.append("engineering quantity representation set drift")
    if quantity.get("numeric_identity") != "EXACT_INTEGER_RATIONAL_OR_CANONICAL_DECIMAL_NO_BINARY_FLOAT":
        errors.append("engineering quantity lost exact portable numeric identity")
    if quantity.get("unit_binding") != "EXPLICIT_EXACT_AFFINE_SOURCE_TO_CANONICAL_TRANSFORM":
        errors.append("engineering quantity unit conversion is not explicit/exact")
    if quantity.get("unit_registry") != "NONE_HIDDEN_OR_MUTABLE":
        errors.append("engineering quantity introduced hidden mutable unit semantics")
    if quantity.get("dimensional_inconsistency") != "FAIL_CLOSED_BEFORE_SOLVING_OR_VERIFICATION":
        errors.append("engineering quantity dimensional inconsistency no longer fails closed")
    if quantity.get("legacy_solver_numeric_tolerance") != "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION":
        errors.append("engineering quantity reinterpreted solver numeric tolerance")
    if quantity.get("legacy_effect_capability_numeric_bounds") != "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION":
        errors.append("engineering quantity reinterpreted EffectCapability numeric bounds")
    if quantity.get("runtime_admission") != "PRE_ADMISSION_ONLY":
        errors.append("engineering quantity semantic foundation unexpectedly gained runtime admission")
    if quantity.get("public_admission") != "QUALIFIED":
        errors.append("engineering quantity public qualification status drift")
    if quantity.get("engine_state_integration") != "NONE_SEMANTIC_VALUE_FOUNDATION_ONLY":
        errors.append("engineering quantity overlay introduced engine state")
    for key in (
        "fact_authority",
        "physical_state_authority",
        "external_state_authority",
        "effect_authority",
        "artifact_acceptance",
        "entity_identity_authority",
        "hidden_wall_clock",
    ):
        if quantity.get(key) != "NONE":
            errors.append(f"engineering quantity authority/state firewall drift: {key}")

    if SUPPORTED_ENGINE_METHODS != list(getattr(_base, "SUPPORTED_ENGINE_METHODS", [])):
        errors.append("engineering quantity overlay added engine methods")

    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}
