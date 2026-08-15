from __future__ import annotations

import pytest

from aasm.optimization import OptimizationResult, OptimizationSolverIdentity
from aasm.solver_outcome_v2 import normalize_optimization_result_v2
from aasm.solver_provenance import SolverExecutionProfile
from aasm.solver_provenance_v2 import (
    SolverRuntimeProvenanceV2,
    build_solver_runtime_provenance_v2,
    evaluate_solver_execution_profile_v2,
    solver_provenance_v2_contract,
)


def _result() -> OptimizationResult:
    return OptimizationResult(
        "prov2-request",
        "prov2-request-fp",
        "prov2-model-fp",
        "FEASIBLE",
        OptimizationSolverIdentity(
            "provider-a",
            "solver.impl",
            "1.2.3",
            ("solver", "--threads=1", "--seed=7"),
        ),
        assignment={"x": 1.0},
        result_id="prov2-result",
    )


def test_provenance_v2_contract_requires_explicit_adapter_identity():
    contract = solver_provenance_v2_contract()
    assert contract["adapter_identity"] == "EXPLICIT_ADAPTER_ID_AND_VERSION_REQUIRED"
    assert contract["requested_vs_effective_options"] == "SEPARATE"
    assert contract["reproducibility"] == "NOT_CLAIMED_BY_PROVENANCE_ALONE"
    assert contract["truth_authority"] == "NONE"


def test_adapter_bound_strict_profile_passes_and_round_trips():
    result = _result()
    outcome = normalize_optimization_result_v2(result)
    profile = SolverExecutionProfile(
        "strict adapter profile",
        "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"threads": 1, "seed": 7},
        required_effective_options={"threads": 1, "seed": 7},
        provider_id="provider-a",
        provider_version="1.2.3",
        adapter_id="aasm.provider-a",
        adapter_version="0.4.0",
        required_environment_fingerprint="env-1",
    )
    provenance = build_solver_runtime_provenance_v2(
        result,
        outcome,
        profile,
        execution_id="exec-1",
        adapter_id="aasm.provider-a",
        adapter_version="0.4.0",
        effective_options={"threads": 1, "seed": 7, "presolve": True},
        environment_fingerprint="env-1",
        build_fingerprint="build-1",
        provider_status_map_id="status-map-1",
        provider_status_map_fingerprint="status-map-fp-1",
    )
    evaluation = evaluate_solver_execution_profile_v2(profile, provenance)
    assert evaluation.compliant is True
    assert provenance.adapter_id == "aasm.provider-a"
    assert provenance.adapter_version == "0.4.0"
    assert provenance.solver_command == ("solver", "--threads=1", "--seed=7")
    assert SolverRuntimeProvenanceV2.from_dict(provenance.to_dict()).fingerprint == provenance.fingerprint


def test_profile_adapter_mismatch_fails_before_provenance_creation():
    result = _result()
    outcome = normalize_optimization_result_v2(result)
    profile = SolverExecutionProfile(
        "adapter pinned",
        "BEST_EFFORT",
        adapter_id="aasm.expected",
        adapter_version="1",
    )
    with pytest.raises(ValueError, match="adapter_id"):
        build_solver_runtime_provenance_v2(
            result,
            outcome,
            profile,
            execution_id="exec-2",
            adapter_id="aasm.other",
            adapter_version="1",
            effective_options={},
            environment_fingerprint="env",
        )


def test_profile_evaluation_detects_tampered_runtime_adapter_identity():
    result = _result()
    outcome = normalize_optimization_result_v2(result)
    profile = SolverExecutionProfile(
        "adapter pinned",
        "BEST_EFFORT",
        adapter_id="aasm.expected",
        adapter_version="1",
    )
    provenance = build_solver_runtime_provenance_v2(
        result,
        outcome,
        profile,
        execution_id="exec-3",
        adapter_id="aasm.expected",
        adapter_version="1",
        effective_options={},
        environment_fingerprint="env",
    )
    payload = provenance.to_dict()
    payload.pop("fingerprint")
    payload["adapter_id"] = "aasm.tampered"
    tampered = SolverRuntimeProvenanceV2.from_dict(payload)
    evaluation = evaluate_solver_execution_profile_v2(profile, tampered)
    assert evaluation.compliant is False
    deviation = next(row for row in evaluation.deviations if row["code"] == "RUNTIME_IDENTITY_MISMATCH")
    assert deviation["key"] == "adapter_id"


def test_strict_effective_option_override_is_durable_deviation():
    result = _result()
    outcome = normalize_optimization_result_v2(result)
    profile = SolverExecutionProfile(
        "strict",
        "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"threads": 1},
        required_effective_options={"threads": 1},
    )
    provenance = build_solver_runtime_provenance_v2(
        result,
        outcome,
        profile,
        execution_id="exec-4",
        adapter_id="aasm.adapter",
        adapter_version="1",
        effective_options={"threads": 8},
        environment_fingerprint="env",
    )
    evaluation = evaluate_solver_execution_profile_v2(profile, provenance)
    assert evaluation.compliant is False
    assert any(row["code"] == "REQUIRED_EFFECTIVE_OPTION_MISMATCH" for row in evaluation.deviations)
