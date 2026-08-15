from aasm import public_v52
from aasm import public_v53
from aasm.cli_v53 import build_parser
from aasm.runtime_v53_learning import AASMEngine


def test_v53_public_surface_is_additive_and_pre_release():
    report = public_v53.validate_public_api_contract()
    assert report["valid"] is True, report
    assert public_v53.__version__ == "0.53.0"
    assert public_v53.PUBLIC_RELEASE_STABILITY == "PRE_RELEASE"
    assert public_v53.PUBLIC_API_CONTRACT["contract_version"] == "0.29.0"
    assert public_v53.PUBLIC_API_CONTRACT["runtime_version"] == "0.53.0"
    assert public_v52.__version__ == "0.52.0"


def test_v53_public_contract_preserves_authority_and_solver_learning_safety_boundaries():
    contract = public_v53.public_api_contract()
    authority = contract["scoped_identity_authority"]
    learning = contract["solver_learning"]
    assert authority["contract_id"] == "aasm.authority.scoped.v1"
    assert authority["default"] == "DENY"
    assert authority["cross_run_authority_transfer"] == "NEVER"
    assert authority["resource_state_grants_authority"] is False
    assert authority["runtime"]["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY"
    assert learning["contract_id"] == "aasm.solver.learning.v1"
    assert learning["cross_run_transport"] == "EXISTING_AASM_V48_REUSE_RESULT_ENVELOPE"
    assert learning["cross_run_authority_transfer"] == "NEVER"
    assert learning["cross_run_admission_implies_truth"] is False
    assert learning["pruning_application"] == "LOCAL_REVALIDATION_REQUIRED"
    assert learning["runtime"]["imported_pruning_state"] == "INERT_UNTIL_RECEIVING_RUN_LOCAL_REVALIDATION"
    assert learning["runtime"]["application"] == "NO_AUTOMATIC_APPLICATION_IN_V0.53_FOUNDATION"


def test_v53_engine_and_imports_are_present_without_promoting_default_package():
    for method in (
        "bootstrap_scoped_workspace",
        "authorize_scoped_request",
        "scoped_authority_report",
        "effect_authority_report",
        "record_solver_learning_artifact",
        "export_solver_learning_artifact",
        "admit_cross_run_solver_learning",
        "revalidate_solver_learning",
        "solver_learning_report",
    ):
        assert callable(getattr(AASMEngine, method))
        assert method in public_v53.SUPPORTED_ENGINE_METHODS
    for name in (
        "Principal",
        "Workspace",
        "ScopedAuthorityGrant",
        "SolverLearningArtifact",
        "SolverLearningValidation",
        "SOLVER_LEARNING_AUTHORITY_CAPABILITIES",
    ):
        assert hasattr(public_v53, name)
        assert name in public_v53.SUPPORTED_PUBLIC_IMPORTS


def test_v53_cli_exposes_contract_inspection_commands_without_switching_default_cli():
    parser = build_parser()
    commands = parser._subparsers._group_actions[0].choices
    for command in (
        "scoped-authority-contract",
        "scoped-authority-runtime-contract",
        "solver-learning-contract",
        "solver-learning-runtime-contract",
    ):
        assert command in commands
        assert command in public_v53.SUPPORTED_CLI_COMMANDS
