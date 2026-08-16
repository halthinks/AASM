from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .optimization import OptimizationResult
from .semantic_result import semantic_fingerprint
from .solver_outcome_v2 import SolverOutcomeV2


SOLVER_EXECUTION_PROFILE_CONTRACT_ID = "aasm.solver.execution-profile.v1"
SOLVER_EXECUTION_PROFILE_CONTRACT_VERSION = "0.1.0"
SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID = "aasm.solver.runtime-provenance.v1"
SOLVER_RUNTIME_PROVENANCE_CONTRACT_VERSION = "0.1.0"
SOLVER_PROFILE_EVALUATION_CONTRACT_ID = "aasm.solver.profile-evaluation.v1"
SOLVER_PROFILE_EVALUATION_CONTRACT_VERSION = "0.1.0"
SOLVER_PROVENANCE_STABILITY = "QUALIFICATION_CANDIDATE"

DETERMINISM_POLICIES = ("BEST_EFFORT", "REPRODUCIBLE_REQUESTED", "STRICT_EFFECTIVE_OPTIONS")


def _required(value: str, name: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{name} is required")
    return normalized


def _optional(value: str) -> str:
    return str(value).strip()


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
    raise TypeError(f"solver provenance value is not JSON serializable: {type(value)!r}")


def _mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return _jsonable(dict(value))


def _positive_optional(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    parsed = int(value)
    if parsed <= 0:
        raise ValueError(f"{name} must be positive when supplied")
    return parsed


def _paired(left: str, right: str, left_name: str, right_name: str) -> tuple[str, str]:
    left_value, right_value = _optional(left), _optional(right)
    if bool(left_value) != bool(right_value):
        raise ValueError(f"{left_name} and {right_name} must be supplied together")
    return left_value, right_value


@dataclass(frozen=True)
class SolverExecutionProfile:
    name: str
    determinism_policy: str
    requested_options: Mapping[str, Any] = field(default_factory=dict)
    required_effective_options: Mapping[str, Any] = field(default_factory=dict)
    provider_id: str = ""
    provider_version: str = ""
    adapter_id: str = ""
    adapter_version: str = ""
    required_environment_fingerprint: str = ""
    required_formulation_id: str = ""
    required_formulation_fingerprint: str = ""
    required_problem_revision_id: str = ""
    required_problem_revision_fingerprint: str = ""
    numeric_policy_id: str = ""
    numeric_policy_fingerprint: str = ""
    required_worker_count: int | None = None
    required_thread_count: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    profile_id: str = ""
    contract_id: str = SOLVER_EXECUTION_PROFILE_CONTRACT_ID
    contract_version: str = SOLVER_EXECUTION_PROFILE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "name", _required(self.name, "execution profile name"))
        if self.contract_id != SOLVER_EXECUTION_PROFILE_CONTRACT_ID or self.contract_version != SOLVER_EXECUTION_PROFILE_CONTRACT_VERSION:
            raise ValueError("unsupported solver execution profile contract")
        if self.determinism_policy not in DETERMINISM_POLICIES:
            raise ValueError(f"invalid solver determinism policy: {self.determinism_policy}")
        object.__setattr__(self, "requested_options", _mapping(self.requested_options))
        object.__setattr__(self, "required_effective_options", _mapping(self.required_effective_options))
        provider_id, provider_version = _paired(self.provider_id, self.provider_version, "provider_id", "provider_version")
        adapter_id, adapter_version = _paired(self.adapter_id, self.adapter_version, "adapter_id", "adapter_version")
        formulation_id, formulation_fp = _paired(self.required_formulation_id, self.required_formulation_fingerprint, "required_formulation_id", "required_formulation_fingerprint")
        revision_id, revision_fp = _paired(self.required_problem_revision_id, self.required_problem_revision_fingerprint, "required_problem_revision_id", "required_problem_revision_fingerprint")
        numeric_id, numeric_fp = _paired(self.numeric_policy_id, self.numeric_policy_fingerprint, "numeric_policy_id", "numeric_policy_fingerprint")
        for name, value in (
            ("provider_id", provider_id), ("provider_version", provider_version),
            ("adapter_id", adapter_id), ("adapter_version", adapter_version),
            ("required_environment_fingerprint", _optional(self.required_environment_fingerprint)),
            ("required_formulation_id", formulation_id), ("required_formulation_fingerprint", formulation_fp),
            ("required_problem_revision_id", revision_id), ("required_problem_revision_fingerprint", revision_fp),
            ("numeric_policy_id", numeric_id), ("numeric_policy_fingerprint", numeric_fp),
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "required_worker_count", _positive_optional(self.required_worker_count, "required_worker_count"))
        object.__setattr__(self, "required_thread_count", _positive_optional(self.required_thread_count, "required_thread_count"))
        if self.determinism_policy == "STRICT_EFFECTIVE_OPTIONS" and not (
            self.required_effective_options or self.required_worker_count is not None or self.required_thread_count is not None
        ):
            raise ValueError("strict effective-options profile requires effective-option, worker, or thread requirements")
        object.__setattr__(self, "metadata", _mapping(self.metadata))
        if not self.profile_id:
            object.__setattr__(self, "profile_id", f"solver-execution-profile-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "name": self.name,
            "determinism_policy": self.determinism_policy,
            "requested_options": _mapping(self.requested_options),
            "required_effective_options": _mapping(self.required_effective_options),
            "provider_id": self.provider_id,
            "provider_version": self.provider_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "required_environment_fingerprint": self.required_environment_fingerprint,
            "required_formulation_id": self.required_formulation_id,
            "required_formulation_fingerprint": self.required_formulation_fingerprint,
            "required_problem_revision_id": self.required_problem_revision_id,
            "required_problem_revision_fingerprint": self.required_problem_revision_fingerprint,
            "numeric_policy_id": self.numeric_policy_id,
            "numeric_policy_fingerprint": self.numeric_policy_fingerprint,
            "required_worker_count": self.required_worker_count,
            "required_thread_count": self.required_thread_count,
            "metadata": _mapping(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"profile_id": self.profile_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"profile_id": self.profile_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverExecutionProfile":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class SolverRuntimeProvenance:
    execution_id: str
    source_result_id: str
    source_result_fingerprint: str
    source_outcome_id: str
    source_outcome_fingerprint: str
    profile_id: str
    profile_fingerprint: str
    model_fingerprint: str
    provider_id: str
    provider_implementation: str
    provider_version: str
    adapter_id: str
    adapter_version: str
    solver_command: tuple[str, ...]
    requested_options: Mapping[str, Any]
    effective_options: Mapping[str, Any]
    worker_count: int | None
    thread_count: int | None
    environment_fingerprint: str
    platform_identity: Mapping[str, Any]
    library_identity: Mapping[str, Any]
    build_fingerprint: str = ""
    formulation_id: str = ""
    formulation_fingerprint: str = ""
    problem_revision_id: str = ""
    problem_revision_fingerprint: str = ""
    provider_status_map_id: str = ""
    provider_status_map_fingerprint: str = ""
    numeric_policy_id: str = ""
    numeric_policy_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provenance_id: str = ""
    contract_id: str = SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID
    contract_version: str = SOLVER_RUNTIME_PROVENANCE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "execution_id", "source_result_id", "source_result_fingerprint", "profile_id", "profile_fingerprint",
            "model_fingerprint", "provider_id", "provider_implementation", "provider_version", "adapter_id",
            "adapter_version", "environment_fingerprint",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        source_outcome_id, source_outcome_fp = _paired(self.source_outcome_id, self.source_outcome_fingerprint, "source_outcome_id", "source_outcome_fingerprint")
        object.__setattr__(self, "source_outcome_id", source_outcome_id)
        object.__setattr__(self, "source_outcome_fingerprint", source_outcome_fp)
        if self.contract_id != SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID or self.contract_version != SOLVER_RUNTIME_PROVENANCE_CONTRACT_VERSION:
            raise ValueError("unsupported solver runtime provenance contract")
        command = tuple(map(str, self.solver_command))
        if not command:
            raise ValueError("solver runtime provenance requires exact solver command identity")
        object.__setattr__(self, "solver_command", command)
        object.__setattr__(self, "requested_options", _mapping(self.requested_options))
        object.__setattr__(self, "effective_options", _mapping(self.effective_options))
        object.__setattr__(self, "worker_count", _positive_optional(self.worker_count, "worker_count"))
        object.__setattr__(self, "thread_count", _positive_optional(self.thread_count, "thread_count"))
        platform = _mapping(self.platform_identity)
        libraries = _mapping(self.library_identity)
        if not platform:
            raise ValueError("solver runtime provenance requires platform_identity")
        if not libraries:
            raise ValueError("solver runtime provenance requires library_identity")
        object.__setattr__(self, "platform_identity", platform)
        object.__setattr__(self, "library_identity", libraries)
        for left, right, left_name, right_name in (
            (self.formulation_id, self.formulation_fingerprint, "formulation_id", "formulation_fingerprint"),
            (self.problem_revision_id, self.problem_revision_fingerprint, "problem_revision_id", "problem_revision_fingerprint"),
            (self.provider_status_map_id, self.provider_status_map_fingerprint, "provider_status_map_id", "provider_status_map_fingerprint"),
            (self.numeric_policy_id, self.numeric_policy_fingerprint, "numeric_policy_id", "numeric_policy_fingerprint"),
        ):
            left_value, right_value = _paired(left, right, left_name, right_name)
            object.__setattr__(self, left_name, left_value)
            object.__setattr__(self, right_name, right_value)
        object.__setattr__(self, "build_fingerprint", _optional(self.build_fingerprint))
        object.__setattr__(self, "dependency_fingerprints", _uniq(self.dependency_fingerprints))
        object.__setattr__(self, "metadata", _mapping(self.metadata))
        if not self.provenance_id:
            object.__setattr__(self, "provenance_id", f"solver-runtime-provenance-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "execution_id": self.execution_id,
            "source_result_id": self.source_result_id,
            "source_result_fingerprint": self.source_result_fingerprint,
            "source_outcome_id": self.source_outcome_id,
            "source_outcome_fingerprint": self.source_outcome_fingerprint,
            "profile_id": self.profile_id,
            "profile_fingerprint": self.profile_fingerprint,
            "model_fingerprint": self.model_fingerprint,
            "provider_id": self.provider_id,
            "provider_implementation": self.provider_implementation,
            "provider_version": self.provider_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "solver_command": list(self.solver_command),
            "requested_options": _mapping(self.requested_options),
            "effective_options": _mapping(self.effective_options),
            "worker_count": self.worker_count,
            "thread_count": self.thread_count,
            "environment_fingerprint": self.environment_fingerprint,
            "platform_identity": _mapping(self.platform_identity),
            "library_identity": _mapping(self.library_identity),
            "build_fingerprint": self.build_fingerprint,
            "formulation_id": self.formulation_id,
            "formulation_fingerprint": self.formulation_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "problem_revision_fingerprint": self.problem_revision_fingerprint,
            "provider_status_map_id": self.provider_status_map_id,
            "provider_status_map_fingerprint": self.provider_status_map_fingerprint,
            "numeric_policy_id": self.numeric_policy_id,
            "numeric_policy_fingerprint": self.numeric_policy_fingerprint,
            "dependency_fingerprints": list(self.dependency_fingerprints),
            "metadata": _mapping(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"provenance_id": self.provenance_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"provenance_id": self.provenance_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverRuntimeProvenance":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["solver_command"] = tuple(payload.get("solver_command") or ())
        payload["dependency_fingerprints"] = tuple(payload.get("dependency_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SolverProfileEvaluation:
    profile_id: str
    profile_fingerprint: str
    provenance_id: str
    provenance_fingerprint: str
    compliant: bool
    deviations: tuple[Mapping[str, Any], ...] = ()
    evaluation_id: str = ""
    contract_id: str = SOLVER_PROFILE_EVALUATION_CONTRACT_ID
    contract_version: str = SOLVER_PROFILE_EVALUATION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("profile_id", "profile_fingerprint", "provenance_id", "provenance_fingerprint"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SOLVER_PROFILE_EVALUATION_CONTRACT_ID or self.contract_version != SOLVER_PROFILE_EVALUATION_CONTRACT_VERSION:
            raise ValueError("unsupported solver profile evaluation contract")
        deviations = tuple(sorted((_mapping(dict(row)) for row in self.deviations), key=lambda row: (str(row.get("code")), str(row.get("key")))))
        object.__setattr__(self, "deviations", deviations)
        if bool(self.compliant) != (not deviations):
            raise ValueError("solver profile compliant flag must match absence of deviations")
        if not self.evaluation_id:
            object.__setattr__(self, "evaluation_id", f"solver-profile-evaluation-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "profile_id": self.profile_id,
            "profile_fingerprint": self.profile_fingerprint,
            "provenance_id": self.provenance_id,
            "provenance_fingerprint": self.provenance_fingerprint,
            "compliant": bool(self.compliant),
            "deviations": [_mapping(row) for row in self.deviations],
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"evaluation_id": self.evaluation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"evaluation_id": self.evaluation_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverProfileEvaluation":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None); payload["deviations"] = tuple(payload.get("deviations") or ()); return cls(**payload)


def build_solver_runtime_provenance(
    result: OptimizationResult | Mapping[str, Any],
    outcome: SolverOutcomeV2 | Mapping[str, Any],
    profile: SolverExecutionProfile | Mapping[str, Any],
    *,
    execution_id: str,
    adapter_id: str,
    adapter_version: str,
    effective_options: Mapping[str, Any],
    worker_count: int | None,
    thread_count: int | None,
    environment_fingerprint: str,
    platform_identity: Mapping[str, Any],
    library_identity: Mapping[str, Any],
    build_fingerprint: str = "",
    formulation_id: str = "",
    formulation_fingerprint: str = "",
    problem_revision_id: str = "",
    problem_revision_fingerprint: str = "",
    provider_status_map_id: str = "",
    provider_status_map_fingerprint: str = "",
    numeric_policy_id: str = "",
    numeric_policy_fingerprint: str = "",
    dependency_fingerprints: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> SolverRuntimeProvenance:
    source = result if isinstance(result, OptimizationResult) else OptimizationResult.from_dict(result)
    normalized = outcome if isinstance(outcome, SolverOutcomeV2) else SolverOutcomeV2.from_dict(outcome)
    selected = profile if isinstance(profile, SolverExecutionProfile) else SolverExecutionProfile.from_dict(profile)
    if normalized.source_result_id != source.result_id or normalized.source_result_fingerprint != source.fingerprint:
        raise ValueError("solver provenance outcome does not bind exact source result")
    adapter_id = _required(adapter_id, "adapter_id")
    adapter_version = _required(adapter_version, "adapter_version")
    environment_fingerprint = _required(environment_fingerprint, "environment_fingerprint")
    if selected.provider_id and selected.provider_id != source.solver.provider_id:
        raise ValueError("solver execution profile provider_id does not match result provider")
    if selected.provider_version and selected.provider_version != source.solver.version:
        raise ValueError("solver execution profile provider_version does not match result provider version")
    if selected.adapter_id and selected.adapter_id != adapter_id:
        raise ValueError("solver execution profile adapter_id does not match runtime adapter")
    if selected.adapter_version and selected.adapter_version != adapter_version:
        raise ValueError("solver execution profile adapter_version does not match runtime adapter version")
    if selected.required_environment_fingerprint and selected.required_environment_fingerprint != environment_fingerprint:
        raise ValueError("solver execution profile required environment fingerprint mismatch")
    return SolverRuntimeProvenance(
        execution_id=execution_id,
        source_result_id=source.result_id,
        source_result_fingerprint=source.fingerprint,
        source_outcome_id=normalized.outcome_id,
        source_outcome_fingerprint=normalized.fingerprint,
        profile_id=selected.profile_id,
        profile_fingerprint=selected.fingerprint,
        model_fingerprint=source.model_fingerprint,
        provider_id=source.solver.provider_id,
        provider_implementation=source.solver.implementation,
        provider_version=source.solver.version,
        adapter_id=adapter_id,
        adapter_version=adapter_version,
        solver_command=tuple(source.solver.invocation) or (source.solver.implementation,),
        requested_options=selected.requested_options,
        effective_options=effective_options,
        worker_count=worker_count,
        thread_count=thread_count,
        environment_fingerprint=environment_fingerprint,
        platform_identity=platform_identity,
        library_identity=library_identity,
        build_fingerprint=build_fingerprint,
        formulation_id=formulation_id,
        formulation_fingerprint=formulation_fingerprint,
        problem_revision_id=problem_revision_id,
        problem_revision_fingerprint=problem_revision_fingerprint,
        provider_status_map_id=provider_status_map_id,
        provider_status_map_fingerprint=provider_status_map_fingerprint,
        numeric_policy_id=numeric_policy_id or selected.numeric_policy_id,
        numeric_policy_fingerprint=numeric_policy_fingerprint or selected.numeric_policy_fingerprint,
        dependency_fingerprints=tuple(dependency_fingerprints),
        metadata=dict(metadata or {}),
    )


def evaluate_solver_execution_profile(
    profile: SolverExecutionProfile | Mapping[str, Any],
    provenance: SolverRuntimeProvenance | Mapping[str, Any],
) -> SolverProfileEvaluation:
    selected = profile if isinstance(profile, SolverExecutionProfile) else SolverExecutionProfile.from_dict(profile)
    actual = provenance if isinstance(provenance, SolverRuntimeProvenance) else SolverRuntimeProvenance.from_dict(provenance)
    deviations: list[dict[str, Any]] = []
    if actual.profile_id != selected.profile_id or actual.profile_fingerprint != selected.fingerprint:
        deviations.append({"code": "PROFILE_BINDING_MISMATCH"})
    for field_name in ("provider_id", "provider_version", "adapter_id", "adapter_version"):
        expected = getattr(selected, field_name)
        if expected and getattr(actual, field_name) != expected:
            deviations.append({"code": "RUNTIME_IDENTITY_MISMATCH", "key": field_name, "expected": expected, "actual": getattr(actual, field_name)})
    if selected.required_environment_fingerprint and actual.environment_fingerprint != selected.required_environment_fingerprint:
        deviations.append({"code": "ENVIRONMENT_FINGERPRINT_MISMATCH", "expected": selected.required_environment_fingerprint, "actual": actual.environment_fingerprint})
    if selected.required_formulation_id and (actual.formulation_id != selected.required_formulation_id or actual.formulation_fingerprint != selected.required_formulation_fingerprint):
        deviations.append({"code": "FORMULATION_BINDING_MISMATCH"})
    if selected.required_problem_revision_id and (actual.problem_revision_id != selected.required_problem_revision_id or actual.problem_revision_fingerprint != selected.required_problem_revision_fingerprint):
        deviations.append({"code": "PROBLEM_REVISION_BINDING_MISMATCH"})
    if selected.numeric_policy_id and (actual.numeric_policy_id != selected.numeric_policy_id or actual.numeric_policy_fingerprint != selected.numeric_policy_fingerprint):
        deviations.append({"code": "NUMERIC_POLICY_MISMATCH"})
    if selected.required_worker_count is not None and actual.worker_count != selected.required_worker_count:
        deviations.append({"code": "WORKER_COUNT_MISMATCH", "expected": selected.required_worker_count, "actual": actual.worker_count})
    if selected.required_thread_count is not None and actual.thread_count != selected.required_thread_count:
        deviations.append({"code": "THREAD_COUNT_MISMATCH", "expected": selected.required_thread_count, "actual": actual.thread_count})
    for key, expected in sorted(selected.requested_options.items()):
        if key not in actual.requested_options:
            deviations.append({"code": "REQUESTED_OPTION_MISSING_FROM_PROVENANCE", "key": key, "expected": deepcopy(expected)})
        elif actual.requested_options[key] != expected:
            deviations.append({"code": "REQUESTED_OPTION_MISMATCH", "key": key, "expected": deepcopy(expected), "actual": deepcopy(actual.requested_options[key])})
    if selected.determinism_policy == "STRICT_EFFECTIVE_OPTIONS":
        for key, expected in sorted(selected.required_effective_options.items()):
            if key not in actual.effective_options:
                deviations.append({"code": "REQUIRED_EFFECTIVE_OPTION_MISSING", "key": key, "expected": deepcopy(expected)})
            elif actual.effective_options[key] != expected:
                deviations.append({"code": "REQUIRED_EFFECTIVE_OPTION_MISMATCH", "key": key, "expected": deepcopy(expected), "actual": deepcopy(actual.effective_options[key])})
    return SolverProfileEvaluation(selected.profile_id, selected.fingerprint, actual.provenance_id, actual.fingerprint, not deviations, tuple(deviations))


def solver_provenance_contract() -> dict[str, Any]:
    return {
        "profile_contract_id": SOLVER_EXECUTION_PROFILE_CONTRACT_ID,
        "profile_contract_version": SOLVER_EXECUTION_PROFILE_CONTRACT_VERSION,
        "runtime_provenance_contract_id": SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID,
        "profile_evaluation_contract_id": SOLVER_PROFILE_EVALUATION_CONTRACT_ID,
        "stability": SOLVER_PROVENANCE_STABILITY,
        "requested_options": "RECORDED_SEPARATELY_FROM_EFFECTIVE_OPTIONS",
        "effective_options": "ADAPTER_OBSERVED_ACTUAL_CONFIGURATION_REQUIRED",
        "provider_identity": "PROVIDER_IMPLEMENTATION_VERSION_FINGERPRINT_BOUND",
        "adapter_identity": "ADAPTER_ID_AND_VERSION_REQUIRED",
        "platform_identity": "REQUIRED",
        "library_identity": "REQUIRED",
        "worker_thread_counts": "FIRST_CLASS_EXPLICIT_OR_UNKNOWN",
        "solver_command": "EXACT_COMMAND_IDENTITY_PRESERVED",
        "environment": "FINGERPRINT_REQUIRED",
        "formulation_binding": "OPTIONAL_EXACT_ID_AND_FINGERPRINT_PAIR",
        "problem_revision_binding": "OPTIONAL_EXACT_ID_AND_FINGERPRINT_PAIR",
        "numeric_policy": "OPTIONAL_EXACT_ID_AND_FINGERPRINT_PAIR",
        "strict_profile": "REQUIRED_EFFECTIVE_OPTIONS_AND_COUNTS_MUST_MATCH_EXACTLY",
        "reproducibility": "NOT_CLAIMED_BY_PROVENANCE_ALONE",
        "truth_authority": "NONE",
        "policy_authority": "NONE",
    }


__all__ = [
    "SOLVER_EXECUTION_PROFILE_CONTRACT_ID", "SOLVER_EXECUTION_PROFILE_CONTRACT_VERSION",
    "SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID", "SOLVER_RUNTIME_PROVENANCE_CONTRACT_VERSION",
    "SOLVER_PROFILE_EVALUATION_CONTRACT_ID", "SOLVER_PROFILE_EVALUATION_CONTRACT_VERSION",
    "DETERMINISM_POLICIES", "SolverExecutionProfile", "SolverRuntimeProvenance", "SolverProfileEvaluation",
    "build_solver_runtime_provenance", "evaluate_solver_execution_profile", "solver_provenance_contract",
]
