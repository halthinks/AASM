from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .semantic_dependencies import SemanticNodeRef
from .semantic_result import semantic_fingerprint


EXPERIMENT_CONTRACT_ID = "aasm.experiment.v1"
EXPERIMENT_CONTRACT_VERSION = "0.1.0"
EXPERIMENT_STABILITY = "FOUNDATION_EXPERIMENTAL"

EXPERIMENT_VARIABLE_ROLES = ("CONTROLLED", "MEASURED")
EXPERIMENT_BINDING_KINDS = (
    "ENVIRONMENT",
    "FIXTURE_IDENTITY",
    "CALIBRATION_IDENTITY",
    "EVIDENCE_FLOOR",
    "RISK_CONSTRAINT",
    "SAFETY_CONSTRAINT",
    "RESOURCE_DEMAND",
    "VERIFICATION_OBLIGATION",
)
EXPERIMENT_BINDING_STATUSES = ("BOUND", "NOT_APPLICABLE")
EXPERIMENT_OPTIONAL_BINDING_KINDS = {"FIXTURE_IDENTITY", "CALIBRATION_IDENTITY"}
EXPERIMENT_SELECTION_CONSTRAINT_STATUSES = (
    "ELIGIBLE",
    "BLOCKED_REVISION",
    "BLOCKED_SAFETY",
    "BLOCKED_EVIDENCE",
    "BLOCKED_RESOURCE",
    "INDETERMINATE",
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"experiment {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"experiment {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Sequence[Any], *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    items = tuple(sorted({_required(name, value) for value in values}))
    if not allow_empty and not items:
        raise ValueError(f"experiment requires at least one {name}")
    return items


def _portable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _portable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _portable(item) for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))}
    if isinstance(value, (tuple, list, set)):
        return [_portable(item) for item in value]
    if isinstance(value, float):
        raise TypeError("binary floating-point values are forbidden in experiment portable identity")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"experiment value is not portable JSON: {type(value)!r}")


def _ppm(name: str, value: Any) -> int:
    if type(value) is not int:
        raise TypeError(f"experiment {name} must be an integer parts-per-million score")
    if value < 0 or value > 1_000_000:
        raise ValueError(f"experiment {name} must be between 0 and 1000000")
    return int(value)


def _round_trip_fingerprint(item: Any, supplied: str, *, label: str) -> None:
    if supplied and supplied != item.fingerprint:
        raise ValueError(f"{label} fingerprint mismatch")


@dataclass(frozen=True)
class ExperimentContextBinding:
    binding_kind: str
    status: str
    contract_id: str = ""
    object_id: str = ""
    object_fingerprint: str = ""
    evidence_ids: tuple[str, ...] = ()
    reason: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        kind = _required("binding_kind", self.binding_kind).upper()
        status = _required("binding status", self.status).upper()
        if kind not in EXPERIMENT_BINDING_KINDS:
            raise ValueError(f"unsupported experiment binding kind: {kind}")
        if status not in EXPERIMENT_BINDING_STATUSES:
            raise ValueError(f"unsupported experiment binding status: {status}")
        contract_id = _optional(self.contract_id)
        object_id = _optional(self.object_id)
        fingerprint = _optional(self.object_fingerprint).lower()
        reason = _optional(self.reason)
        evidence_ids = _uniq(self.evidence_ids, name="binding evidence_id")
        if status == "BOUND":
            contract_id = _required("binding contract_id", contract_id)
            object_id = _required("binding object_id", object_id)
            fingerprint = _sha256("binding object_fingerprint", fingerprint)
            if reason:
                raise ValueError("BOUND experiment binding must not carry NOT_APPLICABLE reason")
        else:
            if kind not in EXPERIMENT_OPTIONAL_BINDING_KINDS:
                raise ValueError(f"{kind} experiment binding cannot be NOT_APPLICABLE")
            if contract_id or object_id or fingerprint or evidence_ids:
                raise ValueError("NOT_APPLICABLE experiment binding cannot masquerade as a bound object")
            reason = _required("NOT_APPLICABLE binding reason", reason)
        object.__setattr__(self, "binding_kind", kind)
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "contract_id", contract_id)
        object.__setattr__(self, "object_id", object_id)
        object.__setattr__(self, "object_fingerprint", fingerprint)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "reason", reason)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "binding_kind": self.binding_kind,
            "status": self.status,
            "contract_id": self.contract_id,
            "object_id": self.object_id,
            "object_fingerprint": self.object_fingerprint,
            "evidence_ids": list(self.evidence_ids),
            "reason": self.reason,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentContextBinding":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="experiment context binding")
        return item


