from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Mapping

from .semantic_result import semantic_fingerprint


PHYSICAL_IDENTITY_CONTRACT_ID = "aasm.physical.identity.v1"
PHYSICAL_IDENTITY_CONTRACT_VERSION = "0.1.0"
PHYSICAL_IDENTITY_STABILITY = "FOUNDATION_EXPERIMENTAL"

PHYSICAL_IDENTITY_CLASSES = (
    "DEVICE",
    "ASSEMBLY",
    "SENSOR",
    "ACTUATOR",
    "COMPUTE_NODE",
    "TOOL_INSTANCE",
    "PROJECT_INSTANCE",
)


def _required(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _optional(value: str | None) -> str:
    return "" if value is None else str(value).strip()


def _string_map(value: Mapping[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, item in sorted(value.items(), key=lambda pair: str(pair[0])):
        normalized_key = str(key).strip()
        if not normalized_key:
            raise ValueError("physical identity attribute keys must be non-empty strings")
        if not isinstance(item, str):
            raise TypeError("physical identity attributes must contain string values only")
        result[normalized_key] = item
    return result


@dataclass(frozen=True)
class PhysicalIdentity:
    workspace_id: str
    scope_id: str
    subject_id: str
    identity_class: str
    identity_namespace: str
    stable_id: str
    instance_id: str
    assembly_revision_id: str = ""
    hardware_revision_id: str = ""
    software_revision_id: str = ""
    configuration_revision_id: str = ""
    problem_revision_id: str = ""
    external_revision_id: str = ""
    attributes: Mapping[str, str] = field(default_factory=dict)
    identity_id: str = ""
    contract_id: str = PHYSICAL_IDENTITY_CONTRACT_ID
    contract_version: str = PHYSICAL_IDENTITY_CONTRACT_VERSION

    def __post_init__(self) -> None:
        for name in (
            "workspace_id",
            "scope_id",
            "subject_id",
            "identity_namespace",
            "stable_id",
            "instance_id",
        ):
            object.__setattr__(self, name, _required(getattr(self, name), name))
        if self.identity_class not in PHYSICAL_IDENTITY_CLASSES:
            raise ValueError(f"invalid physical identity class: {self.identity_class}")
        if self.contract_id != PHYSICAL_IDENTITY_CONTRACT_ID or self.contract_version != PHYSICAL_IDENTITY_CONTRACT_VERSION:
            raise ValueError("unsupported physical-identity contract")
        for name in (
            "assembly_revision_id",
            "hardware_revision_id",
            "software_revision_id",
            "configuration_revision_id",
            "problem_revision_id",
            "external_revision_id",
        ):
            object.__setattr__(self, name, _optional(getattr(self, name)))
        object.__setattr__(self, "attributes", _string_map(dict(self.attributes)))
        if not self.identity_id:
            object.__setattr__(self, "identity_id", f"physical-identity-{semantic_fingerprint(self.identity_payload())[:24]}")
        else:
            object.__setattr__(self, "identity_id", _required(self.identity_id, "identity_id"))

    def logical_context_payload(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "subject_id": self.subject_id,
            "identity_namespace": self.identity_namespace,
            "stable_id": self.stable_id,
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
            "identity_class": self.identity_class,
            "instance_id": self.instance_id,
            "assembly_revision_id": self.assembly_revision_id,
            "hardware_revision_id": self.hardware_revision_id,
            "software_revision_id": self.software_revision_id,
            "configuration_revision_id": self.configuration_revision_id,
            "attributes": dict(self.attributes),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"identity_id": self.identity_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {
            "identity_id": self.identity_id,
            **self.identity_payload(),
            "logical_context_fingerprint": self.logical_context_fingerprint,
            "fingerprint": self.fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "PhysicalIdentity":
        payload = deepcopy(dict(value))
        payload.pop("fingerprint", None)
        payload.pop("logical_context_fingerprint", None)
        return cls(**payload)


def physical_identity_contract() -> dict[str, Any]:
    return {
        "contract_id": PHYSICAL_IDENTITY_CONTRACT_ID,
        "contract_version": PHYSICAL_IDENTITY_CONTRACT_VERSION,
        "stability": PHYSICAL_IDENTITY_STABILITY,
        "identity_classes": list(PHYSICAL_IDENTITY_CLASSES),
        "role": "EXACT_EXTERNAL_SUBJECT_INSTANCE_CONFIGURATION_REFERENCE_NOT_TRUTH_OR_AUTHORITY_BY_EXISTENCE",
        "logical_context": "WORKSPACE_SCOPE_SUBJECT_NAMESPACE_STABLE_ID_AND_BOUND_REVISIONS",
        "same_context_divergence": "FAIL_CLOSED_REQUIRE_NEW_EXTERNAL_OR_PROBLEM_REVISION_BEFORE_DIFFERENT_INSTANCE_OR_CONFIGURATION",
        "attributes": "SORTED_STRING_TO_STRING_PORTABLE_MAP_ONLY",
        "identity_existence_grants_fact_authority": False,
        "identity_existence_grants_effect_authority": False,
        "identity_existence_grants_source_trust": False,
        "identity_mutates_machine_state": False,
        "identity_mutates_external_machine_binding": False,
        "identity_mutates_state_claim": False,
        "attestation": "REFERENCE_SEAM_ONLY_NOT_IMPLEMENTED_OR_CLAIMED_BY_V1",
        "portable_identity": "LANGUAGE_INDEPENDENT_STRINGS_ENUMS_SORTED_STRING_MAP_AND_SEMANTIC_FINGERPRINT",
        "host_wall_clock_in_identity": False,
        "python_object_identity_in_identity": False,
        "parallel_identity_registry": "NONE_EVIDENCE_PROJECTION_ONLY",
        "parallel_truth_table": "NONE",
    }


__all__ = [
    "PHYSICAL_IDENTITY_CONTRACT_ID",
    "PHYSICAL_IDENTITY_CONTRACT_VERSION",
    "PHYSICAL_IDENTITY_STABILITY",
    "PHYSICAL_IDENTITY_CLASSES",
    "PhysicalIdentity",
    "physical_identity_contract",
]
