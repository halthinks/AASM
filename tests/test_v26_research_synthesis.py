from __future__ import annotations

import json
from pathlib import Path

import pytest

from aasm import (
    ProfileConformanceKit,
    SQLiteStore,
    default_profile_registry,
    load_research_corpus,
    research_package,
    research_profile,
    run_research_synthesis_demo,
    verify_research_corpus,
)
from aasm.cli import build_parser
from aasm.control_center import html_document


EXPECTED_PROFILE_FINGERPRINT = "08cf7084a065629429defce22a5383bab08f78677e866412eea3238b86969378"
EXPECTED_PACKAGE_FINGERPRINT = "bd8508eb429e96072844c8abfec4365b67bb479605d42ad95125f8b8ef0f8af1"


def test_research_profile_is_finished_conformant_and_builtin():
    profile = research_profile()
    package = research_package()
    report = ProfileConformanceKit().run(profile, package=package)

    assert report.valid is True
    assert profile.profile_id == "aasm.research-synthesis"
    assert profile.profile_version == "1.0.0"
    assert profile.fingerprint == EXPECTED_PROFILE_FINGERPRINT
    assert package.fingerprint == EXPECTED_PACKAGE_FINGERPRINT
    assert profile.metadata["hero_profile"] is True
    assert profile.metadata["offline"] is True
    assert "conflict-learning" in profile.capabilities
    assert profile.policies["evidence_contracts"]["artifact"] == [
        "resolution",
        "provenance_check",
    ]

    resolved = default_profile_registry().resolve("aasm.research-synthesis@1.0.0")
    assert resolved.fingerprint == profile.fingerprint


def test_packaged_research_corpus_is_offline_and_hash_verified():
    report = verify_research_corpus()
    assert report["valid"] is True
    assert report["errors"] == []
    assert report["corpus_id"] == "aasm-research-corpus-v1"
    assert len(report["verified_files"]) == 6
    assert all(row["valid"] for row in report["verified_files"])
    assert report["manifest"]["network_required"] is False
    assert report["manifest"]["model_key_required"] is False
    assert report["manifest"]["synthetic"] is True

    corpus = load_research_corpus()
    assert corpus["question"]["initial_hypothesis"] == "retrieval_only"
    assert corpus["expected_synthesis"]["active_causal_model"] == (
        "effect_modified_by_prior_knowledge"
    )


def test_setup_mode_exposes_initial_model_obligations_and_conditional_lock(tmp_path):
    store = SQLiteStore(tmp_path / "research-setup.db")
    try:
        result = run_research_synthesis_demo(store=store, mode="setup")
        engine = result.engine
        calculus = engine.calculus_report()

        assert result.summary["runtime_version"] == "0.26.0"
        assert result.summary["state"] == "SELECT"
        assert result.summary["corpus_valid"] is True
        assert result.summary["active_model"]["synthesis.causal_model"] == (
            "retrieval_only"
        )
        assert result.summary["locked_obligations"] == ["O-subgroup"]
        assert calculus["locks"]["L-subgroup-off"]["status"] == "ACTIVE"
        assert calculus["obligations"]["O-subgroup"]["status"] == "LOCKED"
        assert engine.profile_report()["binding"]["profile_id"] == (
            "aasm.research-synthesis"
        )

        resumed = result.engine.__class__.resume(engine.snapshot.machine_id, store)
        assert resumed.calculus_report()["active_values"] == calculus["active_values"]
    finally:
        store.close()


@pytest.fixture(scope="module")
def completed_reference(tmp_path_factory):
    root = tmp_path_factory.mktemp("research-complete")
    store = SQLiteStore(root / "research.db")
    result = run_research_synthesis_demo(
        store=store,
        mode="complete",
        output_dir=root / "output",
    )
    try:
        yield result, store, root
    finally:
        store.close()


