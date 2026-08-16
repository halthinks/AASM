from __future__ import annotations

from pathlib import Path

import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.optimization import OPTIMIZATION_CONTRACT_ID, OptimizationConstraint, OptimizationModel, OptimizationObjective, OptimizationRequest, OptimizationResult, OptimizationSolverIdentity, OptimizationVariable
from aasm.persistence import SQLiteStore
from aasm.provider_status_v2 import default_provider_status_map
from aasm.runtime_v56_foundation import AASMEngine
from aasm.semantic_result import canonical_semantic_json
from aasm.solver_execution_observation import runtime_environment_fingerprint
from aasm.solver_provenance import SolverExecutionProfile


def _durable_chain(engine: AASMEngine):
    model = OptimizationModel(
        "prov-runtime-model",
        (OptimizationVariable("x", "INTEGER", 0, 10),),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1}, sense=">=", rhs=1),),
        OptimizationObjective("MINIMIZE", {"x": 1}), family="CP_SAT",
    )
    request = OptimizationRequest(model, "solver.cp_sat", "0.1.0", "prov-runtime-obligation", timeout_ms=5000, required_provider="ortools-cp-sat")
    request_evidence = engine.add_evidence(EvidenceRecord("optimization_request", canonical_semantic_json(request.to_dict()), source=OPTIMIZATION_CONTRACT_ID))
    result = OptimizationResult(
        request.request_id, request.fingerprint, model.fingerprint, "OPTIMAL",
        OptimizationSolverIdentity("ortools-cp-sat", "ortools.cp-sat", "9.15.6755", ("ortools.cp-sat",)),
        assignment={"x": 1.0}, objective_value=1.0, result_id="prov-runtime-result",
        statistics={"raw_status": "OPTIMAL", "raw_status_code": "4"},
    )
    result_evidence = engine.add_evidence(EvidenceRecord("optimization_result", canonical_semantic_json(result.to_dict()), source=OPTIMIZATION_CONTRACT_ID, derived_from=[request_evidence.evidence_id]))
    outcome = engine.record_solver_outcome_v2(result.result_id)
    profile = SolverExecutionProfile(
        "strict cp-sat runtime", "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"max_time_in_seconds": 5.0, "num_search_workers": 1, "random_seed": 0},
        required_effective_options={"num_search_workers": 1, "random_seed": 0},
        provider_id="ortools-cp-sat", provider_version="9.15.6755",
        adapter_id="aasm.optimization.ortools-cp-sat", adapter_version="0.1.0",
        required_worker_count=1, required_thread_count=1,
    )
    registered = engine.register_solver_execution_profile(profile)
    provenance = engine.record_solver_runtime_provenance(result.result_id, outcome["outcome"]["outcome_id"], profile.profile_id, execution_id="execution-runtime")
    evaluation = engine.evaluate_solver_runtime_profile(provenance["provenance"]["provenance_id"])
    return request, result, result_evidence, outcome, registered, provenance, evaluation


def test_runtime_derives_effective_configuration_from_adapter_not_caller():
    engine = AASMEngine(ProblemSpec("v56 provenance runtime"))
    request, result, _, outcome, profile, provenance, evaluation = _durable_chain(engine)
    row = provenance["provenance"]
    assert row["source_result_id"] == result.result_id
    assert row["source_outcome_id"] == outcome["outcome"]["outcome_id"]
    assert row["profile_id"] == profile["profile"]["profile_id"]
    assert row["adapter_id"] == "aasm.optimization.ortools-cp-sat"
    assert row["effective_options"] == {"max_time_in_seconds": 5.0, "num_search_workers": 1, "random_seed": 0}
    assert row["worker_count"] == 1 and row["thread_count"] == 1
    assert row["environment_fingerprint"] == runtime_environment_fingerprint()
    assert row["platform_identity"] and row["library_identity"]["ortools"] == "9.15.6755"
    assert row["provider_status_map_id"] == default_provider_status_map("ortools-cp-sat", "9.15.6755").map_id
    assert evaluation["evaluation"]["compliant"] is True


def test_provenance_evidence_lineage_contains_request_result_outcome_and_profile():
    engine = AASMEngine(ProblemSpec("v56 provenance lineage"))
    _, _, result_evidence, outcome, profile, provenance, _ = _durable_chain(engine)
    row = next(item for item in engine.snapshot.evidence["records"] if item["evidence_id"] == provenance["evidence_id"])
    assert result_evidence.evidence_id in row["derived_from"]
    assert outcome["evidence_id"] in row["derived_from"]
    assert profile["evidence_id"] in row["derived_from"]
    assert len(row["derived_from"]) >= 4


def test_caller_cannot_supply_fake_effective_options_to_runtime_api():
    engine = AASMEngine(ProblemSpec("no fake effective options"))
    _, result, _, outcome, profile, _, _ = _durable_chain(engine)
    with pytest.raises(TypeError):
        engine.record_solver_runtime_provenance(
            result.result_id, outcome["outcome"]["outcome_id"], profile["profile"]["profile_id"],
            execution_id="fake", effective_options={"num_search_workers": 999},
        )


def test_provenance_chain_survives_sqlite_restart_and_replay(tmp_path: Path):
    path = tmp_path / "prov-v561.db"
    store = SQLiteStore(str(path)); engine = AASMEngine(ProblemSpec("v561 provenance sqlite"), store=store)
    machine_id = engine.snapshot.machine_id
    _, _, _, _, _, provenance, evaluation = _durable_chain(engine)
    canonical = engine.snapshot.canonical_hash(); provenance_id = provenance["provenance"]["provenance_id"]; evaluation_id = evaluation["evaluation"]["evaluation_id"]
    store.close()
    resumed_store = SQLiteStore(str(path)); resumed = AASMEngine.resume(machine_id, resumed_store)
    report = resumed.solver_provenance_report()
    assert report["valid"] is True
    assert provenance_id in report["provenances"] and evaluation_id in report["evaluations"]
    assert resumed.snapshot.canonical_hash() == canonical
    assert resumed.replay().canonical_hash() == canonical
    resumed_store.close()


def test_runtime_contract_has_no_second_table_and_no_reproducibility_or_truth_claim():
    engine = AASMEngine(ProblemSpec("v561 provenance contract"))
    contract = engine.solver_provenance_runtime_contract_report()
    assert contract["parallel_provenance_table"] == "NONE"
    assert contract["effective_configuration_source"] == "AASM_PROVIDER_ADAPTER_OBSERVATION_NOT_CALLER_ASSERTION"
    assert contract["provenance_grants_reproducibility"] is False
    assert contract["truth_authority"] == "NONE"
    assert contract["policy_authority"] == "NONE"
