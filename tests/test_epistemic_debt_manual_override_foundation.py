from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

import aasm
from aasm.calculus import (
    ObligationRecord,
    default_calculus_state,
    normalize_calculus_state,
)
from aasm.epistemic_debt_manual_override import (
    EPISTEMIC_DEBT_CLASSES,
    MANUAL_OVERRIDE_ASSESSMENT_STATUSES,
    EpistemicDebtProjection,
    ManualOverride,
    ManualOverrideAssessment,
    OverrideValidityWindow,
    bind_manual_override,
    epistemic_debt_manual_override_contract,
    evaluate_manual_override,
    project_epistemic_debt,
    validate_epistemic_debt_projection,
)
from aasm.obligation_phase import ObligationPhasePlan, bind_obligation_phase
from aasm.risk_irreversibility import RiskAssessment
from aasm.rule import (
    EngineeringRule,
    RuleApplicabilityPredicate,
    RuleClauseRef,
    RuleControlPolicy,
    RuleScopeSelector,
    RuleSourceAuthorityRef,
)


ROOT = Path(__file__).resolve().parents[1]
REVISION_ID = "problem-revision-s4-9"
REVISION_FINGERPRINT = "9" * 64


def obligation(
    obligation_id: str,
    *,
    status: str = "AVAILABLE",
    dependencies: tuple[str, ...] = (),
    required_evidence_types: tuple[str, ...] = (),
) -> ObligationRecord:
    return ObligationRecord(
        obligation_id,
        f"Obligation {obligation_id}",
        status=status,
        dependencies=list(dependencies),
        required_evidence_types=list(required_evidence_types),
        scope={"scope_id": "control"},
    )


def state_with(*records: ObligationRecord) -> dict:
    state = default_calculus_state()
    for record in records:
        state["obligations"][record.obligation_id] = record.to_dict()
        for dependency in record.dependencies:
            state["obligation_edges"].append(
                {"src": dependency, "dst": record.obligation_id, "relation": "REQUIRES"}
            )
    return normalize_calculus_state(state)


def plan_for(state: dict, phases: dict[str, str]) -> ObligationPhasePlan:
    return ObligationPhasePlan(
        REVISION_ID,
        REVISION_FINGERPRINT,
        tuple(
            bind_obligation_phase(
                state["obligations"][obligation_id],
                phase,
                problem_revision_id=REVISION_ID,
                problem_revision_fingerprint=REVISION_FINGERPRINT,
            )
            for obligation_id, phase in sorted(phases.items())
        ),
    )


def rule(*, strength: str = "POLICY", waivable: bool = True) -> EngineeringRule:
    clause_id = f"override-{strength}-{waivable}"
    control = (
        RuleControlPolicy("EXPLICIT_AUTHORIZED", "FORBIDDEN", "rule.waive")
        if waivable
        else RuleControlPolicy()
    )
    return EngineeringRule(
        "operator-policy",
        RuleClauseRef(
            "aasm.semantic.constraint.v1",
            clause_id,
            hashlib.sha256(clause_id.encode()).hexdigest(),
            "POLICY",
        ),
        strength,
        RuleScopeSelector("workspace-1", "control", "EXACT", ("actuator-1",)),
        RuleApplicabilityPredicate("ALWAYS"),
        "operator-policy",
        control_policy=control,
        severity="HIGH",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )


def risk(status: str = "REQUIRES_EXPLICIT_ACCEPTANCE") -> RiskAssessment:
    return RiskAssessment(
        envelope_id="risk-envelope-1",
        envelope_fingerprint="a" * 64,
        irreversibility_profile_id="irreversibility-profile-1",
        irreversibility_fingerprint="b" * 64,
        status=status,
        required_assurance_level="BASELINE",
        available_assurance_level="MAXIMUM",
        mitigation_hazard_ids=("guard",) if status == "REQUIRES_MITIGATION" else (),
        acceptance_hazard_ids=("operator-risk",)
        if status == "REQUIRES_EXPLICIT_ACCEPTANCE"
        else (),
    )


def authority(capability: str = "rule.waive") -> RuleSourceAuthorityRef:
    return RuleSourceAuthorityRef(
        "principal-1",
        "authority-grant-1",
        "c" * 64,
        capability,
    )


