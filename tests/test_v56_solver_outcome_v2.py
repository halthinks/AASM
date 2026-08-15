from __future__ import annotations

import pytest

from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationRequest,
    OptimizationResult,
    OptimizationSolverIdentity,
    OptimizationVariable,
)
from aasm.solver_outcome_v2 import (
    LegacyStatusProjection,
    ProviderTermination,
    SolverEvidenceGrade,
    SolverOutcomeV2,
    normalize_optimization_result_v2,
    project_v2_to_legacy_status,
    solver_outcome_v2_contract,
)


def _request(*, objective=True) -> OptimizationRequest:
    model = OptimizationModel(
        "status-v2-fixture",
        (OptimizationVariable("x", "INTEGER", 0, 10),),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1}, sense=">=", rhs=1),),
        OptimizationObjective("MINIMIZE", {"x": 1}) if objective else None,
        family="CP_SAT",
    )
    return OptimizationRequest(model, "solver.cp_sat", "0.1.0", "status-v2-obligation", required_provider="ortools-cp-sat")


def _result(request: OptimizationRequest, status: str, *, assignment=None, objective_value=None, best_bound=None, relative_gap=None, raw_status="", raw_code="") -> OptimizationResult:
    return OptimizationResult(
        request.request_id,
        request.fingerprint,
        request.model.fingerprint,
        status,
        OptimizationSolverIdentity("ortools-cp-sat", "ortools.cp-sat", "9.15.6755"),
        assignment=assignment or {},
        objective_value=objective_value,
        best_bound=best_bound,
        relative_gap=relative_gap,
        wall_time_ms=1234,
        statistics={"raw_status": raw_status or status, "raw_status_code": raw_code},
        diagnostics=("provider diagnostic",),
        result_id=f"result-{status.lower()}-{bool(assignment)}",
    )


def test_contract_makes_v2_authoritative_and_v1_projection_one_way():
    contract = solver_outcome_v2_contract()
    assert contract["authoritative_detailed_status"] == "normalized_status"
    assert contract["legacy_projection"] == "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED"
    assert contract["incumbent_admission"] == "NONEMPTY_ASSIGNMENT_MUST_PASS_AASM_INDEPENDENT_MODEL_VALIDATION"
    assert contract["model_invalid"] == "DISTINCT_FROM_INFEASIBLE"
    assert contract["numerical_failure"] == "DISTINCT_FROM_UNKNOWN"


def test_time_limit_with_validated_incumbent_preserves_bound_gap_and_projects_lossily():
    request = _request()
    source = _result(request, "TIMEOUT", assignment={"x": 2.0}, objective_value=2.0, best_bound=1.0, relative_gap=0.5)
    outcome = normalize_optimization_result_v2(source, request=request)
    assert outcome.normalized_status == "TIME_LIMIT_WITH_INCUMBENT"
    assert outcome.incumbent_validation == "VALIDATED"
    assert outcome.objective_value == 2.0 and outcome.best_bound == 1.0 and outcome.relative_gap == 0.5
    assert outcome.legacy_projection.status == "TIMEOUT" and outcome.legacy_projection.lossy is True


def test_time_limit_without_incumbent_is_explicit_no_solution():
    request = _request()
    outcome = normalize_optimization_result_v2(_result(request, "TIMEOUT"), request=request)
    assert outcome.normalized_status == "TIME_LIMIT_NO_SOLUTION"
    assert outcome.incumbent_status == "ABSENT"
    assert outcome.incumbent_validation == "NOT_PRESENT"


def test_optimal_requires_validated_incumbent_and_provider_completed_termination():
    request = _request()
    source = _result(request, "OPTIMAL", assignment={"x": 1.0}, objective_value=1.0)
    outcome = normalize_optimization_result_v2(source, request=request)
    assert outcome.normalized_status == "OPTIMAL"
    assert outcome.optimality_claim == "CLAIMED_OPTIMAL"
    assert outcome.has_proven_optimality is False
    with pytest.raises(ValueError, match="provider optimal completion"):
        normalize_optimization_result_v2(source, request=request, termination=ProviderTermination("TIME_LIMIT"), normalized_status="OPTIMAL")


def test_invalid_incumbent_is_rejected_before_with_incumbent_status_can_exist():
    request = _request()
    source = _result(request, "FEASIBLE", assignment={"x": 0.0}, objective_value=0.0)
    with pytest.raises(ValueError, match="violates"):
        normalize_optimization_result_v2(source, request=request)


def test_inconsistent_objective_is_rejected_by_independent_checker():
    request = _request()
    source = _result(request, "FEASIBLE", assignment={"x": 2.0}, objective_value=9.0)
    with pytest.raises(ValueError, match="objective"):
        normalize_optimization_result_v2(source, request=request)


def test_incumbent_without_exact_request_fails_closed():
    request = _request()
    source = _result(request, "FEASIBLE", assignment={"x": 2.0}, objective_value=2.0)
    with pytest.raises(ValueError, match="exact OptimizationRequest"):
        normalize_optimization_result_v2(source)


