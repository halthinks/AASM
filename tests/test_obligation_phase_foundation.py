from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError, validate

import aasm
from aasm.calculus import OBLIGATION_TRANSITIONS, ObligationRecord, default_calculus_state, normalize_calculus_state
from aasm.obligation_phase import (
    NORMAL_OBLIGATION_PHASES,
    OBLIGATION_BINDING_PROJECTION_ID,
    OBLIGATION_PHASES,
    ObligationPhaseAssessment,
    ObligationPhaseBinding,
    ObligationPhasePlan,
    assess_obligation_phase_readiness,
    bind_obligation_phase,
    obligation_binding_projection,
    obligation_phase_contract,
    obligation_semantic_fingerprint,
    phase_relation,
    validate_obligation_phase_binding,
    validate_obligation_phase_plan,
)


ROOT = Path(__file__).resolve().parents[1]
REVISION_ID = "problem-revision-s4-7"
REVISION_FINGERPRINT = "7" * 64


def obligation(
    obligation_id: str,
    *,
    status: str = "AVAILABLE",
    dependencies: tuple[str, ...] = (),
    required_evidence_types: tuple[str, ...] = (),
    scope_id: str = "root",
) -> ObligationRecord:
    return ObligationRecord(
        obligation_id,
        f"Obligation {obligation_id}",
        status=status,
        dependencies=list(dependencies),
        required_evidence_types=list(required_evidence_types),
        scope={"scope_id": scope_id},
    )


def state_with(*records: ObligationRecord) -> dict:
    state = default_calculus_state()
    for record in records:
        state["obligations"][record.obligation_id] = record.to_dict()
        for dependency in record.dependencies:
            state["obligation_edges"].append({"src": dependency, "dst": record.obligation_id, "relation": "REQUIRES"})
    return normalize_calculus_state(state)


