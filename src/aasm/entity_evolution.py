from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence

from .semantic_result import semantic_fingerprint


ENTITY_EVOLUTION_CONTRACT_ID = "aasm.entity.evolution.v1"
ENTITY_EVOLUTION_CONTRACT_VERSION = "0.1.0"
ENTITY_EVOLUTION_STABILITY = "FOUNDATION_EXPERIMENTAL"
ENTITY_EVOLUTION_RELATIONS = (
    "UNCHANGED",
    "MODIFIED",
    "GENERATED",
    "SPLIT",
    "MERGED",
    "REPLACED",
    "DELETED",
    "AMBIGUOUS",
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _required_text(name: str, value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"entity evolution {name} is required")
    return normalized


def _optional_text(value: str) -> str:
    return str(value).strip()


def _sha256(name: str, value: str) -> str:
    normalized = _required_text(name, value).lower()
    if not _SHA256_RE.fullmatch(normalized):
        raise ValueError(f"entity evolution {name} must be a lowercase 64-hex SHA-256 digest")
    return normalized


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
    raise TypeError(f"entity evolution value is not JSON serializable: {type(value)!r}")


def _uniq_text(values: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(sorted(set(str(value).strip() for value in values)))
    if any(not value for value in normalized):
        raise ValueError("entity evolution Evidence IDs must be non-empty")
    return normalized


@dataclass(frozen=True)
class EntityRepresentationRef:
    """Exact representation of one persistent entity inside one artifact revision.

    This reference is descriptive and authority-neutral. ``entity_id`` is the
    stable logical/physical identity being tracked; the representation and
    artifact revision fingerprints bind exactly what representation was used.
    """

    entity_id: str
    artifact_revision_id: str
    artifact_revision_fingerprint: str
    representation_id: str
    representation_fingerprint: str
    entity_kind: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "entity_id", _required_text("entity_id", self.entity_id))
        object.__setattr__(
            self,
            "artifact_revision_id",
            _required_text("artifact_revision_id", self.artifact_revision_id),
        )
        object.__setattr__(
            self,
            "artifact_revision_fingerprint",
            _sha256("artifact_revision_fingerprint", self.artifact_revision_fingerprint),
        )
        object.__setattr__(
            self,
            "representation_id",
            _required_text("representation_id", self.representation_id),
        )
        object.__setattr__(
            self,
            "representation_fingerprint",
            _sha256("representation_fingerprint", self.representation_fingerprint),
        )
        object.__setattr__(self, "entity_kind", _optional_text(self.entity_kind))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.identity_payload())

    def identity_payload(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "artifact_revision_id": self.artifact_revision_id,
            "artifact_revision_fingerprint": self.artifact_revision_fingerprint,
            "representation_id": self.representation_id,
            "representation_fingerprint": self.representation_fingerprint,
            "entity_kind": self.entity_kind,
            "metadata": _jsonable(self.metadata),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EntityRepresentationRef":
        payload = deepcopy(dict(value))
        supplied_fingerprint = str(payload.pop("fingerprint", "")).strip()
        item = cls(**payload)
        if supplied_fingerprint and supplied_fingerprint != item.fingerprint:
            raise ValueError("entity representation fingerprint does not match canonical content")
        return item


def _refs(
    values: Sequence[EntityRepresentationRef | Mapping[str, Any]],
) -> tuple[EntityRepresentationRef, ...]:
    refs = tuple(
        row if isinstance(row, EntityRepresentationRef) else EntityRepresentationRef.from_dict(row)
        for row in values
    )
    by_fingerprint = {row.fingerprint: row for row in refs}
    if len(by_fingerprint) != len(refs):
        raise ValueError("duplicate entity representation reference")
    return tuple(sorted(refs, key=lambda row: (row.entity_id, row.artifact_revision_id, row.representation_id, row.fingerprint)))


@dataclass(frozen=True)
class EntityEvolution:
    """Immutable, authority-neutral relationship between entity representations.

    The event records what relation is asserted between exact artifact-backed
    representations. It does not select a current entity state, mutate artifact
    lineage, change external/physical truth, or create FactAuthority.
    """

    relation: str
    predecessors: tuple[EntityRepresentationRef | Mapping[str, Any], ...] = ()
    successors: tuple[EntityRepresentationRef | Mapping[str, Any], ...] = ()
    evidence_ids: tuple[str, ...] = ()
    reason: str = ""
    refinement_run_id: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)
    evolution_id: str = ""
    contract_id: str = ENTITY_EVOLUTION_CONTRACT_ID
    contract_version: str = ENTITY_EVOLUTION_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.contract_id != ENTITY_EVOLUTION_CONTRACT_ID or self.contract_version != ENTITY_EVOLUTION_CONTRACT_VERSION:
            raise ValueError("unsupported entity evolution contract")
        relation = _required_text("relation", self.relation).upper()
        if relation not in ENTITY_EVOLUTION_RELATIONS:
            raise ValueError(f"unsupported entity evolution relation: {relation}")
        object.__setattr__(self, "relation", relation)

        predecessors = _refs(self.predecessors)
        successors = _refs(self.successors)
        object.__setattr__(self, "predecessors", predecessors)
        object.__setattr__(self, "successors", successors)
        object.__setattr__(self, "evidence_ids", _uniq_text(self.evidence_ids))
        object.__setattr__(self, "reason", _optional_text(self.reason))
        object.__setattr__(self, "refinement_run_id", _optional_text(self.refinement_run_id))
        object.__setattr__(self, "metadata", _jsonable(dict(self.metadata)))

        self._validate_cardinality_and_identity()
        derived = f"entity-evolution-{semantic_fingerprint(self.identity_payload())[:24]}"
        supplied = str(self.evolution_id).strip()
        if supplied and supplied != derived:
            raise ValueError("entity evolution_id does not match canonical evolution identity")
        object.__setattr__(self, "evolution_id", derived)

    def _validate_cardinality_and_identity(self) -> None:
        p = self.predecessors
        s = self.successors
        relation = self.relation
        if relation == "GENERATED":
            if p or not s:
                raise ValueError("GENERATED requires zero predecessors and at least one successor")
        elif relation == "DELETED":
            if not p or s:
                raise ValueError("DELETED requires at least one predecessor and zero successors")
        elif relation == "SPLIT":
            if len(p) != 1 or len(s) < 2:
                raise ValueError("SPLIT requires exactly one predecessor and at least two successors")
        elif relation == "MERGED":
            if len(p) < 2 or len(s) != 1:
                raise ValueError("MERGED requires at least two predecessors and exactly one successor")
        elif relation in {"UNCHANGED", "MODIFIED", "REPLACED"}:
            if len(p) != 1 or len(s) != 1:
                raise ValueError(f"{relation} requires exactly one predecessor and one successor")
            same_entity = p[0].entity_id == s[0].entity_id
            if relation in {"UNCHANGED", "MODIFIED"} and not same_entity:
                raise ValueError(f"{relation} must preserve entity_id")
            if relation == "REPLACED" and same_entity:
                raise ValueError("REPLACED must identify a distinct successor entity_id")
        elif relation == "AMBIGUOUS":
            if not p or not s:
                raise ValueError("AMBIGUOUS requires at least one predecessor and one successor")

        if relation in {"SPLIT", "MERGED", "REPLACED"}:
            predecessor_ids = {row.entity_id for row in p}
            successor_ids = {row.entity_id for row in s}
            if predecessor_ids == successor_ids:
                raise ValueError(f"{relation} must change the entity identity set")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "relation": self.relation,
            "predecessors": [row.to_dict() for row in self.predecessors],
            "successors": [row.to_dict() for row in self.successors],
            "evidence_ids": list(self.evidence_ids),
            "reason": self.reason,
            "refinement_run_id": self.refinement_run_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"evolution_id": self.evolution_id, **self.identity_payload()})

    @property
    def is_ambiguous(self) -> bool:
        return self.relation == "AMBIGUOUS"

    def to_dict(self) -> dict[str, Any]:
        return {"evolution_id": self.evolution_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EntityEvolution":
        payload = deepcopy(dict(value))
        supplied_fingerprint = str(payload.pop("fingerprint", "")).strip()
        payload["predecessors"] = tuple(payload.get("predecessors") or ())
        payload["successors"] = tuple(payload.get("successors") or ())
        payload["evidence_ids"] = tuple(payload.get("evidence_ids") or ())
        item = cls(**payload)
        if supplied_fingerprint and supplied_fingerprint != item.fingerprint:
            raise ValueError("entity evolution fingerprint does not match canonical content")
        return item


def entity_evolution_contract() -> dict[str, Any]:
    return {
        "contract_id": ENTITY_EVOLUTION_CONTRACT_ID,
        "contract_version": ENTITY_EVOLUTION_CONTRACT_VERSION,
        "stability": ENTITY_EVOLUTION_STABILITY,
        "relations": list(ENTITY_EVOLUTION_RELATIONS),
        "entity_identity": "EXPLICIT_STABLE_ID_NEVER_REWRITTEN_BY_ARTIFACT_RECENCY",
        "representation_identity": "EXACT_ARTIFACT_REVISION_ID_FINGERPRINT_AND_REPRESENTATION_FINGERPRINT",
        "history": "APPEND_ONLY_EVOLUTION_EVENTS",
        "ambiguous_mapping": "FAIL_CLOSED_FOR_HARD_REUSE_OR_AUTOMATIC_IDENTITY_TRANSFER",
        "artifact_authority": "NONE",
        "physical_state_authority": "NONE",
        "external_state_authority": "NONE",
        "fact_authority_creation": "NONE",
        "source_trust_creation": "NONE",
        "effect_authorization": "NONE",
        "effect_dispatch": "NONE",
        "current_entity_state_pointer": "NONE",
        "parallel_entity_registry": "NONE_EVIDENCE_PROJECTION_ONLY",
        "hidden_wall_clock": "NONE",
    }


__all__ = [
    "ENTITY_EVOLUTION_CONTRACT_ID",
    "ENTITY_EVOLUTION_CONTRACT_VERSION",
    "ENTITY_EVOLUTION_STABILITY",
    "ENTITY_EVOLUTION_RELATIONS",
    "EntityRepresentationRef",
    "EntityEvolution",
    "entity_evolution_contract",
]
