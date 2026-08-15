from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation, localcontext
from typing import Any, Mapping, Sequence

from .model_features import ModelAdmissionReport, ModelFeatureSet, ProviderCapabilityManifest
from .semantic_result import semantic_fingerprint


CONTINUOUS_MODEL_CONTRACT_ID = "aasm.optimization.continuous-model.v1"
CONTINUOUS_MODEL_CONTRACT_VERSION = "0.1.0"
CONTINUOUS_ASSIGNMENT_CONTRACT_ID = "aasm.optimization.continuous-assignment.v1"
CONTINUOUS_ASSIGNMENT_CONTRACT_VERSION = "0.1.0"
CONTINUOUS_VALIDATION_CONTRACT_ID = "aasm.optimization.continuous-validation.v1"
CONTINUOUS_VALIDATION_CONTRACT_VERSION = "0.1.0"
CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID = "aasm.optimization.continuous-provider-binding.v1"
CONTINUOUS_PROVIDER_BINDING_CONTRACT_VERSION = "0.1.0"
NUMERIC_TOLERANCE_CONTRACT_ID = "aasm.numeric.tolerance.v1"
NUMERIC_TOLERANCE_CONTRACT_VERSION = "0.1.0"
CONTINUOUS_IR_STABILITY = "FOUNDATION_EXPERIMENTAL"
CONTINUOUS_VALIDATOR_ID = "aasm.checker.continuous-assignment.v1"
CONTINUOUS_VALIDATOR_VERSION = "0.1.0"

