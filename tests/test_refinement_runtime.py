from __future__ import annotations

from copy import deepcopy

import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.reasoning import Claim, ReasoningProducer
from aasm.refinement import (
    RefinementApplicability,
    RefinementApplication,
    RefinementLoopTermination,
    RefinementProposal,
    RefinementSemanticEffect,
    RefinementValidation,
)
from aasm.refinement_runtime import (
    REFINEMENT_APPLICATION_RECORD,
    REFINEMENT_APPLY_CAPABILITY,
    REFINEMENT_DOCUMENT,
    REFINEMENT_RECORD_TYPE,
    RefinementRuntimeMixin,
    refinement_document,
)
from aasm.runtime_v56_foundation import AASMEngine as V56FoundationEngine
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.semantic_dependencies import SemanticNodeRef
from aasm.semantic_evolution import ProblemDelta, ProblemRevision
from aasm.semantic_result import semantic_fingerprint


class RefinementEngine(RefinementRuntimeMixin, V56FoundationEngine):
    pass


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _engine(name: str = "S5.1 refinement runtime") -> RefinementEngine:
    engine = RefinementEngine(ProblemSpec(name))
    trust = engine.add_evidence(EvidenceRecord("observation", "workspace trust anchor", source="test"))
    root = Principal("fabric-root", "SYSTEM")
    engine.bootstrap_scoped_workspace(
        root,
        Workspace("workspace-a", root.principal_id),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "fabric-root",
            "fabric-root",
            "workspace-a",
            "root",
            ("*",),
        )
    )
    engine.register_scoped_principal(
        Principal("controller-c", "SYSTEM"),
        workspace_id="workspace-a",
        actor_principal_id="fabric-root",
    )
    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "controller-c",
            "fabric-root",
            "workspace-a",
            "root",
            (REFINEMENT_APPLY_CAPABILITY,),
        )
    )
    return engine


def _base() -> ProblemRevision:
    return ProblemRevision(
        problem_id="pcb-main",
        problem_fingerprint=_sha("problem-v1"),
        semantic_projection_fingerprint=_sha("projection-v1"),
        dependency_fingerprints=(_sha("dependency-v1"),),
        environment_fingerprint=_sha("environment-v1"),
        created_by="controller-c",
        revision_id="problem-revision-r1",
    )


def _proposal(
    base: ProblemRevision,
    trigger_evidence_id: str,
    *,
    producer: str = "evaluator-a",
    truth_change_roots=(),
) -> RefinementProposal:
    roots = tuple(truth_change_roots)
    effect = RefinementSemanticEffect(
        target_problem_fingerprint=_sha("problem-v2"),
        target_semantic_projection_fingerprint=_sha("projection-v2"),
        truth_change_roots=roots,
        changed_semantic_ids=("semantic-clearance",),
        impacted_obligation_ids=("obligation-reverify-clearance",),
        impacted_solver_object_ids=("solver-routing",),
        incremental_eligibility="INCREMENTAL_CANDIDATE",
        warm_start_eligibility="PERFORMANCE_ONLY_CANDIDATE",
    )
    return RefinementProposal(
        refinement_kind="NEW_CONSTRAINT",
        workspace_id="workspace-a",
        scope_id="root",
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        producer_principal_id=producer,
        trigger_evidence_ids=(trigger_evidence_id,),
        target_semantic_refs=roots,
        proposed_semantic_payload={
            "operation": "tighten_clearance",
            "semantic_id": "semantic-clearance",
        },
        dependency_fingerprints=base.dependency_fingerprints,
        applicability=RefinementApplicability(
            workspace_id="workspace-a",
            scope_id="root",
            problem_revision_id=base.revision_id,
            problem_revision_fingerprint=base.fingerprint,
            subject_ids=("board-a",),
            environment_fingerprints=(_sha("environment-v1"),),
        ),
        expected_semantic_effect=effect,
    )


def _validation(proposal: RefinementProposal, evidence_id: str, *, validator: str = "validator-b") -> RefinementValidation:
    return RefinementValidation(
        proposal_id=proposal.proposal_id,
        proposal_fingerprint=proposal.fingerprint,
        semantic_refinement_fingerprint=proposal.semantic_refinement_fingerprint,
        base_revision_id=proposal.base_revision_id,
        base_revision_fingerprint=proposal.base_revision_fingerprint,
        applicability_fingerprint=proposal.applicability.fingerprint,
        validator_principal_id=validator,
        result="VALID",
        supporting_evidence_ids=(evidence_id,),
        reasoning="independent exact applicability recheck",
    )


