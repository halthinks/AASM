from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
import re
from typing import Any, Mapping, Sequence

from .semantic_dependencies import SemanticNodeRef
from .semantic_evolution import ExternalReference, ProblemDelta, ProblemRevision
from .semantic_result import semantic_fingerprint


REFINEMENT_PROPOSAL_CONTRACT_ID = "aasm.refinement.proposal.v1"
REFINEMENT_LOOP_CONTRACT_ID = "aasm.refinement.loop.v1"
REFINEMENT_CONTRACT_VERSION = "0.1.0"
REFINEMENT_STABILITY = "FOUNDATION_EXPERIMENTAL"

REFINEMENT_KINDS = (
    "NO_GOOD",
    "BOUND_TIGHTENING",
    "NEW_CONSTRAINT",
    "DOMAIN_RESTRICTION",
    "OBJECTIVE_CORRECTION",
    "REQUIRED_OBSERVATION",
    "VERIFICATION_ESCALATION",
    "MODEL_CORRECTION",
    "SCENARIO_ADDITION",
    "RULE_APPLICABILITY_CORRECTION",
)

REFINEMENT_VALIDATION_RESULTS = ("VALID", "INVALID", "INCONCLUSIVE")
REFINEMENT_TERMINATION_REASONS = (
    "GOAL_SATISFIED",
    "NO_PROGRESS",
    "OSCILLATION",
    "RESOURCE_EXHAUSTED",
    "INCONCLUSIVE",
    "CONFLICT",
    "MANUAL_HOLD",
)
REFINEMENT_BLOCKING_TERMINATIONS = ("NO_PROGRESS", "OSCILLATION")

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def _required(name: str, value: Any) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"refinement {name} is required")
    return text


def _optional(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _sha256(name: str, value: Any) -> str:
    text = _required(name, value).lower()
    if not _SHA256.fullmatch(text):
        raise ValueError(f"refinement {name} must be a lowercase 64-hex SHA-256 digest")
    return text


def _uniq(values: Sequence[Any], *, name: str, allow_empty: bool = True) -> tuple[str, ...]:
    out = tuple(sorted({_required(name, value) for value in values}))
    if not out and not allow_empty:
        raise ValueError(f"refinement {name} requires at least one value")
    return out


def _portable(value: Any) -> Any:
    if hasattr(value, "identity_payload"):
        return _portable(value.identity_payload())
    if hasattr(value, "to_dict"):
        return _portable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _portable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_portable(item) for item in value]
    if isinstance(value, float):
        raise TypeError("binary floating-point values are forbidden in refinement portable identity")
    if isinstance(value, (str, int, bool)) or value is None:
        return value
    raise TypeError(f"refinement value is not portable JSON: {type(value)!r}")


def _canonical_positive_decimal(name: str, value: Any) -> str:
    if isinstance(value, float):
        raise TypeError("binary floating-point resource estimates are forbidden")
    text = _required(name, value)
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"refinement {name} must be a finite canonical decimal") from exc
    if not number.is_finite() or number <= 0:
        raise ValueError(f"refinement {name} must be finite and greater than zero")
    normalized = format(number, "f")
    if "." in normalized:
        normalized = normalized.rstrip("0").rstrip(".")
    if normalized in ("", "-0", "+0"):
        normalized = "0"
    return normalized


def _node_refs(values: Sequence[SemanticNodeRef | Mapping[str, Any]]) -> tuple[SemanticNodeRef, ...]:
    refs = tuple(
        item if isinstance(item, SemanticNodeRef) else SemanticNodeRef.from_dict(item)
        for item in values
    )
    by_key = {item.key: item for item in refs}
    if len(by_key) != len(refs):
        raise ValueError("refinement semantic node references must be unique")
    return tuple(sorted(refs, key=lambda item: item.key))


def _external_refs(values: Sequence[ExternalReference | Mapping[str, Any]]) -> tuple[ExternalReference, ...]:
    refs = tuple(
        item if isinstance(item, ExternalReference) else ExternalReference.from_dict(item)
        for item in values
    )
    by_fingerprint = {item.fingerprint: item for item in refs}
    if len(by_fingerprint) != len(refs):
        raise ValueError("refinement external references must be unique")
    for item in refs:
        _portable(item.to_dict())
    return tuple(sorted(refs, key=lambda item: (item.namespace, item.external_id, item.revision, item.role, item.fingerprint)))


def _round_trip_fingerprint(item: Any, supplied: str, *, label: str) -> None:
    if supplied and supplied != item.fingerprint:
        raise ValueError(f"{label} fingerprint mismatch")