CONTINUOUS_SENSES = ("<=", ">=", "==")
CONTINUOUS_OBJECTIVE_SENSES = ("MINIMIZE", "MAXIMIZE")


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def canonical_decimal(value: str | int | float | Decimal, *, name: str = "numeric value") -> str:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean")
    try:
        number = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} is not a valid decimal") from exc
    if not number.is_finite():
        raise ValueError(f"{name} must be finite")
    if number == 0:
        return "0"
    normalized = number.normalize()
    text = format(normalized, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _d(value: str | int | float | Decimal) -> Decimal:
    return Decimal(canonical_decimal(value))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    raise TypeError(f"continuous IR value is not JSON serializable: {type(value)!r}")


def _admission_from_dict(value: Mapping[str, Any]) -> ModelAdmissionReport:
    payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
    for name in ("exact_features", "approximate_features", "verifier_only_features", "unsupported_features", "reasons"):
        payload[name] = tuple(payload.get(name) or ())
    return ModelAdmissionReport(**payload)


@dataclass(frozen=True)
class NumericTolerancePolicy:
    absolute_tolerance: str = "0"
    relative_tolerance: str = "0"
    precision: int = 50
    policy_id: str = ""
    contract_id: str = NUMERIC_TOLERANCE_CONTRACT_ID
    contract_version: str = NUMERIC_TOLERANCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != NUMERIC_TOLERANCE_CONTRACT_ID or self.contract_version != NUMERIC_TOLERANCE_CONTRACT_VERSION:
            raise ValueError("unsupported numeric tolerance contract")
        absolute = canonical_decimal(self.absolute_tolerance, name="absolute_tolerance")
        relative = canonical_decimal(self.relative_tolerance, name="relative_tolerance")
        if _d(absolute) < 0 or _d(relative) < 0:
            raise ValueError("numeric tolerances must be non-negative")
        if isinstance(self.precision, bool) or int(self.precision) != self.precision or int(self.precision) < 28:
            raise ValueError("numeric validation precision must be an integer >= 28")
        object.__setattr__(self, "absolute_tolerance", absolute)
        object.__setattr__(self, "relative_tolerance", relative)
        object.__setattr__(self, "precision", int(self.precision))
        if not self.policy_id:
            object.__setattr__(self, "policy_id", f"numeric-tolerance-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "absolute_tolerance": self.absolute_tolerance,
            "relative_tolerance": self.relative_tolerance,
            "precision": self.precision,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"policy_id": self.policy_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"policy_id": self.policy_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NumericTolerancePolicy":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)

    def allowance(self, left: Decimal, right: Decimal) -> Decimal:
        scale = max(abs(left), abs(right), Decimal(1))
        return _d(self.absolute_tolerance) + _d(self.relative_tolerance) * scale


@dataclass(frozen=True)
class ContinuousVariable:
    variable_id: str
    lower_bound: str | None = None
    upper_bound: str | None = None
    source_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "variable_id", _required(self.variable_id, "continuous variable_id"))
        lower = None if self.lower_bound is None else canonical_decimal(self.lower_bound, name="lower_bound")
        upper = None if self.upper_bound is None else canonical_decimal(self.upper_bound, name="upper_bound")
        if lower is not None and upper is not None and _d(lower) > _d(upper):
            raise ValueError("continuous variable lower_bound exceeds upper_bound")
        object.__setattr__(self, "lower_bound", lower)
        object.__setattr__(self, "upper_bound", upper)
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
            "metadata": _jsonable(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContinuousVariable":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class LinearExpression:
    coefficients: Mapping[str, str | int | float | Decimal] = field(default_factory=dict)
    offset: str | int | float | Decimal = "0"

    def __post_init__(self) -> None:
        coefficients = {}
        for variable_id, coefficient in sorted(self.coefficients.items()):
            key = _required(str(variable_id), "linear coefficient variable_id")
            value = canonical_decimal(coefficient, name=f"linear coefficient {key}")
            if _d(value) != 0:
                coefficients[key] = value
        object.__setattr__(self, "coefficients", coefficients)
        object.__setattr__(self, "offset", canonical_decimal(self.offset, name="linear expression offset"))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"coefficients": dict(self.coefficients), "offset": self.offset}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "LinearExpression":
        return cls(**dict(value))

    def evaluate(self, values: Mapping[str, Decimal]) -> Decimal:
        out = _d(self.offset)
        for variable_id, coefficient in self.coefficients.items():
            out += _d(coefficient) * values[variable_id]
        return out


@dataclass(frozen=True)
class QuadraticTerm:
    left_variable_id: str
    right_variable_id: str
    coefficient: str | int | float | Decimal

    def __post_init__(self) -> None:
        left = _required(self.left_variable_id, "quadratic left_variable_id")
        right = _required(self.right_variable_id, "quadratic right_variable_id")
        if right < left:
            left, right = right, left
        coefficient = canonical_decimal(self.coefficient, name="quadratic coefficient")
        if _d(coefficient) == 0:
            raise ValueError("quadratic term coefficient must be non-zero")
        object.__setattr__(self, "left_variable_id", left)
        object.__setattr__(self, "right_variable_id", right)
        object.__setattr__(self, "coefficient", coefficient)

    @property
    def key(self) -> tuple[str, str]:
        return self.left_variable_id, self.right_variable_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "left_variable_id": self.left_variable_id,
            "right_variable_id": self.right_variable_id,
            "coefficient": self.coefficient,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuadraticTerm":
        return cls(**dict(value))


@dataclass(frozen=True)
class QuadraticExpression:
    linear: LinearExpression | Mapping[str, Any] = field(default_factory=LinearExpression)
    terms: tuple[QuadraticTerm | Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        linear = self.linear if isinstance(self.linear, LinearExpression) else LinearExpression.from_dict(self.linear)
        terms = tuple(row if isinstance(row, QuadraticTerm) else QuadraticTerm.from_dict(row) for row in self.terms)
        keys = [row.key for row in terms]
        if len(keys) != len(set(keys)):
            raise ValueError("quadratic expression cannot repeat a canonical variable pair")
        object.__setattr__(self, "linear", linear)
        object.__setattr__(self, "terms", tuple(sorted(terms, key=lambda row: row.key)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    @property
    def is_quadratic(self) -> bool:
        return bool(self.terms)

    def to_dict(self) -> dict[str, Any]:
        return {"linear": self.linear.to_dict(), "terms": [row.to_dict() for row in self.terms]}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuadraticExpression":
        payload = deepcopy(dict(value)); payload["terms"] = tuple(payload.get("terms") or ()); return cls(**payload)

    def evaluate(self, values: Mapping[str, Decimal]) -> Decimal:
        out = self.linear.evaluate(values)
        for term in self.terms:
            out += _d(term.coefficient) * values[term.left_variable_id] * values[term.right_variable_id]
        return out


@dataclass(frozen=True)
class QuadraticConstraint:
    expression: QuadraticExpression | Mapping[str, Any]
    sense: str
    rhs: str | int | float | Decimal
    source_reference_fingerprints: tuple[str, ...] = ()
    constraint_id: str = ""

    def __post_init__(self) -> None:
        expression = self.expression if isinstance(self.expression, QuadraticExpression) else QuadraticExpression.from_dict(self.expression)
        if self.sense not in CONTINUOUS_SENSES:
            raise ValueError("quadratic constraint sense must be <=, >=, or ==")
        object.__setattr__(self, "expression", expression)
        object.__setattr__(self, "rhs", canonical_decimal(self.rhs, name="quadratic constraint rhs"))
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"quadratic-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": "QUADRATIC",
            "expression": self.expression.to_dict(),
            "sense": self.sense,
            "rhs": self.rhs,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuadraticConstraint":
        payload = deepcopy(dict(value)); payload.pop("kind", None); payload.pop("fingerprint", None)
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SecondOrderConeConstraint:
    components: tuple[LinearExpression | Mapping[str, Any], ...]
    upper: LinearExpression | Mapping[str, Any]
    source_reference_fingerprints: tuple[str, ...] = ()
    constraint_id: str = ""

    def __post_init__(self) -> None:
        components = tuple(row if isinstance(row, LinearExpression) else LinearExpression.from_dict(row) for row in self.components)
        if not components:
            raise ValueError("second-order cone requires at least one norm component")
        upper = self.upper if isinstance(self.upper, LinearExpression) else LinearExpression.from_dict(self.upper)
        object.__setattr__(self, "components", components)
        object.__setattr__(self, "upper", upper)
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"conic-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": "SECOND_ORDER_CONE",
            "components": [row.to_dict() for row in self.components],
            "upper": self.upper.to_dict(),
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SecondOrderConeConstraint":
        payload = deepcopy(dict(value)); payload.pop("kind", None); payload.pop("fingerprint", None)
        payload["components"] = tuple(payload.get("components") or ())
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class QuadraticObjective:
    sense: str
    expression: QuadraticExpression | Mapping[str, Any]
    source_reference_fingerprints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.sense not in CONTINUOUS_OBJECTIVE_SENSES:
            raise ValueError("quadratic objective sense must be MINIMIZE or MAXIMIZE")
        expression = self.expression if isinstance(self.expression, QuadraticExpression) else QuadraticExpression.from_dict(self.expression)
        object.__setattr__(self, "expression", expression)
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {"sense": self.sense, "expression": self.expression.to_dict(), "source_reference_fingerprints": list(self.source_reference_fingerprints)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "QuadraticObjective":
        payload = deepcopy(dict(value)); payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ()); return cls(**payload)


@dataclass(frozen=True)
class ContinuousModel:
    name: str
    variables: tuple[ContinuousVariable | Mapping[str, Any], ...]
    quadratic_constraints: tuple[QuadraticConstraint | Mapping[str, Any], ...] = ()
    conic_constraints: tuple[SecondOrderConeConstraint | Mapping[str, Any], ...] = ()
    objective: QuadraticObjective | Mapping[str, Any] | None = None
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    model_id: str = ""
    contract_id: str = CONTINUOUS_MODEL_CONTRACT_ID
    contract_version: str = CONTINUOUS_MODEL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required(self.name, "continuous model name"))
        if self.contract_id != CONTINUOUS_MODEL_CONTRACT_ID or self.contract_version != CONTINUOUS_MODEL_CONTRACT_VERSION:
            raise ValueError("unsupported continuous model contract")
        variables = tuple(row if isinstance(row, ContinuousVariable) else ContinuousVariable.from_dict(row) for row in self.variables)
        ids = [row.variable_id for row in variables]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("continuous variable IDs must be non-empty and unique")
        known = set(ids)
        quadratic = tuple(row if isinstance(row, QuadraticConstraint) else QuadraticConstraint.from_dict(row) for row in self.quadratic_constraints)
        conic = tuple(row if isinstance(row, SecondOrderConeConstraint) else SecondOrderConeConstraint.from_dict(row) for row in self.conic_constraints)
        objective = self.objective
        if objective is not None and not isinstance(objective, QuadraticObjective):
            objective = QuadraticObjective.from_dict(objective)
        referenced: set[str] = set()
        for row in quadratic:
            referenced.update(row.expression.linear.coefficients)
            for term in row.expression.terms:
                referenced.update(term.key)
        for row in conic:
            for expr in (*row.components, row.upper):
                referenced.update(expr.coefficients)
        if objective is not None:
            referenced.update(objective.expression.linear.coefficients)
            for term in objective.expression.terms:
                referenced.update(term.key)
        missing = sorted(referenced - known)
        if missing:
            raise ValueError(f"continuous model references unknown variables: {missing}")
        constraint_ids = [row.constraint_id for row in (*quadratic, *conic)]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("continuous constraint IDs must be unique")
        object.__setattr__(self, "variables", tuple(sorted(variables, key=lambda row: row.variable_id)))
        object.__setattr__(self, "quadratic_constraints", tuple(sorted(quadratic, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "conic_constraints", tuple(sorted(conic, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "objective", objective)
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "problem_revision_fingerprint", str(self.problem_revision_fingerprint).strip())
        if bool(self.problem_revision_id) != bool(self.problem_revision_fingerprint):
            raise ValueError("problem revision ID and fingerprint must be supplied together")
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.model_id:
            object.__setattr__(self, "model_id", f"continuous-model-{semantic_fingerprint(self.identity_payload())[:20]}")

    @property
    def required_feature_ids(self) -> tuple[str, ...]:
        features = ["LINEAR_REAL"]
        if self.quadratic_constraints or (self.objective is not None and self.objective.expression.is_quadratic):
            features.append("QUADRATIC")
        if self.conic_constraints:
            features.append("CONIC")
        return tuple(features)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "name": self.name,
            "variables": [row.to_dict() for row in self.variables],
            "quadratic_constraints": [row.to_dict() for row in self.quadratic_constraints],
            "conic_constraints": [row.to_dict() for row in self.conic_constraints],
            "objective": None if self.objective is None else self.objective.to_dict(),
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"model_id": self.model_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"model_id": self.model_id, **self.identity_payload(), "required_feature_ids": list(self.required_feature_ids), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContinuousModel":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); payload.pop("required_feature_ids", None)
        payload["variables"] = tuple(payload.get("variables") or ())
        payload["quadratic_constraints"] = tuple(payload.get("quadratic_constraints") or ())
        payload["conic_constraints"] = tuple(payload.get("conic_constraints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class ContinuousAssignment:
    model_id: str
    model_fingerprint: str
    values: Mapping[str, str | int | float | Decimal]
    assignment_id: str = ""
    contract_id: str = CONTINUOUS_ASSIGNMENT_CONTRACT_ID
    contract_version: str = CONTINUOUS_ASSIGNMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _required(self.model_id, "assignment model_id"))
        object.__setattr__(self, "model_fingerprint", _required(self.model_fingerprint, "assignment model_fingerprint"))
        if self.contract_id != CONTINUOUS_ASSIGNMENT_CONTRACT_ID or self.contract_version != CONTINUOUS_ASSIGNMENT_CONTRACT_VERSION:
            raise ValueError("unsupported continuous assignment contract")
        values = {str(key): canonical_decimal(value, name=f"assignment value {key}") for key, value in sorted(self.values.items())}
        object.__setattr__(self, "values", values)
        if not self.assignment_id:
            object.__setattr__(self, "assignment_id", f"continuous-assignment-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "model_id": self.model_id,
            "model_fingerprint": self.model_fingerprint,
            "values": dict(self.values),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assignment_id": self.assignment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"assignment_id": self.assignment_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContinuousAssignment":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class ContinuousValidationReport:
    model_fingerprint: str
    assignment_fingerprint: str
    tolerance_policy_id: str
    tolerance_policy_fingerprint: str
    valid: bool
    violations: tuple[Mapping[str, Any], ...] = ()
    objective_value: str | None = None
    validator_id: str = CONTINUOUS_VALIDATOR_ID
    validator_version: str = CONTINUOUS_VALIDATOR_VERSION
    report_id: str = ""
    contract_id: str = CONTINUOUS_VALIDATION_CONTRACT_ID
    contract_version: str = CONTINUOUS_VALIDATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("model_fingerprint", "assignment_fingerprint", "tolerance_policy_id", "tolerance_policy_fingerprint"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != CONTINUOUS_VALIDATION_CONTRACT_ID or self.contract_version != CONTINUOUS_VALIDATION_CONTRACT_VERSION:
            raise ValueError("unsupported continuous validation contract")
        normalized = tuple(sorted((_jsonable(dict(row)) for row in self.violations), key=lambda row: (str(row.get("code")), str(row.get("constraint_id")), str(row.get("variable_id")))))
        object.__setattr__(self, "violations", normalized)
        object.__setattr__(self, "objective_value", None if self.objective_value is None else canonical_decimal(self.objective_value))
        if bool(self.valid) != (not normalized):
            raise ValueError("continuous valid flag must match absence of violations")
        if not self.report_id:
            object.__setattr__(self, "report_id", f"continuous-validation-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "model_fingerprint": self.model_fingerprint,
            "assignment_fingerprint": self.assignment_fingerprint,
            "tolerance_policy_id": self.tolerance_policy_id,
            "tolerance_policy_fingerprint": self.tolerance_policy_fingerprint,
            "valid": bool(self.valid),
            "violations": [_jsonable(row) for row in self.violations],
            "objective_value": self.objective_value,
            "validator_id": self.validator_id,
            "validator_version": self.validator_version,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"report_id": self.report_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"report_id": self.report_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def _relation_satisfied(left: Decimal, sense: str, right: Decimal, allowance: Decimal) -> bool:
    if sense == "<=":
        return left <= right + allowance
    if sense == ">=":
        return left + allowance >= right
    return abs(left - right) <= allowance


def validate_continuous_assignment(
    model: ContinuousModel | Mapping[str, Any],
    assignment: ContinuousAssignment | Mapping[str, Any],
    tolerance_policy: NumericTolerancePolicy | Mapping[str, Any],
) -> ContinuousValidationReport:
    source = model if isinstance(model, ContinuousModel) else ContinuousModel.from_dict(model)
    item = assignment if isinstance(assignment, ContinuousAssignment) else ContinuousAssignment.from_dict(assignment)
    policy = tolerance_policy if isinstance(tolerance_policy, NumericTolerancePolicy) else NumericTolerancePolicy.from_dict(tolerance_policy)
    violations: list[dict[str, Any]] = []
    if item.model_id != source.model_id or item.model_fingerprint != source.fingerprint:
        violations.append({"code": "MODEL_BINDING_MISMATCH"})
        return ContinuousValidationReport(source.fingerprint, item.fingerprint, policy.policy_id, policy.fingerprint, False, tuple(violations))
    variable_ids = {row.variable_id for row in source.variables}
    if set(item.values) != variable_ids:
        violations.append({"code": "ASSIGNMENT_VARIABLE_SET_MISMATCH", "missing": sorted(variable_ids - set(item.values)), "unexpected": sorted(set(item.values) - variable_ids)})
        return ContinuousValidationReport(source.fingerprint, item.fingerprint, policy.policy_id, policy.fingerprint, False, tuple(violations))
    values = {key: _d(value) for key, value in item.values.items()}
    variables = {row.variable_id: row for row in source.variables}
    with localcontext() as ctx:
        ctx.prec = policy.precision
        for variable_id, variable in variables.items():
            value = values[variable_id]
            if variable.lower_bound is not None:
                lower = _d(variable.lower_bound)
                allowance = policy.allowance(value, lower)
                if value + allowance < lower:
                    violations.append({"code": "LOWER_BOUND_VIOLATION", "variable_id": variable_id, "value": canonical_decimal(value), "lower_bound": variable.lower_bound, "allowance": canonical_decimal(allowance)})
            if variable.upper_bound is not None:
                upper = _d(variable.upper_bound)
                allowance = policy.allowance(value, upper)
                if value > upper + allowance:
                    violations.append({"code": "UPPER_BOUND_VIOLATION", "variable_id": variable_id, "value": canonical_decimal(value), "upper_bound": variable.upper_bound, "allowance": canonical_decimal(allowance)})
        for constraint in source.quadratic_constraints:
            left = constraint.expression.evaluate(values)
            right = _d(constraint.rhs)
            allowance = policy.allowance(left, right)
            if not _relation_satisfied(left, constraint.sense, right, allowance):
                violations.append({"code": "QUADRATIC_CONSTRAINT_VIOLATION", "constraint_id": constraint.constraint_id, "left": canonical_decimal(left), "sense": constraint.sense, "right": constraint.rhs, "allowance": canonical_decimal(allowance)})
        for constraint in source.conic_constraints:
            component_values = [component.evaluate(values) for component in constraint.components]
            norm_squared = sum((value * value for value in component_values), Decimal(0))
            norm = norm_squared.sqrt()
            upper = constraint.upper.evaluate(values)
            allowance = policy.allowance(norm, upper)
            if upper < -allowance or norm > upper + allowance:
                violations.append({"code": "SECOND_ORDER_CONE_VIOLATION", "constraint_id": constraint.constraint_id, "norm": canonical_decimal(norm), "upper": canonical_decimal(upper), "allowance": canonical_decimal(allowance)})
        objective_value = None if source.objective is None else canonical_decimal(source.objective.expression.evaluate(values))
    return ContinuousValidationReport(
        source.fingerprint,
        item.fingerprint,
        policy.policy_id,
        policy.fingerprint,
        not violations,
        tuple(violations),
        objective_value,
    )


@dataclass(frozen=True)
class ContinuousProviderBinding:
    model_id: str
    model_fingerprint: str
    feature_set_id: str
    feature_set_fingerprint: str
    provider_manifest_id: str
    provider_manifest_fingerprint: str
    admission_report_id: str
    admission_report_fingerprint: str
    provider_id: str
    tolerance_policy_id: str
    tolerance_policy_fingerprint: str
    environment_fingerprint: str = ""
    binding_id: str = ""
    contract_id: str = CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID
    contract_version: str = CONTINUOUS_PROVIDER_BINDING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("model_id", "model_fingerprint", "feature_set_id", "feature_set_fingerprint", "provider_manifest_id", "provider_manifest_fingerprint", "admission_report_id", "admission_report_fingerprint", "provider_id", "tolerance_policy_id", "tolerance_policy_fingerprint"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID or self.contract_version != CONTINUOUS_PROVIDER_BINDING_CONTRACT_VERSION:
            raise ValueError("unsupported continuous provider binding contract")
        object.__setattr__(self, "environment_fingerprint", str(self.environment_fingerprint).strip())
        if not self.binding_id:
            object.__setattr__(self, "binding_id", f"continuous-provider-binding-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "model_id": self.model_id,
            "model_fingerprint": self.model_fingerprint,
            "feature_set_id": self.feature_set_id,
            "feature_set_fingerprint": self.feature_set_fingerprint,
            "provider_manifest_id": self.provider_manifest_id,
            "provider_manifest_fingerprint": self.provider_manifest_fingerprint,
            "admission_report_id": self.admission_report_id,
            "admission_report_fingerprint": self.admission_report_fingerprint,
            "provider_id": self.provider_id,
            "tolerance_policy_id": self.tolerance_policy_id,
            "tolerance_policy_fingerprint": self.tolerance_policy_fingerprint,
            "environment_fingerprint": self.environment_fingerprint,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"binding_id": self.binding_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def bind_continuous_provider(
    model: ContinuousModel | Mapping[str, Any],
    *,
    feature_set: ModelFeatureSet | Mapping[str, Any],
    provider_manifest: ProviderCapabilityManifest | Mapping[str, Any],
    admission_report: ModelAdmissionReport | Mapping[str, Any],
    tolerance_policy: NumericTolerancePolicy | Mapping[str, Any],
) -> ContinuousProviderBinding:
    source = model if isinstance(model, ContinuousModel) else ContinuousModel.from_dict(model)
    features = feature_set if isinstance(feature_set, ModelFeatureSet) else ModelFeatureSet.from_dict(feature_set)
    manifest = provider_manifest if isinstance(provider_manifest, ProviderCapabilityManifest) else ProviderCapabilityManifest.from_dict(provider_manifest)
    admission = admission_report if isinstance(admission_report, ModelAdmissionReport) else _admission_from_dict(admission_report)
    policy = tolerance_policy if isinstance(tolerance_policy, NumericTolerancePolicy) else NumericTolerancePolicy.from_dict(tolerance_policy)
    if features.model_fingerprint != source.fingerprint:
        raise ValueError("continuous feature set does not bind model fingerprint")
    if source.problem_revision_id:
        if features.problem_revision_id != source.problem_revision_id or features.problem_revision_fingerprint != source.problem_revision_fingerprint:
            raise ValueError("continuous feature-set revision binding mismatch")
    declared = {row.feature_id for row in features.features}
    missing = sorted(set(source.required_feature_ids) - declared)
    if missing:
        raise ValueError(f"continuous feature set omits required features: {missing}")
    if admission.feature_set_id != features.feature_set_id or admission.feature_set_fingerprint != features.fingerprint:
        raise ValueError("continuous admission report does not bind feature set")
    if admission.provider_manifest_id != manifest.manifest_id or admission.provider_manifest_fingerprint != manifest.fingerprint:
        raise ValueError("continuous admission report does not bind provider manifest")
    if not admission.admitted or not admission.exact:
        raise ValueError("continuous provider binding requires exact feature admission")
    support = manifest.support_by_feature
    for feature_id in source.required_feature_ids:
        row = support.get(feature_id)
        if row is None or row.support_level != "EXACT_NATIVE":
            raise ValueError(f"continuous foundation requires EXACT_NATIVE {feature_id} provider support")
    return ContinuousProviderBinding(
        source.model_id,
        source.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        manifest.manifest_id,
        manifest.fingerprint,
        admission.report_id,
        admission.fingerprint,
        manifest.provider_id,
        policy.policy_id,
        policy.fingerprint,
        manifest.environment_fingerprint,
    )


def continuous_ir_contract() -> dict[str, Any]:
    return {
        "model_contract_id": CONTINUOUS_MODEL_CONTRACT_ID,
        "model_contract_version": CONTINUOUS_MODEL_CONTRACT_VERSION,
        "assignment_contract_id": CONTINUOUS_ASSIGNMENT_CONTRACT_ID,
        "validation_contract_id": CONTINUOUS_VALIDATION_CONTRACT_ID,
        "provider_binding_contract_id": CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID,
        "numeric_tolerance_contract_id": NUMERIC_TOLERANCE_CONTRACT_ID,
        "stability": CONTINUOUS_IR_STABILITY,
        "number_encoding": "CANONICAL_FINITE_DECIMAL_STRINGS",
        "structural_semantics": ["LINEAR_REAL", "QUADRATIC", "SECOND_ORDER_CONE"],
        "numeric_validation": "DECIMAL_ASSIGNMENT_EVALUATION_WITH_EXPLICIT_ABSOLUTE_AND_RELATIVE_TOLERANCE",
        "provider_admission": "REQUIRED_FEATURES_EXACT_NATIVE_ONLY_IN_THIS_FOUNDATION",
        "execution_adapter": "NOT_CLAIMED_BY_THIS_FOUNDATION",
        "optimality_proof": "NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION",
        "global_optimality": "NOT_INFERRED_FROM_FEASIBILITY_OR_OBJECTIVE_VALUE",
        "truth_authority": "NONE",
    }


__all__ = [
    "CONTINUOUS_MODEL_CONTRACT_ID",
    "CONTINUOUS_MODEL_CONTRACT_VERSION",
    "CONTINUOUS_ASSIGNMENT_CONTRACT_ID",
    "CONTINUOUS_VALIDATION_CONTRACT_ID",
    "CONTINUOUS_PROVIDER_BINDING_CONTRACT_ID",
    "NUMERIC_TOLERANCE_CONTRACT_ID",
    "CONTINUOUS_VALIDATOR_ID",
    "canonical_decimal",
    "NumericTolerancePolicy",
    "ContinuousVariable",
    "LinearExpression",
    "QuadraticTerm",
    "QuadraticExpression",
    "QuadraticConstraint",
    "SecondOrderConeConstraint",
    "QuadraticObjective",
    "ContinuousModel",
    "ContinuousAssignment",
    "ContinuousValidationReport",
    "ContinuousProviderBinding",
    "validate_continuous_assignment",
    "bind_continuous_provider",
    "continuous_ir_contract",
]
