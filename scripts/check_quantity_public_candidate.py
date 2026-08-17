from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing quantity public-candidate file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    candidate = text("src/aasm/public_active_engineering_quantity.py")
    parent = text("src/aasm/public_active_entity_evolution.py")
    package_init = text("src/aasm/__init__.py")
    tests = text("tests/test_quantity_public_candidate.py")

    require('"contract_version": "0.32.16"' in candidate, "quantity public candidate adoption version drift")
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
        '"public_admission": "CANDIDATE"',
        '"engine_state_integration": "NONE_SEMANTIC_VALUE_FOUNDATION_ONLY"',
        '"PRE_ADMISSION_ONLY"',
        '"NONE_HIDDEN_OR_MUTABLE"',
        '"UNCHANGED_NOT_REINTERPRETED_BY_QUANTITY_FOUNDATION"',
    ):
        require(token in candidate, f"quantity public candidate missing token: {token}")

    # Candidate must inherit rather than replace the already-qualified parent.
    require("from . import public_active_entity_evolution as _base" in candidate, "quantity candidate does not inherit the active 0.32.15 parent")
    require("AASMEngine = _base.AASMEngine" in candidate, "quantity candidate forked the active engine")
    require("SUPPORTED_ENGINE_METHODS = list(getattr(_base, \"SUPPORTED_ENGINE_METHODS\", []))" in candidate, "quantity candidate changed engine method surface")

    # Parent and package root remain untouched until candidate qualification.
    require("from .quantity" not in parent, "quantity leaked into active 0.32.15 parent")
    require("aasm.quantity.v1" not in parent, "quantity contract leaked into active 0.32.15 parent")
    require("public_active_engineering_quantity" not in package_init, "quantity candidate promoted to package root before qualification")

    banned_candidate_tokens = (
        "FactAuthority(",
        "StateClaim(",
        ".authorize_effect(",
        ".execute_effect(",
        "dispatch_effect(",
        "UNIT_REGISTRY =",
        "GLOBAL_UNIT_REGISTRY",
        "register_unit(",
    )
    for token in banned_candidate_tokens:
        require(token not in candidate, f"quantity public candidate violates firewall with token: {token}")

    for token in (
        "test_quantity_public_candidate_is_additive_over_qualified_parent",
        "test_quantity_public_candidate_exports_exact_quantity_contract_and_firewalls",
        "test_quantity_public_candidate_exposes_real_exact_value_types_without_engine_state",
        "test_quantity_public_candidate_does_not_reinterpret_live_solver_or_effect_capability_types",
        "test_quantity_candidate_does_not_silently_promote_package_root_before_gate",
    ):
        require(token in tests, f"quantity public candidate corpus missing test: {token}")

    print("S4 quantity public adoption candidate source contracts: PASS")


if __name__ == "__main__":
    main()
