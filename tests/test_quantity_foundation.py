from __future__ import annotations

from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path

import pytest

from aasm.effect_capability import EffectCapability, NumericInterval
from aasm.quantity import (
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
from aasm.semantic_evolution import ExternalReference


ROOT = Path(__file__).resolve().parents[1]


def n(value: int) -> ExactNumber:
    return ExactNumber.integer(value)


def d(value: str) -> ExactNumber:
    return ExactNumber.decimal(value)


def length_dimension() -> DimensionVector:
    return DimensionVector({"length": 1})


def time_dimension() -> DimensionVector:
    return DimensionVector({"time": 1})


def identity_unit(name: str) -> UnitBinding:
    return UnitBinding(name, name, n(1), n(0))


def uncertainty_ref() -> ExternalReference:
    return ExternalReference(
        "metrology",
        "certificate-7",
        "uncertainty_model",
        revision="2026-08-17",
        source_fingerprint="a" * 64,
    )


def test_exact_integer_rational_and_decimal_normalization_is_portable():
    assert ExactNumber("INTEGER", "+7").to_dict() == {"representation": "INTEGER", "canonical": "7"}
    assert ExactNumber("INTEGER", "-0").canonical == "0"
    assert ExactNumber("RATIONAL", "2/-4").canonical == "-1/2"
    assert ExactNumber.rational(-6, -8).canonical == "3/4"
    assert ExactNumber("DECIMAL", "+12.3400").canonical == "12.34"
    assert ExactNumber("DECIMAL", "-0.000").canonical == "0"
    assert ExactNumber.from_fraction(Fraction(5, 4)).canonical == "5/4"
    assert ExactNumber.from_fraction(Fraction(8, 4)).to_dict() == {"representation": "INTEGER", "canonical": "2"}


def test_binary_float_and_noncanonical_decimal_syntax_are_rejected():
    with pytest.raises(TypeError, match="float"):
        ExactNumber.integer(1.0)
    with pytest.raises(TypeError, match="explicit string"):
        ExactNumber.decimal(1.25)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="non-exponent"):
        ExactNumber.decimal("1e3")
    with pytest.raises(ValueError, match="canonical base-10"):
        ExactNumber("INTEGER", "01")
    with pytest.raises(ValueError, match="non-zero"):
        ExactNumber.rational(1, 0)


def test_exact_affine_unit_conversion_supports_scale_and_offset_without_float_identity():
    cm_to_m = UnitBinding("cm", "m", ExactNumber.rational(1, 100), n(0))
    assert cm_to_m.convert_number(d("125.00")).as_fraction == Fraction(5, 4)
    assert cm_to_m.convert_delta(d("0.5")).as_fraction == Fraction(1, 200)

    celsius_to_kelvin = UnitBinding("degC", "K", n(1), d("273.15"))
    assert celsius_to_kelvin.convert_number(d("25.0")).as_fraction == Fraction(5963, 20)
    assert celsius_to_kelvin.convert_delta(d("10.0")).as_fraction == Fraction(10, 1)


def test_same_unit_requires_identity_transform_and_scale_must_be_positive():
    with pytest.raises(ValueError, match="identity scale"):
        UnitBinding("m", "m", ExactNumber.rational(2, 1), n(0))
    with pytest.raises(ValueError, match="zero offset"):
        UnitBinding("K", "K", n(1), d("273.15"))
    with pytest.raises(ValueError, match="strictly positive"):
        UnitBinding("cm", "m", n(0), n(0))
    with pytest.raises(ValueError, match="strictly positive"):
        UnitBinding("cm", "m", n(-1), n(0))


def test_dimension_vectors_are_canonical_and_support_exact_dimension_algebra():
    length = DimensionVector({"time": 0, "length": 1})
    time = DimensionVector({"time": 1})
    assert length.to_dict() == {"exponents": {"length": 1}}
    assert length.divide(time).to_dict() == {"exponents": {"length": 1, "time": -1}}
    assert length.multiply(length).to_dict() == {"exponents": {"length": 2}}
    assert DimensionVector({}).is_dimensionless is True
    with pytest.raises(TypeError, match="exact integers"):
        DimensionVector({"length": 1.0})  # type: ignore[dict-item]
    with pytest.raises(ValueError, match="invalid dimension"):
        DimensionVector({"Length!": 1})