def _transition(
    proposal: RefinementProposal,
    base: ProblemRevision,
    *,
    truth_change_roots=(),
) -> tuple[ProblemDelta, ProblemRevision]:
    roots = tuple(truth_change_roots)
    delta = ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint=proposal.expected_semantic_effect.target_problem_fingerprint,
        target_semantic_projection_fingerprint=proposal.expected_semantic_effect.target_semantic_projection_fingerprint,
        truth_change_roots=roots,
        changed_semantic_ids=("semantic-clearance",),
        impacted_obligation_ids=("obligation-reverify-clearance",),
        impacted_solver_object_ids=("solver-routing",),
        incremental_eligibility="INCREMENTAL_CANDIDATE",
        warm_start_eligibility="PERFORMANCE_ONLY_CANDIDATE",
        caused_by_refinement_id=proposal.proposal_id,
    )
    target = ProblemRevision(
        problem_id=base.problem_id,
        problem_fingerprint=delta.target_problem_fingerprint,
        semantic_projection_fingerprint=delta.target_semantic_projection_fingerprint,
        parent_revision_ids=(base.revision_id,),
        dependency_fingerprints=base.dependency_fingerprints,
        environment_fingerprint=base.environment_fingerprint,
        created_by="controller-c",
        created_from_delta_id=delta.delta_id,
        revision_id="problem-revision-r2",
    )
    return delta, target


def _record_ready_refinement(engine: RefinementEngine, *, truth_change_roots=()):
    trigger = engine.add_evidence(EvidenceRecord("observation", "DRC counterexample", source="drc"))
    validation_evidence = engine.add_evidence(
        EvidenceRecord("observation", "independent DRC reproduction", source="independent-drc")
    )
    base = _base()
    engine.register_initial_problem_revision(
        base,
        authority_id="controller-c",
        authority_class="CONTROLLER",
    )
    proposal = _proposal(
        base,
        trigger.evidence_id,
        truth_change_roots=truth_change_roots,
    )
    proposal_record = engine.record_refinement_proposal(proposal)
    validation = _validation(proposal, validation_evidence.evidence_id)
    validation_record = engine.record_refinement_validation(validation)
    delta, target = _transition(
        proposal,
        base,
        truth_change_roots=truth_change_roots,
    )
    return base, proposal, proposal_record, validation, validation_record, delta, target


