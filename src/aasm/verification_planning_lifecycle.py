from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping, Sequence

from .calculus import content_hash, normalize_calculus_state
from .obligation_phase import obligation_semantic_fingerprint
from .verification_planning import (
    SATISFIED_VERIFICATION_OBLIGATION_STATUSES,
    TERMINAL_UNRESOLVED_OBLIGATION_STATUSES,
    VerificationDebtItem,
    VerificationDebtProjection,
    VerificationEvidenceApplicability,
    VerificationPlan,
    _applicability_fingerprint,
    _binding_reasons,
    _canonical_obligation,
    _evidence_fingerprint,
    _evidence_rows,
    _verification_obligations,
)
from .verification_planning_assurance import assure_verification_planning_inputs


VERIFICATION_PLAN_LIFECYCLE_CONTRACT_ID = "aasm.verification.plan.lifecycle.v1"
VERIFICATION_PLAN_LIFECYCLE_CONTRACT_VERSION = "0.1.0"
VERIFICATION_PLAN_LIFECYCLE_STABILITY = "FOUNDATION_EXPERIMENTAL"


def verification_plan_lifecycle_contract() -> dict[str, Any]:
    return {
        "contract_id": VERIFICATION_PLAN_LIFECYCLE_CONTRACT_ID,
        "contract_version": VERIFICATION_PLAN_LIFECYCLE_CONTRACT_VERSION,
        "stability": VERIFICATION_PLAN_LIFECYCLE_STABILITY,
        "planning_snapshot": "IMMUTABLE_EXACT_CALCULUS_STATE_FINGERPRINT",
        "current_applicability": "REVALIDATE_CANONICAL_OBLIGATION_SEMANTICS_NOT_WHOLE_STATE_EQUALITY",
        "allowed_current_evolution": [
            "OBLIGATION_STATUS",
            "ATTACHED_EVIDENCE_IDS",
            "EVIDENCE_ACTIVE_INVALIDATED_STATUS",
        ],
        "replan_on": [
            "NEW_UNRESOLVED_VERIFICATION_OBLIGATION",
            "OBLIGATION_SEMANTIC_FINGERPRINT_CHANGE",
            "REQUIRED_EVIDENCE_TYPE_CHANGE",
            "MISSING_CANONICAL_OBLIGATION",
            "STALE_OR_MISSING_PLAN_SUPPORT",
        ],
        "satisfied_obligation": "MAY_LEAVE_CURRENT_DEBT_WITHOUT_REWRITING_ORIGINAL_PLAN",
        "debt_plan_binding": "ORIGINAL_PLAN_ID_AND_FINGERPRINT_RETAINED",
        "obligation_store": "EXISTING_AASM_CALCULUS_V1_ONLY",
        "parallel_plan_mutation": "NONE",
        "obligation_mutation": "NONE",
        "truth_authority": "NONE",
        "runtime_admission": "PRE_ADMISSION_ONLY",
        "public_admission": "PRE_ADMISSION_ONLY",
    }


def validate_verification_plan_current_applicability(
    calculus_state: Mapping[str, Any],
    plan: VerificationPlan | Mapping[str, Any],
) -> dict[str, Any]:
    item = plan if isinstance(plan, VerificationPlan) else VerificationPlan.from_dict(plan)
    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    current_fingerprint = content_hash(state)
    all_obligations = {
        str(obligation_id): _canonical_obligation(raw)
        for obligation_id, raw in sorted((state.get("obligations") or {}).items())
    }
    current_required = _verification_obligations(state)
    requirements = {row.obligation_id: row for row in item.requirements}
    errors: list[str] = []

    for obligation_id, requirement in sorted(requirements.items()):
        current = all_obligations.get(obligation_id)
        if current is None:
            errors.append(f"CURRENT_PLAN_OBLIGATION_MISSING:{obligation_id}")
            continue
        if obligation_semantic_fingerprint(current) != requirement.obligation_semantic_fingerprint:
            errors.append(f"CURRENT_PLAN_OBLIGATION_SEMANTIC_DRIFT:{obligation_id}")
        if tuple(current["required_evidence_types"]) != tuple(requirement.required_evidence_types):
            errors.append(f"CURRENT_PLAN_REQUIRED_EVIDENCE_TYPES_CHANGED:{obligation_id}")

    missing_new = sorted(set(current_required) - set(requirements))
    if missing_new:
        errors.append(f"CURRENT_PLAN_MISSING_NEW_VERIFICATION_OBLIGATIONS:{missing_new}")

    currently_satisfied = sorted(
        obligation_id
        for obligation_id in requirements
        if obligation_id in all_obligations
        and all_obligations[obligation_id]["status"] in SATISFIED_VERIFICATION_OBLIGATION_STATUSES
    )
    current_unresolved = sorted(set(current_required) & set(requirements))
    return {
        "valid": not errors,
        "errors": errors,
        "plan_id": item.plan_id,
        "plan_fingerprint": item.fingerprint,
        "planning_calculus_state_fingerprint": item.calculus_state_fingerprint,
        "current_calculus_state_fingerprint": current_fingerprint,
        "planning_snapshot_match": item.calculus_state_fingerprint == current_fingerprint,
        "current_unresolved_verification_obligation_ids": current_unresolved,
        "currently_satisfied_planned_obligation_ids": currently_satisfied,
        "new_unplanned_verification_obligation_ids": missing_new,
        "obligation_store": "EXISTING_AASM_CALCULUS_V1_ONLY",
        "plan_mutation": "NONE",
        "replan_required": bool(errors),
        "runtime_admission": "PRE_ADMISSION_ONLY",
    }


