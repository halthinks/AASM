from __future__ import annotations

import json
from pathlib import Path

from aasm.optimization import OptimizationResult, OptimizationSolverIdentity
from aasm.provider_status_v2 import (
    PROVIDER_STATUS_MAP_CONTRACT_ID,
    ProviderStatusMap,
    ProviderStatusRule,
    map_provider_termination,
    provider_status_map_contract,
)
from aasm.solver_outcome_v2 import (
    SOLVER_OUTCOME_V2_CONTRACT_ID,
    ProviderTermination,
    SolverEvidenceGrade,
    normalize_optimization_result_v2,
    solver_outcome_v2_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def _result(status: str, *, assignment=None) -> OptimizationResult:
    return OptimizationResult(
        "v56-request",
        "v56-request-fingerprint",
        "v56-model-fingerprint",
        status,
        OptimizationSolverIdentity("v56-provider", "solver.impl", "1"),
        assignment=assignment or {},
        best_bound=8.0 if assignment else None,
        relative_gap=0.2 if assignment else None,
        result_id=f"v56-result-{status.lower()}",
    )


def main() -> None:
    outcome_contract = solver_outcome_v2_contract()
    status_contract = provider_status_map_contract()
    require(outcome_contract["contract_id"] == SOLVER_OUTCOME_V2_CONTRACT_ID, "solver outcome v2 contract drift")
    require(outcome_contract["provider_optimal_status"] == "CLAIMED_OPTIMAL_NOT_PROVEN_OPTIMAL_WITHOUT_CHECKED_CERTIFICATE", "provider optimal claim boundary drift")
    require(outcome_contract["timeout_with_incumbent"] == "FEASIBLE_INCUMBENT_PRESERVED_SEPARATELY_FROM_TIME_LIMIT", "timeout/incumbent boundary drift")
    require(outcome_contract["truth_authority"] == "NONE", "solver outcome v2 may not grant truth authority")
    require(status_contract["contract_id"] == PROVIDER_STATUS_MAP_CONTRACT_ID, "provider status map contract drift")
    require(status_contract["fuzzy_matching"] == "FORBIDDEN", "provider status mapping may not become fuzzy")
    require(status_contract["ambiguous_mapping"] == "FAIL_CLOSED", "provider status ambiguity must fail closed")

    schemas = {
        "solver-outcome-v2.schema.json": SOLVER_OUTCOME_V2_CONTRACT_ID,
        "provider-status-map.schema.json": PROVIDER_STATUS_MAP_CONTRACT_ID,
    }
    for filename, contract_id in schemas.items():
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    timeout = normalize_optimization_result_v2(_result("TIMEOUT", assignment={"x": 1.0}))
    require(timeout.termination.reason == "TIME_LIMIT", "legacy timeout must normalize to TIME_LIMIT")
    require(timeout.solution_status == "FEASIBLE" and timeout.incumbent_status == "PRESENT", "timeout incumbent was lost")
    require(timeout.has_proven_optimality is False, "timeout incumbent was misreported as proven optimal")

    optimal = normalize_optimization_result_v2(_result("OPTIMAL", assignment={"x": 1.0}))
    require(optimal.optimality_claim == "CLAIMED_OPTIMAL", "provider optimal status was not preserved as a claim")
    require(optimal.has_proven_optimality is False, "provider optimal status became proof without a checked certificate")

    checked = SolverEvidenceGrade(
        "CHECKED_CERTIFICATE",
        "CHECKED_CERTIFICATE",
        certificate_ids=("cert-v56",),
        checker_ids=("checker-v56",),
    )
    proven = normalize_optimization_result_v2(_result("OPTIMAL", assignment={"x": 1.0}), evidence=checked)
    require(proven.has_proven_optimality is True, "checked optimality certificate did not promote the claim")

    mapping = ProviderStatusMap(
        "v56-provider",
        "1",
        "v56-adapter",
        "1",
        (
            ProviderStatusRule("TIME_LIMIT", raw_status="TIME_LIMIT", limit_unit="seconds"),
            ProviderStatusRule("NODE_LIMIT", raw_status_code="17", limit_unit="nodes"),
        ),
    )
    termination = map_provider_termination(mapping, raw_status="TIME_LIMIT", raw_message="limit", limit_value=30)
    require(termination.reason == "TIME_LIMIT" and termination.raw_status == "TIME_LIMIT", "explicit provider status mapping failed")
    unknown = map_provider_termination(mapping, raw_status="FUTURE_STATUS", raw_status_code="999")
    require(unknown.reason == "UNKNOWN", "unknown provider status was guessed instead of preserved as unknown")
    require(unknown.metadata["mapping_status"] == "NO_EXACT_RULE", "unknown provider status mapping provenance missing")
    print("v0.56 truthful solver outcome/status contracts: PASS")


if __name__ == "__main__":
    main()
