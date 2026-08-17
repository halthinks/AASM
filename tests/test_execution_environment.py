from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine as ActiveEngine
from aasm.calibration import CalibrationCertificate
from aasm.calibration_runtime import CALIBRATION_CAPABILITIES
from aasm.evidence import EvidenceRecord
from aasm.execution_environment import (
    EXECUTION_ENVIRONMENT_LEVELS,
    EnvironmentEvidenceBinding,
    ExecutionEnvironment,
    environment_level_accepted,
    execution_environment_contract,
)
from aasm.execution_environment_runtime import (
    EXECUTION_ENVIRONMENT_CAPABILITIES,
    ExecutionEnvironmentRuntimeMixin,
    execution_environment_runtime_contract,
)
from aasm.external_machine import MachineBinding, MachineStateObservation
from aasm.external_machine_runtime import EXTERNAL_MACHINE_CAPABILITIES
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.physical_identity import PhysicalIdentity
from aasm.physical_identity_runtime import PHYSICAL_IDENTITY_CAPABILITIES
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.source_trust import SourceTrustAssertion
from aasm.source_trust_runtime import SOURCE_TRUST_CAPABILITIES
from aasm.state_authority import StateClaim
from aasm.state_authority_runtime import STATE_AUTHORITY_CAPABILITIES
from aasm.typed_protocol import CapabilityContract


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
SENSOR = "sensor-a"
TEXTPCB = "textpcb-engine"
OBSERVER_CAPABILITY = "machine.observe"
OPERATOR_CAPABILITY = "machine.operate"


class ExecutionEnvironmentEngine(ExecutionEnvironmentRuntimeMixin, ActiveEngine):
    """Pre-admission S3 execution-environment composition."""


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None, grant_environment=True):
    engine = ExecutionEnvironmentEngine(ProblemSpec("S3 execution environment"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "S3 execution environment fixture root", source="fixture.root-of-trust"),
        reason="S3 execution environment trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"), Workspace(WORKSPACE, ROOT), trust_anchor_evidence_id=trust.evidence_id
    )
    _grant(engine, ROOT, "identity.register")
    for principal_id in (SENSOR, TEXTPCB):
        engine.register_scoped_principal(
            Principal(principal_id, "SERVICE"), workspace_id=WORKSPACE, actor_principal_id=ROOT
        )
    engine.register_capability_contract(
        CapabilityContract(OBSERVER_CAPABILITY, "OBSERVER", "1.0.0"),
        authority_id="policy",
        authority_class="POLICY",
    )
    engine.register_capability_contract(
        CapabilityContract(OPERATOR_CAPABILITY, "OPERATOR", "1.0.0"),
        authority_id="policy",
        authority_class="POLICY",
    )
    _grant(engine, ROOT, EXTERNAL_MACHINE_CAPABILITIES["binding_register"])
    _grant(
        engine,
        ROOT,
        PHYSICAL_IDENTITY_CAPABILITIES["record"],
        CALIBRATION_CAPABILITIES["record"],
        CALIBRATION_CAPABILITIES["revoke"],
        SOURCE_TRUST_CAPABILITIES["record"],
        SOURCE_TRUST_CAPABILITIES["revoke"],
    )
    for principal_id in (SENSOR, TEXTPCB):
        _grant(
            engine,
            principal_id,
            STATE_AUTHORITY_CAPABILITIES["claim_observed"],
            EXTERNAL_MACHINE_CAPABILITIES["observation_record"],
        )
    if grant_environment:
        _grant(
            engine,
            ROOT,
            EXECUTION_ENVIRONMENT_CAPABILITIES["record"],
            EXECUTION_ENVIRONMENT_CAPABILITIES["bind_observation"],
        )
    return engine


