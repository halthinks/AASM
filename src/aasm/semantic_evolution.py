from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


EXTERNAL_REFERENCE_CONTRACT_ID = "aasm.external.reference.v1"
EXTERNAL_REFERENCE_CONTRACT_VERSION = "0.1.0"
PROBLEM_REVISION_CONTRACT_ID = "aasm.problem.revision.v1"
PROBLEM_REVISION_CONTRACT_VERSION = "0.1.0"
PROBLEM_DELTA_CONTRACT_ID = "aasm.problem.delta.v1"
PROBLEM_DELTA_CONTRACT_VERSION = "0.1.0"
SEMANTIC_EVOLUTION_STABILITY = "FOUNDATION_EXPERIMENTAL"

INCREMENTAL_ELIGIBILITY = (
    "REQUIRES_REBUILD",
    "INCREMENTAL_CANDIDATE",
    "INCREMENTAL_CERTIFIED",
)
WARM_START_ELIGIBILITY = (
    "FORBIDDEN",
    "PERFORMANCE_ONLY_CANDIDATE",
    "PERFORMANCE_ONLY_VALIDATED",
)


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
    raise TypeError(f"semantic evolution value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class ExternalReference:
    namespace: str
    external_id: str
    role: str
    revision: str = ""
    source_fingerprint: str = ""
    source_location: Mapping[str, Any] = field(default_factory=dict)
    semantic_entity_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    contract_id: str = EXTERNAL_REFERENCE_CONTRACT_ID
    contract_version: str = EXTERNAL_REFERENCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("namespace", "external_id", "role"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ValueError(f"external reference {name} is required")
            object.__setattr__(self, name, value)
        if self.contract_id != EXTERNAL_REFERENCE_CONTRACT_ID or self.contract_version != EXTERNAL_REFERENCE_CONTRACT_VERSION:
            raise ValueError("unsupported external reference contract")
        object.__setattr__(self, "revision", str(self.revision).strip())
        object.__setattr__(self, "source_fingerprint", str(self.source_fingerprint).strip())
        object.__setattr__(self, "semantic_entity_id", str(self.semantic_entity_id).strip())
        object.__setattr__(self, "source_location", _jsonable(dict(self.source_location)))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    @property
    def key(self) -> str:
        suffix = f"@{self.revision}" if self.revision else ""
        return f"{self.namespace}:{self.external_id}{suffix}"

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "namespace": self.namespace,
            "external_id": self.external_id,
            "role": self.role,
            "revision": self.revision,
            "source_fingerprint": self.source_fingerprint,
            "source_location": _jsonable(self.source_location),
            "semantic_entity_id": self.semantic_entity_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "key": self.key, "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExternalReference":
        payload = deepcopy(dict(value))
        payload.pop("key", None)
        payload.pop("fingerprint", None)
        return cls(**payload)


def _refs(values: Sequence[ExternalReference | Mapping[str, Any]]) -> tuple[ExternalReference, ...]:
    refs = tuple(row if isinstance(row, ExternalReference) else ExternalReference.from_dict(row) for row in values)
    by_fingerprint = {row.fingerprint: row for row in refs}
    if len(by_fingerprint) != len(refs):
        raise ValueError("duplicate external reference in semantic evolution record")
    return tuple(sorted(refs, key=lambda row: (row.namespace, row.external_id, row.revision, row.role, row.fingerprint)))


@dataclass(frozen=True)
class ProblemRevision:
    problem_id: str
    problem_fingerprint: str
    semantic_projection_fingerprint: str
    parent_revision_ids: tuple[str, ...] = ()
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    environment_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    created_by: str = ""
    created_from_delta_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    revision_id: str = ""
    contract_id: str = PROBLEM_REVISION_CONTRACT_ID
    contract_version: str = PROBLEM_REVISION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("problem_id", "problem_fingerprint", "semantic_projection_fingerprint"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ValueError(f"problem revision {name} is required")
            object.__setattr__(self, name, value)
        if self.contract_id != PROBLEM_REVISION_CONTRACT_ID or self.contract_version != PROBLEM_REVISION_CONTRACT_VERSION:
            raise ValueError("unsupported problem revision contract")
        parents = _uniq(self.parent_revision_ids)
        refs = _refs(self.external_references)
        deps = _uniq(self.dependency_fingerprints)
        object.__setattr__(self, "parent_revision_ids", parents)
        object.__setattr__(self, "external_references", refs)
        object.__setattr__(self, "dependency_fingerprints", deps)
        object.__setattr__(self, "environment_fingerprint", str(self.environment_fingerprint).strip())
        object.__setattr__(self, "created_by", str(self.created_by).strip())
        object.__setattr__(self, "created_from_delta_id", str(self.created_from_delta_id).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        derived = self.revision_id.strip() if self.revision_id else f"problem-revision-{semantic_fingerprint(self.identity_payload())[:24]}"
        if derived in parents:
            raise ValueError("problem revision cannot list itself as a parent")
        object.__setattr__(self, "revision_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "problem_id": self.problem_id,
            "problem_fingerprint": self.problem_fingerprint,
            "semantic_projection_fingerprint": self.semantic_projection_fingerprint,
            "parent_revision_ids": list(self.parent_revision_ids),
            "external_references": [row.to_dict() for row in self.external_references],
            "environment_fingerprint": self.environment_fingerprint,
            "dependency_fingerprints": list(self.dependency_fingerprints),
            "created_by": self.created_by,
            "created_from_delta_id": self.created_from_delta_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"revision_id": self.revision_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"revision_id": self.revision_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProblemRevision":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["parent_revision_ids"] = tuple(payload.get("parent_revision_ids") or ())
        payload["external_references"] = tuple(payload.get("external_references") or ())
        payload["dependency_fingerprints"] = tuple(payload.get("dependency_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class ProblemDelta:
    base_revision_id: str
    base_revision_fingerprint: str
    target_problem_fingerprint: str
    target_semantic_projection_fingerprint: str
    added_external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    removed_external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    modified_external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
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
    caused_by_refinement_id: str = ""
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    delta_id: str = ""
    contract_id: str = PROBLEM_DELTA_CONTRACT_ID
    contract_version: str = PROBLEM_DELTA_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("base_revision_id", "base_revision_fingerprint", "target_problem_fingerprint", "target_semantic_projection_fingerprint"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise ValueError(f"problem delta {name} is required")
            object.__setattr__(self, name, value)
        if self.contract_id != PROBLEM_DELTA_CONTRACT_ID or self.contract_version != PROBLEM_DELTA_CONTRACT_VERSION:
            raise ValueError("unsupported problem delta contract")
        if self.incremental_eligibility not in INCREMENTAL_ELIGIBILITY:
            raise ValueError(f"invalid incremental eligibility: {self.incremental_eligibility}")
        if self.warm_start_eligibility not in WARM_START_ELIGIBILITY:
            raise ValueError(f"invalid warm-start eligibility: {self.warm_start_eligibility}")

        added = _refs(self.added_external_references)
        removed = _refs(self.removed_external_references)
        modified = _refs(self.modified_external_references)
        object.__setattr__(self, "added_external_references", added)
        object.__setattr__(self, "removed_external_references", removed)
        object.__setattr__(self, "modified_external_references", modified)
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
            "evidence_ids",
        ):
            object.__setattr__(self, name, _uniq(getattr(self, name)))
        if set(self.invalidated_evidence_ids) & set(self.preserved_evidence_ids):
            raise ValueError("evidence cannot be both invalidated and preserved by the same delta")
        changed_ref_fingerprints = [
            *(row.fingerprint for row in added),
            *(row.fingerprint for row in removed),
            *(row.fingerprint for row in modified),
        ]
        if len(changed_ref_fingerprints) != len(set(changed_ref_fingerprints)):
            raise ValueError("external reference cannot be added/removed/modified simultaneously in one delta")
        object.__setattr__(self, "caused_by_refinement_id", str(self.caused_by_refinement_id).strip())
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.delta_id:
            object.__setattr__(self, "delta_id", f"problem-delta-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "base_revision_id": self.base_revision_id,
            "base_revision_fingerprint": self.base_revision_fingerprint,
            "target_problem_fingerprint": self.target_problem_fingerprint,
            "target_semantic_projection_fingerprint": self.target_semantic_projection_fingerprint,
            "added_external_references": [row.to_dict() for row in self.added_external_references],
            "removed_external_references": [row.to_dict() for row in self.removed_external_references],
            "modified_external_references": [row.to_dict() for row in self.modified_external_references],
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
            "caused_by_refinement_id": self.caused_by_refinement_id,
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"delta_id": self.delta_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"delta_id": self.delta_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ProblemDelta":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        for name in (
            "added_external_references",
            "removed_external_references",
            "modified_external_references",
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
            "evidence_ids",
        ):
            payload[name] = tuple(payload.get(name) or ())
        return cls(**payload)


def validate_revision_transition(
    base: ProblemRevision | Mapping[str, Any],
    delta: ProblemDelta | Mapping[str, Any],
    target: ProblemRevision | Mapping[str, Any],
) -> dict[str, Any]:
    source = base if isinstance(base, ProblemRevision) else ProblemRevision.from_dict(base)
    change = delta if isinstance(delta, ProblemDelta) else ProblemDelta.from_dict(delta)
    result = target if isinstance(target, ProblemRevision) else ProblemRevision.from_dict(target)
    errors: list[str] = []
    if change.base_revision_id != source.revision_id:
        errors.append("BASE_REVISION_ID_MISMATCH")
    if change.base_revision_fingerprint != source.fingerprint:
        errors.append("BASE_REVISION_FINGERPRINT_MISMATCH")
    if change.target_problem_fingerprint != result.problem_fingerprint:
        errors.append("TARGET_PROBLEM_FINGERPRINT_MISMATCH")
    if change.target_semantic_projection_fingerprint != result.semantic_projection_fingerprint:
        errors.append("TARGET_SEMANTIC_PROJECTION_FINGERPRINT_MISMATCH")
    if source.problem_id != result.problem_id:
        errors.append("PROBLEM_ID_CHANGED")
    if source.revision_id not in result.parent_revision_ids:
        errors.append("TARGET_DOES_NOT_REFERENCE_BASE_PARENT")
    if result.created_from_delta_id and result.created_from_delta_id != change.delta_id:
        errors.append("TARGET_DELTA_LINEAGE_MISMATCH")
    return {
        "valid": not errors,
        "errors": errors,
        "base_revision_id": source.revision_id,
        "delta_id": change.delta_id,
        "target_revision_id": result.revision_id,
    }


def semantic_evolution_contract() -> dict[str, Any]:
    return {
        "external_reference_contract_id": EXTERNAL_REFERENCE_CONTRACT_ID,
        "external_reference_contract_version": EXTERNAL_REFERENCE_CONTRACT_VERSION,
        "problem_revision_contract_id": PROBLEM_REVISION_CONTRACT_ID,
        "problem_revision_contract_version": PROBLEM_REVISION_CONTRACT_VERSION,
        "problem_delta_contract_id": PROBLEM_DELTA_CONTRACT_ID,
        "problem_delta_contract_version": PROBLEM_DELTA_CONTRACT_VERSION,
        "stability": SEMANTIC_EVOLUTION_STABILITY,
        "revision_identity": "IMMUTABLE_FINGERPRINT_BOUND",
        "delta_identity": "BASE_REVISION_AND_TARGET_SEMANTIC_STATE_BOUND",
        "external_lineage": "TYPED_REFERENCE_NOT_FREEFORM_NAME_PARSING",
        "authority": "NONE_GRANTED_BY_REVISION_OR_DELTA",
        "truth_authority": "EXISTING_AASM_ADMISSION_PATH_ONLY",
        "stale_policy": "SUPERSEDED_RESULTS_REMAIN_HISTORICAL_EVIDENCE_ONLY",
        "change_impact": "EXISTING_AASM_SEMANTIC_DEPENDENCY_TRUTH_MAINTENANCE",
    }


__all__ = [
    "EXTERNAL_REFERENCE_CONTRACT_ID",
    "EXTERNAL_REFERENCE_CONTRACT_VERSION",
    "PROBLEM_REVISION_CONTRACT_ID",
    "PROBLEM_REVISION_CONTRACT_VERSION",
    "PROBLEM_DELTA_CONTRACT_ID",
    "PROBLEM_DELTA_CONTRACT_VERSION",
    "SEMANTIC_EVOLUTION_STABILITY",
    "INCREMENTAL_ELIGIBILITY",
    "WARM_START_ELIGIBILITY",
    "ExternalReference",
    "ProblemRevision",
    "ProblemDelta",
    "validate_revision_transition",
    "semantic_evolution_contract",
]
