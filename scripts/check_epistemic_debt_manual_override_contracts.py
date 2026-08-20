from __future__ import annotations

import json
from pathlib import Path

from aasm.calculus import OBLIGATION_STATUSES


ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    if not target.exists():
        fail(f"missing epistemic-debt/manual-override contract file: {path}")
    return target.read_text(encoding="utf-8")


def require(source: str, tokens: tuple[str, ...], label: str) -> None:
    missing = [token for token in tokens if token not in source]
    if missing:
        fail(f"{label} missing required tokens: {missing}")


def forbid(source: str, tokens: tuple[str, ...], label: str) -> None:
    present = [token for token in tokens if token in source]
    if present:
        fail(f"{label} contains forbidden tokens: {present}")


def main() -> None:
    model_paths = (
        "src/aasm/epistemic_debt_manual_override.py",
        "src/aasm/_epistemic_debt.py",
        "src/aasm/_manual_override.py",
    )
    model = "\n".join(text(path) for path in model_paths)
    calculus = text("src/aasm/_calculus_model.py")
    obligation_phase = text("src/aasm/obligation_phase.py")
    rule = text("src/aasm/rule.py")
    risk = text("src/aasm/risk_irreversibility.py")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    package_root = text("src/aasm/__init__.py")
    tests = text("tests/test_epistemic_debt_manual_override_foundation.py")
    workflow = text(".github/workflows/engineering-epistemic-debt-manual-override.yml")

    require(
        model,
        (
            'EPISTEMIC_DEBT_CONTRACT_ID = "aasm.epistemic.debt.v1"',
            'MANUAL_OVERRIDE_CONTRACT_ID = "aasm.manual.override.v1"',
            'MANUAL_OVERRIDE_ASSESSMENT_CONTRACT_ID = "aasm.manual.override.assessment.v1"',
            "from .calculus import OBLIGATION_STATUSES, content_hash, normalize_calculus_state",
            "from .obligation_phase import",
            "obligation_semantic_fingerprint",
            "validate_obligation_phase_plan",
            "from .risk_irreversibility import RiskAssessment",
            "from .rule import EngineeringRule, RuleSourceAuthorityRef",
            "class EpistemicDebtItem:",
            "class EpistemicDebtProjection:",
            "class OverrideValidityWindow:",
            "class ResultingObligationRef:",
            "class ManualOverride:",
            "class ManualOverrideAssessment:",
            "def project_epistemic_debt(",
            "def validate_epistemic_debt_projection(",
            "def bind_manual_override(",
            "def evaluate_manual_override(",
            'rule.strength == "HARD_FLOOR"',
            'rule.control_policy.waiver_mode != "EXPLICIT_AUTHORIZED"',
            'risk.status != "REQUIRES_EXPLICIT_ACCEPTANCE"',
            '"debt_graph": "NONE_SECONDARY_OR_PARALLEL"',
            '"debt_store": "NONE_SECONDARY_OR_PARALLEL"',
            '"debt_scalar_score": "NONE"',
            '"hard_floor_override": "FORBIDDEN_UNCONDITIONALLY"',
            '"assessment_is_waiver": False',
            '"assessment_is_authorization": False',
            '"assessment_mutates_rule": False',
            '"assessment_mutates_obligation": False',
            '"parallel_override_registry": "NONE"',
            '"current_override_pointer": "NONE"',
            '"runtime_admission": "PRE_ADMISSION_ONLY"',
            '"public_admission": "PRE_ADMISSION_ONLY"',
        ),
        "epistemic-debt/manual-override model",
    )
    forbid(
        model,
        (
            "class ObligationRecord:",
            "\nOBLIGATION_STATUSES =",
            "\nOBLIGATION_TRANSITIONS =",
            "CURRENT_OVERRIDE",
            "OVERRIDE_REGISTRY",
            "EPISTEMIC_DEBT_STORE",
            "EPISTEMIC_DEBT_GRAPH",
            "FactAuthority(",
            ".authorize_effect(",
            ".execute_effect(",
            "dispatch_effect(",
            "set_obligation_status(",
            "register_obligation(",
            "datetime.now(",
            "time.time(",
        ),
        "epistemic-debt/manual-override model",
    )
    require(
        calculus,
        (
            "class ObligationRecord:",
            '"obligations": {},',
            '"obligation_edges": [],',
        ),
        "existing calculus",
    )
    require(
        obligation_phase,
        (
            'OBLIGATION_PHASE_CONTRACT_ID = "aasm.obligation.phase.v1"',
            "def obligation_semantic_fingerprint(",
        ),
        "existing obligation-phase foundation",
    )
    require(
        rule,
        (
            'RULE_CONTRACT_ID = "aasm.rule.v1"',
            '"HARD_FLOOR"',
            '"EXPLICIT_AUTHORIZED"',
            "class RuleSourceAuthorityRef:",
        ),
        "existing Rule foundation",
    )
    require(
        risk,
        (
            'RISK_ASSESSMENT_CONTRACT_ID = "aasm.risk.assessment.v1"',
            '"REQUIRES_EXPLICIT_ACCEPTANCE"',
        ),
        "existing RiskAssessment foundation",
    )
    if not {
        "VERIFIED",
        "COMMITTED",
        "REJECTED",
        "SUPERSEDED",
        "IMPOSSIBLE",
    }.issubset(OBLIGATION_STATUSES):
        fail("live obligation status vocabulary no longer supports S4.9 semantics")
    forbid(
        runtime,
        (
            "from .epistemic_debt_manual_override",
            "EpistemicDebtProjection",
            "ManualOverride",
            "ManualOverrideAssessment",
        ),
        "runtime_v56 foundation",
    )
    forbid(
        package_root,
        (
            "from .epistemic_debt_manual_override import",
            "EpistemicDebtProjection",
            "ManualOverride",
            "ManualOverrideAssessment",
        ),
        "active package root",
    )
    for filename, contract_id in (
        ("schemas/epistemic-debt.schema.json", "aasm.epistemic.debt.v1"),
        ("schemas/manual-override.schema.json", "aasm.manual.override.v1"),
        (
            "schemas/manual-override-assessment.schema.json",
            "aasm.manual.override.assessment.v1",
        ),
    ):
        schema = json.loads(text(filename))
        if schema.get("additionalProperties") is not False:
            fail(f"{filename} must be closed")
        serialized = json.dumps(schema, sort_keys=True)
        if contract_id not in serialized:
            fail(f"{filename} missing contract ID {contract_id}")
        if '"type": "number"' in serialized:
            fail(f"{filename} admits binary floating-point identity")
    for token in (
        "test_vocabularies_and_contract_claim_ceiling_are_exact",
        "test_debt_projection_uses_existing_obligations_edges_and_status_machine",
        "test_debt_projection_preserves_optional_s4_7_phase_bindings",
        "test_terminal_obligations_remain_visible_as_unresolved_debt",
        "test_stale_debt_projection_and_malformed_edge_projection_fail_closed",
        "test_manual_override_records_exact_required_bindings_and_round_trips",
        "test_hard_floor_and_nonwaivable_rules_fail_closed",
        "test_authority_capability_is_reference_only_and_must_match_rule_policy",
        "test_only_exact_explicit_acceptance_risk_is_eligible",
        "test_resulting_obligations_reuse_exact_existing_store_and_must_remain_open",
        "test_validity_uses_explicit_clock_and_sequence_without_hidden_wall_clock",
        "test_admissible_assessment_remains_review_only_and_pure",
        "test_override_resulting_obligation_remains_epistemic_debt_until_verified",
        "test_foundation_is_not_public_root_or_runtime_composition",
        "test_schemas_are_closed_and_accept_canonical_documents",
    ):
        if token not in tests:
            fail(f"S4.9 adversarial corpus missing test: {token}")
    require(
        workflow,
        (
            "python scripts/check_epistemic_debt_manual_override_contracts.py",
            "pytest -q tests/test_epistemic_debt_manual_override_foundation.py",
            "aasm/engineering-epistemic-debt-manual-override",
            "schemas/epistemic-debt.schema.json",
            "schemas/manual-override.schema.json",
            "schemas/manual-override-assessment.schema.json",
        ),
        "S4.9 workflow",
    )
    print("S4.9 epistemic-debt/manual-override pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
