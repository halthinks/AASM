from __future__ import annotations

from fractions import Fraction

import aasm
from aasm import public_active_entity_evolution as parent
from aasm import public_active_engineering_quantity as candidate


def test_quantity_public_candidate_is_additive_over_qualified_parent():
    parent_report = parent.validate_public_api_contract()
    candidate_report = candidate.validate_public_api_contract()
    assert parent_report["valid"], parent_report
    assert candidate_report["valid"], candidate_report
    assert parent.PUBLIC_API_CONTRACT["contract_version"] == "0.32.15"
    assert candidate.PUBLIC_API_CONTRACT["contract_version"] == "0.32.16"
    assert candidate.AASMEngine is parent.AASMEngine
    assert candidate.AASMEngine is aasm.AASMEngine
    assert set(parent.SUPPORTED_PUBLIC_IMPORTS).issubset(candidate.SUPPORTED_PUBLIC_IMPORTS)
    assert set(parent.SUPPORTED_INSPECTION_SURFACES).issubset(candidate.SUPPORTED_INSPECTION_SURFACES)
    assert candidate.SUPPORTED_ENGINE_METHODS == parent.SUPPORTED_ENGINE_METHODS


def test_quantity_public_candidate_exports_exact_quantity_contract_and_firewalls():
    contract = candidate.public_api_contract()["engineering_quantity"]
    assert contract["contract_id"] == "aasm.quantity.v1"
    assert contract["contract_version"] == "0.1.0"
    assert contract["numeric_identity"] == "EXACT_INTEGER_RATIONAL_OR_CANONICAL_DECIMAL_NO_BINARY_FLOAT"
    assert contract["physical_dimension"] == "EXPLICIT_CANONICAL_INTEGER_EXPONENT_VECTOR"
    assert contract["unit_binding"] == "EXPLICIT_EXACT_AFFINE_SOURCE_TO_CANONICAL_TRANSFORM"
    assert contract["unit_registry"] == "NONE_HIDDEN_OR_MUTABLE"
    assert contract["dimensional_inconsistency"] == "FAIL_CLOSED_BEFORE_SOLVING_OR_VERIFICATION"
    assert contract["legacy_solver_numeric_tolerance"] == "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"
    assert contract["legacy_effect_capability_numeric_bounds"] == "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "CANDIDATE"
    assert contract["engine_state_integration"] == "NONE_SEMANTIC_VALUE_FOUNDATION_ONLY"
    for key in (
        "fact_authority",
        "physical_state_authority",
        "external_state_authority",
        "effect_authority",
        "artifact_acceptance",
        "entity_identity_authority",
        "hidden_wall_clock",
    ):
        assert contract[key] == "NONE"


def test_quantity_public_candidate_exposes_real_exact_value_types_without_engine_state():
    length = candidate.DimensionVector({"length": 1})
    cm_to_m = candidate.UnitBinding(
        "cm",
        "m",
        candidate.ExactNumber.rational(1, 100),
        candidate.ExactNumber.integer(0),
    )
    item = candidate.Quantity(
        "DECIMAL",
        candidate.ExactNumber.decimal("250.0"),
        length,
        cm_to_m,
        tolerance=candidate.ToleranceSpec("ABSOLUTE", candidate.ExactNumber.decimal("0.5")),
    )
    assert item.canonical_value.as_fraction == Fraction(5, 2)
    assert item.canonical_tolerance.magnitude.as_fraction == Fraction(1, 200)
    assert candidate.Quantity.from_dict(item.to_dict()).fingerprint == item.fingerprint
    assert "engineering-quantity" in candidate.SUPPORTED_INSPECTION_SURFACES
    assert not any(name.startswith("quantity_") for name in candidate.SUPPORTED_ENGINE_METHODS)


def test_quantity_public_candidate_does_not_reinterpret_live_solver_or_effect_capability_types():
    from aasm.effect_capability import NumericInterval

    interval = NumericInterval(1.25, 2.5)
    assert interval.to_dict() == {"minimum": 1.25, "maximum": 2.5}
    assert candidate.PUBLIC_API_CONTRACT["engineering_quantity"]["legacy_solver_numeric_tolerance"] == "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"
    assert candidate.PUBLIC_API_CONTRACT["engineering_quantity"]["legacy_effect_capability_numeric_bounds"] == "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"


def test_quantity_candidate_does_not_silently_promote_package_root_before_gate():
    assert aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.15"
    assert "engineering_quantity" not in aasm.PUBLIC_API_CONTRACT
    assert not hasattr(aasm, "Quantity")
