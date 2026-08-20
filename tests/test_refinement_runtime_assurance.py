from __future__ import annotations

import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
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
    REFINEMENT_PROPOSAL_RECORD,
    REFINEMENT_RECORD_TYPE,
    REFINEMENT_TERMINATION_RECORD,
    refinement_document,
)
from aasm.refinement_runtime_assurance import RefinementRuntimeAssuranceMixin
from aasm.runtime_v56_foundation import AASMEngine as V56FoundationEngine
from aasm.scoped_authority import AuthorityRequest, Principal, ScopedAuthorityGrant, Workspace
from aasm.semantic_evolution import ProblemDelta, ProblemRevision
from aasm.semantic_result import semantic_fingerprint


class AssuredRefinementEngine(RefinementRuntimeAssuranceMixin, V56FoundationEngine):
    pass


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _engine() -> AssuredRefinementEngine:
    engine = AssuredRefinementEngine(ProblemSpec("S5.1 refinement assurance"))
    trust = engine.add_evidence(EvidenceRecord("observation", "workspace trust anchor", source="test"))
    engine.bootstrap_scoped_workspace(
        Principal("fabric-root", "SYSTEM"),
        Workspace("workspace-a", "fabric-root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant("fabric-root", "fabric-root", "workspace-a", "root", ("*",))
    )
    for controller in ("controller-c", "controller-d"):
        engine.register_scoped_principal(
            Principal(controller, "SYSTEM"),
            workspace_id="workspace-a",
            actor_principal_id="fabric-root",
        )
        engine.admit_scoped_authority_grant(
            ScopedAuthorityGrant(
                controller,
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


def _proposal(base: ProblemRevision, trigger_evidence_id: str, *, base_fingerprint: str | None = None) -> RefinementProposal:
    fingerprint = base.fingerprint if base_fingerprint is None else base_fingerprint
    applicability = RefinementApplicability(
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id=base.revision_id,
        problem_revision_fingerprint=fingerprint,
        subject_ids=("board-a",),
        environment_fingerprints=(_sha("environment-v1"),),
    )
    effect = RefinementSemanticEffect(
        target_problem_fingerprint=_sha("problem-v2"),
        target_semantic_projection_fingerprint=_sha("projection-v2"),
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
        base_revision_fingerprint=fingerprint,
        producer_principal_id="evaluator-a",
        trigger_evidence_ids=(trigger_evidence_id,),
        proposed_semantic_payload={"operation": "tighten_clearance"},
        dependency_fingerprints=base.dependency_fingerprints,
        applicability=applicability,
        expected_semantic_effect=effect,
    )


def _validation(proposal: RefinementProposal, support_evidence_id: str) -> RefinementValidation:
    return RefinementValidation(
        proposal_id=proposal.proposal_id,
        proposal_fingerprint=proposal.fingerprint,
        semantic_refinement_fingerprint=proposal.semantic_refinement_fingerprint,
        base_revision_id=proposal.base_revision_id,
        base_revision_fingerprint=proposal.base_revision_fingerprint,
        applicability_fingerprint=proposal.applicability.fingerprint,
        validator_principal_id="validator-b",
        result="VALID",
        supporting_evidence_ids=(support_evidence_id,),
        reasoning="independent reproduction",
    )


def _transition(proposal: RefinementProposal, base: ProblemRevision) -> tuple[ProblemDelta, ProblemRevision]:
    delta = ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint=proposal.expected_semantic_effect.target_problem_fingerprint,
        target_semantic_projection_fingerprint=proposal.expected_semantic_effect.target_semantic_projection_fingerprint,
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


def _ready(engine: AssuredRefinementEngine):
    trigger = engine.add_evidence(EvidenceRecord("observation", "DRC counterexample", source="drc"))
    support = engine.add_evidence(EvidenceRecord("observation", "independent DRC reproduction", source="verifier"))
    base = _base()
    engine.register_initial_problem_revision(base, authority_id="controller-c", authority_class="CONTROLLER")
    proposal = _proposal(base, trigger.evidence_id)
    proposal_row = engine.record_refinement_proposal(proposal)
    validation = _validation(proposal, support.evidence_id)
    validation_row = engine.record_refinement_validation(validation)
    delta, target = _transition(proposal, base)
    return base, proposal, proposal_row, validation, validation_row, support, delta, target


def _add_refinement_record(engine, *, record_type: str, object_id: str, document: dict) -> str:
    record = engine.add_evidence(
        EvidenceRecord(
            "refinement",
            refinement_document(document),
            source="assurance-adversarial-fixture",
            metadata={
                REFINEMENT_RECORD_TYPE: record_type,
                "object_id": object_id,
                REFINEMENT_DOCUMENT: document,
                "authority": "GOVERNANCE_EVIDENCE_ONLY",
            },
        )
    )
    return record.evidence_id


def test_assurance_contract_remains_pre_admission_and_reuses_base_runtime():
    engine = _engine()
    contract = engine.refinement_runtime_assurance_contract_report()
    assert contract["base_runtime"] == "aasm.refinement.runtime.v1"
    assert contract["parallel_store"] == "NONE"
    assert contract["parallel_revision_system"] == "NONE"
    assert contract["parallel_authority_plane"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


def test_forged_proposal_base_fingerprint_is_rejected_by_cross_history_assurance():
    engine = _engine()
    trigger = engine.add_evidence(EvidenceRecord("observation", "counterexample", source="drc"))
    base = _base()
    engine.register_initial_problem_revision(base, authority_id="controller-c", authority_class="CONTROLLER")
    forged = _proposal(base, trigger.evidence_id, base_fingerprint=_sha("forged-base"))
    _add_refinement_record(
        engine,
        record_type=REFINEMENT_PROPOSAL_RECORD,
        object_id=forged.proposal_id,
        document={"proposal": forged.to_dict()},
    )
    report = engine.refinement_report()
    assert report["valid"] is False
    assert any(issue.get("code") == "PROPOSAL_BASE_REVISION_FINGERPRINT_MISMATCH" for issue in report["issues"])


def test_application_actor_must_match_authority_that_committed_canonical_transition():
    engine = _engine()
    _, proposal, proposal_row, validation, validation_row, _, delta, target = _ready(engine)
    committed = engine.commit_problem_revision_transition(
        delta,
        target,
        authority_id="controller-c",
        authority_class="CONTROLLER",
        evidence_ids=[proposal_row["evidence_id"], validation_row["evidence_id"]],
        apply_truth_maintenance=True,
    )
    authorization = engine.authorize_scoped_request(
        AuthorityRequest(
            "controller-d",
            "workspace-a",
            "root",
            REFINEMENT_APPLY_CAPABILITY,
            machine_id=engine.snapshot.machine_id,
        ),
        derived_from=[proposal_row["evidence_id"], validation_row["evidence_id"]],
        reason="adversarial substitute actor authority",
    )
    assert authorization["decision"]["allowed"] is True
    forged = RefinementApplication(
        proposal_id=proposal.proposal_id,
        proposal_fingerprint=proposal.fingerprint,
        validation_id=validation.validation_id,
        validation_fingerprint=validation.fingerprint,
        semantic_refinement_fingerprint=proposal.semantic_refinement_fingerprint,
        base_revision_id=proposal.base_revision_id,
        base_revision_fingerprint=proposal.base_revision_fingerprint,
        delta_id=delta.delta_id,
        delta_fingerprint=delta.fingerprint,
        target_revision_id=target.revision_id,
        target_revision_fingerprint=target.fingerprint,
        producer_principal_id=proposal.producer_principal_id,
        actor_principal_id="controller-d",
        scoped_authorization_evidence_id=authorization["evidence_id"],
        problem_transition_evidence_id=committed["transition_evidence_id"],
        metadata={"truth_impact_application_evidence_id": ""},
    )
    _add_refinement_record(
        engine,
        record_type=REFINEMENT_APPLICATION_RECORD,
        object_id=forged.application_id,
        document={"application": forged.to_dict()},
    )
    report = engine.refinement_report()
    assert report["valid"] is False
    assert any(
        issue.get("code") == "APPLICATION_TRANSITION_AUTHORITY_PRINCIPAL_MISMATCH"
        for issue in report["issues"]
    )


def test_stale_validation_support_cannot_authorize_a_new_revision_transition():
    engine = _engine()
    _, proposal, _, validation, _, support, delta, target = _ready(engine)
    engine.invalidate_evidence(support.evidence_id, "validation observation became stale")
    with pytest.raises(PermissionError, match="STALE_REFINEMENT_VALIDATION_EVIDENCE"):
        engine.apply_refinement(
            proposal_id=proposal.proposal_id,
            validation_id=validation.validation_id,
            delta=delta,
            target_revision=target,
            actor_principal_id="controller-c",
            revision_authority_class="CONTROLLER",
        )
    assert engine.semantic_evolution_report()["transitions"] == {}


def test_stale_validation_does_not_retroactively_erase_exact_committed_retry():
    engine = _engine()
    _, proposal, _, validation, _, support, delta, target = _ready(engine)
    first = engine.apply_refinement(
        proposal_id=proposal.proposal_id,
        validation_id=validation.validation_id,
        delta=delta,
        target_revision=target,
        actor_principal_id="controller-c",
        revision_authority_class="CONTROLLER",
    )
    engine.invalidate_evidence(support.evidence_id, "later superseded measurement")
    retry = engine.apply_refinement(
        proposal_id=proposal.proposal_id,
        validation_id=validation.validation_id,
        delta=delta,
        target_revision=target,
        actor_principal_id="controller-c",
        revision_authority_class="CONTROLLER",
    )
    assert retry["already_applied"] is True
    assert retry["application"]["application_id"] == first["application"]["application_id"]


def test_termination_fingerprints_must_match_canonical_revision_history():
    engine = _engine()
    base, proposal, _, validation, _, _, delta, target = _ready(engine)
    engine.apply_refinement(
        proposal_id=proposal.proposal_id,
        validation_id=validation.validation_id,
        delta=delta,
        target_revision=target,
        actor_principal_id="controller-c",
        revision_authority_class="CONTROLLER",
    )
    final = engine.add_evidence(EvidenceRecord("observation", "verification passed", source="verifier"))
    forged = RefinementLoopTermination(
        problem_id=base.problem_id,
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        head_revision_id=target.revision_id,
        head_revision_fingerprint=_sha("forged-head"),
        reason="GOAL_SATISFIED",
        evidence_ids=(final.evidence_id,),
        actor_principal_id="controller-c",
    )
    _add_refinement_record(
        engine,
        record_type=REFINEMENT_TERMINATION_RECORD,
        object_id=forged.termination_id,
        document={"termination": forged.to_dict()},
    )
    report = engine.refinement_report()
    assert report["valid"] is False
    assert any(issue.get("code") == "TERMINATION_HEAD_REVISION_FINGERPRINT_MISMATCH" for issue in report["issues"])
