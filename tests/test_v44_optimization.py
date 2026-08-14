import pytest

import aasm.runtime_v44 as runtime_v44
from aasm import __version__, validate_public_api_contract
from aasm.model import ProblemSpec
from aasm.optimization import (
    OPTIMIZATION_CAPABILITIES,
    OptimizationResult,
    OptimizationSolverIdentity,
    default_optimization_providers,
    optimization_blueprint,
    reference_optimization_models,
    validate_optimization_solution,
)
from aasm.reuse_model import ReuseCandidate
from aasm.runtime_v44 import AASMEngine
from aasm.solver_types import SolverStepRequest


CADICAL_IMPLEMENTATION = "pysat:cadical195"


def _provider(provider_id):
    return next(row for row in default_optimization_providers() if row.provider_id == provider_id)


def _engine_with_sat():
    engine = AASMEngine(ProblemSpec("v0.44 SAT lifecycle"))
    engine.install_default_optimization_capability_contracts(authority_id="policy", authority_class="POLICY")
    engine.register_optimization_provider_runtime(_provider("cadical"), authority_id="policy", authority_class="POLICY")
    return engine


def _sat_result(request, model, *, implementation=CADICAL_IMPLEMENTATION, assignment=None):
    return OptimizationResult(
        request["request_id"],
        request["fingerprint"],
        model.fingerprint,
        "SAT",
        OptimizationSolverIdentity("cadical", implementation, "fixture-1"),
        assignment=assignment or {"x": 0, "y": 1},
    )


def test_v44_public_contract_is_live_and_preserves_formal_portfolio():
    assert __version__ == "0.47.1"
    report = validate_public_api_contract()
    assert report["valid"], report
    assert report["contract"]["contract_version"] == "0.23.0"
    optimization = report["contract"]["optimization"]
    assert optimization["contract_id"] == "aasm.optimization.v1"
    assert optimization["scheduler"] == "EXISTING_AASM_RESOURCE_WORKER_LEASE"
    assert optimization["result_authority"] == "EVIDENCE_ONLY"
    assert optimization["formal_providers_preserved"] == ["z3", "cvc5", "vampire", "lean4"]


def test_blueprint_exposes_three_optimization_backends():
    blueprint = optimization_blueprint()
    assert [row["provider_id"] for row in blueprint["providers"]] == ["cadical", "ortools-cp-sat", "highs"]
    assert {row["capability_id"] for row in blueprint["capabilities"]} == set(OPTIMIZATION_CAPABILITIES.values())


def test_canonical_ir_selects_sat_cp_sat_and_milp_without_guessing():
    models = reference_optimization_models()
    assert models["SAT"].solver_family == "SAT"
    assert models["CP_SAT"].solver_family == "CP_SAT"
    assert models["MILP"].solver_family == "MILP"
    assert len({row.fingerprint for row in models.values()}) == 3


def test_solution_validator_rejects_invalid_sat_assignment():
    model = reference_optimization_models()["SAT"]
    validate_optimization_solution(model, {"x": 0, "y": 1})
    with pytest.raises(ValueError, match="violates clause"):
        validate_optimization_solution(model, {"x": 0, "y": 0})


def test_existing_capability_resource_worker_and_lease_path_is_used():
    engine = _engine_with_sat()
    provider = _provider("cadical")
    resource = next(row for row in engine.list_resources() if row["resource_id"] == provider.resource_id)
    worker = next(row for row in engine.list_workers() if row["worker_id"] == "worker-cadical")
    assert resource["kind"] == "optimization-solver"
    assert provider.capability_token in resource["capabilities"]
    assert provider.provider_token in resource["capabilities"]
    assert worker["resource_id"] == resource["resource_id"]


def test_result_commit_is_evidence_only_and_replay_safe():
    engine = _engine_with_sat()
    model = reference_optimization_models()["SAT"]
    admitted = engine.admit_optimization_model(model)
    requested = engine.request_optimization(model.model_id, requester_id="agent", required_provider="cadical")
    lease = engine.claim_next_task("worker-cadical", lease_seconds=60)
    result = _sat_result(requested["request"], model)
    committed = engine.commit_optimization_result(result, lease_id=lease["lease_id"])
    assert committed["satisfied"] is True
    assert committed["obligation"]["status"] == "VERIFIED"
    evidence = next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == committed["result_evidence_id"])
    assert evidence["kind"] == "optimization_result"
    assert evidence["metadata"]["result_authority"] == "EVIDENCE_ONLY"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
    assert admitted["model"]["fingerprint"] == model.fingerprint


