from __future__ import annotations

from copy import deepcopy
from typing import Any

from .optimization import OptimizationConstraint, OptimizationModel, OptimizationObjective, OptimizationVariable
from .semantic_result import semantic_fingerprint

PULP_ADAPTER_CONTRACT_ID = "aasm.adapter.pulp.v1"
PULP_ADAPTER_CONTRACT_VERSION = "0.1.0"


def pulp_adapter_contract() -> dict[str, Any]:
    return {
        "contract_id": PULP_ADAPTER_CONTRACT_ID,
        "contract_version": PULP_ADAPTER_CONTRACT_VERSION,
        "authority": "TRANSLATION_ONLY",
        "direction": "PULP_LP_PROBLEM_TO_AASM_OPTIMIZATION_MODEL",
        "solver_execution": "NEVER",
        "supported": ["LINEAR_OBJECTIVE", "LINEAR_CONSTRAINTS", "CONTINUOUS", "INTEGER", "BINARY"],
        "unbounded_variable_policy": "REJECT_NOT_APPROXIMATE",
        "nonlinear_policy": "REJECT",
        "post_import_execution": "AASM_NATIVE_PORTFOLIO",
    }


def _category(variable) -> str:
    category = str(getattr(variable, "cat", "Continuous"))
    low = getattr(variable, "lowBound", None)
    high = getattr(variable, "upBound", None)
    if category.lower() in {"binary", "lpbinary"} or (category.lower() in {"integer", "lpinteger"} and low == 0 and high == 1):
        return "BOOL"
    if category.lower() in {"integer", "lpinteger"}:
        return "INTEGER"
    if category.lower() in {"continuous", "lpcontinuous"}:
        return "CONTINUOUS"
    raise ValueError(f"unsupported PuLP variable category: {category}")


def _expression_terms(expression) -> dict[str, float]:
    if expression is None:
        return {}
    try:
        pairs = list(expression.items())
    except Exception as exc:
        raise TypeError("PuLP expression does not expose linear items()") from exc
    result: dict[str, float] = {}
    for variable, coefficient in pairs:
        name = str(getattr(variable, "name", "") or "")
        if not name:
            raise ValueError("PuLP expression references unnamed variable")
        result[name] = result.get(name, 0.0) + float(coefficient)
    return {key: value for key, value in sorted(result.items()) if value != 0.0}


def pulp_problem_to_optimization_model(problem) -> OptimizationModel:
    if problem is None or not callable(getattr(problem, "variables", None)):
        raise TypeError("expected a PuLP LpProblem-like object")
    variables = list(problem.variables())
    names = [str(getattr(row, "name", "") or "") for row in variables]
    if not names or any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("PuLP import requires unique non-empty variable names")
    converted_variables = []
    for variable in variables:
        low = getattr(variable, "lowBound", None)
        high = getattr(variable, "upBound", None)
        if low is None or high is None:
            raise ValueError(
                f"PuLP variable {variable.name} is unbounded on at least one side; v0.45 refuses semantic bound approximation"
            )
        converted_variables.append(OptimizationVariable(str(variable.name), _category(variable), float(low), float(high)))

    constraints = []
    sense_map = {-1: "<=", 0: "==", 1: ">="}
    for name, constraint in sorted(dict(getattr(problem, "constraints", {}) or {}).items()):
        raw_sense = int(getattr(constraint, "sense"))
        if raw_sense not in sense_map:
            raise ValueError(f"unsupported PuLP constraint sense: {raw_sense}")
        coefficients = _expression_terms(constraint)
        constant = float(getattr(constraint, "constant", 0.0) or 0.0)
        constraints.append(
            OptimizationConstraint(
                "LINEAR",
                coefficients=coefficients,
                sense=sense_map[raw_sense],
                rhs=-constant,
                metadata={"pulp_constraint_name": str(name)},
            )
        )

    objective = getattr(problem, "objective", None)
    converted_objective = None
    if objective is not None:
        coefficients = _expression_terms(objective)
        if coefficients:
            problem_sense = int(getattr(problem, "sense", 1))
            if problem_sense not in {1, -1}:
                raise ValueError(f"unsupported PuLP objective sense: {problem_sense}")
            converted_objective = OptimizationObjective(
                "MINIMIZE" if problem_sense == 1 else "MAXIMIZE",
                coefficients,
                float(getattr(objective, "constant", 0.0) or 0.0),
            )

    model = OptimizationModel(
        str(getattr(problem, "name", "pulp-import") or "pulp-import"),
        tuple(converted_variables),
        tuple(constraints),
        objective=converted_objective,
        family="AUTO",
        metadata={
            "source_adapter": PULP_ADAPTER_CONTRACT_ID,
            "source_modeler": "PuLP",
            "translation_authority": "PROPOSAL_ONLY",
        },
    )
    return model


def pulp_import_report(problem) -> dict[str, Any]:
    model = pulp_problem_to_optimization_model(problem)
    report = {
        "contract": pulp_adapter_contract(),
        "model": model.to_dict(),
        "solver_family": model.solver_family,
        "native_execution_required": True,
    }
    report["report_fingerprint"] = semantic_fingerprint(report)
    return deepcopy(report)


__all__ = [
    "PULP_ADAPTER_CONTRACT_ID", "PULP_ADAPTER_CONTRACT_VERSION", "pulp_adapter_contract",
    "pulp_problem_to_optimization_model", "pulp_import_report",
]