def override_for(
    state: dict,
    *,
    rule_obj: EngineeringRule | None = None,
    risk_obj: RiskAssessment | None = None,
    authority_obj: RuleSourceAuthorityRef | None = None,
    accepted_hazard_ids: tuple[str, ...] | None = None,
) -> tuple[ManualOverride, EngineeringRule, RiskAssessment]:
    rule_obj = rule_obj or rule()
    risk_obj = risk_obj or risk()
    authority_obj = authority_obj or authority()
    item = bind_manual_override(
        rule_obj,
        risk_obj,
        (state["obligations"]["O-review"],),
        principal_id="principal-1",
        authority=authority_obj,
        reason="Operator accepts the bounded policy exception for this revision",
        validity=OverrideValidityWindow("control-sequence", 10, 20),
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
        authority_evidence_ids=("evidence-authority",),
        accepted_hazard_ids=accepted_hazard_ids,
        evidence_ids=("evidence-override-request",),
    )
    return item, rule_obj, risk_obj


def test_vocabularies_and_contract_claim_ceiling_are_exact():
    assert EPISTEMIC_DEBT_CLASSES == ("OUTSTANDING", "TERMINAL_UNRESOLVED")
    assert MANUAL_OVERRIDE_ASSESSMENT_STATUSES == (
        "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW",
        "BLOCKED_HARD_FLOOR",
        "BLOCKED_RULE_POLICY",
        "BLOCKED_AUTHORITY_REFERENCE",
        "BLOCKED_ACCEPTED_RISK",
        "BLOCKED_RESULTING_OBLIGATIONS",
        "OUTSIDE_VALIDITY_WINDOW",
    )
    contract = epistemic_debt_manual_override_contract()
    assert contract["debt_graph"] == "NONE_SECONDARY_OR_PARALLEL"
    assert contract["debt_store"] == "NONE_SECONDARY_OR_PARALLEL"
    assert contract["debt_scalar_score"] == "NONE"
    assert contract["hard_floor_override"] == "FORBIDDEN_UNCONDITIONALLY"
    assert contract["assessment_is_waiver"] is False
    assert contract["assessment_is_authorization"] is False
    assert contract["assessment_mutates_rule"] is False
    assert contract["assessment_mutates_obligation"] is False
    assert contract["parallel_override_registry"] == "NONE"
    assert contract["current_override_pointer"] == "NONE"
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