@dataclass(frozen=True)
class RefinementApplicability:
    workspace_id: str
    scope_id: str
    problem_revision_id: str
    problem_revision_fingerprint: str
    subject_ids: tuple[str, ...] = ()
    environment_fingerprints: tuple[str, ...] = ()
    external_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("workspace_id", "scope_id", "problem_revision_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        object.__setattr__(
            self,
            "problem_revision_fingerprint",
            _sha256("problem_revision_fingerprint", self.problem_revision_fingerprint),
        )
        object.__setattr__(self, "subject_ids", _uniq(self.subject_ids, name="subject_id"))
        object.__setattr__(
            self,
            "environment_fingerprints",
            tuple(sorted({_sha256("environment_fingerprint", value) for value in self.environment_fingerprints})),
        )
        object.__setattr__(
            self,
            "external_reference_fingerprints",
            tuple(sorted({_sha256("external_reference_fingerprint", value) for value in self.external_reference_fingerprints})),
        )
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "subject_ids": list(self.subject_ids),
            "environment_fingerprints": list(self.environment_fingerprints),
            "external_reference_fingerprints": list(self.external_reference_fingerprints),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefinementApplicability":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        for name in ("subject_ids", "environment_fingerprints", "external_reference_fingerprints"):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="refinement applicability")
        return item


@dataclass(frozen=True)
class RefinementResourceEstimate:
    resource_kind: str
    amount: str
    unit: str
    resource_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "resource_kind", _required("resource_kind", self.resource_kind))
        object.__setattr__(self, "amount", _canonical_positive_decimal("resource amount", self.amount))
        object.__setattr__(self, "unit", _required("resource unit", self.unit))
        object.__setattr__(self, "resource_id", _optional(self.resource_id))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "resource_kind": self.resource_kind,
            "amount": self.amount,
            "unit": self.unit,
            "resource_id": self.resource_id,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefinementResourceEstimate":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="refinement resource estimate")
        return item


