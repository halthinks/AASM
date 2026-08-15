from aasm.cross_run_knowledge import CrossRunKnowledgeEnvelope
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.optimization import (
    OptimizationConstraint,
    OptimizationModel,
    OptimizationObjective,
    OptimizationRequest,
    OptimizationVariable,
)
from aasm.runtime_v53_learning import AASMEngine, SOLVER_LEARNING_APPLY_CAPABILITY
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.solver_learning import SolverLearningArtifact
from aasm._runtime_v53_solver_learning import SOLVER_LEARNING_AUTHORITY_CAPABILITIES


def fixture_model():
    return OptimizationModel(
        "cross-run-learning",
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


def bootstrapped_engine(name, *capabilities):
    engine = AASMEngine(ProblemSpec(name))
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement=f"{name} root", source="fixture"),
        reason="fixture trust root",
    )
    engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace("workspace-a", "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    if capabilities:
        engine.admit_scoped_authority_grant(
            ScopedAuthorityGrant(
                "root",
                "root",
                "workspace-a",
                "root",
                tuple(capabilities),
                delegable=True,
                remaining_delegation_depth=4,
            )
        )
    return engine


def admit_v48_envelope(target, envelope):
    proposed = target.propose_cross_run_admission(
        envelope,
        proposer_id="solver-learning-importer",
        target_scope_id="root",
    )
    decision_id = proposed["decision"]["decision_id"]
    assert proposed["decision"]["status"] == "PROPOSED"
    authorized = target.authorize_cross_run_admission(
        decision_id,
        authority_id="policy",
        authority_class="POLICY",
    )
    assert authorized["decision"]["status"] == "ACTIVE"
    committed = target.commit_cross_run_admission(
        decision_id,
        worker_id="solver-learning-admission-worker",
    )
    assert committed["entry"]["status"] == "ACTIVE"
    assert committed["entry"]["envelope"]["envelope_id"] == envelope.envelope_id
    return committed


def source_no_good(source, model, *, forged=False):
    support = source.add_evidence(
        EvidenceRecord(kind="solver_result", statement="source solver observation", source="fixture-solver"),
        reason="fixture solver evidence",
    )
    literals = (
        [{"variable_id": "x", "positive": True}, {"variable_id": "y", "positive": False}]
        if forged
        else [{"variable_id": "x", "positive": False}, {"variable_id": "y", "positive": False}]
    )
    artifact = SolverLearningArtifact(
        "NO_GOOD",
        model.fingerprint,
        model.solver_family,
        {"literals": literals},
        source_result_fingerprint="source-result",
        source_evidence_ids=(support.evidence_id,),
    )
    recorded = source.record_solver_learning_artifact(
        artifact,
        workspace_id="workspace-a",
        scope_id="root",
    )
    return artifact, recorded


def exported_no_good(model):
    source = bootstrapped_engine("source", SOLVER_LEARNING_AUTHORITY_CAPABILITIES["export"])
    artifact, recorded = source_no_good(source, model)
    exported = source.export_solver_learning_artifact(
        artifact.learning_id,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    return source, artifact, recorded, CrossRunKnowledgeEnvelope.from_dict(exported["envelope"])


def test_cross_run_solver_learning_reuses_v48_transport_and_stays_inert_until_local_validation():
    model = fixture_model()
    source, artifact, recorded, envelope = exported_no_good(model)
    assert envelope.knowledge_kind == "REUSE_RESULT"
    assert envelope.metadata["solver_learning_contract_id"] == "aasm.solver.learning.v1"
    assert envelope.metadata["solver_learning_contract_version"] == "0.1.0"
    assert envelope.metadata["authority_inherited"] is False
    assert envelope.source_authority_provenance["authority_transfer"] == "NEVER"
    assert recorded["evidence_id"] in envelope.source_evidence_ids
    assert envelope.source_fingerprints[f"SOLVER_LEARNING:{artifact.learning_id}"] == artifact.fingerprint

    target = bootstrapped_engine(
        "target",
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["import"],
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["validate"],
    )
    admission = admit_v48_envelope(target, envelope)
    imported = target.admit_cross_run_solver_learning(
        envelope.envelope_id,
        expected_model_fingerprint=model.fingerprint,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert imported["activation_status"] == "REVALIDATION_REQUIRED"
    assert imported["authority_inherited"] is False
    assert target.solver_learning_report(workspace_id="workspace-a", scope_id="root")["validations"] == {}

    imported_evidence = next(
        row for row in target.snapshot.evidence["records"] if row["evidence_id"] == imported["evidence_id"]
    )
    assert admission["admission_evidence_id"] in imported_evidence["derived_from"]

    validated = target.revalidate_solver_learning(
        artifact.learning_id,
        model,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert validated["validation"]["status"] == "PASS"
    assert validated["validation"]["application_authority"] == "PRUNING_CERTIFIED_FOR_EXACT_MODEL"
    assert target.solver_learning_report(workspace_id="workspace-a", scope_id="root")["applications"] == {}
    assert target.replay().canonical_hash() == target.snapshot.canonical_hash()


def test_cross_run_solver_learning_cannot_materialize_before_v48_admission_commits():
    model = fixture_model()
    _source, artifact, _recorded, envelope = exported_no_good(model)
    target = bootstrapped_engine("target", SOLVER_LEARNING_AUTHORITY_CAPABILITIES["import"])
    try:
        target.admit_cross_run_solver_learning(
            envelope.envelope_id,
            expected_model_fingerprint=model.fingerprint,
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
    except KeyError as exc:
        assert "no committed v0.48 admission" in str(exc)
    else:
        raise AssertionError("solver learning imported without v0.48 admission")
    assert target.solver_learning_report(workspace_id="workspace-a", scope_id="root")["imported_artifacts"] == {}


def test_cross_run_import_requires_local_scoped_import_authority_after_v48_admission():
    model = fixture_model()
    _source, artifact, _recorded, envelope = exported_no_good(model)
    target = bootstrapped_engine("target")
    admit_v48_envelope(target, envelope)
    try:
        target.admit_cross_run_solver_learning(
            envelope.envelope_id,
            expected_model_fingerprint=model.fingerprint,
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
    except PermissionError as exc:
        assert "solver.learning.import" in str(exc)
    else:
        raise AssertionError("solver learning imported without scoped import authority")
    assert target.solver_learning_report(workspace_id="workspace-a", scope_id="root")["imported_artifacts"] == {}
    authority = target.scoped_authority_report(workspace_id="workspace-a")
    assert any(row["decision"]["reason"] == "NO_APPLICABLE_GRANT" for row in authority["decisions"].values())


def test_forged_cross_run_no_good_may_be_admitted_as_evidence_but_local_revalidation_fails():
    model = fixture_model()
    source = bootstrapped_engine("source", SOLVER_LEARNING_AUTHORITY_CAPABILITIES["export"])
    artifact, _ = source_no_good(source, model, forged=True)
    envelope = CrossRunKnowledgeEnvelope.from_dict(
        source.export_solver_learning_artifact(
            artifact.learning_id,
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )["envelope"]
    )
    target = bootstrapped_engine(
        "target",
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["import"],
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["validate"],
    )
    admit_v48_envelope(target, envelope)
    imported = target.admit_cross_run_solver_learning(
        envelope.envelope_id,
        expected_model_fingerprint=model.fingerprint,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert imported["activation_status"] == "REVALIDATION_REQUIRED"
    checked = target.revalidate_solver_learning(
        artifact.learning_id,
        model,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert checked["validation"]["status"] == "FAIL"
    assert checked["validation"]["application_authority"] == "NONE"
    assert "LEARNED_PRUNING_WOULD_EXCLUDE_FEASIBLE_SOLUTIONS" in checked["validation"]["diagnostics"]


def test_performance_hint_import_never_becomes_truth_authority():
    model = fixture_model()
    source = bootstrapped_engine("source", SOLVER_LEARNING_AUTHORITY_CAPABILITIES["export"])
    support = source.add_evidence(
        EvidenceRecord(kind="solver_result", statement="incumbent", source="fixture-solver"),
        reason="fixture incumbent evidence",
    )
    artifact = SolverLearningArtifact(
        "INCUMBENT",
        model.fingerprint,
        model.solver_family,
        {"assignment": {"x": 1, "y": 0}, "objective": 1},
        source_evidence_ids=(support.evidence_id,),
    )
    source.record_solver_learning_artifact(artifact, workspace_id="workspace-a", scope_id="root")
    envelope = CrossRunKnowledgeEnvelope.from_dict(
        source.export_solver_learning_artifact(
            artifact.learning_id,
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )["envelope"]
    )
    target = bootstrapped_engine(
        "target",
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["import"],
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["validate"],
    )
    admit_v48_envelope(target, envelope)
    imported = target.admit_cross_run_solver_learning(
        envelope.envelope_id,
        expected_model_fingerprint=model.fingerprint,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert imported["activation_status"] == "PERFORMANCE_HINT_PENDING_LOCAL_VALIDATION"
    checked = target.revalidate_solver_learning(
        artifact.learning_id,
        model,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert checked["validation"]["status"] == "PASS"
    assert checked["validation"]["application_authority"] == "PERFORMANCE_HINT_ONLY"
    assert checked["validation"]["details"]["truth_authority"] == "NONE"


def test_validated_learning_remains_inert_without_scoped_apply_authority():
    model = fixture_model()
    _source, artifact, _recorded, envelope = exported_no_good(model)
    target = bootstrapped_engine(
        "target",
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["import"],
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["validate"],
    )
    admit_v48_envelope(target, envelope)
    target.admit_cross_run_solver_learning(
        envelope.envelope_id,
        expected_model_fingerprint=model.fingerprint,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    target.revalidate_solver_learning(
        artifact.learning_id,
        model,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    request = OptimizationRequest(
        model,
        "solver.cp_sat",
        "0.1.0",
        "learning-apply-denied",
        required_provider="ortools-cp-sat",
    )
    try:
        target.apply_solver_learning(
            artifact.learning_id,
            request,
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
    except PermissionError as exc:
        assert SOLVER_LEARNING_APPLY_CAPABILITY in str(exc)
    else:
        raise AssertionError("validated solver learning applied without scoped apply authority")
    report = target.solver_learning_report(workspace_id="workspace-a", scope_id="root")
    assert report["applications"] == {}
    assert any(
        row["decision"]["reason"] == "NO_APPLICABLE_GRANT"
        for row in target.scoped_authority_report(workspace_id="workspace-a")["decisions"].values()
    )


def test_scoped_apply_builds_durable_existing_path_request_without_executing():
    model = fixture_model()
    _source, artifact, _recorded, envelope = exported_no_good(model)
    target = bootstrapped_engine(
        "target",
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["import"],
        SOLVER_LEARNING_AUTHORITY_CAPABILITIES["validate"],
        SOLVER_LEARNING_APPLY_CAPABILITY,
    )
    admit_v48_envelope(target, envelope)
    imported = target.admit_cross_run_solver_learning(
        envelope.envelope_id,
        expected_model_fingerprint=model.fingerprint,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    validated = target.revalidate_solver_learning(
        artifact.learning_id,
        model,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    request = OptimizationRequest(
        model,
        "solver.cp_sat",
        "0.1.0",
        "learning-apply",
        required_provider="ortools-cp-sat",
    )
    applied = target.apply_solver_learning(
        artifact.learning_id,
        request,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert applied["executed"] is False
    assert applied["application"]["application_class"] == "PRUNING_CONSTRAINTS"
    assert applied["application"]["truth_authority"] == "NONE"
    assert applied["application"]["policy_authority"] == "NONE"
    assert applied["request"]["model"]["fingerprint"] != model.fingerprint
    assert applied["request"]["metadata"]["solver_learning_original_model_fingerprint"] == model.fingerprint
    assert applied["request"]["metadata"]["solver_learning_truth_authority"] == "NONE"

    evidence = next(
        row for row in target.snapshot.evidence["records"] if row["evidence_id"] == applied["evidence_id"]
    )
    assert imported["evidence_id"] in evidence["derived_from"]
    assert validated["evidence_id"] in evidence["derived_from"]
    assert applied["authority_decision_evidence_id"] in evidence["derived_from"]
    report = target.solver_learning_report(workspace_id="workspace-a", scope_id="root")
    assert len(report["applications"]) == 1
    assert report["authority_capabilities"]["apply"] == SOLVER_LEARNING_APPLY_CAPABILITY
    assert report["application_contract"]["solver_execution"] if "solver_execution" in report["application_contract"] else True
    assert target.replay().canonical_hash() == target.snapshot.canonical_hash()
