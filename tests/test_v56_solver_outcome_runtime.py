from __future__ import annotations

from pathlib import Path

import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.optimization import (
    OPTIMIZATION_CONTRACT_ID,
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationRequest,
    OptimizationResult,
    OptimizationSolverIdentity,
    OptimizationVariable,
)
from aasm.persistence import SQLiteStore
from aasm.runtime_v56_foundation import AASMEngine
from aasm.semantic_result import canonical_semantic_json
from aasm.solver_outcome_v2 import SolverEvidenceGrade


def _durable_result(engine: AASMEngine, *, status: str = "TIMEOUT", assignment=None, raw_status="UNKNOWN", raw_code="0") -> OptimizationResult:
    model = OptimizationModel(
        "runtime-v56-model",
        (OptimizationVariable("x", "INTEGER", 0, 10),),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1}, sense=">=", rhs=1),),
        OptimizationObjective("MINIMIZE", {"x": 1}),
        family="CP_SAT",
    )
    request = OptimizationRequest(model, "solver.cp_sat", "0.1.0", "runtime-v56-obligation", required_provider="ortools-cp-sat")
    engine.add_evidence(EvidenceRecord(kind="optimization_request", statement=canonical_semantic_json(request.to_dict()), source=OPTIMIZATION_CONTRACT_ID), reason="runtime request fixture")
    assignment = assignment or {}
    result = OptimizationResult(
        request.request_id,
        request.fingerprint,
        model.fingerprint,
        status,
        OptimizationSolverIdentity("ortools-cp-sat", "ortools.cp-sat", "9.15.6755"),
        assignment=assignment,
        objective_value=float(assignment["x"]) if assignment else None,
        best_bound=1.0 if assignment else None,
        relative_gap=0.5 if assignment else None,
        statistics={"raw_status": raw_status, "raw_status_code": raw_code},
        result_id=f"runtime-result-{status.lower()}-{bool(assignment)}",
    )
    engine.add_evidence(EvidenceRecord(kind="optimization_result", statement=canonical_semantic_json(result.to_dict()), source=OPTIMIZATION_CONTRACT_ID), reason="runtime result fixture")
    return result


def test_runtime_records_exact_provider_mapping_and_durable_incumbent_validation():
    engine = AASMEngine(ProblemSpec("v56 runtime"))
    result = _durable_result(engine, status="FEASIBLE", assignment={"x": 2.0}, raw_status="FEASIBLE", raw_code="2")
    recorded = engine.record_solver_outcome_v2(result.result_id)
    outcome = recorded["outcome"]
    assert outcome["normalized_status"] == "FEASIBLE_NOT_PROVEN_OPTIMAL"
    assert outcome["source_result_fingerprint"] == result.fingerprint
    assert outcome["incumbent_validation"] == "VALIDATED"
    assert outcome["evidence"]["grade"] == "INDEPENDENTLY_VALIDATED"
    assert outcome["provider_status_rule_id"]
    assert outcome["legacy_projection"]["status"] == "FEASIBLE"
    validation_ids = outcome["evidence"]["validation_evidence_ids"]
    assert len(validation_ids) == 1
    validation_row = next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == validation_ids[0])
    assert validation_row["kind"] == "solver_incumbent_validation_v2"
    assert validation_row["derived_from"]


def test_runtime_model_invalid_is_not_infeasible():
    engine = AASMEngine(ProblemSpec("v56 model invalid"))
    result = _durable_result(engine, status="ERROR", raw_status="MODEL_INVALID", raw_code="1")
    recorded = engine.record_solver_outcome_v2(result.result_id)
    assert recorded["outcome"]["normalized_status"] == "MODEL_INVALID"
    assert recorded["outcome"]["solution_status"] == "UNKNOWN"
    assert recorded["outcome"]["legacy_projection"]["status"] == "ERROR"


def test_runtime_rejects_invalid_incumbent_before_evidence_admission():
    engine = AASMEngine(ProblemSpec("v56 invalid incumbent"))
    result = _durable_result(engine, status="FEASIBLE", assignment={"x": 0.0}, raw_status="FEASIBLE", raw_code="2")
    with pytest.raises(ValueError, match="violates"):
        engine.record_solver_outcome_v2(result.result_id)
    assert not [row for row in engine.snapshot.evidence["records"] if row.get("kind") == "solver_outcome_v2"]


def test_runtime_requires_local_user_supplied_validation_evidence():
    engine = AASMEngine(ProblemSpec("v56 validation lineage"))
    result = _durable_result(engine, status="FEASIBLE", assignment={"x": 1.0}, raw_status="FEASIBLE", raw_code="2")
    grade = SolverEvidenceGrade("INDEPENDENTLY_VALIDATED", "NO_CERTIFICATE", validation_evidence_ids=("missing-validation",))
    with pytest.raises(KeyError, match="unknown evidence"):
        engine.record_solver_outcome_v2(result.result_id, evidence=grade)


def test_runtime_rejects_unknown_source_result():
    engine = AASMEngine(ProblemSpec("v56 unknown source"))
    with pytest.raises(KeyError, match="unknown durable optimization result"):
        engine.record_solver_outcome_v2("not-there")


def test_runtime_is_idempotent_for_exact_same_normalization():
    engine = AASMEngine(ProblemSpec("v56 idempotent"))
    result = _durable_result(engine, status="FEASIBLE", assignment={"x": 1.0}, raw_status="FEASIBLE", raw_code="2")
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
    result = _durable_result(engine, status="FEASIBLE", assignment={"x": 1.0}, raw_status="FEASIBLE", raw_code="2")
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


def test_runtime_contract_declares_existing_evidence_path_and_no_parallel_result_table():
    engine = AASMEngine(ProblemSpec("v56 contract"))
    contract = engine.solver_outcome_v2_runtime_contract_report()
    assert contract["parallel_result_table"] == "NONE"
    assert contract["source_binding"] == "EXACT_REQUEST_RESULT_MODEL_AND_FINGERPRINT"
    assert contract["provider_mapping"] == "EXACT_VERSIONED_PROVIDER_STATUS_MAP"
    assert contract["incumbent_validation"] == "AASM_VALIDATE_OPTIMIZATION_SOLUTION_BEFORE_ACCEPTANCE"
    assert contract["truth_authority"] == "NONE"
