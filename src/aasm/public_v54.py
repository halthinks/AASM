from __future__ import annotations

from copy import deepcopy

from . import public_v53 as _v53

for _name in dir(_v53):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_v53, _name)

from .effects import (
    EFFECT_DISPATCH_REQUEST_CONTRACT_ID,
    EFFECT_GOVERNANCE_CONTRACT_VERSION,
    EFFECT_GOVERNANCE_STABILITY,
    EFFECT_INTENT_CONTRACT_ID,
    EFFECT_OWNERSHIP_CONTRACT_ID,
    EFFECT_RECONCILIATION_CONTRACT_ID,
    EffectDispatchRequest,
    EffectIntent,
    EffectOutcome,
    EffectOwnership,
    EffectOwnershipRequest,
    EffectReconciliation,
    effect_governance_contract,
)
from .runtime_v54 import (
    EFFECT_GOVERNANCE_RUNTIME_CONTRACT_ID,
    EFFECT_GOVERNANCE_RUNTIME_CONTRACT_VERSION,
    EFFECT_GOVERNANCE_RUNTIME_STABILITY,
    PORTFOLIO_DECISION_STATUSES,
    SOLVER_PORTFOLIO_CONTRACT_ID,
    SOLVER_PORTFOLIO_CONTRACT_VERSION,
    SOLVER_PORTFOLIO_STABILITY,
    SOLVER_TRANSLATION_CHECKER_ID,
    SOLVER_TRANSLATION_CHECKER_VERSION,
    SOLVER_TRANSLATION_CONTRACT_ID,
    PortfolioRaceDecision,
    PortfolioRaceEntry,
    PortfolioRacePolicy,
    SolverTranslation,
    SolverTranslationCertificate,
    effect_governance_runtime_contract,
    evaluate_portfolio_race,
    solver_portfolio_contract,
    translate_model_for_solver,
    verify_solver_translation,
)
from .runtime_v54_exchange import (
    AASMEngine,
    SOLVER_EXCHANGE_AUTHORITY_CAPABILITY,
    SOLVER_EXCHANGE_CHECKER_ID,
    SOLVER_EXCHANGE_CHECKER_VERSION,
    SOLVER_EXCHANGE_CONTRACT_ID,
    SOLVER_EXCHANGE_CONTRACT_VERSION,
    SOLVER_EXCHANGE_STABILITY,
    SolverLearningExchangeCertificate,
    solver_exchange_contract,
)
from .runtime_v54_portfolio import (
    SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES,
    SOLVER_PORTFOLIO_RUNTIME_CONTRACT_ID,
    SOLVER_PORTFOLIO_RUNTIME_CONTRACT_VERSION,
    SOLVER_PORTFOLIO_RUNTIME_STABILITY,
    SolverPortfolioPlan,
    solver_portfolio_runtime_contract,
)


__version__ = "0.54.0"
PUBLIC_RELEASE_STABILITY = "PRE_RELEASE"
REMOTE_PROTOCOL_NAME = _v53.REMOTE_PROTOCOL_NAME
REMOTE_PROTOCOL_VERSION = _v53.REMOTE_PROTOCOL_VERSION

_NEW_ENGINE_METHODS = [
    "effect_governance_runtime_contract_report",
    "effect_governance_report",
    "solver_portfolio_contract_report",
    "solver_portfolio_runtime_contract_report",
    "prepare_solver_portfolio",
    "solver_portfolio_report",
    "claim_solver_portfolio_leg",
    "execute_solver_portfolio_leg",
    "certify_solver_portfolio_leg",
    "evaluate_solver_portfolio",
    "solver_exchange_contract_report",
    "solver_exchange_report",
    "exchange_solver_learning",
]

