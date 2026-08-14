from __future__ import annotations

from .advanced_execution import solve_advanced_request
from .advanced_optimization import (
    ADVANCED_CAPABILITIES,
    ADVANCED_PROVIDERS,
    AdvancedSolverRequest,
    clear_incremental_sat_sessions,
    reference_advanced_problems,
    validate_advanced_result,
)
from .semantic_result import semantic_fingerprint


def run_advanced_optimization_conformance(*, real: bool = False) -> dict:
    problems = reference_advanced_problems()
    checks = {
        "five_advanced_problem_kinds_present": set(problems) == set(ADVANCED_CAPABILITIES),
        "canonical_fingerprints_distinct": len({row.fingerprint for row in problems.values()}) == 5,
        "incremental_problem_has_assumptions": len(problems["INCREMENTAL_SAT"].assumptions) == 2,
        "scheduling_has_no_overlap": bool(problems["CP_SAT_SCHEDULING"].no_overlap),
        "scheduling_has_cumulative": bool(problems["CP_SAT_SCHEDULING"].cumulative),
        "milp_has_warm_start": bool(problems["MILP_ADVANCED"].warm_start),
        "convex_has_affine_soc": bool(problems["CONVEX_ADVANCED"].affine_soc_constraints),
        "convex_has_cross_term_capable_factors": any(len(row.expression.coefficients) > 1 for row in problems["CONVEX_ADVANCED"].objective.quadratic_factors),
    }
    results = {}
    if real:
        clear_incremental_sat_sessions()
        for kind, problem in problems.items():
            request = AdvancedSolverRequest(problem, ADVANCED_CAPABILITIES[kind], "0.1.0", f"advanced-conformance-{kind.lower()}", ADVANCED_PROVIDERS[kind])
            result = solve_advanced_request(request)
            validate_advanced_result(request, result)
            expected = {"FAST_SAT": {"SAT"}, "INCREMENTAL_SAT": {"UNSAT"}, "CP_SAT_SCHEDULING": {"OPTIMAL"}, "MILP_ADVANCED": {"OPTIMAL", "FEASIBLE"}, "CONVEX_ADVANCED": {"OPTIMAL"}}[kind]
            checks[f"{kind.lower()}_real_backend_executes"] = result.status in expected
            if kind == "INCREMENTAL_SAT":
                checks["incremental_sat_unsat_core_returned"] = bool(result.unsat_core)
                second = solve_advanced_request(request)
                checks["incremental_sat_session_reused"] = second.telemetry.get("session_reused") is True
            if kind == "MILP_ADVANCED":
                checks["milp_bound_telemetry_present"] = "mip_nodes" in result.telemetry and "mip_gap" in result.telemetry
                checks["milp_warm_start_recorded"] = result.telemetry.get("warm_start_supplied") is True
            if kind == "CP_SAT_SCHEDULING":
                checks["cp_sat_deterministic_time_telemetry_present"] = "deterministic_time" in result.telemetry
            results[kind] = result.to_dict()
    report = {"status": "PASS" if all(checks.values()) else "FAIL", "real_backends": bool(real), "checks": checks, "results": results}
    report["report_fingerprint"] = semantic_fingerprint(report)
    return report


__all__ = ["run_advanced_optimization_conformance"]
