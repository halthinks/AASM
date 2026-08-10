from __future__ import annotations

from aasm import AASMEngine, DecisionRecord, ObligationRecord, ProblemSpec


def test_observability_report_exposes_generic_decision_and_obligation_graphs():
    engine = AASMEngine(ProblemSpec("observe"))
    engine.register_decision(DecisionRecord("D1", "method", "A"))
    engine.activate_decision("D1")
    engine.register_obligation(
        ObligationRecord(
            "O1",
            "Collect a measurement",
            decision_dependencies=["D1"],
        )
    )
    report = engine.observability_report()
    assert report["machine_id"] == engine.snapshot.machine_id
    decision_ids = {node["id"] for node in report["decision_graph"]["nodes"]}
    obligation_ids = {node["id"] for node in report["obligation_graph"]["nodes"]}
    assert "D1" in decision_ids
    assert "O1" in obligation_ids
    assert any(
        edge["src"] == "D1" and edge["dst"] == "O1" and edge["relation"] == "AUTHORIZED_BY"
        for edge in report["obligation_graph"]["edges"]
    )
    assert "candidate_summary" in report
    assert "assurance_summary" in report


def test_inspection_surfaces_are_domain_neutral_and_stable():
    engine = AASMEngine(ProblemSpec("inspect"))
    for surface in [
        "summary",
        "decisions",
        "obligations",
        "evidence",
        "conflicts",
        "fairness",
        "packages",
        "candidates",
        "assurance",
        "calculus",
        "profile",
    ]:
        value = engine.inspect_machine(surface)
        assert value is not None