def test_interval_ordering_and_zero_width_open_interval_fail_closed():
    interval = IntervalValue(d("1.0"), d("2.0"), True, False)
    assert interval.contains(d("1.0")) is True
    assert interval.contains(d("2.0")) is False
    with pytest.raises(ValueError, match="lower bound"):
        IntervalValue(n(2), n(1))
    with pytest.raises(ValueError, match="zero-width"):
        IntervalValue(n(1), n(1), False, True)


def test_measured_value_requires_uncertainty_interval_containing_nominal_and_reference():
    reference = uncertainty_ref()
    measured = MeasuredValue(
        d("5.00"),
        IntervalValue(d("4.95"), d("5.05")),
        reference,
        "MEASURED",
    )
    estimated = MeasuredValue(
        d("5.00"),
        IntervalValue(d("4.8"), d("5.2")),
        reference,
        "ESTIMATED",
    )
    assert measured.uncertainty_reference.fingerprint == reference.fingerprint
    assert MeasuredValue.from_dict(measured.to_dict()).to_dict() == measured.to_dict()
    assert estimated.measurement_kind == "ESTIMATED"
    with pytest.raises(ValueError, match="contain the nominal"):
        MeasuredValue(d("5.0"), IntervalValue(d("5.1"), d("5.2")), reference)
    with pytest.raises(ValueError, match="measurement kind"):
        MeasuredValue(d("5"), IntervalValue(d("4"), d("6")), reference, "SIMULATED")


def test_tolerance_modes_are_explicit_nonnegative_and_mode_specific():
    assert ToleranceSpec().to_dict() == {"kind": "NONE", "magnitude": None, "lower": None, "upper": None}
    assert ToleranceSpec("ABSOLUTE", d("0.05")).magnitude == d("0.05")
    assert ToleranceSpec("RELATIVE", d("0.01")).magnitude == d("0.01")
    asymmetric = ToleranceSpec("ASYMMETRIC", lower=d("0.1"), upper=d("0.2"))
    assert asymmetric.lower == d("0.1") and asymmetric.upper == d("0.2")
    with pytest.raises(ValueError, match="cannot carry"):
        ToleranceSpec("NONE", n(0))
    with pytest.raises(ValueError, match="requires magnitude"):
        ToleranceSpec("ABSOLUTE")
    with pytest.raises(ValueError, match="requires lower and upper"):
        ToleranceSpec("ASYMMETRIC", lower=n(1))
    with pytest.raises(ValueError, match="non-negative"):
        ToleranceSpec("RELATIVE", d("-0.1"))


def test_absolute_and_asymmetric_tolerances_convert_as_deltas_while_relative_is_unitless():
    cm_to_m = UnitBinding("cm", "m", ExactNumber.rational(1, 100), n(0))
    absolute = Quantity("DECIMAL", d("100"), length_dimension(), cm_to_m, ToleranceSpec("ABSOLUTE", d("0.5")))
    relative = Quantity("DECIMAL", d("100"), length_dimension(), cm_to_m, ToleranceSpec("RELATIVE", d("0.01")))
    asymmetric = Quantity(
        "DECIMAL",
        d("100"),
        length_dimension(),
        cm_to_m,
        ToleranceSpec("ASYMMETRIC", lower=d("0.5"), upper=d("1.0")),
    )
    assert absolute.canonical_tolerance.magnitude.as_fraction == Fraction(1, 200)  # type: ignore[union-attr]
    assert relative.canonical_tolerance.magnitude == d("0.01")
    assert asymmetric.canonical_tolerance.lower.as_fraction == Fraction(1, 200)  # type: ignore[union-attr]
    assert asymmetric.canonical_tolerance.upper.as_fraction == Fraction(1, 100)  # type: ignore[union-attr]


def test_quantization_requires_positive_step_and_explicit_rounding_rule():
    q = QuantizationSpec(d("0.01"), n(0), "HALF_EVEN")
    assert q.rounding_rule == "HALF_EVEN"
    with pytest.raises(ValueError, match="strictly positive"):
        QuantizationSpec(n(0))
    with pytest.raises(ValueError, match="rounding rule"):
        QuantizationSpec(n(1), n(0), "BANKERS_MAGIC")


