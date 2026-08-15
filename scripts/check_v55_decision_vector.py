from __future__ import annotations

import json
from pathlib import Path

from aasm.decision_vector_ir import (
    DECISION_VECTOR_CONTRACT_ID,
    DecisionHardFloor,
    DecisionObjective,
    GovernedDecisionVector,
    compile_linear_decision_vector,
    decision_vector_contract,
    evaluate_hard_floors,
)
from aasm.multi_objective import solve_lexicographic_finite
from aasm.optimization import OptimizationModel, OptimizationVariable

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    contract = decision_vector_contract()
    require(contract["contract_id"] == DECISION_VECTOR_CONTRACT_ID, "decision vector contract drift")
    require(contract["hard_floors"] == "SEPARATE_CONSTRAINT_CLASS_NEVER_WEIGHTED_OR_TRADED", "hard floors must remain non-scalarized")
    require(contract["scalarization"] == "NONE", "decision vector scalarization must remain disabled")
    require(contract["resource_policy_can_weaken_hard_semantics"] is False, "resource policy may not weaken hard semantics")
    require(contract["truth_authority"] == "NONE", "decision vector may not grant truth authority")
    schema = json.loads((ROOT / "schemas" / "decision-vector.schema.json").read_text(encoding="utf-8"))
    require(schema["properties"]["contract_id"]["const"] == DECISION_VECTOR_CONTRACT_ID, "decision-vector schema drift")

    model = OptimizationModel(
        "v55 decision gate",
        (OptimizationVariable("safe", "BOOL"), OptimizationVariable("cheap", "BOOL")),
        (),
        family="CP_SAT",
    )
    vector = GovernedDecisionVector(
        model,
        (DecisionHardFloor("hard-safety", "safety-threshold", ">=", 1, coefficients={"safe": 1}, source_reference_fingerprints=("textpcb:req:safety",)),),
        (
            DecisionObjective("engineering-safety", "safety", 0, "MAXIMIZE", category="ENGINEERING", coefficients={"safe": 1}),
            DecisionObjective("resource-cost", "cost", 1, "MINIMIZE", category="RESOURCE", coefficients={"safe": 100, "cheap": -1}),
        ),
    )
    require(not evaluate_hard_floors(vector, {"safe": 0, "cheap": 1})["passes"], "cheap invalid candidate must fail hard floor before optimization")
    problem, compilation = compile_linear_decision_vector(vector)
    require(problem is not None and compilation.status == "PASS", "linear decision vector must compile into v0.52 multi-objective problem")
    result = solve_lexicographic_finite(problem)["result"]
    require(result.selected.assignment["safe"] == 1.0, "resource savings must not displace higher-priority safety")
    require([stage.objective_id for stage in result.stages] == ["engineering-safety", "resource-cost"], "lexicographic priority trace drift")
    print("v0.55 governed decision vector contracts: PASS")


if __name__ == "__main__":
    main()
