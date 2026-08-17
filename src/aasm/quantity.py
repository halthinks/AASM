from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from fractions import Fraction
import re
from typing import Any, Mapping, Sequence

from .semantic_evolution import ExternalReference
from .semantic_result import semantic_fingerprint


QUANTITY_CONTRACT_ID = "aasm.quantity.v1"
QUANTITY_CONTRACT_VERSION = "0.1.0"
QUANTITY_STABILITY = "FOUNDATION_EXPERIMENTAL"
QUANTITY_REPRESENTATIONS = (
    "INTEGER",
    "RATIONAL",
    "DECIMAL",
    "INTERVAL",
    "MEASURED",
)
MEASUREMENT_KINDS = ("MEASURED", "ESTIMATED")
TOLERANCE_KINDS = ("NONE", "ABSOLUTE", "RELATIVE", "ASYMMETRIC")
ROUNDING_RULES = (
    "EXACT",
    "HALF_EVEN",
    "HALF_UP",
    "HALF_AWAY_FROM_ZERO",
    "TOWARD_ZERO",
    "FLOOR",
    "CEILING",
)
PRECISION_KINDS = ("DECIMAL_PLACES", "SIGNIFICANT_DIGITS")

_INTEGER_RE = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)$")
_RATIONAL_RE = re.compile(r"^([+-]?(?:0|[1-9][0-9]*))/([+-]?(?:0|[1-9][0-9]*))$")
_DECIMAL_RE = re.compile(r"^[+-]?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?$")
_DIMENSION_RE = re.compile(r"^[a-z][a-z0-9_.-]*$")


def _required_text(name: str, value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"quantity {name} is required")
    return normalized


def _optional_text(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _jsonable(value: Any) -> Any:
    if hasattr(value, "identity_payload"):
        return _jsonable(value.identity_payload())
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, float):
        raise TypeError("binary floating-point values are forbidden in quantity semantic identity")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"quantity value is not JSON serializable: {type(value)!r}")


def _fraction_to_decimal(value: Fraction) -> str | None:
    denominator = value.denominator
    probe = denominator
    for factor in (2, 5):
        while probe % factor == 0:
            probe //= factor
    if probe != 1:
        return None
    decimal_value = Decimal(value.numerator) / Decimal(value.denominator)
    text = format(decimal_value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"-0", "+0", ""}:
        return "0"
    return text


@dataclass(frozen=True)
class ExactNumber:
    """Portable exact scalar representation. Binary floats are deliberately absent."""

    representation: str
    canonical: str

    def __post_init__(self) -> None:
        representation = _required_text("number representation", self.representation).upper()
        if representation not in {"INTEGER", "RATIONAL", "DECIMAL"}:
            raise ValueError(f"unsupported exact number representation: {representation}")
        raw = _required_text("number canonical value", self.canonical)

        if representation == "INTEGER":
            if not _INTEGER_RE.fullmatch(raw):
                raise ValueError("integer quantity values must use canonical base-10 integer syntax")
            canonical = str(int(raw))
        elif representation == "RATIONAL":
            match = _RATIONAL_RE.fullmatch(raw)
            if match is None:
                raise ValueError("rational quantity values must use numerator/denominator syntax")
            numerator = int(match.group(1))
            denominator = int(match.group(2))
            if denominator == 0:
                raise ValueError("rational quantity denominator must be non-zero")
            value = Fraction(numerator, denominator)
            canonical = f"{value.numerator}/{value.denominator}"
        else:
            if not _DECIMAL_RE.fullmatch(raw):
                raise ValueError("decimal quantity values must use non-exponent base-10 decimal syntax")
            try:
                value = Decimal(raw)
            except InvalidOperation as exc:
                raise ValueError("invalid canonical decimal quantity value") from exc
            if not value.is_finite():
                raise ValueError("decimal quantity values must be finite")
            canonical = format(value, "f")
            if "." in canonical:
                canonical = canonical.rstrip("0").rstrip(".")
            if canonical in {"-0", "+0", ""}:
                canonical = "0"

        object.__setattr__(self, "representation", representation)
        object.__setattr__(self, "canonical", canonical)

    @property
    def as_fraction(self) -> Fraction:
        if self.representation == "INTEGER":
            return Fraction(int(self.canonical), 1)
        if self.representation == "RATIONAL":
            numerator, denominator = self.canonical.split("/", 1)
            return Fraction(int(numerator), int(denominator))
        return Fraction(Decimal(self.canonical))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, str]:
        return {"representation": self.representation, "canonical": self.canonical}

    def to_dict(self) -> dict[str, str]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExactNumber":
        return cls(str(value["representation"]), str(value["canonical"]))

    @classmethod
    def integer(cls, value: int | str) -> "ExactNumber":
        if isinstance(value, bool) or isinstance(value, float):
            raise TypeError("integer quantity construction forbids bool/float coercion")
        return cls("INTEGER", str(value))

    @classmethod
    def rational(cls, numerator: int, denominator: int) -> "ExactNumber":
        if isinstance(numerator, bool) or isinstance(denominator, bool):
            raise TypeError("rational quantity construction requires integer numerator/denominator")
        return cls("RATIONAL", f"{int(numerator)}/{int(denominator)}")

    @classmethod
    def decimal(cls, value: str) -> "ExactNumber":
        if not isinstance(value, str):
            raise TypeError("canonical decimal quantity construction requires an explicit string")
        return cls("DECIMAL", value)

    @classmethod
    def from_fraction(cls, value: Fraction) -> "ExactNumber":
        value = Fraction(value)
        if value.denominator == 1:
            return cls.integer(value.numerator)
        return cls.rational(value.numerator, value.denominator)

    def is_nonnegative(self) -> bool:
        return self.as_fraction >= 0

    def is_positive(self) -> bool:
        return self.as_fraction > 0


