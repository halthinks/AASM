from __future__ import annotations

from typing import Any

from .model import ProblemSpec
from .optimization import OptimizationConstraint, OptimizationModel, OptimizationVariable, validate_optimization_solution
from .runtime_v51 import AASMEngine
from .solution_pools import (
    EnumerationCursor,
    SolutionPool,
    SolutionRecord,
    binary_overlap_models,
    certify_complete_finite_enumeration,
    enumerate_native_binary_backend,
    enumeration_contract,
    solution_pool_contract,
)


def _oracle_model() -> OptimizationModel:
    return OptimizationModel(
        "v0.51-oracle",
        (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1, "y": 1}, sense=">=", rhs=1),),
        family="CP_SAT",
    )


def _assignment_set(rows) -> set[tuple[tuple[str, float], ...]]:
    return {tuple(sorted((str(key), float(value)) for key, value in row.items())) for row in rows}


def _oracle_assignments(model: OptimizationModel) -> set[tuple[tuple[str, float], ...]]:
    variables = [row.variable_id for row in model.variables]
    out = set()
    limit = 1 << len(variables)
    for mask in range(limit):
        assignment = {variable_id: float((mask >> index) & 1) for index, variable_id in enumerate(variables)}
        try:
            validate_optimization_solution(model, assignment)
        except ValueError:
            continue
        out.add(tuple(sorted(assignment.items())))
    return out


def run_solution_pool_conformance(*, real_backends: bool = False) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}

    model = _oracle_model()
    engine = AASMEngine(ProblemSpec("v0.51 solution-pool conformance"))
    complete = engine.enumerate_complete_solution_pool(model, max_states_per_step=1, max_total_states=16)
    pool = complete["pool"]
    certificate = complete["completeness_certificate"]
    assignments = _assignment_set(row["assignment"] for row in pool["solutions"])
    oracle = _oracle_assignments(model)
    checks["finite_oracle_every_solution_exactly_once"] = assignments == oracle and len(pool["solutions"]) == len(oracle) == 3
    checks["complete_requires_passing_certificate"] = pool["completeness_status"] == "COMPLETE" and certificate["status"] == "PASS" and certificate["unseen_solution_count"] == 0
    checks["independent_exhaustion_checker"] = certificate["independent_of_solver"] is True and certificate["checker_id"] == enumeration_contract()["completeness_checker"]["checker_id"]
    checks["durable_no_good_per_solution"] = len(pool["exclusion_ids"]) == len(pool["solution_ids"]) == 3
    checks["exact_event_replay"] = engine.replay().canonical_hash() == engine.snapshot.canonical_hash()

    partial_engine = AASMEngine(ProblemSpec("v0.51 partial pool"))
    partial = partial_engine.start_solution_pool(model, mode="BOUNDED_PARTIAL_POOL", max_total_states=16)
    partial_id = partial["pool"]["pool_id"]
    partial_engine.advance_solution_pool(partial_id, model, max_states_per_step=2, max_total_states=16)
    partial_pool = partial_engine.solution_pool_report(partial_id)["pool"]
    checks["partial_pool_never_implies_completeness"] = partial_pool["completeness_status"] != "COMPLETE" and not partial_pool["completeness_certificate_id"]

    manual_engine = AASMEngine(ProblemSpec("v0.51 duplicate pool"))
    manual = manual_engine.start_solution_pool(model, mode="DIVERSE_POOL")
    manual_id = manual["pool"]["pool_id"]
    first = manual_engine.admit_solution_to_pool(manual_id, model, {"x": 1, "y": 0}, solver_provider_id="fixture")
    second = manual_engine.admit_solution_to_pool(manual_id, model, {"x": 1, "y": 0}, solver_provider_id="fixture")
    checks["duplicate_solution_is_idempotent"] = first["already_present"] is False and second["already_present"] is True and len(manual_engine.solution_pool_report(manual_id)["pool"]["solutions"]) == 1

    missing = SolutionPool(
        model.fingerprint,
        "COMPLETE_FINITE_ENUMERATION",
        solutions=(SolutionRecord(model.fingerprint, {"x": 1, "y": 0}),),
        completeness_status="EXHAUSTED_PENDING_CERTIFICATION",
    )
    false_cursor = EnumerationCursor(missing.pool_id, model.fingerprint, missing.mode, 4, 4, accepted_solution_ids=tuple(row.solution_id for row in missing.solutions), exhausted=True)
    failed = certify_complete_finite_enumeration(model, missing, cursor=false_cursor, max_total_states=16)
    checks["false_completeness_fails_closed"] = failed.status == "FAIL" and failed.unseen_solution_count == 2

    details["oracle_pool"] = pool
    details["oracle_certificate"] = certificate
    details["partial_pool"] = partial_pool
    details["false_completeness_certificate"] = failed.to_dict()

    if real_backends:
        overlap = binary_overlap_models()
        cp = enumerate_native_binary_backend(overlap["CP_SAT"], "ortools-cp-sat", max_solutions=16)
        milp = enumerate_native_binary_backend(overlap["MILP"], "highs", max_solutions=16)
        cp_set = _assignment_set(cp["solutions"].values())
        milp_set = _assignment_set(milp["solutions"].values())
        expected = _oracle_assignments(overlap["CP_SAT"])
        checks["real_cp_sat_exhausts"] = cp["status"] == "PASS" and cp["exhausted"] is True
        checks["real_highs_exhausts"] = milp["status"] == "PASS" and milp["exhausted"] is True
        checks["real_cross_backend_exact_solution_set"] = cp_set == milp_set == expected and len(expected) == 7
        details["real_cp_sat"] = cp
        details["real_highs"] = milp

    status = "PASS" if all(checks.values()) else "FAIL"
    return {
        "status": status,
        "real_backends": bool(real_backends),
        "contract": solution_pool_contract(),
        "enumeration_contract": enumeration_contract(),
        "checks": checks,
        "details": details,
    }


__all__ = ["run_solution_pool_conformance"]
