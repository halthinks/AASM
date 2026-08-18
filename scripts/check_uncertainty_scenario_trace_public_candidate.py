from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing S4.4 public candidate file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    candidate = text("src/aasm/public_active_uncertainty_scenario_trace.py")
    parent = text("src/aasm/public_active_semantic_projection.py")
    package_root = text("src/aasm/__init__.py")
    foundation = text("src/aasm/uncertainty_scenario_trace.py")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    tests = text("tests/test_uncertainty_scenario_trace_public_candidate.py")

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
        '"active_root_status"] = "CANDIDATE_UNTIL_PACKAGE_ROOT_SWITCH"',
        '"public_admission"] = UNCERTAINTY_SCENARIO_TRACE_PUBLIC_ADMISSION',
        '"runtime_admission"] = "PRE_ADMISSION_ONLY"',
        '"engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"',
        '"scenario_activation": "NONE_FOUNDATION_ONLY"',
        '"static_constraint_lowering": "NONE"',
        'def validate_public_api_contract()',
    ):
        require(token in candidate, f"S4.4 public candidate missing token: {token}")

    for token in (
        "UNCERTAINTY_CONTRACT_ID",
        "SCENARIO_CONTRACT_ID",
        "TRACE_PROPERTY_CONTRACT_ID",
        "TRACE_PROPERTY_ASSESSMENT_CONTRACT_ID",
        "ScenarioBinding",
        "Scenario",
        "UncertaintySpec",
        "TraceEventPattern",
        "TraceProperty",
        "TraceEvaluationContext",
        "TracePropertyAssessment",
        "evaluate_trace_property",
        "uncertainty_contract",
        "scenario_contract",
        "trace_property_contract",
    ):
        require(token in candidate, f"S4.4 public candidate import missing: {token}")

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
        require(token not in candidate, f"S4.4 public candidate violates firewall: {token}")

    require(
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"' in parent,
        "qualified 0.32.18 semantic projection parent drifted",
    )
    require(
        'from .public_active_semantic_projection import *' in package_root,
        "active package root is not qualified 0.32.18 semantic projection overlay",
    )
    require(
        "public_active_uncertainty_scenario_trace" not in package_root,
        "0.32.19 S4.4 candidate activated before qualification",
    )
    require(
        '"runtime_admission": "PRE_ADMISSION_ONLY"' in foundation,
        "S4.4 foundation runtime claim ceiling drifted",
    )
    require(
        '"public_admission": "PRE_ADMISSION_ONLY"' in foundation,
        "S4.4 foundation public claim ceiling drifted",
    )
    require(
        "from .uncertainty_scenario_trace" not in runtime,
        "S4.4 candidate leaked into runtime_v56 foundation",
    )
    require(
        "UncertaintySpec" not in runtime and "TraceProperty" not in runtime,
        "S4.4 value/evaluator types leaked into runtime_v56 foundation",
    )

    for token in (
        "test_uncertainty_scenario_trace_public_candidate_advances_only_candidate_overlay",
        "test_active_package_root_remains_03218_until_ust_candidate_is_qualified",
        "test_ust_candidate_preserves_complete_parent_public_surface_and_engine_identity",
        "test_ust_candidate_exports_complete_s44_ir_without_engine_methods",
        "test_ust_candidate_contract_preserves_claim_ceiling_and_no_parallel_planes",
        "test_ust_candidate_public_types_are_deterministic_and_revision_bound",
        "test_ust_candidate_trace_evaluator_is_semantic_only_and_reuses_existing_trace_projection",
    ):
        require(token in tests, f"S4.4 public candidate corpus missing test: {token}")

    print("S4.4 uncertainty/scenario/trace-property public candidate 0.32.19 source contracts: PASS")


if __name__ == "__main__":
    main()
