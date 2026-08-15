from __future__ import annotations

from aasm.optimization import OptimizationResult, OptimizationSolverIdentity
from aasm.reproducibility import (
    ReproducibilityRun,
    compare_reproducibility_runs,
    reproducibility_contract,
)
from aasm.solver_outcome_v2 import normalize_optimization_result_v2
from aasm.solver_provenance import SolverExecutionProfile
from aasm.solver_provenance_v2 import (
    build_solver_runtime_provenance_v2,
    evaluate_solver_execution_profile_v2,
)


def _run(tag: str, *, assignment=None, objective=5.0, threads=1, semantic="semantic-fp", proof="proof-fp", artifact="artifact-fp", compliant=True):
    result = OptimizationResult(
        f"request-{tag}",
        f"request-fp-{tag}",
        "same-model-fp",
        "FEASIBLE",
        OptimizationSolverIdentity("provider", "solver.impl", "1", ("solver", "--seed=1", "--threads=1")),
        assignment=assignment or {"x": 1.0},
        objective_value=objective,
        result_id=f"result-{tag}",
    )
    outcome = normalize_optimization_result_v2(result)
    profile = SolverExecutionProfile(
        "strict reproducibility",
        "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"seed": 1, "threads": 1},
        required_effective_options={"seed": 1, "threads": 1},
        provider_id="provider",
        provider_version="1",
        adapter_id="adapter",
        adapter_version="1",
        required_environment_fingerprint="env",
    )
    provenance = build_solver_runtime_provenance_v2(
        result,
        outcome,
        profile,
        execution_id=f"execution-{tag}",
        adapter_id="adapter",
        adapter_version="1",
        effective_options={"seed": 1, "threads": threads},
        environment_fingerprint="env",
        build_fingerprint="build",
    )
    evaluation = evaluate_solver_execution_profile_v2(profile, provenance)
    if not compliant:
        assert evaluation.compliant is False
    return ReproducibilityRun(
        result,
        outcome,
        provenance,
        evaluation,
        semantic_projection_fingerprint=semantic,
        proof_fingerprint=proof,
        artifact_fingerprint=artifact,
    )


def test_reproducibility_contract_is_graded_and_non_authoritative():
    contract = reproducibility_contract()
    assert contract["profile_requirement"] == "BOTH_RUNS_COMPLIANT_FOR_ANY_POSITIVE_REPRODUCIBILITY_CLAIM"
    assert contract["proof_equivalence"] == "EXPLICIT_PROOF_FINGERPRINT_ONLY"
    assert contract["artifact_equivalence"] == "EXPLICIT_ARTIFACT_FINGERPRINT_ONLY"
    assert contract["agreement_grants_truth"] is False
    assert contract["truth_authority"] == "NONE"


def test_identical_compliant_runs_reach_artifact_reproduced():
    left = _run("a")
    right = _run("b")
    certificate = compare_reproducibility_runs(left, right)
    assert certificate.claim_level == "ARTIFACT_REPRODUCED"
    assert certificate.configuration_same is True
    assert certificate.both_profile_compliant is True
    assert certificate.semantic_projection_same is True
    assert certificate.assignment_same is True
    assert certificate.objective_same is True
    assert certificate.proof_same is True
    assert certificate.artifact_same is True


def test_matching_result_under_profile_violation_gets_no_positive_claim():
    left = _run("a")
    right = _run("b", threads=8, compliant=False)
    certificate = compare_reproducibility_runs(left, right)
    assert certificate.assignment_same is True
    assert certificate.objective_same is True
    assert certificate.claim_level == "NO_REPRODUCIBILITY_CLAIM"
    assert "PROFILE_NONCOMPLIANT" in certificate.diagnostics
    assert "CONFIGURATION_FINGERPRINT_DIFFERS" in certificate.diagnostics


def test_semantic_projection_difference_caps_claim_at_configuration():
    left = _run("a", semantic="sem-a")
    right = _run("b", semantic="sem-b")
    certificate = compare_reproducibility_runs(left, right)
    assert certificate.claim_level == "CONFIGURATION_REPLAYABLE"
    assert certificate.semantic_projection_same is False
    assert "SEMANTIC_PROJECTION_DIFFERS" in certificate.diagnostics


def test_absent_semantic_projection_can_fall_back_to_exact_assignment():
    left = _run("a", semantic="", proof="", artifact="")
    right = _run("b", semantic="", proof="", artifact="")
    certificate = compare_reproducibility_runs(left, right)
    assert certificate.semantic_projection_same is None
    assert certificate.assignment_same is True
    assert certificate.claim_level == "OBJECTIVE_REPRODUCED"


def test_assignment_difference_caps_claim_below_semantic_when_no_semantic_projection():
    left = _run("a", assignment={"x": 1.0}, semantic="", proof="", artifact="")
    right = _run("b", assignment={"x": 0.0}, semantic="", proof="", artifact="")
    certificate = compare_reproducibility_runs(left, right)
    assert certificate.claim_level == "CONFIGURATION_REPLAYABLE"
    assert certificate.assignment_same is False


def test_proof_difference_never_gets_proof_or_artifact_claim():
    left = _run("a", proof="proof-a")
    right = _run("b", proof="proof-b")
    certificate = compare_reproducibility_runs(left, right)
    assert certificate.claim_level == "OBJECTIVE_REPRODUCED"
    assert certificate.proof_same is False
    assert "PROOF_DIFFERS_OR_MISSING_PEER" in certificate.diagnostics
