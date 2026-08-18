from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .semantic_evolution import ExternalReference
from .semantic_projection import SemanticSubjectRef
from .semantic_result import semantic_fingerprint
from .trace_conformance import KNOWN_EVENT_TYPES, TRANSITION_CLASSES, project_trace


UNCERTAINTY_CONTRACT_ID = "aasm.uncertainty.v1"
UNCERTAINTY_CONTRACT_VERSION = "0.1.0"
SCENARIO_CONTRACT_ID = "aasm.scenario.v1"
SCENARIO_CONTRACT_VERSION = "0.1.0"
TRACE_PROPERTY_CONTRACT_ID = "aasm.trace-property.v1"
TRACE_PROPERTY_CONTRACT_VERSION = "0.1.0"
TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID = "aasm.trace-property.assessment.v1"
TRACE_PROPERTY_ASSESSMENT_CONTRACT_VERSION = "0.1.0"
UNCERTAINTY_SCENARIO_TRACE_STABILITY = "FOUNDATION_EXPERIMENTAL"

UNCERTAINTY_FORMS = (
    "EXACT",
    "INTERVAL",
    "SCENARIOS",
    "DISTRIBUTION_REFERENCE",
    "EMPIRICAL_SAMPLES",
    "UNKNOWN_BOUNDED",
    "UNKNOWN_UNBOUNDED",
)
SCENARIO_BINDING_KINDS = ("LITERAL", "SEMANTIC_REF")
TRACE_PROPERTY_KINDS = (
    "OCCURS",
    "NEVER_OCCURS",
    "PRECEDES",
    "SEQUENCE",
    "BOUNDED_EVENTUALLY_STEPS",
)
TRACE_COMPLETENESS = ("COMPLETE", "PREFIX", "UNKNOWN")
TRACE_PROPERTY_STATUSES = ("PASS", "FAIL", "INCONCLUSIVE", "UNSUPPORTED")
TRACE_INVARIANT_CLASSIFICATION = "DYNAMIC_KERNEL"

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_ALLOWED_LITERAL_TYPES = (str, int, bool, type(None))


def _required(name: str, value: Any) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    normalized = _required(name, value).lower()
    if not _SHA256.fullmatch(normalized):
        raise ValueError(f"{name} must be a lowercase 64-hex SHA-256 digest")
    return normalized


def _uniq(values: Sequence[Any]) -> tuple[str, ...]:
    return tuple(sorted({_required("list value", value) for value in values}))


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
        raise TypeError(
            "binary floating-point values are forbidden in uncertainty/scenario/trace portable identity"
        )
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(
        f"uncertainty/scenario/trace value is not JSON serializable: {type(value)!r}"
    )


def _subject(value: SemanticSubjectRef | Mapping[str, Any]) -> SemanticSubjectRef:
    return value if isinstance(value, SemanticSubjectRef) else SemanticSubjectRef.from_dict(value)


def _subject_refs(
    values: Sequence[SemanticSubjectRef | Mapping[str, Any]], *, required_type: str = ""
) -> tuple[SemanticSubjectRef, ...]:
    refs = tuple(_subject(value) for value in values)
    fingerprints = [ref.fingerprint for ref in refs]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("duplicate semantic subject reference")
    if required_type:
        for ref in refs:
            if ref.semantic_type_id != required_type:
                raise ValueError(
                    f"semantic subject reference must use {required_type}, got {ref.semantic_type_id}"
                )
    return tuple(
        sorted(
            refs,
            key=lambda ref: (
                ref.semantic_type_id,
                ref.object_id,
                ref.fingerprint,
                ref.revision_id,
                ref.revision_fingerprint,
            ),
        )
    )


def _external_ref(
    value: ExternalReference | Mapping[str, Any] | None,
) -> ExternalReference | None:
    if value is None:
        return None
    return value if isinstance(value, ExternalReference) else ExternalReference.from_dict(value)


def _external_refs(
    values: Sequence[ExternalReference | Mapping[str, Any]],
) -> tuple[ExternalReference, ...]:
    refs = tuple(
        value if isinstance(value, ExternalReference) else ExternalReference.from_dict(value)
        for value in values
    )
    fingerprints = [ref.fingerprint for ref in refs]
    if len(fingerprints) != len(set(fingerprints)):
        raise ValueError("duplicate external reference")
    return tuple(
        sorted(
            refs,
            key=lambda ref: (
                ref.namespace,
                ref.external_id,
                ref.revision,
                ref.role,
                ref.fingerprint,
            ),
        )
    )