def test_runtime_contract_reuses_existing_authority_revision_and_truth_planes():
    engine = _engine()
    contract = engine.refinement_runtime_contract_report()
    assert contract["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"
    assert contract["application_authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_DECISION_REQUIRED"
    assert contract["revision_transition"] == "EXISTING_AASM_SEMANTIC_EVOLUTION_RUNTIME_ONLY"
    assert contract["truth_maintenance"] == "EXISTING_AASM_SEMANTIC_DEPENDENCY_RUNTIME_ONLY"
    assert contract["parallel_refinement_store"] == "NONE"
    assert contract["parallel_revision_system"] == "NONE"
    assert contract["parallel_authority_plane"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"


def test_governed_refinement_commits_through_existing_problem_revision_transition():
    engine = _engine()
    base, proposal, _, validation, _, delta, target = _record_ready_refinement(engine)
    applied = engine.apply_refinement(
        proposal_id=proposal.proposal_id,
        validation_id=validation.validation_id,
        delta=delta,
        target_revision=target,
        actor_principal_id="controller-c",
        revision_authority_class="CONTROLLER",
    )
    assert applied["already_applied"] is False
    assert applied["application"]["scoped_authorization_evidence_id"].startswith("scoped-authority-evidence-")
    assert applied["application"]["problem_transition_evidence_id"].startswith("semantic-evolution-evidence-")
    semantic = engine.semantic_evolution_report(base.problem_id)
    assert semantic["heads"] == [target.revision_id]
    assert semantic["pending_impact_delta_ids"] == []
    report = engine.refinement_report()
    assert report["valid"] is True, report["issues"]
    assert report["pending_proposal_ids"] == []
    assert len(report["applications"]) == 1


def test_producer_cannot_apply_its_own_delta_even_before_scoped_authority_is_considered():
    engine = _engine()
    _, proposal, _, validation, _, delta, target = _record_ready_refinement(engine)
    with pytest.raises(PermissionError, match="cannot directly apply"):
        engine.apply_refinement(
            proposal_id=proposal.proposal_id,
            validation_id=validation.validation_id,
            delta=delta,
            target_revision=target,
            actor_principal_id=proposal.producer_principal_id,
            revision_authority_class="CONTROLLER",
        )
    assert engine.semantic_evolution_report()["transitions"] == {}


def test_application_without_existing_scoped_authority_fails_closed_without_revision_mutation():
    engine = _engine()
    _, proposal, _, validation, _, delta, target = _record_ready_refinement(engine)
    with pytest.raises(PermissionError, match="authority denied"):
        engine.apply_refinement(
            proposal_id=proposal.proposal_id,
            validation_id=validation.validation_id,
            delta=delta,
            target_revision=target,
            actor_principal_id="unknown-controller",
            revision_authority_class="CONTROLLER",
        )
    assert engine.semantic_evolution_report()["transitions"] == {}


def test_self_validation_cannot_be_recorded_as_independent_valid_validation():
    engine = _engine()
    trigger = engine.add_evidence(EvidenceRecord("observation", "counterexample", source="test"))
    support = engine.add_evidence(EvidenceRecord("observation", "self recheck", source="test"))
    base = _base()
    engine.register_initial_problem_revision(base, authority_id="controller-c", authority_class="CONTROLLER")
    proposal = _proposal(base, trigger.evidence_id)
    engine.record_refinement_proposal(proposal)
    validation = _validation(
        proposal,
        support.evidence_id,
        validator=proposal.producer_principal_id,
    )
    with pytest.raises(PermissionError, match="independent refinement validation"):
        engine.record_refinement_validation(validation)
    assert engine.refinement_report()["validations"] == {}


def test_exact_application_is_idempotent_but_conflicting_repeat_is_blocked_by_application_key():
    engine = _engine()
    _, proposal, _, validation, _, delta, target = _record_ready_refinement(engine)
    first = engine.apply_refinement(
        proposal_id=proposal.proposal_id,
        validation_id=validation.validation_id,
        delta=delta,
        target_revision=target,
        actor_principal_id="controller-c",
        revision_authority_class="CONTROLLER",
    )
    second = engine.apply_refinement(
        proposal_id=proposal.proposal_id,
        validation_id=validation.validation_id,
        delta=delta,
        target_revision=target,
        actor_principal_id="controller-c",
        revision_authority_class="CONTROLLER",
    )
    assert second["already_applied"] is True
    assert second["application"]["application_id"] == first["application"]["application_id"]

    forged_payload = deepcopy(first["application"])
    forged_payload.pop("fingerprint", None)
    forged_payload["application_id"] = "forged-repeat-application"
    forged = RefinementApplication.from_dict(forged_payload)
    document = {"application": forged.to_dict()}
    engine.add_evidence(
        EvidenceRecord(
            "refinement",
            refinement_document(document),
            source="aasm.refinement.loop.v1",
            metadata={
                REFINEMENT_RECORD_TYPE: REFINEMENT_APPLICATION_RECORD,
                "object_id": forged.application_id,
                REFINEMENT_DOCUMENT: document,
                "authority": "GOVERNANCE_EVIDENCE_ONLY",
            },
        )
    )
    report = engine.refinement_report()
    assert report["valid"] is False
    assert any(
        "DUPLICATE_SEMANTIC_REFINEMENT_APPLICATION" in issue["error"]
        for issue in report["issues"]
    )


def test_truth_changing_refinement_must_complete_existing_truth_maintenance_before_application_record():
    engine = _engine("S5.1 truth maintenance")
    root = Claim("clearance truth root", ReasoningProducer("agent", "PROPOSER"))
    dependent = Claim(
        "dependent routing claim",
        ReasoningProducer("agent", "PROPOSER"),
        premise_artifact_ids=(root.artifact_id,),
    )
    engine.propose_artifact(root)
    engine.propose_artifact(dependent)
    root_ref = SemanticNodeRef("ARTIFACT", root.artifact_id)
    _, proposal, _, validation, _, delta, target = _record_ready_refinement(
        engine,
        truth_change_roots=(root_ref,),
    )
    applied = engine.apply_refinement(
        proposal_id=proposal.proposal_id,
        validation_id=validation.validation_id,
        delta=delta,
        target_revision=target,
        actor_principal_id="controller-c",
        revision_authority_class="CONTROLLER",
    )
    truth_id = applied["application"]["metadata"]["truth_impact_application_evidence_id"]
    assert truth_id.startswith("semantic-evolution-evidence-")
    assert engine.reasoning_report(root.artifact_id)["state"] == "STALE"
    assert engine.reasoning_report(dependent.artifact_id)["state"] == "STALE"
    report = engine.refinement_report()
    row = next(iter(report["applications"].values()))
    assert row["truth_impact_evidence_id"] == truth_id
    assert report["semantic_evolution"]["pending_impact_delta_ids"] == []


def test_loop_termination_is_durable_and_bound_to_current_problem_head():
    engine = _engine()
    base, proposal, _, validation, _, delta, target = _record_ready_refinement(engine)
    engine.apply_refinement(
        proposal_id=proposal.proposal_id,
        validation_id=validation.validation_id,
        delta=delta,
        target_revision=target,
        actor_principal_id="controller-c",
        revision_authority_class="CONTROLLER",
    )
    final = engine.add_evidence(EvidenceRecord("observation", "final verification passed", source="verifier"))
    termination = RefinementLoopTermination(
        problem_id=base.problem_id,
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        head_revision_id=target.revision_id,
        head_revision_fingerprint=target.fingerprint,
        reason="GOAL_SATISFIED",
        evidence_ids=(final.evidence_id,),
        actor_principal_id="controller-c",
    )
    recorded = engine.record_refinement_termination(termination)
    assert recorded["already_recorded"] is False
    report = engine.refinement_report()
    assert report["valid"] is True
    assert report["terminations"][termination.termination_id]["termination"]["is_success"] is True
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
