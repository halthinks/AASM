from __future__ import annotations

from .optimization import (
    OPTIMIZATION_CAPABILITIES,
    OptimizationRequest,
    infer_solver_family,
    reference_optimization_models,
    solve_optimization_request,
    validate_optimization_result,
)
from .semantic_result import semantic_fingerprint


def run_optimization_conformance(*, real: bool = False) -> dict:
    models = reference_optimization_models()
    checks: dict[str, bool] = {
        "sat_family_inferred": infer_solver_family(models["SAT"]) == "SAT",
        "cp_sat_family_inferred": infer_solver_family(models["CP_SAT"]) == "CP_SAT",
        "milp_family_inferred": infer_solver_family(models["MILP"]) == "MILP",
        "canonical_fingerprints_distinct": len({row.fingerprint for row in models.values()}) == 3,
    }
    results = {}
    if real:
        providers = {"SAT": "cadical", "CP_SAT": "ortools-cp-sat", "MILP": "highs"}
        expected = {"SAT": {"SAT"}, "CP_SAT": {"OPTIMAL"}, "MILP": {"OPTIMAL"}}
        for family, model in models.items():
            request = OptimizationRequest(
                model,
                OPTIMIZATION_CAPABILITIES[family],
                "0.1.0",
                f"conformance-{family.lower()}",
                required_provider=providers[family],
            )
            result = solve_optimization_request(request)
            validate_optimization_result(request, result)
            checks[f"{family.lower()}_native_backend_executes"] = result.status in expected[family]
            results[family] = result.to_dict()
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {"status": status, "real_backends": bool(real), "checks": checks, "results": results}
    report["report_fingerprint"] = semantic_fingerprint(report)
    return report


__all__ = ["run_optimization_conformance"]
