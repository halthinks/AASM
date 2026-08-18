from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing S4.4 public file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    active = text("src/aasm/public_active_uncertainty_scenario_trace.py")
    parent = text("src/aasm/public_active_semantic_projection.py")
    child = text("src/aasm/public_active_degraded_operation.py")
    package_root = text("src/aasm/__init__.py")
    foundation = text("src/aasm/uncertainty_scenario_trace.py")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    tests = text("tests/test_uncertainty_scenario_trace_public.py")

    for token in (
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"',
        'PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"',
        'UNCERTAINTY_SCENARIO_TRACE_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"',
        'from . import public_active_semantic_projection as _base',
        'AASMEngine = _base.AASMEngine',
        'PUBLIC_API_CONTRACT["uncertainty"]',
        'PUBLIC_API_CONTRACT["scenario"]',
        'PUBLIC_API_CONTRACT["trace_property"]',
        '"runtime_admission"] = "PRE_ADMISSION_ONLY"',
        '"engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"',
    ):
        require(token in active, f"S4.4 public parent missing token: {token}")

    require('PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"' in parent, "qualified 0.32.18 parent drifted")
    require('from . import public_active_uncertainty_scenario_trace as _base' in child, "active 0.32.20 child does not inherit qualified 0.32.19 parent")
    require('PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"' in child, "active 0.32.20 child parent version drift")
    require('from .public_active_degraded_operation import *' in package_root, "qualified 0.32.20 degraded-operation layer is not package root")
    require('from .public_active_degraded_operation import __version__, AASMEngine' in package_root, "package root does not bind active 0.32.20 helpers")
    require("from .uncertainty_scenario_trace" not in runtime, "S4.4 semantic IR was composed into runtime_v56 foundation")
    require('"runtime_admission": "PRE_ADMISSION_ONLY"' in foundation, "S4.4 foundation runtime boundary drift")

    for token in (
        "test_ust_public_adoption_is_additive_over_qualified_03218_parent",
        "test_ust_remains_qualified_03219_parent_beneath_active_03220",
        "test_ust_public_adoption_preserves_complete_parent_import_and_engine_surfaces",
        "test_ust_public_contract_claim_ceiling_and_parallel_planes_remain_strict",
        "test_ust_public_types_remain_root_accessible_without_runtime_methods",
    ):
        require(token in tests, f"S4.4 public parent corpus missing test: {token}")

    print("S4.4 uncertainty/scenario/trace-property qualified 0.32.19 parent beneath active 0.32.20: PASS")


if __name__ == "__main__":
    main()
