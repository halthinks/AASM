from aasm import public_v53
from aasm import public_v54
from aasm.cli_v54 import build_parser
from aasm.runtime_v54_exchange import AASMEngine


def test_v54_public_surface_is_additive_and_pre_release_without_promoting_v53():
    report = public_v54.validate_public_api_contract()
    assert report["valid"] is True, report
    assert public_v54.__version__ == "0.54.0"
    assert public_v54.PUBLIC_RELEASE_STABILITY == "PRE_RELEASE"
    assert public_v54.PUBLIC_API_CONTRACT["contract_version"] == "0.30.0"
    assert public_v54.PUBLIC_API_CONTRACT["runtime_version"] == "0.54.0"
    assert public_v53.__version__ == "0.53.0"


def test_v54_public_contract_freezes_effect_portfolio_and_exchange_boundaries():
    contract = public_v54.public_api_contract()
    effect = contract["effect_governance"]
    portfolio = contract["solver_portfolio"]
    exchange = contract["solver_exchange"]
    assert effect["intent_contract_id"] == "aasm.effect.intent.v1"
    assert effect["runtime"]["external_boundary"] == "DURABLE_OWNERSHIP_EVIDENCE_REQUIRED_BEFORE_EXECUTOR_CALL"
    assert effect["runtime"]["unknown_outcome"] == "RETRY_BLOCKED_UNTIL_EXPLICIT_RECONCILIATION"
    assert portfolio["portfolio_contract_id"] == "aasm.solver.portfolio.v1"
    assert portfolio["fastest_result"] == "NEVER_CORRECTNESS_TIEBREAK"
    assert portfolio["uncertified_negative_majority"] == "NEVER_DECISIVE"
    assert portfolio["runtime"]["execution_lease"] == "EXISTING_AASM_TASKLEASE"
    assert portfolio["runtime"]["parallel_scheduler"] == "NONE"
    assert exchange["contract_id"] == "aasm.solver.exchange.v1"
    assert exchange["target_validation"] == "EXISTING_V053_LOCAL_REVALIDATION_REQUIRED"
    assert exchange["cross_solver_agreement_grants_truth"] is False
    assert exchange["truth_authority"] == "NONE"
    assert exchange["policy_authority"] == "NONE"


def test_v54_full_engine_and_public_imports_are_exposed_without_default_switch():
    for method in (
        "effect_governance_report",
        "prepare_solver_portfolio",
        "solver_portfolio_report",
        "claim_solver_portfolio_leg",
        "execute_solver_portfolio_leg",
        "certify_solver_portfolio_leg",
        "evaluate_solver_portfolio",
        "solver_exchange_report",
        "exchange_solver_learning",
    ):
        assert callable(getattr(AASMEngine, method))
        assert method in public_v54.SUPPORTED_ENGINE_METHODS
    for name in (
        "EffectIntent",
        "EffectOwnership",
        "EffectReconciliation",
        "SolverTranslation",
        "SolverTranslationCertificate",
        "PortfolioRacePolicy",
        "SolverPortfolioPlan",
        "SolverLearningExchangeCertificate",
    ):
        assert hasattr(public_v54, name)
        assert name in public_v54.SUPPORTED_PUBLIC_IMPORTS


def test_v54_cli_exposes_inspection_only_contract_commands():
    parser = build_parser()
    commands = next(action for action in parser._actions if action.__class__.__name__ == "_SubParsersAction").choices
    for command in (
        "effect-governance-contract",
        "effect-governance-runtime-contract",
        "solver-portfolio-contract",
        "solver-portfolio-runtime-contract",
        "solver-exchange-contract",
    ):
        assert command in commands
        assert command in public_v54.SUPPORTED_CLI_COMMANDS