_NEW_IMPORTS = [
    "EFFECT_INTENT_CONTRACT_ID",
    "EFFECT_DISPATCH_REQUEST_CONTRACT_ID",
    "EFFECT_OWNERSHIP_CONTRACT_ID",
    "EFFECT_RECONCILIATION_CONTRACT_ID",
    "EFFECT_GOVERNANCE_CONTRACT_VERSION",
    "EFFECT_GOVERNANCE_STABILITY",
    "EffectIntent",
    "EffectDispatchRequest",
    "EffectOwnershipRequest",
    "EffectOwnership",
    "EffectOutcome",
    "EffectReconciliation",
    "effect_governance_contract",
    "EFFECT_GOVERNANCE_RUNTIME_CONTRACT_ID",
    "EFFECT_GOVERNANCE_RUNTIME_CONTRACT_VERSION",
    "EFFECT_GOVERNANCE_RUNTIME_STABILITY",
    "effect_governance_runtime_contract",
    "SOLVER_TRANSLATION_CONTRACT_ID",
    "SOLVER_TRANSLATION_CHECKER_ID",
    "SOLVER_TRANSLATION_CHECKER_VERSION",
    "SolverTranslation",
    "SolverTranslationCertificate",
    "translate_model_for_solver",
    "verify_solver_translation",
    "SOLVER_PORTFOLIO_CONTRACT_ID",
    "SOLVER_PORTFOLIO_CONTRACT_VERSION",
    "SOLVER_PORTFOLIO_STABILITY",
    "PORTFOLIO_DECISION_STATUSES",
    "PortfolioRaceEntry",
    "PortfolioRacePolicy",
    "PortfolioRaceDecision",
    "solver_portfolio_contract",
    "evaluate_portfolio_race",
    "SOLVER_PORTFOLIO_RUNTIME_CONTRACT_ID",
    "SOLVER_PORTFOLIO_RUNTIME_CONTRACT_VERSION",
    "SOLVER_PORTFOLIO_RUNTIME_STABILITY",
    "SOLVER_PORTFOLIO_AUTHORITY_CAPABILITIES",
    "SolverPortfolioPlan",
    "solver_portfolio_runtime_contract",
    "SOLVER_EXCHANGE_CONTRACT_ID",
    "SOLVER_EXCHANGE_CONTRACT_VERSION",
    "SOLVER_EXCHANGE_STABILITY",
    "SOLVER_EXCHANGE_CHECKER_ID",
    "SOLVER_EXCHANGE_CHECKER_VERSION",
    "SOLVER_EXCHANGE_AUTHORITY_CAPABILITY",
    "SolverLearningExchangeCertificate",
    "solver_exchange_contract",
]

SUPPORTED_ENGINE_METHODS = list(dict.fromkeys([*getattr(_v53, "SUPPORTED_ENGINE_METHODS", []), *_NEW_ENGINE_METHODS]))
SUPPORTED_CLI_COMMANDS = list(dict.fromkeys([
    *getattr(_v53, "SUPPORTED_CLI_COMMANDS", []),
    "effect-governance-contract",
    "effect-governance-runtime-contract",
    "solver-portfolio-contract",
    "solver-portfolio-runtime-contract",
    "solver-exchange-contract",
]))
SUPPORTED_INSPECTION_SURFACES = list(dict.fromkeys([
    *getattr(_v53, "SUPPORTED_INSPECTION_SURFACES", []),
    "effect-governance",
    "solver-portfolio",
    "solver-exchange",
]))
SUPPORTED_PUBLIC_IMPORTS = list(dict.fromkeys([*getattr(_v53, "SUPPORTED_PUBLIC_IMPORTS", []), *_NEW_IMPORTS]))

PUBLIC_API_CONTRACT = deepcopy(_v53.PUBLIC_API_CONTRACT)
PUBLIC_API_CONTRACT.update({
    "contract_version": "0.30.0",
    "runtime_version": __version__,
    "release_stability": PUBLIC_RELEASE_STABILITY,
    "supported_imports": SUPPORTED_PUBLIC_IMPORTS,
    "supported_engine_methods": SUPPORTED_ENGINE_METHODS,
    "supported_cli_commands": SUPPORTED_CLI_COMMANDS,
    "supported_inspection_surfaces": SUPPORTED_INSPECTION_SURFACES,
})
PUBLIC_API_CONTRACT["effect_governance"] = {
    **effect_governance_contract(),
    "runtime": effect_governance_runtime_contract(),
}
PUBLIC_API_CONTRACT["solver_portfolio"] = {
    **solver_portfolio_contract(),
    "runtime": solver_portfolio_runtime_contract(),
}
PUBLIC_API_CONTRACT["solver_exchange"] = solver_exchange_contract()
PUBLIC_API_CONTRACT["distribution"]["version"] = __version__
PUBLIC_API_CONTRACT["distribution"]["stability"] = PUBLIC_RELEASE_STABILITY


