from __future__ import annotations

import json
from pathlib import Path

from aasm.optimization import (
    OptimizationConstraint, OptimizationModel, OptimizationObjective, OptimizationRequest,
    OptimizationResult, OptimizationSolverIdentity, OptimizationVariable,
)
from aasm.provider_status_v2 import (
    PROVIDER_STATUS_MAP_CONTRACT_ID, ProviderStatusMap, ProviderStatusRule,
    highs_status_map, map_provider_status, ortools_cp_sat_status_map,
    provider_status_map_contract,
)
from aasm.solver_outcome_v2 import (
    SOLVER_OUTCOME_V2_CONTRACT_ID, ProviderTermination, normalize_optimization_result_v2,
    project_v2_to_legacy_status, solver_outcome_v2_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def fixture():
    model = OptimizationModel(
        "v56-gate", (OptimizationVariable("x", "INTEGER", 0, 10),),
        (OptimizationConstraint("LINEAR", coefficients={"x": 1}, sense=">=", rhs=1),),
        OptimizationObjective("MINIMIZE", {"x": 1}), family="CP_SAT",
    )
    request = OptimizationRequest(model, "solver.cp_sat", "0.1.0", "v56-gate-obligation", required_provider="ortools-cp-sat")
    return request


def result(request, status, assignment=None, *, raw_status="", raw_code=""):
    assignment = assignment or {}
    return OptimizationResult(
        request.request_id, request.fingerprint, request.model.fingerprint, status,
        OptimizationSolverIdentity("ortools-cp-sat", "ortools.cp-sat", "9.15.6755"),
        assignment=assignment,
        objective_value=float(assignment["x"]) if assignment else None,
        best_bound=1.0 if assignment else None,
        relative_gap=0.5 if assignment else None,
        statistics={"raw_status": raw_status or status, "raw_status_code": raw_code},
        result_id=f"v56-{status.lower()}-{bool(assignment)}",
    )


def main() -> None:
    outcome_contract = solver_outcome_v2_contract()
    map_contract = provider_status_map_contract()
    require(outcome_contract["contract_id"] == SOLVER_OUTCOME_V2_CONTRACT_ID, "solver outcome contract drift")
    require(outcome_contract["authoritative_detailed_status"] == "normalized_status", "v2 status authority drift")
    require(outcome_contract["legacy_projection"] == "V2_TO_V1_ONE_WAY_EXPLICITLY_LOSSY_WHERE_REQUIRED", "legacy projection drift")
    require(outcome_contract["truth_authority"] == "NONE", "solver outcome may not grant truth authority")
    require(map_contract["contract_id"] == PROVIDER_STATUS_MAP_CONTRACT_ID, "provider status map contract drift")
    require(map_contract["substring_inference"] == "FORBIDDEN", "substring provider status inference reintroduced")

    for filename, contract_id in {
        "solver-outcome-v2.schema.json": SOLVER_OUTCOME_V2_CONTRACT_ID,
        "provider-status-map.schema.json": PROVIDER_STATUS_MAP_CONTRACT_ID,
    }.items():
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    request = fixture()
    timeout = normalize_optimization_result_v2(result(request, "TIMEOUT", {"x": 2.0}), request=request)
    require(timeout.normalized_status == "TIME_LIMIT_WITH_INCUMBENT", "timeout incumbent detail lost")
    require(timeout.incumbent_validation == "VALIDATED", "incumbent not independently validated")
    require(timeout.legacy_projection.status == "TIMEOUT" and timeout.legacy_projection.lossy, "timeout legacy projection incorrect")

    required_terminal_classes = (
        ("NODE_LIMIT", "NODE_LIMIT_NO_SOLUTION", "UNKNOWN"),
        ("MEMORY_LIMIT", "MEMORY_LIMIT_NO_SOLUTION", "UNKNOWN"),
        ("USER_INTERRUPT", "USER_INTERRUPT_NO_SOLUTION", "UNKNOWN"),
        ("NUMERICAL_FAILURE", "NUMERICAL_FAILURE", "ERROR"),
        ("MODEL_INVALID", "MODEL_INVALID", "ERROR"),
        ("PROVIDER_UNAVAILABLE", "PROVIDER_UNAVAILABLE", "ERROR"),
        ("UNSUPPORTED_FEATURE", "UNSUPPORTED_FEATURE", "ERROR"),
        ("STALE_RESULT", "STALE_RESULT", "UNKNOWN"),
    )
    for termination_reason, normalized_status, legacy_status in required_terminal_classes:
        source_status = "ERROR" if legacy_status == "ERROR" else "UNKNOWN"
        outcome = normalize_optimization_result_v2(
            result(request, source_status), request=request,
            termination=ProviderTermination(termination_reason, raw_status=termination_reason),
            normalized_status=normalized_status,
        )
        require(outcome.normalized_status == normalized_status, f"terminal class drift: {normalized_status}")
        require(outcome.termination.reason == termination_reason, f"termination reason drift: {termination_reason}")
        require(outcome.legacy_projection.status == legacy_status, f"legacy projection drift: {normalized_status}")

    require(project_v2_to_legacy_status("FEASIBLE_NOT_PROVEN_OPTIMAL").status == "FEASIBLE", "feasible compatibility projection drift")
    require(project_v2_to_legacy_status("UNBOUNDED").status == "UNKNOWN", "unbounded compatibility projection drift")

    ortools = map_provider_status(ortools_cp_sat_status_map("9.15.6755"), raw_status="MODEL_INVALID", raw_status_code="1")
    require(ortools.normalized_status == "MODEL_INVALID", "OR-Tools model-invalid mapping drift")
    highs = map_provider_status(highs_status_map("1.14.0"), raw_status="kUnboundedOrInfeasible", raw_status_code="9", objective_present=True)
    require(highs.normalized_status == "INFEASIBLE_OR_UNBOUNDED", "HiGHS unbounded-or-infeasible mapping drift")
    unknown = map_provider_status(highs_status_map("1.14.0"), raw_status="kFutureStatus", raw_status_code="999")
    require(unknown.mapping_status == "NO_EXACT_RULE" and unknown.termination.raw_status_code == "999", "unknown provider status guessed")

    synthetic = ProviderStatusMap(
        "v56-terminal-gate", "1", "aasm.v56-gate", "1",
        (
            ProviderStatusRule("MEMORY_LIMIT", "MEMORY_LIMIT_DYNAMIC", raw_status="MEMORY", raw_status_code="21", incumbent_eligibility="VALIDATED_IF_PRESENT", provider_version_range="==1"),
            ProviderStatusRule("PROVIDER_UNAVAILABLE", "PROVIDER_UNAVAILABLE", raw_status="UNAVAILABLE", raw_status_code="22", provider_version_range="==1"),
            ProviderStatusRule("UNSUPPORTED_FEATURE", "UNSUPPORTED_FEATURE", raw_status="UNSUPPORTED", raw_status_code="23", provider_version_range="==1"),
        ),
    )
    require(map_provider_status(synthetic, raw_status="MEMORY", raw_status_code="21").normalized_status == "MEMORY_LIMIT_NO_SOLUTION", "memory-limit mapping drift")
    require(map_provider_status(synthetic, raw_status="UNAVAILABLE", raw_status_code="22").normalized_status == "PROVIDER_UNAVAILABLE", "provider-unavailable mapping drift")
    require(map_provider_status(synthetic, raw_status="UNSUPPORTED", raw_status_code="23").normalized_status == "UNSUPPORTED_FEATURE", "unsupported-feature mapping drift")

    print("v0.56 solver outcome/status-v2 source contract: PASS")


if __name__ == "__main__":
    main()
