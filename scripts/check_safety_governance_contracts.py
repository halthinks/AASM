from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FIXTURES = {
    "dimensional-mismatch",
    "trace-width-clearance-manufacturing",
    "drc-erc-hard-vs-preference",
    "controlled-waiver-provenance",
    "thermal-power-signal-scenarios",
    "tolerance-quantization",
    "production-alternative-equivalence-diversity",
    "degraded-dependency-loss",
    "degraded-unknown",
    "hard-hazard-dominance",
    "irreversibility-assurance",
    "scarcity-cannot-relax-floor",
}
REQUIRED_S4_TESTS = (
    "tests/test_quantity_foundation.py",
    "tests/test_quantity_public.py",
    "tests/test_rule_foundation.py",
    "tests/test_rule_public.py",
    "tests/test_semantic_projection_foundation.py",
    "tests/test_semantic_projection_textpcb.py",
    "tests/test_semantic_projection_adversarial.py",
    "tests/test_semantic_projection_public.py",
    "tests/test_uncertainty_scenario_trace_foundation.py",
    "tests/test_uncertainty_scenario_trace_public.py",
    "tests/test_degraded_operation_foundation.py",
    "tests/test_degraded_operation_public.py",
    "tests/test_risk_irreversibility_foundation.py",
    "tests/test_obligation_phase_foundation.py",
    "tests/test_safety_envelope_hybrid_state_foundation.py",
    "tests/test_epistemic_debt_manual_override_foundation.py",
    "tests/test_textpcb_s4_safety_governance.py",
)


def fail(message: str) -> None:
    raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        fail(f"missing safety-governance contract file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    manifest = json.loads(text("fixtures/textpcb/s4-safety-governance-fixtures.json"))
    schema = json.loads(text("schemas/textpcb-s4-safety-fixture.schema.json"))
    if schema.get("additionalProperties") is not False:
        fail("TextPCB S4 fixture schema must be closed")
    if manifest.get("contract_id") != "aasm.textpcb.s4-safety-fixtures.v1":
        fail("TextPCB S4 fixture contract identity drift")
    if manifest.get("required_aggregate_context") != "aasm/safety-governance":
        fail("TextPCB S4 aggregate context drift")
    if manifest.get("runtime_admission") != "QUALIFICATION_ONLY_NO_RUNTIME_SURFACE":
        fail("TextPCB S4 fixture suite claims runtime admission")
    fixture_ids = {case.get("fixture_id") for case in manifest.get("cases", [])}
    if fixture_ids != REQUIRED_FIXTURES:
        fail(
            f"TextPCB S4 fixture coverage drift: missing={sorted(REQUIRED_FIXTURES - fixture_ids)}, extra={sorted(fixture_ids - REQUIRED_FIXTURES)}"
        )
    tests = text("tests/test_textpcb_s4_safety_governance.py")
    for token in (
        "test_fixture_manifest_is_closed_fingerprinted_and_complete",
        "test_dimensional_mismatch_fixture_fails_before_solving",
        "test_trace_width_clearance_and_drc_erc_hard_floor_dominate_preferences",
        "test_controlled_waiver_provenance_is_review_only_and_creates_debt",
        "test_thermal_power_and_signal_scenarios_are_explicit_and_distinct",
        "test_tolerance_and_quantization_are_conservative_at_safety_boundary",
        "test_production_alternatives_are_projection_equivalent_but_identity_diverse",
        "test_degraded_dependency_loss_and_unknown_never_amplify_authority",
        "test_present_and_unknown_hard_hazards_dominate_all_assurance",
        "test_irreversibility_escalates_assurance_and_scarcity_never_relaxes_floor",
        "test_fixture_suite_creates_no_public_or_runtime_surface",
    ):
        if token not in tests:
            fail(f"TextPCB S4 aggregate corpus missing test: {token}")
    workflow = text(".github/workflows/safety-governance.yml")
    for path in REQUIRED_S4_TESTS:
        if path not in workflow:
            fail(f"aggregate safety-governance workflow missing S4 corpus: {path}")
    for token in (
        "python scripts/check_safety_governance_contracts.py",
        "python scripts/check_release_contracts.py",
        "python scripts/check_s48_release_contracts.py",
        "python scripts/check_s49_release_contracts.py",
        "context='aasm/safety-governance'",
    ):
        if token not in workflow:
            fail(f"aggregate safety-governance workflow missing token: {token}")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    package_root = text("src/aasm/__init__.py")
    for token in ("TextPCBSafetyFixture", "safety_governance_"):
        if token in runtime or token in package_root:
            fail(f"fixture-only S4.10 surface leaked into runtime/public root: {token}")
    print("S4.10 TextPCB fixture and aggregate safety-governance contracts: PASS")


if __name__ == "__main__":
    main()
