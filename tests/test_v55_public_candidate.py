from __future__ import annotations

import aasm
from aasm import public_v54, public_v55


def test_v55_candidate_surface_is_additive_but_not_active_root_package():
    report = public_v55.validate_public_api_contract()
    assert report["valid"] is True, report
    assert public_v55.__version__ == "0.55.0.dev0"
    assert public_v55.PUBLIC_RELEASE_STABILITY == "QUALIFICATION_CANDIDATE"
    assert public_v55.PUBLIC_API_CONTRACT["contract_version"] == "0.31.0"
    assert public_v55.PUBLIC_API_CONTRACT["runtime_version"] == "0.55.0.dev0"
    assert public_v54.__version__ == "0.54.0"
    assert aasm.__version__ == "0.54.0"
    assert aasm.AASMEngine is public_v54.AASMEngine
    assert public_v55.AASMEngine is not aasm.AASMEngine


def test_v55_candidate_engine_exposes_revision_and_formulation_runtime():
    for method in (
        "semantic_evolution_runtime_contract_report",
        "semantic_evolution_report",
        "register_initial_problem_revision",
        "commit_problem_revision_transition",
        "resume_problem_revision_impacts",
        "require_usable_problem_revision",
        "formulation_runtime_contract_report",
        "register_solver_formulation",
        "prepare_registered_formulation_request",
        "formulation_report",
    ):
        assert callable(getattr(public_v55.AASMEngine, method))
        assert method in public_v55.SUPPORTED_ENGINE_METHODS


def test_v55_candidate_exposes_truthful_ir_claim_ceilings():
    contract = public_v55.public_api_contract()
    assert contract["semantic_evolution"]["truth_authority"] == "EXISTING_AASM_ADMISSION_PATH_ONLY"
    assert contract["solver_formulation"]["truth_authority"] == "NONE"
    assert contract["discrete_ir"]["approximation"] == "NOT_SUPPORTED_BY_THIS_CONTRACT"
    assert contract["scheduling_ir"]["execution_adapter"] == "NOT_CLAIMED_BY_THIS_FOUNDATION"
    assert contract["continuous_ir"]["optimality_proof"] == "NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION"
    assert contract["decision_vector"]["scalarization"] == "NONE"
    assert contract["semantic_archive"]["replay_uses_persisted_snapshot"] is False


def test_v55_candidate_import_registry_contains_new_engineering_contracts():
    for name in (
        "ExternalReference",
        "ProblemRevision",
        "ProblemDelta",
        "ModelFeatureSet",
        "ProviderCapabilityManifest",
        "SolverFormulation",
        "DiscreteBooleanModel",
        "SchedulingModel",
        "ContinuousModel",
        "GovernedDecisionVector",
        "SemanticEvolutionArchive",
    ):
        assert hasattr(public_v55, name)
        assert name in public_v55.SUPPORTED_PUBLIC_IMPORTS
        assert not hasattr(aasm, name) or name in public_v54.SUPPORTED_PUBLIC_IMPORTS
