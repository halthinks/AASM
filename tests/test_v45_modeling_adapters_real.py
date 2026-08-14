import os

import pytest

from aasm.convex_optimization import reference_convex_models
from aasm.model import ProblemSpec
from aasm.optimization import default_optimization_providers, reference_optimization_models
from aasm.pulp_adapter import pulp_problem_to_optimization_model
from aasm.runtime_v45 import AASMEngine


def _require():
    if os.environ.get("AASM_REQUIRE_MODELING_BACKENDS") == "1":
        import cvxpy  # noqa: F401
        import pulp  # noqa: F401
    else:
        pytest.importorskip("cvxpy")
        pytest.importorskip("pulp")


def test_real_cvxpy_qp_and_soc_cross_aasm_lease_evidence_and_replay():
    _require()
    engine = AASMEngine(ProblemSpec("v0.45 real cvxpy"))
    engine.install_default_convex_capability_contract(authority_id="policy", authority_class="POLICY")
    engine.register_default_cvxpy_provider_runtime(authority_id="policy", authority_class="POLICY")
    for model in reference_convex_models().values():
        engine.admit_convex_model(model)
        requested = engine.request_convex_optimization(model.model_id, requester_id="integration-test")
        lease = engine.claim_next_task("worker-cvxpy", lease_seconds=120)
        out = engine.execute_convex_lease(lease["lease_id"])
        assert out["result"]["status"] == "OPTIMAL", out
        assert out["satisfied"] is True
        assert out["obligation"]["status"] == "VERIFIED"
        evidence = next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == out["result_evidence_id"])
        assert evidence["metadata"]["result_authority"] == "EVIDENCE_ONLY"
        assert engine.convex_reuse_request(requested["request"]["request_id"]).kind == "OPTIMIZATION_RESULT"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_real_pulp_import_routes_to_existing_highs_native_path():
    _require()
    import pulp
    problem = pulp.LpProblem("pulp-native-route", pulp.LpMinimize)
    x = pulp.LpVariable("x", 0, 4, cat=pulp.LpInteger)
    y = pulp.LpVariable("y", 0, 4)
    problem += x + y
    problem += x + y >= 3, "demand"
    model = pulp_problem_to_optimization_model(problem)
    assert model.solver_family == "MILP"

    engine = AASMEngine(ProblemSpec("v0.45 PuLP to HiGHS"))
    engine.install_default_optimization_capability_contracts(authority_id="policy", authority_class="POLICY")
    highs = next(row for row in default_optimization_providers() if row.provider_id == "highs")
    engine.register_optimization_provider_runtime(highs, authority_id="policy", authority_class="POLICY")
    imported = engine.import_pulp_problem(problem, admit=True)
    admitted = imported["admitted"]["model"]
    request = engine.request_optimization(admitted["model_id"], requester_id="integration-test", required_provider="highs")
    lease = engine.claim_next_task("worker-highs", lease_seconds=120)
    out = engine.execute_optimization_lease(lease["lease_id"])
    assert out["result"]["status"] == "OPTIMAL", out
    assert out["obligation"]["status"] == "VERIFIED"
    assert out["result"]["solver"]["provider_id"] == "highs"
    assert request["request"]["model"]["metadata"]["source_modeler"] == "PuLP"


def test_pulp_unbounded_variables_are_rejected_not_silently_clamped():
    _require()
    import pulp
    problem = pulp.LpProblem("unbounded", pulp.LpMinimize)
    x = pulp.LpVariable("x", 0, None)
    problem += x
    with pytest.raises(ValueError, match="refuses semantic bound approximation"):
        pulp_problem_to_optimization_model(problem)
