from __future__ import annotations

from copy import deepcopy

import pytest

from aasm import (
    AASMEngine,
    CertificateRecord,
    ConflictRecord,
    DecisionLiteral,
    DecisionRecord,
    ExplanationRecord,
    ProblemSpec,
    ProjectionCertificateVerifier,
    check_history,
    minimize_conflict_core,
    projection_payload,
)


class PairOracle:
    def conflicts(self, literals):
        subjects = {literal["subject"] for literal in literals}
        return {"a", "c"}.issubset(subjects)


class RootOracle:
    def conflicts(self, literals):
        return True


def test_projection_certificate_covers_exact_constraint():
    constraint = {
        "constraint_id": "LC1",
        "body": [
            DecisionLiteral("a", "EQ", 1).to_dict(),
            DecisionLiteral("c", "EQ", 1).to_dict(),
        ],
        "guard": {"const": True},
        "source_conflict_id": "C1",
        "source_explanation_id": "X1",
        "evidence_ids": ["E1"],
        "scope": {},
    }
    certificate = CertificateRecord(
        "CERT1",
        "PROJECTION",
        "LEARNED_CONSTRAINT",
        "LC1",
        projection_payload(constraint),
        "aasm.projection",
    )
    verification = ProjectionCertificateVerifier().verify(certificate, constraint)
    assert verification.valid is True
    mutated = dict(constraint)
    mutated["body"] = [DecisionLiteral("a", "EQ", 1).to_dict()]
    assert ProjectionCertificateVerifier().verify(certificate, mutated).valid is False


def test_exact_bounded_conflict_minimization_finds_small_core():
    literals = [
        DecisionLiteral("a", "EQ", 1).to_dict(),
        DecisionLiteral("b", "EQ", 1).to_dict(),
        DecisionLiteral("c", "EQ", 1).to_dict(),
    ]
    result = minimize_conflict_core(
        "C1",
        "X1",
        literals,
        PairOracle(),
        mode="EXACT_BOUNDED",
        max_calls=32,
    )
    assert {literal["subject"] for literal in result.minimized_literals} == {"a", "c"}
    assert result.minimality == "PROVEN_MINIMAL"


def test_runtime_history_check_is_persistable_and_clean():
    engine = AASMEngine(ProblemSpec("history"))
    checked_boundary = engine.events[-1].event_id
    report = engine.check_durable_history()
    assert report["status"] == "PASS"
    assert report["valid"] is True
    assert report["checked_event_id"] == checked_boundary
    assert report["checked_event_id"] != engine.events[-1].event_id
    assert report["reconstructed_snapshot_hash"] == report["persisted_snapshot_hash"]
    assert engine.assurance_report()["history_check_count"] == 1


def test_history_check_detects_sequence_gap_and_snapshot_tampering():
    engine = AASMEngine(ProblemSpec("history corruption"))

    broken_events = deepcopy(engine.events)
    broken_events[0].sequence = 2
    sequence_report = check_history(engine.snapshot, broken_events).to_dict()
    assert sequence_report["status"] == "FAIL"
    assert "NON_CONTIGUOUS_SEQUENCE" in {
        issue["code"] for issue in sequence_report["issues"]
    }

    broken_snapshot = deepcopy(engine.snapshot)
    broken_snapshot.metadata["tampered"] = True
    snapshot_report = check_history(broken_snapshot, engine.events).to_dict()
    assert snapshot_report["status"] == "FAIL"
    assert "PERSISTED_SNAPSHOT_MISMATCH" in {
        issue["code"] for issue in snapshot_report["issues"]
    }


def _engine_with_explanation():
    engine = AASMEngine(ProblemSpec("minimize an explanation"))
    for decision_id, subject in (("D-a", "a"), ("D-b", "b"), ("D-c", "c")):
        engine.register_decision(DecisionRecord(decision_id, subject, 1))
        engine.activate_decision(decision_id)
    evidence = engine.add_observation(
        "the active combination is incompatible",
        source="test",
        confidence=1.0,
        metadata={"evidence_type": "integration_test"},
    )
    engine.raise_conflict(ConflictRecord(
        "C1",
        "ASSUMPTION_CONFLICT",
        [evidence.evidence_id],
        implicated_decision_ids=["D-a", "D-b", "D-c"],
    ))
    engine.register_explanation(ExplanationRecord(
        "X1",
        "C1",
        [
            DecisionLiteral("a", "EQ", 1, "D-a").to_dict(),
            DecisionLiteral("b", "EQ", 1, "D-b").to_dict(),
            DecisionLiteral("c", "EQ", 1, "D-c").to_dict(),
        ],
        [evidence.evidence_id],
        status="VALIDATED",
        certificate={"type": "reproduction", "test": "integration"},
    ))
    return engine


def test_adopting_minimized_core_creates_immutable_successor_explanation():
    engine = _engine_with_explanation()
    original = deepcopy(engine.calculus_report()["explanations"]["X1"])
    result = engine.minimize_conflict(
        "C1",
        "X1",
        PairOracle(),
        mode="EXACT_BOUNDED",
        max_calls=32,
        adopt=True,
    )
    successor_id = result["metadata"]["adopted_explanation_id"]
    report = engine.calculus_report()
    assert report["explanations"]["X1"] == original
    assert successor_id != "X1"
    assert {row["subject"] for row in report["explanations"][successor_id]["assumption_literals"]} == {"a", "c"}
    lineage = report["explanations"][successor_id]["certificate"]["aasm_lineage"]
    assert lineage["supersedes_explanation_id"] == "X1"
    assert lineage["version"] == 2


def test_root_conflict_core_cannot_be_adopted_as_no_good_explanation():
    engine = _engine_with_explanation()
    with pytest.raises(ValueError, match="root conflict"):
        engine.minimize_conflict(
            "C1",
            "X1",
            RootOracle(),
            mode="EXACT_BOUNDED",
            max_calls=32,
            adopt=True,
        )
    assert set(engine.calculus_report()["explanations"]) == {"X1"}
