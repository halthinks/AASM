from __future__ import annotations

from aasm import (
    AASMEngine,
    DecisionRecord,
    MemoryStore,
    ObligationRecord,
    ProblemSpec,
    PUBLIC_API_CONTRACT,
    __version__,
    validate_public_api_contract,
)


def _assert_graph_is_closed(graph):
    node_ids = {node["id"] for node in graph["nodes"]}
    assert all(edge["src"] in node_ids and edge["dst"] in node_ids for edge in graph["edges"])


def test_adoption_contract_validates_existing_golden_path():
    report = validate_public_api_contract()
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["contract"]["contract_id"] == "aasm.adoption.v1"
    assert report["contract"]["runtime_version"] == __version__ == "0.25.2"
    assert PUBLIC_API_CONTRACT["remote_protocol"] == {
        "name": "aasm.remote.v1",
        "version": "0.19.0",
    }
    required_methods = {
        "register_decision",
        "register_obligation",
        "add_evidence",
        "raise_conflict",
        "backjump_conflict",
        "restart_search",
        "inspect_machine",
        "replay",
        "fork",
    }
    assert required_methods.issubset(
        set(report["contract"]["supported_engine_methods"])
    )


def test_observability_report_exposes_closed_generic_graphs():
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
    for key in ("decision_graph", "obligation_graph", "evidence_graph", "causal_graph"):
        _assert_graph_is_closed(report[key])
    causal_relations = {edge["relation"] for edge in report["causal_graph"]["edges"]}
    assert "AUTHORIZES" in causal_relations
    assert "candidate_summary" in report
    assert "assurance_summary" in report


def test_fairness_debt_explains_thresholds_locks_and_next_action():
    engine = AASMEngine(ProblemSpec("fairness visibility"))
    engine.register_obligation(ObligationRecord("O1", "must eventually be reviewed"))
    engine.audit_calculus_fairness()
    rows = engine.fairness_debt()
    assert len(rows) == 1
    row = rows[0]
    assert row["obligation_id"] == "O1"
    assert set(row["thresholds"]) == {
        "max_hidden_epochs",
        "max_lock_age_epochs",
        "max_lock_count",
    }
    assert set(row["over_by"]) == {
        "hidden_epochs",
        "lock_age_epochs",
        "lock_count",
    }
    assert "active_lock_reasons" in row
    assert row["next_action"] in {"NONE", "REVIEW", "EXPOSE_OR_DISPOSITION"}


def test_individual_views_refresh_from_canonical_store_state():
    store = MemoryStore()
    writer = AASMEngine(ProblemSpec("shared state"), store=store)
    reader = AASMEngine.resume(writer.snapshot.machine_id, store)
    writer.register_decision(DecisionRecord("D-new", "method", "new"))

    graph = reader.decision_graph_view()
    assert "D-new" in {node["id"] for node in graph["nodes"]}


def test_inspection_surfaces_are_domain_neutral_and_stable():
    engine = AASMEngine(ProblemSpec("inspect"))
    for surface in [
        "summary",
        "decisions",
        "obligations",
        "evidence",
        "causal",
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
