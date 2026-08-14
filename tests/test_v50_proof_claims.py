from __future__ import annotations

import pytest

from aasm.model import ProblemSpec
from aasm.optimization import (
    BooleanLiteral,
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationResult,
    OptimizationSolverIdentity,
    OptimizationVariable,
)
from aasm.proof_claim_conformance import run_solver_proof_conformance
from aasm.proof_claims import (
    SolverClaimCertificate,
    build_finite_domain_proof,
    certify_optimization_result,
    solver_proof_contract,
    verify_finite_domain_proof,
)
from aasm.runtime_v50 import AASMEngine


def solver():
    return OptimizationSolverIdentity("fixture-solver", "fixture", "1.0.0")


def result(model, status, assignment=None, objective=None):
    return OptimizationResult("req", "req-fp", model.fingerprint, status, solver(), assignment or {}, objective)


def unsat_model():
    return OptimizationModel(
        "unsat",
        (OptimizationVariable("x", "BOOL"),),
        (
            OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x", True),)),
            OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x", False),)),
        ),
        family="SAT",
    )


def optimal_model():
    return OptimizationModel(
        "optimal",
        (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1}, sense=">=", rhs=1),),
        OptimizationObjective("MINIMIZE", {"x": 1, "y": 1}),
        family="CP_SAT",
    )


def test_contract_never_equates_solver_status_with_proof_grade():
    contract = solver_proof_contract()
    assert contract["solver_status_is_proof_grade"] is False
    assert contract["proof_certified_requires_independent_checker"] is True
    assert contract["certificate_authority"] == "EVIDENCE_ONLY"
    assert contract["truth_authority"] == "EXISTING_AASM_POLICY_ONLY"


def test_unsat_is_independently_certified_by_exhaustion():
    model = unsat_model()
    report = certify_optimization_result(model, result(model, "UNSAT"))
    assert report["status"] == "PASS"
    assert report["verification_level"] == "PROOF_CERTIFIED"
    assert report["proof_artifact"]["payload"]["feasible_count"] == 0
    assert report["certificate"]["independent_of_solver"] is True
    assert report["certificate"]["coverage"]["exact_exhaustion"] is True


def test_global_optimality_is_certified_not_just_solver_asserted():
    model = optimal_model()
    report = certify_optimization_result(model, result(model, "OPTIMAL", {"x": 0, "y": 1}, 1.0))
    assert report["status"] == "PASS"
    assert report["proof_artifact"]["payload"]["conclusion"] == "GLOBAL_OPTIMUM"
    assert report["proof_artifact"]["payload"]["optimum"] == 1.0


def test_false_optimality_fails_and_never_promotes():
    model = optimal_model()
    report = certify_optimization_result(model, result(model, "OPTIMAL", {"x": 0, "y": 0}, 0.0))
    assert report["status"] == "FAIL"
    assert report["verification_level"] == "SOLVER_VALIDATED"
    assert report["certificate"] is None


def test_positive_claim_without_proof_checker_stays_solver_validated():
    model = OptimizationModel(
        "sat",
        (OptimizationVariable("x", "BOOL"),),
        (OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x"),)),),
        family="SAT",
    )
    report = certify_optimization_result(model, result(model, "SAT", {"x": 1}))
    assert report["status"] == "UNSUPPORTED"
    assert report["verification_level"] == "SOLVER_VALIDATED"
    assert report["certificate"] is None


def test_tampered_artifact_is_rejected_by_recheck():
    model = unsat_model()
    res = result(model, "UNSAT")
    claim, artifact = build_finite_domain_proof(model, res)
    tampered = type(artifact)(
        claim.claim_id,
        claim.fingerprint,
        artifact.proof_format,
        {**artifact.payload, "feasible_count": 1},
        artifact.producer_id,
        artifact.producer_version,
    )
    with pytest.raises(ValueError, match="failed independent deterministic recheck"):
        verify_finite_domain_proof(model, res, claim, tampered)


def test_self_checker_cannot_create_proof_certified_certificate():
    with pytest.raises(ValueError, match="passing independent checker"):
        SolverClaimCertificate(
            "claim", "c" * 64, "artifact", "a" * 64,
            "solver", "1", False, "m" * 64, "r" * 64,
            "PROOF_CERTIFIED", "PASS", {"exact_exhaustion": True},
        )


def test_runtime_persists_claim_artifact_certificate_in_existing_evidence_plane_and_replays():
    model = optimal_model()
    res = result(model, "OPTIMAL", {"x": 1, "y": 0}, 1.0)
    engine = AASMEngine(ProblemSpec("v50 proof persistence"))
    durable = engine.certify_optimization_claim(model, res)
    report = engine.solver_proof_claim_report(durable["claim"]["claim_id"])
    assert len(report["claim_proof_artifacts"]) == 1
    assert len(report["claim_certificates"]) == 1
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_conformance_passes():
    report = run_solver_proof_conformance()
    assert report["status"] == "PASS", report
    assert all(report["checks"].values())
