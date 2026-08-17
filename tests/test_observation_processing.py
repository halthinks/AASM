from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine as ActiveEngine
from aasm.calibration import CalibrationCertificate
from aasm.calibration_runtime import CALIBRATION_CAPABILITIES
from aasm.evidence import EvidenceRecord
from aasm.execution_environment import ExecutionEnvironment
from aasm.execution_environment_runtime import EXECUTION_ENVIRONMENT_CAPABILITIES
from aasm.external_machine import MachineBinding, MachineStateObservation
from aasm.external_machine_runtime import EXTERNAL_MACHINE_CAPABILITIES
from aasm.model import ProblemSpec
from aasm.observation_fusion import ObservationFusionRecord, observation_fusion_contract
from aasm.observation_lifecycle import (
    ObservationDisposition,
    ObservationLifecycleRecord,
    ObservationSourceRef,
    observation_lifecycle_contract,
)
from aasm.observation_processing_runtime import (
    OBSERVATION_PROCESSING_CAPABILITIES,
    ObservationProcessingRuntimeMixin,
    observation_processing_runtime_contract,
    project_observation_processing_evidence,
)
from aasm.persistence.sqlite import SQLiteStore
from aasm.physical_identity import PhysicalIdentity
from aasm.physical_identity_runtime import PHYSICAL_IDENTITY_CAPABILITIES
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.state_authority import StateClaim
from aasm.state_authority_runtime import STATE_AUTHORITY_CAPABILITIES
from aasm.typed_protocol import CapabilityContract


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
SENSOR = "sensor-a"
PROCESSOR = "processor-a"
OBSERVER_CAPABILITY = "machine.observe"
OPERATOR_CAPABILITY = "machine.operate"


class ObservationProcessingEngine(ObservationProcessingRuntimeMixin, ActiveEngine):
    pass


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None, grant_processing=True):
    engine = ObservationProcessingEngine(ProblemSpec("S3 observation processing"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "S3 observation processing fixture root", source="fixture.root-of-trust"),
        reason="S3 observation processing trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"), Workspace(WORKSPACE, ROOT), trust_anchor_evidence_id=trust.evidence_id
    )
    _grant(engine, ROOT, "identity.register")
    for principal_id in (SENSOR, PROCESSOR):
        engine.register_scoped_principal(
            Principal(principal_id, "SERVICE"), workspace_id=WORKSPACE, actor_principal_id=ROOT
        )
    engine.register_capability_contract(
        CapabilityContract(OBSERVER_CAPABILITY, "OBSERVER", "1.0.0"), authority_id="policy", authority_class="POLICY"
    )
    engine.register_capability_contract(
        CapabilityContract(OPERATOR_CAPABILITY, "OPERATOR", "1.0.0"), authority_id="policy", authority_class="POLICY"
    )
    _grant(engine, ROOT, EXTERNAL_MACHINE_CAPABILITIES["binding_register"])
    _grant(
        engine,
        ROOT,
        PHYSICAL_IDENTITY_CAPABILITIES["record"],
        CALIBRATION_CAPABILITIES["record"],
        CALIBRATION_CAPABILITIES["revoke"],
        EXECUTION_ENVIRONMENT_CAPABILITIES["record"],
        EXECUTION_ENVIRONMENT_CAPABILITIES["bind_observation"],
    )
    _grant(
        engine,
        SENSOR,
        STATE_AUTHORITY_CAPABILITIES["claim_observed"],
        EXTERNAL_MACHINE_CAPABILITIES["observation_record"],
    )
    if grant_processing:
        _grant(engine, PROCESSOR, *OBSERVATION_PROCESSING_CAPABILITIES.values())
    return engine


def prepare_observation(engine, *, value: float, receipt_id: str):
    binding = MachineBinding(
        WORKSPACE,
        SCOPE,
        "machine-device-a-r1",
        "device-a",
        ("temperature.c",),
        OBSERVER_CAPABILITY,
        OPERATOR_CAPABILITY,
        "device-r1",
        problem_revision_id="problem-r1",
    )
    engine.register_machine_binding(binding, actor_principal_id=ROOT)
    claim = StateClaim(
        "OBSERVED",
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        value,
        SENSOR,
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
        metadata={"receipt_id": receipt_id},
    )
    engine.record_state_claim(claim, actor_principal_id=SENSOR)
    observation = MachineStateObservation(
        binding.binding_id,
        claim.claim_id,
        SENSOR,
        OBSERVER_CAPABILITY,
        "device-r1",
        receipt_id=receipt_id,
    )
    engine.record_machine_state_observation(observation, actor_principal_id=SENSOR)
    return claim, observation


