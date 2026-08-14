import pytest

from aasm.convex_optimization import (
    CONVEX_CAPABILITY_ID,
    ConvexObjective,
    ConvexOptimizationModel,
    ConvexVariable,
    SecondOrderConeConstraint,
    convex_optimization_contract,
    reference_convex_models,
    validate_convex_solution,
)
from aasm.model import ProblemSpec
from aasm.pulp_adapter import pulp_adapter_contract
from aasm.runtime_v45 import AASMEngine


def test_convex_contract_preserves_native_v44_paths_and_evidence_authority():
    contract = convex_optimization_contract()
    assert contract["contract_id"] == "aasm.optimization.convex.v1"
    assert contract["capability_id"] == CONVEX_CAPABILITY_ID
    assert contract["scheduler"] == "EXISTING_AASM_RESOURCE_WORKER_LEASE"
    assert contract["result_authority"] == "EVIDENCE_ONLY"
    assert contract["direct_native_v44_paths_preserved"] == ["cadical", "ortools-cp-sat", "highs"]


def test_convex_qp_and_soc_models_are_canonical_and_validate_assignments():
    models = reference_convex_models()
    assert models["QP"].objective.quadratic_diagonal == {"x": 1.0, "y": 1.0}
    assert models["SOC"].soc_constraints[0].radius == 1.0
    validate_convex_solution(models["QP"], {"x": 1.0, "y": 2.0})
    with pytest.raises(ValueError, match="SOC"):
        validate_convex_solution(models["SOC"], {"x": 1.0, "y": 1.0})


def test_nonconvex_quadratic_objective_is_rejected():
    with pytest.raises(ValueError, match="positive semidefinite"):
        ConvexOptimizationModel(
            "bad",
            (ConvexVariable("x", -1, 1),),
            objective=ConvexObjective("MINIMIZE", quadratic_diagonal={"x": -1}),
        )


def test_pulp_contract_is_translation_only_and_never_executes_solver():
    contract = pulp_adapter_contract()
    assert contract["authority"] == "TRANSLATION_ONLY"
    assert contract["solver_execution"] == "NEVER"
    assert contract["post_import_execution"] == "AASM_NATIVE_PORTFOLIO"


def test_runtime_exposes_governed_convex_capability_path_without_parallel_scheduler():
    engine = AASMEngine(ProblemSpec("v0.45 convex capability"))
    engine.install_default_convex_capability_contract(authority_id="policy", authority_class="POLICY")
    admitted = engine.register_default_cvxpy_provider_runtime(authority_id="policy", authority_class="POLICY")
    assert admitted["resource"]["kind"] == "optimization-solver"
    assert admitted["worker"]["resource_id"] == admitted["resource"]["resource_id"]
    assert admitted["provider"]["provider"]["capability_id"] == "solver.convex"