@dataclass(frozen=True)
class DimensionVector:
    """Explicit canonical physical dimension vector with integer exponents."""

    exponents: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized: dict[str, int] = {}
        for raw_name, raw_exponent in sorted(self.exponents.items(), key=lambda pair: str(pair[0])):
            name = _required_text("dimension component", str(raw_name)).lower()
            if not _DIMENSION_RE.fullmatch(name):
                raise ValueError(f"invalid dimension component identifier: {name}")
            if isinstance(raw_exponent, bool) or not isinstance(raw_exponent, int):
                raise TypeError("dimension exponents must be exact integers")
            exponent = int(raw_exponent)
            if exponent:
                normalized[name] = exponent
        object.__setattr__(self, "exponents", normalized)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    @property
    def is_dimensionless(self) -> bool:
        return not self.exponents

    def identity_payload(self) -> dict[str, Any]:
        return {"exponents": dict(sorted(self.exponents.items()))}

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DimensionVector":
        return cls(dict(value.get("exponents") or {}))

    def multiply(self, other: "DimensionVector") -> "DimensionVector":
        exponents = dict(self.exponents)
        for name, exponent in other.exponents.items():
            exponents[name] = exponents.get(name, 0) + exponent
        return DimensionVector(exponents)

    def divide(self, other: "DimensionVector") -> "DimensionVector":
        exponents = dict(self.exponents)
        for name, exponent in other.exponents.items():
            exponents[name] = exponents.get(name, 0) - exponent
        return DimensionVector(exponents)