def _revision_pair(
    revision_id: Any, revision_fingerprint: Any, *, prefix: str
) -> tuple[str, str]:
    rid = _optional(revision_id)
    rfp = _optional(revision_fingerprint)
    if bool(rid) != bool(rfp):
        raise ValueError(
            f"{prefix} revision_id and revision_fingerprint must both be present or both be absent"
        )
    if rfp:
        rfp = _sha256(f"{prefix} revision_fingerprint", rfp)
    return rid, rfp


@dataclass(frozen=True)
class ScenarioBinding:
    parameter_id: str
    binding_kind: str
    literal_value: Any = None
    value_ref: SemanticSubjectRef | Mapping[str, Any] | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        parameter_id = _required("scenario parameter_id", self.parameter_id)
        kind = _required("scenario binding_kind", self.binding_kind).upper()
        if kind not in SCENARIO_BINDING_KINDS:
            raise ValueError(f"unsupported scenario binding kind: {kind}")

        ref = None if self.value_ref is None else _subject(self.value_ref)
        if kind == "LITERAL":
            if ref is not None:
                raise ValueError("LITERAL scenario binding cannot carry value_ref")
            if isinstance(self.literal_value, float) or not isinstance(
                self.literal_value, _ALLOWED_LITERAL_TYPES
            ):
                raise TypeError(
                    "scenario literals are limited to string/integer/boolean/null; "
                    "numeric engineering values must use aasm.quantity.v1 references"
                )
            literal = _jsonable(self.literal_value)
        else:
            if ref is None:
                raise ValueError("SEMANTIC_REF scenario binding requires value_ref")
            if self.literal_value is not None:
                raise ValueError(
                    "SEMANTIC_REF scenario binding cannot carry literal_value"
                )
            literal = None

        object.__setattr__(self, "parameter_id", parameter_id)
        object.__setattr__(self, "binding_kind", kind)
        object.__setattr__(self, "literal_value", literal)
        object.__setattr__(self, "value_ref", ref)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "parameter_id": self.parameter_id,
            "binding_kind": self.binding_kind,
            "literal_value": self.literal_value,
            "value_ref": None if self.value_ref is None else self.value_ref.identity_payload(),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScenarioBinding":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("scenario binding fingerprint mismatch")
        return item


