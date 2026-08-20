#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def require_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    missing = [token for token in tokens if token not in value]
    if missing:
        raise SystemExit(f"{path} is missing required S5.3 verification-runtime tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.3 verification-runtime firewalls: {found}")


def main() -> None:
    runtime = "src/aasm/verification_planning_runtime.py"
    tests = "tests/test_verification_planning_runtime.py"
    workflow = ".github/workflows/verification-planning.yml"
    public = "src/aasm/public_active_degraded_operation.py"

    require_tokens(
        runtime,
        "VERIFICATION_PLANNING_RUNTIME_CONTRACT_ID = \"aasm.verification.planning.runtime.v1\"",
        "class VerificationPlanningRuntimeMixin",
        "project_verification_planning_evidence",
        "record_verification_plan",
        "record_verification_evidence_applicability",
        "verification_debt_report",
        "NONE_RECOMPUTED_PROJECTION_ONLY",
        "EXISTING_AASM_EVIDENCE_EVENT_REPLAY",
        "STALE_VERIFICATION_PLAN_PROBLEM_REVISION",
        "VERIFICATION_APPLICABILITY_ASSURANCE_REJECTED",
        "VERIFICATION_APPLICABILITY_ACTIVE_KEY_CONFLICT",
        "\"verifier_execution\": \"NONE\"",
        "\"effect_dispatch\": \"NONE\"",
        "\"resource_reservation\": \"NONE\"",
        "\"obligation_mutation\": \"NONE\"",
        "\"parallel_debt_store\": \"NONE\"",
        "\"runtime_admission\": \"PRE_ADMISSION_ONLY\"",
        "\"public_admission\": \"PRE_ADMISSION_ONLY\"",
    )
    forbid_tokens(
        runtime,
        "sqlite3",
        "CREATE TABLE",
        "requests.post",
        "subprocess.run",
        "execute_effect(",
        "reserve_candidate_resources(",
        "transition_obligation(",
        "commit_problem_revision_transition(",
        "class VerificationDebtStore",
        "class VerificationExecutor",
    )
    require_tokens(
        tests,
        "test_result_evidence_can_evolve_calculus_then_applicability_records_and_clears_current_debt",
        "test_forged_evidence_type_relabeling_is_rejected_before_durable_applicability_record",
        "test_conflicting_active_applicability_requires_invalidation_before_reassessment",
        "test_later_stale_applicability_assessment_reopens_current_debt_without_rewriting_history",
        "test_new_verification_obligation_after_plan_forces_replan_at_current_debt_boundary",
        "test_runtime_never_executes_verifier_reserves_resource_or_transitions_obligation_itself",
    )
    json.loads(text("schemas/verification-planning-record.schema.json"))
    require_tokens(
        workflow,
        "src/aasm/verification_planning_runtime.py",
        "scripts/check_verification_planning_runtime_contracts.py",
        "tests/test_verification_planning_runtime.py",
    )
    if "verification_planning_runtime" in text(public):
        raise SystemExit("S5.3 verification runtime must remain absent from the active public root")
    print("S5.3 durable verification-planning runtime contracts: PASS")


if __name__ == "__main__":
    main()
