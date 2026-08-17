from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing active quantity public file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    active = text("src/aasm/public_active_engineering_quantity.py")
    parent = text("src/aasm/public_active_entity_evolution.py")
    package_init = text("src/aasm/__init__.py")
    foundation = text("src/aasm/runtime_v56_foundation.py")
    tests = text("tests/test_quantity_public.py")

    require('"contract_version": "0.32.16"' in active, "active quantity adoption version drift")
    for token in (
        "QUANTITY_CONTRACT_ID",
        "QUANTITY_CONTRACT_VERSION",
        "QUANTITY_REPRESENTATIONS",
        "ExactNumber",
        "DimensionVector",
        "UnitBinding",
        "IntervalValue",
        "MeasuredValue",
        "ToleranceSpec",
        "QuantizationSpec",
        "PrecisionSpec",
        "Quantity",
        "require_dimensionally_compatible",
        "require_canonically_compatible",
        "quantity_contract",
        '"engineering-quantity"',
        '"engineering_quantity"',
        '"public_admission": "QUALIFIED"',
        '"engine_state_integration": "NONE_SEMANTIC_VALUE_FOUNDATION_ONLY"',
        '"PRE_ADMISSION_ONLY"',
        '"NONE_HIDDEN_OR_MUTABLE"',
        '"UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"',
    ):
        require(token in active, f"active quantity public surface missing token: {token}")

    require("from . import public_active_entity_evolution as _base" in active, "active quantity surface does not inherit qualified 0.32.15 parent")
    require("AASMEngine = _base.AASMEngine" in active, "active quantity surface forked AASMEngine")
    require("SUPPORTED_ENGINE_METHODS = list(getattr(_base, \"SUPPORTED_ENGINE_METHODS\", []))" in active, "active quantity surface changed engine method set")

    require("from .quantity" not in parent, "quantity leaked backward into 0.32.15 parent")
    require("aasm.quantity.v1" not in parent, "quantity contract leaked backward into 0.32.15 parent")
    require("from .public_active_engineering_quantity import *" in package_init, "qualified quantity surface is not package root")
    require("from .public_active_engineering_quantity import __version__, AASMEngine" in package_init, "package root does not bind qualified quantity contract helpers")

    # Public value semantics do not imply runtime state composition.
    require("from .quantity" not in foundation, "quantity semantic value type was composed into runtime_v56 engine state")
    require("Quantity," not in foundation, "quantity type leaked into runtime_v56 foundation")

    for token in (
        "FactAuthority(",
        "StateClaim(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "UNIT_REGISTRY =",
        "GLOBAL_UNIT_REGISTRY",
        "register_unit(",
    ):
        require(token not in active, f"active quantity public surface violates firewall with token: {token}")

    for token in (
        "test_quantity_public_adoption_is_additive_over_qualified_parent",
        "test_quantity_public_adoption_exports_exact_quantity_contract_and_firewalls",
        "test_quantity_public_adoption_exposes_real_exact_value_types_without_engine_state",
        "test_quantity_public_adoption_does_not_reinterpret_live_solver_or_effect_capability_types",
        "test_quantity_public_adoption_does_not_add_engine_methods_or_runtime_state",
    ):
        require(token in tests, f"active quantity public corpus missing test: {token}")

    print("S4 quantity active public adoption source contracts: PASS")


if __name__ == "__main__":
    main()