def prepare_calibrated_environment(engine):
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
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    engine.record_calibration(calibration, actor_principal_id=ROOT)
    environment = ExecutionEnvironment(
        WORKSPACE,
        SCOPE,
        "device-a",
        "HIL",
        "device.test.environment",
        "lab-rig-a",
        "rig-instance-01",
        "env-r1",
        configuration_revision_id="rig-config-r7",
        qualified_at_ns=200,
        physical_identity_id=identity.identity_id,
        physical_identity_fingerprint=identity.fingerprint,
        calibration_bindings={calibration.calibration_id: calibration.fingerprint},
        qualification_basis_ids=("hil-procedure-v2",),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    engine.record_execution_environment(environment, actor_principal_id=ROOT)
    return identity, calibration, environment


def raw_record(observation, value, *, suffix="1", environment_binding=None):
    kwargs = {}
    if environment_binding is not None:
        kwargs = {
            "environment_binding_id": environment_binding["binding"]["binding_id"],
            "environment_binding_fingerprint": environment_binding["binding"]["fingerprint"],
        }
    return ObservationLifecycleRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        "RAW",
        value,
        PROCESSOR,
        f"raw-capture-{suffix}",
        (ObservationSourceRef("MACHINE_STATE_OBSERVATION", observation.observation_id, observation.fingerprint),),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
        **kwargs,
    )


def next_record(source, stage, value, transformation_id, *, namespace="temperature.c", calibration=None, environment_binding=None):
    kwargs = {}
    if calibration is not None:
        kwargs["calibration_bindings"] = {calibration.calibration_id: calibration.fingerprint}
    if environment_binding is not None:
        kwargs["environment_binding_id"] = environment_binding["binding"]["binding_id"]
        kwargs["environment_binding_fingerprint"] = environment_binding["binding"]["fingerprint"]
    return ObservationLifecycleRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        stage,
        value,
        PROCESSOR,
        transformation_id,
        (ObservationSourceRef("LIFECYCLE_RECORD", source.record_id, source.fingerprint),),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
        **kwargs,
    )


def test_observation_processing_contract_preserves_authority_and_truth_firewalls():
    lifecycle = observation_lifecycle_contract()
    fusion = observation_fusion_contract()
    runtime = observation_processing_runtime_contract()
    assert lifecycle["empirical_root"] == "EXISTING_MACHINE_STATE_OBSERVATION_ONLY"
    assert lifecycle["current_observation_pointer"] == "NONE"
    assert lifecycle["lifecycle_record_grants_fact_authority"] is False
    assert lifecycle["validated_stage_is_universal_admission"] is False
    assert fusion["agreement_semantics"] == "CORROBORATION_ONLY_NEVER_AUTHORITY_OR_TRUTH_BY_VOTE"
    assert fusion["validated_by_agreement"] is False
    assert fusion["declared_independence_grants_authority"] is False
    assert runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY_FOR_RECORDING_NOT_OBSERVATION_TRUTH"
    assert runtime["fact_authority_creation"] == "NONE"
    assert runtime["effect_authority"] == "NONE"
    assert runtime["state_claim_creation"] == "NONE"
    assert runtime["current_observation_pointer"] == "NONE"
    assert runtime["parallel_observation_store"] == "NONE_EVIDENCE_PROJECTION_ONLY"
    assert runtime["parallel_truth_table"] == "NONE"
    assert runtime["parallel_authority_evaluator"] == "NONE"


