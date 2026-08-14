import os
import pytest

from aasm.advanced_optimization import (
    ADVANCED_PROVIDERS,
    clear_incremental_sat_sessions,
    default_advanced_providers,
    reference_advanced_problems,
)
from aasm.advanced_optimization_conformance import run_advanced_optimization_conformance
from aasm.model import ProblemSpec
from aasm.runtime_v46 import AASMEngine


pytestmark = pytest.mark.skipif(
    os.environ.get("AASM_REQUIRE_ADVANCED_BACKENDS") != "1",
    reason="real advanced solver backends are exercised only in the dedicated workflow",
)


def _provider(provider_id):
    return next(row for row in default_advanced_providers() if row.provider_id == provider_id)


def _backend_failures(report):
    return {
        kind: {"status": row.get("status"), "diagnostics": row.get("diagnostics"), "solver": row.get("solver")}
        for kind, row in report.get("results", {}).items()
        if row.get("status") == "ERROR"
    }


def test_real_advanced_conformance_executes_kissat_incremental_cadical_scheduling_highs_and_cvxpy():
    report = run_advanced_optimization_conformance(real=True)
    assert report["status"] == "PASS", {"checks": report["checks"], "backend_failures": _backend_failures(report)}
    for check in (
        "fast_sat_real_backend_executes",
        "incremental_sat_real_backend_executes",
        "incremental_sat_unsat_core_returned",
        "incremental_sat_session_reused",
        "cp_sat_scheduling_real_backend_executes",
        "cp_sat_deterministic_time_telemetry_present",
        "milp_advanced_real_backend_executes",
        "milp_bound_telemetry_present",
        "milp_warm_start_recorded",
        "convex_advanced_real_backend_executes",
    ):
        assert report["checks"][check] is True, {"failed_check": check, "backend_failures": _backend_failures(report)}


def test_every_real_advanced_backend_runs_through_aasm_resource_worker_lease_and_evidence():
    clear_incremental_sat_sessions()
    engine = AASMEngine(ProblemSpec("v0.46 real advanced lifecycle"))
    engine.install_default_advanced_optimization_capabilities(authority_id="policy", authority_class="POLICY")
    for provider in default_advanced_providers():
        engine.register_advanced_optimization_provider_runtime(provider, authority_id="policy", authority_class="POLICY")
    problems = reference_advanced_problems()
    expected = {
        "FAST_SAT": {"SAT"},
        "INCREMENTAL_SAT": {"UNSAT"},
        "CP_SAT_SCHEDULING": {"OPTIMAL"},
        "MILP_ADVANCED": {"OPTIMAL", "FEASIBLE"},
        "CONVEX_ADVANCED": {"OPTIMAL"},
    }
    for kind, problem in problems.items():
        base = getattr(problem, "model", None)
        if base is not None:
            engine.admit_optimization_model(base)
        requested = engine.request_advanced_optimization(problem, requester_id="real-test")
        worker_id = f"worker-{ADVANCED_PROVIDERS[kind]}"
        lease = engine.claim_next_task(worker_id, lease_seconds=120)
        committed = engine.execute_advanced_optimization_lease(lease["lease_id"])
        result = committed["result"]
        assert result["status"] in expected[kind], {"kind": kind, "status": result["status"], "diagnostics": result.get("diagnostics"), "solver": result.get("solver")}
        assert committed["satisfied"] is True
        evidence = next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == committed["result_evidence_id"])
        assert evidence["metadata"]["result_authority"] == "EVIDENCE_ONLY"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
