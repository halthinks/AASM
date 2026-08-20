from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm.refinement import (
    REFINEMENT_BLOCKING_TERMINATIONS,
    REFINEMENT_KINDS,
    REFINEMENT_LOOP_CONTRACT_ID,
    REFINEMENT_PROPOSAL_CONTRACT_ID,
    REFINEMENT_TERMINATION_REASONS,
    REFINEMENT_VALIDATION_RESULTS,
    RefinementApplicability,
    RefinementApplication,
    RefinementLoopTermination,
    RefinementProposal,
    RefinementResourceEstimate,
    RefinementSemanticEffect,
    RefinementValidation,
    refinement_application_key,
    refinement_contract,
    validate_refinement_application,
    validate_refinement_delta,
    validate_refinement_validation,
)
from aasm.semantic_dependencies import SemanticNodeRef
from aasm.semantic_evolution import ExternalReference, ProblemDelta, ProblemRevision
from aasm.semantic_result import semantic_fingerprint


ROOT = Path(__file__).resolve().parents[1]


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _base_revision(*, dependency_fingerprints: tuple[str, ...] | None = None) -> ProblemRevision:
    deps = dependency_fingerprints if dependency_fingerprints is not None else (_sha("dep-a"),)
    return ProblemRevision(
        problem_id="pcb-main",
        problem_fingerprint=_sha("problem-v1"),
        semantic_projection_fingerprint=_sha("projection-v1"),
        dependency_fingerprints=deps,
        environment_fingerprint=_sha("env-a"),
        created_by="controller-a",
        revision_id="problem-revision-base",
    )


def _added_ref() -> ExternalReference:
    return ExternalReference(
        namespace="textpcb",
        external_id="constraint/clearance",
        role="CONSTRAINT_SOURCE",
        revision="r2",
        source_fingerprint=_sha("source-clearance-r2"),
        semantic_entity_id="rule-clearance",
    )


def _effect(ref: ExternalReference | None = None) -> RefinementSemanticEffect:
    row = ref or _added_ref()
    return RefinementSemanticEffect(
        target_problem_fingerprint=_sha("problem-v2"),
        target_semantic_projection_fingerprint=_sha("projection-v2"),
        added_external_reference_fingerprints=(row.fingerprint,),
        truth_change_roots=(SemanticNodeRef("RULE", "clearance"),),
        changed_rule_ids=("rule-clearance",),
        invalidated_evidence_ids=("evidence-old-clearance",),
        impacted_obligation_ids=("obligation-reverify-clearance",),
        impacted_solver_object_ids=("solver-object-routing",),
        incremental_eligibility="INCREMENTAL_CANDIDATE",
        warm_start_eligibility="PERFORMANCE_ONLY_CANDIDATE",
    )


def _proposal(
    *,
    base: ProblemRevision | None = None,
    producer: str = "evaluator-a",
    trigger_evidence_ids: tuple[str, ...] = ("evidence-drc-failure",),
    resource_amount: str = "2.5",
    dependency_fingerprints: tuple[str, ...] | None = None,
    applicability: RefinementApplicability | None = None,
    metadata: dict | None = None,
) -> RefinementProposal:
    source = base or _base_revision()
    ref = _added_ref()
    app = applicability or RefinementApplicability(
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id=source.revision_id,
        problem_revision_fingerprint=source.fingerprint,
        subject_ids=("board-a",),
        environment_fingerprints=(_sha("env-a"),),
        external_reference_fingerprints=(ref.fingerprint,),
    )
    deps = dependency_fingerprints if dependency_fingerprints is not None else source.dependency_fingerprints
    return RefinementProposal(
        refinement_kind="NEW_CONSTRAINT",
        workspace_id="workspace-a",
        scope_id="root",
        base_revision_id=source.revision_id,
        base_revision_fingerprint=source.fingerprint,
        producer_principal_id=producer,
        trigger_evidence_ids=trigger_evidence_ids,
        trigger_reasoning_artifact_ids=("reasoning-drc-1",),
        trigger_conflict_ids=("conflict-clearance-1",),
        target_semantic_refs=(SemanticNodeRef("RULE", "clearance"),),
        target_external_refs=(ref,),
        proposed_semantic_payload={
            "operation": "raise_minimum_clearance",
            "rule_id": "rule-clearance",
            "reason": "verified DRC counterexample",
        },
        dependency_fingerprints=deps,
        independent_validation_required=True,
        applicability=app,
        expected_semantic_effect=_effect(ref),
        resource_estimates=(
            RefinementResourceEstimate(
                resource_kind="solver_budget",
                amount=resource_amount,
                unit="solver_call",
                resource_id="routing-verifier",
            ),
        ),
        metadata={} if metadata is None else metadata,
    )


