from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import math
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


OBSERVATION_LIFECYCLE_CONTRACT_ID = "aasm.observation.lifecycle.v1"
OBSERVATION_LIFECYCLE_CONTRACT_VERSION = "0.1.0"
OBSERVATION_DISPOSITION_CONTRACT_ID = "aasm.observation.disposition.v1"
OBSERVATION_DISPOSITION_CONTRACT_VERSION = "0.1.0"
OBSERVATION_LIFECYCLE_STABILITY = "FOUNDATION_EXPERIMENTAL"

OBSERVATION_LIFECYCLE_STAGES = (
    "RAW",
    "NORMALIZED",
    "CALIBRATED",
    "DERIVED",
    "VALIDATED",
)
OBSERVATION_SOURCE_KINDS = (
    "MACHINE_STATE_OBSERVATION",
    "LIFECYCLE_RECORD",
    "FUSION_RECORD",
)
OBSERVATION_DISPOSITIONS = (
    "REJECTED",
    "SUPERSEDED",
    "STALE",
    "DISPUTED",
)


def _require(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value).strip() for value in values if str(value).strip()}))


def _string_map(values: Mapping[str, str] | None, name: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in sorted(dict(values or {}).items(), key=lambda item: str(item[0])):
        k = _require(str(key), f"{name} key")
        if not isinstance(value, str):
            raise TypeError(f"{name} must contain string values only")
        result[k] = value
    return result


def portable_observation_value(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("observation value contains non-finite float")
        return value
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, child in sorted(value.items(), key=lambda item: str(item[0])):
            if not isinstance(key, str) or not key:
                raise TypeError("observation value mapping keys must be non-empty strings")
            result[key] = portable_observation_value(child)
        return result
    if isinstance(value, (list, tuple)):
        return [portable_observation_value(child) for child in value]
    raise TypeError(f"observation value is not portable JSON: {type(value)!r}")


@dataclass(frozen=True)
class ObservationSourceRef:
    source_kind: str
    source_id: str
    source_fingerprint: str

    def __post_init__(self) -> None:
        if self.source_kind not in OBSERVATION_SOURCE_KINDS:
            raise ValueError(f"invalid observation source kind: {self.source_kind}")
        object.__setattr__(self, "source_id", _require(self.source_id, "source_id"))
        object.__setattr__(self, "source_fingerprint", _require(self.source_fingerprint, "source_fingerprint"))

    def to_dict(self) -> dict[str, str]:
        return {
            "source_kind": self.source_kind,
            "source_id": self.source_id,
            "source_fingerprint": self.source_fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObservationSourceRef":
        return cls(**dict(value))


def _sources(values: Sequence[ObservationSourceRef | Mapping[str, Any]]) -> tuple[ObservationSourceRef, ...]:
    rows = tuple(value if isinstance(value, ObservationSourceRef) else ObservationSourceRef.from_dict(value) for value in values)
    ids = [(row.source_kind, row.source_id) for row in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("observation source references must be unique by kind/id")
    return tuple(sorted(rows, key=lambda row: (row.source_kind, row.source_id, row.source_fingerprint)))


@dataclass(frozen=True)
class ObservationLifecycleRecord:
    workspace_id: str
    scope_id: str
    subject_id: str
    state_namespace: str
    stage: str
    value: Any
    processor_principal_id: str
    transformation_id: str
    source_refs: tuple[ObservationSourceRef, ...]
    problem_revision_id: str = ""
    external_revision_id: str = ""
    environment_binding_id: str = ""
    environment_binding_fingerprint: str = ""
    calibration_bindings: Mapping[str, str] = field(default_factory=dict)
    freshness_assessment_id: str = ""
    freshness_assessment_fingerprint: str = ""
    evidence_ids: tuple[str, ...] = ()
    attributes: Mapping[str, str] = field(default_factory=dict)
    record_id: str = ""
    contract_id: str = OBSERVATION_LIFECYCLE_CONTRACT_ID
    contract_version: str = OBSERVATION_LIFECYCLE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "state_namespace",
            "processor_principal_id",
            "transformation_id",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != OBSERVATION_LIFECYCLE_CONTRACT_ID or self.contract_version != OBSERVATION_LIFECYCLE_CONTRACT_VERSION:
            raise ValueError("unsupported observation lifecycle contract")
        if self.stage not in OBSERVATION_LIFECYCLE_STAGES:
            raise ValueError(f"invalid observation lifecycle stage: {self.stage}")
        source_refs = _sources(self.source_refs)
        if not source_refs:
            raise ValueError("observation lifecycle record requires at least one source")
        if self.stage == "RAW":
            if len(source_refs) != 1 or source_refs[0].source_kind != "MACHINE_STATE_OBSERVATION":
                raise ValueError("RAW observation lifecycle record requires exactly one MACHINE_STATE_OBSERVATION source")
        else:
            if any(row.source_kind == "MACHINE_STATE_OBSERVATION" for row in source_refs):
                raise ValueError("non-RAW lifecycle records must source prior lifecycle/fusion Evidence, not skip lineage")
        object.__setattr__(self, "source_refs", source_refs)
        object.__setattr__(self, "value", portable_observation_value(self.value))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        object.__setattr__(self, "environment_binding_id", _optional(self.environment_binding_id))
        object.__setattr__(self, "environment_binding_fingerprint", _optional(self.environment_binding_fingerprint))
        if bool(self.environment_binding_id) != bool(self.environment_binding_fingerprint):
            raise ValueError("environment binding id and fingerprint must be supplied together")
        object.__setattr__(self, "calibration_bindings", _string_map(self.calibration_bindings, "calibration_bindings"))
        object.__setattr__(self, "freshness_assessment_id", _optional(self.freshness_assessment_id))
        object.__setattr__(self, "freshness_assessment_fingerprint", _optional(self.freshness_assessment_fingerprint))
        if bool(self.freshness_assessment_id) != bool(self.freshness_assessment_fingerprint):
            raise ValueError("freshness assessment id and fingerprint must be supplied together")
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids))
        object.__setattr__(self, "attributes", _string_map(self.attributes, "attributes"))
        if self.stage == "CALIBRATED" and not self.calibration_bindings:
            raise ValueError("CALIBRATED lifecycle record requires exact calibration bindings")
        if not self.record_id:
            object.__setattr__(self, "record_id", f"observation-lifecycle-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "record_id", _require(self.record_id, "record_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "state_namespace": self.state_namespace,
            "stage": self.stage,
            "value": portable_observation_value(self.value),
            "processor_principal_id": self.processor_principal_id,
            "transformation_id": self.transformation_id,
            "source_refs": [row.to_dict() for row in self.source_refs],
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "environment_binding_id": self.environment_binding_id,
            "environment_binding_fingerprint": self.environment_binding_fingerprint,
            "calibration_bindings": dict(self.calibration_bindings),
            "freshness_assessment_id": self.freshness_assessment_id,
            "freshness_assessment_fingerprint": self.freshness_assessment_fingerprint,
            "evidence_ids": list(self.evidence_ids),
            "attributes": dict(self.attributes),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"record_id": self.record_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"record_id": self.record_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObservationLifecycleRecord":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["source_refs"] = tuple(ObservationSourceRef.from_dict(row) for row in payload.get("source_refs") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        return cls(**payload)


@dataclass(frozen=True)
class ObservationDisposition:
    target_kind: str
    target_id: str
    target_fingerprint: str
    disposition: str
    reason_code: str
    actor_principal_id: str
    evidence_ids: tuple[str, ...] = ()
    disposition_id: str = ""
    contract_id: str = OBSERVATION_DISPOSITION_CONTRACT_ID
    contract_version: str = OBSERVATION_DISPOSITION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != OBSERVATION_DISPOSITION_CONTRACT_ID or self.contract_version != OBSERVATION_DISPOSITION_CONTRACT_VERSION:
            raise ValueError("unsupported observation disposition contract")
        if self.target_kind not in {"LIFECYCLE_RECORD", "FUSION_RECORD"}:
            raise ValueError(f"invalid observation disposition target kind: {self.target_kind}")
        if self.disposition not in OBSERVATION_DISPOSITIONS:
            raise ValueError(f"invalid observation disposition: {self.disposition}")
        for name in ("target_id", "target_fingerprint", "reason_code", "actor_principal_id"):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids))
        if not self.disposition_id:
            object.__setattr__(self, "disposition_id", f"observation-disposition-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "disposition_id", _require(self.disposition_id, "disposition_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "target_kind": self.target_kind,
            "target_id": self.target_id,
            "target_fingerprint": self.target_fingerprint,
            "disposition": self.disposition,
            "reason_code": self.reason_code,
            "actor_principal_id": self.actor_principal_id,
            "evidence_ids": list(self.evidence_ids),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"disposition_id": self.disposition_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"disposition_id": self.disposition_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObservationDisposition":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        return cls(**payload)


def observation_lifecycle_contract() -> dict[str, Any]:
    return {
        "contract_id": OBSERVATION_LIFECYCLE_CONTRACT_ID,
        "contract_version": OBSERVATION_LIFECYCLE_CONTRACT_VERSION,
        "disposition_contract_id": OBSERVATION_DISPOSITION_CONTRACT_ID,
        "disposition_contract_version": OBSERVATION_DISPOSITION_CONTRACT_VERSION,
        "stability": OBSERVATION_LIFECYCLE_STABILITY,
        "stages": list(OBSERVATION_LIFECYCLE_STAGES),
        "source_kinds": list(OBSERVATION_SOURCE_KINDS),
        "dispositions": list(OBSERVATION_DISPOSITIONS),
        "empirical_root": "EXISTING_MACHINE_STATE_OBSERVATION_ONLY",
        "lineage": "EVERY_NON_RAW_RECORD_REFERENCES_EXACT_PRIOR_LIFECYCLE_OR_FUSION_ID_AND_FINGERPRINT",
        "stage_progression": "VALIDATED_AT_RUNTIME_NO_SILENT_STAGE_SKIPS",
        "raw_value": "MUST_EQUAL_EXACT_SOURCE_STATE_CLAIM_PORTABLE_VALUE",
        "calibrated_stage": "REQUIRES_EXACT_CALIBRATION_BINDINGS_AND_DOES_NOT_REWRITE_SOURCE",
        "environment": "OPTIONAL_EXACT_EXECUTION_ENVIRONMENT_BINDING_ID_AND_FINGERPRINT",
        "freshness": "OPTIONAL_EXACT_FRESHNESS_ASSESSMENT_ID_AND_FINGERPRINT",
        "disposition_semantics": "APPEND_ONLY_TARGETED_OUTCOME_NEVER_DELETES_OR_REWRITES_SOURCE_EVIDENCE",
        "current_observation_pointer": "NONE",
        "lifecycle_record_grants_fact_authority": False,
        "lifecycle_record_grants_effect_authority": False,
        "lifecycle_record_elevates_observation_authority": False,
        "validated_stage_is_universal_admission": False,
        "disposition_grants_authority": False,
        "host_wall_clock_in_identity": False,
        "python_object_identity_in_identity": False,
        "parallel_observation_store": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
    }


__all__ = [
    "OBSERVATION_LIFECYCLE_CONTRACT_ID",
    "OBSERVATION_LIFECYCLE_CONTRACT_VERSION",
    "OBSERVATION_DISPOSITION_CONTRACT_ID",
    "OBSERVATION_DISPOSITION_CONTRACT_VERSION",
    "OBSERVATION_LIFECYCLE_STABILITY",
    "OBSERVATION_LIFECYCLE_STAGES",
    "OBSERVATION_SOURCE_KINDS",
    "OBSERVATION_DISPOSITIONS",
    "ObservationSourceRef",
    "ObservationLifecycleRecord",
    "ObservationDisposition",
    "portable_observation_value",
    "observation_lifecycle_contract",
]