def test_source_precision_is_explicit_and_nonnegative():
    assert PrecisionSpec("DECIMAL_PLACES", 3).to_dict() == {"kind": "DECIMAL_PLACES", "digits": 3}
    assert PrecisionSpec("SIGNIFICANT_DIGITS", 6).digits == 6
    with pytest.raises(ValueError, match="non-negative integer"):
        PrecisionSpec("DECIMAL_PLACES", -1)
    with pytest.raises(ValueError, match="precision kind"):
        PrecisionSpec("BINARY_BITS", 8)


def test_quantity_identity_round_trip_and_canonical_projection_are_deterministic():
    cm_to_m = UnitBinding("cm", "m", ExactNumber.rational(1, 100), n(0))
    item = Quantity(
        "DECIMAL",
        d("125.00"),
        length_dimension(),
        cm_to_m,
        tolerance=ToleranceSpec("ABSOLUTE", d("0.5")),
        quantization=QuantizationSpec(d("0.1"), n(0), "HALF_EVEN"),
        source_precision=PrecisionSpec("DECIMAL_PLACES", 2),
        provenance_refs=(ExternalReference("cad", "dimension-42", "source_value", revision="17"),),
        metadata={"source": "drawing"},
    )
    same = Quantity.from_dict(item.to_dict())
    assert same.quantity_id == item.quantity_id
    assert same.fingerprint == item.fingerprint
    assert same.canonical_projection_fingerprint == item.canonical_projection_fingerprint
    assert item.canonical_value.as_fraction == Fraction(5, 4)  # type: ignore[union-attr]
    projection = item.canonical_projection_payload()
    assert projection["representation"] == "DECIMAL"
    assert projection["value"] == {"representation": "RATIONAL", "canonical": "5/4"}
    assert projection["canonical_unit"] == "m"