@dataclass(frozen=True)
class Scenario:
    scenario_name: str
    base_problem_revision_id: str
    base_problem_revision_fingerprint: str
    bindings: tuple[ScenarioBinding | Mapping[str, Any], ...]
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    evidence_ids: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    scenario_id: str = ""
    contract_id: str = SCENARIO_CONTRACT_ID
    contract_version: str = SCENARIO_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != SCENARIO_CONTRACT_ID
            or self.contract_version != SCENARIO_CONTRACT_VERSION
        ):
            raise ValueError("unsupported scenario contract")

        name = _required("scenario_name", self.scenario_name)
        revision_id = _required(
            "scenario base_problem_revision_id", self.base_problem_revision_id
        )
        revision_fingerprint = _sha256(
            "scenario base_problem_revision_fingerprint",
            self.base_problem_revision_fingerprint,
        )
        bindings = tuple(
            binding
            if isinstance(binding, ScenarioBinding)
            else ScenarioBinding.from_dict(binding)
            for binding in self.bindings
        )
        if not bindings:
            raise ValueError("scenario requires at least one explicit binding")
        parameter_ids = [binding.parameter_id for binding in bindings]
        if len(parameter_ids) != len(set(parameter_ids)):
            raise ValueError("scenario parameter_id values must be unique")
        bindings = tuple(sorted(bindings, key=lambda binding: binding.parameter_id))

        refs = _external_refs(self.external_references)
        evidence_ids = _uniq(self.evidence_ids)
        tags = _uniq(self.tags)
        metadata = _jsonable(dict(self.metadata))

        object.__setattr__(self, "scenario_name", name)
        object.__setattr__(self, "base_problem_revision_id", revision_id)
        object.__setattr__(self, "base_problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "bindings", bindings)
        object.__setattr__(self, "external_references", refs)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "tags", tags)
        object.__setattr__(self, "metadata", metadata)

        derived = f"scenario-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.scenario_id)
        if supplied and supplied != derived:
            raise ValueError("scenario_id does not match canonical scenario identity")
        object.__setattr__(self, "scenario_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "scenario_name": self.scenario_name,
            "base_problem_revision_id": self.base_problem_revision_id,
            "base_problem_revision_fingerprint": self.base_problem_revision_fingerprint,
            "bindings": [binding.identity_payload() for binding in self.bindings],
            "external_references": [reference.to_dict() for reference in self.external_references],
            "evidence_ids": list(self.evidence_ids),
            "tags": list(self.tags),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"scenario_id": self.scenario_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Scenario":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["bindings"] = tuple(payload.get("bindings") or ())
        payload["external_references"] = tuple(payload.get("external_references") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        payload["tags"] = tuple(payload.get("tags") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("scenario fingerprint mismatch")
        return item

    @property
    def semantic_ref(self) -> SemanticSubjectRef:
        return SemanticSubjectRef(
            SCENARIO_CONTRACT_ID,
            self.scenario_id,
            self.fingerprint,
            self.base_problem_revision_id,
            self.base_problem_revision_fingerprint,
        )


@dataclass(frozen=True)
class UncertaintySpec:
    subject: SemanticSubjectRef | Mapping[str, Any]
    form: str
    interval_quantity: SemanticSubjectRef | Mapping[str, Any] | None = None
    scenario_refs: tuple[SemanticSubjectRef | Mapping[str, Any], ...] = ()
    distribution_reference: ExternalReference | Mapping[str, Any] | None = None
    sample_refs: tuple[SemanticSubjectRef | Mapping[str, Any], ...] = ()
    bound_quantity: SemanticSubjectRef | Mapping[str, Any] | None = None
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    uncertainty_id: str = ""
    contract_id: str = UNCERTAINTY_CONTRACT_ID
    contract_version: str = UNCERTAINTY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != UNCERTAINTY_CONTRACT_ID
            or self.contract_version != UNCERTAINTY_CONTRACT_VERSION
        ):
            raise ValueError("unsupported uncertainty contract")

        subject = _subject(self.subject)
        form = _required("uncertainty form", self.form).upper()
        if form not in UNCERTAINTY_FORMS:
            raise ValueError(f"unsupported uncertainty form: {form}")

        interval_quantity = None if self.interval_quantity is None else _subject(self.interval_quantity)
        if interval_quantity is not None and interval_quantity.semantic_type_id != "aasm.quantity.v1":
            raise ValueError("interval uncertainty must reference aasm.quantity.v1")
        scenario_refs = _subject_refs(self.scenario_refs, required_type=SCENARIO_CONTRACT_ID)
        distribution_reference = _external_ref(self.distribution_reference)
        sample_refs = _subject_refs(self.sample_refs)
        bound_quantity = None if self.bound_quantity is None else _subject(self.bound_quantity)
        if bound_quantity is not None and bound_quantity.semantic_type_id != "aasm.quantity.v1":
            raise ValueError("bounded unknown uncertainty must reference aasm.quantity.v1")
        evidence_ids = _uniq(self.evidence_ids)
        metadata = _jsonable(dict(self.metadata))

        occupied = {
            "interval_quantity": interval_quantity is not None,
            "scenario_refs": bool(scenario_refs),
            "distribution_reference": distribution_reference is not None,
            "sample_refs": bool(sample_refs),
            "bound_quantity": bound_quantity is not None,
        }
        allowed_by_form = {
            "EXACT": set(),
            "INTERVAL": {"interval_quantity"},
            "SCENARIOS": {"scenario_refs"},
            "DISTRIBUTION_REFERENCE": {"distribution_reference"},
            "EMPIRICAL_SAMPLES": {"sample_refs"},
            "UNKNOWN_BOUNDED": {"bound_quantity"},
            "UNKNOWN_UNBOUNDED": set(),
        }
        present = {name for name, is_present in occupied.items() if is_present}
        expected = allowed_by_form[form]
        if present != expected:
            raise ValueError(
                f"{form} uncertainty requires exactly {sorted(expected)}; got {sorted(present)}"
            )
        if form == "SCENARIOS" and not scenario_refs:
            raise ValueError("SCENARIOS uncertainty requires scenario_refs")
        if form == "DISTRIBUTION_REFERENCE":
            assert distribution_reference is not None
            if not distribution_reference.revision or not distribution_reference.source_fingerprint:
                raise ValueError(
                    "distribution uncertainty requires exact external revision and source_fingerprint"
                )
        if form == "EMPIRICAL_SAMPLES":
            if not sample_refs:
                raise ValueError("EMPIRICAL_SAMPLES uncertainty requires sample_refs")
            if not evidence_ids:
                raise ValueError(
                    "EMPIRICAL_SAMPLES uncertainty requires supporting evidence_ids"
                )

        object.__setattr__(self, "subject", subject)
        object.__setattr__(self, "form", form)
        object.__setattr__(self, "interval_quantity", interval_quantity)
        object.__setattr__(self, "scenario_refs", scenario_refs)
        object.__setattr__(self, "distribution_reference", distribution_reference)
        object.__setattr__(self, "sample_refs", sample_refs)
        object.__setattr__(self, "bound_quantity", bound_quantity)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "metadata", metadata)

        derived = f"uncertainty-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.uncertainty_id)
        if supplied and supplied != derived:
            raise ValueError("uncertainty_id does not match canonical uncertainty identity")
        object.__setattr__(self, "uncertainty_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "subject": self.subject.identity_payload(),
            "form": self.form,
            "interval_quantity": None if self.interval_quantity is None else self.interval_quantity.identity_payload(),
            "scenario_refs": [ref.identity_payload() for ref in self.scenario_refs],
            "distribution_reference": None if self.distribution_reference is None else self.distribution_reference.to_dict(),
            "sample_refs": [ref.identity_payload() for ref in self.sample_refs],
            "bound_quantity": None if self.bound_quantity is None else self.bound_quantity.identity_payload(),
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"uncertainty_id": self.uncertainty_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "uncertainty_id": self.uncertainty_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "UncertaintySpec":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["scenario_refs"] = tuple(payload.get("scenario_refs") or ())
        payload["sample_refs"] = tuple(payload.get("sample_refs") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("uncertainty fingerprint mismatch")
        return item


@dataclass(frozen=True)
class TraceEventPattern:
    pattern_id: str
    event_types: tuple[str, ...] = ()
    transition_classes: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        pattern_id = _required("trace pattern_id", self.pattern_id)
        event_types = _uniq(self.event_types)
        transition_classes = _uniq(self.transition_classes)
        if not event_types and not transition_classes:
            raise ValueError("trace event pattern requires event_types or transition_classes")
        unknown_events = sorted(set(event_types) - set(KNOWN_EVENT_TYPES))
        if unknown_events:
            raise ValueError(f"trace event pattern uses unsupported event types: {unknown_events}")
        known_classes = set(TRANSITION_CLASSES.values()) | {"OPERATIONAL"}
        unknown_classes = sorted(set(transition_classes) - known_classes)
        if unknown_classes:
            raise ValueError(
                f"trace event pattern uses unsupported transition classes: {unknown_classes}"
            )
        object.__setattr__(self, "pattern_id", pattern_id)
        object.__setattr__(self, "event_types", event_types)
        object.__setattr__(self, "transition_classes", transition_classes)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "event_types": list(self.event_types),
            "transition_classes": list(self.transition_classes),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TraceEventPattern":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["event_types"] = tuple(payload.get("event_types") or ())
        payload["transition_classes"] = tuple(payload.get("transition_classes") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("trace event pattern fingerprint mismatch")
        return item


@dataclass(frozen=True)
class TraceProperty:
    property_name: str
    kind: str
    patterns: tuple[TraceEventPattern | Mapping[str, Any], ...]
    max_step_distance: int | None = None
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    invariant_classification: str = TRACE_INVARIANT_CLASSIFICATION
    metadata: Mapping[str, Any] = field(default_factory=dict)
    property_id: str = ""
    contract_id: str = TRACE_PROPERTY_CONTRACT_ID
    contract_version: str = TRACE_PROPERTY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != TRACE_PROPERTY_CONTRACT_ID
            or self.contract_version != TRACE_PROPERTY_CONTRACT_VERSION
        ):
            raise ValueError("unsupported trace-property contract")
        name = _required("trace property_name", self.property_name)
        kind = _required("trace property kind", self.kind).upper()
        if kind not in TRACE_PROPERTY_KINDS:
            raise ValueError(f"unsupported trace property kind: {kind}")
        patterns = tuple(
            pattern if isinstance(pattern, TraceEventPattern) else TraceEventPattern.from_dict(pattern)
            for pattern in self.patterns
        )
        pattern_ids = [pattern.pattern_id for pattern in patterns]
        if len(pattern_ids) != len(set(pattern_ids)):
            raise ValueError("trace property pattern_id values must be unique")

        required_counts = {
            "OCCURS": 1,
            "NEVER_OCCURS": 1,
            "PRECEDES": 2,
            "BOUNDED_EVENTUALLY_STEPS": 2,
        }
        if kind in required_counts and len(patterns) != required_counts[kind]:
            raise ValueError(
                f"{kind} trace property requires exactly {required_counts[kind]} patterns"
            )
        if kind == "SEQUENCE" and len(patterns) < 2:
            raise ValueError("SEQUENCE trace property requires at least two patterns")

        max_distance = self.max_step_distance
        if kind == "BOUNDED_EVENTUALLY_STEPS":
            if isinstance(max_distance, bool) or not isinstance(max_distance, int):
                raise TypeError(
                    "BOUNDED_EVENTUALLY_STEPS max_step_distance must be an exact integer"
                )
            if max_distance < 0:
                raise ValueError("max_step_distance must be non-negative")
        elif max_distance is not None:
            raise ValueError(f"{kind} trace property cannot carry max_step_distance")

        revision_id, revision_fingerprint = _revision_pair(
            self.problem_revision_id,
            self.problem_revision_fingerprint,
            prefix="trace property problem",
        )
        classification = _required(
            "trace invariant_classification", self.invariant_classification
        ).upper()
        if classification != TRACE_INVARIANT_CLASSIFICATION:
            raise ValueError(
                "trace properties are DYNAMIC_KERNEL invariants; static or empirical "
                "claims require separate evidence/contracts"
            )

        object.__setattr__(self, "property_name", name)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "patterns", patterns)
        object.__setattr__(self, "max_step_distance", max_distance)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "invariant_classification", classification)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

        derived = f"trace-property-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.property_id)
        if supplied and supplied != derived:
            raise ValueError(
                "trace property_id does not match canonical trace-property identity"
            )
        object.__setattr__(self, "property_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "property_name": self.property_name,
            "kind": self.kind,
            "patterns": [pattern.identity_payload() for pattern in self.patterns],
            "max_step_distance": self.max_step_distance,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "invariant_classification": self.invariant_classification,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"property_id": self.property_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "property_id": self.property_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TraceProperty":
        payload = deepcopy(dict(value))
        supplied = str(payload.pop("fingerprint", "")).strip()
        payload["patterns"] = tuple(payload.get("patterns") or ())
        item = cls(**payload)
        if supplied and supplied != item.fingerprint:
            raise ValueError("trace property fingerprint mismatch")
        return item


@dataclass(frozen=True)
class TraceEvaluationContext:
    completeness: str
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""

    def __post_init__(self) -> None:
        completeness = _required("trace completeness", self.completeness).upper()
        if completeness not in TRACE_COMPLETENESS:
            raise ValueError(f"unsupported trace completeness: {completeness}")
        revision_id, revision_fingerprint = _revision_pair(
            self.problem_revision_id,
            self.problem_revision_fingerprint,
            prefix="trace evaluation problem",
        )
        object.__setattr__(self, "completeness", completeness)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "completeness": self.completeness,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
        }

    def to_dict(self) -> dict[str, Any]:
        return self.identity_payload()


@dataclass(frozen=True)
class TracePropertyAssessment:
    property_id: str
    property_fingerprint: str
    source_trace_sha256: str
    projection_sha256: str
    completeness: str
    status: str
    witness_event_ids: tuple[str, ...] = ()
    violating_event_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()
    assessment_id: str = ""
    contract_id: str = TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID
    contract_version: str = TRACE_PROPERTY_ASSESSMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "property_id",
            "property_fingerprint",
            "source_trace_sha256",
            "projection_sha256",
        ):
            value = _required(f"trace assessment {name}", getattr(self, name))
            if name.endswith("fingerprint") or name.endswith("sha256"):
                value = _sha256(f"trace assessment {name}", value)
            object.__setattr__(self, name, value)
        if (
            self.contract_id != TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID
            or self.contract_version != TRACE_PROPERTY_ASSESSMENT_CONTRACT_VERSION
        ):
            raise ValueError("unsupported trace-property assessment contract")
        completeness = _required("trace assessment completeness", self.completeness).upper()
        status = _required("trace assessment status", self.status).upper()
        if completeness not in TRACE_COMPLETENESS:
            raise ValueError(f"unsupported trace assessment completeness: {completeness}")
        if status not in TRACE_PROPERTY_STATUSES:
            raise ValueError(f"unsupported trace assessment status: {status}")
        object.__setattr__(self, "completeness", completeness)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "witness_event_ids", _uniq(self.witness_event_ids))
        object.__setattr__(self, "violating_event_ids", _uniq(self.violating_event_ids))
        object.__setattr__(self, "diagnostics", _uniq(self.diagnostics))
        derived = f"trace-property-assessment-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.assessment_id)
        if supplied and supplied != derived:
            raise ValueError(
                "trace assessment_id does not match canonical assessment identity"
            )
        object.__setattr__(self, "assessment_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "property_id": self.property_id,
            "property_fingerprint": self.property_fingerprint,
            "source_trace_sha256": self.source_trace_sha256,
            "projection_sha256": self.projection_sha256,
            "completeness": self.completeness,
            "status": self.status,
            "witness_event_ids": list(self.witness_event_ids),
            "violating_event_ids": list(self.violating_event_ids),
            "diagnostics": list(self.diagnostics),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assessment_id": self.assessment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessment_id": self.assessment_id,
            **self.identity_payload(),
            "fingerprint": self.fingerprint,
        }


