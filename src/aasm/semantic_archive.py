from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Sequence

from .core.reducer import replay_events
from .persistence.serde import event_from_dict, event_to_dict, snapshot_from_dict, snapshot_to_dict
from .semantic_result import canonical_semantic_json, semantic_fingerprint


SEMANTIC_ARCHIVE_CONTRACT_ID = "aasm.semantic-evolution.archive.v1"
SEMANTIC_ARCHIVE_CONTRACT_VERSION = "0.1.0"
SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_ID = "aasm.semantic-evolution.archive-verification.v1"
SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_VERSION = "0.1.0"
SEMANTIC_ARCHIVE_STABILITY = "FOUNDATION_EXPERIMENTAL"


def _jsonable_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(canonical_semantic_json(dict(value)))


@dataclass(frozen=True)
class SemanticEvolutionArchive:
    machine_id: str
    snapshot: Mapping[str, Any]
    events: tuple[Mapping[str, Any], ...]
    derived_projections: Mapping[str, Any] = field(default_factory=dict)
    snapshot_fingerprint: str = ""
    events_fingerprint: str = ""
    projections_fingerprint: str = ""
    root_fingerprint: str = ""
    archive_id: str = ""
    contract_id: str = SEMANTIC_ARCHIVE_CONTRACT_ID
    contract_version: str = SEMANTIC_ARCHIVE_CONTRACT_VERSION

    def __post_init__(self) -> None:
        machine_id = str(self.machine_id).strip()
        if not machine_id:
            raise ValueError("semantic archive machine_id is required")
        if self.contract_id != SEMANTIC_ARCHIVE_CONTRACT_ID or self.contract_version != SEMANTIC_ARCHIVE_CONTRACT_VERSION:
            raise ValueError("unsupported semantic archive contract")
        snapshot = _jsonable_mapping(self.snapshot)
        if snapshot.get("machine_id") != machine_id:
            raise ValueError("semantic archive snapshot machine_id mismatch")
        events = tuple(_jsonable_mapping(row) for row in self.events)
        if not events:
            raise ValueError("semantic archive requires event history")
        sequence_values = [int(row.get("sequence") or 0) for row in events]
        if any(value <= 0 for value in sequence_values):
            raise ValueError("semantic archive events require positive durable sequence values")
        if sequence_values != sorted(sequence_values) or len(sequence_values) != len(set(sequence_values)):
            raise ValueError("semantic archive events must be strictly ordered by unique sequence")
        if any(str(row.get("machine_id") or "") != machine_id for row in events):
            raise ValueError("semantic archive event crosses machine identity")
        projections = _jsonable_mapping(self.derived_projections)
        expected_snapshot = semantic_fingerprint(snapshot)
        expected_events = semantic_fingerprint(list(events))
        expected_projections = semantic_fingerprint(projections)
        root_payload = {
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "machine_id": machine_id,
            "snapshot_fingerprint": expected_snapshot,
            "events_fingerprint": expected_events,
            "projections_fingerprint": expected_projections,
        }
        expected_root = semantic_fingerprint(root_payload)
        for supplied, expected, label in (
            (self.snapshot_fingerprint, expected_snapshot, "snapshot"),
            (self.events_fingerprint, expected_events, "events"),
            (self.projections_fingerprint, expected_projections, "projections"),
            (self.root_fingerprint, expected_root, "root"),
        ):
            if supplied and supplied != expected:
                raise ValueError(f"semantic archive {label} fingerprint mismatch")
        object.__setattr__(self, "machine_id", machine_id)
        object.__setattr__(self, "snapshot", snapshot)
        object.__setattr__(self, "events", events)
        object.__setattr__(self, "derived_projections", projections)
        object.__setattr__(self, "snapshot_fingerprint", expected_snapshot)
        object.__setattr__(self, "events_fingerprint", expected_events)
        object.__setattr__(self, "projections_fingerprint", expected_projections)
        object.__setattr__(self, "root_fingerprint", expected_root)
        expected_archive_id = f"semantic-archive-{expected_root[:24]}"
        if self.archive_id and self.archive_id != expected_archive_id:
            raise ValueError("semantic archive archive_id does not match root fingerprint")
        object.__setattr__(self, "archive_id", expected_archive_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_id": self.archive_id,
            "contract_id": self.contract_id,
            "contract_version": self.contract_version,
            "machine_id": self.machine_id,
            "snapshot": deepcopy(dict(self.snapshot)),
            "events": [deepcopy(dict(row)) for row in self.events],
            "derived_projections": deepcopy(dict(self.derived_projections)),
            "snapshot_fingerprint": self.snapshot_fingerprint,
            "events_fingerprint": self.events_fingerprint,
            "projections_fingerprint": self.projections_fingerprint,
            "root_fingerprint": self.root_fingerprint,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SemanticEvolutionArchive":
        payload = deepcopy(dict(value))
        payload["events"] = tuple(payload.get("events") or ())
        return cls(**payload)

    def to_json(self) -> str:
        return canonical_semantic_json(self.to_dict())

    @classmethod
    def from_json(cls, value: str) -> "SemanticEvolutionArchive":
        parsed = json.loads(value)
        if not isinstance(parsed, dict):
            raise ValueError("semantic archive JSON must contain an object")
        return cls.from_dict(parsed)


def build_semantic_evolution_archive(engine) -> SemanticEvolutionArchive:
    events = tuple(event_to_dict(row) for row in engine.store.load_events(engine.snapshot.machine_id))
    projections: dict[str, Any] = {}
    semantic_report = getattr(engine, "semantic_evolution_report", None)
    if callable(semantic_report):
        projections["semantic_evolution"] = semantic_report()
    formulation_report = getattr(engine, "formulation_report", None)
    if callable(formulation_report):
        projections["solver_formulation"] = formulation_report()
    return SemanticEvolutionArchive(
        engine.snapshot.machine_id,
        snapshot_to_dict(engine.snapshot),
        events,
        projections,
    )


def verify_semantic_evolution_archive(archive: SemanticEvolutionArchive | Mapping[str, Any]) -> dict[str, Any]:
    item = archive if isinstance(archive, SemanticEvolutionArchive) else SemanticEvolutionArchive.from_dict(archive)
    events = [event_from_dict(dict(row)) for row in item.events]
    replayed = replay_events(events)
    persisted = snapshot_from_dict(dict(item.snapshot))
    replay_hash = replayed.canonical_hash()
    persisted_hash = persisted.canonical_hash()
    final_sequence = int(item.events[-1].get("sequence") or 0)
    replayed_version = int(replayed.version)
    persisted_version = int(persisted.version)
    errors: list[str] = []
    if replay_hash != persisted_hash:
        errors.append("EVENT_REPLAY_SNAPSHOT_MISMATCH")
    if replayed.machine_id != item.machine_id:
        errors.append("REPLAY_MACHINE_ID_MISMATCH")
    if replayed_version != persisted_version:
        errors.append("REPLAY_VERSION_MISMATCH")
    report = {
        "contract_id": SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_ID,
        "contract_version": SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_VERSION,
        "archive_id": item.archive_id,
        "archive_root_fingerprint": item.root_fingerprint,
        "event_count": len(item.events),
        "final_sequence": final_sequence,
        "persisted_version": persisted_version,
        "replayed_version": replayed_version,
        "persisted_canonical_hash": persisted_hash,
        "replayed_canonical_hash": replay_hash,
        "valid": not errors,
        "errors": errors,
        "replay_source": "ARCHIVED_EVENT_SEQUENCE_ONLY",
        "persisted_snapshot_used_as_replay_input": False,
        "truth_authority": "NONE",
    }
    report["fingerprint"] = semantic_fingerprint(report)
    return report


def semantic_archive_contract() -> dict[str, Any]:
    return {
        "contract_id": SEMANTIC_ARCHIVE_CONTRACT_ID,
        "contract_version": SEMANTIC_ARCHIVE_CONTRACT_VERSION,
        "verification_contract_id": SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_ID,
        "verification_contract_version": SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_VERSION,
        "stability": SEMANTIC_ARCHIVE_STABILITY,
        "portable_sections": ["canonical_snapshot", "complete_event_history", "derived_v055_projections"],
        "integrity": "SECTION_FINGERPRINTS_PLUS_ROOT_FINGERPRINT",
        "serialization": "CANONICAL_SEMANTIC_JSON_BYTE_STABLE",
        "replay": "EXISTING_AASM_REDUCER_OVER_ARCHIVED_EVENTS",
        "event_sequence_semantics": "DURABLE_ORDERING_ONLY_NOT_MACHINE_VERSION",
        "replay_uses_persisted_snapshot": False,
        "derived_projections_grant_truth": False,
        "import_mutation_path": "NONE_IN_FOUNDATION",
        "truth_authority": "NONE",
    }


__all__ = [
    "SEMANTIC_ARCHIVE_CONTRACT_ID",
    "SEMANTIC_ARCHIVE_CONTRACT_VERSION",
    "SEMANTIC_ARCHIVE_VERIFICATION_CONTRACT_ID",
    "SemanticEvolutionArchive",
    "build_semantic_evolution_archive",
    "verify_semantic_evolution_archive",
    "semantic_archive_contract",
]
