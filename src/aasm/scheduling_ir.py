from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .model_features import ModelAdmissionReport, ModelFeatureSet, ProviderCapabilityManifest
from .semantic_result import semantic_fingerprint


SCHEDULING_MODEL_CONTRACT_ID = "aasm.optimization.scheduling.v1"
SCHEDULING_MODEL_CONTRACT_VERSION = "0.1.0"
SCHEDULING_ASSIGNMENT_CONTRACT_ID = "aasm.optimization.scheduling-assignment.v1"
SCHEDULING_ASSIGNMENT_CONTRACT_VERSION = "0.1.0"
SCHEDULING_VALIDATION_CONTRACT_ID = "aasm.optimization.scheduling-validation.v1"
SCHEDULING_VALIDATION_CONTRACT_VERSION = "0.1.0"
SCHEDULING_PROVIDER_BINDING_CONTRACT_ID = "aasm.optimization.scheduling-provider-binding.v1"
SCHEDULING_PROVIDER_BINDING_CONTRACT_VERSION = "0.1.0"
SCHEDULING_IR_STABILITY = "FOUNDATION_EXPERIMENTAL"
SCHEDULING_VALIDATOR_ID = "aasm.checker.scheduling-assignment.v1"
SCHEDULING_VALIDATOR_VERSION = "0.1.0"


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
    raise TypeError(f"scheduling IR value is not JSON serializable: {type(value)!r}")


def _admission_from_dict(value: Mapping[str, Any]) -> ModelAdmissionReport:
    payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
    for name in ("exact_features", "approximate_features", "verifier_only_features", "unsupported_features", "reasons"):
        payload[name] = tuple(payload.get(name) or ())
    return ModelAdmissionReport(**payload)