@dataclass(frozen=True)
class UnitBinding:
    """Explicit exact affine source-unit -> canonical-unit transform.

    No global unit registry participates in this contract. A caller must supply
    the complete binding that makes the conversion semantics reviewable and
    portable: canonical = source * scale + offset.
    """

    source_unit: str
    canonical_unit: str
    scale: ExactNumber | Mapping[str, Any] = field(default_factory=lambda: ExactNumber.integer(1))
    offset: ExactNumber | Mapping[str, Any] = field(default_factory=lambda: ExactNumber.integer(0))

    def __post_init__(self) -> None:
        source = _required_text("source_unit", self.source_unit)
        canonical = _required_text("canonical_unit", self.canonical_unit)
        scale = self.scale if isinstance(self.scale, ExactNumber) else ExactNumber.from_dict(self.scale)
        offset = self.offset if isinstance(self.offset, ExactNumber) else ExactNumber.from_dict(self.offset)
        if not scale.is_positive():
            raise ValueError("unit conversion scale must be strictly positive")
        if source == canonical and (scale.as_fraction != 1 or offset.as_fraction != 0):
            raise ValueError("identical source/canonical units require identity scale and zero offset")
        object.__setattr__(self, "source_unit", source)
        object.__setattr__(self, "canonical_unit", canonical)
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "offset", offset)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source_unit": self.source_unit,
            "canonical_unit": self.canonical_unit,
            "scale": self.scale.identity_payload(),
            "offset": self.offset.identity_payload(),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UnitBinding":
        return cls(
            str(value["source_unit"]),
            str(value["canonical_unit"]),
            ExactNumber.from_dict(value["scale"]),
            ExactNumber.from_dict(value["offset"]),
        )

    def convert_number(self, value: ExactNumber) -> ExactNumber:
        canonical = value.as_fraction * self.scale.as_fraction + self.offset.as_fraction
        return ExactNumber.from_fraction(canonical)

    def convert_delta(self, value: ExactNumber) -> ExactNumber:
        return ExactNumber.from_fraction(value.as_fraction * self.scale.as_fraction)


@dataclass(frozen=True)
class IntervalValue:
    lower: ExactNumber | Mapping[str, Any]
    upper: ExactNumber | Mapping[str, Any]
    lower_inclusive: bool = True
    upper_inclusive: bool = True

    def __post_init__(self) -> None:
        lower = self.lower if isinstance(self.lower, ExactNumber) else ExactNumber.from_dict(self.lower)
        upper = self.upper if isinstance(self.upper, ExactNumber) else ExactNumber.from_dict(self.upper)
        if lower.as_fraction > upper.as_fraction:
            raise ValueError("quantity interval lower bound must be <= upper bound")
        if lower.as_fraction == upper.as_fraction and not (bool(self.lower_inclusive) and bool(self.upper_inclusive)):
            raise ValueError("zero-width quantity intervals must include their single value")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "lower_inclusive", bool(self.lower_inclusive))
        object.__setattr__(self, "upper_inclusive", bool(self.upper_inclusive))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "lower": self.lower.identity_payload(),
            "upper": self.upper.identity_payload(),
            "lower_inclusive": self.lower_inclusive,
            "upper_inclusive": self.upper_inclusive,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "IntervalValue":
        return cls(
            ExactNumber.from_dict(value["lower"]),
            ExactNumber.from_dict(value["upper"]),
            bool(value.get("lower_inclusive", True)),
            bool(value.get("upper_inclusive", True)),
        )

    def contains(self, value: ExactNumber) -> bool:
        candidate = value.as_fraction
        lower = self.lower.as_fraction
        upper = self.upper.as_fraction
        lower_ok = candidate > lower or (self.lower_inclusive and candidate == lower)
        upper_ok = candidate < upper or (self.upper_inclusive and candidate == upper)
        return lower_ok and upper_ok


@dataclass(frozen=True)
class MeasuredValue:
    nominal: ExactNumber | Mapping[str, Any]
    uncertainty_interval: IntervalValue | Mapping[str, Any]
    uncertainty_reference: ExternalReference | Mapping[str, Any]
    measurement_kind: str = "MEASURED"

    def __post_init__(self) -> None:
        nominal = self.nominal if isinstance(self.nominal, ExactNumber) else ExactNumber.from_dict(self.nominal)
        uncertainty = (
            self.uncertainty_interval
            if isinstance(self.uncertainty_interval, IntervalValue)
            else IntervalValue.from_dict(self.uncertainty_interval)
        )
        reference = (
            self.uncertainty_reference
            if isinstance(self.uncertainty_reference, ExternalReference)
            else ExternalReference.from_dict(dict(self.uncertainty_reference))
        )
        kind = _required_text("measurement_kind", self.measurement_kind).upper()
        if kind not in MEASUREMENT_KINDS:
            raise ValueError(f"unsupported measurement kind: {kind}")
        if not uncertainty.contains(nominal):
            raise ValueError("measured quantity uncertainty interval must contain the nominal value")
        _jsonable(reference.identity_payload())
        object.__setattr__(self, "nominal", nominal)
        object.__setattr__(self, "uncertainty_interval", uncertainty)
        object.__setattr__(self, "uncertainty_reference", reference)
        object.__setattr__(self, "measurement_kind", kind)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "measurement_kind": self.measurement_kind,
            "nominal": self.nominal.identity_payload(),
            "uncertainty_interval": self.uncertainty_interval.identity_payload(),
            "uncertainty_reference": self.uncertainty_reference.identity_payload(),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MeasuredValue":
        return cls(
            ExactNumber.from_dict(value["nominal"]),
            IntervalValue.from_dict(value["uncertainty_interval"]),
            ExternalReference.from_dict(dict(value["uncertainty_reference"])),
            str(value.get("measurement_kind") or "MEASURED"),
        )