def _pattern_matches(pattern: TraceEventPattern, step: Mapping[str, Any]) -> bool:
    if pattern.event_types and str(step.get("event_type") or "") not in pattern.event_types:
        return False
    if pattern.transition_classes and str(step.get("transition_class") or "") not in pattern.transition_classes:
        return False
    return True


def _assessment(
    prop: TraceProperty,
    projection: Mapping[str, Any],
    context: TraceEvaluationContext,
    status: str,
    *,
    witness_event_ids: Sequence[str] = (),
    violating_event_ids: Sequence[str] = (),
    diagnostics: Sequence[str] = (),
) -> TracePropertyAssessment:
    return TracePropertyAssessment(
        prop.property_id,
        prop.fingerprint,
        str(projection["source_trace_sha256"]),
        str(projection["projection_sha256"]),
        context.completeness,
        status,
        tuple(witness_event_ids),
        tuple(violating_event_ids),
        tuple(diagnostics),
    )


def evaluate_trace_property(
    prop: TraceProperty,
    source: Any,
    *,
    context: TraceEvaluationContext,
) -> TracePropertyAssessment:
    if not isinstance(prop, TraceProperty):
        raise TypeError("evaluate_trace_property requires TraceProperty")
    if not isinstance(context, TraceEvaluationContext):
        raise TypeError("evaluate_trace_property requires TraceEvaluationContext")

    projection = project_trace(source)
    if not projection["valid"]:
        return _assessment(
            prop,
            projection,
            context,
            "INCONCLUSIVE",
            diagnostics=("TRACE_PROJECTION_INVALID",),
        )
    if projection["unsupported_event_types"]:
        return _assessment(
            prop,
            projection,
            context,
            "UNSUPPORTED",
            diagnostics=tuple(
                f"UNSUPPORTED_EVENT_TYPE:{event_type}"
                for event_type in projection["unsupported_event_types"]
            ),
        )

    if prop.problem_revision_id:
        if not context.problem_revision_id:
            return _assessment(
                prop,
                projection,
                context,
                "INCONCLUSIVE",
                diagnostics=("PROBLEM_REVISION_CONTEXT_MISSING",),
            )
        if (
            prop.problem_revision_id != context.problem_revision_id
            or prop.problem_revision_fingerprint != context.problem_revision_fingerprint
        ):
            return _assessment(
                prop,
                projection,
                context,
                "INCONCLUSIVE",
                diagnostics=("PROBLEM_REVISION_MISMATCH",),
            )

    if context.completeness != "COMPLETE":
        return _assessment(
            prop,
            projection,
            context,
            "INCONCLUSIVE",
            diagnostics=("TRACE_NOT_DECLARED_COMPLETE",),
        )

    steps = list(projection["steps"])
    matches: list[list[int]] = [
        [index for index, step in enumerate(steps) if _pattern_matches(pattern, step)]
        for pattern in prop.patterns
    ]

    def event_id(index: int) -> str:
        return str(steps[index]["event_id"])

    if prop.kind == "OCCURS":
        if matches[0]:
            return _assessment(
                prop,
                projection,
                context,
                "PASS",
                witness_event_ids=(event_id(matches[0][0]),),
            )
        return _assessment(
            prop,
            projection,
            context,
            "FAIL",
            diagnostics=("REQUIRED_PATTERN_NOT_OBSERVED",),
        )

    if prop.kind == "NEVER_OCCURS":
        if matches[0]:
            violating = tuple(event_id(index) for index in matches[0])
            return _assessment(
                prop,
                projection,
                context,
                "FAIL",
                violating_event_ids=violating,
                diagnostics=("FORBIDDEN_PATTERN_OBSERVED",),
            )
        return _assessment(prop, projection, context, "PASS")

    if prop.kind == "PRECEDES":
        left, right = matches
        violating: list[str] = []
        witnesses: list[str] = []
        for right_index in right:
            eligible = [left_index for left_index in left if left_index < right_index]
            if not eligible:
                violating.append(event_id(right_index))
            else:
                witnesses.extend((event_id(eligible[-1]), event_id(right_index)))
        if violating:
            return _assessment(
                prop,
                projection,
                context,
                "FAIL",
                violating_event_ids=violating,
                diagnostics=("PRECEDENCE_VIOLATION",),
            )
        return _assessment(
            prop,
            projection,
            context,
            "PASS",
            witness_event_ids=witnesses,
        )

    if prop.kind == "SEQUENCE":
        cursor = -1
        witness_indexes: list[int] = []
        for positions in matches:
            next_positions = [position for position in positions if position > cursor]
            if not next_positions:
                return _assessment(
                    prop,
                    projection,
                    context,
                    "FAIL",
                    witness_event_ids=tuple(event_id(index) for index in witness_indexes),
                    diagnostics=("REQUIRED_SEQUENCE_NOT_OBSERVED",),
                )
            cursor = next_positions[0]
            witness_indexes.append(cursor)
        return _assessment(
            prop,
            projection,
            context,
            "PASS",
            witness_event_ids=tuple(event_id(index) for index in witness_indexes),
        )

    assert prop.kind == "BOUNDED_EVENTUALLY_STEPS"
    assert prop.max_step_distance is not None
    trigger_positions, response_positions = matches
    violating: list[str] = []
    witnesses: list[str] = []
    for trigger_index in trigger_positions:
        eligible = [
            response_index
            for response_index in response_positions
            if trigger_index < response_index
            and response_index - trigger_index <= prop.max_step_distance
        ]
        if not eligible:
            violating.append(event_id(trigger_index))
        else:
            witnesses.extend((event_id(trigger_index), event_id(eligible[0])))
    if violating:
        return _assessment(
            prop,
            projection,
            context,
            "FAIL",
            witness_event_ids=witnesses,
            violating_event_ids=violating,
            diagnostics=("BOUNDED_EVENTUAL_RESPONSE_MISSING",),
        )
    return _assessment(
        prop,
        projection,
        context,
        "PASS",
        witness_event_ids=witnesses,
    )


