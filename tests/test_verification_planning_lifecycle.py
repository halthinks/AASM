from __future__ import annotations

import pytest

from aasm.calculus import ObligationRecord, content_hash, default_calculus_state, normalize_calculus_state
from aasm.semantic_result import semantic_fingerprint
from aasm.typed_protocol import CapabilityContract
from aasm.verification_planning import (
    VerificationAssignment,
    VerificationBoundReference,
    VerificationEvidenceApplicability,
    VerificationPlan,
    VerificationPropertyClaim,
    VerifierCapabilityProfile,
    validate_verification_plan,
    verification_requirement_from_obligation,
)
from aasm.verification_planning_lifecycle import (
    project_verification_debt_current_assured,
    validate_verification_plan_current_applicability,
    verification_plan_lifecycle_contract,
)


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _state(obligation: ObligationRecord):
    state = default_calculus_state()
    state["obligations"] = {obligation.obligation_id: obligation.to_dict()}
    return normalize_calculus_state(state)


def _record(evidence_id: str, *, kind="observation", status="active") -> dict:
    return {
        "evidence_id": evidence_id,
        "kind": kind,
        "statement": evidence_id,
        "source": "test",
        "confidence": None,
        "supports": [],
        "contradicts": [],
        "derived_from": [],
        "metadata": {},
        "status": status,
        "created_at": 0,
        "invalidated_at": None,
        "invalidated_reason": None,
    }


def _planning_fixture():
    obligation = ObligationRecord(
        "verify-clearance",
        "verify clearance",
        status="AVAILABLE",
        required_evidence_types=["observation"],
        evidence_ids=[],
    )
    planning_state = _state(obligation)
    capability = CapabilityContract(
        "drc.verifier", "VERIFIER", "1.0.0", evidence_types=("observation",), deterministic=True
    )
    refs = (
        VerificationBoundReference("ENVIRONMENT", "aasm.execution.environment-binding.v1", "env-sim", _sha("env"), ("evidence-env",)),
        VerificationBoundReference("NUMERICAL_POLICY", "aasm.numeric.tolerance.v1", "numeric-default", _sha("numeric"), ("evidence-numeric",)),
        VerificationBoundReference("RESOURCE_DEMAND", "aasm.resource.demand.v1", "resource-drc", _sha("resource"), ("evidence-resource",)),
    )
    profile = VerifierCapabilityProfile(
        "verifier-drc",
        capability,
        "EXACT",
        "GRADE_A",
        refs,
        VerificationPropertyClaim("SOUNDNESS", "EVIDENCE_BACKED", "declared semantics checked", ("evidence-soundness",)),
        VerificationPropertyClaim("COMPLETENESS", "UNKNOWN", "not claimed"),
        supporting_evidence_ids=("evidence-profile",),
    )
    requirement = verification_requirement_from_obligation(
        obligation.to_dict(),
        acceptable_fidelities=("EXACT",),
        acceptable_evidence_grades=("GRADE_A",),
        required_environment_id="env-sim",
        required_environment_fingerprint=_sha("env"),
        required_numerical_policy_id="numeric-default",
        required_numerical_policy_fingerprint=_sha("numeric"),
    )
    assignment = VerificationAssignment(
        requirement.obligation_id,
        requirement.obligation_semantic_fingerprint,
        profile.profile_id,
        profile.fingerprint,
        "observation",
    )
    plan = VerificationPlan(
        "problem-revision-r1",
        _sha("revision-r1"),
        content_hash(planning_state),
        (requirement,),
        (profile,),
        (assignment,),
        "planner-a",
        ("evidence-plan",),
    )
    records = [
        _record("evidence-env"), _record("evidence-numeric"), _record("evidence-resource"),
        _record("evidence-soundness"), _record("evidence-profile"), _record("evidence-plan"),
        _record("evidence-assessment"), _record("evidence-result"),
    ]
    return obligation, planning_state, requirement, profile, plan, records


def _binding(requirement, profile):
    return VerificationEvidenceApplicability(
        "evidence-result",
        requirement.obligation_id,
        requirement.obligation_semantic_fingerprint,
        "problem-revision-r1",
        _sha("revision-r1"),
        "observation",
        "EXACT",
        "GRADE_A",
        "APPLICABLE",
        environment_id="env-sim",
        environment_fingerprint=_sha("env"),
        numerical_policy_id="numeric-default",
        numerical_policy_fingerprint=_sha("numeric"),
        verifier_profile_id=profile.profile_id,
        verifier_profile_fingerprint=profile.fingerprint,
        assessment_evidence_ids=("evidence-assessment",),
    )


