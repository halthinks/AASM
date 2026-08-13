from __future__ import annotations

from pathlib import Path
from aasm import (
    AASMEngine, ProblemSpec, __version__, build_trace_corpus, project_trace, semantic_trace_check,
    trace_contract, validate_public_api_contract, provenance_contract, export_provenance,
    verify_provenance_export, create_selective_provenance_export,
)
from aasm.model import Event
from aasm.cli import build_parser


def event(sequence: int, event_type: str, *, data=None) -> Event:
    return Event(event_id=f"E{sequence}", ts=float(sequence), event_type=event_type, from_state=None, to_state=None,
                 reason="fixture", data=data or {}, machine_id="M1", sequence=sequence)


def test_trace_contract_and_version_are_public() -> None:
    assert __version__ == "0.33.0"
    assert trace_contract()["contract_id"] == "aasm.trace.v1"
    assert provenance_contract()["contract_id"] == "aasm.provenance.v1"
    report = validate_public_api_contract(); assert report["valid"] is True, report
    assert report["contract"]["trace_conformance"]["snapshot_only_input"] == "REJECTED"


def test_lossless_projection_preserves_order_identity_and_digests() -> None:
    source = [event(1, "machine_created"), event(2, "transition_committed"), event(3, "evidence_added")]
    first, second = project_trace(source), project_trace(source)
    assert first == second
    assert [step["event_id"] for step in first["steps"]] == ["E1", "E2", "E3"]
    assert all(len(step["source_sha256"]) == 64 for step in first["steps"])


def test_unknown_transition_is_explicitly_unsupported_not_dropped() -> None:
    report = project_trace([event(1, "future_event")]); assert report["event_count"] == 1
    assert report["steps"][0]["support_status"] == "UNSUPPORTED"


def test_snapshot_only_input_is_rejected() -> None:
    try: project_trace({"snapshot": {"state": "COMPLETE"}})
    except ValueError as exc: assert "snapshot-only" in str(exc)
    else: raise AssertionError("snapshot-only projection should fail")


def test_semantic_counterexample_links_exact_source_event() -> None:
    source = [event(1, "snapshot_patched", data={"semantic_witness": {"pre_state": {"hard": ["C1"]}, "post_state": {"hard": []}, "properties": {"restart_retains_hard_knowledge": False}}})]
    report = semantic_trace_check(source); assert report["status"] == "FAIL"; assert report["issues"][0]["event_id"] == "E1"


def test_trace_corpus_is_deterministic_and_sorted() -> None:
    histories = {"b": [event(1, "machine_created")], "a": [event(1, "machine_created"), event(2, "transition_committed")]}
    first, second = build_trace_corpus(histories), build_trace_corpus(histories); assert first == second
    assert [row["name"] for row in first["entries"]] == ["a", "b"]


def test_engine_projects_its_actual_durable_history() -> None:
    engine = AASMEngine(ProblemSpec("trace me")); report = engine.trace_projection()
    assert report["event_count"] == len(engine.events); assert engine.inspect_machine("trace")["source_trace_sha256"] == report["source_trace_sha256"]


def test_signed_export_detects_tamper_and_wrong_key(tmp_path: Path) -> None:
    engine = AASMEngine(ProblemSpec("portable")); destination = tmp_path / "export"
    result = export_provenance(engine, destination, key=b"secret", signer_id="operator")
    assert result["status"] == "PASS"
    assert verify_provenance_export(destination, key=b"secret", signer_id="operator")["valid"] is True
    assert verify_provenance_export(destination, key=b"wrong")["valid"] is False
    with (destination / "events.json").open("ab") as handle: handle.write(b"tamper")
    report = verify_provenance_export(destination, key=b"secret"); assert report["valid"] is False
    assert any("events.json" in error for error in report["errors"])


def test_selective_disclosure_retains_parent_manifest_lineage(tmp_path: Path) -> None:
    engine = AASMEngine(ProblemSpec("selective")); parent, child = tmp_path / "parent", tmp_path / "child"
    export_provenance(engine, parent, key="secret", signer_id="operator")
    result = create_selective_provenance_export(parent, child, ["trace.json"], key="secret", signer_id="operator")
    assert result["manifest"]["selective_disclosure"] is True
    report = verify_provenance_export(child, key="secret", signer_id="operator"); assert report["valid"] is True
    assert len(report["parent_manifest_sha256"]) == 64


def test_trace_and_provenance_cli_commands_are_visible() -> None:
    help_text = build_parser().format_help()
    for name in ("trace-project", "trace-check", "provenance-export", "provenance-verify", "provenance-select"):
        assert name in help_text
