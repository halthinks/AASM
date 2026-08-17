from __future__ import annotations

from pathlib import Path
import json
import sys


def fail(message: str, path: Path | None = None) -> None:
    location = f" file={path}" if path is not None else ""
    safe = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::error{location}::{safe}", file=sys.stderr)
    raise SystemExit(message)


def require(path: Path, tokens) -> None:
    text = path.read_text(encoding="utf-8")
    missing = [token for token in tokens if token not in text]
    if missing:
        fail(f"missing required observation-processing contract tokens: {missing}", path)


def forbid(path: Path, tokens) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    if present:
        fail(f"forbidden observation-processing implementation tokens: {present}", path)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    lifecycle = root / "src/aasm/observation_lifecycle.py"
    fusion = root / "src/aasm/observation_fusion.py"
    runtime = root / "src/aasm/observation_processing_runtime.py"
    tests = root / "tests/test_observation_processing.py"

    require(lifecycle, [
        'OBSERVATION_LIFECYCLE_CONTRACT_ID = "aasm.observation.lifecycle.v1"',
        'OBSERVATION_DISPOSITION_CONTRACT_ID = "aasm.observation.disposition.v1"',
        '"RAW"', '"NORMALIZED"', '"CALIBRATED"', '"DERIVED"', '"VALIDATED"',
        '"empirical_root": "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"',
        '"stage_progression": "VALIDATED_AT_RUNTIME_NO_SILENT_STAGE_SKIPS"',
        '"raw_value": "MUST_EQUAL_EXACT_SOURCE_STATE_CLAIM_PORTABLE_VALUE"',
        '"current_observation_pointer": "NONE"',
        '"lifecycle_record_grants_fact_authority": False',
        '"validated_stage_is_universal_admission": False',
        '"parallel_observation_store": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"parallel_truth_table": "NONE"',
    ])
    require(fusion, [
        'OBSERVATION_FUSION_CONTRACT_ID = "aasm.observation.fusion.v1"',
        '"source_minimum": 2',
        '"direct_machine_observation_source": "FORBIDDEN_USE_RAW_LIFECYCLE_ROOT_FIRST"',
        '"agreement_semantics": "CORROBORATION_ONLY_NEVER_AUTHORITY_OR_TRUTH_BY_VOTE"',
        '"declared_independence_grants_authority": False',
        '"validated_by_agreement": False',
        '"parallel_observation_store": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"parallel_truth_table": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
    ])
    require(runtime, [
        'OBSERVATION_PROCESSING_RUNTIME_CONTRACT_ID = "aasm.observation.processing.runtime.v1"',
        '"authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORDING_NOT_OBSERVATION_TRUTH"',
        '"empirical_root": "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"',
        '"disposed_source_reuse": "FAIL_CLOSED_FOR_NEW_LIFECYCLE_OR_FUSION_RECORDS"',
        '"calibrated_stage": "EXACT_ACTIVE_CALIBRATION_AT_EXPLICIT_FRESHNESS_OR_ENVIRONMENT_REFERENCE_TIME"',
        '"fusion_agreement_authority": "NONE"',
        '"validated_stage_authority": "NONE_LOCAL_PROCESSING_LABEL_ONLY"',
        '"fact_authority_creation": "NONE"',
        '"effect_authority": "NONE"',
        '"source_trust_creation": "NONE"',
        '"state_claim_creation": "NONE"',
        '"machine_state_mutation": "NONE"',
        '"source_observation_mutation": "NONE"',
        '"current_observation_pointer": "NONE"',
        '"parallel_observation_store": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"parallel_truth_table": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
        "authorize_scoped_request",
        "machine_state_observation_report",
        "state_claim_report",
        "calibration_report",
        "execution_environment_binding_report",
        "observation_freshness_assessment_report",
    ])
    require(tests, [
        "raw_requires_exact_machine_observation_value_and_stage_skips_fail_closed",
        "calibrated_stage_requires_exact_active_calibration_and_explicit_time_context",
        "fusion_requires_exact_processed_sources_and_agreement_never_mints_authority",
        "fusion_cannot_bypass_raw_lifecycle_or_accept_forged_fingerprint",
        "disposition_is_append_only_and_disposed_sources_fail_closed_for_new_fusion",
        "projection_detects_lineage_cycle_even_when_source_fingerprints_are_forged",
        "sqlite_restart_replay_preserves_lifecycle_fusion_and_disposition",
    ])

    for path in (lifecycle, fusion, runtime):
        forbid(path, ["time.time(", "time_ns(", "datetime.now(", "TextPCB", "TEXTPCB", "pickle", "id("])
    forbid(runtime, [
        "register_fact_authority(",
        "record_state_claim(",
        "authorize_effect(",
        "execute_effect(",
        "record_source_trust(",
        "revoke_source_trust(",
        "record_execution_environment(",
        "bind_machine_observation_environment(",
    ])

    for schema_name in (
        "observation-lifecycle.schema.json",
        "observation-fusion.schema.json",
        "observation-disposition.schema.json",
    ):
        schema_path = root / "schemas" / schema_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            fail("observation-processing schema must use JSON Schema 2020-12", schema_path)
        if schema.get("additionalProperties") is not False:
            fail("observation-processing schema must fail closed on unknown fields", schema_path)

    sys.path.insert(0, str(root / "src"))
    from aasm.observation_lifecycle import observation_lifecycle_contract
    from aasm.observation_fusion import observation_fusion_contract
    from aasm.observation_processing_runtime import observation_processing_runtime_contract

    lifecycle_contract = observation_lifecycle_contract()
    fusion_contract = observation_fusion_contract()
    runtime_contract = observation_processing_runtime_contract()
    if lifecycle_contract["validated_stage_is_universal_admission"] is not False:
        fail("VALIDATED lifecycle stage acquired universal admission semantics", lifecycle)
    if fusion_contract["validated_by_agreement"] is not False:
        fail("fusion agreement acquired validation semantics", fusion)
    if fusion_contract["declared_independence_grants_authority"] is not False:
        fail("fusion independence declaration acquired authority semantics", fusion)
    if runtime_contract["parallel_observation_store"] != "NONE_EVIDENCE_PROJECTION_ONLY":
        fail("observation processing introduced a parallel observation store", runtime)
    if runtime_contract["parallel_truth_table"] != "NONE":
        fail("observation processing introduced a parallel truth table", runtime)
    if runtime_contract["parallel_authority_evaluator"] != "NONE":
        fail("observation processing introduced a parallel authority evaluator", runtime)

    print("S3 observation lifecycle/fusion source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
