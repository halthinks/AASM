from __future__ import annotations

import json
from pathlib import Path


def require(path: Path, tokens: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing v0.53 contract tokens {missing}")


def schema(root: Path, name: str) -> dict:
    path = root / "schemas" / name
    if not path.exists():
        raise SystemExit(f"missing v0.53 schema: {name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not str(data.get("$schema", "")).startswith("https://json-schema.org/"):
        raise SystemExit(f"invalid schema declaration: {name}")
    return data


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    require(root / "src/aasm/scoped_authority.py", [
        'SCOPED_IDENTITY_CONTRACT_ID = "aasm.identity.scoped.v1"',
        'SCOPED_AUTHORITY_CONTRACT_ID = "aasm.authority.scoped.v1"',
        '"workspace_boundary": "EXACT_MATCH_FAIL_CLOSED"',
        '"scope_flow": "EXISTING_AASM_SCOPE_FLOW_ONLY"',
        '"deny_precedence": "ANY_MATCHING_DENY_OVERRIDES_ALLOW"',
        '"delegated_wildcard": "FORBIDDEN"',
        '"resource_state_grants_authority": False',
        '"cross_run_authority_transfer": "NEVER"',
        '"default": "DENY"',
        "ONLY_WORKSPACE_ROOT_MAY_BOOTSTRAP_GRANT",
        "DELEGATED_WILDCARD_FORBIDDEN",
        "CHILD_CAPABILITY_EXCEEDS_PARENT",
        "CHILD_SCOPE_EXCEEDS_PARENT",
        "EXPLICIT_DENY",
        "NO_APPLICABLE_GRANT",
    ])

    require(root / "src/aasm/_runtime_v53_authority.py", [
        'SCOPED_AUTHORITY_RUNTIME_CONTRACT_ID = "aasm.authority.scoped.runtime.v1"',
        '"durability": "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"',
        '"workspace_bootstrap": "EXPLICIT_TRUST_ANCHOR_EVIDENCE_REQUIRED"',
        '"decision_recording": "ALLOW_AND_DENY_DURABLE"',
        '"resource_state_grants_authority": False',
        '"cross_run_authority_transfer": "NEVER"',
        "bootstrap_scoped_workspace",
        "register_scoped_principal",
        "admit_scoped_authority_grant",
        "authorize_scoped_request",
        "scoped_authority_report",
    ])

    require(root / "src/aasm/runtime_v53.py", [
        "class AASMEngine(PrincipalAwareResourceHistoryMixin, ScopedAuthorityRuntimeMixin, V52Engine)",
        '_guard_resource_evidence_by_version = True',
        '"capacity_register": "resource.capacity.register"',
        '"observe": "resource.observe"',
        '"reserve": "resource.reserve"',
        '"reestimate": "resource.reestimate"',
        '"release": "resource.release"',
        '"settle": "resource.settle"',
        '"authorize": "effect.authorize"',
        '"execute": "effect.execute"',
        '"reconcile": "effect.reconcile"',
        "authority_decision_evidence_id",
        "effect is not bound to a v0.53 workspace/scope; explicit migration is required",
        "effect_execution_authority",
        "effect_reconcile_authority",
        "resource_state_granted_authority",
    ])

    require(root / "src/aasm/engine.py", [
        "def add_evidence_guarded",
        "expected_machine_version",
        "self.snapshot=self.store.load_snapshot(machine_id)",
        "self.events=self.store.load_events(machine_id)",
    ])
    for store_path in ("memory.py", "sqlite.py", "postgres.py"):
        require(root / "src/aasm/persistence" / store_path, [
            "expected_machine_version",
            "Stale machine version",
        ])
    require(root / "src/aasm/_runtime_v52_resources.py", [
        '_guard_resource_evidence_by_version',
        "add_evidence_guarded",
    ])
    require(root / "src/aasm/_runtime_v53_resource_history.py", [
        "class PrincipalAwareResourceHistoryMixin",
        '"principal_history": "DERIVED_FROM_SCOPED_AUTHORITY_EVIDENCE"',
        '"concurrent_commit_guard": "V53_OPTIMISTIC_MACHINE_VERSION_FAIL_CLOSED"',
    ])

    require(root / "src/aasm/scoped_store.py", [
        'SCOPED_STORE_CONTRACT_ID = "aasm.store.scoped.v1"',
        '"raw_snapshot_access": "ROOT_SCOPE_SINGLE_WORKSPACE_ONLY"',
        '"multi_workspace_raw_access": "FAIL_CLOSED_USE_SCOPED_PROJECTIONS"',
        '"legacy_unscoped_effect_access": "FAIL_CLOSED"',
        '"direct_store_write": "FORBIDDEN_USE_GOVERNED_RUNTIME_TRANSITIONS"',
        "class ScopedStoreAccess",
        "class ScopedStoreView",
        "_require_raw_machine_access",
        "_effect_visible",
    ])

    require(root / "src/aasm/cross_run_knowledge.py", [
        '"authority_transfer": "NEVER"',
        '"authority_inherited": False',
    ])

    required_schemas = {
        "scoped-principal.schema.json",
        "workspace.schema.json",
        "scoped-authority-grant.schema.json",
        "scoped-authority-decision.schema.json",
        "scoped-store-access.schema.json",
    }
    parsed = {name: schema(root, name) for name in sorted(required_schemas)}
    decision = parsed["scoped-authority-decision.schema.json"]
    if decision["properties"]["contract_id"].get("const") != "aasm.authority.scoped.v1":
        raise SystemExit("scoped authority decision schema contract drift")
    grant = parsed["scoped-authority-grant.schema.json"]
    if set(grant["properties"]["effect"]["enum"]) != {"ALLOW", "DENY"}:
        raise SystemExit("scoped authority grant effect schema drift")

    require(root / "tests/test_v53_scoped_authority.py", [
        "test_no_grant_means_deny_even_for_workspace_root",
        "test_any_matching_deny_overrides_allow",
        "test_workspace_authority_never_crosses_workspace_boundary",
        "test_cross_run_principal_mapping_does_not_create_local_authority",
        "test_resource_presence_is_not_an_input_to_authorization",
    ])
    require(root / "tests/test_v53_scoped_authority_hardening.py", [
        "test_delegated_wildcard_is_forbidden_even_from_wildcard_parent",
        "test_malformed_grant_scope_never_crashes_authority_evaluation",
    ])
    require(root / "tests/test_runtime_v53_authority.py", [
        "test_workspace_bootstrap_requires_existing_explicit_trust_anchor_evidence",
        "test_principal_registration_requires_durable_scoped_authority_and_denials_are_recorded",
        "test_effect_authorization_requires_scoped_capability_and_denial_does_not_authorize",
        "test_effect_execution_requires_fresh_authority_on_every_attempt_and_expiry_blocks_retry",
        "test_effect_reconciliation_requires_independent_scoped_capability",
    ])
    require(root / "tests/test_v53_resource_authority.py", [
        "test_denied_reservation_is_durable_authority_evidence_but_never_resource_commitment",
        "test_authorized_reservation_transaction_derives_from_authority_decision",
        "test_resource_principal_history_is_derived_from_exact_authority_evidence",
        "test_two_hosts_cannot_commit_reservations_from_same_stale_resource_snapshot",
        "test_sqlite_two_connections_reject_same_stale_resource_commit",
        "test_settlement_has_independent_capability_and_preserves_reservation_when_denied",
    ])
    require(root / "tests/test_postgres_integration.py", [
        "test_postgres_v53_resource_guard_rejects_stale_reservation_commit",
        "Stale machine version",
    ])
    require(root / "tests/test_v53_scoped_store.py", [
        "test_raw_machine_reads_fail_closed_across_workspaces",
        "test_raw_store_access_requires_root_scope_even_when_principal_has_root_grant",
        "test_multi_workspace_machine_cannot_be_returned_as_raw_snapshot",
        "test_unfinished_machine_listing_does_not_leak_other_workspace_machine_ids",
        "test_effect_reads_require_v53_binding_and_scoped_read_authority",
        "test_scoped_store_view_exposes_no_direct_append_or_mutation_surface",
    ])
    require(root / "tests/test_v53_public.py", [
        "test_v53_parent_no_longer_owns_active_demo_stack_after_v54_promotion",
        "test_v53_public_contract_preserves_authority_store_and_solver_learning_safety_boundaries",
        '"scoped-store-contract"',
        "public_v54",
    ])

    print("v0.53 scoped authority contract check: PASS")


if __name__ == "__main__":
    main()
