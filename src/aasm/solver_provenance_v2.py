from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .optimization import OptimizationResult
from .semantic_result import semantic_fingerprint
from .solver_outcome_v2 import SolverOutcomeV2
from .solver_provenance import SolverExecutionProfile


SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID = "aasm.solver.runtime-provenance.v2"
SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_VERSION = "0.1.0"
SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID = "aasm.solver.profile-evaluation.v2"
SOLVER_PROFILE_EVALUATION_V2_CONTRACT_VERSION = "0.1.0"
SOLVER_PROVENANCE_V2_STABILITY = "FOUNDATION_EXPERIMENTAL"


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
    raise TypeError(f"solver provenance v2 value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class SolverRuntimeProvenanceV2:
    execution_id: str
    source_result_id: str
    source_result_fingerprint: str
    source_outcome_id: str
    source_outcome_fingerprint: str
    profile_id: str
    profile_fingerprint: str
    provider_id: str
    provider_implementation: str
    provider_version: str
    adapter_id: str
    adapter_version: str
    solver_command: tuple[str, ...]
    requested_options: Mapping[str, Any]
    effective_options: Mapping[str, Any]
    environment_fingerprint: str
    build_fingerprint: str = ""
    provider_status_map_id: str = ""
    provider_status_map_fingerprint: str = ""
    numeric_policy_id: str = ""
    numeric_policy_fingerprint: str = ""
    dependency_fingerprints: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    provenance_id: str = ""
    contract_id: str = SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID
    contract_version: str = SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "execution_id",
            "source_result_id",
            "source_result_fingerprint",
            "source_outcome_id",
            "source_outcome_fingerprint",
            "profile_id",
            "profile_fingerprint",
            "provider_id",
            "provider_implementation",
            "provider_version",
            "adapter_id",
            "adapter_version",
            "environment_fingerprint",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID or self.contract_version != SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_VERSION:
            raise ValueError("unsupported solver runtime provenance v2 contract")
        command = tuple(map(str, self.solver_command))
        if not command:
            raise ValueError("solver runtime provenance v2 requires exact solver command identity")
        object.__setattr__(self, "solver_command", command)
        object.__setattr__(self, "requested_options", _jsonable(dict(self.requested_options)))
        object.__setattr__(self, "effective_options", _jsonable(dict(self.effective_options)))
        for left, right in (
            ("provider_status_map_id", "provider_status_map_fingerprint"),
            ("numeric_policy_id", "numeric_policy_fingerprint"),
        ):
            if bool(getattr(self, left)) != bool(getattr(self, right)):
                raise ValueError(f"{left} and {right} must be supplied together")
        for name in (
            "build_fingerprint",
            "provider_status_map_id",
            "provider_status_map_fingerprint",
            "numeric_policy_id",
            "numeric_policy_fingerprint",
        ):
            object.__setattr__(self, name, str(getattr(self, name)).strip())
        object.__setattr__(self, "dependency_fingerprints", _uniq(self.dependency_fingerprints))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))
        if not self.provenance_id:
            object.__setattr__(self, "provenance_id", f"solver-runtime-provenance-v2-{semantic_fingerprint(self.identity_payload())[:24]}")

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
            "provider_id": self.provider_id,
            "provider_implementation": self.provider_implementation,
            "provider_version": self.provider_version,
            "adapter_id": self.adapter_id,
            "adapter_version": self.adapter_version,
            "solver_command": list(self.solver_command),
            "requested_options": _jsonable(self.requested_options),
            "effective_options": _jsonable(self.effective_options),
            "environment_fingerprint": self.environment_fingerprint,
            "build_fingerprint": self.build_fingerprint,
            "provider_status_map_id": self.provider_status_map_id,
            "provider_status_map_fingerprint": self.provider_status_map_fingerprint,
            "numeric_policy_id": self.numeric_policy_id,
            "numeric_policy_fingerprint": self.numeric_policy_fingerprint,
            "dependency_fingerprints": list(self.dependency_fingerprints),
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"provenance_id": self.provenance_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"provenance_id": self.provenance_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SolverRuntimeProvenanceV2":
        payload = deepcopy(dict(value)); payload.pop("fingerprint", None)
        payload["solver_command"] = tuple(payload.get("solver_command") or ())
        payload["dependency_fingerprints"] = tuple(payload.get("dependency_fingerprints") or ())
        return cls(**payload)


@dataclass(frozen=True)
class SolverProfileEvaluationV2:
    profile_id: str
    profile_fingerprint: str
    provenance_id: str
    provenance_fingerprint: str
    compliant: bool
    deviations: tuple[Mapping[str, Any], ...] = ()
    evaluation_id: str = ""
    contract_id: str = SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID
    contract_version: str = SOLVER_PROFILE_EVALUATION_V2_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in ("profile_id", "profile_fingerprint", "provenance_id", "provenance_fingerprint"):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.contract_id != SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID or self.contract_version != SOLVER_PROFILE_EVALUATION_V2_CONTRACT_VERSION:
            raise ValueError("unsupported solver profile evaluation v2 contract")
        deviations = tuple(sorted((_jsonable(dict(row)) for row in self.deviations), key=lambda row: (str(row.get("code")), str(row.get("key")))))
        object.__setattr__(self, "deviations", deviations)
        if bool(self.compliant) != (not deviations):
            raise ValueError("solver profile evaluation v2 compliant flag must match deviations")
        if not self.evaluation_id:
            object.__setattr__(self, "evaluation_id", f"solver-profile-evaluation-v2-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "profile_id": self.profile_id,
            "profile_fingerprint": self.profile_fingerprint,
            "provenance_id": self.provenance_id,
            "provenance_fingerprint": self.provenance_fingerprint,
            "compliant": bool(self.compliant),
            "deviations": [_jsonable(row) for row in self.deviations],
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"evaluation_id": self.evaluation_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"evaluation_id": self.evaluation_id, **self.identity_payload(), "fingerprint": self.fingerprint}