def test_lifecycle_fusion_and_disposition_schemas_round_trip():
    raw = ObservationLifecycleRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        "RAW",
        25.0,
        PROCESSOR,
        "capture",
        (ObservationSourceRef("MACHINE_STATE_OBSERVATION", "obs-1", "f" * 64),),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    other = ObservationLifecycleRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        "NORMALIZED",
        25.0,
        PROCESSOR,
        "normalize",
        (ObservationSourceRef("LIFECYCLE_RECORD", raw.record_id, raw.fingerprint),),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    fusion = ObservationFusionRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        25.0,
        PROCESSOR,
        "median-v1",
        (
            ObservationSourceRef("LIFECYCLE_RECORD", other.record_id, other.fingerprint),
            ObservationSourceRef("LIFECYCLE_RECORD", "other-record", "e" * 64),
        ),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    disposition = ObservationDisposition("FUSION_RECORD", fusion.fusion_id, fusion.fingerprint, "DISPUTED", "SOURCES_DIVERGE", PROCESSOR)
    assert ObservationLifecycleRecord.from_dict(raw.to_dict()) == raw
    assert ObservationFusionRecord.from_dict(fusion.to_dict()) == fusion
    assert ObservationDisposition.from_dict(disposition.to_dict()) == disposition
    schemas = Path(__file__).resolve().parents[1] / "schemas"
    Draft202012Validator(json.loads((schemas / "observation-lifecycle.schema.json").read_text())).validate(raw.to_dict())
    Draft202012Validator(json.loads((schemas / "observation-fusion.schema.json").read_text())).validate(fusion.to_dict())
    Draft202012Validator(json.loads((schemas / "observation-disposition.schema.json").read_text())).validate(disposition.to_dict())


def test_raw_requires_exact_machine_observation_value_and_stage_skips_fail_closed():
    engine = bootstrapped_engine()
    _, observation = prepare_observation(engine, value=25.0, receipt_id="sample-1")
    wrong_raw = raw_record(observation, 26.0)
    with pytest.raises(ValueError, match="RAW lifecycle value"):
        engine.record_observation_lifecycle(wrong_raw, actor_principal_id=PROCESSOR)
    raw = raw_record(observation, 25.0)
    engine.record_observation_lifecycle(raw, actor_principal_id=PROCESSOR)
    skipped = next_record(raw, "CALIBRATED", 25.0, "illegal-skip", calibration=CalibrationCertificate(
        WORKSPACE, SCOPE, "device-a", "identity-x", "f" * 64, "MEASUREMENT", "temperature.c", "cal-x", "proc", "cert", 1, 10
    ))
    with pytest.raises(ValueError, match="invalid observation lifecycle stage transition"):
        engine.record_observation_lifecycle(skipped, actor_principal_id=PROCESSOR)


def test_calibrated_stage_requires_exact_active_calibration_and_explicit_time_context():
    engine = bootstrapped_engine()
    _, calibration, environment = prepare_calibrated_environment(engine)
    _, observation = prepare_observation(engine, value=25.0, receipt_id="sample-1")
    bound = engine.bind_machine_observation_environment(observation.observation_id, environment.environment_id, actor_principal_id=ROOT)
    raw = raw_record(observation, 25.0, environment_binding=bound)
    engine.record_observation_lifecycle(raw, actor_principal_id=PROCESSOR)
    normalized = next_record(raw, "NORMALIZED", 25.0, "normalize-v1", environment_binding=bound)
    engine.record_observation_lifecycle(normalized, actor_principal_id=PROCESSOR)
    calibrated = next_record(normalized, "CALIBRATED", 25.1, "apply-cal-v1", calibration=calibration, environment_binding=bound)
    result = engine.record_observation_lifecycle(calibrated, actor_principal_id=PROCESSOR)
    assert result["record"]["stage"] == "CALIBRATED"
    assert result["fact_authority_created"] is False
    assert result["source_observation_mutated"] is False

    no_time = next_record(normalized, "CALIBRATED", 25.1, "apply-cal-no-time", calibration=calibration)
    with pytest.raises(ValueError, match="explicit freshness or environment time context"):
        engine.record_observation_lifecycle(no_time, actor_principal_id=PROCESSOR)

    forged = ObservationLifecycleRecord.from_dict({
        **calibrated.to_dict(),
        "record_id": "",
        "transformation_id": "apply-forged-cal",
        "calibration_bindings": {calibration.calibration_id: "e" * 64},
    })
    with pytest.raises(ValueError, match="calibration fingerprint mismatch"):
        engine.record_observation_lifecycle(forged, actor_principal_id=PROCESSOR)