@dataclass(frozen=True)
class ExperimentHypothesis:
    statement: str
    semantic_refs: tuple[SemanticNodeRef | Mapping[str, Any], ...] = ()
    basis_evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    hypothesis_id: str = ""

    def __post_init__(self) -> None:
        statement = _required("hypothesis statement", self.statement)
        refs = tuple(
            row if isinstance(row, SemanticNodeRef) else SemanticNodeRef.from_dict(row)
            for row in self.semantic_refs
        )
        by_key = {row.key: row for row in refs}
        if len(by_key) != len(refs):
            raise ValueError("experiment hypothesis semantic references must be unique")
        refs = tuple(sorted(refs, key=lambda row: row.key))
        basis = _uniq(self.basis_evidence_ids, name="hypothesis basis evidence_id")
        metadata = _portable(dict(self.metadata))
        object.__setattr__(self, "statement", statement)
        object.__setattr__(self, "semantic_refs", refs)
        object.__setattr__(self, "basis_evidence_ids", basis)
        object.__setattr__(self, "metadata", metadata)
        derived = f"experiment-hypothesis-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.hypothesis_id)
        if supplied and supplied != derived:
            raise ValueError("experiment hypothesis_id does not match canonical identity")
        object.__setattr__(self, "hypothesis_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "statement": self.statement,
            "semantic_refs": [row.to_dict() for row in self.semantic_refs],
            "basis_evidence_ids": list(self.basis_evidence_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"hypothesis_id": self.hypothesis_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"hypothesis_id": self.hypothesis_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentHypothesis":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["semantic_refs"] = tuple(payload.get("semantic_refs") or ())
        payload["basis_evidence_ids"] = tuple(payload.get("basis_evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="experiment hypothesis")
        return item


@dataclass(frozen=True)
class ExperimentVariable:
    variable_id: str
    role: str
    semantic_ref: SemanticNodeRef | Mapping[str, Any]
    definition_fingerprint: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        variable_id = _required("variable_id", self.variable_id)
        role = _required("variable role", self.role).upper()
        if role not in EXPERIMENT_VARIABLE_ROLES:
            raise ValueError(f"unsupported experiment variable role: {role}")
        ref = self.semantic_ref if isinstance(self.semantic_ref, SemanticNodeRef) else SemanticNodeRef.from_dict(self.semantic_ref)
        definition = _sha256("variable definition_fingerprint", self.definition_fingerprint)
        object.__setattr__(self, "variable_id", variable_id)
        object.__setattr__(self, "role", role)
        object.__setattr__(self, "semantic_ref", ref)
        object.__setattr__(self, "definition_fingerprint", definition)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "role": self.role,
            "semantic_ref": self.semantic_ref.to_dict(),
            "definition_fingerprint": self.definition_fingerprint,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentVariable":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="experiment variable")
        return item


@dataclass(frozen=True)
class ExperimentProcedureStep:
    step_id: str
    sequence: int
    instruction: str
    required_capability_ids: tuple[str, ...] = ()
    input_artifact_ids: tuple[str, ...] = ()
    output_artifact_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        step_id = _required("procedure step_id", self.step_id)
        if type(self.sequence) is not int or self.sequence < 0:
            raise ValueError("experiment procedure sequence must be a non-negative integer")
        instruction = _required("procedure instruction", self.instruction)
        object.__setattr__(self, "step_id", step_id)
        object.__setattr__(self, "instruction", instruction)
        object.__setattr__(self, "required_capability_ids", _uniq(self.required_capability_ids, name="procedure capability_id"))
        object.__setattr__(self, "input_artifact_ids", _uniq(self.input_artifact_ids, name="procedure input artifact_id"))
        object.__setattr__(self, "output_artifact_ids", _uniq(self.output_artifact_ids, name="procedure output artifact_id"))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "sequence": self.sequence,
            "instruction": self.instruction,
            "required_capability_ids": list(self.required_capability_ids),
            "input_artifact_ids": list(self.input_artifact_ids),
            "output_artifact_ids": list(self.output_artifact_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentProcedureStep":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        for name in ("required_capability_ids", "input_artifact_ids", "output_artifact_ids"):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="experiment procedure step")
        return item


@dataclass(frozen=True)
class ExperimentOutcomeCriterion:
    outcome_id: str
    description: str
    predicate_fingerprint: str
    supports_hypothesis_ids: tuple[str, ...] = ()
    contradicts_hypothesis_ids: tuple[str, ...] = ()
    inconclusive: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        outcome_id = _required("outcome_id", self.outcome_id)
        description = _required("outcome description", self.description)
        predicate = _sha256("outcome predicate_fingerprint", self.predicate_fingerprint)
        supports = _uniq(self.supports_hypothesis_ids, name="supported hypothesis_id")
        contradicts = _uniq(self.contradicts_hypothesis_ids, name="contradicted hypothesis_id")
        if set(supports) & set(contradicts):
            raise ValueError("experiment outcome cannot both support and contradict the same hypothesis")
        if self.inconclusive and (supports or contradicts):
            raise ValueError("INCONCLUSIVE experiment outcome cannot claim hypothesis discrimination")
        if not self.inconclusive and not (supports or contradicts):
            raise ValueError("non-inconclusive experiment outcome must discriminate at least one hypothesis")
        object.__setattr__(self, "outcome_id", outcome_id)
        object.__setattr__(self, "description", description)
        object.__setattr__(self, "predicate_fingerprint", predicate)
        object.__setattr__(self, "supports_hypothesis_ids", supports)
        object.__setattr__(self, "contradicts_hypothesis_ids", contradicts)
        object.__setattr__(self, "inconclusive", bool(self.inconclusive))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "outcome_id": self.outcome_id,
            "description": self.description,
            "predicate_fingerprint": self.predicate_fingerprint,
            "supports_hypothesis_ids": list(self.supports_hypothesis_ids),
            "contradicts_hypothesis_ids": list(self.contradicts_hypothesis_ids),
            "inconclusive": self.inconclusive,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentOutcomeCriterion":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["supports_hypothesis_ids"] = tuple(payload.get("supports_hypothesis_ids") or ())
        payload["contradicts_hypothesis_ids"] = tuple(payload.get("contradicts_hypothesis_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="experiment outcome criterion")
        return item


@dataclass(frozen=True)
class ExperimentSpec:
    experiment_name: str
    workspace_id: str
    scope_id: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    hypotheses: tuple[ExperimentHypothesis | Mapping[str, Any], ...]
    variables: tuple[ExperimentVariable | Mapping[str, Any], ...]
    procedure_steps: tuple[ExperimentProcedureStep | Mapping[str, Any], ...]
    context_bindings: tuple[ExperimentContextBinding | Mapping[str, Any], ...]
    outcome_criteria: tuple[ExperimentOutcomeCriterion | Mapping[str, Any], ...]
    producer_principal_id: str
    evidence_ids: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    experiment_id: str = ""
    contract_id: str = EXPERIMENT_CONTRACT_ID
    contract_version: str = EXPERIMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != EXPERIMENT_CONTRACT_ID or self.contract_version != EXPERIMENT_CONTRACT_VERSION:
            raise ValueError("unsupported experiment contract")
        name = _required("experiment_name", self.experiment_name)
        workspace = _required("workspace_id", self.workspace_id)
        scope = _required("scope_id", self.scope_id)
        revision_id = _required("problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("problem_revision_fingerprint", self.problem_revision_fingerprint)
        producer = _required("producer_principal_id", self.producer_principal_id)
        evidence = _uniq(self.evidence_ids, name="experiment evidence_id", allow_empty=False)

        hypotheses = tuple(
            row if isinstance(row, ExperimentHypothesis) else ExperimentHypothesis.from_dict(row)
            for row in self.hypotheses
        )
        if not hypotheses:
            raise ValueError("experiment requires at least one explicit hypothesis")
        hypothesis_ids = [row.hypothesis_id for row in hypotheses]
        if len(hypothesis_ids) != len(set(hypothesis_ids)):
            raise ValueError("experiment hypothesis IDs must be unique")
        hypotheses = tuple(sorted(hypotheses, key=lambda row: row.hypothesis_id))

        variables = tuple(
            row if isinstance(row, ExperimentVariable) else ExperimentVariable.from_dict(row)
            for row in self.variables
        )
        variable_ids = [row.variable_id for row in variables]
        if len(variable_ids) != len(set(variable_ids)):
            raise ValueError("experiment variable IDs must be unique")
        controlled = [row for row in variables if row.role == "CONTROLLED"]
        measured = [row for row in variables if row.role == "MEASURED"]
        if not controlled or not measured:
            raise ValueError("experiment requires at least one CONTROLLED and one MEASURED variable")
        if {row.semantic_ref.key for row in controlled} & {row.semantic_ref.key for row in measured}:
            raise ValueError("controlled and measured experiment semantic variables must be disjoint")
        variables = tuple(sorted(variables, key=lambda row: (row.role, row.variable_id)))

        steps = tuple(
            row if isinstance(row, ExperimentProcedureStep) else ExperimentProcedureStep.from_dict(row)
            for row in self.procedure_steps
        )
        if not steps:
            raise ValueError("experiment requires a non-empty explicit procedure")
        step_ids = [row.step_id for row in steps]
        sequences = [row.sequence for row in steps]
        if len(step_ids) != len(set(step_ids)) or len(sequences) != len(set(sequences)):
            raise ValueError("experiment procedure step IDs and sequences must be unique")
        if sorted(sequences) != list(range(len(steps))):
            raise ValueError("experiment procedure sequence must be contiguous from zero")
        steps = tuple(sorted(steps, key=lambda row: row.sequence))

        bindings = tuple(
            row if isinstance(row, ExperimentContextBinding) else ExperimentContextBinding.from_dict(row)
            for row in self.context_bindings
        )
        if not bindings:
            raise ValueError("experiment requires explicit context bindings")
        binding_keys = [(row.binding_kind, row.status, row.object_id, row.object_fingerprint, row.reason) for row in bindings]
        if len(binding_keys) != len(set(binding_keys)):
            raise ValueError("experiment context bindings must be unique")
        by_kind = {kind: [row for row in bindings if row.binding_kind == kind] for kind in EXPERIMENT_BINDING_KINDS}
        if len(by_kind["ENVIRONMENT"]) != 1 or by_kind["ENVIRONMENT"][0].status != "BOUND":
            raise ValueError("experiment requires exactly one bound execution environment")
        if not by_kind["FIXTURE_IDENTITY"]:
            raise ValueError("experiment requires explicit fixture identity binding or NOT_APPLICABLE declaration")
        if not by_kind["CALIBRATION_IDENTITY"]:
            raise ValueError("experiment requires explicit calibration identity binding or NOT_APPLICABLE declaration")
        if not by_kind["EVIDENCE_FLOOR"]:
            raise ValueError("experiment requires at least one bound evidence-floor reference")
        if not by_kind["RESOURCE_DEMAND"]:
            raise ValueError("experiment requires at least one bound existing resource-demand reference")
        if not (by_kind["RISK_CONSTRAINT"] or by_kind["SAFETY_CONSTRAINT"]):
            raise ValueError("experiment requires at least one bound safety/risk constraint reference")
        bindings = tuple(sorted(bindings, key=lambda row: (row.binding_kind, row.status, row.object_id, row.fingerprint)))

        outcomes = tuple(
            row if isinstance(row, ExperimentOutcomeCriterion) else ExperimentOutcomeCriterion.from_dict(row)
            for row in self.outcome_criteria
        )
        if len(outcomes) < 2:
            raise ValueError("experiment requires at least two explicit possible outcome criteria")
        outcome_ids = [row.outcome_id for row in outcomes]
        if len(outcome_ids) != len(set(outcome_ids)):
            raise ValueError("experiment outcome IDs must be unique")
        known_hypotheses = set(hypothesis_ids)
        for outcome in outcomes:
            unknown = (set(outcome.supports_hypothesis_ids) | set(outcome.contradicts_hypothesis_ids)) - known_hypotheses
            if unknown:
                raise ValueError(f"experiment outcome references unknown hypotheses: {sorted(unknown)}")
        if not any(not row.inconclusive for row in outcomes):
            raise ValueError("experiment requires at least one discriminating non-inconclusive outcome")
        outcomes = tuple(sorted(outcomes, key=lambda row: row.outcome_id))

        object.__setattr__(self, "experiment_name", name)
        object.__setattr__(self, "workspace_id", workspace)
        object.__setattr__(self, "scope_id", scope)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "hypotheses", hypotheses)
        object.__setattr__(self, "variables", variables)
        object.__setattr__(self, "procedure_steps", steps)
        object.__setattr__(self, "context_bindings", bindings)
        object.__setattr__(self, "outcome_criteria", outcomes)
        object.__setattr__(self, "producer_principal_id", producer)
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"experiment-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.experiment_id)
        if supplied and supplied != derived:
            raise ValueError("experiment_id does not match canonical identity")
        object.__setattr__(self, "experiment_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "experiment_name": self.experiment_name,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "hypotheses": [row.to_dict() for row in self.hypotheses],
            "variables": [row.to_dict() for row in self.variables],
            "procedure_steps": [row.to_dict() for row in self.procedure_steps],
            "context_bindings": [row.to_dict() for row in self.context_bindings],
            "outcome_criteria": [row.to_dict() for row in self.outcome_criteria],
            "producer_principal_id": self.producer_principal_id,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"experiment_id": self.experiment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"experiment_id": self.experiment_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentSpec":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        for name in ("hypotheses", "variables", "procedure_steps", "context_bindings", "outcome_criteria", "evidence_ids"):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="experiment")
        return item


@dataclass(frozen=True)
class ExperimentSelectionCandidate:
    experiment_id: str
    experiment_fingerprint: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    constraint_status: str
    constraint_assessment_evidence_ids: tuple[str, ...]
    expected_information_gain_ppm: int
    expected_uncertainty_reduction_ppm: int
    metadata: Mapping[str, Any] = field(default_factory=dict)
    candidate_id: str = ""
    contract_id: str = EXPERIMENT_CONTRACT_ID
    contract_version: str = EXPERIMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != EXPERIMENT_CONTRACT_ID or self.contract_version != EXPERIMENT_CONTRACT_VERSION:
            raise ValueError("unsupported experiment selection candidate contract")
        experiment_id = _required("selection experiment_id", self.experiment_id)
        experiment_fingerprint = _sha256("selection experiment_fingerprint", self.experiment_fingerprint)
        revision_id = _required("selection problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("selection problem_revision_fingerprint", self.problem_revision_fingerprint)
        status = _required("selection constraint_status", self.constraint_status).upper()
        if status not in EXPERIMENT_SELECTION_CONSTRAINT_STATUSES:
            raise ValueError(f"unsupported experiment selection constraint status: {status}")
        evidence = _uniq(self.constraint_assessment_evidence_ids, name="constraint assessment evidence_id", allow_empty=False)
        info_gain = _ppm("expected_information_gain_ppm", self.expected_information_gain_ppm)
        uncertainty = _ppm("expected_uncertainty_reduction_ppm", self.expected_uncertainty_reduction_ppm)
        object.__setattr__(self, "experiment_id", experiment_id)
        object.__setattr__(self, "experiment_fingerprint", experiment_fingerprint)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "constraint_status", status)
        object.__setattr__(self, "constraint_assessment_evidence_ids", evidence)
        object.__setattr__(self, "expected_information_gain_ppm", info_gain)
        object.__setattr__(self, "expected_uncertainty_reduction_ppm", uncertainty)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"experiment-selection-candidate-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.candidate_id)
        if supplied and supplied != derived:
            raise ValueError("experiment selection candidate_id does not match canonical identity")
        object.__setattr__(self, "candidate_id", derived)

    @property
    def eligible(self) -> bool:
        return self.constraint_status == "ELIGIBLE"

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "experiment_id": self.experiment_id,
            "experiment_fingerprint": self.experiment_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "constraint_status": self.constraint_status,
            "constraint_assessment_evidence_ids": list(self.constraint_assessment_evidence_ids),
            "expected_information_gain_ppm": self.expected_information_gain_ppm,
            "expected_uncertainty_reduction_ppm": self.expected_uncertainty_reduction_ppm,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"candidate_id": self.candidate_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"candidate_id": self.candidate_id, **self.identity_payload(), "eligible": self.eligible, "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentSelectionCandidate":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        supplied_eligible = payload.pop("eligible", None)
        payload["constraint_assessment_evidence_ids"] = tuple(payload.get("constraint_assessment_evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="experiment selection candidate")
        if supplied_eligible is not None and bool(supplied_eligible) != item.eligible:
            raise ValueError("experiment selection candidate eligible flag mismatch")
        return item


@dataclass(frozen=True)
class ExperimentSelectionProposal:
    workspace_id: str
    scope_id: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    candidates: tuple[ExperimentSelectionCandidate | Mapping[str, Any], ...]
    selected_candidate_id: str
    selection_policy_id: str
    selection_policy_fingerprint: str
    producer_principal_id: str
    evidence_ids: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    selection_id: str = ""
    contract_id: str = EXPERIMENT_CONTRACT_ID
    contract_version: str = EXPERIMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != EXPERIMENT_CONTRACT_ID or self.contract_version != EXPERIMENT_CONTRACT_VERSION:
            raise ValueError("unsupported experiment selection proposal contract")
        workspace = _required("selection workspace_id", self.workspace_id)
        scope = _required("selection scope_id", self.scope_id)
        revision_id = _required("selection problem_revision_id", self.problem_revision_id)
        revision_fingerprint = _sha256("selection problem_revision_fingerprint", self.problem_revision_fingerprint)
        candidates = tuple(
            row if isinstance(row, ExperimentSelectionCandidate) else ExperimentSelectionCandidate.from_dict(row)
            for row in self.candidates
        )
        if not candidates:
            raise ValueError("experiment selection proposal requires candidates")
        candidate_ids = [row.candidate_id for row in candidates]
        if len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("experiment selection candidate IDs must be unique")
        for candidate in candidates:
            if candidate.problem_revision_id != revision_id or candidate.problem_revision_fingerprint != revision_fingerprint:
                raise ValueError("experiment selection candidate revision must match exact proposal revision")
        candidates = tuple(sorted(candidates, key=lambda row: row.candidate_id))
        selected = _optional(self.selected_candidate_id)
        eligible_ids = {row.candidate_id for row in candidates if row.eligible}
        if eligible_ids and not selected:
            raise ValueError("experiment selection proposal with eligible candidates requires a selection")
        if not eligible_ids and selected:
            raise ValueError("experiment selection proposal cannot select when no candidate is eligible")
        if selected and selected not in eligible_ids:
            raise PermissionError("experiment selection cannot choose a candidate blocked by hard constraints")
        policy_id = _required("selection_policy_id", self.selection_policy_id)
        policy_fingerprint = _sha256("selection_policy_fingerprint", self.selection_policy_fingerprint)
        producer = _required("selection producer_principal_id", self.producer_principal_id)
        evidence = _uniq(self.evidence_ids, name="selection evidence_id", allow_empty=False)
        object.__setattr__(self, "workspace_id", workspace)
        object.__setattr__(self, "scope_id", scope)
        object.__setattr__(self, "problem_revision_id", revision_id)
        object.__setattr__(self, "problem_revision_fingerprint", revision_fingerprint)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "selected_candidate_id", selected)
        object.__setattr__(self, "selection_policy_id", policy_id)
        object.__setattr__(self, "selection_policy_fingerprint", policy_fingerprint)
        object.__setattr__(self, "producer_principal_id", producer)
        object.__setattr__(self, "evidence_ids", evidence)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        derived = f"experiment-selection-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = _optional(self.selection_id)
        if supplied and supplied != derived:
            raise ValueError("experiment selection_id does not match canonical identity")
        object.__setattr__(self, "selection_id", derived)

    @property
    def selected_experiment_id(self) -> str:
        if not self.selected_candidate_id:
            return ""
        by_id = {row.candidate_id: row for row in self.candidates}
        return by_id[self.selected_candidate_id].experiment_id

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "candidates": [row.to_dict() for row in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
            "selection_policy_id": self.selection_policy_id,
            "selection_policy_fingerprint": self.selection_policy_fingerprint,
            "producer_principal_id": self.producer_principal_id,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"selection_id": self.selection_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "selection_id": self.selection_id,
            **self.identity_payload(),
            "selected_experiment_id": self.selected_experiment_id,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExperimentSelectionProposal":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        supplied_experiment = payload.pop("selected_experiment_id", None)
        payload["candidates"] = tuple(payload.get("candidates") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="experiment selection proposal")
        if supplied_experiment is not None and str(supplied_experiment) != item.selected_experiment_id:
            raise ValueError("experiment selection selected_experiment_id mismatch")
        return item


def propose_experiment_selection(
    *,
    workspace_id: str,
    scope_id: str,
    problem_revision_id: str,
    problem_revision_fingerprint: str,
    candidates: Sequence[ExperimentSelectionCandidate | Mapping[str, Any]],
    selection_policy_id: str,
    selection_policy_fingerprint: str,
    producer_principal_id: str,
    evidence_ids: Sequence[str],
    metadata: Mapping[str, Any] | None = None,
) -> ExperimentSelectionProposal:
    """Deterministically rank only externally-qualified eligible experiments.

    This function does not evaluate safety, evidence sufficiency, resource
    capacity, or revision authority. Those hard gates are inputs backed by
    existing AASM Evidence. Selection remains a proposal and cannot execute an
    experiment, reserve resources, dispatch effects, accept artifacts, or mint
    facts.
    """

    items = tuple(
        row if isinstance(row, ExperimentSelectionCandidate) else ExperimentSelectionCandidate.from_dict(row)
        for row in candidates
    )
    eligible = [row for row in items if row.eligible]
    selected = ""
    if eligible:
        winner = sorted(
            eligible,
            key=lambda row: (
                -row.expected_information_gain_ppm,
                -row.expected_uncertainty_reduction_ppm,
                row.experiment_id,
                row.candidate_id,
            ),
        )[0]
        selected = winner.candidate_id
    return ExperimentSelectionProposal(
        workspace_id=workspace_id,
        scope_id=scope_id,
        problem_revision_id=problem_revision_id,
        problem_revision_fingerprint=problem_revision_fingerprint,
        candidates=items,
        selected_candidate_id=selected,
        selection_policy_id=selection_policy_id,
        selection_policy_fingerprint=selection_policy_fingerprint,
        producer_principal_id=producer_principal_id,
        evidence_ids=tuple(evidence_ids),
        metadata=dict(metadata or {}),
    )


def experiment_contract() -> dict[str, Any]:
    return {
        "contract_id": EXPERIMENT_CONTRACT_ID,
        "contract_version": EXPERIMENT_CONTRACT_VERSION,
        "stability": EXPERIMENT_STABILITY,
        "variable_roles": list(EXPERIMENT_VARIABLE_ROLES),
        "binding_kinds": list(EXPERIMENT_BINDING_KINDS),
        "binding_statuses": list(EXPERIMENT_BINDING_STATUSES),
        "selection_constraint_statuses": list(EXPERIMENT_SELECTION_CONSTRAINT_STATUSES),
        "problem_revision_binding": "EXACT_ID_AND_FINGERPRINT_REQUIRED",
        "hypothesis": "EXPLICIT_AND_REVISION_BOUND_THROUGH_EXPERIMENT",
        "controlled_and_measured_variables": "EXPLICIT_TYPED_DISJOINT_SEMANTIC_REFS",
        "procedure": "ORDERED_DESCRIPTIVE_STEPS_ONLY_NO_EXECUTABLE_PAYLOAD",
        "environment": "EXACT_EXISTING_EXECUTION_ENVIRONMENT_REFERENCE_REQUIRED",
        "fixture_identity": "EXACT_EXISTING_IDENTITY_REFERENCE_OR_EXPLICIT_NOT_APPLICABLE",
        "calibration_identity": "EXACT_EXISTING_CALIBRATION_REFERENCE_OR_EXPLICIT_NOT_APPLICABLE",
        "expected_discriminating_result": "AT_LEAST_TWO_EXPLICIT_OUTCOMES_WITH_HYPOTHESIS_RELATIONS",
        "evidence_floor": "EXACT_EXISTING_EVIDENCE_POLICY_OR_OBLIGATION_REFERENCE_REQUIRED",
        "resources": "EXACT_EXISTING_RESOURCE_DEMAND_REFERENCE_REQUIRED_NO_RESERVATION",
        "safety_and_risk": "EXACT_EXISTING_SAFETY_OR_RISK_REFERENCE_REQUIRED",
        "selection_order": "HARD_REVISION_SAFETY_EVIDENCE_RESOURCE_GATE_BEFORE_INFORMATION_VALUE",
        "selection_objective": "MAX_EXPECTED_INFORMATION_GAIN_THEN_UNCERTAINTY_REDUCTION_DETERMINISTIC_TIE_BREAK",
        "constraint_status_source": "EXISTING_ASSESSMENT_EVIDENCE_ONLY_NOT_REEVALUATED_HERE",
        "information_gain_encoding": "INTEGER_PARTS_PER_MILLION_NO_BINARY_FLOAT",
        "selection_is_proposal_only": True,
        "experiment_execution": "NONE",
        "effect_dispatch": "NONE",
        "resource_reservation": "NONE",
        "fact_authority": "NONE",
        "effect_authority": "NONE",
        "artifact_acceptance": "NONE",
        "problem_mutation": "NONE",
        "parallel_evidence_store": "NONE",
        "parallel_resource_plane": "NONE",
        "parallel_safety_plane": "NONE",
        "parallel_authority_evaluator": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "EXPERIMENT_CONTRACT_ID",
    "EXPERIMENT_CONTRACT_VERSION",
    "EXPERIMENT_STABILITY",
    "EXPERIMENT_VARIABLE_ROLES",
    "EXPERIMENT_BINDING_KINDS",
    "EXPERIMENT_BINDING_STATUSES",
    "EXPERIMENT_SELECTION_CONSTRAINT_STATUSES",
    "ExperimentContextBinding",
    "ExperimentHypothesis",
    "ExperimentVariable",
    "ExperimentProcedureStep",
    "ExperimentOutcomeCriterion",
    "ExperimentSpec",
    "ExperimentSelectionCandidate",
    "ExperimentSelectionProposal",
    "propose_experiment_selection",
    "experiment_contract",
]
