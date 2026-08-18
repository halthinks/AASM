from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing active degraded-operation public file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    active = text("src/aasm/public_active_degraded_operation.py")
    parent = text("src/aasm/public_active_uncertainty_scenario_trace.py")
    package_root = text("src/aasm/__init__.py")
    foundation = text("src/aasm/degraded_operation.py")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    tests = text("tests/test_degraded_operation_public.py")
    for token in (
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.20"',
        'PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"',
        'DEGRADED_OPERATION_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"',
        'from . import public_active_uncertainty_scenario_trace as _base',
        'AASMEngine = _base.AASMEngine',
        '"active_root_status": "ACTIVE_QUALIFIED_PUBLIC_ROOT"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"engine_state_integration": "NONE_SEMANTIC_IR_ONLY"',
        '"mode_activation": "NONE"',
        'PUBLIC_API_CONTRACT["degraded_operation"] = _degraded',
    ):
        require(token in active, f"active degraded-operation public surface missing token: {token}")
    for token in (
        "class AASMEngine(", "FactAuthority(", "StateClaim(", "authorize_scoped_request(",
        ".authorize_effect(", ".execute_effect(", "dispatch_effect(", "preempt_authority_lease(",
        "activate_degraded_mode(", "DEGRADED_MODE_REGISTRY =", "CURRENT_DEGRADED_MODE =",
    ):
        require(token not in active, f"active degraded-operation public surface violates firewall: {token}")
    require('PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"' in parent, "qualified 0.32.19 parent drifted")
    require('from .public_active_degraded_operation import *' in package_root, "qualified 0.32.20 degraded-operation surface is not package root")
    require('from .public_active_degraded_operation import __version__, AASMEngine' in package_root, "package root does not bind 0.32.20 helpers")
    require("from .degraded_operation" not in runtime, "degraded-operation was composed into runtime_v56 foundation")
    require("DegradedOperationPolicy" not in runtime, "degraded-operation policy leaked into runtime_v56 foundation")
    require('"runtime_admission": "PRE_ADMISSION_ONLY"' in foundation, "degraded-operation foundation runtime claim ceiling drifted")
    for token in (
        "test_degraded_operation_public_adoption_is_additive_over_qualified_03219_parent",
        "test_degraded_public_adoption_preserves_complete_parent_surface_and_engine_identity",
        "test_degraded_public_adoption_exports_policy_assessment_ir_without_runtime_methods",
        "test_degraded_public_adoption_preserves_non_amplification_and_claim_ceiling",
        "test_degraded_public_evaluator_narrows_existing_capability_and_fails_closed",
    ):
        require(token in tests, f"active degraded-operation public corpus missing test: {token}")
    print("S4.5 degraded-operation active 0.32.20 public adoption source contracts: PASS")


if __name__ == "__main__":
    main()
