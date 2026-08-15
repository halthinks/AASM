from __future__ import annotations

from copy import deepcopy

import pytest

from aasm.model import ProblemSpec
from aasm.runtime_v55_foundation import AASMEngine
from aasm.semantic_archive import (
    SemanticEvolutionArchive,
    build_semantic_evolution_archive,
    semantic_archive_contract,
    verify_semantic_evolution_archive,
)
from aasm.semantic_evolution import ProblemDelta, ProblemRevision


def _engine() -> AASMEngine:
    engine = AASMEngine(ProblemSpec("archive fixture"))
    base = ProblemRevision(
        problem_id="archive-problem",
        problem_fingerprint="problem-r1",
        semantic_projection_fingerprint="semantic-r1",
        revision_id="archive-r1",
    )
    engine.register_initial_problem_revision(base, authority_id="policy", authority_class="POLICY")
    delta = ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint="problem-r2",
        target_semantic_projection_fingerprint="semantic-r2",
    )
    target = ProblemRevision(
        problem_id=base.problem_id,
        problem_fingerprint="problem-r2",
        semantic_projection_fingerprint="semantic-r2",
        parent_revision_ids=(base.revision_id,),
        created_from_delta_id=delta.delta_id,
        revision_id="archive-r2",
    )
    engine.commit_problem_revision_transition(delta, target, authority_id="policy", authority_class="POLICY")
    return engine


def test_archive_contract_has_no_parallel_truth_or_import_mutation_path():
    contract = semantic_archive_contract()
    assert contract["replay"] == "EXISTING_AASM_REDUCER_OVER_ARCHIVED_EVENTS"
    assert contract["replay_uses_persisted_snapshot"] is False
    assert contract["derived_projections_grant_truth"] is False
    assert contract["import_mutation_path"] == "NONE_IN_FOUNDATION"
    assert contract["truth_authority"] == "NONE"


def test_archive_round_trip_is_byte_stable_and_replays_from_events():
    engine = _engine()
    archive = build_semantic_evolution_archive(engine)
    encoded = archive.to_json()
    round_trip = SemanticEvolutionArchive.from_json(encoded)
    assert round_trip.to_json() == encoded
    assert round_trip.root_fingerprint == archive.root_fingerprint
    report = verify_semantic_evolution_archive(round_trip)
    assert report["valid"] is True
    assert report["persisted_snapshot_used_as_replay_input"] is False
    assert report["replay_source"] == "ARCHIVED_EVENT_SEQUENCE_ONLY"
    assert report["persisted_canonical_hash"] == report["replayed_canonical_hash"]
    assert report["replayed_canonical_hash"] == engine.snapshot.canonical_hash()


def test_snapshot_tampering_is_detected_before_replay():
    archive = build_semantic_evolution_archive(_engine())
    payload = archive.to_dict()
    payload["snapshot"]["metadata"]["tampered"] = True
    with pytest.raises(ValueError, match="snapshot fingerprint mismatch"):
        SemanticEvolutionArchive.from_dict(payload)


def test_event_tampering_is_detected_before_replay():
    archive = build_semantic_evolution_archive(_engine())
    payload = archive.to_dict()
    payload["events"][-1]["reason"] = "tampered"
    with pytest.raises(ValueError, match="events fingerprint mismatch"):
        SemanticEvolutionArchive.from_dict(payload)


def test_projection_tampering_is_detected_and_projections_are_not_replay_inputs():
    archive = build_semantic_evolution_archive(_engine())
    assert "semantic_evolution" in archive.derived_projections
    payload = archive.to_dict()
    payload["derived_projections"]["semantic_evolution"]["tampered"] = True
    with pytest.raises(ValueError, match="projections fingerprint mismatch"):
        SemanticEvolutionArchive.from_dict(payload)

    no_projections = SemanticEvolutionArchive(
        archive.machine_id,
        archive.snapshot,
        archive.events,
        {},
    )
    report = verify_semantic_evolution_archive(no_projections)
    assert report["valid"] is True


def test_event_sequence_must_be_strictly_ordered_and_single_machine():
    archive = build_semantic_evolution_archive(_engine())
    payload = archive.to_dict()
    payload["snapshot_fingerprint"] = ""
    payload["events_fingerprint"] = ""
    payload["projections_fingerprint"] = ""
    payload["root_fingerprint"] = ""
    payload["events"] = list(reversed(payload["events"]))
    with pytest.raises(ValueError, match="strictly ordered"):
        SemanticEvolutionArchive.from_dict(payload)

    payload2 = archive.to_dict()
    payload2["snapshot_fingerprint"] = ""
    payload2["events_fingerprint"] = ""
    payload2["projections_fingerprint"] = ""
    payload2["root_fingerprint"] = ""
    payload2["events"][0]["machine_id"] = "other-machine"
    with pytest.raises(ValueError, match="crosses machine identity"):
        SemanticEvolutionArchive.from_dict(payload2)
