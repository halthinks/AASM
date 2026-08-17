from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .observation_lifecycle import ObservationSourceRef, portable_observation_value
from .semantic_result import semantic_fingerprint


OBSERVATION_FUSION_CONTRACT_ID = "aasm.observation.fusion.v1"
OBSERVATION_FUSION_CONTRACT_VERSION = "0.1.0"
OBSERVATION_FUSION_STABILITY = "FOUNDATION_EXPERIMENTAL"

OBSERVATION_FUSION_INDEPENDENCE = (
    "UNASSESSED",
    "KNOWN_DEPENDENT",
    "DECLARED_PARTIALLY_INDEPENDENT",
    "DECLARED_INDEPENDENT",
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


@dataclass(frozen=True)
class ObservationFusionRecord:
    workspace_id: str
    scope_id: str
    subject_id: str
    state_namespace: str
    value: Any
    processor_principal_id: str
    fusion_method_id: str
    source_refs: tuple[ObservationSourceRef, ...]
    problem_revision_id: str = ""
    external_revision_id: str = ""
    independence: str = "UNASSESSED"
    independence_basis_evidence_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    attributes: Mapping[str, str] = field(default_factory=dict)
    fusion_id: str = ""
    contract_id: str = OBSERVATION_FUSION_CONTRACT_ID
    contract_version: str = OBSERVATION_FUSION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "state_namespace",
            "processor_principal_id",
            "fusion_method_id",
        ):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if self.contract_id != OBSERVATION_FUSION_CONTRACT_ID or self.contract_version != OBSERVATION_FUSION_CONTRACT_VERSION:
            raise ValueError("unsupported observation fusion contract")
        rows = tuple(
            value if isinstance(value, ObservationSourceRef) else ObservationSourceRef.from_dict(value)
            for value in self.source_refs
        )
        if len(rows) < 2:
            raise ValueError("observation fusion requires at least two exact sources")
        if any(row.source_kind == "MACHINE_STATE_OBSERVATION" for row in rows):
            raise ValueError("fusion cannot bypass lifecycle lineage with direct machine observations")
        identities = [(row.source_kind, row.source_id) for row in rows]
        if len(identities) != len(set(identities)):
            raise ValueError("fusion source references must be unique by kind/id")
        object.__setattr__(self, "source_refs", tuple(sorted(rows, key=lambda row: (row.source_kind, row.source_id, row.source_fingerprint))))
        object.__setattr__(self, "value", portable_observation_value(self.value))
        object.__setattr__(self, "problem_revision_id", _optional(self.problem_revision_id))
        object.__setattr__(self, "external_revision_id", _optional(self.external_revision_id))
        if self.independence not in OBSERVATION_FUSION_INDEPENDENCE:
            raise ValueError(f"invalid observation fusion independence: {self.independence}")
        basis = _uniq(self.independence_basis_evidence_ids)
        if self.independence in {"DECLARED_PARTIALLY_INDEPENDENT", "DECLARED_INDEPENDENT"} and not basis:
            raise ValueError("declared source independence requires explicit basis Evidence")
        object.__setattr__(self, "independence_basis_evidence_ids", basis)
        object.__setattr__(self, "evidence_ids", _uniq(self.evidence_ids))
        object.__setattr__(self, "attributes", _string_map(self.attributes, "attributes"))
        if not self.fusion_id:
            object.__setattr__(self, "fusion_id", f"observation-fusion-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "fusion_id", _require(self.fusion_id, "fusion_id"))

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "state_namespace": self.state_namespace,
            "value": portable_observation_value(self.value),
            "processor_principal_id": self.processor_principal_id,
            "fusion_method_id": self.fusion_method_id,
            "source_refs": [row.to_dict() for row in self.source_refs],
            "problem_revision_id": self.problem_revision_id,
            "external_revision_id": self.external_revision_id,
            "independence": self.independence,
            "independence_basis_evidence_ids": list(self.independence_basis_evidence_ids),
            "evidence_ids": list(self.evidence_ids),
            "attributes": dict(self.attributes),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"fusion_id": self.fusion_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"fusion_id": self.fusion_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ObservationFusionRecord":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload["source_refs"] = tuple(ObservationSourceRef.from_dict(row) for row in payload.get("source_refs") or ())
        payload["independence_basis_evidence_ids"] = tuple(payload.get("independence_basis_evidence_ids") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        return cls(**payload)


def observation_fusion_contract() -> dict[str, Any]:
    return {
        "contract_id": OBSERVATION_FUSION_CONTRACT_ID,
        "contract_version": OBSERVATION_FUSION_CONTRACT_VERSION,
        "stability": OBSERVATION_FUSION_STABILITY,
        "independence_values": list(OBSERVATION_FUSION_INDEPENDENCE),
        "source_minimum": 2,
        "source_lineage": "EXACT_LIFECYCLE_OR_PRIOR_FUSION_ID_AND_FINGERPRINT_ONLY",
        "direct_machine_observation_source": "FORBIDDEN_USE_RAW_LIFECYCLE_ROOT_FIRST",
        "fusion_computation": "EXTERNAL_OR_CALLER_PROCESSOR_RESULT_RECORDED_AASM_DOES_NOT_INFER_NUMERIC_FUSION",
        "agreement_semantics": "CORROBORATION_ONLY_NEVER_AUTHORITY_OR_TRUTH_BY_VOTE",
        "independence_semantics": "EXPLICIT_EVIDENCE_BACKED_DECLARATION_ONLY_NEVER_AUTHORITY",
        "disposed_source_reuse": "FAIL_CLOSED_BY_RUNTIME",
        "fusion_grants_fact_authority": False,
        "fusion_grants_effect_authority": False,
        "fusion_elevates_observation_authority": False,
        "declared_independence_grants_authority": False,
        "validated_by_agreement": False,
        "host_wall_clock_in_identity": False,
        "python_object_identity_in_identity": False,
        "parallel_observation_store": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
        "parallel_authority_evaluator": "NONE",
    }


__all__ = [
    "OBSERVATION_FUSION_CONTRACT_ID",
    "OBSERVATION_FUSION_CONTRACT_VERSION",
    "OBSERVATION_FUSION_STABILITY",
    "OBSERVATION_FUSION_INDEPENDENCE",
    "ObservationFusionRecord",
    "observation_fusion_contract",
]
