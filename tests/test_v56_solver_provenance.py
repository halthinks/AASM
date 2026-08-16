from __future__ import annotations

import pytest

from aasm.optimization import OptimizationConstraint, OptimizationModel, OptimizationObjective, OptimizationRequest, OptimizationResult, OptimizationSolverIdentity, OptimizationVariable
from aasm.semantic_result import semantic_fingerprint
from aasm.solver_execution_observation import SolverExecutionObservation, runtime_environment_fingerprint, runtime_platform_identity
from aasm.solver_outcome_v2 import normalize_optimization_result_v2
from aasm.solver_provenance import SolverExecutionProfile, SolverRuntimeProvenance, build_solver_runtime_provenance, evaluate_solver_execution_profile, solver_provenance_contract


def _request() -> OptimizationRequest:
    model = OptimizationModel(
        "prov-model",
        (OptimizationVariable("x", "INTEGER", 0, 10),),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1}, sense=">=", rhs=1),),
        OptimizationObjective("MINIMIZE", {"x": 1}),
        family="CP_SAT",
    )
    return OptimizationRequest(model, "solver.cp_sat", "0.1.0", "prov-obligation", timeout_ms=5000, required_provider="ortools-cp-sat")


def _result(request: OptimizationRequest) -> OptimizationResult:
    return OptimizationResult(
        request.request_id, request.fingerprint, request.model.fingerprint, "OPTIMAL",
        OptimizationSolverIdentity("ortools-cp-sat", "ortools.cp-sat", "9.15.6755", ("ortools.cp-sat",), metadata={}),
        assignment={"x": 1.0}, objective_value=1.0, result_id="prov-result",
        statistics={"raw_status": "OPTIMAL", "raw_status_code": "4"},
    )


def test_provenance_contract_contains_complete_56_2_identity_boundary():
    contract = solver_provenance_contract()
    assert contract["requested_options"] == "RECORDED_SEPARATELY_FROM_EFFECTIVE_OPTIONS"
    assert contract["effective_options"] == "ADAPTER_OBSERVED_ACTUAL_CONFIGURATION_REQUIRED"
    assert contract["adapter_identity"] == "ADAPTER_ID_AND_VERSION_REQUIRED"
    assert contract["platform_identity"] == "REQUIRED"
    assert contract["library_identity"] == "REQUIRED"
    assert contract["worker_thread_counts"] == "FIRST_CLASS_EXPLICIT_OR_UNKNOWN"
    assert contract["formulation_binding"] == "OPTIONAL_EXACT_ID_AND_FINGERPRINT_PAIR"
    assert contract["problem_revision_binding"] == "OPTIONAL_EXACT_ID_AND_FINGERPRINT_PAIR"
    assert contract["reproducibility"] == "NOT_CLAIMED_BY_PROVENANCE_ALONE"
    assert contract["truth_authority"] == "NONE"
    assert contract["policy_authority"] == "NONE"


def test_strict_profile_matches_effective_options_counts_and_exact_identities():
    request = _request(); source = _result(request); outcome = normalize_optimization_result_v2(source, request=request)
    env = runtime_environment_fingerprint()
    profile = SolverExecutionProfile(
        "deterministic cp-sat", "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"max_time_in_seconds": 5.0, "num_search_workers": 1, "random_seed": 0},
        required_effective_options={"num_search_workers": 1, "random_seed": 0},
        provider_id="ortools-cp-sat", provider_version="9.15.6755",
        adapter_id="aasm.optimization.ortools-cp-sat", adapter_version="0.1.0",
        required_environment_fingerprint=env, required_worker_count=1, required_thread_count=1,
    )
    provenance = build_solver_runtime_provenance(
        source, outcome, profile, execution_id="execution-1",
        adapter_id="aasm.optimization.ortools-cp-sat", adapter_version="0.1.0",
        effective_options={"max_time_in_seconds": 5.0, "num_search_workers": 1, "random_seed": 0},
        worker_count=1, thread_count=1, environment_fingerprint=env,
        platform_identity=runtime_platform_identity(), library_identity={"ortools": "9.15.6755"},
        formulation_id="form-1", formulation_fingerprint="f" * 64,
        problem_revision_id="rev-1", problem_revision_fingerprint="r" * 64,
        numeric_policy_id="numeric-1", numeric_policy_fingerprint="n" * 64,
    )
    assert evaluate_solver_execution_profile(profile, provenance).compliant is True
    assert provenance.adapter_id == "aasm.optimization.ortools-cp-sat"
    assert provenance.worker_count == 1 and provenance.thread_count == 1
    assert provenance.formulation_id == "form-1" and provenance.problem_revision_id == "rev-1"
    assert SolverRuntimeProvenance.from_dict(provenance.to_dict()).fingerprint == provenance.fingerprint


