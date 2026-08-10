from __future__ import annotations

from aasm import (
    AASMEngine,
    CertificateRecord,
    DecisionLiteral,
    HistoryCheckReport,
    ProblemSpec,
    ProjectionCertificateVerifier,
    minimize_conflict_core,
    projection_payload,
)


class PairOracle:
    def conflicts(self, literals):
        subjects = {literal["subject"] for literal in literals}
        return {"a", "c"}.issubset(subjects)


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
    report = engine.check_durable_history()
    assert report["status"] == "PASS"
    assert report["valid"] is True
    assert engine.assurance_report()["history_check_count"] == 1
