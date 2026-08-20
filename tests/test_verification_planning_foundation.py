from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import validate

from aasm.calculus import ObligationRecord, content_hash, default_calculus_state, normalize_calculus_state
from aasm.semantic_result import semantic_fingerprint
from aasm.typed_protocol import CapabilityContract
from aasm.verification_planning import (
    VerificationAssignment,
    VerificationBoundReference,
    VerificationDebtProjection,
    VerificationEvidenceApplicability,
    VerificationPlan,
    VerificationPropertyClaim,
    VerifierCapabilityProfile,
    project_verification_debt,
    validate_verification_debt_projection,
    validate_verification_plan,
    verification_planning_contract,
    verification_requirement_from_obligation,
)


ROOT = Path(__file__).resolve().parents[1]


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _state(*obligations: ObligationRecord):
    state = default_calculus_state()
    state["obligations"] = {row.obligation_id: row.to_dict() for row in obligations}
    state["obligation_edges"] = [
        {"src": dep, "dst": row.obligation_id, "relation": "REQUIRES"}
        for row in obligations
        for dep in row.dependencies
    ]
    return normalize_calculus_state(state)


def _evidence(evidence_id: str, *, kind="observation", status="active") -> dict:
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


def _profile(*, fidelity="EXACT", grade="GRADE_A", evidence_types=("observation",), strengths=("CHECKED_CERTIFICATE",)) -> VerifierCapabilityProfile:
    capability = CapabilityContract(
        capability_id="drc.verifier",
        capability_type="VERIFIER",
        version="1.0.0",
        evidence_types=tuple(evidence_types),
        deterministic=True,
    )
    refs = (
        VerificationBoundReference("ENVIRONMENT", "aasm.execution.environment-binding.v1", "env-sim", _sha("env"), ("evidence-env",)),
        VerificationBoundReference("NUMERICAL_POLICY", "aasm.numeric.tolerance.v1", "numeric-default", _sha("numeric"), ("evidence-numeric",)),
        VerificationBoundReference("RESOURCE_DEMAND", "aasm.resource.demand.v1", "resource-drc", _sha("resource"), ("evidence-resource",)),
    )
    return VerifierCapabilityProfile(
        verifier_id="verifier-drc",
        capability=capability,
        fidelity=fidelity,
        evidence_grade=grade,
        references=refs,
        soundness_claim=VerificationPropertyClaim("SOUNDNESS", "EVIDENCE_BACKED", "sound within declared DRC semantics", ("evidence-soundness",)),
        completeness_claim=VerificationPropertyClaim("COMPLETENESS", "UNKNOWN", "completeness is not claimed"),
        verification_strengths=tuple(strengths),
        cache_reuse_eligibility="PERFORMANCE_ONLY",
        supporting_evidence_ids=("evidence-profile",),
    )


def _obligation(obligation_id="verify-clearance", *, status="VERIFYING", evidence_ids=()):
    return ObligationRecord(
        obligation_id,
        "verify clearance",
        status=status,
        required_evidence_types=["observation"],
        evidence_ids=list(evidence_ids),
    )


def _plan(state, obligation, *, profile=None, assign=True, grades=("GRADE_A",), fidelities=("EXACT",), strengths=("CHECKED_CERTIFICATE",)):
    profile = profile or _profile()
    requirement = verification_requirement_from_obligation(
        obligation.to_dict(),
        acceptable_fidelities=fidelities,
        acceptable_evidence_grades=grades,
        acceptable_verification_strengths=strengths,
        required_environment_id="env-sim",
        required_environment_fingerprint=_sha("env"),
        required_numerical_policy_id="numeric-default",
        required_numerical_policy_fingerprint=_sha("numeric"),
    )
    assignments = ()
    if assign:
        assignments = (
            VerificationAssignment(
                requirement.obligation_id,
                requirement.obligation_semantic_fingerprint,
                profile.profile_id,
                profile.fingerprint,
                "observation",
                "CHECKED_CERTIFICATE",
            ),
        )
    return VerificationPlan(
        problem_revision_id="problem-revision-r1",
        problem_revision_fingerprint=_sha("revision-r1"),
        calculus_state_fingerprint=content_hash(state),
        requirements=(requirement,),
        verifier_profiles=(profile,),
        assignments=assignments,
        producer_principal_id="planner-a",
        evidence_ids=("evidence-plan",),
    ), requirement, profile