def test_strict_profile_detects_provider_override_worker_and_thread_mismatch():
    request = _request(); source = _result(request); outcome = normalize_optimization_result_v2(source, request=request)
    profile = SolverExecutionProfile(
        "strict", "STRICT_EFFECTIVE_OPTIONS",
        required_effective_options={"num_search_workers": 1, "random_seed": 0},
        required_worker_count=1, required_thread_count=1,
    )
    provenance = build_solver_runtime_provenance(
        source, outcome, profile, execution_id="execution-2", adapter_id="adapter", adapter_version="1",
        effective_options={"num_search_workers": 8, "random_seed": 0}, worker_count=2, thread_count=8,
        environment_fingerprint="e" * 64, platform_identity={"os": "test"}, library_identity={"solver": "test"},
    )
    evaluation = evaluate_solver_execution_profile(profile, provenance)
    assert evaluation.compliant is False
    codes = {row["code"] for row in evaluation.deviations}
    assert {"REQUIRED_EFFECTIVE_OPTION_MISMATCH", "WORKER_COUNT_MISMATCH", "THREAD_COUNT_MISMATCH"}.issubset(codes)


def test_profile_exact_adapter_environment_formulation_revision_and_numeric_mismatches_are_visible():
    request = _request(); source = _result(request); outcome = normalize_optimization_result_v2(source, request=request)
    profile = SolverExecutionProfile(
        "bindings", "BEST_EFFORT", adapter_id="adapter-a", adapter_version="1",
        required_environment_fingerprint="a" * 64,
        required_formulation_id="form-a", required_formulation_fingerprint="f" * 64,
        required_problem_revision_id="rev-a", required_problem_revision_fingerprint="r" * 64,
        numeric_policy_id="num-a", numeric_policy_fingerprint="n" * 64,
    )
    with pytest.raises(ValueError, match="adapter_id"):
        build_solver_runtime_provenance(
            source, outcome, profile, execution_id="execution-3", adapter_id="adapter-b", adapter_version="1",
            effective_options={}, worker_count=1, thread_count=1, environment_fingerprint="a" * 64,
            platform_identity={"os": "test"}, library_identity={"solver": "test"},
        )


def test_profile_pairs_fail_closed_instead_of_accepting_unbound_identity():
    with pytest.raises(ValueError, match="provider_id and provider_version"):
        SolverExecutionProfile("bad-provider", "BEST_EFFORT", provider_id="provider-only")
    with pytest.raises(ValueError, match="required_formulation_id and required_formulation_fingerprint"):
        SolverExecutionProfile("bad-formulation", "BEST_EFFORT", required_formulation_id="form-only")
    with pytest.raises(ValueError, match="numeric_policy_id and numeric_policy_fingerprint"):
        SolverExecutionProfile("bad-numeric", "BEST_EFFORT", numeric_policy_id="numeric-only")


def test_runtime_identity_helpers_are_deterministic_and_nonempty():
    first = runtime_platform_identity(); second = runtime_platform_identity()
    assert first == second
    assert first["python_version"] and first["os"] and first["machine"]
    assert runtime_environment_fingerprint() == semantic_fingerprint(first)


def test_execution_observation_requires_real_identity_and_has_no_authority_semantics():
    observation = SolverExecutionObservation(
        "adapter", "1", {"seed": 0}, {"seed": 0}, 1, 1,
        "e" * 64, {"os": "test"}, {"solver": "1"}, metadata={"authority": "NONE"},
    )
    assert observation.to_dict()["contract_id"] == "aasm.solver.execution-observation.internal.v1"
    assert observation.fingerprint
