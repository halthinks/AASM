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
        fail(f"missing required execution-environment contract tokens: {missing}", path)


def forbid(path: Path, tokens) -> None:
    text = path.read_text(encoding="utf-8")
    present = [token for token in tokens if token in text]
    if present:
        fail(f"forbidden execution-environment implementation tokens: {present}", path)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    semantic = root / "src/aasm/execution_environment.py"
    runtime = root / "src/aasm/execution_environment_runtime.py"
    tests = root / "tests/test_execution_environment.py"

    require(semantic, [
        'EXECUTION_ENVIRONMENT_CONTRACT_ID = "aasm.execution.environment.v1"',
        'EXECUTION_ENVIRONMENT_BINDING_CONTRACT_ID = "aasm.execution.environment-binding.v1"',
        '"MODEL"', '"SIMULATION"', '"SIL"', '"HIL"', '"BENCH"', '"CONTROLLED_PHYSICAL"', '"OPERATIONAL"',
        '"level_ordering": "NONE"',
        '"higher_level_implies_truth": False',
        '"higher_level_implies_authority": False',
        '"automatic_level_upgrade": False',
        '"simulation_as_physical": "REJECT_EXACT_ACCEPTED_LEVELS_ONLY"',
        '"environment_existence_grants_fact_authority": False',
        '"environment_existence_grants_effect_authority": False',
        '"environment_existence_grants_source_trust": False',
        '"environment_level_is_universal_admission": False',
        '"host_wall_clock_in_identity": False',
        '"python_object_identity_in_identity": False',
        '"parallel_environment_store": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"parallel_truth_table": "NONE"',
        "environment_level_accepted",
        "PORTABLE_U63_MAX",
    ])
    require(runtime, [
        'EXECUTION_ENVIRONMENT_RUNTIME_CONTRACT_ID = "aasm.execution.environment.runtime.v1"',
        '"authority": "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORD_BIND_NOT_ENVIRONMENT_TRUTH"',
        '"physical_identity_source": "EXISTING_PHYSICAL_IDENTITY_PROJECTION_ONLY"',
        '"calibration_source": "EXISTING_CALIBRATION_PROJECTION_ONLY"',
        '"source_trust_source": "EXISTING_SOURCE_TRUST_PROJECTION_ONLY"',
        '"observation_source": "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"',
        '"level_acceptance": "EXACT_ACCEPTED_LEVEL_SET_MEMBERSHIP_NO_ORDINAL_INFERENCE"',
        '"environment_level_authority": "NONE"',
        '"fact_authority_creation": "NONE"',
        '"effect_authority": "NONE"',
        '"source_trust_creation": "NONE"',
        '"observation_mutation": "NONE"',
        '"machine_state_mutation": "NONE"',
        '"parallel_environment_store": "NONE_EVIDENCE_PROJECTION_ONLY"',
        '"parallel_observation_store": "NONE"',
        '"parallel_truth_table": "NONE"',
        '"parallel_authority_evaluator": "NONE"',
        "authorize_scoped_request",
        "physical_identity_report",
        "calibration_report",
        "source_trust_report",
        "machine_state_observation_report",
        "state_claim_report",
    ])
    require(tests, [
        "simulation_observation_cannot_satisfy_bench_or_physical_requirement",
        "calibration_revocation_invalidates_environment_reference_without_rewriting_environment",
        "same_environment_revision_cannot_silently_change_level_or_configuration",
        "sqlite_restart_reconstructs_environment_and_binding_without_identity_drift",
    ])

    for path in (semantic, runtime):
        forbid(path, ["time.time(", "time_ns(", "datetime.now(", "TextPCB", "TEXTPCB"])
    forbid(runtime, [
        "register_fact_authority(",
        "authorize_effect(",
        "execute_effect(",
        "record_state_claim(",
        "record_source_trust(",
        "record_calibration(",
    ])

    for schema_name in ("execution-environment.schema.json", "execution-environment-binding.schema.json"):
        schema_path = root / "schemas" / schema_name
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
            fail("execution-environment schema must use JSON Schema 2020-12", schema_path)
        if schema.get("additionalProperties") is not False:
            fail("execution-environment schema must fail closed on unknown fields", schema_path)

    sys.path.insert(0, str(root / "src"))
    from aasm.execution_environment import execution_environment_contract
    from aasm.execution_environment_runtime import execution_environment_runtime_contract

    semantic_contract = execution_environment_contract()
    runtime_contract = execution_environment_runtime_contract()
    if semantic_contract["level_ordering"] != "NONE":
        fail("execution environment levels acquired ordinal semantics", semantic)
    if semantic_contract["higher_level_implies_authority"] is not False:
        fail("execution environment level incorrectly grants authority", semantic)
    if semantic_contract["simulation_as_physical"] != "REJECT_EXACT_ACCEPTED_LEVELS_ONLY":
        fail("simulation-as-physical laundering firewall drift", semantic)
    if runtime_contract["parallel_environment_store"] != "NONE_EVIDENCE_PROJECTION_ONLY":
        fail("execution environment introduced a parallel store", runtime)
    if runtime_contract["parallel_authority_evaluator"] != "NONE":
        fail("execution environment introduced a parallel authority evaluator", runtime)

    print("S3 execution environment source contracts: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
