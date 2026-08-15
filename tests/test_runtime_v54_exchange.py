import pytest

from aasm._runtime_v53_solver_learning import SOLVER_LEARNING_AUTHORITY_CAPABILITIES
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationVariable,
    default_optimization_providers,
)
from aasm.runtime_v54_exchange import (
    AASMEngine,
    SOLVER_EXCHANGE_AUTHORITY_CAPABILITY,
)
from aasm.runtime_v54_portfolio import SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.solver_learning import SolverLearningArtifact


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"


def _provider(provider_id):
    return next(row for row in default_optimization_providers() if row.provider_id == provider_id)


def _source_model():
    return OptimizationModel(
        "v0.54 exchange source",
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


def _engine_and_plan():
    engine = AASMEngine(ProblemSpec("v0.54 exchange runtime"))
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement="exchange root", source="fixture"),
        reason="exchange trust root",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    capabilities = tuple(
        sorted(
            {
                *SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES.values(),
                SOLVER_EXCHANGE_AUTHORITY_CAPABILITY,
                SOLVER_LEARNING_AUTHORITY_CAPABILITIES["validate"],
                SOLVER_LEARNING_AUTHORITY_CAPABILITIES["apply"],
            }
        )
    )
    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(ROOT, ROOT, WORKSPACE, SCOPE, capabilities)
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
    prepared = engine.prepare_solver_portfolio(
        source.model_id,
        (
            {"target_family": "CP_SAT", "target_provider_id": "ortools-cp-sat"},
            {"target_family": "MILP", "target_provider_id": "highs"},
        ),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        requester_id=ROOT,
    )
    return engine, prepared["plan"]


def _leg(plan, provider_id):
    return next(row for row in plan["legs"] if row["provider_id"] == provider_id)


def _record_source_artifact(engine, plan, provider_id, kind, payload):
    leg = _leg(plan, provider_id)
    support = engine.add_evidence(
        EvidenceRecord(
            kind="solver_result",
            statement=f"source learning support from {provider_id}",
            source=provider_id,
        ),
        reason="exchange source learning support",
    )
    artifact = SolverLearningArtifact(
        kind,
        leg["target_model_fingerprint"],
        leg["target_family"],
        payload,
        source_evidence_ids=(support.evidence_id,),
        provider_id=provider_id,
    )
    recorded = engine.record_solver_learning_artifact(
        artifact,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
    )
    return artifact, recorded


