from __future__ import annotations

from pathlib import Path

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.optimization import OPTIMIZATION_CONTRACT_ID, OptimizationResult, OptimizationSolverIdentity
from aasm.persistence import SQLiteStore
from aasm.runtime_v56_foundation import AASMEngine
from aasm.semantic_result import canonical_semantic_json
from aasm.solver_provenance import SolverExecutionProfile


def _result(engine: AASMEngine) -> OptimizationResult:
    result = OptimizationResult(
        "prov-runtime-request",
        "prov-runtime-request-fp",
        "prov-runtime-model-fp",
        "FEASIBLE",
        OptimizationSolverIdentity(
            "prov-runtime-provider",
            "solver.impl",
            "2",
            ("solver", "--threads=1", "--seed=3"),
        ),
        assignment={"x": 1.0},
        result_id="prov-runtime-result",
    )
    engine.add_evidence(
        EvidenceRecord(
            kind="optimization_result",
            statement=canonical_semantic_json(result.to_dict()),
            source=OPTIMIZATION_CONTRACT_ID,
        )
    )
    return result


def _chain(engine: AASMEngine):
    result = _result(engine)
    outcome = engine.record_solver_outcome_v2(result.result_id)
    profile = SolverExecutionProfile(
        "strict runtime profile",
        "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"threads": 1, "seed": 3},
        required_effective_options={"threads": 1, "seed": 3},
        provider_id="prov-runtime-provider",
        provider_version="2",
        adapter_id="aasm.prov-runtime",
        adapter_version="1",
        required_environment_fingerprint="env-runtime",
    )
    registered = engine.register_solver_execution_profile(profile)
    provenance = engine.record_solver_runtime_provenance_v2(
        result.result_id,
        outcome["outcome"]["outcome_id"],
        profile.profile_id,
        execution_id="execution-runtime",
        adapter_id="aasm.prov-runtime",
        adapter_version="1",
        effective_options={"threads": 1, "seed": 3, "presolve": True},
        environment_fingerprint="env-runtime",
        build_fingerprint="build-runtime",
        dependency_fingerprints=("dep-b", "dep-a"),
    )
    evaluation = engine.evaluate_solver_runtime_profile_v2(provenance["provenance"]["provenance_id"])
    return result, outcome, registered, provenance, evaluation


def test_durable_provenance_chain_binds_exact_result_outcome_profile_and_adapter():
    engine = AASMEngine(ProblemSpec("v56 provenance runtime"))
    result, outcome, profile, provenance, evaluation = _chain(engine)
    row = provenance["provenance"]
    assert row["source_result_id"] == result.result_id
    assert row["source_result_fingerprint"] == result.fingerprint
    assert row["source_outcome_id"] == outcome["outcome"]["outcome_id"]
    assert row["profile_id"] == profile["profile"]["profile_id"]
    assert row["adapter_id"] == "aasm.prov-runtime"
    assert row["adapter_version"] == "1"
    assert row["requested_options"] == {"seed": 3, "threads": 1}
    assert row["effective_options"]["presolve"] is True
    assert evaluation["evaluation"]["compliant"] is True


def test_provenance_evidence_lineage_contains_result_outcome_and_profile():
    engine = AASMEngine(ProblemSpec("v56 provenance lineage"))
    _, outcome, profile, provenance, _ = _chain(engine)
    provenance_evidence = next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == provenance["evidence_id"])
    assert outcome["evidence_id"] in provenance_evidence["derived_from"]
    assert profile["evidence_id"] in provenance_evidence["derived_from"]
    assert len(provenance_evidence["derived_from"]) >= 3


def test_profile_override_is_durable_noncompliance_not_hidden():
    engine = AASMEngine(ProblemSpec("v56 provenance override"))
    result = _result(engine)
    outcome = engine.record_solver_outcome_v2(result.result_id)
    profile = SolverExecutionProfile(
        "strict override profile",
        "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"threads": 1},
        required_effective_options={"threads": 1},
    )
    engine.register_solver_execution_profile(profile)
    provenance = engine.record_solver_runtime_provenance_v2(
        result.result_id,
        outcome["outcome"]["outcome_id"],
        profile.profile_id,
        execution_id="execution-override",
        adapter_id="aasm.prov-runtime",
        adapter_version="1",
        effective_options={"threads": 8},
        environment_fingerprint="env-runtime",
    )
    evaluation = engine.evaluate_solver_runtime_profile_v2(provenance["provenance"]["provenance_id"])
    assert evaluation["evaluation"]["compliant"] is False
    assert any(row["code"] == "REQUIRED_EFFECTIVE_OPTION_MISMATCH" for row in evaluation["evaluation"]["deviations"])


def test_provenance_chain_survives_sqlite_restart_and_replay(tmp_path: Path):
    path = tmp_path / "prov-v56.db"
    store = SQLiteStore(str(path))
    engine = AASMEngine(ProblemSpec("v56 provenance sqlite"), store=store)
    machine_id = engine.snapshot.machine_id
    _, _, _, provenance, evaluation = _chain(engine)
    canonical = engine.snapshot.canonical_hash()
    provenance_id = provenance["provenance"]["provenance_id"]
    evaluation_id = evaluation["evaluation"]["evaluation_id"]
    store.close()

    resumed_store = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, resumed_store)
    report = resumed.solver_provenance_v2_report()
    assert report["valid"] is True
    assert provenance_id in report["provenances"]
    assert evaluation_id in report["evaluations"]
    assert resumed.snapshot.canonical_hash() == canonical
    assert resumed.replay().canonical_hash() == canonical
    resumed_store.close()


def test_provenance_runtime_contract_adds_no_parallel_table_or_reproducibility_claim():
    engine = AASMEngine(ProblemSpec("v56 provenance contract"))
    contract = engine.solver_provenance_v2_runtime_contract_report()
    assert contract["parallel_provenance_table"] == "NONE"
    assert contract["source_result"] == "EXACT_DURABLE_OPTIMIZATION_RESULT_REQUIRED"
    assert contract["source_outcome"] == "EXACT_DURABLE_SOLVER_OUTCOME_V2_REQUIRED"
    assert contract["provenance_grants_reproducibility"] is False
    assert contract["truth_authority"] == "NONE"
