import importlib
import os

import pytest

from aasm.model import ProblemSpec
from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationRequest,
    OptimizationResult,
    OptimizationVariable,
    default_optimization_providers,
    reference_optimization_models,
    solve_optimization_request,
    validate_optimization_result,
)
from aasm.optimization_conformance import run_optimization_conformance
from aasm.runtime_v44 import AASMEngine
from aasm.solver_learning import (
    SolverLearningArtifact,
    apply_solver_learning_to_optimization_request,
    revalidate_finite_solver_learning,
)


def _require_backends():
    modules = ("pysat.solvers", "ortools.sat.python.cp_model", "highspy")
    if os.environ.get("AASM_REQUIRE_OPTIMIZATION_BACKENDS") == "1":
        for name in modules:
            importlib.import_module(name)
    else:
        for name in modules:
            pytest.importorskip(name)


def _provider(provider_id):
    return next(row for row in default_optimization_providers() if row.provider_id == provider_id)


def test_real_native_backend_conformance():
    _require_backends()
    report = run_optimization_conformance(real=True)
    assert report["status"] == "PASS", report
    assert report["checks"]["sat_native_backend_executes"] is True
    assert report["checks"]["cp_sat_native_backend_executes"] is True
    assert report["checks"]["milp_native_backend_executes"] is True


def test_real_backends_cross_existing_aasm_lease_and_evidence_boundary():
    _require_backends()
    engine = AASMEngine(ProblemSpec("v0.44 real optimization portfolio"))
    engine.install_default_optimization_capability_contracts(authority_id="policy", authority_class="POLICY")
    for provider in default_optimization_providers():
        engine.register_optimization_provider_runtime(provider, authority_id="policy", authority_class="POLICY")

    provider_for = {"SAT": "cadical", "CP_SAT": "ortools-cp-sat", "MILP": "highs"}
    expected = {"SAT": "SAT", "CP_SAT": "OPTIMAL", "MILP": "OPTIMAL"}
    for family, model in reference_optimization_models().items():
        engine.admit_optimization_model(model)
        requested = engine.request_optimization(
            model.model_id,
            requester_id="integration-test",
            required_provider=provider_for[family],
        )
        lease = engine.claim_next_task(f"worker-{provider_for[family]}", lease_seconds=120)
        out = engine.execute_optimization_lease(lease["lease_id"])
        assert out["result"]["status"] == expected[family], out
        assert out["satisfied"] is True
        assert out["obligation"]["status"] == "VERIFIED"
        stored = engine.optimization_result_report(requested["request"]["request_id"])["results"]
        assert len(stored) == 1
        validate_optimization_result(
            OptimizationRequest.from_dict(
                engine.optimization_request_report(requested["request"]["request_id"])["request"]
            ),
            OptimizationResult.from_dict(stored[0]["result"]),
        )
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_real_ortools_consumes_validated_solver_learning_assignment_hint():
    _require_backends()
    model = OptimizationModel(
        "v0.53-real-learning-hint",
        (
            OptimizationVariable("x", "BOOL"),
            OptimizationVariable("y", "BOOL"),
        ),
        (
            OptimizationConstraint(
                "LINEAR",
                coefficients={"x": 1, "y": 1},
                sense=">=",
                rhs=1,
            ),
        ),
        objective=OptimizationObjective("MINIMIZE", {"x": 1, "y": 1}),
        family="CP_SAT",
    )
    artifact = SolverLearningArtifact(
        "INCUMBENT",
        model.fingerprint,
        model.solver_family,
        {"assignment": {"x": 1, "y": 0}, "objective": 1},
    )
    validation = revalidate_finite_solver_learning(artifact, model)
    assert validation.status == "PASS"
    assert validation.application_authority == "PERFORMANCE_HINT_ONLY"

    request = OptimizationRequest(
        model,
        "solver.cp_sat",
        "0.1.0",
        "v53-real-hint-obligation",
        required_provider="ortools-cp-sat",
    )
    application, learned_request = apply_solver_learning_to_optimization_request(
        artifact,
        validation,
        request,
    )
    result = solve_optimization_request(learned_request)
    assert result.status == "OPTIMAL", result
    validate_optimization_result(learned_request, result)
    assert result.statistics["solver_learning_hint_count"] == 1
    assert result.statistics["solver_learning_application_ids"] == [application.application_id]
    assert result.metadata["solver_learning_hints_consumed"] == 1
    assert result.metadata["solver_learning_application_ids"] == [application.application_id]