def _derived_chain(engine, *, value: float, receipt_id: str, suffix: str):
    _, observation = prepare_observation(engine, value=value, receipt_id=receipt_id)
    raw = raw_record(observation, value, suffix=suffix)
    engine.record_observation_lifecycle(raw, actor_principal_id=PROCESSOR)
    normalized = next_record(raw, "NORMALIZED", value, f"normalize-{suffix}")
    engine.record_observation_lifecycle(normalized, actor_principal_id=PROCESSOR)
    derived = next_record(normalized, "DERIVED", value, f"derive-{suffix}")
    engine.record_observation_lifecycle(derived, actor_principal_id=PROCESSOR)
    return observation, raw, normalized, derived


def test_fusion_requires_exact_processed_sources_and_agreement_never_mints_authority():
    engine = bootstrapped_engine()
    _, _, _, first = _derived_chain(engine, value=25.0, receipt_id="sample-1", suffix="1")
    _, _, _, second = _derived_chain(engine, value=25.2, receipt_id="sample-2", suffix="2")
    basis = engine.add_evidence(EvidenceRecord("independence", "two acquisition paths declared separately clocked", source="fixture"), reason="fusion independence basis")
    fusion = ObservationFusionRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        25.1,
        PROCESSOR,
        "median-v1",
        (
            ObservationSourceRef("LIFECYCLE_RECORD", first.record_id, first.fingerprint),
            ObservationSourceRef("LIFECYCLE_RECORD", second.record_id, second.fingerprint),
        ),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
        independence="DECLARED_INDEPENDENT",
        independence_basis_evidence_ids=(basis.evidence_id,),
    )
    result = engine.record_observation_fusion(fusion, actor_principal_id=PROCESSOR)
    assert result["fusion"]["value"] == 25.1
    assert result["fact_authority_created"] is False
    assert result["observation_authority_elevated"] is False
    assert result["agreement_granted_authority"] is False
    assert result["declared_independence_granted_authority"] is False

    validated = ObservationLifecycleRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        "VALIDATED",
        25.1,
        PROCESSOR,
        "local-validation-v1",
        (ObservationSourceRef("FUSION_RECORD", fusion.fusion_id, fusion.fingerprint),),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    validated_result = engine.record_observation_lifecycle(validated, actor_principal_id=PROCESSOR)
    assert validated_result["universal_admission_granted"] is False
    assert validated_result["fact_authority_created"] is False


def test_fusion_cannot_bypass_raw_lifecycle_or_accept_forged_fingerprint():
    engine = bootstrapped_engine()
    _, observation = prepare_observation(engine, value=25.0, receipt_id="sample-1")
    with pytest.raises(ValueError, match="cannot bypass lifecycle"):
        ObservationFusionRecord(
            WORKSPACE,
            SCOPE,
            "device-a",
            "temperature.c",
            25.0,
            PROCESSOR,
            "illegal",
            (
                ObservationSourceRef("MACHINE_STATE_OBSERVATION", observation.observation_id, observation.fingerprint),
                ObservationSourceRef("LIFECYCLE_RECORD", "x", "f" * 64),
            ),
        )
    _, _, _, first = _derived_chain(engine, value=25.0, receipt_id="sample-2", suffix="2")
    _, _, _, second = _derived_chain(engine, value=25.2, receipt_id="sample-3", suffix="3")
    forged = ObservationFusionRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        25.1,
        PROCESSOR,
        "median-v1",
        (
            ObservationSourceRef("LIFECYCLE_RECORD", first.record_id, "e" * 64),
            ObservationSourceRef("LIFECYCLE_RECORD", second.record_id, second.fingerprint),
        ),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    with pytest.raises(ValueError, match="source fingerprint mismatch"):
        engine.record_observation_fusion(forged, actor_principal_id=PROCESSOR)


