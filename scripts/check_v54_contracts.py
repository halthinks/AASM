from __future__ import annotations

from pathlib import Path


def require(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        raise SystemExit(f"{path}: missing v0.54 contract tokens {missing}")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    require(root / "src/aasm/effects.py", (
        'EFFECT_INTENT_CONTRACT_ID = "aasm.effect.intent.v1"',
        'EFFECT_OWNERSHIP_CONTRACT_ID = "aasm.effect.ownership.v1"',
        'EFFECT_RECONCILIATION_CONTRACT_ID = "aasm.effect.reconciliation.v1"',
        '"unknown_outcome": "REQUIRES_EXPLICIT_RECONCILIATION_BEFORE_NEW_OWNERSHIP"',
        '"history": "APPEND_ONLY_DISPATCH_OWNERSHIP_RECONCILIATION"',
    ))
    require(root / "src/aasm/runtime_v54.py", (
        'SOLVER_TRANSLATION_CONTRACT_ID = "aasm.solver.translation.v1"',
        'SOLVER_PORTFOLIO_CONTRACT_ID = "aasm.solver.portfolio.v1"',
        '"fastest_result": "NEVER_CORRECTNESS_TIEBREAK"',
        '"uncertified_negative_majority": "NEVER_DECISIVE"',
        '"external_boundary": "DURABLE_OWNERSHIP_EVIDENCE_REQUIRED_BEFORE_EXECUTOR_CALL"',
        '"unknown_outcome": "RETRY_BLOCKED_UNTIL_EXPLICIT_RECONCILIATION"',
        '"result_authority": "EVIDENCE_ONLY"',
        '"truth_authority": "EXISTING_AASM_POLICY_ONLY"',
    ))
    require(root / "src/aasm/_runtime_v54_effect_resources.py", (
        'EFFECT_RESOURCE_SETTLEMENT_CONTRACT_ID = "aasm.effect.resource-settlement.v1"',
        '"resource_ledger": "EXISTING_AASM_RESOURCE_SETTLEMENT_ONLY"',
        '"authority": "EXISTING_RESOURCE_SETTLE_SCOPED_AUTHORITY"',
        '"outcome_gate": "CONFIRMED_OR_FAILED_RECONCILIATION_REQUIRED"',
        '"unknown_outcome": "SETTLEMENT_BLOCKED"',
        '"multi_reservation_atomicity": "RECOVERABLE_IDEMPOTENT_PER_RESERVATION_NOT_ALL_OR_NOTHING"',
        "settle_effect_resources",
    ))
    require(root / "src/aasm/runtime_v54_portfolio.py", (
        'SOLVER_PORTFOLIO_RUNTIME_CONTRACT_ID = "aasm.solver.portfolio.runtime.v1"',
        '"execution_lease": "EXISTING_AASM_TASKLEASE"',
        '"provider_execution": "EXISTING_EXECUTE_OPTIMIZATION_LEASE"',
        '"parallel_scheduler": "NONE"',
        '"decision_authority": "EVIDENCE_ONLY"',
        "prepare_solver_portfolio",
        "claim_solver_portfolio_leg",
        "execute_solver_portfolio_leg",
        "evaluate_solver_portfolio",
    ))
    require(root / "src/aasm/runtime_v54_exchange.py", (
        'SOLVER_EXCHANGE_CONTRACT_ID = "aasm.solver.exchange.v1"',
        'SOLVER_EXCHANGE_AUTHORITY_CAPABILITY = "solver.portfolio.exchange"',
        '"source_learning": "EXACT_LOCAL_PASS_VALIDATION_REQUIRED"',
        '"target_validation": "EXISTING_V053_LOCAL_REVALIDATION_REQUIRED"',
        '"native_accelerator_exchange": "FORBIDDEN_ACROSS_SOLVERS"',
        '"cross_solver_agreement_grants_truth": False',
        '"truth_authority": "NONE"',
        '"policy_authority": "NONE"',
        "exchange_solver_learning",
    ))
    require(root / "src/aasm/public_v54.py", (
        '__version__ = "0.54.0"',
        'PUBLIC_RELEASE_STABILITY = "ACTIVE_DEVELOPMENT"',
        '"contract_version": "0.30.0"',
        "settle_effect_resources",
        "validate_public_api_contract",
        "_demo_stack.AASMEngine = AASMEngine",
    ))
    require(root / "src/aasm/__init__.py", ("public_v54",))
    require(root / "src/aasm/cli.py", ("cli_v54",))
    require(root / "tests/test_runtime_v54_effects.py", (
        "test_executor_cannot_cross_external_boundary_before_atomic_ownership_and_evidence",
        "test_sqlite_recovery_retains_ownership_marks_unknown_and_requires_scoped_reconciliation",
        "test_portfolio_race_is_arrival_order_and_wall_time_invariant",
        "test_uncertified_negative_majority_cannot_outvote_one_validated_feasible_solution",
    ))
    require(root / "tests/test_runtime_v54_settlement.py", (
        "test_effect_resources_cannot_settle_before_observed_terminal_outcome",
        "test_confirmed_effect_settles_bound_resource_actuals_and_retry_is_idempotent",
        "test_settlement_retry_cannot_rewrite_already_durable_actual_consumption",
    ))
    require(root / "tests/test_runtime_v54_portfolio.py", (
        "test_portfolio_plan_uses_existing_requests_tasks_and_taskleases",
        "test_pending_portfolio_evaluation_records_no_decision_or_authority_mutation",
        "test_committed_portfolio_results_use_existing_leases_and_certified_decision_lineage",
    ))
    require(root / "tests/test_runtime_v54_exchange.py", (
        "test_correctness_sensitive_learning_exchanges_cp_sat_to_milp_and_reuses_existing_apply_path",
        "test_performance_hint_exchanges_milp_to_cp_sat_and_becomes_explicit_ortools_hint",
        "test_exchange_requires_source_local_pass_validation_before_target_materialization",
        "test_native_accelerator_state_is_not_cross_solver_portable",
    ))
    require(root / "tests/test_v54_public.py", (
        "test_v54_public_surface_is_additive_and_active_default",
        "test_v54_active_public_surface_binds_demo_stack_to_v54_runtime",
    ))
    print("v0.54 active effect, resource settlement, portfolio, exchange, and public contracts: PASS")


if __name__ == "__main__":
    main()
