from pathlib import Path

import pytest

from aasm.model import ProblemSpec
from aasm.optimization import OptimizationConstraint, OptimizationModel, OptimizationVariable
from aasm.persistence.sqlite import SQLiteStore
from aasm.runtime_v50 import AASMEngine as V50Engine
from aasm.runtime_v51 import AASMEngine as V51Engine
from aasm.solution_pool_conformance import run_solution_pool_conformance
from aasm.solution_pools import (
    ENUMERATION_CONTRACT_ID,
    SOLUTION_POOL_CONTRACT_ID,
    EnumerationCursor,
    EnumerationUnsupportedError,
    SolutionPool,
    SolutionRecord,
    certify_complete_finite_enumeration,
    enumeration_contract,
    solution_pool_contract,
)


def fixture_model():
    return OptimizationModel(
        "pool-fixture",
        (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1}, sense=">=", rhs=1),),
        family="CP_SAT",
    )


def test_v51_runtime_is_thin_v50_composition():
    assert issubclass(V51Engine, V50Engine)
    engine = V51Engine(ProblemSpec("v51 thin"))
    assert engine.solution_pool_contract_report()["contract_id"] == SOLUTION_POOL_CONTRACT_ID
    assert engine.enumeration_contract_report()["contract_id"] == ENUMERATION_CONTRACT_ID


def test_contract_distinguishes_complete_from_bounded_or_native_pool():
    pool = solution_pool_contract()
    enumeration = enumeration_contract()
    assert pool["complete_requires_independent_exhaustion_certificate"] is True
    assert pool["bounded_or_native_pool_implies_completeness"] is False
    assert pool["result_authority"] == "EVIDENCE_ONLY"
    assert pool["truth_authority"] == "EXISTING_AASM_POLICY_ONLY"
    assert enumeration["complete_claim_without_certificate"] == "REJECTED"
    assert enumeration["cross_backend_consistency"] == "EXACT_SOLUTION_SET_EQUALITY_NEVER_VOTING"


def test_complete_enumeration_returns_every_solution_once_and_certificate():
    model = fixture_model()
    engine = V51Engine(ProblemSpec("complete"))
    report = engine.enumerate_complete_solution_pool(model, max_states_per_step=1, max_total_states=8)
    pool = report["pool"]
    assert pool["completeness_status"] == "COMPLETE"
    assert len(pool["solutions"]) == 3
    assert len(set(pool["solution_ids"])) == 3
    assert len(pool["exclusion_ids"]) == 3
    cert = report["completeness_certificate"]
    assert cert["status"] == "PASS"
    assert cert["independent_of_solver"] is True
    assert cert["feasible_count"] == 3
    assert cert["unseen_solution_count"] == 0
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_restart_mid_enumeration_resumes_without_duplicates(tmp_path: Path):
    model = fixture_model()
    store = SQLiteStore(str(tmp_path / "pool.db"))
    engine = V51Engine(ProblemSpec("restart"), store=store)
    machine_id = engine.snapshot.machine_id
    started = engine.start_solution_pool(model, max_total_states=8)
    pool_id = started["pool"]["pool_id"]
    first = engine.advance_solution_pool(pool_id, model, max_states_per_step=2, max_total_states=8)
    assert first["cursor"]["next_state_index"] == 2
    assert first["pool"]["completeness_status"] == "PARTIAL"
    store.close()

    resumed_store = SQLiteStore(str(tmp_path / "pool.db"))
    resumed = V51Engine.resume(machine_id, resumed_store)
    before = resumed.solution_pool_report(pool_id)["pool"]
    assert len(before["solution_ids"]) == len(set(before["solution_ids"]))
    resumed.advance_solution_pool(pool_id, model, max_states_per_step=1, max_total_states=8)
    resumed.advance_solution_pool(pool_id, model, max_states_per_step=10, max_total_states=8)
    final = resumed.solution_pool_report(pool_id)
    assert final["pool"]["completeness_status"] == "COMPLETE"
    assert len(final["pool"]["solution_ids"]) == len(set(final["pool"]["solution_ids"])) == 3
    assert final["completeness_certificate"]["status"] == "PASS"
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    resumed_store.close()


def test_partial_pool_never_claims_complete_even_if_cursor_exhausts():
    model = fixture_model()
    engine = V51Engine(ProblemSpec("partial"))
    started = engine.start_solution_pool(model, mode="BOUNDED_PARTIAL_POOL", max_total_states=8)
    pool_id = started["pool"]["pool_id"]
    engine.advance_solution_pool(pool_id, model, max_states_per_step=99, max_total_states=8)
    report = engine.solution_pool_report(pool_id)
    assert report["pool"]["completeness_status"] == "PARTIAL_NON_EXHAUSTIVE"
    assert report["completeness_certificate"] is None


def test_duplicate_manual_solution_is_idempotent_and_no_double_count():
    model = fixture_model()
    engine = V51Engine(ProblemSpec("dedupe"))
    started = engine.start_solution_pool(model, mode="DIVERSE_POOL")
    pool_id = started["pool"]["pool_id"]
    first = engine.admit_solution_to_pool(pool_id, model, {"x": 1, "y": 0}, solver_provider_id="fixture")
    second = engine.admit_solution_to_pool(pool_id, model, {"x": 1, "y": 0}, solver_provider_id="fixture")
    assert first["already_present"] is False
    assert second["already_present"] is True
    report = engine.solution_pool_report(pool_id)
    assert len(report["pool"]["solutions"]) == 1
    assert len(report["pool"]["exclusion_ids"]) == 1


def test_false_completeness_claim_fails_closed():
    model = fixture_model()
    one = SolutionRecord(model.fingerprint, {"x": 1, "y": 0})
    pool = SolutionPool(model.fingerprint, "COMPLETE_FINITE_ENUMERATION", solutions=(one,), completeness_status="EXHAUSTED_PENDING_CERTIFICATION")
    cursor = EnumerationCursor(pool.pool_id, model.fingerprint, pool.mode, 4, 4, accepted_solution_ids=(one.solution_id,), exhausted=True)
    cert = certify_complete_finite_enumeration(model, pool, cursor=cursor, max_total_states=8)
    assert cert.status == "FAIL"
    assert cert.unseen_solution_count == 2


def test_continuous_complete_enumeration_is_explicitly_unsupported():
    model = OptimizationModel(
        "continuous",
        (OptimizationVariable("x", "CONTINUOUS", 0, 1),),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1}, sense=">=", rhs=0),),
        family="MILP",
    )
    engine = V51Engine(ProblemSpec("continuous"))
    with pytest.raises(EnumerationUnsupportedError):
        engine.start_solution_pool(model, mode="COMPLETE_FINITE_ENUMERATION")


def test_dependency_neutral_conformance_passes():
    report = run_solution_pool_conformance(real_backends=False)
    assert report["status"] == "PASS", report
    assert all(report["checks"].values())