def test_model_invalid_and_numerical_failure_never_collapse_to_infeasible_or_unknown():
    request = _request()
    invalid = normalize_optimization_result_v2(
        _result(request, "ERROR"), request=request,
        termination=ProviderTermination("MODEL_INVALID", raw_status="MODEL_INVALID", raw_status_code="1"),
        normalized_status="MODEL_INVALID",
    )
    numerical = normalize_optimization_result_v2(
        _result(request, "ERROR"), request=request,
        termination=ProviderTermination("NUMERICAL_FAILURE", raw_status="NUMERICAL_FAILURE"),
        normalized_status="NUMERICAL_FAILURE",
    )
    assert invalid.normalized_status == "MODEL_INVALID" and invalid.legacy_projection.status == "ERROR"
    assert numerical.normalized_status == "NUMERICAL_FAILURE" and numerical.legacy_projection.status == "ERROR"


def test_stale_result_is_first_class_fail_closed_status():
    request = _request()
    outcome = normalize_optimization_result_v2(
        _result(request, "UNKNOWN"), request=request,
        termination=ProviderTermination("STALE_RESULT", raw_status="STALE"),
        normalized_status="STALE_RESULT",
    )
    assert outcome.normalized_status == "STALE_RESULT"
    assert outcome.legacy_projection.status == "UNKNOWN"


@pytest.mark.parametrize(
    ("termination_reason", "normalized_status", "legacy_status"),
    (
        ("NODE_LIMIT", "NODE_LIMIT_NO_SOLUTION", "UNKNOWN"),
        ("MEMORY_LIMIT", "MEMORY_LIMIT_NO_SOLUTION", "UNKNOWN"),
        ("USER_INTERRUPT", "USER_INTERRUPT_NO_SOLUTION", "UNKNOWN"),
        ("PROVIDER_UNAVAILABLE", "PROVIDER_UNAVAILABLE", "ERROR"),
        ("UNSUPPORTED_FEATURE", "UNSUPPORTED_FEATURE", "ERROR"),
    ),
)
def test_all_roadmap_mandated_terminal_classes_are_first_class(termination_reason: str, normalized_status: str, legacy_status: str):
    request = _request()
    outcome = normalize_optimization_result_v2(
        _result(request, "UNKNOWN" if termination_reason in {"NODE_LIMIT", "MEMORY_LIMIT", "USER_INTERRUPT"} else "ERROR"),
        request=request,
        termination=ProviderTermination(termination_reason, raw_status=termination_reason),
        normalized_status=normalized_status,
    )
    assert outcome.normalized_status == normalized_status
    assert outcome.termination.reason == termination_reason
    assert outcome.incumbent_status == "ABSENT"
    assert outcome.legacy_projection.status == legacy_status
    assert outcome.legacy_projection.lossy is True


def test_node_and_memory_limit_with_incumbent_require_independent_validation():
    request = _request()
    for reason, status in (("NODE_LIMIT", "NODE_LIMIT_WITH_INCUMBENT"), ("MEMORY_LIMIT", "MEMORY_LIMIT_WITH_INCUMBENT")):
        source = _result(request, "FEASIBLE", assignment={"x": 2.0}, objective_value=2.0, best_bound=1.0)
        outcome = normalize_optimization_result_v2(
            source,
            request=request,
            termination=ProviderTermination(reason, raw_status=reason),
            normalized_status=status,
        )
        assert outcome.normalized_status == status
        assert outcome.incumbent_validation == "VALIDATED"
        assert outcome.best_bound == 1.0


def test_checked_certificate_is_stronger_than_provider_optimality_claim():
    request = _request()
    evidence = SolverEvidenceGrade(
        "CHECKED_CERTIFICATE", "CHECKED_CERTIFICATE",
        certificate_ids=("cert-1",), checker_ids=("checker-1",),
    )
    source = _result(request, "OPTIMAL", assignment={"x": 1.0}, objective_value=1.0)
    outcome = normalize_optimization_result_v2(source, request=request, evidence=evidence)
    assert outcome.has_proven_optimality is True
    assert SolverOutcomeV2.from_dict(outcome.to_dict()).fingerprint == outcome.fingerprint


def test_v2_to_v1_projection_examples_are_explicitly_lossy():
    assert project_v2_to_legacy_status("FEASIBLE_NOT_PROVEN_OPTIMAL") == LegacyStatusProjection("FEASIBLE", True, "v1 cannot preserve explicit not-proven-optimal semantics")
    assert project_v2_to_legacy_status("TIME_LIMIT_WITH_INCUMBENT").status == "TIMEOUT"
    assert project_v2_to_legacy_status("NUMERICAL_FAILURE").status == "ERROR"
    assert project_v2_to_legacy_status("UNBOUNDED").status == "UNKNOWN"


def test_no_solution_status_rejects_assignment_even_if_caller_tries_to_force_it():
    request = _request()
    source = _result(request, "UNKNOWN", assignment={"x": 2.0}, objective_value=2.0)
    with pytest.raises(ValueError, match="forbids an incumbent"):
        normalize_optimization_result_v2(source, request=request, normalized_status="TIME_LIMIT_NO_SOLUTION")
