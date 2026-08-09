from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from aasm import (
    AASMEngine,
    AASMPackageManifest,
    AASMProfile,
    AdapterBinding,
    CandidateModel,
    DecisionRecord,
    DecisionRequest,
    MachineDefinition,
    MemoryStore,
    ProblemSpec,
    ProducerRef,
    ProfileConformanceKit,
    ProfileEvolutionPolicy,
    ProfileEvolutionProposal,
    ProfileMigration,
    ProfileRegistry,
    SemanticResultEnvelope,
    SQLiteStore,
    bare_profile,
    evolve_profile,
    check_machine,
    load_adapter,
)
from aasm.cli import build_parser
from aasm.persistence.serde import snapshot_from_dict


def example_profile(version="1.0.0"):
    return AASMProfile(
        profile_id="example.field-study",
        profile_version=version,
        description="Domain-neutral field-study contract",
        decision_namespaces=["method"],
        obligation_kinds=["measurement", "work"],
        evidence_kinds=["measurement", "observation"],
        artifact_kinds=["record"],
        policies={
            "validation_classifications": [
                "PASS",
                "LOCAL_DEFECT",
                "INFORMATION_GAP",
                "ASSUMPTION_CONFLICT",
                "EVIDENCE_CONFLICT",
                "POLICY_CONFLICT",
                "FATAL",
            ]
        },
        evolution_policy=ProfileEvolutionPolicy(mode="PROPOSAL_ONLY"),
    )



def test_evolve_machine_definition_is_structurally_valid():
    root = Path(__file__).resolve().parents[1]
    definition = MachineDefinition.load(root / "profiles" / "evolve" / "machine.json")
    report = check_machine(definition)
    assert report.valid, report.to_dict()

def test_builtin_profiles_and_package_manifest_are_domain_neutral():
    root = Path(__file__).resolve().parents[1]
    file_profile = AASMProfile.load(root / "profiles" / "evolve" / "profile.json")
    file_package = AASMPackageManifest.load(root / "profiles" / "evolve" / "package.json")
    assert file_profile.profile_id == "aasm.evolve"
    assert file_package.profiles == ["aasm.evolve"]
    registry = ProfileRegistry()
    ids = {(row["profile_id"], row["profile_version"]) for row in registry.list_profiles()}
    assert ("aasm.bare", "1.0.0") in ids
    assert ("aasm.evolve", "1.0.0") in ids
    assert "software" not in json.dumps(evolve_profile().to_dict()).lower()
    package = AASMPackageManifest(
        "example.study-package",
        "1.0.0",
        "Example package",
        ["example.field-study"],
    )
    report = ProfileConformanceKit().run(example_profile(), package=package)
    assert report.valid


def test_profile_identity_is_immutable_per_id_and_version():
    registry = ProfileRegistry(include_builtins=False)
    first = example_profile()
    registry.register(first)
    changed = example_profile()
    changed.description = "Different contract with the same identity"
    with pytest.raises(ValueError, match="different fingerprint"):
        registry.register(changed)


def test_adapter_import_is_explicit_and_protocol_conformance_is_independent():
    binding = AdapterBinding("decision_backend", "json:loads")
    with pytest.raises(PermissionError, match="allow_import"):
        load_adapter(binding)

    class Backend:
        def propose(self, request):
            return CandidateModel("candidate", {}, "test", "1.0.0")

    request = DecisionRequest("m", {}, {}, [])
    profile = example_profile()
    report = ProfileConformanceKit().run(
        profile,
        adapter_objects={"decision_backend": Backend()},
        determinism_fixtures={"decision_backend": (request,)},
    )
    assert report.valid
    assert report.checks["adapter:decision_backend"] is True
    assert report.checks["determinism:decision_backend"] is True


def test_semantic_result_is_generic_fingerprinted_and_roundtrippable():
    result = SemanticResultEnvelope(
        "r1",
        ProducerRef("human", "reviewer"),
        ["subject-1"],
        "PASS",
        "Observed result accepted",
        observations=[{"value": 42}],
        evidence=[{"kind": "measurement", "ref": "log-1"}],
        confidence=0.9,
    )
    ok, error = ProfileConformanceKit().semantic_roundtrip(result)
    assert ok, error
    assert len(result.fingerprint) == 64