def test_quantity_tamper_checks_reject_id_fingerprint_projection_and_projection_fingerprint_changes():
    item = Quantity("INTEGER", n(5), length_dimension(), identity_unit("m"))

    changed = deepcopy(item.to_dict())
    changed["quantity_id"] = "quantity-" + "0" * 24
    with pytest.raises(ValueError, match="quantity_id"):
        Quantity.from_dict(changed)

    changed = deepcopy(item.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint"):
        Quantity.from_dict(changed)

    changed = deepcopy(item.to_dict())
    changed["canonical_projection"]["canonical_unit"] = "cm"
    with pytest.raises(ValueError, match="canonical projection"):
        Quantity.from_dict(changed)

    changed = deepcopy(item.to_dict())
    changed["canonical_projection_fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="projection fingerprint"):
        Quantity.from_dict(changed)


def test_different_source_units_can_project_to_same_canonical_mathematical_value():
    one_meter = Quantity("DECIMAL", d("1.0"), length_dimension(), identity_unit("m"))
    hundred_cm = Quantity(
        "DECIMAL",
        d("100.0"),
        length_dimension(),
        UnitBinding("cm", "m", ExactNumber.rational(1, 100), n(0)),
    )
    assert one_meter.quantity_id != hundred_cm.quantity_id
    assert one_meter.unit.source_unit != hundred_cm.unit.source_unit
    assert one_meter.canonical_value.as_fraction == hundred_cm.canonical_value.as_fraction == Fraction(1, 1)  # type: ignore[union-attr]
    assert one_meter.canonical_projection_payload() == hundred_cm.canonical_projection_payload()
    assert one_meter.canonical_projection_fingerprint == hundred_cm.canonical_projection_fingerprint


def test_dimensional_and_canonical_unit_inconsistency_fail_closed():
    distance = Quantity("INTEGER", n(1), length_dimension(), identity_unit("m"))
    duration = Quantity("INTEGER", n(1), time_dimension(), identity_unit("s"))
    with pytest.raises(ValueError, match="dimensionally inconsistent"):
        require_dimensionally_compatible(distance, duration)

    meters = Quantity("INTEGER", n(1), length_dimension(), identity_unit("m"))
    canonical_cm = Quantity("INTEGER", n(1), length_dimension(), identity_unit("cm"))
    assert meters.dimensionally_compatible_with(canonical_cm) is True
    with pytest.raises(ValueError, match="explicit translation contract"):
        require_canonically_compatible(meters, canonical_cm)


def test_quantity_metadata_and_provenance_cannot_smuggle_binary_float_identity():
    with pytest.raises(TypeError, match="binary floating-point"):
        Quantity("INTEGER", n(1), DimensionVector({}), identity_unit("1"), metadata={"score": 0.1})

    floating_ref = ExternalReference("lab", "cert", "uncertainty", metadata={"confidence": 0.9})
    with pytest.raises(TypeError, match="binary floating-point"):
        Quantity("INTEGER", n(1), DimensionVector({}), identity_unit("1"), provenance_refs=(floating_ref,))


def test_measured_quantity_round_trip_preserves_uncertainty_provenance():
    measured = MeasuredValue(d("10.0"), IntervalValue(d("9.9"), d("10.1")), uncertainty_ref())
    item = Quantity("MEASURED", measured, DimensionVector({"voltage": 1}), identity_unit("V"))
    restored = Quantity.from_dict(item.to_dict())
    assert restored.value.to_dict() == measured.to_dict()
    assert restored.fingerprint == item.fingerprint


def test_quantity_contract_firewalls_and_pre_admission_boundary_are_explicit():
    contract = quantity_contract()
    assert contract["contract_id"] == "aasm.quantity.v1"
    assert contract["contract_version"] == "0.1.0"
    assert contract["numeric_identity"] == "EXACT_INTEGER_RATIONAL_OR_CANONICAL_DECIMAL_NO_BINARY_FLOAT"
    assert contract["unit_registry"] == "NONE_HIDDEN_OR_MUTABLE"
    assert contract["dimensional_inconsistency"] == "FAIL_CLOSED_BEFORE_SOLVING_OR_VERIFICATION"
    assert contract["legacy_solver_numeric_tolerance"] == "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"
    assert contract["legacy_effect_capability_numeric_bounds"] == "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"
    assert contract["fact_authority"] == "NONE"
    assert contract["effect_authority"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"


def test_quantity_schema_is_closed_and_durable_numerics_are_strings_not_json_numbers():
    schema = json.loads((ROOT / "schemas/quantity.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert schema["properties"]["contract_id"]["const"] == "aasm.quantity.v1"
    assert schema["properties"]["contract_version"]["const"] == "0.1.0"
    exact = schema["$defs"]["exactNumber"]
    assert exact["additionalProperties"] is False
    assert exact["properties"]["canonical"] == {"type": "string", "minLength": 1}
    assert exact["properties"]["representation"]["enum"] == ["INTEGER", "RATIONAL", "DECIMAL"]
    assert schema["$defs"]["unitBinding"]["additionalProperties"] is False
    assert schema["$defs"]["canonicalProjection"]["additionalProperties"] is False


def test_legacy_solver_numeric_tolerance_schema_is_not_reinterpreted_as_physical_quantity():
    schema_text = (ROOT / "schemas/numeric-tolerance.schema.json").read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    assert set(schema["properties"]) == {
        "absolute",
        "relative",
        "primal_feasibility",
        "dual_feasibility",
        "integrality",
        "mip_gap",
    }
    for forbidden in ("aasm.quantity.v1", "dimension", "source_unit", "canonical_unit"):
        assert forbidden not in schema_text


def test_legacy_effect_capability_float_numeric_interval_behavior_is_untouched():
    interval = NumericInterval(1.25, 2.5)
    assert interval.contains_value(1.5) is True
    assert interval.contains_value(3.0) is False
    assert interval.to_dict() == {"minimum": 1.25, "maximum": 2.5}

    capability = EffectCapability(
        domain_id="motor",
        authority_lease_id="lease-1",
        workspace_id="w",
        scope_id="s",
        subject_id="machine",
        holder_principal_id="controller",
        issuer_principal_id="policy",
        allowed_operations=("set_speed",),
        numeric_bounds={"rpm": {"minimum": 0.0, "maximum": 1000.0}},
        valid_from=0.0,
        expires_at=10.0,
        authority_epoch=1,
    )
    assert capability.bounds_allow({"rpm": 500.0}) is True
    assert capability.bounds_allow({"rpm": 1500.0}) is False