def uncertainty_contract() -> dict[str, Any]:
    return {
        "contract_id": UNCERTAINTY_CONTRACT_ID,
        "contract_version": UNCERTAINTY_CONTRACT_VERSION,
        "stability": UNCERTAINTY_SCENARIO_TRACE_STABILITY,
        "forms": list(UNCERTAINTY_FORMS),
        "subject_binding": "EXACT_EXISTING_SEMANTIC_OBJECT_ID_FINGERPRINT_AND_OPTIONAL_REVISION",
        "quantity_relation": "NUMERIC_INTERVAL_AND_BOUND_SEMANTICS_REFERENCE_AASM_QUANTITY_V1_NO_DUPLICATE_NUMERIC_ENCODING",
        "scenario_relation": "SCENARIO_FORM_REFERENCES_AASM_SCENARIO_V1_BY_EXACT_ID_AND_FINGERPRINT",
        "distribution_relation": "EXTERNAL_REFERENCE_WITH_EXACT_REVISION_AND_SOURCE_FINGERPRINT_NO_EMBEDDED_PROBABILITY_ENGINE",
        "empirical_samples": "EXACT_SAMPLE_OBJECT_REFERENCES_PLUS_SUPPORTING_EVIDENCE_IDS",
        "exact_form_meaning": "NO_ADDITIONAL_UNCERTAINTY_DECLARED_BY_THIS_RECORD_NOT_TRUTH_CERTAINTY",
        "confidence_relation": "DISTINCT_FROM_SEMANTIC_RESULT_CONFIDENCE_NO_INFERENCE_OR_COERCION",
        "numeric_tolerance_relation": "DISTINCT_FROM_AASM_NUMERIC_TOLERANCE_V1_ACCEPTANCE_POLICY",
        "probability_inference": "NONE",
        "truth_authority": "NONE",
        "fact_authority": "NONE",
        "effect_authority": "NONE",
        "artifact_acceptance": "NONE",
        "objective_preference": "NONE",
        "reuse_admission": "NONE",
        "hidden_wall_clock": "NONE",
        "parallel_uncertainty_registry": "NONE",
        "current_uncertainty_pointer": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def scenario_contract() -> dict[str, Any]:
    return {
        "contract_id": SCENARIO_CONTRACT_ID,
        "contract_version": SCENARIO_CONTRACT_VERSION,
        "stability": UNCERTAINTY_SCENARIO_TRACE_STABILITY,
        "problem_revision_binding": "EXACT_EXISTING_PROBLEM_REVISION_ID_AND_FINGERPRINT_REQUIRED",
        "binding_kinds": list(SCENARIO_BINDING_KINDS),
        "literal_semantics": "DISCRETE_STRING_INTEGER_BOOLEAN_OR_NULL_ONLY_NO_BINARY_FLOAT_ENGINEERING_NUMERICS_USE_AASM_QUANTITY_V1_REFERENCE",
        "scenario_is_problem_revision": False,
        "scenario_is_evidence": False,
        "scenario_activation": "NONE_FOUNDATION_ONLY",
        "scenario_selection_grants_authority": False,
        "scenario_existence_grants_fact_authority": False,
        "scenario_existence_grants_effect_authority": False,
        "problem_delta_relation": "EXISTING_CHANGED_SCENARIO_IDS_REMAINS_REVISION_INVALIDATION_SEAM_NO_AUTOMATIC_DELTA_CREATION",
        "probability_semantics": "NONE_UNLESS_EXPLICIT_UNCERTAINTY_CONTRACT_REFERENCE",
        "truth_authority": "NONE",
        "effect_authority": "NONE",
        "artifact_acceptance": "NONE",
        "objective_preference": "NONE",
        "hidden_current_scenario": "NONE",
        "parallel_scenario_registry": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def trace_property_contract() -> dict[str, Any]:
    return {
        "contract_id": TRACE_PROPERTY_CONTRACT_ID,
        "contract_version": TRACE_PROPERTY_CONTRACT_VERSION,
        "assessment_contract_id": TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID,
        "assessment_contract_version": TRACE_PROPERTY_ASSESSMENT_CONTRACT_VERSION,
        "stability": UNCERTAINTY_SCENARIO_TRACE_STABILITY,
        "property_kinds": list(TRACE_PROPERTY_KINDS),
        "trace_source": "EXISTING_AASM_TRACE_V1_AUTHORITATIVE_DURABLE_EVENT_HISTORY",
        "trace_projection": "EXISTING_PROJECT_TRACE_FUNCTION_UNCHANGED",
        "completion": "EXPLICIT_COMPLETE_PREFIX_OR_UNKNOWN_COMPLETE_REQUIRED_FOR_DECISIVE_FOUNDATION_EVALUATION",
        "unsupported_transition_policy": "PRESERVE_AASM_TRACE_V1_UNSUPPORTED_EXPLICIT",
        "invariant_classification": TRACE_INVARIANT_CLASSIFICATION,
        "static_constraint_lowering": "NONE",
        "host_wall_clock": "NONE",
        "time_distance": "EVENT_POSITION_STEPS_ONLY_FOUNDATION_DOES_NOT_INFER_WALL_CLOCK_DURATION",
        "problem_revision_binding": "OPTIONAL_EXACT_ID_AND_FINGERPRINT_FAIL_CLOSED",
        "assessment_grants_truth": False,
        "assessment_grants_fact_authority": False,
        "assessment_grants_effect_authority": False,
        "assessment_is_solver_proof": False,
        "parallel_trace_store": "NONE",
        "parallel_property_registry": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "UNCERTAINTY_CONTRACT_ID",
    "UNCERTAINTY_CONTRACT_VERSION",
    "SCENARIO_CONTRACT_ID",
    "SCENARIO_CONTRACT_VERSION",
    "TRACE_PROPERTY_CONTRACT_ID",
    "TRACE_PROPERTY_CONTRACT_VERSION",
    "TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID",
    "TRACE_PROPERTY_ASSESSMENT_CONTRACT_VERSION",
    "UNCERTAINTY_SCENARIO_TRACE_STABILITY",
    "UNCERTAINTY_FORMS",
    "SCENARIO_BINDING_KINDS",
    "TRACE_PROPERTY_KINDS",
    "TRACE_COMPLETENESS",
    "TRACE_PROPERTY_STATUSES",
    "TRACE_INVARIANT_CLASSIFICATION",
    "ScenarioBinding",
    "Scenario",
    "UncertaintySpec",
    "TraceEventPattern",
    "TraceProperty",
    "TraceEvaluationContext",
    "TracePropertyAssessment",
    "evaluate_trace_property",
    "uncertainty_contract",
    "scenario_contract",
    "trace_property_contract",
]
