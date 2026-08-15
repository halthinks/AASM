from aasm import public_v52
from aasm import public_v53
from aasm.cli_v53 import build_parser
from aasm.runtime_v53_learning import AASMEngine, SOLVER_LEARNING_APPLY_CAPABILITY


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
    application = learning["application"]
    runtime = learning["runtime"]
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
    assert learning["application"] == "EXPLICIT_VALIDATED_ADAPTER_APPLICATION_ONLY"
    assert learning["application_truth_authority"] == "NONE"
    assert learning["application_policy_authority"] == "NONE"
    assert application["contract_id"] == "aasm.solver.learning.application.v1"
    assert application["validation_required"] == "PASS_EXACT_ARTIFACT_AND_MODEL"
    assert application["truth_authority"] == "NONE"
    assert application["policy_authority"] == "NONE"
    assert application["pruning_lowering"] == "NEW_OPTIMIZATION_MODEL_EXISTING_PROVIDER_PATH"
    assert application["performance_lowering"] == "EXPLICIT_PROVIDER_CONSUMED_HINT_ONLY"
    assert runtime["imported_pruning_state"] == "INERT_UNTIL_RECEIVING_RUN_LOCAL_REVALIDATION"
    assert runtime["application"] == "EXPLICIT_VALIDATED_ADAPTER_APPLICATION_ONLY"
    assert runtime["apply_authority"] == "SCOPED_SOLVER_LEARNING_APPLY_REQUIRED"
    assert runtime["truth_authority"] == "NONE"
    assert runtime["policy_authority"] == "NONE"
    assert runtime["solver_execution"] == "EXISTING_AASM_OPTIMIZATION_PROVIDER_PATH_ONLY"


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
        "apply_solver_learning",
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
        "SolverLearningApplication",
        "SOLVER_LEARNING_APPLICATION_CONTRACT_ID",
        "SOLVER_LEARNING_APPLICATION_CONTRACT_VERSION",
        "SOLVER_LEARNING_APPLICATION_CLASSES",
        "solver_learning_application_contract",
        "build_solver_learning_application",
        "apply_solver_learning_to_optimization_request",
        "SOLVER_LEARNING_AUTHORITY_CAPABILITIES",
        "SOLVER_LEARNING_APPLY_CAPABILITY",
    ):
        assert hasattr(public_v53, name)
        assert name in public_v53.SUPPORTED_PUBLIC_IMPORTS
    assert public_v53.SOLVER_LEARNING_AUTHORITY_CAPABILITIES["apply"] == SOLVER_LEARNING_APPLY_CAPABILITY


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