def test_complete_reference_run_demonstrates_learning_backjump_and_preservation(
    completed_reference,
):
    result, store, _root = completed_reference
    engine = result.engine
    summary = result.summary
    calculus = engine.calculus_report()

    assert engine.state_value == "COMPLETE"
    assert summary["runtime_version"] == "0.26.0"
    assert summary["corpus_valid"] is True
    assert summary["conflict_status"] == "RESOLVED"
    assert summary["learned_constraint_strength"] == "HARD"
    assert summary["certificate_verified"] is True
    assert summary["repeat_failed_model_blocked"] is True
    assert summary["unrelated_report_decision_preserved"] is True
    assert summary["backjump_target"] == "D-model-retrieval-only"
    assert "D-model-retrieval-only" in summary["invalidated_decisions"]
    assert summary["active_model"]["synthesis.causal_model"] == (
        "effect_modified_by_prior_knowledge"
    )
    assert summary["active_model"]["report.format"] == "structured_json"
    assert summary["history_check_valid"] is True
    assert summary["replay_snapshot_hash"] == summary["persisted_snapshot_hash"]
    assert "L-subgroup-off" in summary["broken_lock_ids"]
    assert "source-delta" in summary["steering_affected_nodes"]
    assert "source-alpha" in summary["steering_preserved_nodes"]
    assert set(summary["mandatory_obligations"].values()) == {"COMMITTED"}

    constraint = calculus["constraints"]["LC-retrieval-only"]
    assert constraint["status"] == "ACTIVE"
    assert constraint["certificate_id"] == "CERT-retrieval-only"
    assert calculus["locks"]["L-subgroup-off"]["status"] == "BROKEN"
    assert calculus["decisions"]["D-report-json"]["status"] == "ACTIVE"
    assert calculus["decisions"]["D-model-retrieval-only-repeat"]["status"] == (
        "PROPOSED"
    )

    assurance = engine.snapshot.assurance_state
    certificate = assurance["certificates"]["CERT-retrieval-only"]
    verification = assurance["verifications"][certificate["verification_id"]]
    assert certificate["status"] == "VERIFIED"
    assert verification["valid"] is True

    replayed = engine.replay()
    assert replayed.canonical_hash() == engine.snapshot.canonical_hash()
    resumed = engine.__class__.resume(engine.snapshot.machine_id, store)
    assert resumed.snapshot.canonical_hash() == engine.snapshot.canonical_hash()


def test_complete_reference_artifact_has_claim_level_provenance(completed_reference):
    result, _store, _root = completed_reference
    artifact = result.artifact
    assert artifact is not None
    assert artifact["artifact_id"] == "aasm-research-synthesis-v1"
    assert artifact["synthetic"] is True
    assert artifact["active_causal_model"] == "effect_modified_by_prior_knowledge"
    assert artifact["rejected_model"] == "retrieval_only"
    assert artifact["sha256"]
    assert set(artifact["claim_provenance"]) == {
        "matched_exposure_novice_benefit",
        "unequal_exposure_confounds_aggregate_effect",
        "experienced_population_contradiction",
        "effect_modification_resolution",
    }
    assert all(artifact["claim_provenance"].values())
    assert artifact["machine_provenance"]["constraint_id"] == "LC-retrieval-only"
    assert artifact["machine_provenance"]["certificate_id"] == (
        "CERT-retrieval-only"
    )

    latest = result.engine.semantic_results_report(limit=1)[0]
    assert latest["classification"] == "PASS"
    assert latest["artifacts"][0]["sha256"] == artifact["sha256"]


def test_reference_run_writes_replayable_output_bundle(completed_reference):
    result, _store, _root = completed_reference
    expected = {
        "final_synthesis.json",
        "run_summary.json",
        "history_check.json",
        "machine_export.json",
        "machine_id.txt",
        "replay_commands.txt",
    }
    assert set(result.output_files) == expected
    for name, raw_path in result.output_files.items():
        path = Path(raw_path)
        assert path.is_file(), name
        assert path.stat().st_size > 0, name

    summary = json.loads(Path(result.output_files["run_summary.json"]).read_text())
    artifact = json.loads(Path(result.output_files["final_synthesis.json"]).read_text())
    assert summary["history_check_valid"] is True
    assert artifact["sha256"] == result.artifact["sha256"]
    commands = Path(result.output_files["replay_commands.txt"]).read_text()
    assert "aasm history-check" in commands
    assert "aasm replay" in commands


def test_demo_cli_extends_existing_command_instead_of_creating_private_runner():
    parser = build_parser()
    args = parser.parse_args(
        [
            "demo",
            "--scenario",
            "research-synthesis",
            "--mode",
            "setup",
            "--db",
            "research.db",
            "--output-dir",
            "out",
        ]
    )
    assert args.command == "demo"
    assert args.scenario == "research-synthesis"
    assert args.mode == "setup"
    assert args.db == "research.db"
    assert args.output_dir == "out"


def test_control_center_extends_existing_dashboard_with_reasoning_surfaces():
    html = html_document()
    for token in [
        "Decision Graph",
        "Obligation Graph",
        "Evidence Graph",
        "Conflict · learned no-good · backjump",
        "Fairness debt",
        "Final synthesis and provenance",
        "/inspect/decisions",
        "/inspect/obligations",
        "/inspect/evidence",
        "/inspect/conflicts",
    ]:
        assert token in html
    assert "mission authority · effects · controlled forks" in html
