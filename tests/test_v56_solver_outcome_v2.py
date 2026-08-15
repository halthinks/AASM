from __future__ import annotations

import pytest

from aasm.optimization import OptimizationResult, OptimizationSolverIdentity
from aasm.solver_outcome_v2 import (
    ProviderTermination,
    SolverEvidenceGrade,
    SolverOutcomeV2,
    normalize_optimization_result_v2,
    solver_outcome_v2_contract,
)


def _result(status: str, *, assignment=None, objective_value=None, best_bound=None, relative_gap=None) -> OptimizationResult:
    return OptimizationResult(
        "request-1",
        "request-fingerprint-1",
        "model-fingerprint-1",
        status,
        OptimizationSolverIdentity("provider-1", "solver.impl", "1.2.3", ("solver", "--flag")),
        assignment=assignment or {},
        objective_value=objective_value,
        best_bound=best_bound,
        relative_gap=relative_gap,
        wall_time_ms=1234,
        statistics={"nodes": 99},
        diagnostics=("provider diagnostic",),
        metadata={"provider_payload_hash": "abc"},
        result_id=f"result-{status.lower()}",
    )


def test_status_v2_contract_separates_axes_and_preserves_legacy_result():
    contract = solver_outcome_v2_contract()
    assert contract["legacy_result"] == "PRESERVED_AND_FINGERPRINT_BOUND"
    assert contract["timeout_with_incumbent"] == "FEASIBLE_INCUMBENT_PRESERVED_SEPARATELY_FROM_TIME_LIMIT"
    assert contract["provider_optimal_status"] == "CLAIMED_OPTIMAL_NOT_PROVEN_OPTIMAL_WITHOUT_CHECKED_CERTIFICATE"
    assert contract["raw_provider_status"] == "PRESERVED_VERBATIM_IN_TERMINATION_RECORD"
    assert contract["truth_authority"] == "NONE"


def test_timeout_with_incumbent_remains_feasible_and_preserves_bound_gap():
    source = _result("TIMEOUT", assignment={"x": 1.0}, objective_value=10.0, best_bound=8.0, relative_gap=0.2)
    outcome = normalize_optimization_result_v2(source)
    assert outcome.termination.reason == "TIME_LIMIT"
    assert outcome.solution_status == "FEASIBLE"
    assert outcome.incumbent_status == "PRESENT"
    assert outcome.optimality_claim == "NOT_CLAIMED"
    assert outcome.objective_value == 10.0
    assert outcome.best_bound == 8.0
    assert outcome.relative_gap == 0.2
    assert outcome.source_result_fingerprint == source.fingerprint
    assert outcome.evidence.grade == "PROVIDER_ASSERTED"
    assert outcome.has_proven_optimality is False


def test_timeout_without_incumbent_is_unknown_not_infeasible():
    outcome = normalize_optimization_result_v2(_result("TIMEOUT"))
    assert outcome.termination.reason == "TIME_LIMIT"
    assert outcome.solution_status == "UNKNOWN"
    assert outcome.incumbent_status == "ABSENT"
    assert outcome.optimality_claim == "UNKNOWN"


def test_provider_optimal_is_claim_not_proof_by_default():
    outcome = normalize_optimization_result_v2(_result("OPTIMAL", assignment={"x": 1.0}, objective_value=4.0))
    assert outcome.solution_status == "FEASIBLE"
    assert outcome.optimality_claim == "CLAIMED_OPTIMAL"
    assert outcome.evidence.proof_status == "NO_CERTIFICATE"
    assert outcome.evidence.grade == "PROVIDER_ASSERTED"
    assert outcome.has_proven_optimality is False


def test_checked_certificate_can_promote_optimality_claim_to_proven_without_changing_provider_status():
    evidence = SolverEvidenceGrade(
        "CHECKED_CERTIFICATE",
        "CHECKED_CERTIFICATE",
        certificate_ids=("cert-1",),
        checker_ids=("checker-1",),
        validation_evidence_ids=("evidence-check-1",),
    )
    source = _result("OPTIMAL", assignment={"x": 1.0}, objective_value=4.0)
    outcome = normalize_optimization_result_v2(source, evidence=evidence)
    assert outcome.legacy_status == "OPTIMAL"
    assert outcome.has_proven_optimality is True
    assert outcome.evidence.certificate_ids == ("cert-1",)
    assert SolverOutcomeV2.from_dict(outcome.to_dict()).fingerprint == outcome.fingerprint


def test_infeasible_provider_status_is_not_decisive_negative_without_checked_certificate():
    outcome = normalize_optimization_result_v2(_result("INFEASIBLE"))
    assert outcome.solution_status == "INFEASIBLE"
    assert outcome.incumbent_status == "ABSENT"
    assert outcome.has_decisive_negative_proof is False

    checked = SolverEvidenceGrade(
        "CHECKED_CERTIFICATE",
        "CHECKED_CERTIFICATE",
        certificate_ids=("infeasible-cert",),
        checker_ids=("independent-checker",),
    )
    proven = normalize_optimization_result_v2(_result("INFEASIBLE"), evidence=checked)
    assert proven.has_decisive_negative_proof is True


def test_raw_provider_node_limit_is_preserved_independently_from_incumbent():
    termination = ProviderTermination(
        "NODE_LIMIT",
        raw_status="kHighsModelStatusSolutionLimit",
        raw_status_code="17",
        raw_message="node cap reached",
        limit_value=1000,
        limit_unit="nodes",
        metadata={"provider": "highs"},
    )
    outcome = normalize_optimization_result_v2(
        _result("FEASIBLE", assignment={"x": 1.0}),
        termination=termination,
    )
    assert outcome.termination.reason == "NODE_LIMIT"
    assert outcome.termination.raw_status == "kHighsModelStatusSolutionLimit"
    assert outcome.termination.raw_status_code == "17"
    assert outcome.termination.limit_value == 1000.0
    assert outcome.solution_status == "FEASIBLE"
    assert outcome.incumbent_status == "PRESENT"


def test_independent_validation_is_not_misreported_as_certificate_proof():
    evidence = SolverEvidenceGrade(
        "INDEPENDENTLY_VALIDATED",
        "NO_CERTIFICATE",
        validation_evidence_ids=("validation-evidence",),
    )
    outcome = normalize_optimization_result_v2(_result("FEASIBLE", assignment={"x": 1.0}), evidence=evidence)
    assert outcome.evidence.grade == "INDEPENDENTLY_VALIDATED"
    assert outcome.evidence.proof_status == "NO_CERTIFICATE"
    assert outcome.has_proven_optimality is False


def test_checked_evidence_grade_requires_certificate_and_checker():
    with pytest.raises(ValueError, match="certificate"):
        SolverEvidenceGrade("CHECKED_CERTIFICATE", "CHECKED_CERTIFICATE")
    with pytest.raises(ValueError, match="validation Evidence"):
        SolverEvidenceGrade("INDEPENDENTLY_VALIDATED", "NO_CERTIFICATE")


def test_legacy_feasible_or_optimal_without_assignment_fails_closed():
    with pytest.raises(ValueError, match="requires assignment"):
        normalize_optimization_result_v2(_result("OPTIMAL"))
    with pytest.raises(ValueError, match="requires assignment"):
        normalize_optimization_result_v2(_result("FEASIBLE"))