@dataclass(frozen=True)
class ToleranceSpec:
    kind: str = "NONE"
    magnitude: ExactNumber | Mapping[str, Any] | None = None
    lower: ExactNumber | Mapping[str, Any] | None = None
    upper: ExactNumber | Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        kind = _required_text("tolerance kind", self.kind).upper()
        if kind not in TOLERANCE_KINDS:
            raise ValueError(f"unsupported quantity tolerance kind: {kind}")
        magnitude = None if self.magnitude is None else (
            self.magnitude if isinstance(self.magnitude, ExactNumber) else ExactNumber.from_dict(self.magnitude)
        )
        lower = None if self.lower is None else (
            self.lower if isinstance(self.lower, ExactNumber) else ExactNumber.from_dict(self.lower)
        )
        upper = None if self.upper is None else (
            self.upper if isinstance(self.upper, ExactNumber) else ExactNumber.from_dict(self.upper)
        )
        for name, item in (("magnitude", magnitude), ("lower", lower), ("upper", upper)):
            if item is not None and not item.is_nonnegative():
                raise ValueError(f"quantity tolerance {name} must be non-negative")
        if kind == "NONE" and any(item is not None for item in (magnitude, lower, upper)):
            raise ValueError("NONE tolerance cannot carry numeric tolerance values")
        if kind in {"ABSOLUTE", "RELATIVE"}:
            if magnitude is None or lower is not None or upper is not None:
                raise ValueError(f"{kind} tolerance requires magnitude only")
        if kind == "ASYMMETRIC":
            if magnitude is not None or lower is None or upper is None:
                raise ValueError("ASYMMETRIC tolerance requires lower and upper magnitudes")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "magnitude", magnitude)
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "magnitude": None if self.magnitude is None else self.magnitude.identity_payload(),
            "lower": None if self.lower is None else self.lower.identity_payload(),
            "upper": None if self.upper is None else self.upper.identity_payload(),
        }

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ToleranceSpec":
        def number(name: str) -> ExactNumber | None:
            raw = value.get(name)
            return None if raw is None else ExactNumber.from_dict(raw)
        return cls(str(value.get("kind") or "NONE"), number("magnitude"), number("lower"), number("upper"))


@dataclass(frozen=True)
class QuantizationSpec:
    step: ExactNumber | Mapping[str, Any]
    origin: ExactNumber | Mapping[str, Any] = field(default_factory=lambda: ExactNumber.integer(0))
    rounding_rule: str = "EXACT"

    def __post_init__(self) -> None:
        step = self.step if isinstance(self.step, ExactNumber) else ExactNumber.from_dict(self.step)
        origin = self.origin if isinstance(self.origin, ExactNumber) else ExactNumber.from_dict(self.origin)
        rule = _required_text("rounding_rule", self.rounding_rule).upper()
        if not step.is_positive():
            raise ValueError("quantity quantization step must be strictly positive")
        if rule not in ROUNDING_RULES:
            raise ValueError(f"unsupported quantity rounding rule: {rule}")
        object.__setattr__(self, "step", step)
        object.__setattr__(self, "origin", origin)
        object.__setattr__(self, "rounding_rule", rule)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "step": self.step.identity_payload(),
            "origin": self.origin.identity_payload(),
            "rounding_rule": self.rounding_rule,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuantizationSpec":
        return cls(
            ExactNumber.from_dict(value["step"]),
            ExactNumber.from_dict(value.get("origin") or ExactNumber.integer(0).to_dict()),
            str(value.get("rounding_rule") or "EXACT"),
        )


