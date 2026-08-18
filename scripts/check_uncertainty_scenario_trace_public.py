from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing active S4.4 public file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    active = text("src/aasm/public_active_uncertainty_scenario_trace.py")
    parent = text("src/aasm/public_active_semantic_projection.py")
    package_root = text("src/aasm/__init__.py")
    foundation = text("src/aasm/uncertainty_scenario_trace.py")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    tests = text("tests/test_uncertainty_scenario_trace_public.py")

    for token in (
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"',
        'PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"',
        'UNCERTAINTY_SCENARIO_TRACE_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"',
        'from . import public_active_semantic_projection as _base',
        'for _name in dir(_base):',
        'AASMEngine = _base.AASMEngine',
        'PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY',
        'SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))',
        'SUPPORTED_CLI_COMMANDS = list(getattr(_base, "SUPPORTED_CLI_COMMANDS", []))',
        '"uncertainty-scenario-trace"',
        'PUBLIC_API_CONTRACT["uncertainty"]',
        'PUBLIC_API_CONTRACT["scenario"]',
        'PUBLIC_API_CONTRACT["trace_property"]',
        '"active_root_status"] = "ACTIVE_QUALIFIED_PUBLIC_ROOT"',
        '"runtime_admission"] = "PRE_ADMISSION_ONLY"',
        '"engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"',
        '"scenario_activation": "NONE_FOUNDATION_ONLY"',
        '"static_constraint_lowering": "NONE"',
    ):
        require(token in active, f"active S4.4 public surface missing token: {token}")

    for token in (
        "class AASMEngine(",
        "FactAuthority(",
        "StateClaim(",
        "authorize_scoped_request(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "register_uncertainty(",
        "register_scenario(",
        "activate_scenario(",
        "UNCERTAINTY_REGISTRY =",
        "SCENARIO_REGISTRY =",
        "TRACE_PROPERTY_REGISTRY =",
        "current_scenario_store",
        "latest_scenario",
    ):
        require(token not in active, f"active S4.4 public surface violates firewall: {token}")

    require(
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"' in parent,
        "qualified 0.32.18 parent adoption drifted",
    )
    require(
        'from .public_active_uncertainty_scenario_trace import *' in package_root,
        "qualified 0.32.19 S4.4 public surface is not package root",
    )
    require(
        'from .public_active_uncertainty_scenario_trace import __version__, AASMEngine' in package_root,
        "package root does not bind 0.32.19 helpers",
    )
    require(
        'from .public_active_semantic_projection import *' not in package_root,
        "package root still points directly at 0.32.18 parent",
    )
    require(
        '"runtime_admission": "PRE_ADMISSION_ONLY"' in foundation,
        "S4.4 foundation runtime claim ceiling drifted",
    )
    require(
        "from .uncertainty_scenario_trace" not in runtime,
        "S4.4 was composed into runtime_v56 engine state",
    )
    require(
        "UncertaintySpec" not in runtime and "TraceProperty" not in runtime,
        "S4.4 value/evaluator types leaked into runtime_v56 foundation",
    )

    for token in (
        "test_ust_public_adoption_is_additive_over_qualified_03218_parent",
        "test_ust_public_adoption_preserves_complete_parent_import_and_engine_surfaces",
        "test_ust_public_adoption_exports_exact_s44_semantic_ir_without_runtime_methods",
        "test_ust_public_adoption_preserves_claim_ceiling_and_parallel_plane_firewalls",
        "test_ust_public_types_are_deterministic_revision_bound_and_root_accessible",
        "test_ust_public_trace_evaluator_reuses_existing_trace_without_engine_state",
    ):
        require(token in tests, f"active S4.4 public corpus missing test: {token}")

    print("S4.4 uncertainty/scenario/trace-property active 0.32.19 public adoption source contracts: PASS")


if __name__ == "__main__":
    main()