def project_verification_debt_current(
    calculus_state: Mapping[str, Any],
    evidence_records: Iterable[Mapping[str, Any]],
    plan: VerificationPlan | Mapping[str, Any],
    applicability: Sequence[VerificationEvidenceApplicability | Mapping[str, Any]],
    *,
    metadata: Mapping[str, Any] | None = None,
) -> VerificationDebtProjection:
    state = normalize_calculus_state(deepcopy(dict(calculus_state)))
    item = plan if isinstance(plan, VerificationPlan) else VerificationPlan.from_dict(plan)
    lifecycle = validate_verification_plan_current_applicability(state, item)
    if not lifecycle["valid"]:
        raise PermissionError(
            "VERIFICATION_PLAN_CURRENT_SEMANTIC_DRIFT_REPLAN_REQUIRED: "
            + str(lifecycle["errors"])
        )

    evidence_list = [deepcopy(dict(row)) for row in evidence_records]
    evidence = _evidence_rows(evidence_list)
    bindings = tuple(
        row if isinstance(row, VerificationEvidenceApplicability) else VerificationEvidenceApplicability.from_dict(row)
        for row in applicability
    )
    current_required = _verification_obligations(state)
    requirements = {row.obligation_id: row for row in item.requirements}
    assignments: dict[str, list[Any]] = {}
    for assignment in item.assignments:
        assignments.setdefault(assignment.obligation_id, []).append(assignment)
    profiles = {row.profile_id: row for row in item.verifier_profiles}

    by_obligation: dict[str, list[VerificationEvidenceApplicability]] = {}
    seen_ids: set[str] = set()
    for binding in bindings:
        if binding.applicability_id in seen_ids:
            raise ValueError(f"duplicate verification evidence applicability identity: {binding.applicability_id}")
        seen_ids.add(binding.applicability_id)
        requirement = requirements.get(binding.obligation_id)
        if requirement is None:
            raise ValueError(f"verification evidence applicability references non-plan obligation: {binding.obligation_id}")
        if binding.obligation_semantic_fingerprint != requirement.obligation_semantic_fingerprint:
            raise ValueError(f"verification evidence applicability obligation fingerprint mismatch: {binding.obligation_id}")
        if binding.problem_revision_id != item.problem_revision_id or binding.problem_revision_fingerprint != item.problem_revision_fingerprint:
            raise ValueError(f"verification evidence applicability ProblemRevision mismatch: {binding.applicability_id}")
        if binding.evidence_id not in evidence:
            raise ValueError(f"verification evidence applicability references unknown Evidence: {binding.evidence_id}")
        missing_assessments = sorted(set(binding.assessment_evidence_ids) - set(evidence))
        if missing_assessments:
            raise ValueError(f"verification evidence applicability assessment Evidence missing: {missing_assessments}")
        if binding.verifier_profile_id:
            profile = profiles.get(binding.verifier_profile_id)
            if profile is None or profile.fingerprint != binding.verifier_profile_fingerprint:
                raise ValueError(f"verification evidence applicability verifier profile mismatch: {binding.applicability_id}")
        by_obligation.setdefault(binding.obligation_id, []).append(binding)

    debt: list[VerificationDebtItem] = []
    for obligation_id, obligation in sorted(current_required.items()):
        requirement = requirements[obligation_id]
        obligation_bindings = by_obligation.get(obligation_id, [])
        attached_ids = set(obligation.get("evidence_ids") or [])
        active_attached = {
            evidence_id
            for evidence_id in attached_ids
            if evidence_id in evidence and str(evidence[evidence_id].get("status", "active")) == "active"
        }
        stale_attached = {
            evidence_id
            for evidence_id in attached_ids
            if evidence_id in evidence and str(evidence[evidence_id].get("status", "active")) != "active"
        }
        reasons: set[str] = set()
        applicable_ids: set[str] = set()
        mismatch_reasons: set[str] = set()
        assessed_attached: set[str] = set()
        indeterminate = False

        for binding in obligation_bindings:
            if binding.evidence_id not in attached_ids:
                continue
            assessed_attached.add(binding.evidence_id)
            row = evidence[binding.evidence_id]
            if str(row.get("status", "active")) != "active":
                reasons.add("STALE_EVIDENCE")
                continue
            if binding.status == "INDETERMINATE":
                indeterminate = True
                continue
            if binding.status != "APPLICABLE":
                continue
            failures = _binding_reasons(requirement, binding)
            if failures:
                mismatch_reasons.update(failures)
                continue
            applicable_ids.add(binding.evidence_id)

        if obligation["status"] in TERMINAL_UNRESOLVED_OBLIGATION_STATUSES:
            reasons.add("TERMINAL_UNRESOLVED")
        if not applicable_ids:
            if not attached_ids:
                reasons.add("NO_ATTACHED_EVIDENCE")
            elif stale_attached:
                reasons.add("STALE_EVIDENCE")
            if active_attached - assessed_attached:
                reasons.add("EVIDENCE_APPLICABILITY_UNASSESSED")
            reasons.update(mismatch_reasons)
            if indeterminate:
                reasons.add("INDETERMINATE_APPLICABILITY")
            if not mismatch_reasons and not indeterminate and active_attached and active_attached <= assessed_attached:
                reasons.add("EVIDENCE_TYPE_UNSATISFIED")
        if not assignments.get(obligation_id) and not applicable_ids:
            reasons.add("NO_VERIFIER_ASSIGNMENT")

        if reasons:
            classification = (
                "TERMINAL_UNVERIFIED"
                if obligation["status"] in TERMINAL_UNRESOLVED_OBLIGATION_STATUSES
                else "UNVERIFIED"
            )
            planned_profiles = tuple(sorted({row.verifier_profile_id for row in assignments.get(obligation_id, [])}))
            debt.append(
                VerificationDebtItem(
                    obligation_id=obligation_id,
                    obligation_semantic_fingerprint=obligation_semantic_fingerprint(obligation),
                    obligation_status=obligation["status"],
                    classification=classification,
                    statement=str(obligation.get("statement") or ""),
                    required_evidence_types=tuple(obligation["required_evidence_types"]),
                    applicable_evidence_ids=tuple(sorted(applicable_ids)),
                    planned_verifier_profile_ids=planned_profiles,
                    reasons=tuple(sorted(reasons)),
                )
            )

    return VerificationDebtProjection(
        problem_revision_id=item.problem_revision_id,
        problem_revision_fingerprint=item.problem_revision_fingerprint,
        calculus_state_fingerprint=content_hash(state),
        verification_plan_id=item.plan_id,
        verification_plan_fingerprint=item.fingerprint,
        evidence_state_fingerprint=_evidence_fingerprint(evidence_list),
        applicability_fingerprint=_applicability_fingerprint(bindings),
        items=tuple(debt),
        metadata=dict(metadata or {}),
    )


def project_verification_debt_current_assured(
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
    debt = project_verification_debt_current(
        calculus_state,
        records,
        item,
        sanitized,
        metadata=metadata,
    )
    return {
        "contract": verification_plan_lifecycle_contract(),
        "lifecycle": validate_verification_plan_current_applicability(calculus_state, item),
        "debt": debt.to_dict(),
        "input_issues": deepcopy(assurance["issues"]),
        "sanitized_applicability": [row.to_dict() for row in sanitized],
    }


__all__ = [
    "VERIFICATION_PLAN_LIFECYCLE_CONTRACT_ID",
    "VERIFICATION_PLAN_LIFECYCLE_CONTRACT_VERSION",
    "VERIFICATION_PLAN_LIFECYCLE_STABILITY",
    "verification_plan_lifecycle_contract",
    "validate_verification_plan_current_applicability",
    "project_verification_debt_current",
    "project_verification_debt_current_assured",
]
