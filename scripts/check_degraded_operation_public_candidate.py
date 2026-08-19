from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing degraded-operation post-promotion compatibility file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    promoted = text("src/aasm/public_active_degraded_operation.py")
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
        '"active_root_status": "ACTIVE_QUALIFIED_PUBLIC_ROOT"',
        '"public_admission": DEGRADED_OPERATION_PUBLIC_ADMISSION',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"engine_state_integration": "NONE_SEMANTIC_IR_ONLY"',
        '"mode_activation": "NONE"',
        '"CAPABILITY_NARROWING_POLICY_AND_ASSESSMENT_ONLY"',
    ):
        require(token in promoted, f"promoted degraded-operation public surface missing token: {token}")

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
        require(token in promoted, f"promoted degraded-operation public import missing: {token}")

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
        require(token not in promoted, f"promoted degraded-operation public surface violates firewall: {token}")

    require('PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"' in parent, "qualified 0.32.19 parent drifted")
    require('from . import public_active_degraded_operation as _active_public' in package_root, "qualified 0.32.20 degraded-operation module is not selected by package root")
    require('__version__ = _active_public.__version__' in package_root, "package root does not bind promoted version")
    require('AASMEngine = _active_public.AASMEngine' in package_root, "package root does not preserve promoted engine identity")
    require('"runtime_admission": "PRE_ADMISSION_ONLY"' in foundation, "degraded-operation foundation runtime claim ceiling drifted")
    require('"public_admission": "PRE_ADMISSION_ONLY"' in foundation, "degraded-operation foundation public claim ceiling drifted")
    require("from .degraded_operation" not in runtime, "degraded-operation promotion leaked into runtime_v56 foundation")
    require("DegradedOperationPolicy" not in runtime, "degraded-operation policy leaked into runtime_v56 foundation")

    for token in (
        "test_degraded_operation_candidate_overlay_is_now_qualified_active_root",
        "test_active_package_root_is_03220_after_degraded_candidate_qualification",
        "test_promoted_degraded_overlay_preserves_complete_parent_surface_and_engine_identity",
        "test_promoted_degraded_overlay_exports_policy_assessment_ir_without_engine_methods",
        "test_promoted_degraded_contract_preserves_non_amplification_and_claim_ceiling",
        "test_promoted_degraded_evaluator_narrows_existing_capability_and_never_authorizes",
    ):
        require(token in tests, f"degraded-operation post-promotion compatibility corpus missing test: {token}")

    import aasm
    import aasm.public_active_degraded_operation as promoted_module

    require(aasm.PUBLIC_API_CONTRACT["contract_version"] == "0.32.20", "package root regressed from promoted 0.32.20")
    require(aasm.AASMEngine is promoted_module.AASMEngine, "package root engine identity differs from promoted overlay")
    for name in ("DegradedOperationPolicy", "DegradedOperationAssessment", "evaluate_degraded_operation"):
        require(getattr(aasm, name) is getattr(promoted_module, name), f"promoted root export identity drift: {name}")

    print("S4.5 degraded-operation 0.32.20 post-promotion compatibility contracts: PASS")


if __name__ == "__main__":
    main()
