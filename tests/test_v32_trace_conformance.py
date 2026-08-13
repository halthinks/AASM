from __future__ import annotations

from aasm import (
    AASMEngine,
    ProblemSpec,
    __version__,
    build_trace_corpus,
    project_trace,
    semantic_trace_check,
    trace_contract,
    validate_public_api_contract,
)
from aasm.model import Event
from aasm.cli import build_parser


def event(sequence: int, event_type: str, *, data=None) -> Event:
    return Event(
        event_id=f"E{sequence}",
        ts=float(sequence),
        event_type=event_type,
        from_state=None,
        to_state=None,
        reason="fixture",
        data=data or {},
        machine_id="M1",
        sequence=sequence,
    )


def test_trace_contract_and_version_are_public() -> None:
    assert __version__ == "0.32.0"
    contract = trace_contract()
    assert contract["contract_id"] == "aasm.trace.v1"
    assert contract["semantic_contract_id"] == "aasm.trace.semantic.v1"
    report = validate_public_api_contract()
    assert report["valid"] is True, report
    assert report["contract"]["trace_conformance"]["snapshot_only_input"] == "REJECTED"


def test_lossless_projection_preserves_order_identity_and_digests() -> None:
    source = [event(1, "machine_created"), event(2, "transition_committed"), event(3, "evidence_added")]
    first = project_trace(source)
    second = project_trace(source)
    assert first == second
    assert [step["event_id"] for step in first["steps"]] == ["E1", "E2", "E3"]
    assert [step["source_sequence"] for step in first["steps"]] == [1, 2, 3]
    assert all(len(step["source_sha256"]) == 64 for step in first["steps"])
    assert first["source_trace_sha256"] == second["source_trace_sha256"]
    assert first["valid"] is True


def test_unknown_transition_is_explicitly_unsupported_not_dropped() -> None:
    report = project_trace([event(1, "future_event")])
    assert report["event_count"] == 1
    assert report["steps"][0]["support_status"] == "UNSUPPORTED"
    assert report["unsupported_event_types"] == ["future_event"]
    assert report["issues"][0]["event_id"] == "E1"


def test_snapshot_only_input_is_rejected() -> None:
    try:
        project_trace({"snapshot": {"state": "COMPLETE"}})
    except ValueError as exc:
        assert "snapshot-only" in str(exc)
    else:
        raise AssertionError("snapshot-only projection should fail")


def test_semantic_counterexample_links_exact_source_event() -> None:
    source = [event(1, "snapshot_patched", data={"semantic_witness": {"pre_state": {"hard": ["C1"]}, "post_state": {"hard": []}, "properties": {"restart_retains_hard_knowledge": False, "candidate_activation_atomic": True}}})]
    report = semantic_trace_check(source)
    assert report["status"] == "FAIL"
    issue = report["issues"][0]
    assert issue["event_id"] == "E1"
    assert issue["source_sequence"] == 1
    assert issue["issue_code"] == "RESTART_LOST_HARD_KNOWLEDGE"
    assert len(issue["pre_state_fingerprint"]) == 64
    assert len(issue["post_state_fingerprint"]) == 64


def test_missing_semantic_witness_is_inconclusive_not_invented() -> None:
    report = semantic_trace_check([event(1, "transition_committed")])
    assert report["status"] == "INCONCLUSIVE"
    assert report["unsupported"][0]["event_id"] == "E1"


def test_trace_corpus_is_deterministic_and_sorted() -> None:
    histories = {"b": [event(1, "machine_created")], "a": [event(1, "machine_created"), event(2, "transition_committed")]}
    first = build_trace_corpus(histories)
    second = build_trace_corpus(histories)
    assert first == second
    assert [row["name"] for row in first["entries"]] == ["a", "b"]
    assert len(first["corpus_sha256"]) == 64


def test_engine_projects_its_actual_durable_history() -> None:
    engine = AASMEngine(ProblemSpec("trace me"))
    report = engine.trace_projection()
    assert report["event_count"] == len(engine.events)
    assert report["steps"][0]["event_type"] == "machine_created"
    assert engine.inspect_machine("trace")["source_trace_sha256"] == report["source_trace_sha256"]


def test_trace_cli_commands_are_visible() -> None:
    help_text = build_parser().format_help()
    assert "trace-project" in help_text
    assert "trace-check" in help_text