@dataclass(frozen=True)
class PrecisionSpec:
    kind: str
    digits: int

    def __post_init__(self) -> None:
        kind = _required_text("precision kind", self.kind).upper()
        if kind not in PRECISION_KINDS:
            raise ValueError(f"unsupported quantity precision kind: {kind}")
        if isinstance(self.digits, bool) or not isinstance(self.digits, int) or self.digits < 0:
            raise ValueError("quantity source precision digits must be a non-negative integer")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "digits", int(self.digits))

    def identity_payload(self) -> dict[str, Any]:
        return {"kind": self.kind, "digits": self.digits}

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PrecisionSpec":
        return cls(str(value["kind"]), int(value["digits"]))


QuantityValue = ExactNumber | IntervalValue | MeasuredValue


def _quantity_value(representation: str, value: QuantityValue | Mapping[str, Any]) -> QuantityValue:
    if representation in {"INTEGER", "RATIONAL", "DECIMAL"}:
        item = value if isinstance(value, ExactNumber) else ExactNumber.from_dict(value)
        if item.representation != representation:
            raise ValueError("quantity representation must match exact scalar representation")
        return item
    if representation == "INTERVAL":
        if isinstance(value, IntervalValue):
            return value
        return IntervalValue.from_dict(value)
    if representation == "MEASURED":
        if isinstance(value, MeasuredValue):
            return value
        return MeasuredValue.from_dict(value)
    raise ValueError(f"unsupported quantity representation: {representation}")


def _convert_interval(value: IntervalValue, binding: UnitBinding) -> IntervalValue:
    return IntervalValue(
        binding.convert_number(value.lower),
        binding.convert_number(value.upper),
        value.lower_inclusive,
        value.upper_inclusive,
    )


def _convert_measured(value: MeasuredValue, binding: UnitBinding) -> MeasuredValue:
    return MeasuredValue(
        binding.convert_number(value.nominal),
        _convert_interval(value.uncertainty_interval, binding),
        value.uncertainty_reference,
        value.measurement_kind,
    )


def _convert_tolerance(value: ToleranceSpec, binding: UnitBinding) -> ToleranceSpec:
    if value.kind == "NONE":
        return value
    if value.kind == "RELATIVE":
        return value
    if value.kind == "ABSOLUTE":
        assert value.magnitude is not None
        return ToleranceSpec("ABSOLUTE", binding.convert_delta(value.magnitude))
    assert value.lower is not None and value.upper is not None
    return ToleranceSpec(
        "ASYMMETRIC",
        lower=binding.convert_delta(value.lower),
        upper=binding.convert_delta(value.upper),
    )


