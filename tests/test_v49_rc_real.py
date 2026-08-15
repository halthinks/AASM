import os
import pytest

from aasm import public_api_contract
from aasm.model import ProblemSpec
from aasm.runtime_v49 import AASMEngine as V49Engine
from aasm.semantic_solver_rc import (
    run_cross_backend_overlap_certification,
    run_rc_benchmarks,
    run_semantic_solver_rc_certification,
)

pytestmark = pytest.mark.skipif(
    os.environ.get("AASM_REQUIRE_RC_BACKENDS") != "1",
    reason="real v0.49 RC backends are exercised by the dedicated RC workflow",
)


def test_real_cross_backend_overlap_agrees_without_voting():
    report = run_cross_backend_overlap_certification(real=True)
    assert report["status"] == "PASS", report
    assert report["checks"]["sat_feasibility_projection_satisfied"] is True
    assert report["checks"]["cp_sat_optimum_is_one"] is True
    assert report["checks"]["milp_optimum_is_one"] is True
    assert report["checks"]["cp_sat_and_milp_objectives_agree"] is True
    assert report["voting"] == "NEVER"


def test_real_rc_benchmark_measures_full_tasklease_lifecycle_without_speedup_claim():
    report = run_rc_benchmarks(real=True, target_engine_cls=V49Engine, iterations=8)
    assert report["status"] == "PASS", report
    assert report["checks"]["real_direct_solver_completed"] is True
    assert report["checks"]["real_leased_solver_completed"] is True
    assert report["checks"]["real_leased_solver_replay_exact"] is True
    assert report["measurements"]["observed_orchestration_overhead_ratio"] >= 0
    assert report["inner_solver_claim"] == "NONE"


def test_real_semantic_solver_rc_certification_passes_complete_native_portfolio():
    report = run_semantic_solver_rc_certification(
        real=True,
        target_engine_cls=V49Engine,
        public_contract=public_api_contract(),
    )
    assert report["status"] == "PASS", report
    assert report["real_backends"] is True
    assert all(report["checks"].values())
    # The RC implementation remains v0.49, but certification freezes the
    # current public contract supplied by the caller, which is v0.52 here.
    assert report["freeze_manifest"]["runtime_version"] == "0.52.0"
    assert report["component_status"]["optimization"] == "PASS"
    assert report["component_status"]["modeling"] == "PASS"
    assert report["component_status"]["advanced_optimization"] == "PASS"


def test_real_rc_runtime_facade_preserves_existing_engine_path():
    engine = V49Engine(ProblemSpec("real rc facade"))
    report = engine.semantic_solver_rc_certify(real=False, public_contract=public_api_contract())
    assert report["status"] == "PASS"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()