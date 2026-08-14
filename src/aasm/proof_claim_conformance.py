from __future__ import annotations

from .model import ProblemSpec
from .optimization import (
    BooleanLiteral,
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationResult,
    OptimizationSolverIdentity,
    OptimizationVariable,
)
from .proof_claims import certify_optimization_result, solver_proof_contract
from .runtime_v50 import AASMEngine


def _solver() -> OptimizationSolverIdentity:
    return OptimizationSolverIdentity("fixture-solver", "fixture", "1.0.0")


def _result(model: OptimizationModel, status: str, assignment=None, objective=None) -> OptimizationResult:
    return OptimizationResult(
        request_id=f"request-{status.lower()}",
        request_fingerprint=f"request-fingerprint-{status.lower()}",
        model_fingerprint=model.fingerprint,
        status=status,
        solver=_solver(),
        assignment=assignment or {},
        objective_value=objective,
    )


def _unsat_model() -> OptimizationModel:
    return OptimizationModel(
        "proof-unsat",
        (OptimizationVariable("x", "BOOL"),),
        (
            OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x", True),)),
            OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x", False),)),
        ),
        family="SAT",
    )


def _optimal_model() -> OptimizationModel:
    return OptimizationModel(
        "proof-optimal",
        (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1}, sense=">=", rhs=1),),
        OptimizationObjective("MINIMIZE", {"x": 1, "y": 1}),
        family="CP_SAT",
    )


def run_solver_proof_conformance() -> dict:
    checks = {}
    unsat_model = _unsat_model()
    unsat = certify_optimization_result(unsat_model, _result(unsat_model, "UNSAT"))
    checks["unsat_is_proof_certified"] = unsat["status"] == "PASS" and unsat["verification_level"] == "PROOF_CERTIFIED"
    checks["unsat_exact_exhaustion"] = bool((unsat.get("certificate") or {}).get("coverage", {}).get("exact_exhaustion"))

    optimal_model = _optimal_model()
    optimal_result = _result(optimal_model, "OPTIMAL", {"x": 0, "y": 1}, 1.0)
    optimal = certify_optimization_result(optimal_model, optimal_result)
    checks["optimal_is_proof_certified"] = optimal["status"] == "PASS" and optimal["verification_level"] == "PROOF_CERTIFIED"
    checks["optimal_value_is_one"] = (optimal.get("proof_artifact") or {}).get("payload", {}).get("optimum") == 1.0

    forged = certify_optimization_result(optimal_model, _result(optimal_model, "OPTIMAL", {"x": 0, "y": 0}, 0.0))
    checks["false_optimality_never_certifies"] = forged["status"] == "FAIL" and forged["verification_level"] == "SOLVER_VALIDATED"

    sat_model = OptimizationModel(
        "proof-sat",
        (OptimizationVariable("x", "BOOL"),),
        (OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x"),)),),
        family="SAT",
    )
    unsupported = certify_optimization_result(sat_model, _result(sat_model, "SAT", {"x": 1}))
    checks["positive_claim_does_not_fake_proof"] = unsupported["status"] == "UNSUPPORTED" and unsupported["verification_level"] == "SOLVER_VALIDATED"

    engine = AASMEngine(ProblemSpec("proof conformance"))
    durable = engine.certify_optimization_claim(optimal_model, optimal_result)
    report = engine.solver_proof_claim_report(durable["claim"]["claim_id"])
    checks["certificate_is_durable_evidence"] = len(report["claim_certificates"]) == 1
    checks["replay_exact"] = engine.replay().canonical_hash() == engine.snapshot.canonical_hash()

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "contract": solver_proof_contract(),
        "checks": checks,
        "unsat": unsat,
        "optimal": optimal,
        "false_optimality": forged,
    }
