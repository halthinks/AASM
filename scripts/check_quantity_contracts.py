from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing required quantity file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    quantity = text("src/aasm/quantity.py")
    schema_text = text("schemas/quantity.schema.json")
    tests = text("tests/test_quantity_foundation.py")
    foundation = text("src/aasm/runtime_v56_foundation.py")
    public = text("src/aasm/public_active_entity_evolution.py")
    package_init = text("src/aasm/__init__.py")
    capability = text("src/aasm/effect_capability.py")
    legacy_tolerance_text = text("schemas/numeric-tolerance.schema.json")

    schema = json.loads(schema_text)
    legacy_tolerance = json.loads(legacy_tolerance_text)

    require(schema["properties"]["contract_id"]["const"] == "aasm.quantity.v1", "quantity schema contract ID drift")
    require(schema["properties"]["contract_version"]["const"] == "0.1.0", "quantity schema version drift")
    require(schema.get("additionalProperties") is False, "quantity top-level schema must be closed")
    for definition in (
        "exactNumber",
        "dimensionVector",
        "unitBinding",
        "intervalValue",
        "externalReferenceIdentity",
        "measuredValue",
        "tolerance",
        "quantization",
        "precision",
        "canonicalProjection",
    ):
        require(schema["$defs"][definition].get("additionalProperties") is False, f"quantity schema definition is not closed: {definition}")
    exact = schema["$defs"]["exactNumber"]
    require(exact["properties"]["canonical"].get("type") == "string", "quantity durable numeric canonical value must be a string")
    require(exact["properties"]["representation"]["enum"] == ["INTEGER", "RATIONAL", "DECIMAL"], "quantity exact-number representation drift")

    required_tokens = [
        'QUANTITY_CONTRACT_ID = "aasm.quantity.v1"',
        'QUANTITY_CONTRACT_VERSION = "0.1.0"',
        '"INTEGER"',
        '"RATIONAL"',
        '"DECIMAL"',
        '"INTERVAL"',
        '"MEASURED"',
        '"ESTIMATED"',
        '"ABSOLUTE"',
        '"RELATIVE"',
        '"ASYMMETRIC"',
        '"HALF_EVEN"',
        '"SIGNIFICANT_DIGITS"',
        'raise TypeError("binary floating-point values are forbidden in quantity semantic identity")',
        '"EXPLICIT_EXACT_AFFINE_SOURCE_TO_CANONICAL_TRANSFORM"',
        '"NONE_HIDDEN_OR_MUTABLE"',
        '"FAIL_CLOSED_BEFORE_SOLVING_OR_VERIFICATION"',
        '"UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"fact_authority": "NONE"',
        '"effect_authority": "NONE"',
        "require_dimensionally_compatible",
        "require_canonically_compatible",
        "canonical_projection_fingerprint",
    ]
    for token in required_tokens:
        require(token in quantity, f"quantity semantic contract missing token: {token}")

    banned_source_tokens = [
        "datetime.now(",
        "time.time(",
        "FactAuthority(",
        "StateClaim(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "UNIT_REGISTRY =",
        "GLOBAL_UNIT_REGISTRY",
        "register_unit(",
        "current_quantity_store",
        "latest_quantity",
    ]
    for token in banned_source_tokens:
        require(token not in quantity, f"quantity foundation violates source firewall with token: {token}")

    # Pre-admission firewall: semantic foundation is importable internally but
    # must not yet be composed into the engine or claimed by the active public
    # adoption contract.
    for active_source, label in (
        (foundation, "runtime_v56_foundation"),
        (public, "active public overlay"),
        (package_init, "package root"),
    ):
        require("from .quantity" not in active_source, f"quantity was prematurely imported by {label}")
        require("aasm.quantity.v1" not in active_source, f"quantity was prematurely claimed by {label}")
        require('"Quantity"' not in active_source, f"quantity was prematurely exported by {label}")

    # Existing solver tolerance remains its own numerical-policy substrate.
    expected_legacy_fields = {
        "absolute",
        "relative",
        "primal_feasibility",
        "dual_feasibility",
        "integrality",
        "mip_gap",
    }
    require(set(legacy_tolerance["properties"]) == expected_legacy_fields, "legacy numeric-tolerance schema was reinterpreted or expanded")
    for forbidden in ("aasm.quantity.v1", "dimension", "source_unit", "canonical_unit"):
        require(forbidden not in legacy_tolerance_text, f"legacy solver numeric-tolerance schema leaked quantity semantics: {forbidden}")

    # Existing EffectCapability numeric bounds also remain byte-semantically
    # independent of the pre-admission physical quantity contract.
    require("from .quantity" not in capability, "EffectCapability prematurely depends on quantity foundation")
    require("class NumericInterval:" in capability, "legacy EffectCapability NumericInterval disappeared")
    require("minimum: float" in capability and "maximum: float" in capability, "legacy EffectCapability float interval semantics changed")
    require("numeric_bounds" in capability, "legacy EffectCapability numeric_bounds disappeared")

    required_test_tokens = [
        "test_exact_integer_rational_and_decimal_normalization_is_portable",
        "test_binary_float_and_noncanonical_decimal_syntax_are_rejected",
        "test_exact_affine_unit_conversion_supports_scale_and_offset_without_float_identity",
        "test_dimension_vectors_are_canonical_and_support_exact_dimension_algebra",
        "test_measured_value_requires_uncertainty_interval_containing_nominal_and_reference",
        "test_tolerance_modes_are_explicit_nonnegative_and_mode_specific",
        "test_quantity_identity_round_trip_and_canonical_projection_are_deterministic",
        "test_quantity_tamper_checks_reject_id_fingerprint_projection_and_projection_fingerprint_changes",
        "test_different_source_units_can_project_to_same_canonical_mathematical_value",
        "test_dimensional_and_canonical_unit_inconsistency_fail_closed",
        "test_quantity_metadata_and_provenance_cannot_smuggle_binary_float_identity",
        "test_legacy_solver_numeric_tolerance_schema_is_not_reinterpreted_as_physical_quantity",
        "test_legacy_effect_capability_float_numeric_interval_behavior_is_untouched",
    ]
    for token in required_test_tokens:
        require(token in tests, f"quantity adversarial corpus missing test: {token}")

    print("S4 quantity pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
