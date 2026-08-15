import importlib
import os

import pytest

from aasm.evidence import EvidenceRecord
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
from aasm.runtime_v44 import AASMEngine as V44Engine
from aasm.runtime_v54_exchange import AASMEngine as V54Engine
from aasm.runtime_v54_portfolio import SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.solver_learning import (
    SolverLearningArtifact,
    apply_solver_learning_to_optimization_request,
    revalidate_finite_solver_learning,
)


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"


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
    engine = V44Engine(ProblemSpec("v0.44 real optimization portfolio"))
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


def test_real_v54_ortools_highs_portfolio_uses_existing_leases_and_certified_race_policy():
    _require_backends()
    engine = V54Engine(ProblemSpec("v0.54 real governed portfolio"))
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement="native portfolio root", source="fixture"),
        reason="native portfolio trust root",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            ROOT,
            ROOT,
            WORKSPACE,
            SCOPE,
            tuple(SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES.values()),
        )
    )
    engine.install_default_optimization_capability_contracts(
        authority_id="policy",
        authority_class="POLICY",
    )
    for provider_id in ("ortools-cp-sat", "highs"):
        engine.register_optimization_provider_runtime(
            _provider(provider_id),
            authority_id="policy",
            authority_class="POLICY",
        )

    source = OptimizationModel(
        "v0.54-real-portfolio-source",
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
        family="AUTO",
    )
    engine.admit_optimization_model(source)
    prepared = engine.prepare_solver_portfolio(
        source.model_id,
        (
            {"target_family": "CP_SAT", "target_provider_id": "ortools-cp-sat"},
            {"target_family": "MILP", "target_provider_id": "highs"},
        ),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        requester_id="native-portfolio-test",
    )
    plan = prepared["plan"]
    leases = {}
    for provider_id in ("ortools-cp-sat", "highs"):
        claimed = engine.claim_solver_portfolio_leg(
            plan["portfolio_id"],
            provider_id,
            f"worker-{provider_id}",
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            lease_seconds=120,
        )
        leases[provider_id] = claimed["lease"]
        executed = engine.execute_solver_portfolio_leg(
            plan["portfolio_id"],
            provider_id,
            claimed["lease"]["lease_id"],
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
        )
        assert executed["result"]["status"] == "OPTIMAL", executed
        certified = engine.certify_solver_portfolio_leg(
            plan["portfolio_id"],
            provider_id,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
        )
        assert certified["status"] == "PASS", certified

    decision = engine.evaluate_solver_portfolio(
        plan["portfolio_id"],
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert decision["status"] == "CERTIFIED_OPTIMAL", decision
    assert decision["decision"]["certified"] is True
    assert decision["decision"]["selected_objective"] == 1.0
    assert len(decision["decision"]["decisive_certificate_ids"]) == 2
    assert decision["decision"]["policy"]["fastest_wins"] is False
    assert decision["decision"]["policy"]["majority_vote"] is False

    stored_leases = {row["lease_id"]: row for row in engine.list_leases()}
    for lease in leases.values():
        assert stored_leases[lease["lease_id"]]["status"] == "COMPLETED"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
