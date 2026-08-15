from __future__ import annotations

import aasm
from aasm import public_v55, public_v56


def test_v56_candidate_is_additive_and_root_package_remains_released_v55():
    report = public_v56.validate_public_api_contract()
    assert report["valid"] is True, report
    assert public_v56.__version__ == "0.56.0.dev0"
    assert public_v56.PUBLIC_RELEASE_STABILITY == "QUALIFICATION_CANDIDATE"
    assert public_v56.PUBLIC_API_CONTRACT["contract_version"] == "0.32.0"
    assert public_v56.PUBLIC_API_CONTRACT["runtime_version"] == "0.56.0.dev0"
    assert public_v55.__version__ == "0.55.0"
    assert public_v55.PUBLIC_RELEASE_STABILITY == "ACTIVE_DEVELOPMENT"
    assert aasm.__version__ == "0.55.0"
    assert aasm.AASMEngine is public_v55.AASMEngine
    assert public_v56.AASMEngine is not aasm.AASMEngine


def test_v56_candidate_engine_exposes_durable_solver_outcome_projection():
    for method in (
        "solver_outcome_v2_runtime_contract_report",
        "record_solver_outcome_v2",
        "solver_outcome_v2_report",
    ):
        assert callable(getattr(public_v56.AASMEngine, method))
        assert method in public_v56.SUPPORTED_ENGINE_METHODS


def test_v56_candidate_exposes_truthful_status_claim_boundaries():
    contract = public_v56.public_api_contract()["solver_outcome_v2"]
    assert contract["timeout_with_incumbent"] == "FEASIBLE_INCUMBENT_PRESERVED_SEPARATELY_FROM_TIME_LIMIT"
    assert contract["provider_optimal_status"] == "CLAIMED_OPTIMAL_NOT_PROVEN_OPTIMAL_WITHOUT_CHECKED_CERTIFICATE"
    assert contract["negative_status"] == "INFEASIBLE_NOT_DECISIVE_WITHOUT_CHECKED_CERTIFICATE_WHERE_PROOF_IS_REQUIRED"
    assert contract["provider_status_map"]["fuzzy_matching"] == "FORBIDDEN"
    assert contract["provider_status_map"]["ambiguous_mapping"] == "FAIL_CLOSED"
    assert contract["runtime"]["parallel_result_table"] == "NONE"
    assert contract["truth_authority"] == "NONE"


def test_v56_candidate_import_registry_contains_status_v2_contracts():
    for name in (
        "ProviderTermination",
        "SolverEvidenceGrade",
        "SolverOutcomeV2",
        "ProviderStatusRule",
        "ProviderStatusMap",
        "normalize_optimization_result_v2",
        "map_provider_termination",
    ):
        assert hasattr(public_v56, name)
        assert name in public_v56.SUPPORTED_PUBLIC_IMPORTS
