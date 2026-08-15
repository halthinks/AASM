from __future__ import annotations

from pathlib import Path

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.optimization import OPTIMIZATION_CONTRACT_ID, OptimizationResult, OptimizationSolverIdentity
from aasm.persistence import SQLiteStore
from aasm.runtime_v56_foundation import AASMEngine
from aasm.semantic_result import canonical_semantic_json
from aasm.solver_provenance import SolverExecutionProfile


def _add_result(engine: AASMEngine, tag: str, *, threads: int = 1):
    result = OptimizationResult(
        f"repro-request-{tag}",
        f"repro-request-fp-{tag}",
        "repro-model-fp",
        "FEASIBLE",
        OptimizationSolverIdentity(
            "repro-provider",
            "solver.impl",
            "1",
            ("solver", "--seed=5", "--threads=1"),
        ),
        assignment={"x": 1.0},
        objective_value=2.0,
        result_id=f"repro-result-{tag}",
    )
    result_evidence = engine.add_evidence(
        EvidenceRecord(
            kind="optimization_result",
            statement=canonical_semantic_json(result.to_dict()),
            source=OPTIMIZATION_CONTRACT_ID,
        )
    )
    outcome = engine.record_solver_outcome_v2(result.result_id)
    profile_id = ""
    report = engine.solver_provenance_v2_report()
    if report["profiles"]:
        profile_id = next(iter(report["profiles"]))
        profile = SolverExecutionProfile.from_dict(report["profiles"][profile_id]["profile"])
    else:
        profile = SolverExecutionProfile(
            "repro runtime profile",
            "STRICT_EFFECTIVE_OPTIONS",
            requested_options={"seed": 5, "threads": 1},
            required_effective_options={"seed": 5, "threads": 1},
            provider_id="repro-provider",
            provider_version="1",
            adapter_id="aasm.repro",
            adapter_version="1",
            required_environment_fingerprint="repro-env",
        )
        engine.register_solver_execution_profile(profile)
        profile_id = profile.profile_id
    provenance = engine.record_solver_runtime_provenance_v2(
        result.result_id,
        outcome["outcome"]["outcome_id"],
        profile_id,
        execution_id=f"repro-execution-{tag}",
        adapter_id="aasm.repro",
        adapter_version="1",
        effective_options={"seed": 5, "threads": threads},
        environment_fingerprint="repro-env",
        build_fingerprint="repro-build",
    )
    evaluation = engine.evaluate_solver_runtime_profile_v2(provenance["provenance"]["provenance_id"])
    run = engine.record_reproducibility_run(
        result.result_id,
        outcome["outcome"]["outcome_id"],
        provenance["provenance"]["provenance_id"],
        evaluation["evaluation"]["evaluation_id"],
        semantic_projection_fingerprint="repro-semantic",
        proof_fingerprint="repro-proof",
        artifact_fingerprint="repro-artifact",
    )
    return {
        "result": result,
        "result_evidence_id": result_evidence.evidence_id,
        "outcome": outcome,
        "provenance": provenance,
        "evaluation": evaluation,
        "run": run,
    }


def test_two_compliant_durable_runs_receive_artifact_reproduced_certificate():
    engine = AASMEngine(ProblemSpec("v56 reproducibility runtime"))
    left = _add_result(engine, "a")
    right = _add_result(engine, "b")
    certified = engine.certify_reproducibility(left["run"]["run"]["run_id"], right["run"]["run"]["run_id"])
    certificate = certified["certificate"]
    assert certificate["claim_level"] == "ARTIFACT_REPRODUCED"
    assert certificate["configuration_same"] is True
    assert certificate["both_profile_compliant"] is True
    assert certificate["assignment_same"] is True
    assert certificate["proof_same"] is True
    assert certificate["artifact_same"] is True


def test_profile_noncompliance_caps_durable_certificate_at_no_claim():
    engine = AASMEngine(ProblemSpec("v56 reproducibility noncompliant"))
    left = _add_result(engine, "a")
    right = _add_result(engine, "b", threads=8)
    assert right["evaluation"]["evaluation"]["compliant"] is False
    certified = engine.certify_reproducibility(left["run"]["run"]["run_id"], right["run"]["run"]["run_id"])
    certificate = certified["certificate"]
    assert certificate["claim_level"] == "NO_REPRODUCIBILITY_CLAIM"
    assert "PROFILE_NONCOMPLIANT" in certificate["diagnostics"]


def test_reproducibility_chain_survives_sqlite_restart_and_can_be_recertified(tmp_path: Path):
    path = tmp_path / "repro-v56.db"
    store = SQLiteStore(str(path))
    engine = AASMEngine(ProblemSpec("v56 reproducibility sqlite"), store=store)
    machine_id = engine.snapshot.machine_id
    left = _add_result(engine, "a")
    right = _add_result(engine, "b")
    first = engine.certify_reproducibility(left["run"]["run"]["run_id"], right["run"]["run"]["run_id"])
    canonical = engine.snapshot.canonical_hash()
    certificate_id = first["certificate"]["certificate_id"]
    store.close()

    resumed_store = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, resumed_store)
    report = resumed.reproducibility_report()
    assert report["valid"] is True
    assert certificate_id in report["certificates"]
    second = resumed.certify_reproducibility(left["run"]["run"]["run_id"], right["run"]["run"]["run_id"])
    assert second["already_recorded"] is True
    assert second["certificate"]["fingerprint"] == first["certificate"]["fingerprint"]
    assert resumed.snapshot.canonical_hash() == canonical
    assert resumed.replay().canonical_hash() == canonical
    resumed_store.close()


def test_reproducibility_runtime_adds_no_parallel_table_or_truth_authority():
    engine = AASMEngine(ProblemSpec("v56 reproducibility contract"))
    contract = engine.reproducibility_runtime_contract_report()
    assert contract["parallel_reproducibility_table"] == "NONE"
    assert contract["run_materialization"] == "RE_RESOLVE_EXACT_BOUND_RESULT_OUTCOME_PROVENANCE_EVALUATION"
    assert contract["agreement_grants_truth"] is False
    assert contract["truth_authority"] == "NONE"