@dataclass(frozen=True)
class RefinementSemanticEffect:
    target_problem_fingerprint: str
    target_semantic_projection_fingerprint: str
    added_external_reference_fingerprints: tuple[str, ...] = ()
    removed_external_reference_fingerprints: tuple[str, ...] = ()
    modified_external_reference_fingerprints: tuple[str, ...] = ()
    truth_change_roots: tuple[SemanticNodeRef | Mapping[str, Any], ...] = ()
    changed_semantic_ids: tuple[str, ...] = ()
    changed_quantity_ids: tuple[str, ...] = ()
    changed_rule_ids: tuple[str, ...] = ()
    changed_objective_ids: tuple[str, ...] = ()
    changed_scenario_ids: tuple[str, ...] = ()
    changed_artifact_ids: tuple[str, ...] = ()
    invalidated_evidence_ids: tuple[str, ...] = ()
    preserved_evidence_ids: tuple[str, ...] = ()
    impacted_obligation_ids: tuple[str, ...] = ()
    impacted_solver_object_ids: tuple[str, ...] = ()
    incremental_eligibility: str = "REQUIRES_REBUILD"
    warm_start_eligibility: str = "FORBIDDEN"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_problem_fingerprint",
            _sha256("target_problem_fingerprint", self.target_problem_fingerprint),
        )
        object.__setattr__(
            self,
            "target_semantic_projection_fingerprint",
            _sha256("target_semantic_projection_fingerprint", self.target_semantic_projection_fingerprint),
        )
        for name in (
            "added_external_reference_fingerprints",
            "removed_external_reference_fingerprints",
            "modified_external_reference_fingerprints",
        ):
            object.__setattr__(
                self,
                name,
                tuple(sorted({_sha256(name, value) for value in getattr(self, name)})),
            )
        changed_refs = [
            *self.added_external_reference_fingerprints,
            *self.removed_external_reference_fingerprints,
            *self.modified_external_reference_fingerprints,
        ]
        if len(changed_refs) != len(set(changed_refs)):
            raise ValueError("refinement external reference cannot be added/removed/modified simultaneously")
        object.__setattr__(self, "truth_change_roots", _node_refs(self.truth_change_roots))
        for name in (
            "changed_semantic_ids",
            "changed_quantity_ids",
            "changed_rule_ids",
            "changed_objective_ids",
            "changed_scenario_ids",
            "changed_artifact_ids",
            "invalidated_evidence_ids",
            "preserved_evidence_ids",
            "impacted_obligation_ids",
            "impacted_solver_object_ids",
        ):
            object.__setattr__(self, name, _uniq(getattr(self, name), name=name))
        if set(self.invalidated_evidence_ids) & set(self.preserved_evidence_ids):
            raise ValueError("refinement expected effect cannot both invalidate and preserve Evidence")
        if self.incremental_eligibility not in (
            "REQUIRES_REBUILD",
            "INCREMENTAL_CANDIDATE",
            "INCREMENTAL_CERTIFIED",
        ):
            raise ValueError("invalid refinement incremental eligibility")
        if self.warm_start_eligibility not in (
            "FORBIDDEN",
            "PERFORMANCE_ONLY_CANDIDATE",
            "PERFORMANCE_ONLY_VALIDATED",
        ):
            raise ValueError("invalid refinement warm-start eligibility")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "target_problem_fingerprint": self.target_problem_fingerprint,
            "target_semantic_projection_fingerprint": self.target_semantic_projection_fingerprint,
            "added_external_reference_fingerprints": list(self.added_external_reference_fingerprints),
            "removed_external_reference_fingerprints": list(self.removed_external_reference_fingerprints),
            "modified_external_reference_fingerprints": list(self.modified_external_reference_fingerprints),
            "truth_change_roots": [item.to_dict() for item in self.truth_change_roots],
            "changed_semantic_ids": list(self.changed_semantic_ids),
            "changed_quantity_ids": list(self.changed_quantity_ids),
            "changed_rule_ids": list(self.changed_rule_ids),
            "changed_objective_ids": list(self.changed_objective_ids),
            "changed_scenario_ids": list(self.changed_scenario_ids),
            "changed_artifact_ids": list(self.changed_artifact_ids),
            "invalidated_evidence_ids": list(self.invalidated_evidence_ids),
            "preserved_evidence_ids": list(self.preserved_evidence_ids),
            "impacted_obligation_ids": list(self.impacted_obligation_ids),
            "impacted_solver_object_ids": list(self.impacted_solver_object_ids),
            "incremental_eligibility": self.incremental_eligibility,
            "warm_start_eligibility": self.warm_start_eligibility,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefinementSemanticEffect":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        for name in (
            "added_external_reference_fingerprints",
            "removed_external_reference_fingerprints",
            "modified_external_reference_fingerprints",
            "truth_change_roots",
            "changed_semantic_ids",
            "changed_quantity_ids",
            "changed_rule_ids",
            "changed_objective_ids",
            "changed_scenario_ids",
            "changed_artifact_ids",
            "invalidated_evidence_ids",
            "preserved_evidence_ids",
            "impacted_obligation_ids",
            "impacted_solver_object_ids",
        ):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="refinement semantic effect")
        return item

    def compare_delta(self, delta: ProblemDelta | Mapping[str, Any]) -> dict[str, Any]:
        change = delta if isinstance(delta, ProblemDelta) else ProblemDelta.from_dict(delta)
        actual = {
            "target_problem_fingerprint": change.target_problem_fingerprint,
            "target_semantic_projection_fingerprint": change.target_semantic_projection_fingerprint,
            "added_external_reference_fingerprints": tuple(sorted(row.fingerprint for row in change.added_external_references)),
            "removed_external_reference_fingerprints": tuple(sorted(row.fingerprint for row in change.removed_external_references)),
            "modified_external_reference_fingerprints": tuple(sorted(row.fingerprint for row in change.modified_external_references)),
            "truth_change_roots": tuple(sorted(row.key for row in change.truth_change_roots)),
            "changed_semantic_ids": change.changed_semantic_ids,
            "changed_quantity_ids": change.changed_quantity_ids,
            "changed_rule_ids": change.changed_rule_ids,
            "changed_objective_ids": change.changed_objective_ids,
            "changed_scenario_ids": change.changed_scenario_ids,
            "changed_artifact_ids": change.changed_artifact_ids,
            "invalidated_evidence_ids": change.invalidated_evidence_ids,
            "preserved_evidence_ids": change.preserved_evidence_ids,
            "impacted_obligation_ids": change.impacted_obligation_ids,
            "impacted_solver_object_ids": change.impacted_solver_object_ids,
            "incremental_eligibility": change.incremental_eligibility,
            "warm_start_eligibility": change.warm_start_eligibility,
        }
        expected = {
            "target_problem_fingerprint": self.target_problem_fingerprint,
            "target_semantic_projection_fingerprint": self.target_semantic_projection_fingerprint,
            "added_external_reference_fingerprints": self.added_external_reference_fingerprints,
            "removed_external_reference_fingerprints": self.removed_external_reference_fingerprints,
            "modified_external_reference_fingerprints": self.modified_external_reference_fingerprints,
            "truth_change_roots": tuple(row.key for row in self.truth_change_roots),
            "changed_semantic_ids": self.changed_semantic_ids,
            "changed_quantity_ids": self.changed_quantity_ids,
            "changed_rule_ids": self.changed_rule_ids,
            "changed_objective_ids": self.changed_objective_ids,
            "changed_scenario_ids": self.changed_scenario_ids,
            "changed_artifact_ids": self.changed_artifact_ids,
            "invalidated_evidence_ids": self.invalidated_evidence_ids,
            "preserved_evidence_ids": self.preserved_evidence_ids,
            "impacted_obligation_ids": self.impacted_obligation_ids,
            "impacted_solver_object_ids": self.impacted_solver_object_ids,
            "incremental_eligibility": self.incremental_eligibility,
            "warm_start_eligibility": self.warm_start_eligibility,
        }
        errors = [f"DELTA_{name.upper()}_MISMATCH" for name in expected if expected[name] != actual[name]]
        return {"valid": not errors, "errors": errors, "expected": expected, "actual": actual}


