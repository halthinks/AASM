from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .model_features import ModelAdmissionReport, ModelFeatureSet, ProviderCapabilityManifest
from .optimization import BooleanLiteral, OptimizationConstraint, OptimizationModel, OptimizationVariable
from .semantic_result import semantic_fingerprint


DISCRETE_BOOLEAN_MODEL_CONTRACT_ID = "aasm.optimization.discrete-boolean.v1"
DISCRETE_BOOLEAN_MODEL_CONTRACT_VERSION = "0.1.0"
DISCRETE_LINEARIZATION_CONTRACT_ID = "aasm.optimization.discrete-linearization.v1"
DISCRETE_LINEARIZATION_CONTRACT_VERSION = "0.1.0"
DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID = "aasm.optimization.discrete-lowering-certificate.v1"
DISCRETE_LOWERING_CERTIFICATE_CONTRACT_VERSION = "0.1.0"
DISCRETE_IR_STABILITY = "FOUNDATION_EXPERIMENTAL"

PSEUDO_BOOLEAN_LINEARIZATION_ID = "aasm.transform.pseudo-boolean.linear.v1"
CARDINALITY_LINEARIZATION_ID = "aasm.transform.cardinality.linear.v1"
DISCRETE_LINEARIZATION_CHECKER_ID = "aasm.checker.discrete-linearization.v1"
DISCRETE_LINEARIZATION_CHECKER_VERSION = "0.1.0"

DISCRETE_CONSTRAINT_KINDS = ("PSEUDO_BOOLEAN", "CARDINALITY")
DISCRETE_TARGET_FAMILIES = ("CP_SAT", "MILP")
DISCRETE_CERTIFICATE_STATUSES = ("PASS", "FAIL")


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"discrete IR value is not JSON serializable: {type(value)!r}")


def _admission_from_dict(value: Mapping[str, Any]) -> ModelAdmissionReport:
    payload = deepcopy(dict(value))
    payload.pop("fingerprint", None)
    for name in (
        "exact_features",
        "approximate_features",
        "verifier_only_features",
        "unsupported_features",
        "reasons",
    ):
        payload[name] = tuple(payload.get(name) or ())
    return ModelAdmissionReport(**payload)


