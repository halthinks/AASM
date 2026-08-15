from __future__ import annotations

from pathlib import Path

import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.optimization import OPTIMIZATION_CONTRACT_ID, OptimizationResult, OptimizationSolverIdentity
from aasm.persistence import SQLiteStore
from aasm.runtime_v56_foundation import AASMEngine
from aasm.semantic_result import canonical_semantic_json
from aasm.solver_outcome_v2 import SolverEvidenceGrade


def _durable_result(engine: AASMEngine, *, status: str = "TIMEOUT", assignment=None) -> OptimizationResult:
    result = OptimizationResult(
        "runtime-request",
        "runtime-request-fingerprint",
        "runtime-model-fingerprint",
        status,
        OptimizationSolverIdentity("runtime-provider", "solver.runtime", "1"),
        assignment=assignment or {},
        objective_value=7.0 if assignment else None,
        best_bound=5.0 if assignment else None,
        relative_gap=0.25 if assignment else None,
        result_id=f"runtime-result-{status.lower()}",
    )
    engine.add_evidence(
        EvidenceRecord(
            kind="optimization_result",
            statement=canonical_semantic_json(result.to_dict()),
            source=OPTIMIZATION_CONTRACT_ID,
        ),
        reason="runtime result fixture",
    )
    return result


def test_runtime_records_normalization_as_evidence_over_exact_durable_result():
    engine = AASMEngine(ProblemSpec("v56 runtime"))
    result = _durable_result(engine, assignment={"x": 1.0})
    recorded = engine.record_solver_outcome_v2(result.result_id)
    outcome = recorded["outcome"]
    assert outcome["source_result_id"] == result.result_id
    assert outcome["source_result_fingerprint"] == result.fingerprint
    assert outcome["termination"]["reason"] == "TIME_LIMIT"
    assert outcome["solution_status"] == "FEASIBLE"
    assert outcome["incumbent_status"] == "PRESENT"
    assert outcome["best_bound"] == 5.0
    assert outcome["relative_gap"] == 0.25
    assert recorded["evidence_id"] in {row["evidence_id"] for row in engine.snapshot.evidence["records"]}
    report = engine.solver_outcome_v2_report(outcome["outcome_id"])
    assert report["valid"] is True
    assert report["outcome"]["fingerprint"] == outcome["fingerprint"]


def test_runtime_requires_local_independent_validation_evidence():
    engine = AASMEngine(ProblemSpec("v56 validation lineage"))
    result = _durable_result(engine, status="FEASIBLE", assignment={"x": 1.0})
    grade = SolverEvidenceGrade(
        "INDEPENDENTLY_VALIDATED",
        "NO_CERTIFICATE",
        validation_evidence_ids=("missing-validation",),
    )
    with pytest.raises(KeyError, match="unknown evidence"):
        engine.record_solver_outcome_v2(result.result_id, evidence=grade)

    validation = engine.add_observation("independent source-model validation passed", source="v56-test")
    valid_grade = SolverEvidenceGrade(
        "INDEPENDENTLY_VALIDATED",
        "NO_CERTIFICATE",
        validation_evidence_ids=(validation.evidence_id,),
    )
    recorded = engine.record_solver_outcome_v2(result.result_id, evidence=valid_grade)
    row = next(item for item in engine.snapshot.evidence["records"] if item["evidence_id"] == recorded["evidence_id"])
    assert validation.evidence_id in row["derived_from"]


def test_runtime_rejects_unknown_source_result():
    engine = AASMEngine(ProblemSpec("v56 unknown source"))
    with pytest.raises(KeyError, match="unknown durable optimization result"):
        engine.record_solver_outcome_v2("not-there")


def test_runtime_is_idempotent_for_exact_same_normalization():
    engine = AASMEngine(ProblemSpec("v56 idempotent"))
    result = _durable_result(engine, status="FEASIBLE", assignment={"x": 1.0})
    first = engine.record_solver_outcome_v2(result.result_id)
    second = engine.record_solver_outcome_v2(result.result_id)
    assert first["outcome"]["fingerprint"] == second["outcome"]["fingerprint"]
    assert second["already_recorded"] is True
    assert first["evidence_id"] == second["evidence_id"]


def test_runtime_projection_survives_sqlite_restart_and_replay(tmp_path: Path):
    path = tmp_path / "v56.db"
    store = SQLiteStore(str(path))
    engine = AASMEngine(ProblemSpec("v56 sqlite"), store=store)
    machine_id = engine.snapshot.machine_id
    result = _durable_result(engine, status="FEASIBLE", assignment={"x": 1.0})
    recorded = engine.record_solver_outcome_v2(result.result_id)
    expected_hash = engine.snapshot.canonical_hash()
    store.close()

    resumed_store = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, resumed_store)
    report = resumed.solver_outcome_v2_report(recorded["outcome"]["outcome_id"])
    assert report["valid"] is True
    assert report["outcome"]["fingerprint"] == recorded["outcome"]["fingerprint"]
    assert resumed.snapshot.canonical_hash() == expected_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    resumed_store.close()


def test_runtime_contract_declares_no_parallel_result_table_or_truth_authority():
    engine = AASMEngine(ProblemSpec("v56 contract"))
    contract = engine.solver_outcome_v2_runtime_contract_report()
    assert contract["parallel_result_table"] == "NONE"
    assert contract["source_binding"] == "EXACT_RESULT_ID_AND_FINGERPRINT"
    assert contract["normalization_grants_truth"] is False
    assert contract["truth_authority"] == "NONE"