def test_profile_binding_configuration_and_versioned_evolution():
    engine = AASMEngine(ProblemSpec("field study"), store=MemoryStore())
    profile = example_profile()
    bound = engine.bind_profile(profile, configuration={"plots": 4}, actor="owner")
    assert bound["profile_id"] == profile.profile_id
    assert bound["profile_fingerprint"] == profile.fingerprint

    updated = engine.bind_profile(profile, configuration={"plots": 6}, actor="owner")
    assert updated["configuration"] == {"plots": 6}
    assert updated["profile_version"] == "1.0.0"
    assert updated["metadata"]["configuration_history"]

    evidence = engine.add_observation("repeated measurements need a calibration obligation", source="field-log")
    target = example_profile("1.1.0")
    target.obligation_kinds.append("calibration")
    target.obligation_kinds = sorted(set(target.obligation_kinds))
    proposal = ProfileEvolutionProposal(
        "proposal-1",
        profile.profile_id,
        "1.0.0",
        "1.1.0",
        "Add calibration as a first-class obligation",
        [{"op": "add_obligation_kind", "value": "calibration"}],
        evidence_ids=[evidence.evidence_id],
        migration_id="migration-1",
        target_profile_fingerprint=target.fingerprint,
        actor="owner",
    )
    engine.propose_profile_evolution(proposal)
    migration = ProfileMigration(
        "migration-1",
        "1.0.0",
        "1.1.0",
        "BACKWARD_COMPATIBLE",
        operations=[],
    )
    evolved = engine.activate_profile_evolution(
        "proposal-1",
        target,
        migration,
        actor="owner",
    )
    assert evolved["profile_version"] == "1.1.0"
    assert evolved["previous_binding"]["profile_version"] == "1.0.0"
    assert evolved["evolution_history"][-1]["migration"]["migration_id"] == "migration-1"


def test_profile_cannot_silently_replace_itself():
    engine = AASMEngine(ProblemSpec("governed profile"))
    engine.bind_profile(example_profile(), actor="owner")
    with pytest.raises(ValueError, match="explicit versioned ProfileMigration"):
        engine.bind_profile(example_profile("2.0.0"), actor="owner")


def test_candidate_model_is_solver_neutral_and_kernel_validated():
    engine = AASMEngine(ProblemSpec("candidate validation"))
    engine.bind_profile(example_profile(), actor="owner")
    engine.register_decision(DecisionRecord("D1", "method.schedule", "daily"))
    valid = engine.validate_candidate_model(
        CandidateModel("candidate-ok", {"method.schedule": "D1"}, "human", "1")
    )
    assert valid.valid
    invalid = engine.validate_candidate_model(
        CandidateModel("candidate-bad", {"other.schedule": "D1"}, "human", "1")
    )
    assert not invalid.valid
    assert any("does not match" in error for error in invalid.errors)


def test_semantic_results_and_profile_binding_survive_sqlite_resume(tmp_path):
    store = SQLiteStore(tmp_path / "profiles.db")
    engine = AASMEngine(ProblemSpec("durable domain result"), store=store)
    engine.bind_profile(example_profile(), actor="owner")
    engine.record_semantic_result(
        SemanticResultEnvelope(
            "r-durable",
            ProducerRef("simulator", "measurement-rig", version="1"),
            ["plot-1"],
            "PASS",
            "Measurement persisted",
            evidence=[{"kind": "measurement", "value": 8.2}],
        )
    )
    machine_id = engine.snapshot.machine_id
    store.close()

    store = SQLiteStore(tmp_path / "profiles.db")
    resumed = AASMEngine.resume(machine_id, store)
    assert resumed.profile_report()["binding"]["profile_id"] == "example.field-study"
    assert resumed.semantic_results_report()[0]["result_id"] == "r-durable"
    store.close()


def test_legacy_snapshot_defaults_profile_fields():
    snapshot = snapshot_from_dict(
        {
            "machine_id": "m",
            "version": 0,
            "state": "INGEST",
            "problem": {"goal": "legacy"},
            "graph": {"nodes": [], "edges": []},
            "frontier": [],
            "visited": [],
            "pruned": [],
            "memory": {},
            "resources": {},
            "evidence": {
                "claims": [],
                "observations": [],
                "contradictions": [],
                "assumptions": [],
                "records": [],
            },
        }
    )
    assert snapshot.profile_binding == {}
    assert snapshot.semantic_results == []
    assert snapshot.calculus["schema_version"] == 1


def test_cli_exposes_profile_package_contract():
    parser = build_parser()
    cases = [
        ["profiles"],
        ["profile-describe", "aasm.evolve"],
        ["profile-validate", "profile.json"],
        ["package-validate", "package.json"],
        ["profile-conformance", "profile.json"],
        ["semantic-result-validate", "result.json"],
        ["profile", "m", "--store", "runs.db"],
        ["profile-bind", "m", "--store", "runs.db", "--profile", "aasm.evolve"],
        ["candidate-validate", "m", "--store", "runs.db", "--candidate", "candidate.json"],
        ["decision-request", "m", "--store", "runs.db"],
        ["semantic-result-record", "m", "--store", "runs.db", "--result", "result.json"],
        ["semantic-results", "m", "--store", "runs.db"],
    ]
    for argv in cases:
        assert parser.parse_args(argv).command == argv[0]
