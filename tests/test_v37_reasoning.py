from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from aasm import (
    AASMEngine,
    ProblemSpec,
    SQLiteStore,
    __version__,
    Claim,
    Hypothesis,
    Observation,
    ReasoningArtifact,
    ReasoningProducer,
    VerifierRequirement,
    reasoning_contract,
    project_reasoning_evidence,
    run_reasoning_conformance,
    validate_public_api_contract,
)
from aasm.cli import build_parser
from aasm.evidence import EvidenceRecord


def fixture_claim(engine: AASMEngine, *, producer_id: str = "agent-a"):
    evidence = engine.add_evidence(EvidenceRecord("observation", "sensor says ready", source="fixture"))
    artifact = Claim(
        "component is ready",
        ReasoningProducer(producer_id, "PROPOSER"),
        evidence_ids=(evidence.evidence_id,),
        verifier_requirements=(VerifierRequirement("verifier-b"),),
        subject_ids=("component-1",),
    )
    return artifact, evidence


def authorize_fixture(engine: AASMEngine):
    artifact, evidence = fixture_claim(engine)
    engine.propose_artifact(artifact)
    engine.request_verification(
        artifact.artifact_id,
        verifier_ids=["verifier-b"],
        requester_id="agent-a",
    )
    engine.record_verification(
        artifact.artifact_id,
        verifier_id="verifier-b",
        verdict="PASS",
        evidence_ids=[evidence.evidence_id],
    )
    return artifact, evidence, engine.authorize_artifact(
        artifact.artifact_id,
        authority_id="policy-1",
        authority_class="POLICY",
    )


def test_v37_reasoning_contract_and_public_surface():
    contract = reasoning_contract()
    assert __version__ == "0.38.0"
    assert contract["artifact_contract_id"] == "aasm.reasoning.artifact.v1"
    assert contract["admission_contract_id"] == "aasm.reasoning.admission.v1"
    assert contract["commit_contract_id"] == "aasm.reasoning.commit.v1"
    assert contract["durability_boundary"] == "AASM_EVIDENCE_EVENT_REDUCER_ONLY"
    assert contract["dependency_truth_maintenance"] == "RESERVED_FOR_V0.38"
    report = validate_public_api_contract()
    assert report["valid"] is True, report
    assert report["contract"]["contract_version"] == "0.14.0"


def test_typed_reasoning_artifacts_have_deterministic_ids_and_fingerprints():
    producer = ReasoningProducer("agent-a", "PROPOSER")
    first = Claim("same statement", producer, subject_ids=("b", "a"))
    second = Claim("same statement", producer, subject_ids=("a", "b"))
    assert first.artifact_id == second.artifact_id
    assert first.fingerprint == second.fingerprint
    assert first.kind == "Claim"
    assert ReasoningArtifact.from_dict(first.to_dict()).fingerprint == first.fingerprint
    assert Observation("observed", ReasoningProducer("sensor", "OBSERVER")).kind == "Observation"


def test_artifact_proposal_is_durable_evidence_and_exact_replay():
    engine = AASMEngine(ProblemSpec("reasoning replay"))
    artifact, _ = fixture_claim(engine)
    before = len(engine.events)
    report = engine.propose_artifact(artifact)
    assert report["state"] == "PROPOSED"
    assert len(engine.events) == before + 1
    assert engine.events[-1].event_type == "evidence_added"
    replay = project_reasoning_evidence(engine.replay().evidence["records"])
    assert replay["valid"] is True
    assert replay["projection_fingerprint"] == engine.reasoning_report()["projection_fingerprint"]


def test_support_contest_and_verification_lifecycle_is_explicit():
    engine = AASMEngine(ProblemSpec("reasoning lifecycle"))
    artifact, evidence = fixture_claim(engine)
    engine.propose_artifact(artifact)
    assert engine.support_artifact(
        artifact.artifact_id,
        supporter_id="reviewer",
        evidence_ids=[evidence.evidence_id],
    )["state"] == "SUPPORTED"
    assert engine.contest_artifact(
        artifact.artifact_id,
        contester_id="critic",
        evidence_ids=[evidence.evidence_id],
    )["state"] == "CONTESTED"
    assert engine.request_verification(
        artifact.artifact_id,
        verifier_ids=["verifier-b"],
        requester_id="policy-1",
        authority_class="POLICY",
    )["state"] == "VERIFICATION_REQUESTED"
    assert engine.record_verification(
        artifact.artifact_id,
        verifier_id="verifier-b",
        verdict="PASS",
        evidence_ids=[evidence.evidence_id],
    )["state"] == "VERIFIED"


