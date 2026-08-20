from __future__ import annotations

import pytest

from aasm.calculus import ObligationRecord, content_hash, normalize_calculus_state
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.runtime_v56_foundation import AASMEngine as V56FoundationEngine
from aasm.semantic_evolution import ProblemRevision
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
from aasm.verification_planning_runtime import VerificationPlanningRuntimeMixin


class VerificationEngine(VerificationPlanningRuntimeMixin, V56FoundationEngine):
    pass


def _sha(label: str) -> str:
    return semantic_fingerprint({"fixture": label})


def _engine() -> VerificationEngine:
    return VerificationEngine(ProblemSpec("S5.3 durable verification planning"))


def _support(engine: VerificationEngine) -> dict[str, EvidenceRecord]:
    names = (
        "plan", "env", "numeric", "resource", "soundness", "profile",
        "result", "assessment",
    )
    return {
        name: engine.add_evidence(EvidenceRecord("observation", name, source="test"))
        for name in names
    }


def _base() -> ProblemRevision:
    return ProblemRevision(
        problem_id="pcb-main",
        problem_fingerprint=_sha("problem-v1"),
        semantic_projection_fingerprint=_sha("projection-v1"),
        environment_fingerprint=_sha("environment-v1"),
        created_by="controller-c",
        revision_id="problem-revision-r1",
    )


def _profile(rows) -> VerifierCapabilityProfile:
    capability = CapabilityContract(
        "drc.verifier", "VERIFIER", "1.0.0", evidence_types=("observation",), deterministic=True
    )
    references = (
        VerificationBoundReference("ENVIRONMENT", "aasm.execution.environment-binding.v1", "env-sim", _sha("env"), (rows["env"].evidence_id,)),
        VerificationBoundReference("NUMERICAL_POLICY", "aasm.numeric.tolerance.v1", "numeric-default", _sha("numeric"), (rows["numeric"].evidence_id,)),
        VerificationBoundReference("RESOURCE_DEMAND", "aasm.resource.demand.v1", "resource-drc", _sha("resource"), (rows["resource"].evidence_id,)),
    )
    return VerifierCapabilityProfile(
        "verifier-drc",
        capability,
        "EXACT",
        "GRADE_A",
        references,
        VerificationPropertyClaim("SOUNDNESS", "EVIDENCE_BACKED", "declared semantics checked", (rows["soundness"].evidence_id,)),
        VerificationPropertyClaim("COMPLETENESS", "UNKNOWN", "not claimed"),
        supporting_evidence_ids=(rows["profile"].evidence_id,),
    )


def _obligation() -> ObligationRecord:
    return ObligationRecord(
        "verify-clearance",
        "verify clearance",
        status="AVAILABLE",
        required_evidence_types=["observation"],
    )


def _setup():
    engine = _engine()
    rows = _support(engine)
    base = _base()
    engine.register_initial_problem_revision(base, authority_id="controller-c", authority_class="CONTROLLER")
    obligation = _obligation()
    engine.register_obligation(obligation)
    profile = _profile(rows)
    calculus = normalize_calculus_state(engine._calculus())
    requirement = verification_requirement_from_obligation(
        calculus["obligations"][obligation.obligation_id],
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
        base.revision_id,
        base.fingerprint,
        content_hash(calculus),
        (requirement,),
        (profile,),
        (assignment,),
        "planner-a",
        (rows["plan"].evidence_id,),
    )
    return engine, rows, base, obligation, requirement, profile, plan


def _advance_with_result(engine, rows, obligation):
    engine.enable_obligation(obligation.obligation_id)
    engine.set_obligation_status(obligation.obligation_id, "IN_PROGRESS")
    engine.set_obligation_status(
        obligation.obligation_id,
        "VERIFYING",
        evidence_ids=(rows["result"].evidence_id,),
    )


def _binding(rows, base, obligation, requirement, profile, *, evidence_type="observation"):
    return VerificationEvidenceApplicability(
        rows["result"].evidence_id,
        obligation.obligation_id,
        requirement.obligation_semantic_fingerprint,
        base.revision_id,
        base.fingerprint,
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
        assessment_evidence_ids=(rows["assessment"].evidence_id,),
    )


