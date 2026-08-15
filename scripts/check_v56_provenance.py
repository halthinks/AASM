from __future__ import annotations

import json
from pathlib import Path

from aasm.optimization import OptimizationResult, OptimizationSolverIdentity
from aasm.solver_outcome_v2 import normalize_optimization_result_v2
from aasm.solver_provenance import SOLVER_EXECUTION_PROFILE_CONTRACT_ID, SolverExecutionProfile
from aasm.solver_provenance_v2 import (
    SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID,
    SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID,
    build_solver_runtime_provenance_v2,
    evaluate_solver_execution_profile_v2,
    solver_provenance_v2_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = solver_provenance_v2_contract()
    require(contract["execution_profile_contract_id"] == SOLVER_EXECUTION_PROFILE_CONTRACT_ID, "execution profile contract drift")
    require(contract["runtime_provenance_contract_id"] == SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID, "runtime provenance v2 contract drift")
    require(contract["profile_evaluation_contract_id"] == SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID, "profile evaluation v2 contract drift")
    require(contract["adapter_identity"] == "EXPLICIT_ADAPTER_ID_AND_VERSION_REQUIRED", "adapter identity boundary drift")
    require(contract["requested_vs_effective_options"] == "SEPARATE", "requested/effective options were collapsed")
    require(contract["reproducibility"] == "NOT_CLAIMED_BY_PROVENANCE_ALONE", "provenance alone must not claim reproducibility")
    require(contract["truth_authority"] == "NONE", "solver provenance may not grant truth authority")

    schemas = {
        "solver-execution-profile.schema.json": SOLVER_EXECUTION_PROFILE_CONTRACT_ID,
        "solver-runtime-provenance-v2.schema.json": SOLVER_RUNTIME_PROVENANCE_V2_CONTRACT_ID,
        "solver-profile-evaluation-v2.schema.json": SOLVER_PROFILE_EVALUATION_V2_CONTRACT_ID,
    }
    for filename, contract_id in schemas.items():
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    result = OptimizationResult(
        "prov-gate-request",
        "prov-gate-request-fp",
        "prov-gate-model-fp",
        "FEASIBLE",
        OptimizationSolverIdentity("provider-gate", "solver.impl", "2", ("solver", "--threads=1", "--seed=11")),
        assignment={"x": 1.0},
        result_id="prov-gate-result",
    )
    outcome = normalize_optimization_result_v2(result)
    profile = SolverExecutionProfile(
        "strict gate profile",
        "STRICT_EFFECTIVE_OPTIONS",
        requested_options={"threads": 1, "seed": 11},
        required_effective_options={"threads": 1, "seed": 11},
        provider_id="provider-gate",
        provider_version="2",
        adapter_id="aasm.provider-gate",
        adapter_version="1",
        required_environment_fingerprint="env-gate",
    )
    provenance = build_solver_runtime_provenance_v2(
        result,
        outcome,
        profile,
        execution_id="prov-gate-execution",
        adapter_id="aasm.provider-gate",
        adapter_version="1",
        effective_options={"threads": 1, "seed": 11, "presolve": True},
        environment_fingerprint="env-gate",
        build_fingerprint="build-gate",
    )
    evaluation = evaluate_solver_execution_profile_v2(profile, provenance)
    require(evaluation.compliant, f"reference strict provenance profile failed: {evaluation.deviations}")
    require(provenance.adapter_id == "aasm.provider-gate" and provenance.adapter_version == "1", "adapter identity missing from provenance")
    require(provenance.requested_options != provenance.effective_options, "requested/effective configurations were incorrectly collapsed")
    print("v0.56 adapter-bound solver provenance contracts: PASS")


if __name__ == "__main__":
    main()
