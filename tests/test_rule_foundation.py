from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

import aasm
from aasm._calculus_model import LearnedConstraint
from aasm.decision_vector_ir import DecisionHardFloor
from aasm.rule import (
    EngineeringRule,
    RuleApplicabilityContext,
    RuleApplicabilityPredicate,
    RuleClauseRef,
    RuleControlPolicy,
    RuleScopeSelector,
    RuleSourceAuthorityRef,
    compare_rule_precedence,
    evaluate_rule_applicability,
    rule_contract,
    rule_override_structurally_eligible,
    rule_waiver_structurally_eligible,
)
from aasm.scoped_authority import ScopedAuthorityGrant
from aasm.semantic_evolution import ExternalReference


ROOT = Path(__file__).resolve().parents[1]


def ext(
    external_id: str = "clearance-rule",
    *,
    revision: str = "17",
    role: str = "rule_source",
    namespace: str = "cad",
) -> ExternalReference:
    return ExternalReference(
        namespace,
        external_id,
        role,
        revision=revision,
        source_fingerprint=(external_id[0].lower() if external_id else "a") * 64,
    )


def clause(*, clause_id: str = "clearance-min", fingerprint: str = "c" * 64) -> RuleClauseRef:
    return RuleClauseRef(
        "aasm.semantic.constraint.v1",
        clause_id,
        fingerprint,
        "CONSTRAINT",
        metadata={"source": "engineering"},
    )


def source_authority() -> RuleSourceAuthorityRef:
    grant = ScopedAuthorityGrant(
        subject_principal_id="standards-service",
        issuer_principal_id="workspace-root",
        workspace_id="w",
        scope_id="layout",
        capabilities=("rule.issue",),
        not_before=0.0,
        expires_at=100.0,
    )
    return RuleSourceAuthorityRef(
        "standards-service",
        grant.grant_id,
        grant.fingerprint,
        "rule.issue",
    )


def selector(
    *,
    policy: str = "EXACT",
    scope_id: str = "layout",
    subjects: tuple[str, ...] = ("board",),
    workspace_id: str = "w",
) -> RuleScopeSelector:
    if policy == "ANY_IN_WORKSPACE":
        scope_id = ""
    return RuleScopeSelector(workspace_id, scope_id, policy, subjects)


def rule(**overrides) -> EngineeringRule:
    payload = {
        "rule_id": "pcb-clearance-rule",
        "clause": clause(),
        "strength": "HARD",
        "scope_selector": selector(),
        "applicability": RuleApplicabilityPredicate("ALWAYS"),
        "precedence_group": "pcb-clearance",
        "priority": 10,
        "specificity": 2,
        "control_policy": RuleControlPolicy(),
        "severity": "HIGH",
        "source_authority": source_authority(),
        "problem_revision_id": "problem-revision-17",
        "problem_revision_fingerprint": "d" * 64,
        "applicable_external_references": (ext(),),
        "evidence_ids": ("ev-2", "ev-1"),
        "metadata": {"origin": "standard"},
    }
    payload.update(overrides)
    return EngineeringRule(**payload)


def context(**overrides) -> RuleApplicabilityContext:
    payload = {
        "workspace_id": "w",
        "scope_id": "layout",
        "subject_id": "board",
        "scope_ancestor_ids": ("architecture", "root"),
        "problem_revision_id": "problem-revision-17",
        "problem_revision_fingerprint": "d" * 64,
        "external_references": (ext(),),
        "attributes": {},
        "tags": (),
    }
    payload.update(overrides)
    return RuleApplicabilityContext(**payload)


def test_rule_round_trip_identity_and_external_evidence_order_are_deterministic():
    first = ext("z-rule", namespace="z")
    second = ext("a-rule", namespace="a")
    item = rule(
        applicable_external_references=(first, second),
        evidence_ids=("z-evidence", "a-evidence", "z-evidence"),
    )
    restored = EngineeringRule.from_dict(item.to_dict())
    assert restored.rule_revision_id == item.rule_revision_id
    assert restored.fingerprint == item.fingerprint
    assert [row.namespace for row in item.applicable_external_references] == ["a", "z"]
    assert item.evidence_ids == ("a-evidence", "z-evidence")