def record_sensor_reference_chain(engine):
    identity = PhysicalIdentity(
        WORKSPACE,
        SCOPE,
        "device-a",
        "SENSOR",
        "sensor.measurement-source",
        "sensor-stable-a",
        "sensor-serial-001",
        hardware_revision_id="hw-r2",
        software_revision_id="fw-r7",
        configuration_revision_id="cfg-r1",
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
        attributes={"model": "temp-probe"},
    )
    engine.record_physical_identity(identity, actor_principal_id=ROOT)
    calibration = CalibrationCertificate(
        WORKSPACE,
        SCOPE,
        identity.subject_id,
        identity.identity_id,
        identity.fingerprint,
        "MEASUREMENT",
        "temperature.c",
        "cal-r1",
        "procedure-temp-cal-v3",
        "certificate://temp-cal/001",
        100,
        1000,
        problem_revision_id=identity.problem_revision_id,
        external_revision_id=identity.external_revision_id,
    )
    engine.record_calibration(calibration, actor_principal_id=ROOT)
    trust = SourceTrustAssertion(
        WORKSPACE,
        SCOPE,
        identity.subject_id,
        SENSOR,
        "SENSOR",
        "TRUSTED",
        ("temperature.c",),
        150,
        900,
        physical_identity_id=identity.identity_id,
        physical_identity_fingerprint=identity.fingerprint,
        required_calibrations={calibration.calibration_id: calibration.fingerprint},
        policy_basis_ids=("sensor-policy-v1",),
        problem_revision_id=identity.problem_revision_id,
        external_revision_id=identity.external_revision_id,
    )
    engine.record_source_trust(trust, actor_principal_id=ROOT)
    return identity, calibration, trust


def sensor_environment(identity, calibration, trust, *, level="HIL", environment_revision="env-r1", config_revision="rig-config-r7"):
    return ExecutionEnvironment(
        WORKSPACE,
        SCOPE,
        identity.subject_id,
        level,
        "device.test.environment",
        "lab-rig-a",
        "rig-instance-01",
        environment_revision,
        configuration_revision_id=config_revision,
        qualified_at_ns=200,
        physical_identity_id=identity.identity_id,
        physical_identity_fingerprint=identity.fingerprint,
        calibration_bindings={calibration.calibration_id: calibration.fingerprint},
        source_trust_id=trust.trust_id,
        source_trust_fingerprint=trust.fingerprint,
        qualification_basis_ids=("hil-procedure-v2",),
        problem_revision_id=identity.problem_revision_id,
        external_revision_id=identity.external_revision_id,
        attributes={"fixture": "rig-a", "transport": "loopback"},
    )


def prepare_observation(
    engine,
    *,
    source_principal=SENSOR,
    subject_id="device-a",
    namespace="temperature.c",
    value=25.0,
    problem_revision="problem-r1",
    external_revision="device-r1",
    receipt_id="sample-1",
):
    binding = MachineBinding(
        WORKSPACE,
        SCOPE,
        f"machine-{subject_id}-{external_revision}",
        subject_id,
        (namespace,),
        OBSERVER_CAPABILITY,
        OPERATOR_CAPABILITY,
        external_revision,
        problem_revision_id=problem_revision,
    )
    engine.register_machine_binding(binding, actor_principal_id=ROOT)
    claim = StateClaim(
        "OBSERVED",
        WORKSPACE,
        SCOPE,
        subject_id,
        namespace,
        value,
        source_principal,
        problem_revision_id=problem_revision,
        external_revision_id=external_revision,
    )
    engine.record_state_claim(claim, actor_principal_id=source_principal)
    observation = MachineStateObservation(
        binding.binding_id,
        claim.claim_id,
        source_principal,
        OBSERVER_CAPABILITY,
        external_revision,
        receipt_id=receipt_id,
    )
    engine.record_machine_state_observation(observation, actor_principal_id=source_principal)
    return claim, observation


