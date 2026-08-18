from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing degraded-operation public candidate file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    candidate = text("src/aasm/public_active_degraded_operation.py")
    parent = text("src/aasm/public_active_uncertainty_scenario_trace.py")
    package_root = text("src/aasm/__init__.py")
    foundation = text("src/aasm/degraded_operation.py")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    tests = text("tests/test_degraded_operation_public_candidate.py")

    for token in (
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.20"',
        'PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"',
        'DEGRADED_OPERATION_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"',
        'from . import public_active_uncertainty_scenario_trace as _base',
        'for _name in dir(_base):',
        'AASMEngine = _base.AASMEngine',
        'SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))',
        'SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))',
        '"degraded-operation"',
        'PUBLIC_API_CONTRACT["degraded_operation"] = _degraded',
        '"active_root_status": "CANDIDATE_UNTIL_PACKAGE_ROOT_SWITCH"',
        '"public_admission": DEGRADED_OPERATION_PUBLIC_ADMISSION',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"engine_state_integration": "NONE_SEMANTIC_IR_ONLY"',
        '"mode_activation": "NONE"',
        '"CAPABILITY_NARROWING_POLICY_AND_ASSESSMENT_ONLY"',
    ):
        require(token in candidate, f"degraded-operation public candidate missing token: {token}")

    for token in (
        "DEGRADED_OPERATION_CONTRACT_ID",
        "DEGRADED_OPERATION_ASSESSMENT_CONTRACT_ID",
        "DependencyState",
        "DependencyRequirement",
        "DegradedModeEnvelope",
        "ModeSelectionRule",
        "DegradedOperationPolicy",
        "DegradedOperationContext",
        "DegradedOperationAssessment",
        "evaluate_degraded_operation",
        "degraded_operation_contract",
    ):
        require(token in candidate, f"degraded-operation public candidate import missing: {token}")

    for token in (
        "class AASMEngine(",
        "FactAuthority(",
        "StateClaim(",
        "authorize_scoped_request(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "preempt_authority_lease(",
        "activate_degraded_mode(",
        "register_degraded_mode(",
        "DEGRADED_MODE_REGISTRY =",
        "CURRENT_DEGRADED_MODE =",
        "current_degraded_mode_store",
    ):
        require(token not in candidate, f"degraded-operation public candidate violates firewall: {token}")

    require('PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"' in parent, "qualified 0.32.19 parent drifted")
    require('from .public_active_uncertainty_scenario_trace import *' in package_root, "active package root is not qualified 0.32.19 S4.4 overlay")
    require("public_active_degraded_operation" not in package_root, "0.32.20 degraded-operation candidate activated before qualification")
    require('"runtime_admission": "PRE_ADMISSION_ONLY"' in foundation, "degraded-operation foundation runtime claim ceiling drifted")
    require('"public_admission": "PRE_ADMISSION_ONLY"' in foundation, "degraded-operation foundation public claim ceiling drifted")
    require("from .degraded_operation" not in runtime, "degraded-operation candidate leaked into runtime_v56 foundation")
    require("DegradedOperationPolicy" not in runtime, "degraded-operation policy leaked into runtime_v56 foundation")

    for token in (
        "test_degraded_operation_public_candidate_advances_only_candidate_overlay",
        "test_active_package_root_remains_03219_until_degraded_candidate_is_qualified",
        "test_degraded_candidate_preserves_complete_parent_surface_and_engine_identity",
        "test_degraded_candidate_exports_policy_assessment_ir_without_engine_methods",
        "test_degraded_candidate_contract_preserves_non_amplification_and_claim_ceiling",
        "test_degraded_candidate_evaluator_narrows_existing_capability_and_never_authorizes",
    ):
        require(token in tests, f"degraded-operation public candidate corpus missing test: {token}")

    print("S4.5 degraded-operation public candidate 0.32.20 source contracts: PASS")


if __name__ == "__main__":
    main()
