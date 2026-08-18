from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def text(path: str) -> str:
    target = ROOT / path
    require(target.exists(), f"missing S4.6 risk/irreversibility file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    model = text("src/aasm/risk_irreversibility.py")
    risk_schema = json.loads(text("schemas/risk-envelope.schema.json"))
    irreversibility_schema = json.loads(text("schemas/effect-irreversibility.schema.json"))
    assurance_schema = json.loads(text("schemas/irreversibility-assurance-policy.schema.json"))
    assessment_schema = json.loads(text("schemas/risk-assessment.schema.json"))
    tests = text("tests/test_risk_irreversibility_foundation.py")
    workflow = text(".github/workflows/engineering-risk-irreversibility.yml")
    runtime = text("src/aasm/runtime_v56_foundation.py")
    public = text("src/aasm/public_active_degraded_operation.py")
    rule = text("src/aasm/rule.py")
    decision_vector = text("src/aasm/decision_vector_ir.py")
    effect_capability = text("src/aasm/effect_capability.py")

    for token in (
        'RISK_ENVELOPE_CONTRACT_ID = "aasm.risk.envelope.v1"',
        'EFFECT_IRREVERSIBILITY_CONTRACT_ID = "aasm.effect.irreversibility.v1"',
        'RISK_ASSESSMENT_CONTRACT_ID = "aasm.risk.assessment.v1"',
        '"PROHIBITED"', '"MITIGATION_REQUIRED"', '"EXPLICIT_ACCEPTANCE_REQUIRED"', '"ADVISORY"',
        '"REVERSIBLE"', '"CONDITIONALLY_REVERSIBLE"', '"COSTLY_TO_REVERSE"', '"IRREVERSIBLE"', '"UNKNOWN"',
        '"BASELINE"', '"ELEVATED"', '"STRONG"', '"MAXIMUM"',
        "class HazardRef", "class RiskEnvelope", "class HazardObservation", "class EffectIrreversibility",
        "class IrreversibilityAssurancePolicy", "class RiskAssessment", "def evaluate_risk", "def risk_irreversibility_contract",
        '"EXACT_EXISTING_AASM_RULE_V1_HARD_FLOOR_REFERENCE_ONLY_NO_SECOND_HARD_FLOOR_SYSTEM"',
        '"RISK_IS_NOT_RESOURCE_OR_MONETARY_COST_AND_HAS_NO_SCALAR_COST_COLLAPSE"',
        '"OBJECTIVE_IMPROVEMENT_CANNOT_OVERRIDE_PRESENT_OR_UNKNOWN_HARD_HAZARD"',
        '"RESOURCE_SCARCITY_CANNOT_RELAX_HARD_HAZARD_OR_ASSURANCE_REQUIREMENT"',
        '"EXPLICIT_MONOTONIC_PROFILE_POLICY_UNKNOWN_REQUIRES_MAXIMUM"',
        '"risk_assessment_is_effect_authority": False',
        '"risk_assessment_is_rule_waiver": False',
        '"risk_assessment_is_artifact_acceptance": False',
        '"risk_assessment_proves_empirical_safety": False',
        '"parallel_risk_registry": "NONE"',
        '"parallel_hazard_truth_table": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
        '"parallel_resource_plane": "NONE"',
        '"parallel_objective_plane": "NONE"',
        '"runtime_admission": "PRE_ADMISSION_ONLY"',
        '"public_admission": "PRE_ADMISSION_ONLY"',
    ):
        require(token in model, f"S4.6 model missing token: {token}")

    for token in (
        "FactAuthority(", "StateClaim(", "authorize_scoped_request(", ".authorize_effect(", ".execute_effect(",
        "dispatch_effect(", "register_risk(", "accept_risk(", "waive_rule(", "RISK_REGISTRY =", "HAZARD_TRUTH_TABLE =",
        "current_risk", "resource_reservations[", "objective_value =", "datetime.now(", "time.time(", "random.", "eval(", "exec(",
    ):
        require(token not in model, f"S4.6 model violates firewall: {token}")

    require("from .rule import EngineeringRule" in model, "S4.6 does not reuse EngineeringRule")
    require('RULE_CONTRACT_ID = "aasm.rule.v1"' in rule, "aasm.rule.v1 substrate drift")
    require('"HARD_FLOOR"' in rule, "engineering HARD_FLOOR substrate missing")
    require('class DecisionHardFloor' in decision_vector, "decision-vector hard floor substrate missing")
    require("from .risk_irreversibility" not in decision_vector, "S4.6 risk leaked into decision-vector objective/hard-floor IR")
    require('EFFECT_CAPABILITY_CONTRACT_ID = "aasm.effect.capability.v1"' in effect_capability, "EffectCapability substrate drift")
    require("from .risk_irreversibility" not in effect_capability, "S4.6 risk leaked backward into EffectCapability")

    for source, label in ((runtime, "runtime_v56_foundation"), (public, "active public root")):
        require("from .risk_irreversibility" not in source, f"S4.6 foundation leaked into {label} before admission")
        require("RiskEnvelope" not in source, f"S4.6 RiskEnvelope leaked into {label} before admission")
        require("aasm.risk.envelope.v1" not in source, f"S4.6 risk contract leaked into {label} before admission")

    require(risk_schema.get("additionalProperties") is False, "risk-envelope schema is not closed")
    require(irreversibility_schema.get("additionalProperties") is False, "effect-irreversibility schema is not closed")
    require(assurance_schema.get("additionalProperties") is False, "irreversibility-assurance-policy schema is not closed")
    require(assessment_schema.get("additionalProperties") is False, "risk-assessment schema is not closed")
    require(risk_schema["properties"]["contract_id"]["const"] == "aasm.risk.envelope.v1", "risk schema ID drift")
    require(irreversibility_schema["properties"]["contract_id"]["const"] == "aasm.effect.irreversibility.v1", "irreversibility schema ID drift")
    require(assessment_schema["properties"]["contract_id"]["const"] == "aasm.risk.assessment.v1", "risk assessment schema ID drift")
    for field in ("effect_authority_granted", "rule_waiver_performed", "objective_override_performed", "resource_override_performed", "artifact_acceptance_granted"):
        require(assessment_schema["properties"][field]["const"] is False, f"risk assessment schema firewall drift: {field}")

    for token in (
        "test_risk_irreversibility_vocabularies_and_contract_are_exact",
        "test_risk_envelope_and_irreversibility_identity_are_deterministic_and_round_trip",
        "test_present_hard_floor_hazard_blocks_even_with_maximum_assurance",
        "test_unknown_hard_floor_hazard_fails_closed_not_absent",
        "test_prohibited_hazard_must_reuse_exact_existing_hard_floor_rule",
        "test_mitigation_and_explicit_acceptance_are_requirements_not_waivers_or_authority",
        "test_irreversibility_assurance_is_explicit_monotonic_and_unknown_requires_maximum",
        "test_irreversible_effect_requires_stronger_assurance_but_does_not_create_authority",
        "test_irreversible_profile_cannot_claim_recovery_operation",
        "test_risk_evaluation_requires_exact_rule_fingerprint_and_exact_hazard_observation_set",
        "test_risk_and_irreversibility_subjects_are_exact_revision_bound",
        "test_risk_contract_separates_resource_cost_objective_and_authority_planes",
        "test_binary_float_metadata_and_identity_tampering_fail_closed",
        "test_risk_schemas_are_closed_and_accept_canonical_documents",
    ):
        require(token in tests, f"S4.6 adversarial corpus missing test: {token}")

    for token in (
        "check_risk_irreversibility_contracts.py", "tests/test_risk_irreversibility_foundation.py",
        "schemas/risk-envelope.schema.json", "schemas/effect-irreversibility.schema.json",
        "schemas/irreversibility-assurance-policy.schema.json", "schemas/risk-assessment.schema.json",
        "context='aasm/engineering-risk-irreversibility'",
    ):
        require(token in workflow, f"S4.6 workflow missing token: {token}")

    print("S4.6 risk/irreversibility pre-admission source contracts: PASS")


if __name__ == "__main__":
    main()