def build_solver_runtime_provenance_v2(
    result: OptimizationResult | Mapping[str, Any],
    outcome: SolverOutcomeV2 | Mapping[str, Any],
    profile: SolverExecutionProfile | Mapping[str, Any],
    *,
    execution_id: str,
    adapter_id: str,
    adapter_version: str,
    effective_options: Mapping[str, Any],
    environment_fingerprint: str,
    build_fingerprint: str = "",
    provider_status_map_id: str = "",
    provider_status_map_fingerprint: str = "",
    dependency_fingerprints: Sequence[str] = (),
    metadata: Mapping[str, Any] | None = None,
) -> SolverRuntimeProvenanceV2:
    source = result if isinstance(result, OptimizationResult) else OptimizationResult.from_dict(result)
    normalized = outcome if isinstance(outcome, SolverOutcomeV2) else SolverOutcomeV2.from_dict(outcome)
    selected = profile if isinstance(profile, SolverExecutionProfile) else SolverExecutionProfile.from_dict(profile)
    if normalized.source_result_id != source.result_id or normalized.source_result_fingerprint != source.fingerprint:
        raise ValueError("solver provenance v2 outcome does not bind exact source result")
    adapter_id = _required(adapter_id, "adapter_id")
    adapter_version = _required(adapter_version, "adapter_version")
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
    return SolverRuntimeProvenanceV2(
        execution_id,
        source.result_id,
        source.fingerprint,
        normalized.outcome_id,
        normalized.fingerprint,
        selected.profile_id,
        selected.fingerprint,
        source.solver.provider_id,
        source.solver.implementation,
        source.solver.version,
        adapter_id,
        adapter_version,
        source.solver.command,
        selected.requested_options,
        effective_options,
        environment_fingerprint,
        build_fingerprint,
        provider_status_map_id,
        provider_status_map_fingerprint,
        selected.numeric_policy_id,
        selected.numeric_policy_fingerprint,
        tuple(dependency_fingerprints),
        dict(metadata or {}),
    )


def evaluate_solver_execution_profile_v2(
    profile: SolverExecutionProfile | Mapping[str, Any],
    provenance: SolverRuntimeProvenanceV2 | Mapping[str, Any],
) -> SolverProfileEvaluationV2:
    selected = profile if isinstance(profile, SolverExecutionProfile) else SolverExecutionProfile.from_dict(profile)
    actual = provenance if isinstance(provenance, SolverRuntimeProvenanceV2) else SolverRuntimeProvenanceV2.from_dict(provenance)
    deviations: list[dict[str, Any]] = []
    if actual.profile_id != selected.profile_id or actual.profile_fingerprint != selected.fingerprint:
        deviations.append({"code": "PROFILE_BINDING_MISMATCH"})
    for field_name in ("provider_id", "provider_version", "adapter_id", "adapter_version"):
        expected = getattr(selected, field_name)
        if expected and getattr(actual, field_name) != expected:
            deviations.append({"code": "RUNTIME_IDENTITY_MISMATCH", "key": field_name, "expected": expected, "actual": getattr(actual, field_name)})
    if selected.required_environment_fingerprint and actual.environment_fingerprint != selected.required_environment_fingerprint:
        deviations.append({"code": "ENVIRONMENT_FINGERPRINT_MISMATCH", "expected": selected.required_environment_fingerprint, "actual": actual.environment_fingerprint})
    if selected.numeric_policy_id:
        if actual.numeric_policy_id != selected.numeric_policy_id or actual.numeric_policy_fingerprint != selected.numeric_policy_fingerprint:
            deviations.append({"code": "NUMERIC_POLICY_MISMATCH"})
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
    return SolverProfileEvaluationV2(
        selected.profile_id,
        selected.fingerprint,
        actual.provenance_id,
        actual.fingerprint,
        not deviations,
        tuple(deviations),
    )


def solver_provenance_v2_contract() -> dict[str, Any]:
    return {
        "execution_profile_contract_id": "aasm.solver.execution-profile.v1",
        "runtime_provenance_contract_id": SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID,
        "profile_evaluation_contract_id": SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID,
        "stability": SOLVER_PROVENANCE_V2_STABILITY,
        "provider_identity": "EXPLICIT_AND_FINGERPRINT_BOUND_VIA_SOURCE_RESULT",
        "adapter_identity": "EXPLICIT_ADAPTER_ID_AND_VERSION_REQUIRED",
        "requested_vs_effective_options": "SEPARATE",
        "solver_command": "EXACT_COMMAND_IDENTITY_PRESERVED",
        "environment": "FINGERPRINT_REQUIRED",
        "numeric_policy": "OPTIONALLY_FINGERPRINT_BOUND",
        "strict_determinism": "PROFILE_REQUIRED_EFFECTIVE_OPTIONS_MATCH_EXACTLY",
        "reproducibility": "NOT_CLAIMED_BY_PROVENANCE_ALONE",
        "truth_authority": "NONE",
    }


__all__ = [
    "SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID",
    "SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID",
    "SolverRuntimeProvenanceV2",
    "SolverProfileEvaluationV2",
    "build_solver_runtime_provenance_v2",
    "evaluate_solver_execution_profile_v2",
    "solver_provenance_v2_contract",
]