@dataclass(frozen=True)
class RefinementProposal:
    refinement_kind: str
    workspace_id: str
    scope_id: str
    base_revision_id: str
    base_revision_fingerprint: str
    producer_principal_id: str
    trigger_evidence_ids: tuple[str, ...]
    applicability: RefinementApplicability | Mapping[str, Any]
    expected_semantic_effect: RefinementSemanticEffect | Mapping[str, Any]
    trigger_reasoning_artifact_ids: tuple[str, ...] = ()
    trigger_conflict_ids: tuple[str, ...] = ()
    trigger_core_ids: tuple[str, ...] = ()
    target_semantic_refs: tuple[SemanticNodeRef | Mapping[str, Any], ...] = ()
    target_external_refs: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    proposed_semantic_payload: Mapping[str, Any] = field(default_factory=dict)
    dependency_fingerprints: tuple[str, ...] = ()
    independent_validation_required: bool = True
    resource_estimates: tuple[RefinementResourceEstimate | Mapping[str, Any], ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    proposal_id: str = ""
    status: str = "PROPOSED"
    contract_id: str = REFINEMENT_PROPOSAL_CONTRACT_ID
    contract_version: str = REFINEMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != REFINEMENT_PROPOSAL_CONTRACT_ID or self.contract_version != REFINEMENT_CONTRACT_VERSION:
            raise ValueError("unsupported refinement proposal contract")
        kind = _required("refinement_kind", self.refinement_kind).upper()
        if kind not in REFINEMENT_KINDS:
            raise ValueError(f"unsupported refinement kind: {kind}")
        object.__setattr__(self, "refinement_kind", kind)
        for name in ("workspace_id", "scope_id", "base_revision_id", "producer_principal_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        object.__setattr__(
            self,
            "base_revision_fingerprint",
            _sha256("base_revision_fingerprint", self.base_revision_fingerprint),
        )
        if self.status != "PROPOSED":
            raise ValueError("refinement proposal status must be PROPOSED")
        triggers = _uniq(self.trigger_evidence_ids, name="trigger_evidence_id", allow_empty=False)
        object.__setattr__(self, "trigger_evidence_ids", triggers)
        object.__setattr__(
            self,
            "trigger_reasoning_artifact_ids",
            _uniq(self.trigger_reasoning_artifact_ids, name="trigger_reasoning_artifact_id"),
        )
        object.__setattr__(self, "trigger_conflict_ids", _uniq(self.trigger_conflict_ids, name="trigger_conflict_id"))
        object.__setattr__(self, "trigger_core_ids", _uniq(self.trigger_core_ids, name="trigger_core_id"))
        object.__setattr__(self, "target_semantic_refs", _node_refs(self.target_semantic_refs))
        object.__setattr__(self, "target_external_refs", _external_refs(self.target_external_refs))
        object.__setattr__(
            self,
            "dependency_fingerprints",
            tuple(sorted({_sha256("dependency_fingerprint", value) for value in self.dependency_fingerprints})),
        )
        applicability = (
            self.applicability
            if isinstance(self.applicability, RefinementApplicability)
            else RefinementApplicability.from_dict(self.applicability)
        )
        if applicability.workspace_id != self.workspace_id or applicability.scope_id != self.scope_id:
            raise ValueError("refinement applicability workspace/scope must exactly match proposal")
        if applicability.problem_revision_id != self.base_revision_id:
            raise ValueError("refinement applicability revision ID must exactly match proposal base")
        if applicability.problem_revision_fingerprint != self.base_revision_fingerprint:
            raise ValueError("refinement applicability revision fingerprint must exactly match proposal base")
        object.__setattr__(self, "applicability", applicability)
        effect = (
            self.expected_semantic_effect
            if isinstance(self.expected_semantic_effect, RefinementSemanticEffect)
            else RefinementSemanticEffect.from_dict(self.expected_semantic_effect)
        )
        object.__setattr__(self, "expected_semantic_effect", effect)
        resources = tuple(
            item if isinstance(item, RefinementResourceEstimate) else RefinementResourceEstimate.from_dict(item)
            for item in self.resource_estimates
        )
        resource_keys = [(item.resource_kind, item.resource_id, item.unit) for item in resources]
        if len(resource_keys) != len(set(resource_keys)):
            raise ValueError("refinement resource estimates must be unique per kind/resource/unit")
        object.__setattr__(
            self,
            "resource_estimates",
            tuple(sorted(resources, key=lambda item: (item.resource_kind, item.resource_id, item.unit, item.amount))),
        )
        object.__setattr__(self, "proposed_semantic_payload", _portable(dict(self.proposed_semantic_payload)))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        if not self.proposal_id:
            object.__setattr__(self, "proposal_id", f"refinement-proposal-{semantic_fingerprint(self.identity_payload())[:24]}")

    def semantic_payload(self) -> dict[str, Any]:
        return {
            "refinement_kind": self.refinement_kind,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "base_revision_id": self.base_revision_id,
            "base_revision_fingerprint": self.base_revision_fingerprint,
            "applicability": self.applicability.to_dict(),
            "target_semantic_refs": [item.to_dict() for item in self.target_semantic_refs],
            "target_external_refs": [item.to_dict() for item in self.target_external_refs],
            "proposed_semantic_payload": _portable(self.proposed_semantic_payload),
            "dependency_fingerprints": list(self.dependency_fingerprints),
            "independent_validation_required": bool(self.independent_validation_required),
            "expected_semantic_effect": self.expected_semantic_effect.to_dict(),
        }

    @property
    def semantic_refinement_fingerprint(self) -> str:
        return semantic_fingerprint(self.semantic_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            **self.semantic_payload(),
            "producer_principal_id": self.producer_principal_id,
            "trigger_evidence_ids": list(self.trigger_evidence_ids),
            "trigger_reasoning_artifact_ids": list(self.trigger_reasoning_artifact_ids),
            "trigger_conflict_ids": list(self.trigger_conflict_ids),
            "trigger_core_ids": list(self.trigger_core_ids),
            "resource_estimates": [item.to_dict() for item in self.resource_estimates],
            "metadata": _portable(self.metadata),
            "status": self.status,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"proposal_id": self.proposal_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            **self.identity_payload(),
            "semantic_refinement_fingerprint": self.semantic_refinement_fingerprint,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefinementProposal":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        supplied_semantic = _optional(payload.pop("semantic_refinement_fingerprint", ""))
        for name in (
            "trigger_evidence_ids",
            "trigger_reasoning_artifact_ids",
            "trigger_conflict_ids",
            "trigger_core_ids",
            "target_semantic_refs",
            "target_external_refs",
            "dependency_fingerprints",
            "resource_estimates",
        ):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="refinement proposal")
        if supplied_semantic and supplied_semantic != item.semantic_refinement_fingerprint:
            raise ValueError("refinement semantic fingerprint mismatch")
        return item


@dataclass(frozen=True)
class RefinementValidation:
    proposal_id: str
    proposal_fingerprint: str
    semantic_refinement_fingerprint: str
    base_revision_id: str
    base_revision_fingerprint: str
    applicability_fingerprint: str
    validator_principal_id: str
    result: str
    supporting_evidence_ids: tuple[str, ...] = ()
    reasoning: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    validation_id: str = ""
    contract_id: str = REFINEMENT_LOOP_CONTRACT_ID
    contract_version: str = REFINEMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != REFINEMENT_LOOP_CONTRACT_ID or self.contract_version != REFINEMENT_CONTRACT_VERSION:
            raise ValueError("unsupported refinement loop contract")
        for name in ("proposal_id", "base_revision_id", "validator_principal_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        for name in (
            "proposal_fingerprint",
            "semantic_refinement_fingerprint",
            "base_revision_fingerprint",
            "applicability_fingerprint",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        result = _required("validation result", self.result).upper()
        if result not in REFINEMENT_VALIDATION_RESULTS:
            raise ValueError(f"unsupported refinement validation result: {result}")
        object.__setattr__(self, "result", result)
        evidence = _uniq(self.supporting_evidence_ids, name="supporting_evidence_id")
        if result == "VALID" and not evidence:
            raise ValueError("VALID refinement validation requires supporting Evidence")
        object.__setattr__(self, "supporting_evidence_ids", evidence)
        object.__setattr__(self, "reasoning", str(self.reasoning))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        if not self.validation_id:
            object.__setattr__(self, "validation_id", f"refinement-validation-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "proposal_id": self.proposal_id,
            "proposal_fingerprint": self.proposal_fingerprint,
            "semantic_refinement_fingerprint": self.semantic_refinement_fingerprint,
            "base_revision_id": self.base_revision_id,
            "base_revision_fingerprint": self.base_revision_fingerprint,
            "applicability_fingerprint": self.applicability_fingerprint,
            "validator_principal_id": self.validator_principal_id,
            "result": self.result,
            "supporting_evidence_ids": list(self.supporting_evidence_ids),
            "reasoning": self.reasoning,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"validation_id": self.validation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"validation_id": self.validation_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefinementValidation":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        payload["supporting_evidence_ids"] = tuple(payload.get("supporting_evidence_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="refinement validation")
        return item


@dataclass(frozen=True)
class RefinementApplication:
    proposal_id: str
    proposal_fingerprint: str
    validation_id: str
    validation_fingerprint: str
    semantic_refinement_fingerprint: str
    base_revision_id: str
    base_revision_fingerprint: str
    delta_id: str
    delta_fingerprint: str
    target_revision_id: str
    target_revision_fingerprint: str
    producer_principal_id: str
    actor_principal_id: str
    scoped_authorization_evidence_id: str
    problem_transition_evidence_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    application_id: str = ""
    contract_id: str = REFINEMENT_LOOP_CONTRACT_ID
    contract_version: str = REFINEMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != REFINEMENT_LOOP_CONTRACT_ID or self.contract_version != REFINEMENT_CONTRACT_VERSION:
            raise ValueError("unsupported refinement loop contract")
        for name in (
            "proposal_id",
            "validation_id",
            "base_revision_id",
            "delta_id",
            "target_revision_id",
            "producer_principal_id",
            "actor_principal_id",
            "scoped_authorization_evidence_id",
            "problem_transition_evidence_id",
        ):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        if self.actor_principal_id == self.producer_principal_id:
            raise PermissionError("refinement producer/evaluator cannot directly apply its own delta")
        for name in (
            "proposal_fingerprint",
            "validation_fingerprint",
            "semantic_refinement_fingerprint",
            "base_revision_fingerprint",
            "delta_fingerprint",
            "target_revision_fingerprint",
        ):
            object.__setattr__(self, name, _sha256(name, getattr(self, name)))
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        if not self.application_id:
            object.__setattr__(self, "application_id", f"refinement-application-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "proposal_id": self.proposal_id,
            "proposal_fingerprint": self.proposal_fingerprint,
            "validation_id": self.validation_id,
            "validation_fingerprint": self.validation_fingerprint,
            "semantic_refinement_fingerprint": self.semantic_refinement_fingerprint,
            "base_revision_id": self.base_revision_id,
            "base_revision_fingerprint": self.base_revision_fingerprint,
            "delta_id": self.delta_id,
            "delta_fingerprint": self.delta_fingerprint,
            "target_revision_id": self.target_revision_id,
            "target_revision_fingerprint": self.target_revision_fingerprint,
            "producer_principal_id": self.producer_principal_id,
            "actor_principal_id": self.actor_principal_id,
            "scoped_authorization_evidence_id": self.scoped_authorization_evidence_id,
            "problem_transition_evidence_id": self.problem_transition_evidence_id,
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"application_id": self.application_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"application_id": self.application_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefinementApplication":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="refinement application")
        return item


@dataclass(frozen=True)
class RefinementLoopTermination:
    problem_id: str
    base_revision_id: str
    base_revision_fingerprint: str
    head_revision_id: str
    head_revision_fingerprint: str
    reason: str
    evidence_ids: tuple[str, ...]
    actor_principal_id: str
    blocking_obligation_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    termination_id: str = ""
    contract_id: str = REFINEMENT_LOOP_CONTRACT_ID
    contract_version: str = REFINEMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != REFINEMENT_LOOP_CONTRACT_ID or self.contract_version != REFINEMENT_CONTRACT_VERSION:
            raise ValueError("unsupported refinement loop contract")
        for name in ("problem_id", "base_revision_id", "head_revision_id", "actor_principal_id"):
            object.__setattr__(self, name, _required(name, getattr(self, name)))
        object.__setattr__(self, "base_revision_fingerprint", _sha256("base_revision_fingerprint", self.base_revision_fingerprint))
        object.__setattr__(self, "head_revision_fingerprint", _sha256("head_revision_fingerprint", self.head_revision_fingerprint))
        reason = _required("termination reason", self.reason).upper()
        if reason not in REFINEMENT_TERMINATION_REASONS:
            raise ValueError(f"unsupported refinement termination reason: {reason}")
        object.__setattr__(self, "reason", reason)
        evidence = _uniq(self.evidence_ids, name="termination_evidence_id", allow_empty=False)
        object.__setattr__(self, "evidence_ids", evidence)
        blocking = _uniq(self.blocking_obligation_ids, name="blocking_obligation_id")
        if reason in REFINEMENT_BLOCKING_TERMINATIONS and not blocking:
            raise ValueError(f"{reason} termination requires an existing blocking obligation reference")
        object.__setattr__(self, "blocking_obligation_ids", blocking)
        object.__setattr__(self, "metadata", _portable(dict(self.metadata)))
        if not self.termination_id:
            object.__setattr__(self, "termination_id", f"refinement-termination-{semantic_fingerprint(self.identity_payload())[:24]}")

    @property
    def is_success(self) -> bool:
        return self.reason == "GOAL_SATISFIED"

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "problem_id": self.problem_id,
            "base_revision_id": self.base_revision_id,
            "base_revision_fingerprint": self.base_revision_fingerprint,
            "head_revision_id": self.head_revision_id,
            "head_revision_fingerprint": self.head_revision_fingerprint,
            "reason": self.reason,
            "evidence_ids": list(self.evidence_ids),
            "actor_principal_id": self.actor_principal_id,
            "blocking_obligation_ids": list(self.blocking_obligation_ids),
            "metadata": _portable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"termination_id": self.termination_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "termination_id": self.termination_id,
            **self.identity_payload(),
            "is_success": self.is_success,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RefinementLoopTermination":
        payload = deepcopy(dict(value))
        supplied = _optional(payload.pop("fingerprint", ""))
        supplied_success = payload.pop("is_success", None)
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        payload["blocking_obligation_ids"] = tuple(payload.get("blocking_obligation_ids") or ())
        item = cls(**payload)
        _round_trip_fingerprint(item, supplied, label="refinement termination")
        if supplied_success is not None and bool(supplied_success) != item.is_success:
            raise ValueError("refinement termination success flag mismatch")
        return item


def validate_refinement_validation(
    proposal: RefinementProposal | Mapping[str, Any],
    validation: RefinementValidation | Mapping[str, Any],
) -> dict[str, Any]:
    item = proposal if isinstance(proposal, RefinementProposal) else RefinementProposal.from_dict(proposal)
    check = validation if isinstance(validation, RefinementValidation) else RefinementValidation.from_dict(validation)
    errors: list[str] = []
    if check.proposal_id != item.proposal_id:
        errors.append("PROPOSAL_ID_MISMATCH")
    if check.proposal_fingerprint != item.fingerprint:
        errors.append("PROPOSAL_FINGERPRINT_MISMATCH")
    if check.semantic_refinement_fingerprint != item.semantic_refinement_fingerprint:
        errors.append("SEMANTIC_REFINEMENT_FINGERPRINT_MISMATCH")
    if check.base_revision_id != item.base_revision_id:
        errors.append("BASE_REVISION_ID_MISMATCH")
    if check.base_revision_fingerprint != item.base_revision_fingerprint:
        errors.append("BASE_REVISION_FINGERPRINT_MISMATCH")
    if check.applicability_fingerprint != item.applicability.fingerprint:
        errors.append("APPLICABILITY_FINGERPRINT_MISMATCH")
    if item.independent_validation_required and check.validator_principal_id == item.producer_principal_id:
        errors.append("INDEPENDENT_VALIDATOR_REQUIRED")
    if check.result != "VALID":
        errors.append(f"VALIDATION_RESULT_{check.result}")
    return {
        "valid": not errors,
        "application_eligible": not errors,
        "errors": errors,
        "proposal_id": item.proposal_id,
        "validation_id": check.validation_id,
    }


def validate_refinement_delta(
    proposal: RefinementProposal | Mapping[str, Any],
    base_revision: ProblemRevision | Mapping[str, Any],
    delta: ProblemDelta | Mapping[str, Any],
) -> dict[str, Any]:
    item = proposal if isinstance(proposal, RefinementProposal) else RefinementProposal.from_dict(proposal)
    base = base_revision if isinstance(base_revision, ProblemRevision) else ProblemRevision.from_dict(base_revision)
    change = delta if isinstance(delta, ProblemDelta) else ProblemDelta.from_dict(delta)
    errors: list[str] = []
    if item.base_revision_id != base.revision_id:
        errors.append("PROPOSAL_BASE_REVISION_ID_MISMATCH")
    if item.base_revision_fingerprint != base.fingerprint:
        errors.append("PROPOSAL_BASE_REVISION_FINGERPRINT_MISMATCH")
    if item.applicability.problem_revision_id != base.revision_id:
        errors.append("APPLICABILITY_BASE_REVISION_ID_MISMATCH")
    if item.applicability.problem_revision_fingerprint != base.fingerprint:
        errors.append("APPLICABILITY_BASE_REVISION_FINGERPRINT_MISMATCH")
    if change.base_revision_id != base.revision_id:
        errors.append("DELTA_BASE_REVISION_ID_MISMATCH")
    if change.base_revision_fingerprint != base.fingerprint:
        errors.append("DELTA_BASE_REVISION_FINGERPRINT_MISMATCH")
    if change.caused_by_refinement_id != item.proposal_id:
        errors.append("DELTA_REFINEMENT_LINEAGE_MISMATCH")
    if not set(item.dependency_fingerprints).issubset(set(base.dependency_fingerprints)):
        errors.append("REFINEMENT_DEPENDENCY_NOT_APPLICABLE_TO_BASE")
    effect = item.expected_semantic_effect.compare_delta(change)
    errors.extend(effect["errors"])
    return {
        "valid": not errors,
        "errors": errors,
        "proposal_id": item.proposal_id,
        "base_revision_id": base.revision_id,
        "delta_id": change.delta_id,
        "effect_validation": effect,
    }


def validate_refinement_application(
    proposal: RefinementProposal | Mapping[str, Any],
    validation: RefinementValidation | Mapping[str, Any],
    application: RefinementApplication | Mapping[str, Any],
    delta: ProblemDelta | Mapping[str, Any],
    target_revision: ProblemRevision | Mapping[str, Any],
) -> dict[str, Any]:
    item = proposal if isinstance(proposal, RefinementProposal) else RefinementProposal.from_dict(proposal)
    check = validation if isinstance(validation, RefinementValidation) else RefinementValidation.from_dict(validation)
    app = application if isinstance(application, RefinementApplication) else RefinementApplication.from_dict(application)
    change = delta if isinstance(delta, ProblemDelta) else ProblemDelta.from_dict(delta)
    target = target_revision if isinstance(target_revision, ProblemRevision) else ProblemRevision.from_dict(target_revision)
    errors = list(validate_refinement_validation(item, check)["errors"])
    if change.base_revision_id != item.base_revision_id:
        errors.append("APPLICATION_DELTA_BASE_REVISION_ID_MISMATCH")
    if change.base_revision_fingerprint != item.base_revision_fingerprint:
        errors.append("APPLICATION_DELTA_BASE_REVISION_FINGERPRINT_MISMATCH")
    if change.caused_by_refinement_id != item.proposal_id:
        errors.append("APPLICATION_DELTA_REFINEMENT_LINEAGE_MISMATCH")
    errors.extend(item.expected_semantic_effect.compare_delta(change)["errors"])
    expected_pairs = {
        "proposal_id": (app.proposal_id, item.proposal_id),
        "proposal_fingerprint": (app.proposal_fingerprint, item.fingerprint),
        "validation_id": (app.validation_id, check.validation_id),
        "validation_fingerprint": (app.validation_fingerprint, check.fingerprint),
        "semantic_refinement_fingerprint": (app.semantic_refinement_fingerprint, item.semantic_refinement_fingerprint),
        "base_revision_id": (app.base_revision_id, item.base_revision_id),
        "base_revision_fingerprint": (app.base_revision_fingerprint, item.base_revision_fingerprint),
        "delta_id": (app.delta_id, change.delta_id),
        "delta_fingerprint": (app.delta_fingerprint, change.fingerprint),
        "target_revision_id": (app.target_revision_id, target.revision_id),
        "target_revision_fingerprint": (app.target_revision_fingerprint, target.fingerprint),
        "producer_principal_id": (app.producer_principal_id, item.producer_principal_id),
    }
    for name, (actual, expected) in expected_pairs.items():
        if actual != expected:
            errors.append(f"APPLICATION_{name.upper()}_MISMATCH")
    if app.actor_principal_id == item.producer_principal_id:
        errors.append("PRODUCER_DIRECT_APPLICATION_FORBIDDEN")
    if target.created_from_delta_id != change.delta_id:
        errors.append("TARGET_DELTA_LINEAGE_MISMATCH")
    if target.parent_revision_ids != (item.base_revision_id,):
        errors.append("TARGET_PARENT_MISMATCH")
    return {
        "valid": not errors,
        "errors": errors,
        "application_id": app.application_id,
        "application_key": refinement_application_key(item),
    }


def refinement_application_key(proposal: RefinementProposal | Mapping[str, Any]) -> str:
    item = proposal if isinstance(proposal, RefinementProposal) else RefinementProposal.from_dict(proposal)
    return semantic_fingerprint(
        {
            "base_revision_id": item.base_revision_id,
            "base_revision_fingerprint": item.base_revision_fingerprint,
            "semantic_refinement_fingerprint": item.semantic_refinement_fingerprint,
        }
    )


def refinement_contract() -> dict[str, Any]:
    return {
        "proposal_contract_id": REFINEMENT_PROPOSAL_CONTRACT_ID,
        "loop_contract_id": REFINEMENT_LOOP_CONTRACT_ID,
        "contract_version": REFINEMENT_CONTRACT_VERSION,
        "stability": REFINEMENT_STABILITY,
        "refinement_kinds": list(REFINEMENT_KINDS),
        "validation_results": list(REFINEMENT_VALIDATION_RESULTS),
        "termination_reasons": list(REFINEMENT_TERMINATION_REASONS),
        "pipeline": (
            "SOLVE_VERIFY_DIAGNOSE_PROPOSE_VALIDATE_APPLICABILITY_AUTHORIZE_"
            "EXISTING_PROBLEM_DELTA_EXISTING_PROBLEM_REVISION_TRUTH_MAINTENANCE_REPLAN"
        ),
        "producer_direct_application": "FORBIDDEN_ALWAYS_EVALUATOR_OR_PRODUCER_CANNOT_APPLY_OWN_DELTA",
        "independent_validation": "EXPLICIT_PER_PROPOSAL_AND_FAIL_CLOSED_WHEN_REQUIRED",
        "problem_delta_lineage": "EXISTING_PROBLEM_DELTA_CAUSED_BY_REFINEMENT_ID_REQUIRED",
        "problem_revision_commit": "EXISTING_COMMIT_PROBLEM_REVISION_TRANSITION_ONLY_NO_PARALLEL_REVISION_SYSTEM",
        "duplicate_application": "EXACT_BASE_REVISION_PLUS_SEMANTIC_REFINEMENT_FINGERPRINT",
        "stale_base_policy": "FAIL_CLOSED_EXACT_BASE_REVISION_ID_AND_FINGERPRINT_REQUIRED",
        "applicability_broadening": "FORBIDDEN_EXACT_PROPOSAL_APPLICABILITY_FINGERPRINT_REQUIRED",
        "delta_broadening": "FORBIDDEN_EXACT_EXPECTED_SEMANTIC_EFFECT_MUST_MATCH_PROBLEM_DELTA",
        "blocking_termination": "NO_PROGRESS_OR_OSCILLATION_REQUIRES_EXISTING_BLOCKING_OBLIGATION_REFERENCE",
        "resource_estimate": "PORTABLE_ESTIMATE_ONLY_EXISTING_RESOURCE_GOVERNANCE_REMAINS_REQUIRED",
        "resource_estimate_reserves_resources": False,
        "resource_estimate_consumes_resources": False,
        "resource_exhaustion_means_success": False,
        "inconclusive_means_success": False,
        "goal_satisfied_termination_mints_truth": False,
        "proposal_existence_grants_fact_authority": False,
        "proposal_existence_grants_effect_authority": False,
        "validation_is_reusable_authorization_token": False,
        "application_record_grants_fact_authority": False,
        "application_record_grants_effect_authority": False,
        "termination_grants_authority": False,
        "direct_solver_mutation": "NONE",
        "direct_problem_revision_mutation": "NONE",
        "parallel_refinement_store": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_problem_revision_system": "NONE",
        "parallel_truth_table": "NONE",
        "parallel_authority_evaluator": "NONE",
        "parallel_resource_plane": "NONE",
        "parallel_effect_lifecycle": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "REFINEMENT_PROPOSAL_CONTRACT_ID",
    "REFINEMENT_LOOP_CONTRACT_ID",
    "REFINEMENT_CONTRACT_VERSION",
    "REFINEMENT_STABILITY",
    "REFINEMENT_KINDS",
    "REFINEMENT_VALIDATION_RESULTS",
    "REFINEMENT_TERMINATION_REASONS",
    "REFINEMENT_BLOCKING_TERMINATIONS",
    "RefinementApplicability",
    "RefinementResourceEstimate",
    "RefinementSemanticEffect",
    "RefinementProposal",
    "RefinementValidation",
    "RefinementApplication",
    "RefinementLoopTermination",
    "validate_refinement_validation",
    "validate_refinement_delta",
    "validate_refinement_application",
    "refinement_application_key",
    "refinement_contract",
]