def _delta(proposal: RefinementProposal, base: ProblemRevision, *, extra_rule: bool = False, caused_by: str | None = None) -> ProblemDelta:
    ref = _added_ref()
    rules = ("rule-clearance", "rule-extra") if extra_rule else ("rule-clearance",)
    return ProblemDelta(
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        target_problem_fingerprint=proposal.expected_semantic_effect.target_problem_fingerprint,
        target_semantic_projection_fingerprint=proposal.expected_semantic_effect.target_semantic_projection_fingerprint,
        added_external_references=(ref,),
        truth_change_roots=(SemanticNodeRef("RULE", "clearance"),),
        changed_rule_ids=rules,
        invalidated_evidence_ids=("evidence-old-clearance",),
        impacted_obligation_ids=("obligation-reverify-clearance",),
        impacted_solver_object_ids=("solver-object-routing",),
        incremental_eligibility="INCREMENTAL_CANDIDATE",
        warm_start_eligibility="PERFORMANCE_ONLY_CANDIDATE",
        caused_by_refinement_id=proposal.proposal_id if caused_by is None else caused_by,
    )


def _target(delta: ProblemDelta, base: ProblemRevision) -> ProblemRevision:
    return ProblemRevision(
        problem_id=base.problem_id,
        problem_fingerprint=delta.target_problem_fingerprint,
        semantic_projection_fingerprint=delta.target_semantic_projection_fingerprint,
        parent_revision_ids=(base.revision_id,),
        dependency_fingerprints=base.dependency_fingerprints,
        environment_fingerprint=base.environment_fingerprint,
        created_by="controller-b",
        created_from_delta_id=delta.delta_id,
        revision_id="problem-revision-target",
    )


def _validation(proposal: RefinementProposal, *, validator: str = "validator-b", result: str = "VALID") -> RefinementValidation:
    evidence = ("evidence-independent-recheck",) if result == "VALID" else ("evidence-validation",)
    return RefinementValidation(
        proposal_id=proposal.proposal_id,
        proposal_fingerprint=proposal.fingerprint,
        semantic_refinement_fingerprint=proposal.semantic_refinement_fingerprint,
        base_revision_id=proposal.base_revision_id,
        base_revision_fingerprint=proposal.base_revision_fingerprint,
        applicability_fingerprint=proposal.applicability.fingerprint,
        validator_principal_id=validator,
        result=result,
        supporting_evidence_ids=evidence,
        reasoning="independent recheck of the proposed semantic effect",
    )


def _application(
    proposal: RefinementProposal,
    validation: RefinementValidation,
    delta: ProblemDelta,
    target: ProblemRevision,
    *,
    actor: str = "controller-c",
) -> RefinementApplication:
    return RefinementApplication(
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
        actor_principal_id=actor,
        scoped_authorization_evidence_id="evidence-refinement-apply-authority",
        problem_transition_evidence_id="semantic-evolution-evidence-transition",
    )


