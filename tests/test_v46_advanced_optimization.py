import pytest

from aasm.advanced_optimization import (
    ADVANCED_CAPABILITIES,
    ADVANCED_PROVIDERS,
    AdvancedConvexProblem,
    AdvancedSolverIdentity,
    AdvancedSolverResult,
    advanced_optimization_contract,
    default_advanced_providers,
    reference_advanced_problems,
)
from aasm.model import ProblemSpec
from aasm.runtime_v46 import AASMEngine


def _provider(provider_id):
    return next(row for row in default_advanced_providers() if row.provider_id == provider_id)


def _engine(kind="FAST_SAT"):
    engine = AASMEngine(ProblemSpec("v0.46 advanced solver"))
    engine.install_default_advanced_optimization_capabilities(authority_id="policy", authority_class="POLICY")
    provider_id = ADVANCED_PROVIDERS[kind]
    engine.register_advanced_optimization_provider_runtime(_provider(provider_id), authority_id="policy", authority_class="POLICY")
    return engine


def test_advanced_contract_makes_search_state_non_authoritative():
    contract = advanced_optimization_contract()
    assert contract["contract_id"] == "aasm.optimization.advanced.v1"
    assert contract["scheduler"] == "EXISTING_AASM_RESOURCE_WORKER_LEASE"
    assert contract["result_authority"] == "EVIDENCE_ONLY"
    assert contract["incremental_sat"]["unsat_core"] is True
    assert contract["incremental_sat"]["learned_state"] == "EPHEMERAL_PERFORMANCE_ONLY"
    assert contract["milp_advanced"]["bound_gap_telemetry"] is True
    assert contract["truth_rule"] == "SEARCH_STATE_NEVER_PROMOTES_TRUTH"


def test_reference_advanced_problems_cover_all_five_kinds():
    problems = reference_advanced_problems()
    assert set(problems) == set(ADVANCED_CAPABILITIES)
    assert len({row.fingerprint for row in problems.values()}) == 5
    convex = problems["CONVEX_ADVANCED"]
    assert isinstance(convex, AdvancedConvexProblem)
    assert convex.affine_soc_constraints
    assert any(len(row.expression.coefficients) > 1 for row in convex.objective.quadratic_factors)


def test_base_model_must_be_durably_admitted_before_advanced_request():
    engine = _engine("FAST_SAT")
    problem = reference_advanced_problems()["FAST_SAT"]
    with pytest.raises(KeyError):
        engine.request_advanced_optimization(problem, requester_id="agent")
    engine.admit_optimization_model(problem.model)
    requested = engine.request_advanced_optimization(problem, requester_id="agent")
    assert requested["request"]["kind"] == "FAST_SAT"


def test_advanced_result_uses_existing_resource_worker_lease_and_evidence_path():
    engine = _engine("FAST_SAT")
    problem = reference_advanced_problems()["FAST_SAT"]
    engine.admit_optimization_model(problem.model)
    requested = engine.request_advanced_optimization(problem, requester_id="agent")
    lease = engine.claim_next_task("worker-kissat", lease_seconds=60)
    request = requested["request"]
    result = AdvancedSolverResult(
        request["request_id"], request["fingerprint"], problem.fingerprint, "SAT",
        AdvancedSolverIdentity("kissat", "pysat:kissat404", "fixture", "kissat404"),
        assignment={"x": 1, "y": 0},
    )
    committed = engine.commit_advanced_optimization_result(result, lease_id=lease["lease_id"])
    assert committed["satisfied"] is True
    evidence = next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == committed["result_evidence_id"])
    assert evidence["kind"] == "advanced_optimization_result"
    assert evidence["metadata"]["result_authority"] == "EVIDENCE_ONLY"
    replay = engine.commit_advanced_optimization_result(result, lease_id=lease["lease_id"])
    assert replay["already_committed"] is True
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_forged_advanced_provider_implementation_is_rejected_before_evidence():
    engine = _engine("FAST_SAT")
    problem = reference_advanced_problems()["FAST_SAT"]
    engine.admit_optimization_model(problem.model)
    requested = engine.request_advanced_optimization(problem, requester_id="agent")
    lease = engine.claim_next_task("worker-kissat", lease_seconds=60)
    request = requested["request"]
    before = len(engine.snapshot.evidence["records"])
    forged = AdvancedSolverResult(
        request["request_id"], request["fingerprint"], problem.fingerprint, "SAT",
        AdvancedSolverIdentity("kissat", "forged-backend", "fixture", "kissat404"),
        assignment={"x": 1, "y": 0},
    )
    with pytest.raises(ValueError, match="implementation does not match admitted provider"):
        engine.commit_advanced_optimization_result(forged, lease_id=lease["lease_id"])
    assert len(engine.snapshot.evidence["records"]) == before


def test_advanced_result_enters_existing_v41_reuse_request_shape():
    engine = _engine("FAST_SAT")
    problem = reference_advanced_problems()["FAST_SAT"]
    engine.admit_optimization_model(problem.model)
    requested = engine.request_advanced_optimization(problem, requester_id="agent")
    reuse = engine.advanced_optimization_reuse_request(requested["request"]["request_id"])
    assert reuse.kind == "OPTIMIZATION_RESULT"
    assert reuse.semantic_payload["advanced_kind"] == "FAST_SAT"
    assert reuse.effect_class == "PURE"
