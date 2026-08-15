from __future__ import annotations

import json
from pathlib import Path

from aasm.optimization import (
    OptimizationConstraint, OptimizationModel, OptimizationObjective, OptimizationRequest,
    OptimizationResult, OptimizationSolverIdentity, OptimizationVariable,
)
from aasm.provider_status_v2 import (
    PROVIDER_STATUS_MAP_CONTRACT_ID, highs_status_map, map_provider_status,
    ortools_cp_sat_status_map, provider_status_map_contract,
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

    invalid = normalize_optimization_result_v2(
        result(request, "ERROR"), request=request,
        termination=ProviderTermination("MODEL_INVALID", raw_status="MODEL_INVALID", raw_status_code="1"),
        normalized_status="MODEL_INVALID",
    )
    require(invalid.normalized_status == "MODEL_INVALID", "model-invalid collapsed into another status")
    require(project_v2_to_legacy_status("NUMERICAL_FAILURE").status == "ERROR", "numerical failure v1 projection drift")

    ortools = map_provider_status(ortools_cp_sat_status_map("9.15.6755"), raw_status="MODEL_INVALID", raw_status_code="1")
    require(ortools.normalized_status == "MODEL_INVALID", "OR-Tools model-invalid mapping drift")
    highs = map_provider_status(highs_status_map("1.14.0"), raw_status="kUnboundedOrInfeasible", raw_status_code="9", objective_present=True)
    require(highs.normalized_status == "INFEASIBLE_OR_UNBOUNDED", "HiGHS unbounded-or-infeasible mapping drift")
    unknown = map_provider_status(highs_status_map("1.14.0"), raw_status="kFutureStatus", raw_status_code="999")
    require(unknown.mapping_status == "NO_EXACT_RULE" and unknown.termination.raw_status_code == "999", "unknown provider status guessed")
    print("v0.56 solver outcome/status-v2 source contract: PASS")


if __name__ == "__main__":
    main()