def test_contract_reuses_existing_obligation_capability_and_evidence_planes():
    contract = verification_planning_contract()
    assert contract["obligation_source"] == "EXISTING_AASM_CALCULUS_V1_ONLY"
    assert contract["verifier_abi"] == "COMPOSES_EXISTING_AASM_CAPABILITY_ABI_VERIFIER"
    assert contract["evidence_grade"] == "OPAQUE_NAMED_GRADE_EXACT_ACCEPTABILITY_NO_IMPLICIT_ORDERING"
    assert contract["fidelity"]["ordering"] == "NONE"
    assert contract["soundness_completeness"] == "DECLARATIVE_CLAIMS_NOT_PROOF_AUTHORITY"
    assert contract["verifier_execution"] == "NONE"
    assert contract["resource_reservation"] == "NONE"
    assert contract["fact_authority"] == "NONE"
    assert contract["debt_scalar_score"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"


def test_verifier_profile_composes_existing_verifier_capability_and_rejects_operator():
    profile = _profile()
    assert profile.capability.capability_type == "VERIFIER"
    assert profile.capability.token.startswith("aasm.capability:")
    operator = CapabilityContract("not-a-verifier", "OPERATOR", "1.0.0", evidence_types=("observation",))
    with pytest.raises(ValueError, match="VERIFIER CapabilityContract"):
        VerifierCapabilityProfile(
            verifier_id="operator",
            capability=operator,
            fidelity="EXACT",
            evidence_grade="GRADE_A",
            references=profile.references,
            soundness_claim=profile.soundness_claim,
            completeness_claim=profile.completeness_claim,
        )


def test_plan_cannot_omit_a_canonical_verification_obligation():
    first = _obligation("verify-a")
    second = _obligation("verify-b")
    state = _state(first, second)
    plan, _, _ = _plan(state, first)
    result = validate_verification_plan(state, plan)
    assert result["valid"] is False
    assert any("PLAN_OMITS_CANONICAL_VERIFICATION_OBLIGATIONS" in error for error in result["errors"])


def test_plan_cannot_weaken_canonical_required_evidence_types():
    obligation = ObligationRecord("verify-a", "verify a", status="VERIFYING", required_evidence_types=["claim", "observation"])
    state = _state(obligation)
    profile = _profile(evidence_types=("claim", "observation"))
    requirement = verification_requirement_from_obligation(
        obligation.to_dict(),
        acceptable_fidelities=("EXACT",),
        acceptable_evidence_grades=("GRADE_A",),
    )
    payload = requirement.to_dict()
    payload.pop("fingerprint")
    payload.pop("requirement_id")
    payload["required_evidence_types"] = ["observation"]
    weakened = type(requirement).from_dict(payload)
    plan = VerificationPlan(
        "problem-revision-r1", _sha("revision-r1"), content_hash(state),
        (weakened,), (profile,), (), "planner-a", ("evidence-plan",),
    )
    result = validate_verification_plan(state, plan)
    assert result["valid"] is False
    assert any("REQUIREMENT_WEAKENS_OR_ALTERS_CANONICAL_EVIDENCE_TYPES" in error for error in result["errors"])


def test_assignment_rejects_fidelity_and_grade_laundering():
    obligation = _obligation()
    state = _state(obligation)
    profile = _profile(fidelity="APPROXIMATE", grade="GRADE_B")
    requirement = verification_requirement_from_obligation(
        obligation.to_dict(),
        acceptable_fidelities=("EXACT",),
        acceptable_evidence_grades=("GRADE_A",),
    )
    with pytest.raises(ValueError, match="FIDELITY_UNSATISFIED"):
        VerificationPlan(
            "problem-revision-r1", _sha("revision-r1"), content_hash(state),
            (requirement,), (profile,),
            (VerificationAssignment(requirement.obligation_id, requirement.obligation_semantic_fingerprint, profile.profile_id, profile.fingerprint, "observation"),),
            "planner-a", ("evidence-plan",),
        )


def test_evidence_grades_have_no_implicit_ordering():
    obligation = _obligation(evidence_ids=("evidence-result",))
    state = _state(obligation)
    plan, requirement, profile = _plan(state, obligation, grades=("GRADE_A",), strengths=())
    records = [_evidence("evidence-result")]
    binding = VerificationEvidenceApplicability(
        "evidence-result", obligation.obligation_id, requirement.obligation_semantic_fingerprint,
        plan.problem_revision_id, plan.problem_revision_fingerprint, "observation", "EXACT", "GRADE_Z", "APPLICABLE",
        environment_id="env-sim", environment_fingerprint=_sha("env"),
        numerical_policy_id="numeric-default", numerical_policy_fingerprint=_sha("numeric"),
        verifier_profile_id=profile.profile_id, verifier_profile_fingerprint=profile.fingerprint,
    )
    debt = project_verification_debt(state, records, plan, (binding,))
    assert len(debt.items) == 1
    assert "EVIDENCE_GRADE_UNSATISFIED" in debt.items[0].reasons


def test_applicable_active_exact_evidence_clears_verification_debt():
    obligation = _obligation(evidence_ids=("evidence-result",))
    state = _state(obligation)
    plan, requirement, profile = _plan(state, obligation, strengths=())
    records = [_evidence("evidence-result"), _evidence("evidence-applicability")]
    binding = VerificationEvidenceApplicability(
        "evidence-result", obligation.obligation_id, requirement.obligation_semantic_fingerprint,
        plan.problem_revision_id, plan.problem_revision_fingerprint, "observation", "EXACT", "GRADE_A", "APPLICABLE",
        environment_id="env-sim", environment_fingerprint=_sha("env"),
        numerical_policy_id="numeric-default", numerical_policy_fingerprint=_sha("numeric"),
        verifier_profile_id=profile.profile_id, verifier_profile_fingerprint=profile.fingerprint,
        assessment_evidence_ids=("evidence-applicability",),
    )
    debt = project_verification_debt(state, records, plan, (binding,))
    assert debt.items == ()
    result = validate_verification_debt_projection(state, records, plan, (binding,), debt)
    assert result["valid"] is True
    assert result["parallel_truth_plane"] == "NONE"


def test_stale_evidence_remains_debt_and_cannot_clear_obligation():
    obligation = _obligation(evidence_ids=("evidence-result",))
    state = _state(obligation)
    plan, requirement, profile = _plan(state, obligation, strengths=())
    records = [_evidence("evidence-result", status="invalidated")]
    binding = VerificationEvidenceApplicability(
        "evidence-result", obligation.obligation_id, requirement.obligation_semantic_fingerprint,
        plan.problem_revision_id, plan.problem_revision_fingerprint, "observation", "EXACT", "GRADE_A", "APPLICABLE",
        environment_id="env-sim", environment_fingerprint=_sha("env"),
        numerical_policy_id="numeric-default", numerical_policy_fingerprint=_sha("numeric"),
        verifier_profile_id=profile.profile_id, verifier_profile_fingerprint=profile.fingerprint,
    )
    before = deepcopy(state)
    debt = project_verification_debt(state, records, plan, (binding,))
    assert "STALE_EVIDENCE" in debt.items[0].reasons
    assert state == before
    assert state["obligations"][obligation.obligation_id]["status"] == "VERIFYING"


def test_unassessed_attached_evidence_is_visible_debt_not_implicitly_applicable():
    obligation = _obligation(evidence_ids=("evidence-result",))
    state = _state(obligation)
    plan, _, _ = _plan(state, obligation, strengths=())
    debt = project_verification_debt(state, [_evidence("evidence-result")], plan, ())
    assert "EVIDENCE_APPLICABILITY_UNASSESSED" in debt.items[0].reasons


def test_terminal_unresolved_verification_obligation_remains_visible_debt():
    obligation = _obligation(status="IMPOSSIBLE", evidence_ids=("evidence-result",))
    state = _state(obligation)
    plan, requirement, profile = _plan(state, obligation, strengths=())
    records = [_evidence("evidence-result")]
    binding = VerificationEvidenceApplicability(
        "evidence-result", obligation.obligation_id, requirement.obligation_semantic_fingerprint,
        plan.problem_revision_id, plan.problem_revision_fingerprint, "observation", "EXACT", "GRADE_A", "APPLICABLE",
        environment_id="env-sim", environment_fingerprint=_sha("env"),
        numerical_policy_id="numeric-default", numerical_policy_fingerprint=_sha("numeric"),
        verifier_profile_id=profile.profile_id, verifier_profile_fingerprint=profile.fingerprint,
    )
    debt = project_verification_debt(state, records, plan, (binding,))
    assert len(debt.items) == 1
    assert debt.items[0].classification == "TERMINAL_UNVERIFIED"
    assert "TERMINAL_UNRESOLVED" in debt.items[0].reasons


def test_satisfied_existing_obligation_leaves_verification_debt_projection():
    obligation = _obligation(status="VERIFIED")
    state = _state(obligation)
    plan = VerificationPlan(
        "problem-revision-r1", _sha("revision-r1"), content_hash(state),
        (), (), (), "planner-a", ("evidence-plan",),
    )
    assert validate_verification_plan(state, plan)["valid"] is True
    debt = project_verification_debt(state, [], plan, ())
    assert debt.items == ()


def test_plan_and_debt_json_schemas_validate():
    obligation = _obligation(evidence_ids=("evidence-result",))
    state = _state(obligation)
    plan, _, _ = _plan(state, obligation, strengths=())
    debt = project_verification_debt(state, [_evidence("evidence-result")], plan, ())
    plan_schema = json.loads((ROOT / "schemas" / "verification-plan.schema.json").read_text(encoding="utf-8"))
    debt_schema = json.loads((ROOT / "schemas" / "verification-debt.schema.json").read_text(encoding="utf-8"))
    validate(plan.to_dict(), plan_schema)
    validate(debt.to_dict(), debt_schema)
    assert VerificationPlan.from_dict(plan.to_dict()).fingerprint == plan.fingerprint
    assert VerificationDebtProjection.from_dict(debt.to_dict()).fingerprint == debt.fingerprint


def test_binary_float_is_forbidden_in_verification_plan_identity():
    obligation = _obligation()
    state = _state(obligation)
    plan, _, _ = _plan(state, obligation)
    payload = plan.to_dict()
    payload.pop("fingerprint")
    payload.pop("plan_id")
    payload["metadata"] = {"unsafe_float": 0.2}
    with pytest.raises(TypeError, match="binary floating-point"):
        VerificationPlan.from_dict(payload)