@dataclass(frozen=True)
class Quantity:
    """Immutable portable engineering quantity foundation.

    ``value`` and absolute/asymmetric tolerance/quantization metadata are stated
    in ``unit.source_unit``. ``canonical_projection`` applies the explicit exact
    affine binding. Nothing in this object creates fact/effect/physical authority.
    """

    representation: str
    value: QuantityValue | Mapping[str, Any]
    dimension: DimensionVector | Mapping[str, Any]
    unit: UnitBinding | Mapping[str, Any]
    tolerance: ToleranceSpec | Mapping[str, Any] = field(default_factory=ToleranceSpec)
    quantization: QuantizationSpec | Mapping[str, Any] | None = None
    source_precision: PrecisionSpec | Mapping[str, Any] | None = None
    provenance_refs: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    quantity_id: str = ""
    contract_id: str = QUANTITY_CONTRACT_ID
    contract_version: str = QUANTITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != QUANTITY_CONTRACT_ID or self.contract_version != QUANTITY_CONTRACT_VERSION:
            raise ValueError("unsupported quantity contract")
        representation = _required_text("representation", self.representation).upper()
        if representation not in QUANTITY_REPRESENTATIONS:
            raise ValueError(f"unsupported quantity representation: {representation}")
        value = _quantity_value(representation, self.value)
        dimension = self.dimension if isinstance(self.dimension, DimensionVector) else DimensionVector.from_dict(self.dimension)
        unit = self.unit if isinstance(self.unit, UnitBinding) else UnitBinding.from_dict(self.unit)
        tolerance = self.tolerance if isinstance(self.tolerance, ToleranceSpec) else ToleranceSpec.from_dict(self.tolerance)
        quantization = None if self.quantization is None else (
            self.quantization if isinstance(self.quantization, QuantizationSpec) else QuantizationSpec.from_dict(self.quantization)
        )
        precision = None if self.source_precision is None else (
            self.source_precision if isinstance(self.source_precision, PrecisionSpec) else PrecisionSpec.from_dict(self.source_precision)
        )
        refs = tuple(
            ref if isinstance(ref, ExternalReference) else ExternalReference.from_dict(dict(ref))
            for ref in self.provenance_refs
        )
        by_fp = {ref.fingerprint: ref for ref in refs}
        if len(by_fp) != len(refs):
            raise ValueError("duplicate quantity provenance external reference")
        refs = tuple(sorted(refs, key=lambda ref: (ref.namespace, ref.external_id, ref.revision, ref.role, ref.fingerprint)))
        for ref in refs:
            _jsonable(ref.identity_payload())
        metadata = _jsonable(dict(self.metadata))

        object.__setattr__(self, "representation", representation)
        object.__setattr__(self, "value", value)
        object.__setattr__(self, "dimension", dimension)
        object.__setattr__(self, "unit", unit)
        object.__setattr__(self, "tolerance", tolerance)
        object.__setattr__(self, "quantization", quantization)
        object.__setattr__(self, "source_precision", precision)
        object.__setattr__(self, "provenance_refs", refs)
        object.__setattr__(self, "metadata", metadata)

        derived = f"quantity-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional_text(self.quantity_id)
        if supplied and supplied != derived:
            raise ValueError("quantity_id does not match canonical quantity identity")
        object.__setattr__(self, "quantity_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "representation": self.representation,
            "value": self.value.identity_payload(),
            "dimension": self.dimension.identity_payload(),
            "unit": self.unit.identity_payload(),
            "tolerance": self.tolerance.identity_payload(),
            "quantization": None if self.quantization is None else self.quantization.identity_payload(),
            "source_precision": None if self.source_precision is None else self.source_precision.identity_payload(),
            "provenance_refs": [ref.identity_payload() for ref in self.provenance_refs],
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"quantity_id": self.quantity_id, **self.identity_payload()})

    @property
    def canonical_value(self) -> QuantityValue:
        if isinstance(self.value, ExactNumber):
            return self.unit.convert_number(self.value)
        if isinstance(self.value, IntervalValue):
            return _convert_interval(self.value, self.unit)
        return _convert_measured(self.value, self.unit)

    @property
    def canonical_tolerance(self) -> ToleranceSpec:
        return _convert_tolerance(self.tolerance, self.unit)

    @property
    def canonical_quantization(self) -> QuantizationSpec | None:
        if self.quantization is None:
            return None
        return QuantizationSpec(
            self.unit.convert_delta(self.quantization.step),
            self.unit.convert_number(self.quantization.origin),
            self.quantization.rounding_rule,
        )

    def canonical_projection_payload(self) -> dict[str, Any]:
        value = self.canonical_value
        return {
            "dimension": self.dimension.identity_payload(),
            "canonical_unit": self.unit.canonical_unit,
            "representation": self.representation,
            "value": value.identity_payload(),
            "tolerance": self.canonical_tolerance.identity_payload(),
            "quantization": None if self.canonical_quantization is None else self.canonical_quantization.identity_payload(),
            "source_precision": None if self.source_precision is None else self.source_precision.identity_payload(),
        }

    @property
    def canonical_projection_fingerprint(self) -> str:
        return semantic_fingerprint(self.canonical_projection_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            "quantity_id": self.quantity_id,
            **self.identity_payload(),
            "canonical_projection": self.canonical_projection_payload(),
            "canonical_projection_fingerprint": self.canonical_projection_fingerprint,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Quantity":
        payload = deepcopy(dict(value))
        supplied_fingerprint = str(payload.pop("fingerprint", "")).strip()
        supplied_projection = payload.pop("canonical_projection", None)
        supplied_projection_fingerprint = str(payload.pop("canonical_projection_fingerprint", "")).strip()
        refs = tuple(payload.get("provenance_refs") or ())
        payload["provenance_refs"] = refs
        item = cls(**payload)
        if supplied_fingerprint and supplied_fingerprint != item.fingerprint:
            raise ValueError("quantity fingerprint does not match canonical quantity identity")
        if supplied_projection is not None and _jsonable(supplied_projection) != item.canonical_projection_payload():
            raise ValueError("quantity canonical projection does not match explicit source/unit semantics")
        if supplied_projection_fingerprint and supplied_projection_fingerprint != item.canonical_projection_fingerprint:
            raise ValueError("quantity canonical projection fingerprint mismatch")
        return item

    def dimensionally_compatible_with(self, other: "Quantity") -> bool:
        return self.dimension == other.dimension

    def canonically_compatible_with(self, other: "Quantity") -> bool:
        return self.dimension == other.dimension and self.unit.canonical_unit == other.unit.canonical_unit


def require_dimensionally_compatible(left: Quantity, right: Quantity) -> None:
    if not left.dimensionally_compatible_with(right):
        raise ValueError("dimensionally inconsistent quantities fail closed")


def require_canonically_compatible(left: Quantity, right: Quantity) -> None:
    require_dimensionally_compatible(left, right)
    if left.unit.canonical_unit != right.unit.canonical_unit:
        raise ValueError("quantities with different canonical units require an explicit translation contract")


def quantity_contract() -> dict[str, Any]:
    return {
        "contract_id": QUANTITY_CONTRACT_ID,
        "contract_version": QUANTITY_CONTRACT_VERSION,
        "stability": QUANTITY_STABILITY,
        "representations": list(QUANTITY_REPRESENTATIONS),
        "numeric_identity": "EXACT_INTEGER_RATIONAL_OR_CANONICAL_DECIMAL_NO_BINARY_FLOAT",
        "physical_dimension": "EXPLICIT_CANONICAL_INTEGER_EXPONENT_VECTOR",
        "unit_binding": "EXPLICIT_EXACT_AFFINE_SOURCE_TO_CANONICAL_TRANSFORM",
        "unit_registry": "NONE_HIDDEN_OR_MUTABLE",
        "value_basis": "SOURCE_UNIT_WITH_DETERMINISTIC_CANONICAL_PROJECTION",
        "tolerance": "EXPLICIT_NONE_ABSOLUTE_RELATIVE_OR_ASYMMETRIC",
        "quantization": "EXPLICIT_STEP_ORIGIN_AND_ROUNDING_RULE",
        "source_precision": "EXPLICIT_DECIMAL_PLACES_OR_SIGNIFICANT_DIGITS",
        "uncertainty": "MEASURED_OR_ESTIMATED_VALUES_REQUIRE_INTERVAL_AND_EXTERNAL_REFERENCE",
        "dimensional_inconsistency": "FAIL_CLOSED_BEFORE_SOLVING_OR_VERIFICATION",
        "canonical_unit_mismatch": "FAIL_CLOSED_UNLESS_EXPLICIT_TRANSLATION_CONTRACT_IS_SUPPLIED",
        "canonical_identity": "LANGUAGE_INDEPENDENT_JSON_FINGERPRINT_OVER_EXACT_TEXTUAL_NUMERICS",
        "legacy_solver_numeric_tolerance": "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION",
        "legacy_effect_capability_numeric_bounds": "UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION",
        "fact_authority": "NONE",
        "physical_state_authority": "NONE",
        "external_state_authority": "NONE",
        "effect_authority": "NONE",
        "artifact_acceptance": "NONE",
        "entity_identity_authority": "NONE",
        "hidden_wall_clock": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
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
