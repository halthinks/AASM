from __future__ import annotations

import pytest

from aasm.semantic_evolution import (
    EXTERNAL_REFERENCE_CONTRACT_ID,
    PROBLEM_DELTA_CONTRACT_ID,
    PROBLEM_REVISION_CONTRACT_ID,
    ExternalReference,
    ProblemDelta,
    ProblemRevision,
    semantic_evolution_contract,
    validate_revision_transition,
)


def _ref(revision: str = "7") -> ExternalReference:
    return ExternalReference(
        namespace="textpcb.requirement",
        external_id="REQ-USB-02",
        role="HARD_REQUIREMENT",
        revision=revision,
        source_fingerprint="sha256:abc123",
        source_location={"contract_path": "/requirements/usb/1"},
        semantic_entity_id="requirement.usb.02",
    )


def test_external_reference_is_deterministic_and_round_trips():
    first = _ref()
    second = ExternalReference.from_dict(first.to_dict())
    assert first.fingerprint == second.fingerprint
    assert first.key == "textpcb.requirement:REQ-USB-02@7"
    assert second.to_dict() == first.to_dict()


def test_external_reference_rejects_missing_required_identity():
    with pytest.raises(ValueError):
        ExternalReference(namespace="", external_id="REQ-1", role="HARD_REQUIREMENT")
    with pytest.raises(ValueError):
        ExternalReference(namespace="requirements", external_id="", role="HARD_REQUIREMENT")
    with pytest.raises(ValueError):
        ExternalReference(namespace="requirements", external_id="REQ-1", role="")


def test_problem_revision_deduplicates_sortable_dependency_identity():
    revision = ProblemRevision(
        problem_id="board-alpha",
        problem_fingerprint="problem-fp-1",
        semantic_projection_fingerprint="semantic-fp-1",
        dependency_fingerprints=("b", "a", "a"),
        external_references=(_ref(),),
        created_by="controller",
    )
    assert revision.dependency_fingerprints == ("a", "b")
    assert revision.revision_id.startswith("problem-revision-")
    assert ProblemRevision.from_dict(revision.to_dict()).fingerprint == revision.fingerprint


def test_problem_delta_rejects_evidence_that_is_both_preserved_and_invalidated():
    with pytest.raises(ValueError):
        ProblemDelta(
            base_revision_id="r1",
            base_revision_fingerprint="fp-r1",
            target_problem_fingerprint="target-p",
            target_semantic_projection_fingerprint="target-s",
            invalidated_evidence_ids=("e1",),
            preserved_evidence_ids=("e1",),
        )


def test_revision_transition_binds_exact_base_delta_and_target():
    base = ProblemRevision(
        problem_id="board-alpha",
        problem_fingerprint="problem-fp-1",
        semantic_projection_fingerprint="semantic-fp-1",
        external_references=(_ref("7"),),
        created_by="controller",
        revision_id="board-alpha-r7",
    )
    provisional_delta = ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint="problem-fp-2",
        target_semantic_projection_fingerprint="semantic-fp-2",
        modified_external_references=(_ref("8"),),
        changed_semantic_ids=("requirement.usb.02",),
        invalidated_evidence_ids=("verification-r7",),
        impacted_obligation_ids=("verify-usb",),
        impacted_solver_object_ids=("constraint-usb-pin",),
        incremental_eligibility="INCREMENTAL_CANDIDATE",
        warm_start_eligibility="PERFORMANCE_ONLY_CANDIDATE",
        evidence_ids=("change-request-8",),
    )
    target = ProblemRevision(
        problem_id="board-alpha",
        problem_fingerprint="problem-fp-2",
        semantic_projection_fingerprint="semantic-fp-2",
        parent_revision_ids=(base.revision_id,),
        external_references=(_ref("8"),),
        created_by="controller",
        created_from_delta_id=provisional_delta.delta_id,
        revision_id="board-alpha-r8",
    )
    report = validate_revision_transition(base, provisional_delta, target)
    assert report["valid"] is True
    assert report["errors"] == []


def test_revision_transition_fails_closed_for_stale_base_fingerprint():
    base = ProblemRevision(
        problem_id="p",
        problem_fingerprint="p-fp",
        semantic_projection_fingerprint="s-fp",
        revision_id="r1",
    )
    delta = ProblemDelta(
        base_revision_id="r1",
        base_revision_fingerprint="wrong",
        target_problem_fingerprint="p-fp-2",
        target_semantic_projection_fingerprint="s-fp-2",
    )
    target = ProblemRevision(
        problem_id="p",
        problem_fingerprint="p-fp-2",
        semantic_projection_fingerprint="s-fp-2",
        parent_revision_ids=("r1",),
        revision_id="r2",
    )
    report = validate_revision_transition(base, delta, target)
    assert report["valid"] is False
    assert "BASE_REVISION_FINGERPRINT_MISMATCH" in report["errors"]


def test_revision_transition_rejects_wrong_target_semantic_state():
    base = ProblemRevision(
        problem_id="p",
        problem_fingerprint="p-fp",
        semantic_projection_fingerprint="s-fp",
        revision_id="r1",
    )
    delta = ProblemDelta(
        base_revision_id="r1",
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint="expected-p2",
        target_semantic_projection_fingerprint="expected-s2",
    )
    target = ProblemRevision(
        problem_id="p",
        problem_fingerprint="different-p2",
        semantic_projection_fingerprint="different-s2",
        parent_revision_ids=("r1",),
        revision_id="r2",
    )
    report = validate_revision_transition(base, delta, target)
    assert report["valid"] is False
    assert "TARGET_PROBLEM_FINGERPRINT_MISMATCH" in report["errors"]
    assert "TARGET_SEMANTIC_PROJECTION_FINGERPRINT_MISMATCH" in report["errors"]


def test_contract_declares_no_new_truth_authority():
    contract = semantic_evolution_contract()
    assert contract["external_reference_contract_id"] == EXTERNAL_REFERENCE_CONTRACT_ID
    assert contract["problem_revision_contract_id"] == PROBLEM_REVISION_CONTRACT_ID
    assert contract["problem_delta_contract_id"] == PROBLEM_DELTA_CONTRACT_ID
    assert contract["authority"] == "NONE_GRANTED_BY_REVISION_OR_DELTA"
    assert contract["truth_authority"] == "EXISTING_AASM_ADMISSION_PATH_ONLY"