def test_runtime_contract_stores_proposals_and_applicability_but_never_debt_or_execution_state():
    engine = _engine()
    contract = engine.verification_planning_runtime_contract_report()
    assert contract["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"
    assert contract["debt_storage"] == "NONE_RECOMPUTED_PROJECTION_ONLY"
    assert contract["verifier_execution"] == "NONE"
    assert contract["resource_reservation"] == "NONE"
    assert contract["obligation_mutation"] == "NONE"
    assert contract["parallel_debt_store"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"


def test_plan_records_idempotently_through_existing_evidence_replay():
    engine, _, _, _, _, _, plan = _setup()
    first = engine.record_verification_plan(plan)
    second = engine.record_verification_plan(plan)
    assert first["already_recorded"] is False
    assert second["already_recorded"] is True
    assert second["evidence_id"] == first["evidence_id"]
    report = engine.verification_planning_history_report()
    assert report["valid"] is True, report["issues"]
    assert report["plans"][plan.plan_id]["plan"]["fingerprint"] == plan.fingerprint
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_plan_must_bind_exact_current_problem_revision_head():
    engine, rows, base, obligation, requirement, profile, plan = _setup()
    payload = plan.to_dict()
    payload.pop("fingerprint")
    payload.pop("plan_id")
    payload["problem_revision_fingerprint"] = _sha("forged-revision")
    forged = VerificationPlan.from_dict(payload)
    with pytest.raises(ValueError, match="ProblemRevision fingerprint"):
        engine.record_verification_plan(forged)


def test_result_evidence_can_evolve_calculus_then_applicability_records_and_clears_current_debt():
    engine, rows, base, obligation, requirement, profile, plan = _setup()
    engine.record_verification_plan(plan)
    _advance_with_result(engine, rows, obligation)
    binding = _binding(rows, base, obligation, requirement, profile)
    recorded = engine.record_verification_evidence_applicability(
        plan_id=plan.plan_id,
        applicability=binding,
    )
    assert recorded["already_recorded"] is False
    debt = engine.verification_debt_report(plan.plan_id)
    assert debt["lifecycle"]["planning_snapshot_match"] is False
    assert debt["debt"]["total_debt_count"] == 0
    assert debt["debt"]["verification_plan_id"] == plan.plan_id


def test_forged_evidence_type_relabeling_is_rejected_before_durable_applicability_record():
    engine, rows, base, obligation, requirement, profile, plan = _setup()
    engine.record_verification_plan(plan)
    _advance_with_result(engine, rows, obligation)
    forged = _binding(rows, base, obligation, requirement, profile, evidence_type="claim")
    with pytest.raises(PermissionError, match="ASSURANCE_REJECTED"):
        engine.record_verification_evidence_applicability(
            plan_id=plan.plan_id,
            applicability=forged,
        )
    assert engine.verification_planning_history_report()["applicability"] == {}


def test_conflicting_active_applicability_requires_invalidation_before_reassessment():
    engine, rows, base, obligation, requirement, profile, plan = _setup()
    engine.record_verification_plan(plan)
    _advance_with_result(engine, rows, obligation)
    first = _binding(rows, base, obligation, requirement, profile)
    recorded = engine.record_verification_evidence_applicability(plan_id=plan.plan_id, applicability=first)
    payload = first.to_dict()
    payload.pop("fingerprint")
    payload.pop("applicability_id")
    payload["status"] = "INAPPLICABLE"
    payload["reason"] = "independent reassessment rejected applicability"
    replacement = VerificationEvidenceApplicability.from_dict(payload)
    with pytest.raises(ValueError, match="ACTIVE_KEY_CONFLICT"):
        engine.record_verification_evidence_applicability(plan_id=plan.plan_id, applicability=replacement)
    engine.invalidate_evidence(recorded["evidence_id"], "applicability assessment superseded")
    second = engine.record_verification_evidence_applicability(plan_id=plan.plan_id, applicability=replacement)
    assert second["already_recorded"] is False
    report = engine.verification_planning_history_report()
    assert report["valid"] is True, report["issues"]
    assert len(report["applicability"]) == 1
    assert next(iter(report["applicability"].values()))["applicability"]["status"] == "INAPPLICABLE"


def test_later_stale_applicability_assessment_reopens_current_debt_without_rewriting_history():
    engine, rows, base, obligation, requirement, profile, plan = _setup()
    engine.record_verification_plan(plan)
    _advance_with_result(engine, rows, obligation)
    binding = _binding(rows, base, obligation, requirement, profile)
    engine.record_verification_evidence_applicability(plan_id=plan.plan_id, applicability=binding)
    assert engine.verification_debt_report(plan.plan_id)["debt"]["total_debt_count"] == 0
    engine.invalidate_evidence(rows["assessment"].evidence_id, "assessment basis superseded")
    debt = engine.verification_debt_report(plan.plan_id)
    assert debt["debt"]["total_debt_count"] == 1
    assert "INDETERMINATE_APPLICABILITY" in debt["debt"]["items"][0]["reasons"]
    history = engine.verification_planning_history_report()
    assert history["valid"] is True
    assert binding.applicability_id in history["applicability"]


def test_new_verification_obligation_after_plan_forces_replan_at_current_debt_boundary():
    engine, rows, base, obligation, requirement, profile, plan = _setup()
    engine.record_verification_plan(plan)
    engine.register_obligation(
        ObligationRecord(
            "verify-new",
            "new verification requirement",
            status="AVAILABLE",
            required_evidence_types=["observation"],
        )
    )
    with pytest.raises(PermissionError, match="REPLAN_REQUIRED"):
        engine.verification_debt_report(plan.plan_id)


def test_stale_profile_support_forces_replan_without_destroying_recorded_plan():
    engine, rows, _, _, _, _, plan = _setup()
    recorded = engine.record_verification_plan(plan)
    engine.invalidate_evidence(rows["profile"].evidence_id, "verifier qualification expired")
    with pytest.raises(PermissionError, match="REPLAN_REQUIRED"):
        engine.verification_debt_report(plan.plan_id)
    history = engine.verification_planning_history_report()
    assert history["valid"] is True
    assert history["plans"][plan.plan_id]["evidence_id"] == recorded["evidence_id"]


def test_runtime_never_executes_verifier_reserves_resource_or_transitions_obligation_itself():
    engine, _, _, obligation, _, _, plan = _setup()
    before = normalize_calculus_state(engine._calculus())
    engine.record_verification_plan(plan)
    after = normalize_calculus_state(engine._calculus())
    assert before == after
    assert after["obligations"][obligation.obligation_id]["status"] == "AVAILABLE"
    contract = engine.verification_planning_runtime_contract_report()
    assert contract["verifier_execution"] == "NONE"
    assert contract["resource_reservation"] == "NONE"
    assert contract["effect_dispatch"] == "NONE"
