from __future__ import annotations

import json
from pathlib import Path

from aasm.calibration import CALIBRATION_CONTRACT_ID, CALIBRATION_KINDS, calibration_contract
from aasm.calibration_runtime import CALIBRATION_CAPABILITIES, CALIBRATION_RUNTIME_CONTRACT_ID, calibration_runtime_contract
from aasm.physical_identity import PHYSICAL_IDENTITY_CLASSES, PHYSICAL_IDENTITY_CONTRACT_ID, physical_identity_contract
from aasm.physical_identity_runtime import (
    PHYSICAL_IDENTITY_CAPABILITIES,
    PHYSICAL_IDENTITY_RUNTIME_CONTRACT_ID,
    physical_identity_runtime_contract,
)
from aasm.source_trust import (
    SOURCE_KINDS,
    SOURCE_TRUST_CONTRACT_ID,
    SOURCE_TRUST_DISPOSITIONS,
    source_trust_contract,
)
from aasm.source_trust_runtime import SOURCE_TRUST_CAPABILITIES, SOURCE_TRUST_RUNTIME_CONTRACT_ID, source_trust_runtime_contract


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    require(not missing, f"{path}: missing S3 identity/calibration/trust contract tokens {missing}")


def forbid_tokens(path: Path, tokens: tuple[str, ...]) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    require(not present, f"{path}: identity/calibration/trust layer contains forbidden hidden authority/time/mutation tokens {present}")