def test_debt_projection_uses_existing_obligations_edges_and_status_machine():
    state = state_with(
        obligation("O-evidence", required_evidence_types=("hardware-test",)),
        obligation("O-review", dependencies=("O-evidence",), status="BLOCKED"),
        obligation("O-done", status="VERIFIED"),
    )
    projection = project_epistemic_debt(
        state,
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    assert tuple(value.obligation_id for value in projection.items) == (
        "O-evidence",
        "O-review",
    )
    assert projection.outstanding_count == 2
    assert projection.terminal_unresolved_count == 0
    assert projection.items[1].dependency_obligation_ids == ("O-evidence",)
    assert validate_epistemic_debt_projection(state, projection)["valid"] is True
    assert EpistemicDebtProjection.from_dict(projection.to_dict()) == projection


def test_debt_projection_preserves_optional_s4_7_phase_bindings():
    state = state_with(
        obligation("O-auth"),
        obligation("O-review", dependencies=("O-auth",)),
    )
    plan = plan_for(state, {"O-auth": "PRE_AUTHORIZE", "O-review": "POST_VERIFY"})
    projection = project_epistemic_debt(
        state,
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
        phase_plan=plan,
    )
    phases = {value.obligation_id: value.phase for value in projection.items}
    assert phases == {"O-auth": "PRE_AUTHORIZE", "O-review": "POST_VERIFY"}
    assert (
        validate_epistemic_debt_projection(
            state,
            projection,
            phase_plan=plan,
        )["valid"]
        is True
    )


def test_terminal_obligations_remain_visible_as_unresolved_debt():
    for status in ("REJECTED", "SUPERSEDED", "IMPOSSIBLE"):
        state = state_with(obligation("O-terminal", status=status))
        projection = project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        assert projection.items[0].classification == "TERMINAL_UNRESOLVED"
        assert projection.terminal_unresolved_count == 1


def test_verified_and_committed_obligations_clear_projection_without_mutation():
    for status in ("VERIFIED", "COMMITTED"):
        state = state_with(obligation("O-done", status=status))
        before = deepcopy(state)
        projection = project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        assert projection.items == ()
        assert projection.to_dict()["total_debt_count"] == 0
        assert state == before


def test_stale_debt_projection_and_malformed_edge_projection_fail_closed():
    state = state_with(obligation("O-review"))
    projection = project_epistemic_debt(
        state,
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    changed = deepcopy(state)
    changed["obligations"]["O-review"]["statement"] = "Changed requirement"
    with pytest.raises(ValueError, match="stale or mismatched"):
        validate_epistemic_debt_projection(changed, projection)
    malformed = deepcopy(state)
    malformed["obligation_edges"] = [
        {"src": "O-review", "dst": "O-review", "relation": "REQUIRES"}
    ]
    with pytest.raises(ValueError, match="exactly represent"):
        project_epistemic_debt(
            malformed,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )


def test_manual_override_records_exact_required_bindings_and_round_trips():
    state = state_with(obligation("O-review"))
    item, _, _ = override_for(state)
    restored = ManualOverride.from_dict(item.to_dict())
    assert restored == item
    assert restored.principal_id == "principal-1"
    assert restored.workspace_id == "workspace-1"
    assert restored.scope_id == "control"
    assert restored.validity.clock_id == "control-sequence"
    assert restored.accepted_hazard_ids == ("operator-risk",)
    assert restored.authority_evidence_ids == ("evidence-authority",)
    assert restored.resulting_obligations[0].obligation_id == "O-review"


def test_hard_floor_and_nonwaivable_rules_fail_closed():
    state = state_with(obligation("O-review"))
    hard = rule(strength="HARD_FLOOR", waivable=False)
    hard_override, _, risk_obj = override_for(state, rule_obj=hard)
    hard_result = evaluate_manual_override(
        hard_override,
        (hard,),
        (risk_obj,),
        state,
        clock_id="control-sequence",
        sequence=15,
    )
    assert hard_result.status == "BLOCKED_HARD_FLOOR"
    policy = rule(strength="POLICY", waivable=False)
    policy_override, _, risk_obj = override_for(state, rule_obj=policy)
    policy_result = evaluate_manual_override(
        policy_override,
        (policy,),
        (risk_obj,),
        state,
        clock_id="control-sequence",
        sequence=15,
    )
    assert policy_result.status == "BLOCKED_RULE_POLICY"


def test_authority_capability_is_reference_only_and_must_match_rule_policy():
    state = state_with(obligation("O-review"))
    item, rule_obj, risk_obj = override_for(
        state,
        authority_obj=authority("different.capability"),
    )
    result = evaluate_manual_override(
        item,
        (rule_obj,),
        (risk_obj,),
        state,
        clock_id="control-sequence",
        sequence=15,
    )
    assert result.status == "BLOCKED_AUTHORITY_REFERENCE"
    assert result.authority_granted is False
    assert result.effect_authority_granted is False


def test_only_exact_explicit_acceptance_risk_is_eligible():
    state = state_with(obligation("O-review"))
    mitigation = risk("REQUIRES_MITIGATION")
    item, rule_obj, _ = override_for(
        state,
        risk_obj=mitigation,
        accepted_hazard_ids=("operator-risk",),
    )
    result = evaluate_manual_override(
        item,
        (rule_obj,),
        (mitigation,),
        state,
        clock_id="control-sequence",
        sequence=15,
    )
    assert result.status == "BLOCKED_ACCEPTED_RISK"
    accepted = risk()
    changed = deepcopy(item.to_dict())
    changed["accepted_risk_assessment_id"] = accepted.assessment_id
    changed["accepted_risk_assessment_fingerprint"] = accepted.fingerprint
    changed["accepted_hazard_ids"] = ["wrong-hazard"]
    changed.pop("fingerprint")
    changed.pop("override_id")
    mismatch = ManualOverride.from_dict(changed)
    result = evaluate_manual_override(
        mismatch,
        (rule_obj,),
        (accepted,),
        state,
        clock_id="control-sequence",
        sequence=15,
    )
    assert result.status == "BLOCKED_ACCEPTED_RISK"


def test_resulting_obligations_reuse_exact_existing_store_and_must_remain_open():
    state = state_with(obligation("O-review"))
    item, rule_obj, risk_obj = override_for(state)
    stale = deepcopy(state)
    stale["obligations"]["O-review"]["statement"] = "Different obligation"
    with pytest.raises(ValueError, match="stale or mismatched"):
        evaluate_manual_override(
            item,
            (rule_obj,),
            (risk_obj,),
            stale,
            clock_id="control-sequence",
            sequence=15,
        )
    verified = deepcopy(state)
    verified["obligations"]["O-review"]["status"] = "VERIFIED"
    result = evaluate_manual_override(
        item,
        (rule_obj,),
        (risk_obj,),
        verified,
        clock_id="control-sequence",
        sequence=15,
    )
    assert result.status == "BLOCKED_RESULTING_OBLIGATIONS"


def test_validity_uses_explicit_clock_and_sequence_without_hidden_wall_clock():
    state = state_with(obligation("O-review"))
    item, rule_obj, risk_obj = override_for(state)
    for clock_id, sequence in (
        ("other-clock", 15),
        ("control-sequence", 9),
        ("control-sequence", 21),
    ):
        result = evaluate_manual_override(
            item,
            (rule_obj,),
            (risk_obj,),
            state,
            clock_id=clock_id,
            sequence=sequence,
        )
        assert result.status == "OUTSIDE_VALIDITY_WINDOW"
    assert (
        OverrideValidityWindow("control-sequence", 10, 20).to_dict()[
            "not_after_sequence"
        ]
        == 20
    )


def test_admissible_assessment_remains_review_only_and_pure():
    state = state_with(obligation("O-review"))
    item, rule_obj, risk_obj = override_for(state)
    before = deepcopy(state)
    result = evaluate_manual_override(
        item,
        (rule_obj,),
        (risk_obj,),
        state,
        clock_id="control-sequence",
        sequence=15,
    )
    assert result.status == "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW"
    assert state == before
    for name in (
        "waiver_performed",
        "rule_mutated",
        "authority_granted",
        "effect_authority_granted",
        "obligation_mutated",
        "history_deleted",
        "current_override_activated",
    ):
        assert getattr(result, name) is False
    assert ManualOverrideAssessment.from_dict(result.to_dict()) == result


def test_override_resulting_obligation_remains_epistemic_debt_until_verified():
    state = state_with(obligation("O-review"))
    item, rule_obj, risk_obj = override_for(state)
    assert (
        evaluate_manual_override(
            item,
            (rule_obj,),
            (risk_obj,),
            state,
            clock_id="control-sequence",
            sequence=15,
        ).status
        == "ADMISSIBLE_FOR_AUTHORIZATION_REVIEW"
    )
    debt = project_epistemic_debt(
        state,
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    assert tuple(value.obligation_id for value in debt.items) == ("O-review",)
    verified = deepcopy(state)
    verified["obligations"]["O-review"]["status"] = "VERIFIED"
    assert (
        project_epistemic_debt(
            verified,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        ).items
        == ()
    )


def test_binary_float_metadata_and_identity_tampering_fail_closed():
    state = state_with(obligation("O-review"))
    with pytest.raises(TypeError, match="binary floating-point"):
        project_epistemic_debt(
            state,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
            metadata={"confidence": 0.9},
        )
    item, _, _ = override_for(state)
    changed = deepcopy(item.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        ManualOverride.from_dict(changed)


def test_foundation_is_not_public_root_or_runtime_composition():
    assert not hasattr(aasm, "EpistemicDebtProjection")
    assert not hasattr(aasm, "ManualOverride")
    runtime_source = (ROOT / "src/aasm/runtime_v56_foundation.py").read_text(
        encoding="utf-8"
    )
    assert "from .epistemic_debt_manual_override" not in runtime_source
    assert "EpistemicDebtProjection" not in runtime_source
    assert "ManualOverride" not in runtime_source


def test_schemas_are_closed_and_accept_canonical_documents():
    state = state_with(obligation("O-review"))
    debt = project_epistemic_debt(
        state,
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    item, rule_obj, risk_obj = override_for(state)
    assessment = evaluate_manual_override(
        item,
        (rule_obj,),
        (risk_obj,),
        state,
        clock_id="control-sequence",
        sequence=15,
    )
    docs = (
        ("epistemic-debt.schema.json", debt.to_dict()),
        ("manual-override.schema.json", item.to_dict()),
        ("manual-override-assessment.schema.json", assessment.to_dict()),
    )
    for filename, document in docs:
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        validate(document, schema)
        changed = deepcopy(document)
        changed["unknown_field"] = True
        with pytest.raises(ValidationError):
            validate(changed, schema)