def test_execution_environment_contract_has_no_level_authority_or_truth_ranking():
    semantic = execution_environment_contract()
    runtime = execution_environment_runtime_contract()
    assert semantic["levels"] == list(EXECUTION_ENVIRONMENT_LEVELS)
    assert semantic["level_semantics"] == "EXACT_QUALIFICATION_CONTEXT_NOT_ORDINAL_TRUTH_OR_AUTHORITY_RANK"
    assert semantic["level_ordering"] == "NONE"
    assert semantic["higher_level_implies_truth"] is False
    assert semantic["higher_level_implies_authority"] is False
    assert semantic["automatic_level_upgrade"] is False
    assert semantic["simulation_as_physical"] == "REJECT_EXACT_ACCEPTED_LEVELS_ONLY"
    assert semantic["cross_environment_evidence_equivalence"] == "NONE_UNLESS_EXPLICIT_EXTERNAL_POLICY"
    assert semantic["environment_existence_grants_fact_authority"] is False
    assert semantic["environment_existence_grants_effect_authority"] is False
    assert semantic["environment_existence_grants_source_trust"] is False
    assert semantic["environment_level_is_universal_admission"] is False
    assert semantic["host_wall_clock_in_identity"] is False
    assert semantic["python_object_identity_in_identity"] is False
    assert runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORD_BIND_NOT_ENVIRONMENT_TRUTH"
    assert runtime["level_acceptance"] == "EXACT_ACCEPTED_LEVEL_SET_MEMBERSHIP_NO_ORDINAL_INFERENCE"
    assert runtime["environment_level_authority"] == "NONE"
    assert runtime["parallel_environment_store"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert runtime["parallel_observation_store"] == "NONE"
    assert runtime["parallel_truth_table"] == "NONE"
    assert runtime["parallel_authority_evaluator"] == "NONE"


def test_environment_level_acceptance_is_exact_membership_not_rank():
    assert environment_level_accepted("SIMULATION", ("SIMULATION",)) is True
    assert environment_level_accepted("SIMULATION", ("BENCH", "CONTROLLED_PHYSICAL")) is False
    assert environment_level_accepted("OPERATIONAL", ("BENCH",)) is False
    assert environment_level_accepted("BENCH", ("BENCH", "CONTROLLED_PHYSICAL")) is True
    with pytest.raises(ValueError, match="invalid accepted"):
        environment_level_accepted("SIMULATION", ("MAGIC",))


def test_execution_environment_round_trip_and_schemas_are_deterministic():
    identity = PhysicalIdentity(WORKSPACE, SCOPE, "device-a", "SENSOR", "sensor.ns", "stable", "instance", problem_revision_id="p1", external_revision_id="e1")
    calibration = CalibrationCertificate(WORKSPACE, SCOPE, "device-a", identity.identity_id, identity.fingerprint, "MEASUREMENT", "temperature.c", "cal1", "proc", "cert", 1, 10, problem_revision_id="p1", external_revision_id="e1")
    trust = SourceTrustAssertion(WORKSPACE, SCOPE, "device-a", SENSOR, "SENSOR", "TRUSTED", ("temperature.c",), 2, 9, physical_identity_id=identity.identity_id, physical_identity_fingerprint=identity.fingerprint, required_calibrations={calibration.calibration_id: calibration.fingerprint}, problem_revision_id="p1", external_revision_id="e1")
    environment = ExecutionEnvironment(WORKSPACE, SCOPE, "device-a", "HIL", "test.env", "stable-env", "instance-env", "env-r1", qualified_at_ns=3, physical_identity_id=identity.identity_id, physical_identity_fingerprint=identity.fingerprint, calibration_bindings={calibration.calibration_id: calibration.fingerprint}, source_trust_id=trust.trust_id, source_trust_fingerprint=trust.fingerprint, problem_revision_id="p1", external_revision_id="e1")
    binding = EnvironmentEvidenceBinding(WORKSPACE, SCOPE, "device-a", environment.environment_id, environment.fingerprint, "MACHINE_STATE_OBSERVATION", "obs-1", "f" * 64, problem_revision_id="p1", external_revision_id="e1")
    assert ExecutionEnvironment.from_dict(environment.to_dict()) == environment
    assert EnvironmentEvidenceBinding.from_dict(binding.to_dict()) == binding
    schemas = Path(__file__).resolve().parents[1] / "schemas"
    Draft202012Validator(json.loads((schemas / "execution-environment.schema.json").read_text())).validate(environment.to_dict())
    Draft202012Validator(json.loads((schemas / "execution-environment-binding.schema.json").read_text())).validate(binding.to_dict())


def test_same_environment_revision_cannot_silently_change_level_or_configuration():
    engine = bootstrapped_engine()
    identity, calibration, trust = record_sensor_reference_chain(engine)
    first = sensor_environment(identity, calibration, trust)
    engine.record_execution_environment(first, actor_principal_id=ROOT)
    changed_level = sensor_environment(identity, calibration, trust, level="BENCH")
    with pytest.raises(ValueError, match="advance environment/problem/external revision"):
        engine.record_execution_environment(changed_level, actor_principal_id=ROOT)
    changed_config = sensor_environment(identity, calibration, trust, config_revision="rig-config-r8")
    with pytest.raises(ValueError, match="advance environment/problem/external revision"):
        engine.record_execution_environment(changed_config, actor_principal_id=ROOT)
    advanced = sensor_environment(identity, calibration, trust, level="BENCH", environment_revision="env-r2", config_revision="rig-config-r8")
    result = engine.record_execution_environment(advanced, actor_principal_id=ROOT)
    assert result["environment"]["environment_level"] == "BENCH"
    assert result["fact_authority_created"] is False
    assert result["effect_authority_granted"] is False
    assert result["source_trust_created"] is False
    assert result["claim_admitted"] is False


def test_environment_requires_exact_identity_calibration_and_effective_trust_at_qualification_time():
    engine = bootstrapped_engine()
    identity, calibration, trust = record_sensor_reference_chain(engine)
    environment = sensor_environment(identity, calibration, trust)
    result = engine.record_execution_environment(environment, actor_principal_id=ROOT)
    assert result["reference_details"]["physical_identity"]["fingerprint"] == identity.fingerprint
    assert result["reference_details"]["calibrations"][calibration.calibration_id]["fingerprint"] == calibration.fingerprint
    assert result["reference_details"]["source_trust"]["fingerprint"] == trust.fingerprint

    wrong_calibration = ExecutionEnvironment.from_dict({
        **environment.to_dict(),
        "environment_id": "",
        "environment_revision_id": "env-r2",
        "calibration_bindings": {calibration.calibration_id: "e" * 64},
    })
    with pytest.raises(ValueError, match="calibration fingerprint mismatch"):
        engine.record_execution_environment(wrong_calibration, actor_principal_id=ROOT)

    ineffective_time = ExecutionEnvironment.from_dict({
        **environment.to_dict(),
        "environment_id": "",
        "environment_revision_id": "env-r3",
        "qualified_at_ns": 950,
    })
    with pytest.raises(ValueError, match="calibration is not active|source trust is not effective"):
        engine.record_execution_environment(ineffective_time, actor_principal_id=ROOT)


def test_calibration_revocation_invalidates_environment_reference_without_rewriting_environment():
    engine = bootstrapped_engine()
    identity, calibration, trust = record_sensor_reference_chain(engine)
    environment = sensor_environment(identity, calibration, trust)
    engine.record_execution_environment(environment, actor_principal_id=ROOT)
    before = engine.execution_environment_report(environment.environment_id, reference_time_ns=299)
    assert before["qualification_references_effective_at_reference_time"] is True
    fingerprint = before["environment"]["fingerprint"]
    engine.revoke_calibration(calibration.calibration_id, revoked_at_ns=300, reason_code="DRIFT", actor_principal_id=ROOT)
    after = engine.execution_environment_report(environment.environment_id, reference_time_ns=300)
    assert after["qualification_references_effective_at_reference_time"] is False
    assert after["environment"]["fingerprint"] == fingerprint
    assert after["environment"]["environment_level"] == "HIL"


def test_environment_binding_requires_exact_machine_observation_context_and_revision():
    engine = bootstrapped_engine()
    identity, calibration, trust = record_sensor_reference_chain(engine)
    environment = sensor_environment(identity, calibration, trust)
    engine.record_execution_environment(environment, actor_principal_id=ROOT)
    _, observation = prepare_observation(engine)
    result = engine.bind_machine_observation_environment(observation.observation_id, environment.environment_id, actor_principal_id=ROOT)
    report = engine.execution_environment_binding_report(result["binding"]["binding_id"], accepted_levels=("HIL",))
    assert report["environment_level_accepted"] is True
    assert report["environment_level"] == "HIL"
    assert result["fact_authority_created"] is False
    assert result["effect_authority_granted"] is False
    assert result["observation_mutated"] is False

    wrong_environment = ExecutionEnvironment(
        WORKSPACE, SCOPE, "device-a", "HIL", "device.test.environment", "lab-rig-b", "rig-b", "env-r1",
        problem_revision_id="problem-r2", external_revision_id="device-r2"
    )
    engine.record_execution_environment(wrong_environment, actor_principal_id=ROOT)
    with pytest.raises(ValueError, match="problem revision|external revision"):
        engine.bind_machine_observation_environment(observation.observation_id, wrong_environment.environment_id, actor_principal_id=ROOT)


def test_textpcb_simulation_observation_cannot_satisfy_bench_or_physical_requirement():
    engine = bootstrapped_engine()
    claim, observation = prepare_observation(
        engine,
        source_principal=TEXTPCB,
        subject_id="board-project-a",
        namespace="board.drc.summary",
        value={"drc": "PASS", "unresolved": 0},
        problem_revision="pcb-problem-r17",
        external_revision="textpcb-project-r43",
        receipt_id="drc-run-43",
    )
    environment = ExecutionEnvironment(
        WORKSPACE,
        SCOPE,
        "board-project-a",
        "SIMULATION",
        "pcb.drc.environment",
        "drc-simulation-a",
        "drc-worker-01",
        "sim-env-r43",
        configuration_revision_id="ruleset-v12",
        problem_revision_id="pcb-problem-r17",
        external_revision_id="textpcb-project-r43",
        attributes={"tool_role": "drc-engine", "mode": "simulation"},
    )
    engine.record_execution_environment(environment, actor_principal_id=ROOT)
    bound = engine.bind_machine_observation_environment(observation.observation_id, environment.environment_id, actor_principal_id=ROOT)
    binding_id = bound["binding"]["binding_id"]
    simulation = engine.execution_environment_binding_report(binding_id, accepted_levels=("SIMULATION",))
    physical = engine.execution_environment_binding_report(binding_id, accepted_levels=("BENCH", "CONTROLLED_PHYSICAL"))
    assert simulation["environment_level_accepted"] is True
    assert physical["environment_level_accepted"] is False
    assert physical["environment_level_is_authority_rank"] is False
    assert engine.state_claim_report(claim.claim_id)["claim"]["value"] == {"drc": "PASS", "unresolved": 0}
    assert "textpcb" not in environment.contract_id.lower()


def test_execution_environment_recording_requires_existing_scoped_authority():
    engine = bootstrapped_engine(grant_environment=False)
    environment = ExecutionEnvironment(WORKSPACE, SCOPE, "device-a", "MODEL", "model.env", "model-a", "model-1", "env-r1")
    with pytest.raises(PermissionError, match="execution.environment.record"):
        engine.record_execution_environment(environment, actor_principal_id=ROOT)
    assert engine.execution_environments_report()["environments"] == {}


def test_environment_records_do_not_mutate_state_or_mint_authority():
    engine = bootstrapped_engine()
    before_state = deepcopy(engine.snapshot.state)
    before_values = deepcopy(engine.calculus_report()["active_values"])
    before_authorities = deepcopy(engine.state_authority_report()["authorities"])
    identity, calibration, trust = record_sensor_reference_chain(engine)
    environment = sensor_environment(identity, calibration, trust)
    engine.record_execution_environment(environment, actor_principal_id=ROOT)
    assert engine.snapshot.state == before_state
    assert engine.calculus_report()["active_values"] == before_values
    assert engine.state_authority_report()["authorities"] == before_authorities
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_sqlite_restart_reconstructs_environment_and_binding_without_identity_drift(tmp_path: Path):
    path = tmp_path / "execution-environment.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    identity, calibration, trust = record_sensor_reference_chain(engine)
    environment = sensor_environment(identity, calibration, trust)
    engine.record_execution_environment(environment, actor_principal_id=ROOT)
    _, observation = prepare_observation(engine)
    bound = engine.bind_machine_observation_environment(observation.observation_id, environment.environment_id, actor_principal_id=ROOT)
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = ExecutionEnvironmentEngine.resume(machine_id, reopened)
    report = resumed.execution_environment_report(environment.environment_id, reference_time_ns=200)
    binding = resumed.execution_environment_binding_report(bound["binding"]["binding_id"], accepted_levels=("HIL",), reference_time_ns=200)
    assert report["environment"]["fingerprint"] == environment.fingerprint
    assert report["qualification_references_effective_at_reference_time"] is True
    assert binding["environment_level_accepted"] is True
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
