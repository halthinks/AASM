import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationResult,
    OptimizationSolverIdentity,
    OptimizationVariable,
    default_optimization_providers,
)
from aasm.runtime_v54 import PortfolioRacePolicy
from aasm.runtime_v54_portfolio import (
    AASMEngine,
    SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES,
)
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"


def _provider(provider_id):
    return next(row for row in default_optimization_providers() if row.provider_id == provider_id)


def _source_model():
    return OptimizationModel(
        "v0.54 governed portfolio",
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


def _engine():
    engine = AASMEngine(ProblemSpec("v0.54 portfolio runtime"))
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement="portfolio root", source="fixture"),
        reason="portfolio trust root",
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
    source = _source_model()
    engine.admit_optimization_model(source)
    return engine, source


def _prepare(engine, source):
    return engine.prepare_solver_portfolio(
        source.model_id,
        (
            {"target_family": "CP_SAT", "target_provider_id": "ortools-cp-sat"},
            {"target_family": "MILP", "target_provider_id": "highs"},
        ),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        requester_id=ROOT,
        policy=PortfolioRacePolicy(),
    )


def _leg(plan, provider_id):
    return next(row for row in plan["legs"] if row["provider_id"] == provider_id)


def _commit_result(engine, plan, provider_id, lease_id, status, assignment):
    leg = _leg(plan, provider_id)
    request = engine.optimization_request_report(leg["request_id"])["request"]
    provider = _provider(provider_id)
    objective = float(assignment["x"] + assignment["y"])
    result = OptimizationResult(
        request["request_id"],
        request["fingerprint"],
        request["model"]["fingerprint"],
        status,
        OptimizationSolverIdentity(
            provider_id,
            provider.implementation,
            "fixture-1",
        ),
        assignment=assignment,
        objective_value=objective,
    )
    return engine.commit_optimization_result(result, lease_id=lease_id)


def test_portfolio_plan_uses_existing_requests_tasks_and_taskleases():
    engine, source = _engine()
    prepared = _prepare(engine, source)
    plan = prepared["plan"]
    assert len(plan["legs"]) == 2
    assert {row["provider_id"] for row in plan["legs"]} == {"ortools-cp-sat", "highs"}
    assert all(row["translation_certificate"]["status"] == "PASS" for row in plan["legs"])
    assert all(row["task"]["task_id"].endswith(f":{row['provider_id']}") for row in plan["legs"])

    report = engine.solver_portfolio_report(
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        portfolio_id=plan["portfolio_id"],
    )
    assert report["plan"]["evidence_id"] == prepared["evidence_id"]
    plan_evidence = next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == prepared["evidence_id"]
    )
    assert prepared["authority_decision_evidence_id"] in plan_evidence["derived_from"]

    cp = engine.claim_solver_portfolio_leg(
        plan["portfolio_id"],
        "ortools-cp-sat",
        "worker-ortools-cp-sat",
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
    )
    highs = engine.claim_solver_portfolio_leg(
        plan["portfolio_id"],
        "highs",
        "worker-highs",
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
    )
    assert cp["lease"]["task_id"] == _leg(plan, "ortools-cp-sat")["task"]["task_id"]
    assert highs["lease"]["task_id"] == _leg(plan, "highs")["task"]["task_id"]


def test_pending_portfolio_evaluation_records_no_decision_or_authority_mutation():
    engine, source = _engine()
    plan = _prepare(engine, source)["plan"]
    before_decisions = len(
        engine.solver_portfolio_report(workspace_id=WORKSPACE, scope_id=SCOPE)["decisions"].get(plan["portfolio_id"], [])
    )
    before_authority = len(engine.scoped_authority_report(workspace_id=WORKSPACE)["decisions"])
    pending = engine.evaluate_solver_portfolio(
        plan["portfolio_id"],
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert pending["status"] == "PENDING"
    assert set(pending["pending_providers"]) == {"ortools-cp-sat", "highs"}
    assert pending["recorded"] is False
    after_decisions = len(
        engine.solver_portfolio_report(workspace_id=WORKSPACE, scope_id=SCOPE)["decisions"].get(plan["portfolio_id"], [])
    )
    after_authority = len(engine.scoped_authority_report(workspace_id=WORKSPACE)["decisions"])
    assert after_decisions == before_decisions
    assert after_authority == before_authority


def test_committed_portfolio_results_use_existing_leases_and_certified_decision_lineage():
    engine, source = _engine()
    prepared = _prepare(engine, source)
    plan = prepared["plan"]
    cp_lease = engine.claim_solver_portfolio_leg(
        plan["portfolio_id"],
        "ortools-cp-sat",
        "worker-ortools-cp-sat",
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
    )["lease"]
    highs_lease = engine.claim_solver_portfolio_leg(
        plan["portfolio_id"],
        "highs",
        "worker-highs",
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
    )["lease"]

    cp_commit = _commit_result(
        engine,
        plan,
        "ortools-cp-sat",
        cp_lease["lease_id"],
        "OPTIMAL",
        {"x": 1, "y": 0},
    )
    highs_commit = _commit_result(
        engine,
        plan,
        "highs",
        highs_lease["lease_id"],
        "FEASIBLE",
        {"x": 0, "y": 1},
    )
    certification = engine.certify_solver_portfolio_leg(
        plan["portfolio_id"],
        "ortools-cp-sat",
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
    )
    assert certification["status"] == "PASS"

    evaluated = engine.evaluate_solver_portfolio(
        plan["portfolio_id"],
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert evaluated["status"] == "CERTIFIED_OPTIMAL"
    assert evaluated["decision"]["selected_provider_id"] == "ortools-cp-sat"
    assert evaluated["decision"]["certified"] is True
    assert evaluated["recorded"] is True

    decision_evidence = next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == evaluated["evidence_id"]
    )
    assert prepared["evidence_id"] in decision_evidence["derived_from"]
    assert cp_commit["result_evidence_id"] in decision_evidence["derived_from"]
    assert highs_commit["result_evidence_id"] in decision_evidence["derived_from"]
    assert certification["durable_certificate_evidence_id"] in decision_evidence["derived_from"]
    assert evaluated["authority_decision_evidence_id"] in decision_evidence["derived_from"]

    leases = {row["lease_id"]: row for row in engine.list_leases()}
    assert leases[cp_lease["lease_id"]]["status"] == "COMPLETED"
    assert leases[highs_lease["lease_id"]]["status"] == "COMPLETED"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_portfolio_leg_cannot_execute_without_its_existing_tasklease():
    engine, source = _engine()
    plan = _prepare(engine, source)["plan"]
    before = engine.optimization_result_report(_leg(plan, "ortools-cp-sat")["request_id"])["results"]
    assert before == []
    with pytest.raises(KeyError):
        engine.execute_solver_portfolio_leg(
            plan["portfolio_id"],
            "ortools-cp-sat",
            "missing-lease",
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
        )
    after = engine.optimization_result_report(_leg(plan, "ortools-cp-sat")["request_id"])["results"]
    assert after == []


def test_wrong_provider_worker_cannot_claim_another_portfolio_leg():
    engine, source = _engine()
    plan = _prepare(engine, source)["plan"]
    with pytest.raises(ValueError):
        engine.claim_solver_portfolio_leg(
            plan["portfolio_id"],
            "ortools-cp-sat",
            "worker-highs",
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
        )
