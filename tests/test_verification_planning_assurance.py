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
    verification_requirement_from_obligation,
)
from aasm.verification_planning_assurance import (
    assure_verification_planning_inputs,
    project_verification_debt_assured,
    verification_planning_assurance_contract,
)


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


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
        "invalidated_at": 1 if status != "active" else None,
        "invalidated_reason": "stale" if status != "active" else None,
    }


def _fixture():
    obligation = ObligationRecord(
        "verify-clearance",
        "verify clearance",
        status="VERIFYING",
        required_evidence_types=["observation"],
        evidence_ids=["evidence-result"],
    )
    state = default_calculus_state()
    state["obligations"] = {obligation.obligation_id: obligation.to_dict()}
    state = normalize_calculus_state(state)
    capability = CapabilityContract(
        "drc.verifier",
        "VERIFIER",
        "1.0.0",
        evidence_types=("observation",),
        deterministic=True,
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
        cache_reuse_eligibility="PERFORMANCE_ONLY",
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
        content_hash(state),
        (requirement,),
        (profile,),
        (assignment,),
        "planner-a",
        ("evidence-plan",),
    )
    records = [
        _record("evidence-result"),
        _record("evidence-assessment"),
        _record("evidence-env"),
        _record("evidence-numeric"),
        _record("evidence-resource"),
        _record("evidence-soundness"),
        _record("evidence-profile"),
        _record("evidence-plan"),
    ]
    return state, obligation, requirement, profile, plan, records


def _binding(requirement, profile, *, evidence_type="observation", assessments=("evidence-assessment",)):
    return VerificationEvidenceApplicability(
        "evidence-result",
        requirement.obligation_id,
        requirement.obligation_semantic_fingerprint,
        "problem-revision-r1",
        _sha("revision-r1"),
        evidence_type,
        "EXACT",
        "GRADE_A",
        "APPLICABLE",
        environment_id="env-sim",
        environment_fingerprint=_sha("env"),
        numerical_policy_id="numeric-default",
        numerical_policy_fingerprint=_sha("numeric"),
        verifier_profile_id=profile.profile_id,
        verifier_profile_fingerprint=profile.fingerprint,
        assessment_evidence_ids=tuple(assessments),
    )


def test_assurance_contract_is_fail_closed_and_pre_admission():
    contract = verification_planning_assurance_contract()
    assert contract["evidence_type_binding"] == "APPLICABILITY_TYPE_MUST_EQUAL_EXISTING_EVIDENCE_KIND"
    assert contract["applicability_provenance"] == "APPLICABLE_REQUIRES_ACTIVE_ASSESSMENT_EVIDENCE"
    assert contract["stale_applicability"] == "DOWNGRADE_TO_INDETERMINATE_FOR_DEBT_PROJECTION"
    assert contract["truth_authority"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"


def test_applicability_cannot_relabel_existing_evidence_kind_to_clear_debt():
    state, _, requirement, profile, plan, records = _fixture()
    records[0]["kind"] = "claim"
    binding = _binding(requirement, profile, evidence_type="observation")
    result = project_verification_debt_assured(state, records, plan, (binding,))
    assert any(issue["code"] == "APPLICABILITY_EVIDENCE_TYPE_MISMATCH" for issue in result["input_issues"])
    debt = result["debt"]
    assert debt["total_debt_count"] == 1
    assert "INDETERMINATE_APPLICABILITY" in debt["items"][0]["reasons"]


def test_applicable_claim_requires_assessment_evidence_provenance():
    state, _, requirement, profile, plan, records = _fixture()
    binding = _binding(requirement, profile, assessments=())
    result = project_verification_debt_assured(state, records, plan, (binding,))
    assert any(issue["code"] == "APPLICABILITY_ASSESSMENT_EVIDENCE_REQUIRED" for issue in result["input_issues"])
    assert "INDETERMINATE_APPLICABILITY" in result["debt"]["items"][0]["reasons"]


def test_stale_applicability_assessment_is_downgraded_not_trusted():
    state, _, requirement, profile, plan, records = _fixture()
    for row in records:
        if row["evidence_id"] == "evidence-assessment":
            row["status"] = "invalidated"
            row["invalidated_reason"] = "superseded assessment"
    result = project_verification_debt_assured(state, records, plan, (_binding(requirement, profile),))
    assert any(issue["code"] == "STALE_APPLICABILITY_ASSESSMENT_EVIDENCE" for issue in result["input_issues"])
    assert result["sanitized_applicability"][0]["status"] == "INDETERMINATE"
    assert result["debt"]["total_debt_count"] == 1


def test_stale_verifier_profile_support_requires_replan_instead_of_using_assignment():
    state, _, requirement, profile, plan, records = _fixture()
    for row in records:
        if row["evidence_id"] == "evidence-profile":
            row["status"] = "invalidated"
            row["invalidated_reason"] = "profile qualification expired"
    assurance = assure_verification_planning_inputs(records, plan, (_binding(requirement, profile),))
    assert assurance["plan_support_valid"] is False
    assert any(issue["code"] == "STALE_VERIFICATION_PLAN_SUPPORT" for issue in assurance["issues"])
    with pytest.raises(PermissionError, match="REPLAN_REQUIRED"):
        project_verification_debt_assured(state, records, plan, (_binding(requirement, profile),))


def test_stale_environment_reference_evidence_also_requires_replan():
    state, _, requirement, profile, plan, records = _fixture()
    for row in records:
        if row["evidence_id"] == "evidence-env":
            row["status"] = "invalidated"
            row["invalidated_reason"] = "environment binding stale"
    with pytest.raises(PermissionError, match="REPLAN_REQUIRED"):
        project_verification_debt_assured(state, records, plan, (_binding(requirement, profile),))


def test_invalidated_result_evidence_remains_verification_debt_not_input_failure():
    state, _, requirement, profile, plan, records = _fixture()
    for row in records:
        if row["evidence_id"] == "evidence-result":
            row["status"] = "invalidated"
            row["invalidated_reason"] = "measurement superseded"
    result = project_verification_debt_assured(state, records, plan, (_binding(requirement, profile),))
    assert result["debt"]["total_debt_count"] == 1
    assert "STALE_EVIDENCE" in result["debt"]["items"][0]["reasons"]
