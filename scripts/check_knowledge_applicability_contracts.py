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
        raise SystemExit(f"{path} is missing required S5.4 knowledge-applicability tokens: {missing}")


def forbid_tokens(path: str, *tokens: str) -> None:
    value = text(path)
    found = [token for token in tokens if token in value]
    if found:
        raise SystemExit(f"{path} violates S5.4 knowledge-applicability firewalls: {found}")


def main() -> None:
    semantic = "src/aasm/knowledge_applicability.py"
    runtime = "src/aasm/knowledge_applicability_runtime.py"
    tests = "tests/test_knowledge_applicability_runtime.py"
    workflow = ".github/workflows/knowledge-applicability.yml"
    public = "src/aasm/public_active_degraded_operation.py"

    require_tokens(
        semantic,
        'KNOWLEDGE_APPLICABILITY_CONTRACT_ID = "aasm.knowledge.applicability.v1"',
        'KNOWLEDGE_APPLICATION_CONTRACT_ID = "aasm.knowledge.application.v1"',
        "class KnowledgeItem", "class KnowledgeSelection", "class ApplicabilityPredicateResult",
        "class ApplicabilityCheck", "class KnowledgeApplication",
        '"applicability_claim": "NONE"', '"authority_claim": "NONE"',
        '"source_authority_transfer": "NEVER"', '"source_authority_inherited": False',
        "knowledge_item_from_cross_run_envelope", "applicability_check_from_cross_run_certificate",
        "selected != applicable != applied",
    )
    require_tokens(
        runtime,
        'KNOWLEDGE_APPLICABILITY_RUNTIME_CONTRACT_ID = "aasm.knowledge.applicability.runtime.v1"',
        "class KnowledgeApplicabilityRuntimeMixin", "project_knowledge_applicability_history",
        "record_knowledge_item", "record_knowledge_selection", "record_applicability_check",
        "knowledge_applicability_current_report", "authorize_knowledge_application", "record_knowledge_application",
        "EXISTING_AASM_AUTHORITY_POLICY_AUTHORIZED_ACTION_ONLY", "EXISTING_AASM_AUTHORIZED_EVENT_REQUIRED",
        "KNOWLEDGE_APPLICATION_AUTHORIZED_EVENT_MISSING", "KNOWLEDGE_APPLICATION_APPLICABILITY_NOT_CURRENT",
        '"verification_mutation": "NONE"', '"parallel_authority_plane": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"', '"public_admission": "PRE_ADMISSION_ONLY"',
    )
    forbid_tokens(
        runtime,
        "sqlite3", "CREATE TABLE", "requests.post", "subprocess.run", "execute_effect(",
        "reserve_candidate_resources(", "transition_obligation(", "commit_problem_revision_transition(",
        "class KnowledgeAuthority", "class ApplicabilityAuthority", "class KnowledgeApplicationAuthority",
    )
    require_tokens(
        tests,
        "test_selection_is_not_applicability_or_authority",
        "test_applicable_check_requires_every_declared_predicate_and_evidence",
        "test_inapplicable_and_inconclusive_checks_block_authorization",
        "test_target_semantic_drift_blocks_authorization_and_application",
        "test_authorized_application_binds_existing_aasm_authority_event",
        "test_forged_application_without_canonical_authorized_event_is_rejected_by_projection",
        "test_verification_relief_requires_exact_authorized_proposal_and_does_not_mutate_verification",
        "test_stale_or_invalidated_applicability_support_blocks_application",
        "test_cross_run_adapter_never_transfers_source_authority",
        "test_reassessment_requires_invalidation_of_prior_applicability_evidence",
    )
    json.loads(text("schemas/knowledge-applicability-record.schema.json"))
    json.loads(text("schemas/knowledge-applicability.schema.json"))
    require_tokens(
        workflow,
        "src/aasm/knowledge_applicability.py", "src/aasm/knowledge_applicability_runtime.py",
        "scripts/check_knowledge_applicability_contracts.py", "tests/test_knowledge_applicability_runtime.py",
        "tests/test_v48_cross_run_knowledge.py", "aasm/knowledge-applicability",
    )
    if "knowledge_applicability" in text(public):
        raise SystemExit("S5.4 knowledge applicability must remain absent from the active public root")
    print("S5.4 knowledge applicability/application contracts: PASS")


if __name__ == "__main__":
    main()
