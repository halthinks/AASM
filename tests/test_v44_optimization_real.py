import importlib
import os

import pytest

from aasm.model import ProblemSpec
from aasm.optimization import (
    default_optimization_providers,
    reference_optimization_models,
    solve_optimization_request,
    validate_optimization_result,
)
from aasm.optimization_conformance import run_optimization_conformance
from aasm.runtime_v44 import AASMEngine


def _require_backends():
    modules = ("pysat.solvers", "ortools.sat.python.cp_model", "highspy")
    if os.environ.get("AASM_REQUIRE_OPTIMIZATION_BACKENDS") == "1":
        for name in modules:
            importlib.import_module(name)
    else:
        for name in modules:
            pytest.importorskip(name)


def _provider(provider_id):
    return next(row for row in default_optimization_providers() if row.provider_id == provider_id)


def test_real_native_backend_conformance():
    _require_backends()
    report = run_optimization_conformance(real=True)
    assert report["status"] == "PASS", report
    assert report["checks"]["sat_native_backend_executes"] is True
    assert report["checks"]["cp_sat_native_backend_executes"] is True
    assert report["checks"]["milp_native_backend_executes"] is True


def test_real_backends_cross_existing_aasm_lease_and_evidence_boundary():
    _require_backends()
    engine = AASMEngine(ProblemSpec("v0.44 real optimization portfolio"))
    engine.install_default_optimization_capability_contracts(authority_id="policy", authority_class="POLICY")
    for provider in default_optimization_providers():
        engine.register_optimization_provider_runtime(provider, authority_id="policy", authority_class="POLICY")

    provider_for = {"SAT": "cadical", "CP_SAT": "ortools-cp-sat", "MILP": "highs"}
    expected = {"SAT": "SAT", "CP_SAT": "OPTIMAL", "MILP": "OPTIMAL"}
    for family, model in reference_optimization_models().items():
        engine.admit_optimization_model(model)
        requested = engine.request_optimization(
            model.model_id,
            requester_id="integration-test",
            required_provider=provider_for[family],
        )
        lease = engine.claim_next_task(f"worker-{provider_for[family]}", lease_seconds=120)
        out = engine.execute_optimization_lease(lease["lease_id"])
        assert out["result"]["status"] == expected[family], out
        assert out["satisfied"] is True
        assert out["obligation"]["status"] == "VERIFIED"
        stored = engine.optimization_result_report(requested["request"]["request_id"])["results"]
        assert len(stored) == 1
        validate_optimization_result(
            engine.optimization_request_report(requested["request"]["request_id"])["request"],
            stored[0]["result"],
        )
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