def test_refinement_vocabularies_and_contract_are_exact():
    contract = refinement_contract()
    assert contract["proposal_contract_id"] == REFINEMENT_PROPOSAL_CONTRACT_ID == "aasm.refinement.proposal.v1"
    assert contract["loop_contract_id"] == REFINEMENT_LOOP_CONTRACT_ID == "aasm.refinement.loop.v1"
    assert REFINEMENT_KINDS == (
        "NO_GOOD",
        "BOUND_TIGHTENING",
        "NEW_CONSTRAINT",
        "DOMAIN_RESTRICTION",
        "OBJECTIVE_CORRECTION",
        "REQUIRED_OBSERVATION",
        "VERIFICATION_ESCALATION",
        "MODEL_CORRECTION",
        "SCENARIO_ADDITION",
        "RULE_APPLICABILITY_CORRECTION",
    )
    assert REFINEMENT_VALIDATION_RESULTS == ("VALID", "INVALID", "INCONCLUSIVE")
    assert REFINEMENT_TERMINATION_REASONS == (
        "GOAL_SATISFIED",
        "NO_PROGRESS",
        "OSCILLATION",
        "RESOURCE_EXHAUSTED",
        "INCONCLUSIVE",
        "CONFLICT",
        "MANUAL_HOLD",
    )
    assert REFINEMENT_BLOCKING_TERMINATIONS == ("NO_PROGRESS", "OSCILLATION")
    assert contract["parallel_refinement_store"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert contract["parallel_problem_revision_system"] == "NONE"
    assert contract["parallel_authority_evaluator"] == "NONE"
    assert contract["parallel_resource_plane"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["resource_exhaustion_means_success"] is False
    assert contract["inconclusive_means_success"] is False
    assert contract["goal_satisfied_termination_mints_truth"] is False


def test_refinement_proposal_identity_is_deterministic_and_round_trips():
    first = _proposal()
    second = _proposal()
    assert first.proposal_id == second.proposal_id
    assert first.fingerprint == second.fingerprint
    assert first.semantic_refinement_fingerprint == second.semantic_refinement_fingerprint
    restored = RefinementProposal.from_dict(first.to_dict())
    assert restored == first
    assert restored.to_dict() == first.to_dict()


def test_semantic_refinement_identity_ignores_producer_trigger_and_resource_estimate():
    first = _proposal(producer="evaluator-a", trigger_evidence_ids=("evidence-a",), resource_amount="2.5")
    second = _proposal(producer="evaluator-b", trigger_evidence_ids=("evidence-b",), resource_amount="9")
    assert first.semantic_refinement_fingerprint == second.semantic_refinement_fingerprint
    assert refinement_application_key(first) == refinement_application_key(second)
    assert first.fingerprint != second.fingerprint


def test_binary_float_payload_metadata_and_resource_estimate_fail_closed():
    with pytest.raises(TypeError, match="binary floating-point resource estimates"):
        RefinementResourceEstimate("solver_budget", 1.25, "solver_call")
    with pytest.raises(TypeError, match="binary floating-point"):
        _proposal(metadata={"score": 0.5})
    base = _base_revision()
    with pytest.raises(TypeError, match="binary floating-point"):
        RefinementProposal(
            refinement_kind="NEW_CONSTRAINT",
            workspace_id="workspace-a",
            scope_id="root",
            base_revision_id=base.revision_id,
            base_revision_fingerprint=base.fingerprint,
            producer_principal_id="evaluator-a",
            trigger_evidence_ids=("evidence-a",),
            applicability=RefinementApplicability("workspace-a", "root", base.revision_id, base.fingerprint),
            expected_semantic_effect=RefinementSemanticEffect(_sha("p2"), _sha("s2")),
            proposed_semantic_payload={"binary_float": 1.5},
        )


def test_applicability_must_bind_exact_base_revision():
    base = _base_revision()
    wrong = RefinementApplicability(
        workspace_id="workspace-a",
        scope_id="root",
        problem_revision_id="problem-revision-other",
        problem_revision_fingerprint=_sha("wrong-revision"),
    )
    with pytest.raises(ValueError, match="applicability revision ID"):
        _proposal(base=base, applicability=wrong)


def test_independent_validation_rejects_producer_self_validation():
    proposal = _proposal()
    validation = _validation(proposal, validator=proposal.producer_principal_id)
    result = validate_refinement_validation(proposal, validation)
    assert result["valid"] is False
    assert result["application_eligible"] is False
    assert "INDEPENDENT_VALIDATOR_REQUIRED" in result["errors"]


def test_valid_validation_is_exact_and_application_eligible():
    proposal = _proposal()
    validation = _validation(proposal)
    result = validate_refinement_validation(proposal, validation)
    assert result["valid"] is True
    assert result["application_eligible"] is True
    assert result["errors"] == []


def test_validation_fingerprint_tampering_fails_closed():
    proposal = _proposal()
    value = _validation(proposal).to_dict()
    value["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        RefinementValidation.from_dict(value)


def test_exact_refinement_delta_matches_existing_problem_delta_contract():
    base = _base_revision()
    proposal = _proposal(base=base)
    delta = _delta(proposal, base)
    result = validate_refinement_delta(proposal, base, delta)
    assert result["valid"] is True
    assert result["errors"] == []


def test_delta_cannot_widen_expected_semantic_effect():
    base = _base_revision()
    proposal = _proposal(base=base)
    delta = _delta(proposal, base, extra_rule=True)
    result = validate_refinement_delta(proposal, base, delta)
    assert result["valid"] is False
    assert "DELTA_CHANGED_RULE_IDS_MISMATCH" in result["errors"]


def test_delta_requires_exact_caused_by_refinement_lineage():
    base = _base_revision()
    proposal = _proposal(base=base)
    delta = _delta(proposal, base, caused_by="other-refinement")
    result = validate_refinement_delta(proposal, base, delta)
    assert result["valid"] is False
    assert "DELTA_REFINEMENT_LINEAGE_MISMATCH" in result["errors"]


def test_stale_or_wrong_base_revision_fails_closed():
    base = _base_revision()
    proposal = _proposal(base=base)
    delta = _delta(proposal, base)
    other = ProblemRevision(
        problem_id=base.problem_id,
        problem_fingerprint=base.problem_fingerprint,
        semantic_projection_fingerprint=base.semantic_projection_fingerprint,
        dependency_fingerprints=base.dependency_fingerprints,
        created_by="controller-other",
        revision_id="problem-revision-other",
    )
    result = validate_refinement_delta(proposal, other, delta)
    assert result["valid"] is False
    assert "PROPOSAL_BASE_REVISION_ID_MISMATCH" in result["errors"]
    assert "DELTA_BASE_REVISION_ID_MISMATCH" in result["errors"]


def test_refinement_dependencies_must_be_applicable_to_base_revision():
    base = _base_revision()
    proposal = _proposal(base=base, dependency_fingerprints=(_sha("dep-not-on-base"),))
    delta = _delta(proposal, base)
    result = validate_refinement_delta(proposal, base, delta)
    assert result["valid"] is False
    assert "REFINEMENT_DEPENDENCY_NOT_APPLICABLE_TO_BASE" in result["errors"]


@pytest.mark.parametrize("reason", REFINEMENT_BLOCKING_TERMINATIONS)
def test_no_progress_and_oscillation_require_existing_blocking_obligation(reason):
    base = _base_revision()
    with pytest.raises(ValueError, match="blocking obligation"):
        RefinementLoopTermination(
            problem_id=base.problem_id,
            base_revision_id=base.revision_id,
            base_revision_fingerprint=base.fingerprint,
            head_revision_id=base.revision_id,
            head_revision_fingerprint=base.fingerprint,
            reason=reason,
            evidence_ids=("evidence-loop-analysis",),
            actor_principal_id="controller-a",
        )
    row = RefinementLoopTermination(
        problem_id=base.problem_id,
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        head_revision_id=base.revision_id,
        head_revision_fingerprint=base.fingerprint,
        reason=reason,
        evidence_ids=("evidence-loop-analysis",),
        actor_principal_id="controller-a",
        blocking_obligation_ids=("obligation-human-review",),
    )
    assert row.is_success is False


def test_resource_exhausted_and_inconclusive_are_explicit_non_success_terminations():
    base = _base_revision()
    for reason in ("RESOURCE_EXHAUSTED", "INCONCLUSIVE"):
        row = RefinementLoopTermination(
            problem_id=base.problem_id,
            base_revision_id=base.revision_id,
            base_revision_fingerprint=base.fingerprint,
            head_revision_id=base.revision_id,
            head_revision_fingerprint=base.fingerprint,
            reason=reason,
            evidence_ids=("evidence-termination",),
            actor_principal_id="controller-a",
        )
        assert row.is_success is False


def test_application_record_is_provenance_not_authority():
    base = _base_revision()
    proposal = _proposal(base=base)
    validation = _validation(proposal)
    delta = _delta(proposal, base)
    target = _target(delta, base)
    app = _application(proposal, validation, delta, target)
    result = validate_refinement_application(proposal, validation, app, delta, target)
    assert result["valid"] is True
    assert result["application_key"] == refinement_application_key(proposal)
    contract = refinement_contract()
    assert contract["application_record_grants_fact_authority"] is False
    assert contract["application_record_grants_effect_authority"] is False
    assert contract["validation_is_reusable_authorization_token"] is False
    with pytest.raises(PermissionError, match="cannot directly apply"):
        _application(proposal, validation, delta, target, actor=proposal.producer_principal_id)


def test_refinement_schemas_are_closed_and_accept_canonical_documents():
    proposal_schema = json.loads((ROOT / "schemas/refinement-proposal.schema.json").read_text(encoding="utf-8"))
    loop_schema = json.loads((ROOT / "schemas/refinement-loop.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(proposal_schema)
    Draft202012Validator.check_schema(loop_schema)

    base = _base_revision()
    proposal = _proposal(base=base)
    validation = _validation(proposal)
    delta = _delta(proposal, base)
    target = _target(delta, base)
    application = _application(proposal, validation, delta, target)
    termination = RefinementLoopTermination(
        problem_id=base.problem_id,
        base_revision_id=base.revision_id,
        base_revision_fingerprint=base.fingerprint,
        head_revision_id=target.revision_id,
        head_revision_fingerprint=target.fingerprint,
        reason="GOAL_SATISFIED",
        evidence_ids=("evidence-final-verification",),
        actor_principal_id="controller-c",
    )

    Draft202012Validator(proposal_schema).validate(proposal.to_dict())
    validator = Draft202012Validator(loop_schema)
    validator.validate(validation.to_dict())
    validator.validate(application.to_dict())
    validator.validate(termination.to_dict())


def test_proposal_schema_rejects_unknown_fields():
    schema = json.loads((ROOT / "schemas/refinement-proposal.schema.json").read_text(encoding="utf-8"))
    proposal = _proposal().to_dict()
    proposal["hidden_authority"] = "allow"
    errors = list(Draft202012Validator(schema).iter_errors(proposal))
    assert errors
    assert any("Additional properties are not allowed" in error.message for error in errors)
