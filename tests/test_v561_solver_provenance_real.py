from __future__ import annotations

import os
import pytest

from aasm.convex_optimization import ConvexOptimizationRequest, reference_convex_models, solve_convex_request, validate_convex_result
from aasm.optimization import OptimizationRequest, reference_optimization_models, solve_optimization_request, validate_optimization_result
from aasm.solver_execution_observation import execution_observation_for_convex, execution_observation_for_optimization
from aasm.solver_outcome_v2 import normalize_optimization_result_v2
from aasm.solver_provenance import SolverExecutionProfile, SolverRuntimeProvenance, build_solver_runtime_provenance, evaluate_solver_execution_profile

pytestmark = pytest.mark.skipif(
    os.environ.get("AASM_REQUIRE_V561_PROVIDERS") != "1",
    reason="real v0.56.1 provenance providers are exercised by the dedicated provenance gate",
)


def _provenance_from_native(request, result):
    validate_optimization_result(request, result)
    outcome = normalize_optimization_result_v2(result, request=request)
    observation = execution_observation_for_optimization(request, result)
    profile = SolverExecutionProfile(
        f"real-{result.solver.provider_id}",
        "STRICT_EFFECTIVE_OPTIONS" if result.solver.provider_id == "ortools-cp-sat" else "REPRODUCIBLE_REQUESTED",
        requested_options=observation.requested_options,
        required_effective_options=observation.effective_options if result.solver.provider_id == "ortools-cp-sat" else {},
        provider_id=result.solver.provider_id,
        provider_version=result.solver.version,
        adapter_id=observation.adapter_id,
        adapter_version=observation.adapter_version,
        required_worker_count=observation.worker_count,
        required_thread_count=observation.thread_count,
    )
    provenance = build_solver_runtime_provenance(
        result, outcome, profile, execution_id=f"real-{result.solver.provider_id}",
        adapter_id=observation.adapter_id, adapter_version=observation.adapter_version,
        effective_options=observation.effective_options, worker_count=observation.worker_count, thread_count=observation.thread_count,
        environment_fingerprint=observation.environment_fingerprint,
        platform_identity=observation.platform_identity, library_identity=observation.library_identity,
        build_fingerprint=observation.build_fingerprint,
        formulation_id=observation.formulation_id, formulation_fingerprint=observation.formulation_fingerprint,
        problem_revision_id=observation.problem_revision_id, problem_revision_fingerprint=observation.problem_revision_fingerprint,
        numeric_policy_id=observation.numeric_policy_id, numeric_policy_fingerprint=observation.numeric_policy_fingerprint,
        metadata=observation.metadata,
    )
    return profile, provenance, observation


@pytest.mark.parametrize("family,provider,capability", [
    ("SAT", "cadical", "solver.sat"),
    ("CP_SAT", "ortools-cp-sat", "solver.cp_sat"),
    ("MILP", "highs", "solver.milp"),
])
def test_real_native_provider_provenance_is_observed_and_profile_checked(family: str, provider: str, capability: str):
    model = reference_optimization_models()[family]
    request = OptimizationRequest(model, capability, "0.1.0", f"real-prov-{family.lower()}", required_provider=provider)
    result = solve_optimization_request(request)
    profile, provenance, observation = _provenance_from_native(request, result)
    evaluation = evaluate_solver_execution_profile(profile, provenance)
    assert evaluation.compliant is True, evaluation.to_dict()
    assert provenance.provider_id == provider
    assert provenance.adapter_id == observation.adapter_id
    assert provenance.effective_options == observation.effective_options
    assert provenance.platform_identity and provenance.library_identity
    assert provenance.environment_fingerprint == observation.environment_fingerprint
    if provider == "ortools-cp-sat":
        assert provenance.thread_count == 1
        assert provenance.effective_options["num_search_workers"] == 1
        assert provenance.effective_options["random_seed"] == 0
    if provider == "highs":
        assert provenance.thread_count is None
        assert provenance.metadata["thread_count_observation"] == "UNAVAILABLE_FROM_CURRENT_ADAPTER"


def test_real_cvxpy_backend_provenance_captures_selected_backend_without_fabricated_threads():
    model = reference_convex_models()["QP"]
    request = ConvexOptimizationRequest(model, "solver.convex", "0.1.0", "real-cvxpy-prov")
    result = solve_convex_request(request)
    validate_convex_result(request, result)
    if result.status != "OPTIMAL":
        pytest.skip(f"qualified CVXPY backend did not produce OPTIMAL result: {result.status} {result.diagnostics}")
    observation = execution_observation_for_convex(request, result)
    profile = SolverExecutionProfile(
        "real-cvxpy", "REPRODUCIBLE_REQUESTED",
        requested_options=observation.requested_options,
        provider_id="cvxpy", provider_version=result.solver.version,
        adapter_id=observation.adapter_id, adapter_version=observation.adapter_version,
        required_worker_count=1,
    )
    provenance = SolverRuntimeProvenance(
        execution_id="real-cvxpy", source_result_id=result.result_id, source_result_fingerprint=result.fingerprint,
        source_outcome_id="", source_outcome_fingerprint="", profile_id=profile.profile_id, profile_fingerprint=profile.fingerprint,
        model_fingerprint=result.model_fingerprint, provider_id=result.solver.provider_id,
        provider_implementation=result.solver.implementation, provider_version=result.solver.version,
        adapter_id=observation.adapter_id, adapter_version=observation.adapter_version,
        solver_command=(result.solver.implementation, result.solver.backend_solver), requested_options=profile.requested_options,
        effective_options=observation.effective_options, worker_count=observation.worker_count, thread_count=observation.thread_count,
        environment_fingerprint=observation.environment_fingerprint, platform_identity=observation.platform_identity,
        library_identity=observation.library_identity, build_fingerprint=observation.build_fingerprint, metadata=observation.metadata,
    )
    evaluation = evaluate_solver_execution_profile(profile, provenance)
    assert evaluation.compliant is True, evaluation.to_dict()
    assert provenance.provider_id == "cvxpy"
    assert provenance.effective_options["solver"] == result.solver.backend_solver
    assert provenance.thread_count is None
    assert provenance.metadata["thread_count_observation"] == "BACKEND_SPECIFIC_NOT_EXPOSED_BY_CURRENT_CVXPY_ADAPTER"