def test_disposition_is_append_only_and_disposed_sources_fail_closed_for_new_fusion():
    engine = bootstrapped_engine()
    _, _, _, first = _derived_chain(engine, value=25.0, receipt_id="sample-1", suffix="1")
    _, _, _, second = _derived_chain(engine, value=25.2, receipt_id="sample-2", suffix="2")
    disposition = ObservationDisposition(
        "LIFECYCLE_RECORD",
        first.record_id,
        first.fingerprint,
        "DISPUTED",
        "SENSOR_DISAGREEMENT_REVIEW",
        PROCESSOR,
    )
    result = engine.record_observation_disposition(disposition, actor_principal_id=PROCESSOR)
    assert result["source_deleted"] is False
    assert result["source_mutated"] is False
    original = engine.observation_lifecycle_record_report(first.record_id)
    assert original["record"]["fingerprint"] == first.fingerprint
    assert original["dispositions"][0]["disposition"]["disposition"] == "DISPUTED"
    fusion = ObservationFusionRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        25.1,
        PROCESSOR,
        "median-v1",
        (
            ObservationSourceRef("LIFECYCLE_RECORD", first.record_id, first.fingerprint),
            ObservationSourceRef("LIFECYCLE_RECORD", second.record_id, second.fingerprint),
        ),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    with pytest.raises(ValueError, match="disposed source"):
        engine.record_observation_fusion(fusion, actor_principal_id=PROCESSOR)


def test_scoped_recording_authority_is_required_but_does_not_become_truth_authority():
    engine = bootstrapped_engine(grant_processing=False)
    _, observation = prepare_observation(engine, value=25.0, receipt_id="sample-1")
    raw = raw_record(observation, 25.0)
    with pytest.raises(PermissionError, match="observation-processing denied"):
        engine.record_observation_lifecycle(raw, actor_principal_id=PROCESSOR)


def test_projection_detects_lineage_cycle_even_when_source_fingerprints_are_forged():
    a = ObservationLifecycleRecord(
        WORKSPACE, SCOPE, "device-a", "temperature.c", "NORMALIZED", 1, PROCESSOR, "a",
        (ObservationSourceRef("LIFECYCLE_RECORD", "b", "b" * 64),), record_id="a"
    )
    b = ObservationLifecycleRecord(
        WORKSPACE, SCOPE, "device-a", "temperature.c", "NORMALIZED", 1, PROCESSOR, "b",
        (ObservationSourceRef("LIFECYCLE_RECORD", "a", "a" * 64),), record_id="b"
    )
    rows = []
    for item, evidence_id in ((a, "e-a"), (b, "e-b")):
        rows.append({
            "status": "active",
            "evidence_id": evidence_id,
            "statement": json.dumps(item.to_dict(), sort_keys=True),
            "metadata": {
                "aasm_observation_processing_record_type": "OBSERVATION_LIFECYCLE_RECORD",
                "document": item.to_dict(),
                "object_id": item.record_id,
                "object_fingerprint": item.fingerprint,
            },
        })
    report = project_observation_processing_evidence(rows)
    assert report["valid"] is False
    assert any("lineage cycle" in issue["error"] for issue in report["issues"])


def test_sqlite_restart_replay_preserves_lifecycle_fusion_and_disposition(tmp_path):
    path = tmp_path / "observation-processing.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    _, _, _, first = _derived_chain(engine, value=25.0, receipt_id="sample-1", suffix="1")
    _, _, _, second = _derived_chain(engine, value=25.2, receipt_id="sample-2", suffix="2")
    fusion = ObservationFusionRecord(
        WORKSPACE,
        SCOPE,
        "device-a",
        "temperature.c",
        25.1,
        PROCESSOR,
        "median-v1",
        (
            ObservationSourceRef("LIFECYCLE_RECORD", first.record_id, first.fingerprint),
            ObservationSourceRef("LIFECYCLE_RECORD", second.record_id, second.fingerprint),
        ),
        problem_revision_id="problem-r1",
        external_revision_id="device-r1",
    )
    engine.record_observation_fusion(fusion, actor_principal_id=PROCESSOR)
    disposition = ObservationDisposition("FUSION_RECORD", fusion.fusion_id, fusion.fingerprint, "SUPERSEDED", "NEW_SAMPLE_WINDOW", PROCESSOR)
    engine.record_observation_disposition(disposition, actor_principal_id=PROCESSOR)
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = ObservationProcessingEngine.resume(machine_id, reopened)
    fusion_report = resumed.observation_fusion_record_report(fusion.fusion_id)
    assert fusion_report["fusion"]["fingerprint"] == fusion.fingerprint
    assert fusion_report["dispositions"][0]["disposition"]["disposition"] == "SUPERSEDED"
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