def public_api_contract():
    return deepcopy(PUBLIC_API_CONTRACT)


def validate_public_api_contract():
    parent = _v53.validate_public_api_contract()
    errors = []
    if not parent["valid"]:
        errors.extend(f"v0.53: {error}" for error in parent["errors"])
    missing_imports = [name for name in _NEW_IMPORTS if name not in globals()]
    missing_methods = [name for name in _NEW_ENGINE_METHODS if not callable(getattr(AASMEngine, name, None))]
    if missing_imports:
        errors.append(f"missing v0.54 imports: {missing_imports}")
    if missing_methods:
        errors.append(f"missing v0.54 engine methods: {missing_methods}")
    if PUBLIC_API_CONTRACT.get("runtime_version") != __version__:
        errors.append("runtime version mismatch")
    if PUBLIC_API_CONTRACT.get("contract_version") != "0.30.0":
        errors.append("adoption contract mismatch")
    effect = PUBLIC_API_CONTRACT.get("effect_governance") or {}
    portfolio = PUBLIC_API_CONTRACT.get("solver_portfolio") or {}
    exchange = PUBLIC_API_CONTRACT.get("solver_exchange") or {}
    if effect.get("intent_contract_id") != EFFECT_INTENT_CONTRACT_ID:
        errors.append("effect intent contract mismatch")
    if (effect.get("runtime") or {}).get("external_boundary") != "DURABLE_OWNERSHIP_EVIDENCE_REQUIRED_BEFORE_EXECUTOR_CALL":
        errors.append("effect external-boundary contract mismatch")
    if (effect.get("runtime") or {}).get("unknown_outcome") != "RETRY_BLOCKED_UNTIL_EXPLICIT_RECONCILIATION":
        errors.append("effect UNKNOWN recovery contract mismatch")
    if portfolio.get("portfolio_contract_id") != SOLVER_PORTFOLIO_CONTRACT_ID:
        errors.append("solver portfolio contract mismatch")
    if portfolio.get("fastest_result") != "NEVER_CORRECTNESS_TIEBREAK":
        errors.append("solver portfolio fastest-result boundary mismatch")
    if portfolio.get("uncertified_negative_majority") != "NEVER_DECISIVE":
        errors.append("solver portfolio vote boundary mismatch")
    if (portfolio.get("runtime") or {}).get("execution_lease") != "EXISTING_AASM_TASKLEASE":
        errors.append("solver portfolio TaskLease boundary mismatch")
    if exchange.get("contract_id") != SOLVER_EXCHANGE_CONTRACT_ID:
        errors.append("solver exchange contract mismatch")
    if exchange.get("target_validation") != "EXISTING_V053_LOCAL_REVALIDATION_REQUIRED":
        errors.append("solver exchange target-validation boundary mismatch")
    if exchange.get("cross_solver_agreement_grants_truth") is not False:
        errors.append("cross-solver agreement must not grant truth")
    if exchange.get("truth_authority") != "NONE" or exchange.get("policy_authority") != "NONE":
        errors.append("solver exchange must carry no truth or policy authority")
    if PUBLIC_API_CONTRACT.get("distribution", {}).get("version") != __version__:
        errors.append("distribution version mismatch")
    if PUBLIC_RELEASE_STABILITY != "PRE_RELEASE":
        errors.append("v0.54 must remain PRE_RELEASE before promotion")
    return {"valid": not errors, "errors": errors, "contract": public_api_contract()}
