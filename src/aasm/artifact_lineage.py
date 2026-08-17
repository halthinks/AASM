from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .semantic_evolution import ExternalReference
from .semantic_result import semantic_fingerprint


ARTIFACT_REVISION_CONTRACT_ID = "aasm.artifact.revision.v1"
ARTIFACT_REVISION_CONTRACT_VERSION = "0.2.0"
ARTIFACT_LINEAGE_STABILITY = "FOUNDATION_EXPERIMENTAL"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _uniq(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted(set(map(str, values))))


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {
            str(key): _jsonable(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"artifact lineage value is not JSON serializable: {type(value)!r}")


def _required_text(name: str, value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"artifact revision {name} is required")
    return normalized


def _optional_text(value: str) -> str:
    return str(value).strip()


def _sha256(name: str, value: str) -> str:
    normalized = _required_text(name, value).lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"artifact revision {name} must be a lowercase 64-hex SHA-256 digest")
    return normalized


def _refs(values: Sequence[ExternalReference | Mapping[str, Any]]) -> tuple[ExternalReference, ...]:
    refs = tuple(
        row if isinstance(row, ExternalReference) else ExternalReference.from_dict(row)
        for row in values
    )
    by_fingerprint = {row.fingerprint: row for row in refs}
    if len(by_fingerprint) != len(refs):
        raise ValueError("duplicate external reference in artifact revision")
    return tuple(
        sorted(
            refs,
            key=lambda row: (
                row.namespace,
                row.external_id,
                row.revision,
                row.role,
                row.fingerprint,
            ),
        )
    )


def _content_ref_digest(artifact_ref: str) -> str | None:
    value = artifact_ref.strip()
    if _SHA256_RE.fullmatch(value):
        return value
    for prefix in ("sha256:", "inline:sha256:"):
        if value.startswith(prefix):
            candidate = value[len(prefix) :]
            if _SHA256_RE.fullmatch(candidate):
                return candidate
    return None


