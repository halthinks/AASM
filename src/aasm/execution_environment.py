from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .event_causality import PORTABLE_U63_MAX
from .semantic_result import semantic_fingerprint


EXECUTION_ENVIRONMENT_CONTRACT_ID = "aasm.execution.environment.v1"
EXECUTION_ENVIRONMENT_CONTRACT_VERSION = "0.1.0"
EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID = "aasm.execution.environment-binding.v1"
EXECUTION_ENVIRONMENT_BINDING_CONTRACT_VERSION = "0.1.0"
EXECUTION_ENVIRONMENT_STABILITY = "FOUNDATION_EXPERIMENTAL"

EXECUTION_ENVIRONMENT_LEVELS = (
    "MODEL",
    "SIMULATION",
    "SIL",
    "HIL",
    "BENCH",
    "CONTROLLED_PHYSICAL",
    "OPERATIONAL",
)
ENVIRONMENT_BINDING_OBJECT_KINDS = ("MACHINE_STATE_OBSERVATION",)


def _require(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _u63(value: int | None, name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value < 0 or value > PORTABLE_U63_MAX:
        raise ValueError(f"{name} must be in [0, {PORTABLE_U63_MAX}]")
    return int(value)


def _string_map(values: Mapping[str, str] | None, name: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in sorted(dict(values or {}).items(), key=lambda item: str(item[0])):
        k = _require(str(key), f"{name} key")
        if not isinstance(value, str):
            raise TypeError(f"{name} must contain string values only")
        result[k] = value
    return result


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def environment_level_accepted(actual_level: str, accepted_levels: Sequence[str]) -> bool:
    if actual_level not in EXECUTION_ENVIRONMENT_LEVELS:
        raise ValueError(f"invalid execution environment level: {actual_level}")
    accepted = _uniq(accepted_levels)
    invalid = [value for value in accepted if value not in EXECUTION_ENVIRONMENT_LEVELS]
    if invalid:
        raise ValueError(f"invalid accepted execution environment levels: {invalid}")
    return actual_level in accepted


@dataclass(frozen=True)
class ExecutionEnvironment:
    workspace_id: str
    scope_id: str
    subject_id: str
    environment_level: str
    environment_namespace: str
    stable_environment_id: str
    instance_id: str
    environment_revision_id: str
    configuration_revision_id: str = ""
    qualified_at_ns: int | None = None
    physical_identity_id: str = ""
    physical_identity_fingerprint: str = ""
    calibration_bindings: Mapping[str, str] = field(default_factory=dict)
    source_trust_id: str = ""
    source_trust_fingerprint: str = ""
    qualification_basis_ids: tuple[str, ...] = ()
    problem_revision_id: str = ""
    external_revision_id: str = ""
    attributes: Mapping[str, str] = field(default_factory=dict)
    environment_id: str = ""
    contract_id: str = EXECUTION_ENVIRONMENT_CONTRACT_ID
    contract_version: str = EXECUTION_ENVIRONMENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "environment_namespace",
            "stable_environment_id",
            "instance_id",
            "environment_revision_id",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != EXECUTION_ENVIRONMENT_CONTRACT_ID or self.contract_version != EXECUTION_ENVIRONMENT_CONTRACT_VERSION:
            raise ValueError("unsupported execution environment contract")
        if self.environment_level not in EXECUTION_ENVIRONMENT_LEVELS:
            raise ValueError(f"invalid execution environment level: {self.environment_level}")
        object.__setattr__(self, "configuration_revision_id", _optional(self.configuration_revision_id))
        object.__setattr__(self, "qualified_at_ns", _u63(self.qualified_at_ns, "qualified_at_ns"))
        object.__setattr__(self, "physical_identity_id", _optional(self.physical_identity_id))
        object.__setattr__(self, "physical_identity_fingerprint", _optional(self.physical_identity_fingerprint))
        if bool(self.physical_identity_id) != bool(self.physical_identity_fingerprint):
            raise ValueError("physical identity id and fingerprint must be supplied together")
        calibrations = _string_map(self.calibration_bindings, "calibration_bindings")
        object.__setattr__(self, "calibration_bindings", calibrations)
        if calibrations and not self.physical_identity_id:
            raise ValueError("calibration_bindings require a physical identity binding")
        object.__setattr__(self, "source_trust_id", _optional(self.source_trust_id))
        object.__setattr__(self, "source_trust_fingerprint", _optional(self.source_trust_fingerprint))
        if bool(self.source_trust_id) != bool(self.source_trust_fingerprint):
            raise ValueError("source trust id and fingerprint must be supplied together")
        if (calibrations or self.source_trust_id) and self.qualified_at_ns is None:
            raise ValueError("qualified_at_ns is required when calibration/source-trust references are supplied")
        object.__setattr__(self, "qualification_basis_ids", _uniq(self.qualification_basis_ids))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        object.__setattr__(self, "attributes", _string_map(self.attributes, "attributes"))
        if not self.environment_id:
            object.__setattr__(
                self,
                "environment_id",
                f"execution-environment-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "environment_id", _require(self.environment_id, "environment_id"))

    def logical_context_payload(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "environment_namespace": self.environment_namespace,
            "stable_environment_id": self.stable_environment_id,
            "environment_revision_id": self.environment_revision_id,
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
        }

    @property
    def logical_context_fingerprint(self) -> str:
        return semantic_fingerprint(self.logical_context_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            **self.logical_context_payload(),
            "environment_level": self.environment_level,
            "instance_id": self.instance_id,
            "configuration_revision_id": self.configuration_revision_id,
            "qualified_at_ns": self.qualified_at_ns,
            "physical_identity_id": self.physical_identity_id,
            "physical_identity_fingerprint": self.physical_identity_fingerprint,
            "calibration_bindings": dict(self.calibration_bindings),
            "source_trust_id": self.source_trust_id,
            "source_trust_fingerprint": self.source_trust_fingerprint,
            "qualification_basis_ids": list(self.qualification_basis_ids),
            "attributes": dict(self.attributes),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"environment_id": self.environment_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "environment_id": self.environment_id,
            **self.identity_payload(),
            "logical_context_fingerprint": self.logical_context_fingerprint,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ExecutionEnvironment":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload.pop("logical_context_fingerprint", None)
        payload["qualification_basis_ids"] = tuple(payload.get("qualification_basis_ids") or ())
        return cls(**payload)


@dataclass(frozen=True)
class EnvironmentEvidenceBinding:
    workspace_id: str
    scope_id: str
    subject_id: str
    environment_id: str
    environment_fingerprint: str
    object_kind: str
    object_id: str
    object_fingerprint: str
    problem_revision_id: str = ""
    external_revision_id: str = ""
    binding_id: str = ""
    contract_id: str = EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID
    contract_version: str = EXECUTION_ENVIRONMENT_BINDING_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "environment_id",
            "environment_fingerprint",
            "object_id",
            "object_fingerprint",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID or self.contract_version != EXECUTION_ENVIRONMENT_BINDING_CONTRACT_VERSION:
            raise ValueError("unsupported execution environment binding contract")
        if self.object_kind not in ENVIRONMENT_BINDING_OBJECT_KINDS:
            raise ValueError(f"invalid environment binding object kind: {self.object_kind}")
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        if not self.binding_id:
            object.__setattr__(
                self,
                "binding_id",
                f"environment-binding-{semantic_fingerprint(self.identity_payload())[:24]}",
            )
        else:
            object.__setattr__(self, "binding_id", _require(self.binding_id, "binding_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "environment_id": self.environment_id,
            "environment_fingerprint": self.environment_fingerprint,
            "object_kind": self.object_kind,
            "object_id": self.object_id,
            "object_fingerprint": self.object_fingerprint,
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"binding_id": self.binding_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"binding_id": self.binding_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EnvironmentEvidenceBinding":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        return cls(**payload)


def execution_environment_contract() -> dict[str, Any]:
    return {
        "contract_id": EXECUTION_ENVIRONMENT_CONTRACT_ID,
        "contract_version": EXECUTION_ENVIRONMENT_CONTRACT_VERSION,
        "binding_contract_id": EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID,
        "binding_contract_version": EXECUTION_ENVIRONMENT_BINDING_CONTRACT_VERSION,
        "stability": EXECUTION_ENVIRONMENT_STABILITY,
        "levels": list(EXECUTION_ENVIRONMENT_LEVELS),
        "binding_object_kinds": list(ENVIRONMENT_BINDING_OBJECT_KINDS),
        "level_semantics": "EXACT_QUALIFICATION_CONTEXT_NOT_ORDINAL_TRUTH_OR_AUTHORITY_RANK",
        "level_ordering": "NONE",
        "higher_level_implies_truth": False,
        "higher_level_implies_authority": False,
        "automatic_level_upgrade": False,
        "simulation_as_physical": "REJECT_EXACT_ACCEPTED_LEVELS_ONLY",
        "cross_environment_evidence_equivalence": "NONE_UNLESS_EXPLICIT_EXTERNAL_POLICY",
        "identity_binding": "OPTIONAL_EXACT_PHYSICAL_IDENTITY_ID_AND_FINGERPRINT",
        "calibration_binding": "OPTIONAL_EXACT_CALIBRATION_ID_TO_FINGERPRINT_MAP_REQUIRES_IDENTITY",
        "source_trust_binding": "OPTIONAL_EXACT_SOURCE_TRUST_ID_AND_FINGERPRINT",
        "reference_time": "EXPLICIT_QUALIFIED_AT_NANOSECONDS_WHEN_VALIDITY_REFERENCES_ARE_BOUND",
        "same_context_divergence": "REQUIRES_EXPLICIT_ENVIRONMENT_OR_PROBLEM_EXTERNAL_REVISION_CHANGE",
        "environment_existence_grants_fact_authority": False,
        "environment_existence_grants_effect_authority": False,
        "environment_existence_grants_source_trust": False,
        "environment_binding_grants_authority": False,
        "environment_level_is_universal_admission": False,
        "host_wall_clock_in_identity": False,
        "python_object_identity_in_identity": False,
        "parallel_environment_store": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
    }


__all__ = [
    "EXECUTION_ENVIRONMENT_CONTRACT_ID",
    "EXECUTION_ENVIRONMENT_CONTRACT_VERSION",
    "EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID",
    "EXECUTION_ENVIRONMENT_BINDING_CONTRACT_VERSION",
    "EXECUTION_ENVIRONMENT_STABILITY",
    "EXECUTION_ENVIRONMENT_LEVELS",
    "ENVIRONMENT_BINDING_OBJECT_KINDS",
    "ExecutionEnvironment",
    "EnvironmentEvidenceBinding",
    "environment_level_accepted",
    "execution_environment_contract",
]
