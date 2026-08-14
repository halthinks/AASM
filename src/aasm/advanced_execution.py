from __future__ import annotations

import time
from typing import Any, Mapping

from . import advanced_optimization as _advanced
from .advanced_optimization import (
    AdvancedSolverIdentity,
    AdvancedSolverRequest,
    AdvancedSolverResult,
    FastSATProblem,
    validate_advanced_result,
)


def _package_version(name: str) -> str:
    return _advanced._package_version(name)


def _run_fast_sat(request: AdvancedSolverRequest) -> AdvancedSolverResult:
    """Execute Kissat through its dedicated PySAT class.

    PySAT exposes Kissat404 as a concrete solver class but does not register it
    in the generic SolverNames dispatcher. Kissat's PySAT binding also does not
    expose aggregate statistics, so lack of those statistics is represented as
    telemetry rather than being misclassified as a failed solve.
    """
    from pysat.solvers import Kissat404

    problem: FastSATProblem = request.problem  # type: ignore[assignment]
    mapping = {row.variable_id: index + 1 for index, row in enumerate(problem.model.variables)}
    clauses = [
        [mapping[lit.variable_id] if lit.positive else -mapping[lit.variable_id] for lit in row.literals]
        for row in problem.model.constraints
    ]
    start = time.monotonic()
    try:
        with Kissat404(bootstrap_with=clauses, use_timer=True) as solver:
            solved = solver.solve()
            assignment: dict[str, float] = {}
            if solved:
                values = set(solver.get_model() or [])
                assignment = {vid: 1.0 if idx in values else 0.0 for vid, idx in mapping.items()}
            result = AdvancedSolverResult(
                request.request_id,
                request.fingerprint,
                problem.fingerprint,
                "SAT" if solved else "UNSAT",
                AdvancedSolverIdentity("kissat", "pysat:kissat404", _package_version("python-sat"), "kissat404"),
                assignment=assignment,
                telemetry={"aggregate_statistics_exposed": False, "non_incremental": True},
                wall_time_ms=int((time.monotonic() - start) * 1000),
            )
            validate_advanced_result(request, result)
            return result
    except Exception as exc:
        return AdvancedSolverResult(
            request.request_id,
            request.fingerprint,
            problem.fingerprint,
            "ERROR",
            AdvancedSolverIdentity("kissat", "pysat:kissat404", _package_version("python-sat"), "kissat404"),
            wall_time_ms=int((time.monotonic() - start) * 1000),
            diagnostics=(f"{type(exc).__name__}: {exc}",),
        )


def solve_advanced_request(request: AdvancedSolverRequest | Mapping[str, Any]) -> AdvancedSolverResult:
    parsed = request if isinstance(request, AdvancedSolverRequest) else AdvancedSolverRequest.from_dict(request)
    if parsed.kind == "FAST_SAT":
        return _run_fast_sat(parsed)
    # The other v0.46 adapters are implemented in the canonical advanced module.
    return _advanced.solve_advanced_request(parsed)


__all__ = ["solve_advanced_request"]