@dataclass(frozen=True)
class ArtifactRevision:
    """Immutable, authority-neutral lineage record for one logical artifact revision.

    Revision identity is backend-independent: storage location never changes the
    semantic identity of the immutable revision. The current storage locator is
    protected separately by ``storage_binding_fingerprint``. Payload bytes remain
    in an existing AASM artifact backend or an external system. This object does
    not store bytes, select a current artifact, or grant acceptance or authority.
    """

    logical_artifact_id: str
    content_sha256: str
    semantic_projection_sha256: str
    producer_id: str
    format_id: str
    artifact_ref: str = ""
    artifact_kind: str = ""
    parent_revision_ids: tuple[str, ...] = ()
    producer_kind: str = ""
    machine_id: str = ""
    effect_id: str = ""
    source_problem_revision_id: str = ""
    source_problem_revision_fingerprint: str = ""
    source_external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    schema_id: str = ""
    tool_id: str = ""
    tool_version: str = ""
    external_references: tuple[ExternalReference | Mapping[str, Any], ...] = ()
    evidence_ids: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)
    revision_id: str = ""
    contract_id: str = ARTIFACT_REVISION_CONTRACT_ID
    contract_version: str = ARTIFACT_REVISION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if (
            self.contract_id != ARTIFACT_REVISION_CONTRACT_ID
            or self.contract_version != ARTIFACT_REVISION_CONTRACT_VERSION
        ):
            raise ValueError("unsupported artifact revision contract")

        object.__setattr__(
            self, "logical_artifact_id", _required_text("logical_artifact_id", self.logical_artifact_id)
        )
        object.__setattr__(self, "content_sha256", _sha256("content_sha256", self.content_sha256))
        object.__setattr__(
            self,
            "semantic_projection_sha256",
            _sha256("semantic_projection_sha256", self.semantic_projection_sha256),
        )
        object.__setattr__(self, "producer_id", _required_text("producer_id", self.producer_id))
        object.__setattr__(self, "format_id", _required_text("format_id", self.format_id))

        for name in (
            "artifact_ref",
            "artifact_kind",
            "producer_kind",
            "machine_id",
            "effect_id",
            "source_problem_revision_id",
            "source_problem_revision_fingerprint",
            "schema_id",
            "tool_id",
            "tool_version",
        ):
            object.__setattr__(self, name, _optional_text(getattr(self, name)))

        parents = _uniq(self.parent_revision_ids)
        if any(not item for item in parents):
            raise ValueError("artifact revision parent IDs must be non-empty")
        object.__setattr__(self, "parent_revision_ids", parents)

        source_refs = _refs(self.source_external_references)
        refs = _refs(self.external_references)
        object.__setattr__(self, "source_external_references", source_refs)
        object.__setattr__(self, "external_references", refs)

        evidence_ids = _uniq(self.evidence_ids)
        if any(not item for item in evidence_ids):
            raise ValueError("artifact revision Evidence IDs must be non-empty")
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

        ref_digest = _content_ref_digest(self.artifact_ref)
        if ref_digest is not None and ref_digest != self.content_sha256:
            raise ValueError("artifact_ref content digest does not match content_sha256")

        if bool(self.source_problem_revision_id) != bool(self.source_problem_revision_fingerprint):
            raise ValueError(
                "source problem revision ID and fingerprint must either both be present or both be absent"
            )

        derived = f"artifact-revision-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = self.revision_id.strip()
        if supplied and supplied != derived:
            raise ValueError("artifact revision_id does not match canonical revision identity")
        if derived in parents:
            raise ValueError("artifact revision cannot list itself as a parent")
        object.__setattr__(self, "revision_id", derived)

    def identity_payload(self) -> dict[str, Any]:
        """Portable semantic identity. Deliberately excludes storage location."""
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "logical_artifact_id": self.logical_artifact_id,
            "content_sha256": self.content_sha256,
            "semantic_projection_sha256": self.semantic_projection_sha256,
            "artifact_kind": self.artifact_kind,
            "parent_revision_ids": list(self.parent_revision_ids),
            "producer_id": self.producer_id,
            "producer_kind": self.producer_kind,
            "machine_id": self.machine_id,
            "effect_id": self.effect_id,
            "source_problem_revision_id": self.source_problem_revision_id,
            "source_problem_revision_fingerprint": self.source_problem_revision_fingerprint,
            "source_external_references": [row.to_dict() for row in self.source_external_references],
            "format_id": self.format_id,
            "schema_id": self.schema_id,
            "tool_id": self.tool_id,
            "tool_version": self.tool_version,
            "external_references": [row.to_dict() for row in self.external_references],
            "evidence_ids": list(self.evidence_ids),
            "metadata": _jsonable(self.metadata),
        }

    def storage_binding_payload(self) -> dict[str, Any]:
        """Integrity binding for the current opaque storage locator."""
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "revision_id": self.revision_id,
            "content_sha256": self.content_sha256,
            "artifact_ref": self.artifact_ref,
        }

    @property
    def fingerprint(self) -> str:
        """Backend-independent semantic revision fingerprint."""
        return semantic_fingerprint({"revision_id": self.revision_id, **self.identity_payload()})

    @property
    def storage_binding_fingerprint(self) -> str:
        return semantic_fingerprint(self.storage_binding_payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            "revision_id": self.revision_id,
            **self.identity_payload(),
            "artifact_ref": self.artifact_ref,
            "fingerprint": self.fingerprint,
            "storage_binding_fingerprint": self.storage_binding_fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ArtifactRevision":
        payload = deepcopy(dict(value))
        supplied_fingerprint = str(payload.pop("fingerprint", "")).strip()
        supplied_storage_fingerprint = str(payload.pop("storage_binding_fingerprint", "")).strip()
        for name in (
            "parent_revision_ids",
            "source_external_references",
            "external_references",
            "evidence_ids",
        ):
            payload[name] = tuple(payload.get(name) or ())
        item = cls(**payload)
        if supplied_fingerprint and supplied_fingerprint != item.fingerprint:
            raise ValueError("artifact revision fingerprint does not match canonical semantic content")
        if (
            supplied_storage_fingerprint
            and supplied_storage_fingerprint != item.storage_binding_fingerprint
        ):
            raise ValueError("artifact storage binding fingerprint does not match artifact_ref")
        return item


def validate_artifact_revision_transition(
    parents: Sequence[ArtifactRevision | Mapping[str, Any]],
    target: ArtifactRevision | Mapping[str, Any],
) -> dict[str, Any]:
    """Validate immediate lineage without choosing or accepting a current revision."""

    source = tuple(
        row if isinstance(row, ArtifactRevision) else ArtifactRevision.from_dict(row)
        for row in parents
    )
    result = target if isinstance(target, ArtifactRevision) else ArtifactRevision.from_dict(target)
    errors: list[str] = []

    parent_ids = tuple(sorted(row.revision_id for row in source))
    if len(parent_ids) != len(set(parent_ids)):
        errors.append("DUPLICATE_PARENT_REVISION")
    if tuple(result.parent_revision_ids) != parent_ids:
        errors.append("PARENT_REVISION_SET_MISMATCH")
    if any(row.logical_artifact_id != result.logical_artifact_id for row in source):
        errors.append("LOGICAL_ARTIFACT_ID_CHANGED")
    if result.revision_id in parent_ids:
        errors.append("SELF_PARENT_REVISION")

    return {
        "valid": not errors,
        "errors": errors,
        "logical_artifact_id": result.logical_artifact_id,
        "parent_revision_ids": list(parent_ids),
        "target_revision_id": result.revision_id,
    }


def artifact_lineage_contract() -> dict[str, Any]:
    return {
        "artifact_revision_contract_id": ARTIFACT_REVISION_CONTRACT_ID,
        "artifact_revision_contract_version": ARTIFACT_REVISION_CONTRACT_VERSION,
        "stability": ARTIFACT_LINEAGE_STABILITY,
        "logical_identity": "STABLE_ACROSS_IMMUTABLE_REVISIONS",
        "revision_identity": "BACKEND_INDEPENDENT_CONTENT_HASH_SEMANTIC_HASH_AND_PROVENANCE_BOUND",
        "storage_binding_identity": "SEPARATE_FROM_REVISION_IDENTITY_AND_INTEGRITY_FINGERPRINTED",
        "content_storage": "EXISTING_AASM_ARTIFACT_BACKENDS_OR_EXTERNAL_REFERENCE",
        "artifact_ref": "NON_SEMANTIC_OPAQUE_STORAGE_BINDING_WITH_DIGEST_CHECK_WHEN_DECODABLE",
        "external_lineage": "EXISTING_AASM_EXTERNAL_REFERENCE_CONTRACT",
        "evidence_lineage": "EXISTING_AASM_EVIDENCE_IDS_ONLY",
        "source_problem_revision": "EXACT_ID_AND_FINGERPRINT_WHEN_PRESENT",
        "authority": "NONE_GRANTED_BY_ARTIFACT_REVISION",
        "truth_authority": "EXISTING_AASM_ADMISSION_PATH_ONLY",
        "artifact_acceptance": "NOT_DEFINED_BY_FOUNDATION_CONTRACT",
        "generated_artifact_authority": "NONE",
        "successful_generation_authority": "NONE",
        "current_artifact_pointer": "NONE",
        "parallel_artifact_registry": "NONE",
        "parallel_truth_table": "NONE",
        "parallel_authority_evaluator": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


__all__ = [
    "ARTIFACT_REVISION_CONTRACT_ID",
    "ARTIFACT_REVISION_CONTRACT_VERSION",
    "ARTIFACT_LINEAGE_STABILITY",
    "ArtifactRevision",
    "validate_artifact_revision_transition",
    "artifact_lineage_contract",
]