def plan_for(state: dict, phases: dict[str, str]) -> ObligationPhasePlan:
    bindings = tuple(
        bind_obligation_phase(
            state["obligations"][obligation_id],
            phase,
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        for obligation_id, phase in sorted(phases.items())
    )
    return ObligationPhasePlan(REVISION_ID, REVISION_FINGERPRINT, bindings)


def test_phase_vocabulary_order_and_recovery_orthogonality_are_exact():
    assert OBLIGATION_PHASES == (
        "PRE_AUTHORIZE",
        "PRE_DISPATCH",
        "POST_DISPATCH",
        "POST_OBSERVE",
        "POST_VERIFY",
        "RECOVERY",
    )
    assert NORMAL_OBLIGATION_PHASES == OBLIGATION_PHASES[:-1]
    assert phase_relation("PRE_AUTHORIZE", "PRE_DISPATCH") == "PRECEDES"
    assert phase_relation("POST_VERIFY", "PRE_AUTHORIZE") == "FOLLOWS"
    assert phase_relation("POST_DISPATCH", "POST_DISPATCH") == "SAME_PHASE"
    assert phase_relation("RECOVERY", "POST_VERIFY") == "INCOMPARABLE"
    assert phase_relation("PRE_AUTHORIZE", "RECOVERY") == "INCOMPARABLE"


def test_contract_reuses_existing_calculus_and_has_strict_claim_ceiling():
    contract = obligation_phase_contract()
    assert contract["contract_id"] == "aasm.obligation.phase.v1"
    assert contract["calculus_contract_id"] == "aasm.calculus.v1"
    assert contract["calculus_state_schema_version"] == 1
    assert contract["obligation_type"] == "EXISTING_AASM_CALCULUS_V1_OBLIGATION_RECORD_ONLY"
    assert contract["obligation_identity"] == "EXISTING_OBLIGATION_ID_UNCHANGED_NO_NEW_OBLIGATION_IDENTITY"
    assert contract["binding_projection_id"] == "aasm.obligation.phase.binding-projection.v1"
    assert contract["binding_projection"] == "VERSIONED_STABLE_REQUIREMENT_PROJECTION_HASHED_WITH_EXISTING_CALCULUS_CONTENT_HASH"
    assert contract["binding_projection_is_obligation_identity"] is False
    assert "status" in contract["binding_projection_excludes_runtime_fields"]
    assert "evidence_ids" in contract["binding_projection_excludes_runtime_fields"]
    assert "lock_ids" in contract["binding_projection_excludes_runtime_fields"]
    assert contract["obligation_store"] == "EXISTING_AASM_CALCULUS_V1_ONLY"
    assert contract["obligation_edges"] == "EXISTING_AASM_CALCULUS_V1_REQUIRES_EDGES_ONLY"
    assert contract["obligation_status_machine"] == "EXISTING_AASM_CALCULUS_V1_OBLIGATION_TRANSITIONS_UNCHANGED"
    assert contract["recovery_phase_order"] == "ORTHOGONAL_NO_IMPLICIT_PRECEDENCE"
    assert contract["obligation_mutation"] == "NONE"
    assert contract["phase_activation"] == "NONE"
    assert contract["effect_authorization"] == "NONE"
    assert contract["effect_dispatch"] == "NONE"
    assert contract["recovery_execution"] == "NONE"
    assert contract["current_phase_pointer"] == "NONE"
    assert contract["parallel_obligation_store"] == "NONE"
    assert contract["parallel_obligation_lifecycle"] == "NONE"
    assert contract["parallel_authority_evaluator"] == "NONE"
    assert contract["parallel_dispatcher"] == "NONE"
    assert contract["phase_readiness_grants_fact_authority"] is False
    assert contract["phase_readiness_grants_effect_authority"] is False
    assert contract["phase_readiness_accepts_artifact"] is False
    assert contract["phase_readiness_proves_obligation"] is False
    assert contract["phase_readiness_mutates_status"] is False
    assert contract["phase_readiness_executes_recovery"] is False
    assert contract["runtime_admission"] == "PRE_ADMISSION_ONLY"
    assert contract["public_admission"] == "PRE_ADMISSION_ONLY"


def test_binding_uses_exact_obligation_semantic_projection_scope_and_revision():
    state = state_with(obligation("O-auth"))
    row = state["obligations"]["O-auth"]
    binding = bind_obligation_phase(
        row,
        "PRE_AUTHORIZE",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    report = validate_obligation_phase_binding(binding, row)
    assert report["valid"] is True
    assert report["binding_projection_id"] == OBLIGATION_BINDING_PROJECTION_ID
    assert binding.obligation_semantic_fingerprint == obligation_semantic_fingerprint(row)
    projection = obligation_binding_projection(row)
    assert projection["projection_id"] == OBLIGATION_BINDING_PROJECTION_ID
    assert projection["obligation_id"] == "O-auth"
    assert "status" not in projection
    assert "evidence_ids" not in projection
    assert "artifact_ids" not in projection
    assert "lock_ids" not in projection
    assert binding.scope_id == "root"
    assert binding.problem_revision_id == REVISION_ID
    assert ObligationPhaseBinding.from_dict(binding.to_dict()) == binding


def test_runtime_progress_changes_do_not_stale_binding_but_semantic_requirement_changes_do():
    state = state_with(obligation("O-verify", required_evidence_types=("integration_test",)))
    original = state["obligations"]["O-verify"]
    binding = bind_obligation_phase(
        original,
        "POST_VERIFY",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    runtime_changed = deepcopy(original)
    runtime_changed["status"] = "VERIFIED"
    runtime_changed["attempt_count"] = 99
    runtime_changed["created_sequence"] = 10
    runtime_changed["last_state_change_sequence"] = 123
    runtime_changed["evidence_ids"] = ["evidence-new"]
    runtime_changed["artifact_ids"] = ["artifact-new"]
    runtime_changed["lock_ids"] = ["lock-new"]
    runtime_changed["disposition_reason"] = "runtime progress only"
    assert obligation_semantic_fingerprint(runtime_changed) == binding.obligation_semantic_fingerprint
    assert validate_obligation_phase_binding(binding, runtime_changed)["valid"] is True

    semantic_change = deepcopy(original)
    semantic_change["required_evidence_types"] = ["integration_test", "hardware_test"]
    assert obligation_semantic_fingerprint(semantic_change) != binding.obligation_semantic_fingerprint
    with pytest.raises(ValueError, match="stale or mismatched"):
        validate_obligation_phase_binding(binding, semantic_change)


def test_statement_activation_dependency_and_scope_changes_stale_phase_binding():
    state = state_with(obligation("O-auth"))
    original = state["obligations"]["O-auth"]
    binding = bind_obligation_phase(
        original,
        "PRE_AUTHORIZE",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    variants = []
    changed = deepcopy(original); changed["statement"] = "Changed requirement"; variants.append(changed)
    changed = deepcopy(original); changed["activation_condition"] = {"const": False}; variants.append(changed)
    changed = deepcopy(original); changed["decision_dependencies"] = ["decision-x"]; variants.append(changed)
    changed = deepcopy(original); changed["scope"] = {"scope_id": "implementation"}; variants.append(changed)
    changed = deepcopy(original); changed["mandatory"] = False; variants.append(changed)
    for changed in variants:
        assert obligation_semantic_fingerprint(changed) != binding.obligation_semantic_fingerprint
        with pytest.raises(ValueError, match="stale or mismatched"):
            validate_obligation_phase_binding(binding, changed)


def test_plan_requires_exactly_one_binding_for_every_existing_obligation():
    state = state_with(obligation("O-auth"), obligation("O-dispatch"))
    complete = plan_for(state, {"O-auth": "PRE_AUTHORIZE", "O-dispatch": "PRE_DISPATCH"})
    report = validate_obligation_phase_plan(state, complete)
    assert report["obligation_count"] == 2
    assert report["binding_projection_id"] == OBLIGATION_BINDING_PROJECTION_ID
    incomplete = ObligationPhasePlan(REVISION_ID, REVISION_FINGERPRINT, (complete.bindings[0],))
    with pytest.raises(ValueError, match="bind every existing obligation exactly once"):
        validate_obligation_phase_plan(state, incomplete)
    with pytest.raises(ValueError, match="exactly one binding"):
        ObligationPhasePlan(REVISION_ID, REVISION_FINGERPRINT, (complete.bindings[0], complete.bindings[0]))


def test_forward_normal_dependency_is_valid_and_backward_normal_dependency_fails_closed():
    forward_state = state_with(
        obligation("O-auth"),
        obligation("O-dispatch", dependencies=("O-auth",)),
    )
    forward = plan_for(forward_state, {"O-auth": "PRE_AUTHORIZE", "O-dispatch": "PRE_DISPATCH"})
    report = validate_obligation_phase_plan(forward_state, forward)
    assert report["edge_count"] == 1
    assert report["recovery_edges"] == []

    backward_state = state_with(
        obligation("O-late"),
        obligation("O-early", dependencies=("O-late",)),
    )
    backward = plan_for(backward_state, {"O-late": "POST_VERIFY", "O-early": "PRE_AUTHORIZE"})
    with pytest.raises(ValueError, match="points backward"):
        validate_obligation_phase_plan(backward_state, backward)


def test_dependency_record_and_edge_projection_must_agree_exactly():
    state = state_with(
        obligation("O-auth"),
        obligation("O-dispatch", dependencies=("O-auth",)),
    )
    plan = plan_for(state, {"O-auth": "PRE_AUTHORIZE", "O-dispatch": "PRE_DISPATCH"})
    missing_edge = deepcopy(state); missing_edge["obligation_edges"] = []
    with pytest.raises(ValueError, match="exactly represent"):
        validate_obligation_phase_plan(missing_edge, plan)
    duplicate_edge = deepcopy(state); duplicate_edge["obligation_edges"].append(deepcopy(duplicate_edge["obligation_edges"][0]))
    with pytest.raises(ValueError, match="duplicate canonical obligation edge"):
        validate_obligation_phase_plan(duplicate_edge, plan)


def test_recovery_dependencies_are_explicit_edges_without_implicit_phase_order():
    state = state_with(
        obligation("O-normal"),
        obligation("O-recovery", dependencies=("O-normal",)),
    )
    plan = plan_for(state, {"O-normal": "POST_VERIFY", "O-recovery": "RECOVERY"})
    report = validate_obligation_phase_plan(state, plan)
    assert report["recovery_phase_order"] == "INCOMPARABLE_USE_EXPLICIT_REQUIRES_EDGES_ONLY"
    assert report["recovery_edges"] == [
        {"src": "O-normal", "dst": "O-recovery", "src_phase": "POST_VERIFY", "dst_phase": "RECOVERY"}
    ]

    inverse = state_with(
        obligation("O-recovery"),
        obligation("O-normal", dependencies=("O-recovery",)),
    )
    inverse_plan = plan_for(inverse, {"O-recovery": "RECOVERY", "O-normal": "PRE_AUTHORIZE"})
    assert validate_obligation_phase_plan(inverse, inverse_plan)["recovery_edges"]


def test_phase_readiness_uses_existing_status_machine_without_mutating_it():
    state = state_with(obligation("O-auth", status="AVAILABLE"))
    plan = plan_for(state, {"O-auth": "PRE_AUTHORIZE"})
    before = deepcopy(state)
    pending = assess_obligation_phase_readiness(
        state,
        plan,
        "PRE_AUTHORIZE",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    assert pending.readiness == "NOT_READY"
    assert pending.blocking_obligation_ids == ("O-auth",)
    assert pending.effect_authority_granted is False
    assert pending.authorization_performed is False
    assert pending.dispatch_performed is False
    assert pending.recovery_execution_performed is False
    assert pending.obligation_status_mutated is False
    assert pending.phase_activated is False
    assert state == before

    verified_state = deepcopy(state)
    verified_state["obligations"]["O-auth"]["status"] = "VERIFIED"
    ready = assess_obligation_phase_readiness(
        verified_state,
        plan,
        "PRE_AUTHORIZE",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    assert ready.readiness == "READY"
    assert ready.satisfied_obligation_ids == ("O-auth",)
    assert ObligationPhaseAssessment.from_dict(ready.to_dict()) == ready


def test_terminal_obligation_disposition_is_not_treated_as_phase_success():
    for status in ("REJECTED", "SUPERSEDED", "IMPOSSIBLE"):
        state = state_with(obligation("O-terminal", status=status))
        plan = plan_for(state, {"O-terminal": "POST_VERIFY"})
        assessment = assess_obligation_phase_readiness(
            state,
            plan,
            "POST_VERIFY",
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
        assert assessment.readiness == "TERMINAL_UNSATISFIED"
        assert assessment.terminal_unsatisfied_obligation_ids == ("O-terminal",)


def test_empty_phase_is_ready_only_because_complete_plan_proves_no_obligations_are_bound_there():
    state = state_with(obligation("O-auth", status="VERIFIED"))
    plan = plan_for(state, {"O-auth": "PRE_AUTHORIZE"})
    assessment = assess_obligation_phase_readiness(
        state,
        plan,
        "POST_DISPATCH",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    assert assessment.readiness == "READY"
    assert assessment.required_obligation_ids == ()
    assert assessment.reasons == ("NO_OBLIGATIONS_FOR_PHASE",)


def test_revision_and_scope_mismatch_fail_closed():
    state = state_with(obligation("O-auth", scope_id="implementation"))
    correct = bind_obligation_phase(
        state["obligations"]["O-auth"],
        "PRE_AUTHORIZE",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    wrong_scope = ObligationPhaseBinding(
        correct.obligation_id,
        correct.obligation_semantic_fingerprint,
        correct.phase,
        correct.problem_revision_id,
        correct.problem_revision_fingerprint,
        scope_id="root",
    )
    with pytest.raises(ValueError, match="scope_id mismatch"):
        validate_obligation_phase_binding(wrong_scope, state["obligations"]["O-auth"])

    plan = ObligationPhasePlan(REVISION_ID, REVISION_FINGERPRINT, (correct,))
    with pytest.raises(ValueError, match="exact plan ProblemRevision"):
        assess_obligation_phase_readiness(
            state,
            plan,
            "PRE_AUTHORIZE",
            problem_revision_id="different-revision",
            problem_revision_fingerprint="8" * 64,
        )


def test_binary_float_metadata_activation_and_identity_tampering_fail_closed():
    state = state_with(obligation("O-auth"))
    row = state["obligations"]["O-auth"]
    with pytest.raises(TypeError, match="binary floating-point"):
        bind_obligation_phase(
            row,
            "PRE_AUTHORIZE",
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
            metadata={"confidence": 0.9},
        )
    float_activation = deepcopy(row)
    float_activation["activation_condition"] = {"threshold": 0.5}
    with pytest.raises(TypeError, match="binary floating-point"):
        bind_obligation_phase(
            float_activation,
            "PRE_AUTHORIZE",
            problem_revision_id=REVISION_ID,
            problem_revision_fingerprint=REVISION_FINGERPRINT,
        )
    binding = bind_obligation_phase(
        row,
        "PRE_AUTHORIZE",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    changed = deepcopy(binding.to_dict()); changed["fingerprint"] = "0" * 64
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        ObligationPhaseBinding.from_dict(changed)


def test_existing_obligation_status_machine_is_not_redefined_or_weakened():
    assert OBLIGATION_TRANSITIONS["AVAILABLE"] == {"ENABLED", "BLOCKED", "LOCKED", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
    assert OBLIGATION_TRANSITIONS["ENABLED"] == {"IN_PROGRESS", "BLOCKED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
    assert OBLIGATION_TRANSITIONS["IN_PROGRESS"] == {"VERIFYING", "BLOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
    assert OBLIGATION_TRANSITIONS["VERIFYING"] == {"VERIFIED", "BLOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
    assert OBLIGATION_TRANSITIONS["VERIFIED"] == {"COMMITTED", "NEEDS_REVALIDATION", "SUPERSEDED"}
    assert OBLIGATION_TRANSITIONS["COMMITTED"] == {"NEEDS_REVALIDATION", "SUPERSEDED"}
    assert OBLIGATION_TRANSITIONS["BLOCKED"] == {"AVAILABLE", "ENABLED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
    assert OBLIGATION_TRANSITIONS["LOCKED"] == {"AVAILABLE", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
    assert OBLIGATION_TRANSITIONS["NEEDS_REVALIDATION"] == {"AVAILABLE", "ENABLED", "VERIFYING", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
    assert OBLIGATION_TRANSITIONS["REJECTED"] == set()
    assert OBLIGATION_TRANSITIONS["SUPERSEDED"] == set()
    assert OBLIGATION_TRANSITIONS["IMPOSSIBLE"] == set()


def test_foundation_is_not_public_root_or_runtime_composition():
    assert not hasattr(aasm, "ObligationPhasePlan")
    runtime_source = (ROOT / "src/aasm/runtime_v56_foundation.py").read_text(encoding="utf-8")
    assert "from .obligation_phase" not in runtime_source
    assert "ObligationPhasePlan" not in runtime_source


def test_obligation_phase_schemas_are_closed_and_accept_canonical_documents():
    state = state_with(obligation("O-auth", status="VERIFIED"))
    binding = bind_obligation_phase(
        state["obligations"]["O-auth"],
        "PRE_AUTHORIZE",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    plan = ObligationPhasePlan(REVISION_ID, REVISION_FINGERPRINT, (binding,))
    assessment = assess_obligation_phase_readiness(
        state,
        plan,
        "PRE_AUTHORIZE",
        problem_revision_id=REVISION_ID,
        problem_revision_fingerprint=REVISION_FINGERPRINT,
    )
    docs = (
        ("obligation-phase-binding.schema.json", binding.to_dict()),
        ("obligation-phase-plan.schema.json", plan.to_dict()),
        ("obligation-phase-assessment.schema.json", assessment.to_dict()),
    )
    for filename, document in docs:
        schema = json.loads((ROOT / "schemas" / filename).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False
        validate(document, schema)
        changed = deepcopy(document); changed["unknown_field"] = True
        with pytest.raises(ValidationError):
            validate(changed, schema)
