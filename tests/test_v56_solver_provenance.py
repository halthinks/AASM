from __future__ import annotations

import pytest

from aasm.optimization import OptimizationResult, OptimizationSolverIdentity
from aasm.solver_outcome_v2 import normalize_optimization_result_v2
from aasm.solver_provenance import (
    SolverExecutionProfile,
    build_solver_runtime_provenance,
    evaluate_solver_execution_profile,
    solver_provenance_contract,
)


def _result() -> OptimizationResult:
    return OptimizationResult(
        "prov-request",
        "prov-request-fp",
        "prov-model-fp",
        "FEASIBLE",
        OptimizationSolverIdentity(
            "provider-a",
            "solver.impl",
            "1.2.3",
            ("solver", "--threads=1", "--seed=7"),
        ),
        assignment={"x": 1.0},
        result_id="prov-result",
    )


def test_provenance_contract_separates_requested_and_effective_configuration():
    contract = solver_provenance_contract()
    assert contract["requested_options"] == "RECORDED_SEPARATELY_FROM_EFFECTIVE_OPTIONS"
    assert contract["effective_options"] == "ADAPTER_OBSERVED_ACTUAL_CONFIGURATION_REQUIRED"
    assert contract["solver_command"] == "EXACT_COMMAND_IDENTITY_PRESERVED"
    assert contract["environment"] == "FINGERPRINT_BOUND"
    assert contract["reproducibility"] == "NOT_CLAIMED_BY_PROVENANCE_ALONE"
    assert contract["truth_authority"] == "NONE"


def test_strict_profile_passes_when_effective_seed_threads_and_environment_match():
    source = _result()
    outcome = normalize_optimization_result_v2(source)
    profile = SolverExecutionProfile(
        "deterministic single-thread",
        "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"threads": 1, "seed": 7},
        required_effective_options={"threads": 1, "seed": 7},
        provider_id="provider-a",
        provider_version="1.2.3",
        required_environment_fingerprint="env-abc",
    )
    provenance = build_solver_runtime_provenance(
        source,
        outcome,
        profile,
        execution_id="execution-1",
        effective_options={"threads": 1, "seed": 7, "presolve": True},
        environment_fingerprint="env-abc",
        build_fingerprint="build-123",
        dependency_fingerprints=("dep-b", "dep-a", "dep-a"),
    )
    evaluation = evaluate_solver_execution_profile(profile, provenance)
    assert evaluation.compliant is True
    assert evaluation.deviations == ()
    assert provenance.solver_command == ("solver", "--threads=1", "--seed=7")
    assert provenance.requested_options == {"seed": 7, "threads": 1}
    assert provenance.effective_options["presolve"] is True
    assert provenance.dependency_fingerprints == ("dep-a", "dep-b")


def test_strict_profile_records_provider_override_instead_of_hiding_it():
    source = _result()
    outcome = normalize_optimization_result_v2(source)
    profile = SolverExecutionProfile(
        "strict",
        "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"threads": 1, "seed": 7},
        required_effective_options={"threads": 1, "seed": 7},
    )
    provenance = build_solver_runtime_provenance(
        source,
        outcome,
        profile,
        execution_id="execution-2",
        effective_options={"threads": 8, "seed": 7},
        environment_fingerprint="env",
    )
    evaluation = evaluate_solver_execution_profile(profile, provenance)
    assert evaluation.compliant is False
    deviation = next(row for row in evaluation.deviations if row["code"] == "REQUIRED_EFFECTIVE_OPTION_MISMATCH")
    assert deviation["key"] == "threads"
    assert deviation["expected"] == 1
    assert deviation["actual"] == 8


def test_required_environment_mismatch_fails_before_provenance_is_built():
    source = _result()
    outcome = normalize_optimization_result_v2(source)
    profile = SolverExecutionProfile(
        "env-pinned",
        "REPRODUCIBLE_REQUESTED",
        requested_options={"seed": 7},
        required_environment_fingerprint="env-a",
    )
    with pytest.raises(ValueError, match="environment fingerprint mismatch"):
        build_solver_runtime_provenance(
            source,
            outcome,
            profile,
            execution_id="execution-3",
            effective_options={"seed": 7},
            environment_fingerprint="env-b",
        )


def test_profile_provider_identity_must_match_exact_result_provider():
    source = _result()
    outcome = normalize_optimization_result_v2(source)
    profile = SolverExecutionProfile(
        "wrong provider",
        "BEST_EFFORT",
        provider_id="other-provider",
    )
    with pytest.raises(ValueError, match="provider_id"):
        build_solver_runtime_provenance(
            source,
            outcome,
            profile,
            execution_id="execution-4",
            effective_options={},
            environment_fingerprint="env",
        )


def test_outcome_must_bind_exact_result_before_provenance_can_be_built():
    source = _result()
    other = OptimizationResult(
        "other-request",
        "other-request-fp",
        "other-model-fp",
        "FEASIBLE",
        source.solver,
        assignment={"x": 1.0},
        result_id="other-result",
    )
    other_outcome = normalize_optimization_result_v2(other)
    profile = SolverExecutionProfile("basic", "BEST_EFFORT")
    with pytest.raises(ValueError, match="exact source result"):
        build_solver_runtime_provenance(
            source,
            other_outcome,
            profile,
            execution_id="execution-5",
            effective_options={},
            environment_fingerprint="env",
        )


def test_strict_profile_requires_declared_effective_options():
    with pytest.raises(ValueError, match="required_effective_options"):
        SolverExecutionProfile("bad strict", "STRICT_EFFECTIVE_OPTIONS")