def test_forged_provider_implementation_is_rejected_before_result_admission():
    engine = _engine_with_sat()
    model = reference_optimization_models()["SAT"]
    engine.admit_optimization_model(model)
    requested = engine.request_optimization(model.model_id, requester_id="agent", required_provider="cadical")
    lease = engine.claim_next_task("worker-cadical", lease_seconds=60)
    before = len(engine.snapshot.evidence["records"])
    with pytest.raises(ValueError, match="implementation does not match admitted provider"):
        engine.commit_optimization_result(
            _sat_result(requested["request"], model, implementation="forged-backend"),
            lease_id=lease["lease_id"],
        )
    assert len(engine.snapshot.evidence["records"]) == before
    assert next(row for row in engine.list_leases() if row["lease_id"] == lease["lease_id"])["status"] == "ACTIVE"


def test_expired_optimization_lease_is_rejected_before_result_admission(monkeypatch):
    engine = _engine_with_sat()
    model = reference_optimization_models()["SAT"]
    engine.admit_optimization_model(model)
    requested = engine.request_optimization(model.model_id, requester_id="agent", required_provider="cadical")
    lease = engine.claim_next_task("worker-cadical", lease_seconds=60)
    monkeypatch.setattr(runtime_v44, "now", lambda: float(lease["expires_at"]) + 1.0)
    before = len(engine.snapshot.evidence["records"])
    with pytest.raises(ValueError, match="expired before result commit"):
        engine.commit_optimization_result(_sat_result(requested["request"], model), lease_id=lease["lease_id"])
    assert len(engine.snapshot.evidence["records"]) == before


def test_superseded_optimization_lease_attempt_is_rejected(monkeypatch):
    engine = _engine_with_sat()
    model = reference_optimization_models()["SAT"]
    engine.admit_optimization_model(model)
    requested = engine.request_optimization(model.model_id, requester_id="agent", required_provider="cadical")
    lease = engine.claim_next_task("worker-cadical", lease_seconds=60)
    actual_list_leases = engine.list_leases
    newer = dict(lease)
    newer["lease_id"] = "lease-newer-attempt"
    newer["attempt"] = int(lease.get("attempt", 1)) + 1
    newer["status"] = "ACTIVE"
    monkeypatch.setattr(engine, "list_leases", lambda: [*actual_list_leases(), newer])
    with pytest.raises(ValueError, match="superseded by a newer attempt"):
        engine.commit_optimization_result(_sat_result(requested["request"], model), lease_id=lease["lease_id"])


def test_completed_lease_allows_only_exact_idempotent_result_replay():
    engine = _engine_with_sat()
    model = reference_optimization_models()["SAT"]
    engine.admit_optimization_model(model)
    requested = engine.request_optimization(model.model_id, requester_id="agent", required_provider="cadical")
    lease = engine.claim_next_task("worker-cadical", lease_seconds=60)
    result = _sat_result(requested["request"], model)
    first = engine.commit_optimization_result(result, lease_id=lease["lease_id"])
    replay = engine.commit_optimization_result(result, lease_id=lease["lease_id"])
    assert replay["already_committed"] is True
    assert replay["result_evidence_id"] == first["result_evidence_id"]
    with pytest.raises(ValueError, match="completed optimization lease cannot commit a new result"):
        engine.commit_optimization_result(
            _sat_result(requested["request"], model, assignment={"x": 1, "y": 1}),
            lease_id=lease["lease_id"],
        )


def test_optimization_result_can_enter_existing_v41_reuse_plane_only_after_policy_admission():
    engine = _engine_with_sat()
    model = reference_optimization_models()["SAT"]
    engine.admit_optimization_model(model)
    requested = engine.request_optimization(model.model_id, requester_id="agent", required_provider="cadical")
    lease = engine.claim_next_task("worker-cadical", lease_seconds=60)
    request = requested["request"]
    committed = engine.commit_optimization_result(_sat_result(request, model), lease_id=lease["lease_id"])
    reuse_request = engine.optimization_reuse_request(request["request_id"])
    assert engine.lookup_reuse(reuse_request)["hit"] is False
    candidate = ReuseCandidate(
        kind=reuse_request.kind,
        request_fingerprint=reuse_request.fingerprint,
        source=engine.canonical_reuse_ref("EVIDENCE", committed["result_evidence_id"]),
        semantic_payload=reuse_request.semantic_payload,
        environment_fingerprint=reuse_request.environment_fingerprint,
        dependency_fingerprints=reuse_request.dependency_fingerprints,
        effect_class=reuse_request.effect_class,
        reusable_modes=("EXACT",),
    )
    engine.register_reuse_candidate(candidate, authority_id="policy", authority_class="POLICY")
    lookup = engine.lookup_reuse(reuse_request)
    assert lookup["hit"] is True
    step = engine.solver_step(SolverStepRequest(scope_id="root"), reuse_request=reuse_request)
    assert step["phase"] == "REUSE"
    assert step["action"] == "SKIP_EXECUTION"
    assert step["reuse_certificate_id"]
