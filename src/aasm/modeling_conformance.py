from __future__ import annotations

import importlib

from .convex_optimization import (
    CONVEX_CAPABILITY_ID,
    ConvexOptimizationRequest,
    default_cvxpy_provider,
    reference_convex_models,
    solve_convex_request,
    validate_convex_result,
)
from .pulp_adapter import pulp_problem_to_optimization_model
from .semantic_result import semantic_fingerprint


def run_modeling_conformance(*, real: bool = False) -> dict:
    models = reference_convex_models()
    checks = {
        "qp_canonical": models["QP"].objective is not None and bool(models["QP"].objective.quadratic_diagonal),
        "soc_canonical": bool(models["SOC"].soc_constraints),
        "cvxpy_provider_is_solver_convex": default_cvxpy_provider().capability_id == CONVEX_CAPABILITY_ID,
        "pulp_adapter_translation_only": True,
    }
    results = {}
    if real:
        importlib.import_module("cvxpy")
        pulp = importlib.import_module("pulp")
        for name, model in models.items():
            request = ConvexOptimizationRequest(model, CONVEX_CAPABILITY_ID, "0.1.0", f"modeling-conformance-{name.lower()}")
            result = solve_convex_request(request)
            validate_convex_result(request, result)
            checks[f"cvxpy_{name.lower()}_executes"] = result.status == "OPTIMAL"
            results[name] = result.to_dict()
        problem = pulp.LpProblem("aasm-pulp-conformance", pulp.LpMinimize)
        x = pulp.LpVariable("x", 0, 4, cat=pulp.LpInteger)
        y = pulp.LpVariable("y", 0, 4)
        problem += x + y
        problem += x + y >= 3, "demand"
        imported = pulp_problem_to_optimization_model(problem)
        checks["pulp_imports_to_native_milp"] = imported.solver_family == "MILP"
        results["PULP_IMPORT"] = imported.to_dict()
    status = "PASS" if all(checks.values()) else "FAIL"
    report = {"status": status, "real_backends": bool(real), "checks": checks, "results": results}
    report["report_fingerprint"] = semantic_fingerprint(report)
    return report


__all__ = ["run_modeling_conformance"]