def _validate_source(engine, artifact, plan, provider_id):
    target_model = OptimizationModel.from_dict(_leg(plan, provider_id)["translation"]["target_model"])
    result = engine.revalidate_solver_learning(
        artifact.learning_id,
        target_model,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert result["validation"]["status"] == "PASS"
    return result


def test_correctness_sensitive_learning_exchanges_cp_sat_to_milp_and_reuses_existing_apply_path():
    engine, plan = _engine_and_plan()
    artifact, recorded = _record_source_artifact(
        engine,
        plan,
        "ortools-cp-sat",
        "NO_GOOD",
        {
            "literals": [
                {"variable_id": "x", "positive": False},
                {"variable_id": "y", "positive": False},
            ]
        },
    )
    source_validation = _validate_source(engine, artifact, plan, "ortools-cp-sat")
    exchanged = engine.exchange_solver_learning(
        plan["portfolio_id"],
        "ortools-cp-sat",
        "highs",
        artifact.learning_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert exchanged["certificate"]["status"] == "PASS"
    assert exchanged["certificate"]["application_ready"] is True
    assert exchanged["target_validation"]["status"] == "PASS"
    assert exchanged["target_validation"]["application_authority"] == "PRUNING_CERTIFIED_FOR_EXACT_MODEL"
    target = exchanged["target_artifact"]
    assert target["learning_kind"] == "NO_GOOD"
    assert target["solver_family"] == "MILP"
    assert target["provider_id"] == "highs"
    assert target["payload"] == artifact.to_dict()["payload"]
    assert target["metadata"]["exchange_source_learning_fingerprint"] == artifact.fingerprint

    target_request = engine.optimization_request_report(_leg(plan, "highs")["request_id"])["request"]
    applied = engine.apply_solver_learning(
        target["learning_id"],
        target_request,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert applied["application"]["application_class"] == "PRUNING_CONSTRAINTS"
    assert applied["application"]["truth_authority"] == "NONE"
    assert applied["request"]["model"]["solver_family"] == "MILP"
    assert applied["executed"] is False

    exchange_evidence = next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == exchanged["evidence_id"]
    )
    assert recorded["evidence_id"] in exchange_evidence["derived_from"]
    assert source_validation["evidence_id"] in exchange_evidence["derived_from"]
    assert exchanged["target_artifact_evidence_id"] in exchange_evidence["derived_from"]
    assert exchanged["target_validation_evidence_id"] in exchange_evidence["derived_from"]
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_performance_hint_exchanges_milp_to_cp_sat_and_becomes_explicit_ortools_hint():
    engine, plan = _engine_and_plan()
    artifact, _ = _record_source_artifact(
        engine,
        plan,
        "highs",
        "INCUMBENT",
        {"assignment": {"x": 1, "y": 0}, "objective": 1},
    )
    _validate_source(engine, artifact, plan, "highs")
    exchanged = engine.exchange_solver_learning(
        plan["portfolio_id"],
        "highs",
        "ortools-cp-sat",
        artifact.learning_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert exchanged["certificate"]["status"] == "PASS"
    assert exchanged["certificate"]["application_ready"] is True
    assert exchanged["target_validation"]["application_authority"] == "PERFORMANCE_HINT_ONLY"

    target_request = engine.optimization_request_report(_leg(plan, "ortools-cp-sat")["request_id"])["request"]
    applied = engine.apply_solver_learning(
        exchanged["target_artifact"]["learning_id"],
        target_request,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert applied["application"]["application_class"] == "PERFORMANCE_HINT"
    assert applied["application"]["provider_id"] == "ortools-cp-sat"
    hints = applied["request"]["metadata"]["solver_learning_hints"]
    assert hints[0]["provider_id"] == "ortools-cp-sat"
    assert hints[0]["assignment"] == {"x": 1.0, "y": 0.0}
    assert applied["application"]["truth_authority"] == "NONE"


def test_exchange_requires_source_local_pass_validation_before_target_materialization():
    engine, plan = _engine_and_plan()
    artifact, _ = _record_source_artifact(
        engine,
        plan,
        "ortools-cp-sat",
        "NO_GOOD",
        {
            "literals": [
                {"variable_id": "x", "positive": False},
                {"variable_id": "y", "positive": False},
            ]
        },
    )
    before = engine.solver_exchange_report(workspace_id=WORKSPACE, scope_id=SCOPE)["exchanges"]
    assert before == {}
    with pytest.raises(PermissionError, match="local validation Evidence"):
        engine.exchange_solver_learning(
            plan["portfolio_id"],
            "ortools-cp-sat",
            "highs",
            artifact.learning_id,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
        )
    after = engine.solver_exchange_report(workspace_id=WORKSPACE, scope_id=SCOPE)["exchanges"]
    assert after == {}
    target_model_fp = _leg(plan, "highs")["target_model_fingerprint"]
    target_artifacts = [
        row
        for row in engine.solver_learning_report(workspace_id=WORKSPACE, scope_id=SCOPE)["local_artifacts"].values()
        if row["document"]["artifact"]["model_fingerprint"] == target_model_fp
    ]
    assert target_artifacts == []


def test_native_accelerator_state_is_not_cross_solver_portable():
    engine, plan = _engine_and_plan()
    leg = _leg(plan, "ortools-cp-sat")
    support = engine.add_evidence(
        EvidenceRecord(kind="solver_result", statement="native state", source="ortools-cp-sat"),
        reason="native state support",
    )
    artifact = SolverLearningArtifact(
        "NATIVE_ACCELERATOR",
        leg["target_model_fingerprint"],
        leg["target_family"],
        {
            "backend_id": "ortools-cp-sat",
            "backend_version": "fixture-1",
            "state_fingerprint": "state-abc",
        },
        source_evidence_ids=(support.evidence_id,),
        provider_id="ortools-cp-sat",
        provider_version="fixture-1",
    )
    engine.record_solver_learning_artifact(artifact, workspace_id=WORKSPACE, scope_id=SCOPE)
    with pytest.raises(ValueError, match="cannot be exchanged"):
        engine.exchange_solver_learning(
            plan["portfolio_id"],
            "ortools-cp-sat",
            "highs",
            artifact.learning_id,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
        )