@dataclass(frozen=True)
class SchedulingTask:
    task_id: str
    duration: int
    earliest_start: int = 0
    latest_end: int | None = None
    source_reference_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_id", _required(self.task_id, "task_id"))
        if isinstance(self.duration, bool) or int(self.duration) != self.duration or int(self.duration) <= 0:
            raise ValueError("scheduling task duration must be a positive integer")
        if isinstance(self.earliest_start, bool) or int(self.earliest_start) != self.earliest_start or int(self.earliest_start) < 0:
            raise ValueError("scheduling earliest_start must be a non-negative integer")
        latest = None if self.latest_end is None else int(self.latest_end)
        if latest is not None and latest < int(self.earliest_start) + int(self.duration):
            raise ValueError("scheduling latest_end cannot precede earliest feasible completion")
        object.__setattr__(self, "duration", int(self.duration))
        object.__setattr__(self, "earliest_start", int(self.earliest_start))
        object.__setattr__(self, "latest_end", latest)
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "duration": self.duration,
            "earliest_start": self.earliest_start,
            "latest_end": self.latest_end,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
            "metadata": _jsonable(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SchedulingTask":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class PrecedenceConstraint:
    before_task_id: str
    after_task_id: str
    min_lag: int = 0
    source_reference_fingerprints: tuple[str, ...] = ()
    constraint_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "before_task_id", _required(self.before_task_id, "before_task_id"))
        object.__setattr__(self, "after_task_id", _required(self.after_task_id, "after_task_id"))
        if self.before_task_id == self.after_task_id:
            raise ValueError("precedence constraint cannot self-reference")
        if isinstance(self.min_lag, bool) or int(self.min_lag) != self.min_lag or int(self.min_lag) < 0:
            raise ValueError("precedence min_lag must be a non-negative integer")
        object.__setattr__(self, "min_lag", int(self.min_lag))
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"precedence-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": "PRECEDENCE",
            "before_task_id": self.before_task_id,
            "after_task_id": self.after_task_id,
            "min_lag": self.min_lag,
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PrecedenceConstraint":
        payload = deepcopy(dict(value)); payload.pop("kind", None); payload.pop("fingerprint", None)
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class NoOverlapConstraint:
    task_ids: tuple[str, ...]
    source_reference_fingerprints: tuple[str, ...] = ()
    constraint_id: str = ""

    def __post_init__(self) -> None:
        task_ids = _uniq(self.task_ids)
        if len(task_ids) < 2:
            raise ValueError("no-overlap constraint requires at least two tasks")
        object.__setattr__(self, "task_ids", task_ids)
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"no-overlap-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": "NO_OVERLAP",
            "task_ids": list(self.task_ids),
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NoOverlapConstraint":
        payload = deepcopy(dict(value)); payload.pop("kind", None); payload.pop("fingerprint", None)
        payload["task_ids"] = tuple(payload.get("task_ids") or ())
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class CumulativeResourceConstraint:
    resource_id: str
    capacity: int
    demands: Mapping[str, int]
    source_reference_fingerprints: tuple[str, ...] = ()
    constraint_id: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "resource_id", _required(self.resource_id, "resource_id"))
        if isinstance(self.capacity, bool) or int(self.capacity) != self.capacity or int(self.capacity) <= 0:
            raise ValueError("cumulative capacity must be a positive integer")
        demands = {}
        for task_id, amount in sorted(self.demands.items()):
            if isinstance(amount, bool) or int(amount) != amount or int(amount) <= 0:
                raise ValueError("cumulative demands must be positive integers")
            demands[str(task_id)] = int(amount)
        if not demands:
            raise ValueError("cumulative demands must be positive integers")
        object.__setattr__(self, "capacity", int(self.capacity))
        object.__setattr__(self, "demands", demands)
        object.__setattr__(self, "source_reference_fingerprints", _uniq(self.source_reference_fingerprints))
        if not self.constraint_id:
            object.__setattr__(self, "constraint_id", f"cumulative-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "kind": "CUMULATIVE_RESOURCE",
            "resource_id": self.resource_id,
            "capacity": self.capacity,
            "demands": dict(self.demands),
            "source_reference_fingerprints": list(self.source_reference_fingerprints),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"constraint_id": self.constraint_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"constraint_id": self.constraint_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CumulativeResourceConstraint":
        payload = deepcopy(dict(value)); payload.pop("kind", None); payload.pop("fingerprint", None)
        payload["source_reference_fingerprints"] = tuple(payload.get("source_reference_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SchedulingModel:
    name: str
    horizon: int
    tasks: tuple[SchedulingTask | Mapping[str, Any], ...]
    precedences: tuple[PrecedenceConstraint | Mapping[str, Any], ...] = ()
    no_overlaps: tuple[NoOverlapConstraint | Mapping[str, Any], ...] = ()
    cumulative_resources: tuple[CumulativeResourceConstraint | Mapping[str, Any], ...] = ()
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    model_id: str = ""
    contract_id: str = SCHEDULING_MODEL_CONTRACT_ID
    contract_version: str = SCHEDULING_MODEL_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required(self.name, "scheduling model name"))
        if self.contract_id != SCHEDULING_MODEL_CONTRACT_ID or self.contract_version != SCHEDULING_MODEL_CONTRACT_VERSION:
            raise ValueError("unsupported scheduling model contract")
        if isinstance(self.horizon, bool) or int(self.horizon) != self.horizon or int(self.horizon) <= 0:
            raise ValueError("scheduling horizon must be a positive integer")
        tasks = tuple(row if isinstance(row, SchedulingTask) else SchedulingTask.from_dict(row) for row in self.tasks)
        ids = [row.task_id for row in tasks]
        if not ids or len(ids) != len(set(ids)):
            raise ValueError("scheduling task IDs must be non-empty and unique")
        known = set(ids)
        precedences = tuple(row if isinstance(row, PrecedenceConstraint) else PrecedenceConstraint.from_dict(row) for row in self.precedences)
        no_overlaps = tuple(row if isinstance(row, NoOverlapConstraint) else NoOverlapConstraint.from_dict(row) for row in self.no_overlaps)
        cumulative = tuple(row if isinstance(row, CumulativeResourceConstraint) else CumulativeResourceConstraint.from_dict(row) for row in self.cumulative_resources)
        for task in tasks:
            if task.earliest_start + task.duration > int(self.horizon):
                raise ValueError(f"task cannot fit within scheduling horizon: {task.task_id}")
            if task.latest_end is not None and task.latest_end > int(self.horizon):
                raise ValueError(f"task latest_end exceeds scheduling horizon: {task.task_id}")
        for row in precedences:
            if row.before_task_id not in known or row.after_task_id not in known:
                raise ValueError("precedence constraint references unknown task")
        for row in no_overlaps:
            missing = sorted(set(row.task_ids) - known)
            if missing:
                raise ValueError(f"no-overlap constraint references unknown tasks: {missing}")
        for row in cumulative:
            missing = sorted(set(row.demands) - known)
            if missing:
                raise ValueError(f"cumulative resource references unknown tasks: {missing}")
        constraint_ids = [row.constraint_id for row in (*precedences, *no_overlaps, *cumulative)]
        if len(constraint_ids) != len(set(constraint_ids)):
            raise ValueError("scheduling constraint IDs must be unique")
        object.__setattr__(self, "horizon", int(self.horizon))
        object.__setattr__(self, "tasks", tuple(sorted(tasks, key=lambda row: row.task_id)))
        object.__setattr__(self, "precedences", tuple(sorted(precedences, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "no_overlaps", tuple(sorted(no_overlaps, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "cumulative_resources", tuple(sorted(cumulative, key=lambda row: row.constraint_id)))
        object.__setattr__(self, "problem_revision_id", str(self.problem_revision_id).strip())
        object.__setattr__(self, "problem_revision_fingerprint", str(self.problem_revision_fingerprint).strip())
        if bool(self.problem_revision_id) != bool(self.problem_revision_fingerprint):
            raise ValueError("problem revision ID and fingerprint must be supplied together")
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.model_id:
            object.__setattr__(self, "model_id", f"scheduling-model-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "name": self.name,
            "horizon": self.horizon,
            "tasks": [row.to_dict() for row in self.tasks],
            "precedences": [row.to_dict() for row in self.precedences],
            "no_overlaps": [row.to_dict() for row in self.no_overlaps],
            "cumulative_resources": [row.to_dict() for row in self.cumulative_resources],
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"model_id": self.model_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"model_id": self.model_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SchedulingModel":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        for name in ("tasks", "precedences", "no_overlaps", "cumulative_resources"):
            payload[name] = tuple(payload.get(name) or ())
        return cls(**payload)


@dataclass(frozen=True)
class SchedulingAssignment:
    model_id: str
    model_fingerprint: str
    starts: Mapping[str, int]
    assignment_id: str = ""
    contract_id: str = SCHEDULING_ASSIGNMENT_CONTRACT_ID
    contract_version: str = SCHEDULING_ASSIGNMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_id", _required(self.model_id, "assignment model_id"))
        object.__setattr__(self, "model_fingerprint", _required(self.model_fingerprint, "assignment model_fingerprint"))
        if self.contract_id != SCHEDULING_ASSIGNMENT_CONTRACT_ID or self.contract_version != SCHEDULING_ASSIGNMENT_CONTRACT_VERSION:
            raise ValueError("unsupported scheduling assignment contract")
        starts = {}
        for task_id, value in sorted(self.starts.items()):
            if isinstance(value, bool) or int(value) != value or int(value) < 0:
                raise ValueError("scheduling starts must be non-negative integers")
            starts[str(task_id)] = int(value)
        object.__setattr__(self, "starts", starts)
        if not self.assignment_id:
            object.__setattr__(self, "assignment_id", f"schedule-assignment-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "model_id": self.model_id,
            "model_fingerprint": self.model_fingerprint,
            "starts": dict(self.starts),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"assignment_id": self.assignment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"assignment_id": self.assignment_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SchedulingAssignment":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class SchedulingValidationReport:
    model_fingerprint: str
    assignment_fingerprint: str
    valid: bool
    violations: tuple[Mapping[str, Any], ...] = ()
    validator_id: str = SCHEDULING_VALIDATOR_ID
    validator_version: str = SCHEDULING_VALIDATOR_VERSION
    report_id: str = ""
    contract_id: str = SCHEDULING_VALIDATION_CONTRACT_ID
    contract_version: str = SCHEDULING_VALIDATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "model_fingerprint", _required(self.model_fingerprint, "validation model_fingerprint"))
        object.__setattr__(self, "assignment_fingerprint", _required(self.assignment_fingerprint, "validation assignment_fingerprint"))
        if self.contract_id != SCHEDULING_VALIDATION_CONTRACT_ID or self.contract_version != SCHEDULING_VALIDATION_CONTRACT_VERSION:
            raise ValueError("unsupported scheduling validation contract")
        normalized = tuple(sorted((_jsonable(dict(row)) for row in self.violations), key=lambda row: (str(row.get("code")), str(row.get("constraint_id")), str(row.get("task_id")))))
        object.__setattr__(self, "violations", normalized)
        if bool(self.valid) != (not normalized):
            raise ValueError("scheduling valid flag must match absence of violations")
        if not self.report_id:
            object.__setattr__(self, "report_id", f"scheduling-validation-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "model_fingerprint": self.model_fingerprint,
            "assignment_fingerprint": self.assignment_fingerprint,
            "valid": bool(self.valid),
            "violations": [_jsonable(row) for row in self.violations],
            "validator_id": self.validator_id,
            "validator_version": self.validator_version,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"report_id": self.report_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"report_id": self.report_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def validate_scheduling_assignment(model: SchedulingModel | Mapping[str, Any], assignment: SchedulingAssignment | Mapping[str, Any]) -> SchedulingValidationReport:
    source = model if isinstance(model, SchedulingModel) else SchedulingModel.from_dict(model)
    item = assignment if isinstance(assignment, SchedulingAssignment) else SchedulingAssignment.from_dict(assignment)
    violations: list[dict[str, Any]] = []
    if item.model_id != source.model_id or item.model_fingerprint != source.fingerprint:
        violations.append({"code": "MODEL_BINDING_MISMATCH"})
        return SchedulingValidationReport(source.fingerprint, item.fingerprint, False, tuple(violations))
    task_ids = {row.task_id for row in source.tasks}
    if set(item.starts) != task_ids:
        violations.append({"code": "ASSIGNMENT_TASK_SET_MISMATCH", "missing": sorted(task_ids - set(item.starts)), "unexpected": sorted(set(item.starts) - task_ids)})
        return SchedulingValidationReport(source.fingerprint, item.fingerprint, False, tuple(violations))
    tasks = {row.task_id: row for row in source.tasks}
    intervals = {}
    for task_id, task in tasks.items():
        start = item.starts[task_id]
        end = start + task.duration
        intervals[task_id] = (start, end)
        if start < task.earliest_start:
            violations.append({"code": "EARLIEST_START_VIOLATION", "task_id": task_id, "start": start, "earliest_start": task.earliest_start})
        latest = source.horizon if task.latest_end is None else task.latest_end
        if end > latest:
            violations.append({"code": "LATEST_END_VIOLATION", "task_id": task_id, "end": end, "latest_end": latest})
    for constraint in source.precedences:
        before_end = intervals[constraint.before_task_id][1]
        after_start = intervals[constraint.after_task_id][0]
        required = before_end + constraint.min_lag
        if after_start < required:
            violations.append({"code": "PRECEDENCE_VIOLATION", "constraint_id": constraint.constraint_id, "before_task_id": constraint.before_task_id, "after_task_id": constraint.after_task_id, "required_after_start": required, "actual_after_start": after_start})
    for constraint in source.no_overlaps:
        ids = constraint.task_ids
        for index, first in enumerate(ids):
            for second in ids[index + 1:]:
                first_start, first_end = intervals[first]
                second_start, second_end = intervals[second]
                if first_start < second_end and second_start < first_end:
                    violations.append({"code": "NO_OVERLAP_VIOLATION", "constraint_id": constraint.constraint_id, "task_ids": [first, second]})
    for constraint in source.cumulative_resources:
        boundaries = sorted({point for task_id in constraint.demands for point in intervals[task_id]})
        for left, right in zip(boundaries, boundaries[1:]):
            if left == right:
                continue
            active = [task_id for task_id in constraint.demands if intervals[task_id][0] < right and intervals[task_id][1] > left]
            load = sum(constraint.demands[task_id] for task_id in active)
            if load > constraint.capacity:
                violations.append({"code": "CUMULATIVE_CAPACITY_VIOLATION", "constraint_id": constraint.constraint_id, "resource_id": constraint.resource_id, "interval": [left, right], "active_task_ids": sorted(active), "load": load, "capacity": constraint.capacity})
    return SchedulingValidationReport(source.fingerprint, item.fingerprint, not violations, tuple(violations))


@dataclass(frozen=True)
class SchedulingProviderBinding:
    model_id: str
    model_fingerprint: str
    feature_set_id: str
    feature_set_fingerprint: str
    provider_manifest_id: str
    provider_manifest_fingerprint: str
    admission_report_id: str
    admission_report_fingerprint: str
    provider_id: str
    environment_fingerprint: str = ""
    binding_id: str = ""
    contract_id: str = SCHEDULING_PROVIDER_BINDING_CONTRACT_ID
    contract_version: str = SCHEDULING_PROVIDER_BINDING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("model_id", "model_fingerprint", "feature_set_id", "feature_set_fingerprint", "provider_manifest_id", "provider_manifest_fingerprint", "admission_report_id", "admission_report_fingerprint", "provider_id"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SCHEDULING_PROVIDER_BINDING_CONTRACT_ID or self.contract_version != SCHEDULING_PROVIDER_BINDING_CONTRACT_VERSION:
            raise ValueError("unsupported scheduling provider binding contract")
        object.__setattr__(self, "environment_fingerprint", str(self.environment_fingerprint).strip())
        if not self.binding_id:
            object.__setattr__(self, "binding_id", f"scheduling-provider-binding-{semantic_fingerprint(self.identity_payload())[:20]}")

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
            "environment_fingerprint": self.environment_fingerprint,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"binding_id": self.binding_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def bind_scheduling_provider(
    model: SchedulingModel | Mapping[str, Any],
    *,
    feature_set: ModelFeatureSet | Mapping[str, Any],
    provider_manifest: ProviderCapabilityManifest | Mapping[str, Any],
    admission_report: ModelAdmissionReport | Mapping[str, Any],
) -> SchedulingProviderBinding:
    source = model if isinstance(model, SchedulingModel) else SchedulingModel.from_dict(model)
    features = feature_set if isinstance(feature_set, ModelFeatureSet) else ModelFeatureSet.from_dict(feature_set)
    manifest = provider_manifest if isinstance(provider_manifest, ProviderCapabilityManifest) else ProviderCapabilityManifest.from_dict(provider_manifest)
    admission = admission_report if isinstance(admission_report, ModelAdmissionReport) else _admission_from_dict(admission_report)
    if features.model_fingerprint != source.fingerprint:
        raise ValueError("scheduling feature set does not bind model fingerprint")
    required = {row.feature_id for row in features.features}
    if "GLOBAL_SCHEDULING" not in required:
        raise ValueError("scheduling feature set must declare GLOBAL_SCHEDULING")
    if source.problem_revision_id:
        if features.problem_revision_id != source.problem_revision_id or features.problem_revision_fingerprint != source.problem_revision_fingerprint:
            raise ValueError("scheduling feature-set revision binding mismatch")
    if admission.feature_set_id != features.feature_set_id or admission.feature_set_fingerprint != features.fingerprint:
        raise ValueError("scheduling admission report does not bind feature set")
    if admission.provider_manifest_id != manifest.manifest_id or admission.provider_manifest_fingerprint != manifest.fingerprint:
        raise ValueError("scheduling admission report does not bind provider manifest")
    support = manifest.support_by_feature.get("GLOBAL_SCHEDULING")
    if support is None or support.support_level != "EXACT_NATIVE":
        raise ValueError("portable scheduling foundation requires EXACT_NATIVE GLOBAL_SCHEDULING provider support")
    if not admission.admitted or not admission.exact:
        raise ValueError("scheduling provider binding requires exact admission")
    if manifest.solver_families and "CP_SAT" not in manifest.solver_families:
        raise ValueError("scheduling provider must declare CP_SAT family in this foundation")
    return SchedulingProviderBinding(
        source.model_id,
        source.fingerprint,
        features.feature_set_id,
        features.fingerprint,
        manifest.manifest_id,
        manifest.fingerprint,
        admission.report_id,
        admission.fingerprint,
        manifest.provider_id,
        manifest.environment_fingerprint,
    )


def scheduling_ir_contract() -> dict[str, Any]:
    return {
        "model_contract_id": SCHEDULING_MODEL_CONTRACT_ID,
        "model_contract_version": SCHEDULING_MODEL_CONTRACT_VERSION,
        "assignment_contract_id": SCHEDULING_ASSIGNMENT_CONTRACT_ID,
        "validation_contract_id": SCHEDULING_VALIDATION_CONTRACT_ID,
        "provider_binding_contract_id": SCHEDULING_PROVIDER_BINDING_CONTRACT_ID,
        "stability": SCHEDULING_IR_STABILITY,
        "task_semantics": "MANDATORY_INTEGER_INTERVAL_START_DURATION_END",
        "global_constraints": ["PRECEDENCE", "NO_OVERLAP", "CUMULATIVE_RESOURCE"],
        "validation": "INDEPENDENT_ASSIGNMENT_CHECK_OVER_HALF_OPEN_INTERVALS",
        "provider_admission": "GLOBAL_SCHEDULING_EXACT_NATIVE_REQUIRED",
        "execution_adapter": "NOT_CLAIMED_BY_THIS_FOUNDATION",
        "approximation": "NOT_SUPPORTED_BY_THIS_CONTRACT",
        "truth_authority": "NONE",
    }


__all__ = [
    "SCHEDULING_MODEL_CONTRACT_ID",
    "SCHEDULING_MODEL_CONTRACT_VERSION",
    "SCHEDULING_ASSIGNMENT_CONTRACT_ID",
    "SCHEDULING_VALIDATION_CONTRACT_ID",
    "SCHEDULING_PROVIDER_BINDING_CONTRACT_ID",
    "SCHEDULING_VALIDATOR_ID",
    "SchedulingTask",
    "PrecedenceConstraint",
    "NoOverlapConstraint",
    "CumulativeResourceConstraint",
    "SchedulingModel",
    "SchedulingAssignment",
    "SchedulingValidationReport",
    "SchedulingProviderBinding",
    "validate_scheduling_assignment",
    "bind_scheduling_provider",
    "scheduling_ir_contract",
]
