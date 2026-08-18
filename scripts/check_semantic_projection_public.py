from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing semantic projection public file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    active = text("src/aasm/public_active_semantic_projection.py")
    parent = text("src/aasm/public_active_engineering_rule.py")
    s44_child = text("src/aasm/public_active_uncertainty_scenario_trace.py")
    degraded_child = text("src/aasm/public_active_degraded_operation.py")
    package_root = text("src/aasm/__init__.py")
    foundation = "\n".join((
        text("src/aasm/semantic_projection.py"),
        text("src/aasm/_semantic_projection_core.py"),
        text("src/aasm/_semantic_projection_equivalence.py"),
    ))
    runtime = text("src/aasm/runtime_v56_foundation.py")
    tests = text("tests/test_semantic_projection_public.py")

    for token in (
        'PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"',
        'PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.17"',
        'SEMANTIC_PROJECTION_PUBLIC_ADMISSION = "QUALIFIED_SEMANTIC_IR_ONLY"',
        '"active_root_status"] = "ACTIVE_QUALIFIED_PUBLIC_ROOT"',
        '"runtime_admission"] = "PRE_ADMISSION_ONLY"',
        '"engine_state_integration"] = "NONE_SEMANTIC_IR_ONLY"',
        '"truth_authority": "NONE"',
        '"fact_authority": "NONE"',
        '"effect_authority": "NONE"',
        '"artifact_acceptance": "NONE"',
        '"entity_identity_authority": "NONE"',
        '"proof_authority": "NONE"',
        '"objective_preference": "NONE"',
        '"reuse_admission": "NONE"',
        '"runtime_execution": "NONE"',
        '"supported_imports": SUPPORTED_PUBLIC_IMPORTS',
        'PUBLIC_API_CONTRACT["semantic_projection"] = _semantic',
        'from . import public_active_engineering_rule as _base',
        'for _name in dir(_base):',
        'AASMEngine = _base.AASMEngine',
        'PUBLIC_RELEASE_STABILITY = _base.PUBLIC_RELEASE_STABILITY',
        'SUPPORTED_ENGINE_METHODS = list(getattr(_base, "SUPPORTED_ENGINE_METHODS", []))',
    ):
        require(token in active, f"semantic projection public layer missing token: {token}")

    for token in (
        "SEMANTIC_PROJECTION_CONTRACT_ID",
        "SEMANTIC_EQUIVALENCE_CONTRACT_ID",
        "INVARIANT_CONTRACT_ID",
        "InvariantRef",
        "SemanticSubjectRef",
        "SemanticProjectionDefinition",
        "SemanticProjectionResult",
        "SemanticEquivalenceAssessment",
        "assess_semantic_equivalence",
        "invariant_contract",
        "semantic_projection_contract",
        '"semantic-projection"',
    ):
        require(token in active, f"semantic projection import/surface missing: {token}")

    for token in (
        "class AASMEngine(",
        "FactAuthority(",
        "StateClaim(",
        "authorize_scoped_request(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "register_projection(",
        "PROJECTION_REGISTRY =",
        "projection_registry[",
        "latest_projection",
        "current_projection_store",
        "PUBLIC_ADOPTION_STABILITY",
        "PUBLIC_ADOPTION_SUPPORT",
    ):
        require(token not in active, f"semantic projection public layer violates firewall: {token}")

    require('"contract_version": "0.32.17"' in parent, "qualified Rule parent public adoption drifted")
    require('from . import public_active_semantic_projection as _base' in s44_child, "qualified 0.32.19 S4.4 layer does not inherit qualified 0.32.18 projection parent")
    require('PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.18"' in s44_child, "qualified S4.4 child parent version drift")
    require('from . import public_active_uncertainty_scenario_trace as _base' in degraded_child, "active 0.32.20 child does not inherit qualified 0.32.19 S4.4 parent")
    require('PARENT_PUBLIC_ADOPTION_CONTRACT_VERSION = "0.32.19"' in degraded_child, "active degraded-operation child parent version drift")
    require('"active_root_status": "ACTIVE_QUALIFIED_PUBLIC_ROOT"' in degraded_child, "active degraded-operation status drift")
    require('from .public_active_degraded_operation import *' in package_root, "qualified 0.32.20 degraded-operation surface is not package root")
    require('from .public_active_degraded_operation import __version__, AASMEngine' in package_root, "package root does not bind 0.32.20 helpers")
    require('from .public_active_semantic_projection import *' not in package_root, "package root still points directly at 0.32.18 projection parent")

    require('"public_admission": "PRE_ADMISSION_ONLY"' in foundation, "semantic foundation public pre-admission declaration drifted")
    require('"runtime_admission": "PRE_ADMISSION_ONLY"' in foundation, "semantic foundation runtime claim ceiling drifted")
    require("from .semantic_projection" not in runtime, "semantic projection was composed into runtime_v56 engine state")
    require("SemanticProjectionDefinition" not in runtime, "semantic projection value type leaked into runtime_v56 foundation")

    for token in (
        "test_semantic_projection_public_adoption_is_additive_over_qualified_rule_parent",
        "test_semantic_projection_remains_qualified_03218_parent_beneath_active_03220",
        "test_semantic_projection_public_adoption_preserves_full_parent_import_surface",
        "test_semantic_projection_public_adoption_adds_ir_without_engine_methods",
        "test_semantic_projection_public_claim_ceiling_and_invariant_classes_remain_strict",
        "test_semantic_projection_public_types_are_deterministic_and_projection_relative",
    ):
        require(token in tests, f"semantic projection public corpus missing test: {token}")

    print("S4 semantic projection/equivalence qualified 0.32.18 parent beneath active 0.32.20: PASS")


if __name__ == "__main__":
    main()