def test_negative_admission_rejects_self_verification_missing_evidence_and_low_authority():
    engine = AASMEngine(ProblemSpec("negative admission"))
    artifact, evidence = fixture_claim(engine)
    engine.propose_artifact(artifact)
    engine.request_verification(
        artifact.artifact_id,
        verifier_ids=["agent-a", "verifier-b"],
        requester_id="agent-a",
    )
    with pytest.raises(ValueError, match="self-verification"):
        engine.record_verification(
            artifact.artifact_id,
            verifier_id="agent-a",
            verdict="PASS",
            evidence_ids=[evidence.evidence_id],
        )
    with pytest.raises(KeyError, match="unknown evidence"):
        engine.record_verification(
            artifact.artifact_id,
            verifier_id="verifier-b",
            verdict="PASS",
            evidence_ids=["missing-evidence"],
        )
    engine.record_verification(
        artifact.artifact_id,
        verifier_id="verifier-b",
        verdict="PASS",
        evidence_ids=[evidence.evidence_id],
    )
    with pytest.raises(PermissionError, match="POLICY or CONTROLLER"):
        engine.authorize_artifact(
            artifact.artifact_id,
            authority_id="agent-a",
            authority_class="PROPOSER",
        )


def test_reasoning_commit_accepts_only_authorized_artifacts():
    engine = AASMEngine(ProblemSpec("reasoning commit"))
    artifact, _, authorized = authorize_fixture(engine)
    assert authorized["state"] == "AUTHORIZED"
    commit = engine.reasoning_commit(
        [artifact.artifact_id],
        authority_id="policy-1",
        authority_class="POLICY",
    )
    assert commit["commit"]["artifact_fingerprints"][artifact.artifact_id] == artifact.fingerprint
    assert engine.reasoning_report()["latest_commit"]["commit_id"] == commit["commit"]["commit_id"]

    other = Hypothesis("not yet authorized", ReasoningProducer("agent-c", "PROPOSER"))
    engine.propose_artifact(other)
    with pytest.raises(ValueError, match="AUTHORIZED"):
        engine.reasoning_commit(
            [other.artifact_id],
            authority_id="policy-1",
            authority_class="POLICY",
        )


def test_refute_and_stale_are_append_only_transitions_not_direct_mutations():
    engine = AASMEngine(ProblemSpec("refute stale"))
    artifact, evidence, _ = authorize_fixture(engine)
    prior_records = len(engine.snapshot.evidence["records"])
    refuted = engine.refute_artifact(
        artifact.artifact_id,
        verifier_id="verifier-b",
        evidence_ids=[evidence.evidence_id],
    )
    assert refuted["state"] == "REFUTED"
    assert len(engine.snapshot.evidence["records"]) == prior_records + 1
    with pytest.raises(ValueError, match="terminal"):
        engine.mark_stale(
            artifact.artifact_id,
            reason="new information",
            authority_id="verifier-b",
            authority_class="VERIFIER",
        )


def test_sqlite_restart_preserves_authorized_reasoning_and_commit(tmp_path: Path):
    path = tmp_path / "reasoning.db"
    store = SQLiteStore(str(path))
    engine = AASMEngine(ProblemSpec("restart reasoning"), store=store)
    machine_id = engine.snapshot.machine_id
    artifact, _, _ = authorize_fixture(engine)
    commit = engine.reasoning_commit(
        [artifact.artifact_id],
        authority_id="controller-1",
        authority_class="CONTROLLER",
    )
    fingerprint = engine.reasoning_report()["projection_fingerprint"]
    store.close()

    resumed_store = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, resumed_store)
    assert resumed.reasoning_report(artifact.artifact_id)["state"] == "AUTHORIZED"
    assert resumed.reasoning_report()["latest_commit"]["commit_id"] == commit["commit"]["commit_id"]
    assert resumed.reasoning_report()["projection_fingerprint"] == fingerprint
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    resumed_store.close()


def test_invalid_direct_record_is_detected_not_admitted():
    engine = AASMEngine(ProblemSpec("tamper detection"))
    artifact, _ = fixture_claim(engine)
    engine.propose_artifact(artifact)
    records = deepcopy(engine.snapshot.evidence["records"])
    records.append({
        "evidence_id": "forged",
        "kind": "reasoning_transition",
        "statement": '{"artifact_id":"%s","action":"AUTHORIZE","actor_id":"intruder","authority_class":"CONTROLLER"}' % artifact.artifact_id,
        "metadata": {
            "reasoning_record_type": "TRANSITION",
            "reasoning_contract_id": "aasm.reasoning.admission.v1",
            "transition_fingerprint": "forged",
        },
    })
    report = project_reasoning_evidence(records)
    assert report["valid"] is False
    assert report["issues"]


def test_reasoning_conformance_and_cli_are_visible():
    report = run_reasoning_conformance()
    assert report["status"] == "PASS", report
    assert all(report["checks"].values())
    help_text = build_parser().format_help()
    for name in (
        "reasoning-contract",
        "reasoning",
        "reasoning-artifact",
        "reasoning-provenance",
        "reasoning-commit",
        "reasoning-conformance",
    ):
        assert name in help_text