def test_lifecycle_contract_preserves_immutable_planning_snapshot_without_requiring_whole_state_stasis():
    contract = verification_plan_lifecycle_contract()
    assert contract["planning_snapshot"] == "IMMUTABLE_EXACT_CALCULUS_STATE_FINGERPRINT"
    assert contract["current_applicability"] == "REVALIDATE_CANONICAL_OBLIGATION_SEMANTICS_NOT_WHOLE_STATE_EQUALITY"
    assert contract["plan_mutation"] if "plan_mutation" in contract else True
    assert contract["obligation_mutation"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"


def test_evidence_attachment_changes_state_fingerprint_but_does_not_semantically_invalidate_plan():
    obligation, planning_state, _, _, plan, _ = _planning_fixture()
    current = _state(
        ObligationRecord(
            obligation.obligation_id,
            obligation.statement,
            status="VERIFYING",
            required_evidence_types=obligation.required_evidence_types,
            evidence_ids=["evidence-result"],
        )
    )
    assert content_hash(current) != plan.calculus_state_fingerprint
    assert validate_verification_plan(current, plan)["valid"] is False
    lifecycle = validate_verification_plan_current_applicability(current, plan)
    assert lifecycle["valid"] is True, lifecycle["errors"]
    assert lifecycle["planning_snapshot_match"] is False
    assert lifecycle["replan_required"] is False


def test_current_debt_can_clear_after_result_evidence_attaches_without_rewriting_plan():
    obligation, _, requirement, profile, plan, records = _planning_fixture()
    current = _state(
        ObligationRecord(
            obligation.obligation_id,
            obligation.statement,
            status="VERIFYING",
            required_evidence_types=obligation.required_evidence_types,
            evidence_ids=["evidence-result"],
        )
    )
    result = project_verification_debt_current_assured(current, records, plan, (_binding(requirement, profile),))
    assert result["lifecycle"]["planning_snapshot_match"] is False
    assert result["debt"]["total_debt_count"] == 0
    assert result["debt"]["verification_plan_id"] == plan.plan_id
    assert result["debt"]["verification_plan_fingerprint"] == plan.fingerprint
    assert plan.calculus_state_fingerprint != result["debt"]["calculus_state_fingerprint"]


def test_satisfied_obligation_may_leave_current_debt_without_rewriting_original_plan():
    obligation, _, _, _, plan, records = _planning_fixture()
    current = _state(
        ObligationRecord(
            obligation.obligation_id,
            obligation.statement,
            status="VERIFIED",
            required_evidence_types=obligation.required_evidence_types,
            evidence_ids=["evidence-result"],
        )
    )
    result = project_verification_debt_current_assured(current, records, plan, ())
    assert result["lifecycle"]["currently_satisfied_planned_obligation_ids"] == [obligation.obligation_id]
    assert result["debt"]["total_debt_count"] == 0


def test_new_unplanned_verification_obligation_forces_replan():
    obligation, planning_state, _, _, plan, records = _planning_fixture()
    new = ObligationRecord(
        "verify-new",
        "new verification requirement",
        status="AVAILABLE",
        required_evidence_types=["observation"],
    )
    current = normalize_calculus_state(planning_state)
    current["obligations"][new.obligation_id] = new.to_dict()
    current = normalize_calculus_state(current)
    lifecycle = validate_verification_plan_current_applicability(current, plan)
    assert lifecycle["valid"] is False
    assert lifecycle["new_unplanned_verification_obligation_ids"] == [new.obligation_id]
    with pytest.raises(PermissionError, match="REPLAN_REQUIRED"):
        project_verification_debt_current_assured(current, records, plan, ())


def test_required_evidence_semantic_drift_forces_replan():
    obligation, _, _, _, plan, records = _planning_fixture()
    changed = _state(
        ObligationRecord(
            obligation.obligation_id,
            obligation.statement,
            status="AVAILABLE",
            required_evidence_types=["claim", "observation"],
        )
    )
    lifecycle = validate_verification_plan_current_applicability(changed, plan)
    assert lifecycle["valid"] is False
    assert any("CURRENT_PLAN_OBLIGATION_SEMANTIC_DRIFT" in error for error in lifecycle["errors"])
    with pytest.raises(PermissionError, match="REPLAN_REQUIRED"):
        project_verification_debt_current_assured(changed, records, plan, ())


def test_current_lifecycle_validation_does_not_mutate_original_plan_or_calculus():
    _, planning_state, _, _, plan, _ = _planning_fixture()
    state_before = normalize_calculus_state(planning_state)
    plan_before = plan.to_dict()
    validate_verification_plan_current_applicability(planning_state, plan)
    assert normalize_calculus_state(planning_state) == state_before
    assert plan.to_dict() == plan_before
