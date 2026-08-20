from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from .verification_planning import (
    VerificationEvidenceApplicability,
    VerificationPlan,
    project_verification_debt,
)


VERIFICATION_PLANNING_ASSURANCE_CONTRACT_ID = "aasm.verification.planning.assurance.v1"
VERIFICATION_PLANNING_ASSURANCE_CONTRACT_VERSION = "0.1.0"
VERIFICATION_PLANNING_ASSURANCE_STABILITY = "FOUNDATION_EXPERIMENTAL"


def verification_planning_assurance_contract() -> dict[str, Any]:
    return {
        "contract_id": VERIFICATION_PLANNING_ASSURANCE_CONTRACT_ID,
        "contract_version": VERIFICATION_PLANNING_ASSURANCE_CONTRACT_VERSION,
        "stability": VERIFICATION_PLANNING_ASSURANCE_STABILITY,
        "base_plan_contract": "aasm.verification.plan.v1",
        "base_debt_contract": "aasm.verification.debt.v1",
        "evidence_type_binding": "APPLICABILITY_TYPE_MUST_EQUAL_EXISTING_EVIDENCE_KIND",
        "applicability_provenance": "APPLICABLE_REQUIRES_ACTIVE_ASSESSMENT_EVIDENCE",
        "plan_support_freshness": "ACTIVE_EXISTING_EVIDENCE_REQUIRED_FOR_CURRENT_PLAN_USE",
        "stale_applicability": "DOWNGRADE_TO_INDETERMINATE_FOR_DEBT_PROJECTION",
        "stale_plan_support": "FAIL_CLOSED_REPLAN_REQUIRED",
        "historical_replay": "BASE_PROJECTION_REMAINS_AVAILABLE_FOR_HISTORICAL_AUDIT",
        "truth_authority": "NONE",
        "obligation_mutation": "NONE",
        "evidence_mutation": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def _evidence_map(records: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for raw in records:
        row = deepcopy(dict(raw))
        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            out[evidence_id] = row
    return out


def _is_active(row: Mapping[str, Any] | None) -> bool:
    return row is not None and str(row.get("status", "active")) == "active"


def _plan_support_ids(plan: VerificationPlan) -> dict[str, str]:
    support: dict[str, str] = {evidence_id: "PLAN" for evidence_id in plan.evidence_ids}
    for profile in plan.verifier_profiles:
        for evidence_id in profile.supporting_evidence_ids:
            support[evidence_id] = f"VERIFIER_PROFILE:{profile.profile_id}"
        for reference in profile.references:
            for evidence_id in reference.evidence_ids:
                support[evidence_id] = f"VERIFIER_REFERENCE:{profile.profile_id}:{reference.reference_kind}"
        for claim in (profile.soundness_claim, profile.completeness_claim):
            for evidence_id in claim.evidence_ids:
                support[evidence_id] = f"VERIFIER_{claim.claim_kind}_CLAIM:{profile.profile_id}"
    return support


def assure_verification_planning_inputs(
    evidence_records: Iterable[Mapping[str, Any]],
    plan: VerificationPlan | Mapping[str, Any],
    applicability: Sequence[VerificationEvidenceApplicability | Mapping[str, Any]],
) -> dict[str, Any]:
    item = plan if isinstance(plan, VerificationPlan) else VerificationPlan.from_dict(plan)
    records = [deepcopy(dict(row)) for row in evidence_records]
    evidence = _evidence_map(records)
    issues: list[dict[str, str]] = []

    for evidence_id, role in sorted(_plan_support_ids(item).items()):
        row = evidence.get(evidence_id)
        if row is None:
            issues.append({
                "code": "VERIFICATION_PLAN_SUPPORT_EVIDENCE_MISSING",
                "evidence_id": evidence_id,
                "detail": role,
            })
        elif not _is_active(row):
            issues.append({
                "code": "STALE_VERIFICATION_PLAN_SUPPORT",
                "evidence_id": evidence_id,
                "detail": role,
            })

    sanitized: list[VerificationEvidenceApplicability] = []
    for raw in applicability:
        binding = raw if isinstance(raw, VerificationEvidenceApplicability) else VerificationEvidenceApplicability.from_dict(raw)
        binding_issues: list[str] = []
        row = evidence.get(binding.evidence_id)
        if row is None:
            binding_issues.append("APPLICABILITY_EVIDENCE_MISSING")
        elif str(row.get("kind") or "") != binding.evidence_type:
            binding_issues.append("APPLICABILITY_EVIDENCE_TYPE_MISMATCH")

        if binding.status == "APPLICABLE" and not binding.assessment_evidence_ids:
            binding_issues.append("APPLICABILITY_ASSESSMENT_EVIDENCE_REQUIRED")
        for assessment_id in binding.assessment_evidence_ids:
            assessment = evidence.get(assessment_id)
            if assessment is None:
                binding_issues.append("APPLICABILITY_ASSESSMENT_EVIDENCE_MISSING")
            elif not _is_active(assessment):
                binding_issues.append("STALE_APPLICABILITY_ASSESSMENT_EVIDENCE")

        if binding_issues:
            for code in sorted(set(binding_issues)):
                issues.append({
                    "code": code,
                    "evidence_id": binding.evidence_id,
                    "detail": binding.applicability_id,
                })
            payload = binding.to_dict()
            payload.pop("fingerprint", None)
            payload.pop("applicability_id", None)
            payload["status"] = "INDETERMINATE"
            payload["reason"] = "assurance downgrade: " + ",".join(sorted(set(binding_issues)))
            sanitized.append(VerificationEvidenceApplicability.from_dict(payload))
        else:
            sanitized.append(binding)

    plan_issue_codes = {
        "VERIFICATION_PLAN_SUPPORT_EVIDENCE_MISSING",
        "STALE_VERIFICATION_PLAN_SUPPORT",
    }
    plan_support_valid = not any(row["code"] in plan_issue_codes for row in issues)
    return {
        "contract": verification_planning_assurance_contract(),
        "plan_support_valid": plan_support_valid,
        "issues": issues,
        "sanitized_applicability": [row.to_dict() for row in sanitized],
    }


def project_verification_debt_assured(
    calculus_state: Mapping[str, Any],
    evidence_records: Iterable[Mapping[str, Any]],
    plan: VerificationPlan | Mapping[str, Any],
    applicability: Sequence[VerificationEvidenceApplicability | Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    records = [deepcopy(dict(row)) for row in evidence_records]
    item = plan if isinstance(plan, VerificationPlan) else VerificationPlan.from_dict(plan)
    assurance = assure_verification_planning_inputs(records, item, applicability)
    if not assurance["plan_support_valid"]:
        raise PermissionError(
            "STALE_OR_MISSING_VERIFICATION_PLAN_SUPPORT_REPLAN_REQUIRED: "
            + str(assurance["issues"])
        )
    sanitized = tuple(
        VerificationEvidenceApplicability.from_dict(row)
        for row in assurance["sanitized_applicability"]
    )
    debt = project_verification_debt(
        calculus_state,
        records,
        item,
        sanitized,
        metadata=metadata,
    )
    return {
        "contract": assurance["contract"],
        "debt": debt.to_dict(),
        "input_issues": deepcopy(assurance["issues"]),
        "sanitized_applicability": [row.to_dict() for row in sanitized],
    }


__all__ = [
    "VERIFICATION_PLANNING_ASSURANCE_CONTRACT_ID",
    "VERIFICATION_PLANNING_ASSURANCE_CONTRACT_VERSION",
    "VERIFICATION_PLANNING_ASSURANCE_STABILITY",
    "verification_planning_assurance_contract",
    "assure_verification_planning_inputs",
    "project_verification_debt_assured",
]