def test_rule_schema_is_closed_portable_and_accepts_canonical_rule():
    schema = json.loads((ROOT / "schemas/rule.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    validate(rule().to_dict(), schema)
    assert schema["additionalProperties"] is False
    assert schema["properties"]["contract_id"]["const"] == "aasm.rule.v1"
    assert schema["properties"]["contract_version"]["const"] == "0.1.0"
    assert schema["properties"]["strength"]["enum"] == [
        "HARD_FLOOR",
        "HARD",
        "POLICY",
        "PREFERENCE",
        "ADVISORY",
    ]

    changed = deepcopy(rule().to_dict())
    changed["unknown_field"] = True
    with pytest.raises(ValidationError):
        validate(changed, schema)

    changed = deepcopy(rule().to_dict())
    changed["priority"] = 1.25
    with pytest.raises(ValidationError):
        validate(changed, schema)

    changed = deepcopy(rule().to_dict())
    changed["metadata"] = {"score": 0.1}
    with pytest.raises(ValidationError):
        validate(changed, schema)


def test_binary_float_executable_predicates_and_portable_integer_overflow_fail_closed():
    with pytest.raises(TypeError, match="binary floating-point"):
        rule(metadata={"score": 0.1})
    with pytest.raises(TypeError, match="binary floating-point"):
        RuleApplicabilityContext("w", "layout", "board", attributes={"temperature": 22.5})
    with pytest.raises(TypeError, match="portable scalar"):
        RuleApplicabilityPredicate("CONTEXT_MATCH", required_attributes={"predicate": lambda: True})
    with pytest.raises(ValueError, match="portable signed 63-bit"):
        rule(priority=1 << 63)
    with pytest.raises(ValueError, match="portable non-negative 31-bit"):
        rule(specificity=1 << 31)


def test_scope_selector_is_explicit_and_invalid_shapes_fail_closed():
    assert RuleScopeSelector("w", "", "ANY_IN_WORKSPACE").match_policy == "ANY_IN_WORKSPACE"
    assert RuleScopeSelector("w", "layout", "EXACT").scope_id == "layout"
    assert RuleScopeSelector("w", "architecture", "DESCENDANT_OR_SELF").scope_id == "architecture"
    with pytest.raises(ValueError, match="must not carry scope_id"):
        RuleScopeSelector("w", "layout", "ANY_IN_WORKSPACE")
    with pytest.raises(ValueError, match="requires scope_id"):
        RuleScopeSelector("w", "", "EXACT")


def test_scope_and_subject_applicability_is_deterministic():
    assert evaluate_rule_applicability(rule(), context()).result == "APPLICABLE"
    assert evaluate_rule_applicability(rule(), context(scope_id="routing")).result == "NOT_APPLICABLE"
    assert evaluate_rule_applicability(rule(), context(subject_id="enclosure")).result == "NOT_APPLICABLE"

    descendant = rule(scope_selector=selector(policy="DESCENDANT_OR_SELF", scope_id="architecture"))
    assert evaluate_rule_applicability(descendant, context()).result == "APPLICABLE"
    assert evaluate_rule_applicability(descendant, context(scope_ancestor_ids=("root",))).result == "NOT_APPLICABLE"

    workspace_rule = rule(scope_selector=selector(policy="ANY_IN_WORKSPACE", subjects=()))
    assert evaluate_rule_applicability(workspace_rule, context(scope_id="anything", subject_id="anything")).result == "APPLICABLE"
    assert evaluate_rule_applicability(workspace_rule, context(workspace_id="other")).result == "NOT_APPLICABLE"


def test_problem_revision_applicability_distinguishes_missing_mismatch_and_exact():
    item = rule()
    missing = context(problem_revision_id="", problem_revision_fingerprint="")
    assessment = evaluate_rule_applicability(item, missing)
    assert assessment.result == "INDETERMINATE"
    assert assessment.reasons == ("PROBLEM_REVISION_CONTEXT_MISSING",)

    mismatched = context(problem_revision_id="problem-revision-18", problem_revision_fingerprint="e" * 64)
    assessment = evaluate_rule_applicability(item, mismatched)
    assert assessment.result == "NOT_APPLICABLE"
    assert assessment.reasons == ("PROBLEM_REVISION_MISMATCH",)

    assert evaluate_rule_applicability(item, context()).result == "APPLICABLE"


def test_problem_revision_id_and_fingerprint_are_atomic_pairs():
    with pytest.raises(ValueError, match="supplied together"):
        rule(problem_revision_id="problem-revision-17", problem_revision_fingerprint="")
    with pytest.raises(ValueError, match="supplied together"):
        RuleApplicabilityContext(
            "w",
            "layout",
            "board",
            problem_revision_id="problem-revision-17",
            problem_revision_fingerprint="",
        )


def test_external_revision_applicability_distinguishes_missing_mismatch_and_exact():
    item = rule(problem_revision_id="", problem_revision_fingerprint="")
    missing = context(
        problem_revision_id="",
        problem_revision_fingerprint="",
        external_references=(),
    )
    assessment = evaluate_rule_applicability(item, missing)
    assert assessment.result == "INDETERMINATE"
    assert assessment.reasons == ("EXTERNAL_REFERENCE_CONTEXT_MISSING:cad:clearance-rule:rule_source",)

    mismatched = context(
        problem_revision_id="",
        problem_revision_fingerprint="",
        external_references=(ext(revision="18"),),
    )
    assessment = evaluate_rule_applicability(item, mismatched)
    assert assessment.result == "NOT_APPLICABLE"
    assert assessment.reasons == ("EXTERNAL_REFERENCE_MISMATCH:cad:clearance-rule:rule_source",)

    exact = context(
        problem_revision_id="",
        problem_revision_fingerprint="",
        external_references=(ext(),),
    )
    assert evaluate_rule_applicability(item, exact).result == "APPLICABLE"


def test_duplicate_external_reference_identity_is_rejected_in_rule_and_context():
    current = ext(revision="17")
    competing = ext(revision="18")
    with pytest.raises(ValueError, match="duplicate external reference identity"):
        rule(applicable_external_references=(current, competing))
    with pytest.raises(ValueError, match="duplicate external reference identity"):
        context(external_references=(current, competing))
    with pytest.raises(ValueError, match="duplicate external reference"):
        context(external_references=(current, current))


def test_context_match_predicate_is_portable_tri_state_and_fail_closed():
    predicate = RuleApplicabilityPredicate(
        "CONTEXT_MATCH",
        required_attributes={"mode": "production", "layer_count": 4},
        forbidden_attribute_values={"phase": "prototype"},
        required_tags=("ipc-2221",),
        forbidden_tags=("waived",),
    )
    item = rule(applicability=predicate)
    full = context(
        attributes={"mode": "production", "layer_count": 4, "phase": "production"},
        tags=("ipc-2221",),
    )
    assert evaluate_rule_applicability(item, full).result == "APPLICABLE"

    missing_attribute = context(attributes={"mode": "production"}, tags=("ipc-2221",))
    assessment = evaluate_rule_applicability(item, missing_attribute)
    assert assessment.result == "INDETERMINATE"
    assert "REQUIRED_ATTRIBUTE_MISSING:layer_count" in assessment.reasons

    wrong_attribute = context(attributes={"mode": "prototype", "layer_count": 4}, tags=("ipc-2221",))
    assert evaluate_rule_applicability(item, wrong_attribute).result == "NOT_APPLICABLE"

    forbidden_value = context(
        attributes={"mode": "production", "layer_count": 4, "phase": "prototype"},
        tags=("ipc-2221",),
    )
    assert evaluate_rule_applicability(item, forbidden_value).result == "NOT_APPLICABLE"

    missing_tag = context(attributes={"mode": "production", "layer_count": 4})
    assert evaluate_rule_applicability(item, missing_tag).result == "NOT_APPLICABLE"

    forbidden_tag = context(
        attributes={"mode": "production", "layer_count": 4},
        tags=("ipc-2221", "waived"),
    )
    assert evaluate_rule_applicability(item, forbidden_tag).result == "NOT_APPLICABLE"


def test_self_contradictory_predicates_are_rejected():
    with pytest.raises(ValueError, match="same attribute value"):
        RuleApplicabilityPredicate(
            "CONTEXT_MATCH",
            required_attributes={"mode": "production"},
            forbidden_attribute_values={"mode": "production"},
        )
    with pytest.raises(ValueError, match="same tag"):
        RuleApplicabilityPredicate(
            "CONTEXT_MATCH",
            required_tags=("required",),
            forbidden_tags=("required",),
        )
    with pytest.raises(ValueError, match="cannot carry"):
        RuleApplicabilityPredicate("ALWAYS", required_tags=("unexpected",))
    with pytest.raises(ValueError, match="requires at least one"):
        RuleApplicabilityPredicate("CONTEXT_MATCH")


def test_precedence_is_strength_then_specificity_then_priority_only_within_group():
    hard = rule(strength="HARD", specificity=0, priority=-100)
    policy = rule(strength="POLICY", specificity=100, priority=100000)
    assert compare_rule_precedence(hard, policy) == "LEFT_PRECEDES"

    specific = rule(strength="HARD", specificity=3, priority=0)
    broad = rule(strength="HARD", specificity=2, priority=1000)
    assert compare_rule_precedence(specific, broad) == "LEFT_PRECEDES"

    high_priority = rule(strength="HARD", specificity=2, priority=11)
    low_priority = rule(strength="HARD", specificity=2, priority=10)
    assert compare_rule_precedence(high_priority, low_priority) == "LEFT_PRECEDES"

    equivalent = rule(rule_id="another-rule", clause=clause(clause_id="other", fingerprint="f" * 64))
    assert compare_rule_precedence(rule(), equivalent) == "EQUIVALENT_PRECEDENCE"

    other_group = rule(precedence_group="different")
    assert compare_rule_precedence(rule(), other_group) == "INCOMPARABLE"


def test_hard_floor_cannot_be_waived_or_overridden_even_by_control_policy():
    hard_floor = rule(strength="HARD_FLOOR", control_policy=RuleControlPolicy())
    assert rule_waiver_structurally_eligible(hard_floor, "rule.waive") is False
    assert rule_override_structurally_eligible(hard_floor, rule(strength="HARD_FLOOR"), "rule.override") is False
    with pytest.raises(ValueError, match="HARD_FLOOR"):
        rule(
            strength="HARD_FLOOR",
            control_policy=RuleControlPolicy(
                "EXPLICIT_AUTHORIZED",
                "FORBIDDEN",
                "rule.waive",
            ),
        )


def test_waiver_structural_eligibility_requires_exact_capability_but_is_not_authority():
    item = rule(
        control_policy=RuleControlPolicy(
            "EXPLICIT_AUTHORIZED",
            "FORBIDDEN",
            "rule.waive",
        )
    )
    assert rule_waiver_structurally_eligible(item, "rule.waive") is True
    assert rule_waiver_structurally_eligible(item, "rule.override") is False
    contract = rule_contract()
    assert contract["waiver_override_authority"] == "STRUCTURAL_ELIGIBILITY_ONLY_EXISTING_SCOPED_AUTHORITY_MUST_AUTHORIZE_LATER_RUNTIME_ACTION"
    assert contract["precedence_authorizes_override"] is False


def test_override_structural_eligibility_obeys_explicit_strength_policy_not_objective_priority():
    strict = rule(
        strength="POLICY",
        control_policy=RuleControlPolicy(
            "FORBIDDEN",
            "STRICTLY_STRONGER_EXPLICIT",
            "rule.override",
        ),
    )
    stronger = rule(strength="HARD")
    same_strength_higher_specificity = rule(strength="POLICY", specificity=100, priority=100)
    assert rule_override_structurally_eligible(strict, stronger, "rule.override") is True
    assert rule_override_structurally_eligible(strict, same_strength_higher_specificity, "rule.override") is False
    assert rule_override_structurally_eligible(strict, stronger, "wrong.capability") is False
    assert rule_override_structurally_eligible(strict, rule(strength="HARD", precedence_group="other"), "rule.override") is False

    same_or_stronger = rule(
        strength="HARD",
        control_policy=RuleControlPolicy(
            "FORBIDDEN",
            "SAME_OR_STRONGER_EXPLICIT",
            "rule.override",
        ),
    )
    assert rule_override_structurally_eligible(same_or_stronger, rule(strength="HARD"), "rule.override") is True
    assert rule_override_structurally_eligible(same_or_stronger, rule(strength="POLICY"), "rule.override") is False


def test_control_policy_requires_capability_exactly_when_explicit_action_is_possible():
    with pytest.raises(ValueError, match="requires required_capability"):
        RuleControlPolicy("EXPLICIT_AUTHORIZED", "FORBIDDEN", "")
    with pytest.raises(ValueError, match="requires required_capability"):
        RuleControlPolicy("FORBIDDEN", "STRICTLY_STRONGER_EXPLICIT", "")
    with pytest.raises(ValueError, match="must not carry"):
        RuleControlPolicy("FORBIDDEN", "FORBIDDEN", "rule.override")


def test_source_authority_is_exact_reference_only_and_does_not_verify_or_mint_authority():
    fake = RuleSourceAuthorityRef("principal", "nonexistent-grant", "a" * 64, "rule.issue")
    item = rule(source_authority=fake)
    assert item.source_authority == fake
    contract = rule_contract()
    assert contract["source_authority"] == "EXACT_EXISTING_SCOPED_AUTHORITY_GRANT_REFERENCE_ONLY_NOT_VERIFIED_BY_FOUNDATION"
    assert contract["rule_existence_grants_source_authority"] is False
    assert contract["parallel_authority_evaluator"] == "NONE"


def test_clause_authority_rule_and_context_tampering_fail_closed():
    ref = clause()
    changed = deepcopy(ref.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="clause fingerprint"):
        RuleClauseRef.from_dict(changed)

    authority = source_authority()
    changed = deepcopy(authority.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="authority reference fingerprint"):
        RuleSourceAuthorityRef.from_dict(changed)

    item = rule()
    changed = deepcopy(item.to_dict())
    changed["rule_revision_id"] = "rule-revision-" + "0" * 24
    with pytest.raises(ValueError, match="rule_revision_id"):
        EngineeringRule.from_dict(changed)

    changed = deepcopy(item.to_dict())
    changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="engineering rule fingerprint"):
        EngineeringRule.from_dict(changed)

    changed = deepcopy(item.to_dict())
    changed["clause"]["clause_fingerprint"] = "1" * 64
    with pytest.raises(ValueError, match="rule_revision_id"):
        EngineeringRule.from_dict(changed)

    ctx = context()
    changed_context = deepcopy(ctx.to_dict())
    changed_context["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="context fingerprint"):
        RuleApplicabilityContext.from_dict(changed_context)


def test_metadata_and_external_reference_payloads_cannot_smuggle_float_identity():
    with pytest.raises(TypeError, match="binary floating-point"):
        RuleClauseRef("x", "y", "a" * 64, metadata={"score": 0.5})
    floating_ref = ExternalReference("cad", "r", "rule_source", metadata={"confidence": 0.9})
    with pytest.raises(TypeError, match="binary floating-point"):
        rule(applicable_external_references=(floating_ref,))


def test_rule_foundation_is_distinct_from_formal_calculus_learned_constraints():
    hard = LearnedConstraint(
        "learned-hard",
        [{"subject": "route", "op": "EQ", "value": "A"}],
        "conflict-1",
        "explanation-1",
        ["evidence-1"],
        strength="HARD",
    )
    soft = LearnedConstraint(
        "learned-soft",
        [{"subject": "route", "op": "EQ", "value": "B"}],
        "conflict-2",
        "explanation-2",
        ["evidence-2"],
        strength="SOFT",
    )
    assert hard.strength == "HARD"
    assert soft.strength == "SOFT"
    with pytest.raises(ValueError, match="HARD or SOFT"):
        LearnedConstraint(
            "learned-invalid",
            [{"subject": "route", "op": "EQ", "value": "C"}],
            "conflict-3",
            "explanation-3",
            ["evidence-3"],
            strength="HARD_FLOOR",
        )
    assert rule_contract()["learned_constraint_relation"] == "DISTINCT_NO_IMPLICIT_MAPPING_TO_FORMAL_CALCULUS_HARD_SOFT"
    assert rule_contract()["rule_to_constraint_lowering"] == "NONE_FOUNDATION_ONLY_EXPLICIT_VERSIONED_FUTURE_CONTRACT_REQUIRED"


def test_existing_decision_vector_hard_floor_remains_separate_and_unchanged():
    floor = DecisionHardFloor(
        "floor-1",
        "clearance",
        ">=",
        0.5,
        coefficients={"x": 1.0},
    )
    assert floor.threshold == 0.5
    assert floor.passes(0.5) is True
    assert floor.passes(0.49) is False
    assert rule_contract()["precedence_is_objective_priority"] is False


def test_rule_contract_firewalls_and_pre_admission_boundary_are_explicit():
    contract = rule_contract()
    assert contract["contract_id"] == "aasm.rule.v1"
    assert contract["contract_version"] == "0.1.0"
    assert contract["strengths"] == ["HARD_FLOOR", "HARD", "POLICY", "PREFERENCE", "ADVISORY"]
    assert contract["applicability"] == "EXPLICIT_PORTABLE_CONTEXT_MATCH_TRI_STATE_FAIL_CLOSED"
    assert contract["predicate_scope"] == "ALWAYS_OR_EXACT_CONTEXT_MATCH_ONLY_NO_EXECUTABLE_CALLBACKS"
    assert contract["revision_applicability"] == "EXACT_PROBLEM_AND_EXTERNAL_REFERENCE_IDENTITY"
    assert contract["precedence"] == "STRENGTH_THEN_SPECIFICITY_THEN_PRIORITY_WITHIN_EXPLICIT_GROUP"
    assert contract["precedence_is_objective_priority"] is False
    assert contract["precedence_authorizes_override"] is False
    assert contract["hard_floor_waiver"] == "FORBIDDEN"
    assert contract["hard_floor_override"] == "FORBIDDEN"
    assert contract["parallel_rule_registry"] == "NONE"
    assert contract["current_rule_pointer"] == "NONE"
    assert contract["parallel_constraint_engine"] == "NONE"
    assert contract["parallel_authority_evaluator"] == "NONE"
    assert contract["rule_existence_grants_fact_authority"] is False
    assert contract["rule_existence_grants_effect_authority"] is False
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


def test_rule_public_admission_does_not_imply_runtime_composition():
    contract = aasm.public_api_contract()
    assert contract["contract_version"] in {"0.32.16", "0.32.17", "0.32.18"}
    if contract["contract_version"] == "0.32.16":
        assert "engineering_rule" not in contract
        assert not hasattr(aasm, "EngineeringRule")
    else:
        public_rule = contract["engineering_rule"]
        assert public_rule["contract_id"] == "aasm.rule.v1"
        assert public_rule["public_admission"] == "QUALIFIED"
        assert public_rule["runtime_admission"] == "PRE_ADMISSION_ONLY"
        assert hasattr(aasm, "EngineeringRule")
    if contract["contract_version"] == "0.32.18":
        assert contract["parent_contract_version"] == "0.32.17"
        assert contract["semantic_projection"]["runtime_admission"] == "PRE_ADMISSION_ONLY"
    runtime_source = (ROOT / "src/aasm/runtime_v56_foundation.py").read_text(encoding="utf-8")
    assert "EngineeringRule" not in runtime_source
    assert "from .rule" not in runtime_source