@dataclass(frozen=True)
class WeightedBooleanLiteral:
    variable_id: str
    positive: bool = True
    weight: int = 1

    def __post_init__(self) -> None:
        object.__setattr__(self, "variable_id", _required(self.variable_id, "weighted literal variable_id"))
        if isinstance(self.weight, bool) or int(self.weight) != self.weight:
            raise ValueError("pseudo-Boolean literal weight must be an integer")
        if int(self.weight) == 0:
            raise ValueError("pseudo-Boolean literal weight must be non-zero")
        object.__setattr__(self, "weight", int(self.weight))

    def to_dict(self) -> dict[str, Any]:
        return {"variable_id": self.variable_id, "positive": bool(self.positive), "weight": int(self.weight)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WeightedBooleanLiteral":
        return cls(**dict(value))


@dataclass(frozen=True)
class PseudoBooleanConstraint:
    terms: tuple[WeightedBooleanLiteral | Mapping[str, Any], ...]
    sense: str
    rhs: int
    source_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    constraint_id: str = ""

    def __post_init__(self) -> None:
        terms = tuple(row if isinstance(row, WeightedBooleanLiteral) else WeightedBooleanLiteral.from_dict(row) for row in self.terms)
        if not terms:
            raise ValueError("pseudo-Boolean constraint requires at least one term")
        keys = [(row.variable_id, row.positive) for row in terms]
        if len(keys) != len(set(keys)):
            raise ValueError("pseudo-Boolean constraint cannot repeat the same signed literal")
        if self.sense not in {"<=", ">=", "=="}:
            raise ValueError("pseudo-Boolean sense must be <=, >=, or ==")
        if isinstance(self.rhs, bool) or int(self.rhs) != self.rhs:
            raise ValueError("pseudo-Boolean rhs must be an integer")
        object.__setattr__(self, "terms", tuple(sorted(terms, key=lambda row: (row.variable_id, not row.positive))))
        object.__setattr__(self, "rhs", int(self.rhs))
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"pb-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": "PSEUDO_BOOLEAN",
            "terms": [row.to_dict() for row in self.terms],
            "sense": self.sense,
            "rhs": int(self.rhs),
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PseudoBooleanConstraint":
        payload = deepcopy(dict(value))
        payload.pop("kind", None)
        payload.pop("fingerprint", None)
        payload["terms"] = tuple(payload.get("terms") or ())
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class CardinalityConstraint:
    literals: tuple[BooleanLiteral | Mapping[str, Any], ...]
    min_count: int | None = None
    max_count: int | None = None
    source_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    constraint_id: str = ""

    def __post_init__(self) -> None:
        literals = tuple(row if isinstance(row, BooleanLiteral) else BooleanLiteral.from_dict(row) for row in self.literals)
        if not literals:
            raise ValueError("cardinality constraint requires at least one literal")
        keys = [(row.variable_id, row.positive) for row in literals]
        if len(keys) != len(set(keys)):
            raise ValueError("cardinality constraint cannot repeat the same signed literal")
        if self.min_count is None and self.max_count is None:
            raise ValueError("cardinality constraint requires min_count and/or max_count")
        minimum = None if self.min_count is None else int(self.min_count)
        maximum = None if self.max_count is None else int(self.max_count)
        if minimum is not None and (minimum < 0 or minimum > len(literals)):
            raise ValueError("cardinality min_count is outside the literal count")
        if maximum is not None and (maximum < 0 or maximum > len(literals)):
            raise ValueError("cardinality max_count is outside the literal count")
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("cardinality min_count exceeds max_count")
        object.__setattr__(self, "literals", tuple(sorted(literals, key=lambda row: (row.variable_id, not row.positive))))
        object.__setattr__(self, "min_count", minimum)
        object.__setattr__(self, "max_count", maximum)
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"card-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": "CARDINALITY",
            "literals": [row.to_dict() for row in self.literals],
            "min_count": self.min_count,
            "max_count": self.max_count,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CardinalityConstraint":
        payload = deepcopy(dict(value))
        payload.pop("kind", None)
        payload.pop("fingerprint", None)
        payload["literals"] = tuple(payload.get("literals") or ())
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class DiscreteBooleanModel:
    name: str
    variable_ids: tuple[str, ...]
    pseudo_boolean_constraints: tuple[PseudoBooleanConstraint | Mapping[str, Any], ...] = ()
    cardinality_constraints: tuple[CardinalityConstraint | Mapping[str, Any], ...] = ()
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    model_id: str = ""
    contract_id: str = DISCRETE_BOOLEAN_MODEL_CONTRACT_ID
    contract_version: str = DISCRETE_BOOLEAN_MODEL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required(self.name, "discrete model name"))
        if self.contract_id != DISCRETE_BOOLEAN_MODEL_CONTRACT_ID or self.contract_version != DISCRETE_BOOLEAN_MODEL_CONTRACT_VERSION:
            raise ValueError("unsupported discrete Boolean model contract")
        variables = _uniq(self.variable_ids)
        if not variables:
            raise ValueError("discrete Boolean model requires variables")
        pb = tuple(row if isinstance(row, PseudoBooleanConstraint) else PseudoBooleanConstraint.from_dict(row) for row in self.pseudo_boolean_constraints)
        cardinality = tuple(row if isinstance(row, CardinalityConstraint) else CardinalityConstraint.from_dict(row) for row in self.cardinality_constraints)
        if not pb and not cardinality:
            raise ValueError("discrete Boolean model requires pseudo-Boolean and/or cardinality constraints")
        constraint_ids = [row.constraint_id for row in (*pb, *cardinality)]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("discrete constraint IDs must be unique")
        known = set(variables)
        referenced = {term.variable_id for row in pb for term in row.terms} | {lit.variable_id for row in cardinality for lit in row.literals}
        missing = sorted(referenced - known)
        if missing:
            raise ValueError(f"discrete constraint references unknown variables: {missing}")
        object.__setattr__(self, "variable_ids", variables)
        object.__setattr__(self, "pseudo_boolean_constraints", tuple(sorted(pb, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "cardinality_constraints", tuple(sorted(cardinality, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "problem_revision_fingerprint", str(self.problem_revision_fingerprint).strip())
        if bool(self.problem_revision_id) != bool(self.problem_revision_fingerprint):
            raise ValueError("problem revision ID and fingerprint must be supplied together")
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.model_id:
            object.__setattr__(self, "model_id", f"discrete-model-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "name": self.name,
            "variable_ids": list(self.variable_ids),
            "pseudo_boolean_constraints": [row.to_dict() for row in self.pseudo_boolean_constraints],
            "cardinality_constraints": [row.to_dict() for row in self.cardinality_constraints],
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"model_id": self.model_id, **self.identity_payload()})

    @property
    def required_feature_ids(self) -> tuple[str, ...]:
        out = []
        if self.pseudo_boolean_constraints:
            out.append("PSEUDO_BOOLEAN")
        if self.cardinality_constraints:
            out.append("CARDINALITY")
        return tuple(out)

    def to_dict(self) -> dict[str, Any]:
        return {"model_id": self.model_id, **self.identity_payload(), "required_feature_ids": list(self.required_feature_ids), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DiscreteBooleanModel":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload.pop("required_feature_ids", None)
        payload["variable_ids"] = tuple(payload.get("variable_ids") or ())
        payload["pseudo_boolean_constraints"] = tuple(payload.get("pseudo_boolean_constraints") or ())
        payload["cardinality_constraints"] = tuple(payload.get("cardinality_constraints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class DiscreteConstraintMapping:
    source_constraint_id: str
    source_kind: str
    target_constraint_ids: tuple[str, ...]
    transformation_id: str
    source_reference_fingerprints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_constraint_id", _required(self.source_constraint_id, "source_constraint_id"))
        if self.source_kind not in DISCRETE_CONSTRAINT_KINDS:
            raise ValueError("invalid discrete source constraint kind")
        object.__setattr__(self, "target_constraint_ids", _uniq(self.target_constraint_ids))
        object.__setattr__(self, "transformation_id", _required(self.transformation_id, "transformation_id"))
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_constraint_id": self.source_constraint_id,
            "source_kind": self.source_kind,
            "target_constraint_ids": list(self.target_constraint_ids),
            "transformation_id": self.transformation_id,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
            "fingerprint": self.fingerprint,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({
            "source_constraint_id": self.source_constraint_id,
            "source_kind": self.source_kind,
            "target_constraint_ids": list(self.target_constraint_ids),
            "transformation_id": self.transformation_id,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
        })

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DiscreteConstraintMapping":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["target_constraint_ids"] = tuple(payload.get("target_constraint_ids") or ())
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class DiscreteLinearization:
    source_model: DiscreteBooleanModel | Mapping[str, Any]
    target_model: OptimizationModel | Mapping[str, Any]
    target_provider_id: str
    provider_manifest_id: str
    provider_manifest_fingerprint: str
    feature_set_id: str
    feature_set_fingerprint: str
    admission_report_id: str
    admission_report_fingerprint: str
    mappings: tuple[DiscreteConstraintMapping | Mapping[str, Any], ...]
    lowering_id: str = ""
    contract_id: str = DISCRETE_LINEARIZATION_CONTRACT_ID
    contract_version: str = DISCRETE_LINEARIZATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        source = self.source_model if isinstance(self.source_model, DiscreteBooleanModel) else DiscreteBooleanModel.from_dict(self.source_model)
        target = self.target_model if isinstance(self.target_model, OptimizationModel) else OptimizationModel.from_dict(self.target_model)
        object.__setattr__(self, "source_model", source)
        object.__setattr__(self, "target_model", target)
        if target.solver_family not in DISCRETE_TARGET_FAMILIES:
            raise ValueError("discrete linearization target must be CP_SAT or MILP")
        for name in (
            "target_provider_id",
            "provider_manifest_id",
            "provider_manifest_fingerprint",
            "feature_set_id",
            "feature_set_fingerprint",
            "admission_report_id",
            "admission_report_fingerprint",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != DISCRETE_LINEARIZATION_CONTRACT_ID or self.contract_version != DISCRETE_LINEARIZATION_CONTRACT_VERSION:
            raise ValueError("unsupported discrete linearization contract")
        mappings = tuple(row if isinstance(row, DiscreteConstraintMapping) else DiscreteConstraintMapping.from_dict(row) for row in self.mappings)
        ids = [row.source_constraint_id for row in mappings]
        if len(ids) != len(set(ids)):
            raise ValueError("each discrete source constraint may be mapped only once")
        object.__setattr__(self, "mappings", tuple(sorted(mappings, key=lambda row: row.source_constraint_id)))
        if not self.lowering_id:
            object.__setattr__(self, "lowering_id", f"discrete-linearization-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "source_model": self.source_model.to_dict(),
            "target_model": self.target_model.to_dict(),
            "target_provider_id": self.target_provider_id,
            "provider_manifest_id": self.provider_manifest_id,
            "provider_manifest_fingerprint": self.provider_manifest_fingerprint,
            "feature_set_id": self.feature_set_id,
            "feature_set_fingerprint": self.feature_set_fingerprint,
            "admission_report_id": self.admission_report_id,
            "admission_report_fingerprint": self.admission_report_fingerprint,
            "mappings": [row.to_dict() for row in self.mappings],
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"lowering_id": self.lowering_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"lowering_id": self.lowering_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DiscreteLinearization":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["mappings"] = tuple(payload.get("mappings") or ())
        return cls(**payload)


@dataclass(frozen=True)
class DiscreteLoweringCertificate:
    lowering_id: str
    lowering_fingerprint: str
    source_model_fingerprint: str
    target_model_fingerprint: str
    mapping_complete: bool
    lineage_preserved: bool
    exact: bool
    status: str
    diagnostics: tuple[str, ...] = ()
    checker_id: str = DISCRETE_LINEARIZATION_CHECKER_ID
    checker_version: str = DISCRETE_LINEARIZATION_CHECKER_VERSION
    certificate_id: str = ""
    contract_id: str = DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID
    contract_version: str = DISCRETE_LOWERING_CERTIFICATE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("lowering_id", "lowering_fingerprint", "source_model_fingerprint", "target_model_fingerprint", "checker_id", "checker_version"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID or self.contract_version != DISCRETE_LOWERING_CERTIFICATE_CONTRACT_VERSION:
            raise ValueError("unsupported discrete lowering certificate contract")
        if self.status not in DISCRETE_CERTIFICATE_STATUSES:
            raise ValueError("invalid discrete lowering certificate status")
        object.__setattr__(self, "diagnostics", _uniq(self.diagnostics))
        if self.status == "PASS" and not (self.mapping_complete and self.lineage_preserved and self.exact):
            raise ValueError("passing discrete lowering certificate requires exact complete lineage-preserving lowering")
        if not self.certificate_id:
            object.__setattr__(self, "certificate_id", f"discrete-lowering-certificate-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "lowering_id": self.lowering_id,
            "lowering_fingerprint": self.lowering_fingerprint,
            "source_model_fingerprint": self.source_model_fingerprint,
            "target_model_fingerprint": self.target_model_fingerprint,
            "mapping_complete": bool(self.mapping_complete),
            "lineage_preserved": bool(self.lineage_preserved),
            "exact": bool(self.exact),
            "status": self.status,
            "diagnostics": list(self.diagnostics),
            "checker_id": self.checker_id,
            "checker_version": self.checker_version,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"certificate_id": self.certificate_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"certificate_id": self.certificate_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def _normalize_weighted_terms(terms: Sequence[WeightedBooleanLiteral]) -> tuple[dict[str, int], int]:
    coefficients: dict[str, int] = {}
    constant = 0
    for term in terms:
        if term.positive:
            coefficients[term.variable_id] = coefficients.get(term.variable_id, 0) + term.weight
        else:
            constant += term.weight
            coefficients[term.variable_id] = coefficients.get(term.variable_id, 0) - term.weight
    return {key: value for key, value in sorted(coefficients.items()) if value != 0}, constant


def _constraint_holds(constant: int, sense: str, rhs: int) -> bool:
    if sense == "<=":
        return constant <= rhs
    if sense == ">=":
        return constant >= rhs
    return constant == rhs


def _false_constraint(variable_id: str, constraint_id: str) -> OptimizationConstraint:
    return OptimizationConstraint("LINEAR", coefficients={variable_id: 1}, sense=">=", rhs=1, constraint_id=constraint_id)


def _linear_constraint(coefficients: Mapping[str, int], constant: int, sense: str, rhs: int, constraint_id: str) -> OptimizationConstraint:
    return OptimizationConstraint("LINEAR", coefficients={key: float(value) for key, value in coefficients.items()}, sense=sense, rhs=float(rhs - constant), constraint_id=constraint_id)


def _build_expected_target(source: DiscreteBooleanModel, target_family: str) -> tuple[OptimizationModel, tuple[DiscreteConstraintMapping, ...]]:
    if target_family not in DISCRETE_TARGET_FAMILIES:
        raise ValueError(f"unsupported discrete target family: {target_family}")
    variables = [OptimizationVariable(variable_id, "BOOL") for variable_id in source.variable_ids]
    target_constraints: list[OptimizationConstraint] = []
    mappings: list[DiscreteConstraintMapping] = []
    sentinel_id = "__aasm_discrete_false"
    sentinel_added = False

    def add_relation(source_id: str, source_kind: str, coefficients: Mapping[str, int], constant: int, sense: str, rhs: int, target_id: str, transform: str, refs: tuple[str, ...]) -> str | None:
        nonlocal sentinel_added
        if coefficients:
            target_constraints.append(_linear_constraint(coefficients, constant, sense, rhs, target_id))
            return target_id
        if _constraint_holds(constant, sense, rhs):
            return None
        if not sentinel_added:
            variables.append(OptimizationVariable(sentinel_id, "BOOL", 0, 0))
            sentinel_added = True
        target_constraints.append(_false_constraint(sentinel_id, target_id))
        return target_id

    for constraint in source.pseudo_boolean_constraints:
        coefficients, constant = _normalize_weighted_terms(constraint.terms)
        target_id = f"{constraint.constraint_id}__pb_linear"
        emitted = add_relation(
            constraint.constraint_id,
            "PSEUDO_BOOLEAN",
            coefficients,
            constant,
            constraint.sense,
            constraint.rhs,
            target_id,
            PSEUDO_BOOLEAN_LINEARIZATION_ID,
            constraint.source_reference_fingerprints,
        )
        mappings.append(DiscreteConstraintMapping(
            constraint.constraint_id,
            "PSEUDO_BOOLEAN",
            () if emitted is None else (emitted,),
            PSEUDO_BOOLEAN_LINEARIZATION_ID,
            constraint.source_reference_fingerprints,
        ))

    for constraint in source.cardinality_constraints:
        weighted = tuple(WeightedBooleanLiteral(row.variable_id, row.positive, 1) for row in constraint.literals)
        coefficients, constant = _normalize_weighted_terms(weighted)
        target_ids: list[str] = []
        if constraint.min_count is not None and constraint.max_count is not None and constraint.min_count == constraint.max_count:
            target_id = f"{constraint.constraint_id}__card_exact"
            emitted = add_relation(
                constraint.constraint_id,
                "CARDINALITY",
                coefficients,
                constant,
                "==",
                constraint.min_count,
                target_id,
                CARDINALITY_LINEARIZATION_ID,
                constraint.source_reference_fingerprints,
            )
            if emitted:
                target_ids.append(emitted)
        else:
            if constraint.min_count is not None:
                target_id = f"{constraint.constraint_id}__card_min"
                emitted = add_relation(
                    constraint.constraint_id,
                    "CARDINALITY",
                    coefficients,
                    constant,
                    ">=",
                    constraint.min_count,
                    target_id,
                    CARDINALITY_LINEARIZATION_ID,
                    constraint.source_reference_fingerprints,
                )
                if emitted:
                    target_ids.append(emitted)
            if constraint.max_count is not None:
                target_id = f"{constraint.constraint_id}__card_max"
                emitted = add_relation(
                    constraint.constraint_id,
                    "CARDINALITY",
                    coefficients,
                    constant,
                    "<=",
                    constraint.max_count,
                    target_id,
                    CARDINALITY_LINEARIZATION_ID,
                    constraint.source_reference_fingerprints,
                )
                if emitted:
                    target_ids.append(emitted)
        mappings.append(DiscreteConstraintMapping(
            constraint.constraint_id,
            "CARDINALITY",
            tuple(target_ids),
            CARDINALITY_LINEARIZATION_ID,
            constraint.source_reference_fingerprints,
        ))

    target = OptimizationModel(
        f"{source.name} discrete exact linearization",
        tuple(variables),
        tuple(target_constraints),
        family=target_family,
        metadata={
            "discrete_source_model_id": source.model_id,
            "discrete_source_fingerprint": source.fingerprint,
            "semantic_fidelity": "EXACT",
        },
    )
    return target, tuple(mappings)


def lower_discrete_boolean_model(
    source_model: DiscreteBooleanModel | Mapping[str, Any],
    *,
    feature_set: ModelFeatureSet | Mapping[str, Any],
    provider_manifest: ProviderCapabilityManifest | Mapping[str, Any],
    admission_report: ModelAdmissionReport | Mapping[str, Any],
    target_family: str,
) -> tuple[DiscreteLinearization, DiscreteLoweringCertificate]:
    source = source_model if isinstance(source_model, DiscreteBooleanModel) else DiscreteBooleanModel.from_dict(source_model)
    features = feature_set if isinstance(feature_set, ModelFeatureSet) else ModelFeatureSet.from_dict(feature_set)
    manifest = provider_manifest if isinstance(provider_manifest, ProviderCapabilityManifest) else ProviderCapabilityManifest.from_dict(provider_manifest)
    admission = admission_report if isinstance(admission_report, ModelAdmissionReport) else _admission_from_dict(admission_report)
    if features.model_fingerprint != source.fingerprint:
        raise ValueError("feature set does not bind the discrete source model")
    if features.problem_revision_id:
        if features.problem_revision_id != source.problem_revision_id or features.problem_revision_fingerprint != source.problem_revision_fingerprint:
            raise ValueError("feature-set revision binding does not match discrete source model")
    declared_features = {row.feature_id for row in features.features}
    missing_features = sorted(set(source.required_feature_ids) - declared_features)
    if missing_features:
        raise ValueError(f"feature set omits required discrete features: {missing_features}")
    if admission.feature_set_id != features.feature_set_id or admission.feature_set_fingerprint != features.fingerprint:
        raise ValueError("admission report does not bind discrete feature set")
    if admission.provider_manifest_id != manifest.manifest_id or admission.provider_manifest_fingerprint != manifest.fingerprint:
        raise ValueError("admission report does not bind provider manifest")
    if not admission.admitted or not admission.exact:
        raise ValueError("discrete linearization requires exact provider admission")
    if target_family not in DISCRETE_TARGET_FAMILIES:
        raise ValueError("discrete linearization target must be CP_SAT or MILP")
    if manifest.solver_families and target_family not in manifest.solver_families:
        raise ValueError("provider manifest does not declare target solver family")
    support = manifest.support_by_feature
    required_transforms = {
        "PSEUDO_BOOLEAN": PSEUDO_BOOLEAN_LINEARIZATION_ID,
        "CARDINALITY": CARDINALITY_LINEARIZATION_ID,
    }
    for feature_id in source.required_feature_ids:
        row = support.get(feature_id)
        if row is None or row.support_level != "EXACT_TRANSLATED":
            raise ValueError(f"{feature_id} must be admitted as explicit EXACT_TRANSLATED support")
        if row.transformation_id != required_transforms[feature_id]:
            raise ValueError(f"{feature_id} transformation_id does not match AASM exact lowering")

    target, mappings = _build_expected_target(source, target_family)
    lowering = DiscreteLinearization(
        source,
        target,
        manifest.provider_id,
        manifest.manifest_id,
        manifest.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        admission.report_id,
        admission.fingerprint,
        mappings,
    )
    return lowering, verify_discrete_boolean_linearization(lowering)


def verify_discrete_boolean_linearization(lowering: DiscreteLinearization | Mapping[str, Any]) -> DiscreteLoweringCertificate:
    item = lowering if isinstance(lowering, DiscreteLinearization) else DiscreteLinearization.from_dict(lowering)
    diagnostics: list[str] = []
    expected_target, expected_mappings = _build_expected_target(item.source_model, item.target_model.solver_family)
    source_ids = {
        *(row.constraint_id for row in item.source_model.pseudo_boolean_constraints),
        *(row.constraint_id for row in item.source_model.cardinality_constraints),
    }
    mapped_ids = {row.source_constraint_id for row in item.mappings}
    mapping_complete = source_ids == mapped_ids
    if not mapping_complete:
        diagnostics.append("SOURCE_CONSTRAINT_MAPPING_MISMATCH")
    expected_mapping_payload = [row.to_dict() for row in expected_mappings]
    actual_mapping_payload = [row.to_dict() for row in item.mappings]
    if actual_mapping_payload != expected_mapping_payload:
        diagnostics.append("DISCRETE_MAPPING_PAYLOAD_MISMATCH")
        mapping_complete = False
    if item.target_model.to_dict() != expected_target.to_dict():
        diagnostics.append("TARGET_LINEARIZATION_MISMATCH")
    lineage_preserved = all(
        row.source_reference_fingerprints == next(
            source.source_reference_fingerprints
            for source in (*item.source_model.pseudo_boolean_constraints, *item.source_model.cardinality_constraints)
            if source.constraint_id == row.source_constraint_id
        )
        for row in item.mappings
        if row.source_constraint_id in source_ids
    )
    if not lineage_preserved:
        diagnostics.append("SOURCE_REFERENCE_LINEAGE_MISMATCH")
    exact = not diagnostics
    status = "PASS" if exact else "FAIL"
    return DiscreteLoweringCertificate(
        item.lowering_id,
        item.fingerprint,
        item.source_model.fingerprint,
        item.target_model.fingerprint,
        mapping_complete,
        lineage_preserved,
        exact,
        status,
        tuple(diagnostics),
    )


def discrete_ir_contract() -> dict[str, Any]:
    return {
        "model_contract_id": DISCRETE_BOOLEAN_MODEL_CONTRACT_ID,
        "model_contract_version": DISCRETE_BOOLEAN_MODEL_CONTRACT_VERSION,
        "linearization_contract_id": DISCRETE_LINEARIZATION_CONTRACT_ID,
        "linearization_contract_version": DISCRETE_LINEARIZATION_CONTRACT_VERSION,
        "certificate_contract_id": DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID,
        "certificate_contract_version": DISCRETE_LOWERING_CERTIFICATE_CONTRACT_VERSION,
        "stability": DISCRETE_IR_STABILITY,
        "source_semantics": ["PSEUDO_BOOLEAN", "CARDINALITY"],
        "target_families": list(DISCRETE_TARGET_FAMILIES),
        "pseudo_boolean_transform": PSEUDO_BOOLEAN_LINEARIZATION_ID,
        "cardinality_transform": CARDINALITY_LINEARIZATION_ID,
        "checker_id": DISCRETE_LINEARIZATION_CHECKER_ID,
        "checker_method": "INDEPENDENT_ALGEBRAIC_RECONSTRUCTION_OF_EXPECTED_LINEAR_TARGET",
        "negative_literal_semantics": "w*NOT(x)=w-w*x",
        "provider_admission": "EXACT_TRANSLATED_WITH_MATCHING_TRANSFORMATION_ID_REQUIRED",
        "lineage": "SOURCE_REFERENCE_FINGERPRINTS_PRESERVED_PER_CONSTRAINT_MAPPING",
        "approximation": "NOT_SUPPORTED_BY_THIS_CONTRACT",
        "truth_authority": "NONE",
    }


__all__ = [
    "DISCRETE_BOOLEAN_MODEL_CONTRACT_ID",
    "DISCRETE_BOOLEAN_MODEL_CONTRACT_VERSION",
    "DISCRETE_LINEARIZATION_CONTRACT_ID",
    "DISCRETE_LINEARIZATION_CONTRACT_VERSION",
    "DISCRETE_LOWERING_CERTIFICATE_CONTRACT_ID",
    "DISCRETE_LOWERING_CERTIFICATE_CONTRACT_VERSION",
    "PSEUDO_BOOLEAN_LINEARIZATION_ID",
    "CARDINALITY_LINEARIZATION_ID",
    "DISCRETE_LINEARIZATION_CHECKER_ID",
    "WeightedBooleanLiteral",
    "PseudoBooleanConstraint",
    "CardinalityConstraint",
    "DiscreteBooleanModel",
    "DiscreteConstraintMapping",
    "DiscreteLinearization",
    "DiscreteLoweringCertificate",
    "lower_discrete_boolean_model",
    "verify_discrete_boolean_linearization",
    "discrete_ir_contract",
]
