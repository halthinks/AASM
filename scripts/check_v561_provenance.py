from __future__ import annotations

import json
from pathlib import Path

from aasm.solver_provenance import (
    SOLVER_EXECUTION_PROFILE_CONTRACT_ID,
    SOLVER_PROFILE_EVALUATION_CONTRACT_ID,
    SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID,
    solver_provenance_contract,
)
from aasm._runtime_v56_provenance import SOLVER_PROVENANCE_RUNTIME_CONTRACT_ID, solver_provenance_runtime_contract

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = solver_provenance_contract()
    runtime = solver_provenance_runtime_contract()
    require(contract["profile_contract_id"] == SOLVER_EXECUTION_PROFILE_CONTRACT_ID, "execution profile contract drift")
    require(contract["runtime_provenance_contract_id"] == SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID, "runtime provenance contract drift")
    require(contract["profile_evaluation_contract_id"] == SOLVER_PROFILE_EVALUATION_CONTRACT_ID, "profile evaluation contract drift")
    require(contract["effective_options"] == "ADAPTER_OBSERVED_ACTUAL_CONFIGURATION_REQUIRED", "effective-option authority drift")
    require(contract["adapter_identity"] == "ADAPTER_ID_AND_VERSION_REQUIRED", "adapter identity drift")
    require(contract["worker_thread_counts"] == "FIRST_CLASS_EXPLICIT_OR_UNKNOWN", "worker/thread identity drift")
    require(contract["reproducibility"] == "NOT_CLAIMED_BY_PROVENANCE_ALONE", "provenance overclaims reproducibility")
    require(contract["truth_authority"] == "NONE" and contract["policy_authority"] == "NONE", "provenance authority drift")
    require(runtime["contract_id"] == SOLVER_PROVENANCE_RUNTIME_CONTRACT_ID, "runtime contract drift")
    require(runtime["effective_configuration_source"] == "AASM_PROVIDER_ADAPTER_OBSERVATION_NOT_CALLER_ASSERTION", "runtime accepts caller effective configuration")
    require(runtime["parallel_provenance_table"] == "NONE", "parallel provenance table introduced")
    require(runtime["provenance_grants_reproducibility"] is False, "runtime provenance overclaims reproducibility")

    schemas = {
        "solver-execution-profile.schema.json": SOLVER_EXECUTION_PROFILE_CONTRACT_ID,
        "solver-runtime-provenance.schema.json": SOLVER_RUNTIME_PROVENANCE_CONTRACT_ID,
        "solver-profile-evaluation.schema.json": SOLVER_PROFILE_EVALUATION_CONTRACT_ID,
    }
    for filename, contract_id in schemas.items():
        data = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        require(data["properties"]["contract_id"]["const"] == contract_id, f"schema contract drift: {filename}")

    text = (ROOT / "src/aasm/solver_execution_observation.py").read_text(encoding="utf-8")
    for token in (
        "execution_observation_for_optimization",
        "execution_observation_for_convex",
        "aasm.optimization.pysat-cadical",
        "aasm.optimization.ortools-cp-sat",
        "aasm.optimization.highs",
        "aasm.optimization.cvxpy",
        "UNAVAILABLE_FROM_CURRENT_ADAPTER",
        "BACKEND_SPECIFIC_NOT_EXPOSED_BY_CURRENT_CVXPY_ADAPTER",
    ):
        require(token in text, f"provider execution observation drift: {token}")

    runtime_text = (ROOT / "src/aasm/_runtime_v56_provenance.py").read_text(encoding="utf-8")
    require("PROVENANCE_V2" not in runtime_text, "interrupted provenance-v2 plane leaked into authoritative runtime")
    require("record_solver_runtime_provenance" in runtime_text, "v1 provenance runtime method missing")
    require("record_convex_solver_runtime_provenance" in runtime_text, "CVXPY provenance runtime method missing")
    require("effective_options:" not in runtime_text.split("def record_solver_runtime_provenance", 1)[1].split(") ->", 1)[0], "runtime method accepts caller effective options")

    print("v0.56.1 execution profile/runtime provenance source contract: PASS")


if __name__ == "__main__":
    main()