def main() -> None:
    identity = physical_identity_contract()
    identity_runtime = physical_identity_runtime_contract()
    calibration = calibration_contract()
    calibration_runtime = calibration_runtime_contract()
    trust = source_trust_contract()
    trust_runtime = source_trust_runtime_contract()

    require(identity["contract_id"] == PHYSICAL_IDENTITY_CONTRACT_ID, "physical identity contract drift")
    require(identity["identity_classes"] == list(PHYSICAL_IDENTITY_CLASSES), "physical identity class enum drift")
    require(identity["same_context_divergence"] == "FAIL_CLOSED_REQUIRE_NEW_EXTERNAL_OR_PROBLEM_REVISION_BEFORE_DIFFERENT_INSTANCE_OR_CONFIGURATION", "identity divergence boundary drift")
    require(identity["identity_existence_grants_fact_authority"] is False, "identity existence grants fact authority")
    require(identity["identity_existence_grants_effect_authority"] is False, "identity existence grants effect authority")
    require(identity["identity_existence_grants_source_trust"] is False, "identity existence grants source trust")
    require(identity["attestation"] == "REFERENCE_SEAM_ONLY_NOT_IMPLEMENTED_OR_CLAIMED_BY_V1", "identity overclaims attestation")
    require(identity["host_wall_clock_in_identity"] is False, "identity uses host wall clock")
    require(identity["python_object_identity_in_identity"] is False, "identity uses Python object identity")
    require(identity["parallel_identity_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY", "identity introduced registry")
    require(identity["parallel_truth_table"] == "NONE", "identity introduced truth table")

    require(identity_runtime["contract_id"] == PHYSICAL_IDENTITY_RUNTIME_CONTRACT_ID, "physical identity runtime drift")
    require(identity_runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "identity bypassed Evidence/event replay")
    require(identity_runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "identity introduced parallel authority")
    require(identity_runtime["capabilities"] == PHYSICAL_IDENTITY_CAPABILITIES, "identity capability registry drift")
    require(identity_runtime["same_context_divergence"] == "REJECTED_BEFORE_RECORDING_REQUIRE_EXPLICIT_REVISION_CHANGE", "identity runtime divergence drift")
    require(identity_runtime["fact_authority_creation"] == "NONE", "identity runtime creates FactAuthority")
    require(identity_runtime["effect_authority"] == "NONE", "identity runtime grants effect authority")
    require(identity_runtime["source_trust"] == "NONE_IDENTITY_IS_ONLY_AN_EXACT_REFERENCE", "identity runtime grants trust")
    require(identity_runtime["attestation"] == "NONE_REFERENCE_SEAM_ONLY", "identity runtime overclaims attestation")

    require(calibration["contract_id"] == CALIBRATION_CONTRACT_ID, "calibration contract drift")
    require(calibration["calibration_kinds"] == list(CALIBRATION_KINDS), "calibration kind enum drift")
    require(calibration["identity_binding"] == "EXACT_PHYSICAL_IDENTITY_ID_AND_FINGERPRINT_REQUIRED", "calibration identity binding drift")
    require(calibration["selection"] == "EXPLICIT_CALIBRATION_ID_NO_HIDDEN_CURRENT_CALIBRATION_POINTER", "calibration selection drift")
    require(calibration["transform_application"] == "NOT_IMPLEMENTED_IN_S3_FOUNDATION", "calibration overclaims transform")
    require(calibration["calibration_existence_grants_fact_authority"] is False, "calibration grants fact authority")
    require(calibration["calibration_existence_grants_effect_authority"] is False, "calibration grants effect authority")
    require(calibration["calibration_existence_grants_source_trust"] is False, "calibration grants source trust")
    require(calibration["calibration_mutates_observation"] is False, "calibration mutates observation")
    require(calibration["host_wall_clock_in_identity"] is False, "calibration uses host wall clock")
    require(calibration["parallel_calibration_store"] == "NONE_EVIDENCE_PROJECTION_ONLY", "calibration introduced store")

    require(calibration_runtime["contract_id"] == CALIBRATION_RUNTIME_CONTRACT_ID, "calibration runtime drift")
    require(calibration_runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY", "calibration runtime introduced parallel authority")
    require(calibration_runtime["capabilities"] == CALIBRATION_CAPABILITIES, "calibration capability registry drift")
    require(calibration_runtime["identity_source"] == "EXACT_EXISTING_PHYSICAL_IDENTITY_ONLY", "calibration bypassed physical identity")
    require(calibration_runtime["validity_reference"] == "EXPLICIT_CALLER_NANOSECOND_TIME_ONLY", "calibration runtime uses hidden time")
    require(calibration_runtime["selection"] == "EXPLICIT_CALIBRATION_ID_NO_LATEST_OR_CURRENT_POINTER", "calibration runtime gained current pointer")
    require(calibration_runtime["observation_mutation"] == "NONE", "calibration runtime mutates observation")
    require(calibration_runtime["fact_authority_creation"] == "NONE", "calibration runtime creates FactAuthority")
    require(calibration_runtime["effect_authority"] == "NONE", "calibration runtime grants effect authority")
    require(calibration_runtime["source_trust"] == "NONE_CALIBRATION_IS_ONLY_EVIDENCE_INPUT_TO_LATER_POLICY", "calibration runtime grants trust")

    require(trust["contract_id"] == SOURCE_TRUST_CONTRACT_ID, "source trust contract drift")
    require(trust["source_kinds"] == list(SOURCE_KINDS), "source kind enum drift")
    require(trust["trust_dispositions"] == list(SOURCE_TRUST_DISPOSITIONS), "trust disposition enum drift")
    require(trust["role"] == "EXPLICIT_POLICY_INPUT_ABOUT_A_SOURCE_NOT_FACT_AUTHORITY_OR_EFFECT_AUTHORITY", "source trust role drift")
    require(trust["selection"] == "EXPLICIT_TRUST_ASSERTION_ID_NO_HIDDEN_CURRENT_TRUST_OR_REPUTATION_SCORE", "source trust selection drift")
    require(trust["aggregation"] == "NONE_NO_TRUST_SCORE_NO_VOTING_NO_AUTOMATIC_LATEST_ASSERTION", "source trust aggregation introduced")
    require(trust["trusted_disposition_grants_fact_authority"] is False, "trusted disposition grants FactAuthority")
    require(trust["trusted_disposition_grants_effect_authority"] is False, "trusted disposition grants effect authority")
    require(trust["trusted_disposition_makes_claim_authoritative"] is False, "trusted disposition makes claim authoritative")
    require(trust["source_trust_is_universal_admission"] is False, "source trust became universal admission")
    require(trust["parallel_authority_evaluator"] == "NONE", "source trust introduced authority evaluator")
    require(trust["parallel_trust_registry"] == "NONE_EVIDENCE_PROJECTION_ONLY", "source trust introduced registry")
    require(trust["parallel_truth_table"] == "NONE", "source trust introduced truth table")

    require(trust_runtime["contract_id"] == SOURCE_TRUST_RUNTIME_CONTRACT_ID, "source trust runtime drift")
    require(trust_runtime["durability"] == "EXISTING_AASM_EVIDENCE_EVENT_REPLAY", "source trust bypassed Evidence/event replay")
    require(trust_runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORD_REVOKE_NOT_TRUST_EVALUATION", "source trust authority boundary drift")
    require(trust_runtime["capabilities"] == SOURCE_TRUST_CAPABILITIES, "source trust capability registry drift")
    require(trust_runtime["source_principal"] == "MUST_EXIST_IN_EXISTING_SCOPED_IDENTITY_PROJECTION", "source trust bypassed principal identity")
    require(trust_runtime["physical_identity"] == "OPTIONAL_EXACT_EXISTING_PHYSICAL_IDENTITY", "source trust physical identity drift")
    require(trust_runtime["required_calibrations"] == "OPTIONAL_EXACT_EXISTING_CALIBRATIONS_WITH_INTERVAL_CONTAINMENT", "source trust calibration dependency drift")
    require(trust_runtime["selection"] == "EXPLICIT_TRUST_ID_NO_LATEST_REPUTATION_OR_AGGREGATION", "source trust runtime hidden latest/score introduced")
    require(trust_runtime["fact_authority"] == "EXISTING_FACT_AUTHORITY_REMAINS_SEPARATE_AND_REQUIRED", "source trust replaced FactAuthority")
    require(trust_runtime["trusted_claim_admission"] == "NONE", "source trust directly admits claims")
    require(trust_runtime["effect_authority"] == "NONE", "source trust grants effect authority")
    require(trust_runtime["reputation_score"] == "NONE", "source trust created reputation score")
    require(trust_runtime["aggregation"] == "NONE", "source trust runtime aggregates trust")
    require(trust_runtime["parallel_authority_evaluator"] == "NONE", "source trust runtime introduced authority evaluator")

    schemas = ROOT / "schemas"
    physical_schema = json.loads((schemas / "physical-identity.schema.json").read_text(encoding="utf-8"))
    calibration_schema = json.loads((schemas / "calibration.schema.json").read_text(encoding="utf-8"))
    calibration_rev_schema = json.loads((schemas / "calibration-revocation.schema.json").read_text(encoding="utf-8"))
    trust_schema = json.loads((schemas / "source-trust.schema.json").read_text(encoding="utf-8"))
    trust_rev_schema = json.loads((schemas / "source-trust-revocation.schema.json").read_text(encoding="utf-8"))
    require(physical_schema["properties"]["contract_id"]["const"] == PHYSICAL_IDENTITY_CONTRACT_ID, "physical identity schema drift")
    require(calibration_schema["properties"]["contract_id"]["const"] == CALIBRATION_CONTRACT_ID, "calibration schema drift")
    require(calibration_rev_schema["properties"]["contract_id"]["const"] == CALIBRATION_CONTRACT_ID, "calibration revocation schema drift")
    require(trust_schema["properties"]["contract_id"]["const"] == SOURCE_TRUST_CONTRACT_ID, "source trust schema drift")
    require(trust_rev_schema["properties"]["contract_id"]["const"] == SOURCE_TRUST_CONTRACT_ID, "source trust revocation schema drift")

    require_tokens(
        ROOT / "src/aasm/physical_identity.py",
        (
            'PHYSICAL_IDENTITY_CONTRACT_ID = "aasm.physical.identity.v1"',
            "class PhysicalIdentity",
            "def logical_context_payload(",
            '"identity_existence_grants_source_trust": False',
            '"attestation": "REFERENCE_SEAM_ONLY_NOT_IMPLEMENTED_OR_CLAIMED_BY_V1"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/physical_identity_runtime.py",
        (
            'PHYSICAL_IDENTITY_RUNTIME_CONTRACT_ID = "aasm.physical.identity.runtime.v1"',
            '"record": "physical.identity.record"',
            "self.authorize_scoped_request(",
            "self.add_evidence_guarded(",
            "logical_context_fingerprint",
            '"source_trust": "NONE"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/calibration.py",
        (
            'CALIBRATION_CONTRACT_ID = "aasm.calibration.v1"',
            "class CalibrationCertificate",
            "class CalibrationRevocation",
            '"transform_application": "NOT_IMPLEMENTED_IN_S3_FOUNDATION"',
            '"calibration_existence_grants_source_trust": False',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/calibration_runtime.py",
        (
            'CALIBRATION_RUNTIME_CONTRACT_ID = "aasm.calibration.runtime.v1"',
            '"record": "calibration.record"',
            '"revoke": "calibration.revoke"',
            "self.physical_identity_report(",
            "self.authorize_scoped_request(",
            "self.add_evidence_guarded(",
            '"host_context_time_is_calibration_validity_time": False',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/source_trust.py",
        (
            'SOURCE_TRUST_CONTRACT_ID = "aasm.source.trust.v1"',
            "class SourceTrustAssertion",
            "class SourceTrustRevocation",
            '"trusted_disposition_makes_claim_authoritative": False',
            '"aggregation": "NONE_NO_TRUST_SCORE_NO_VOTING_NO_AUTOMATIC_LATEST_ASSERTION"',
        ),
    )
    require_tokens(
        ROOT / "src/aasm/source_trust_runtime.py",
        (
            'SOURCE_TRUST_RUNTIME_CONTRACT_ID = "aasm.source.trust.runtime.v1"',
            '"record": "source.trust.record"',
            '"revoke": "source.trust.revoke"',
            "self.physical_identity_report(",
            "self.calibration_report(",
            "self._workspace_authority_inputs(",
            '"fact_authority": "EXISTING_FACT_AUTHORITY_REMAINS_SEPARATE_AND_REQUIRED"',
            '"reputation_score": "NONE"',
        ),
    )

    for path in (
        ROOT / "src/aasm/physical_identity.py",
        ROOT / "src/aasm/physical_identity_runtime.py",
        ROOT / "src/aasm/calibration.py",
        ROOT / "src/aasm/calibration_runtime.py",
        ROOT / "src/aasm/source_trust.py",
        ROOT / "src/aasm/source_trust_runtime.py",
    ):
        forbid_tokens(
            path,
            (
                "time.time(",
                "time_ns(",
                "datetime.now(",
                "self.register_fact_authority(",
                "self.record_state_claim(",
                "self.propose_effect(",
                "self.authorize_effect(",
                "self.execute_effect(",
                "trust_score",
                "reputation_score =",
            ),
        )

    require_tokens(
        ROOT / "tests/test_identity_calibration_trust.py",
        (
            "test_same_physical_identity_context_cannot_silently_change_instance_or_configuration",
            "test_calibration_validity_expiry_and_revocation_use_explicit_reference_time",
            "test_effective_trusted_source_still_cannot_mint_authoritative_state_without_fact_authority",
            "test_revoked_calibration_makes_existing_trusted_assertion_ineffective_without_rewriting_it",
            "test_textpcb_project_tool_source_uses_generic_identity_calibration_and_trust_contracts",
            "test_sqlite_restart_reconstructs_identity_calibration_trust_and_revocations",
        ),
    )

    print("S3 physical identity + calibration + source trust preserve exact portable references, explicit validity, no hidden current/reputation, no FactAuthority replacement, and no authority elevation: PASS")


if __name__ == "__main__":
    main()
