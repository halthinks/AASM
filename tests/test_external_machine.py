from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine
from aasm.evidence import EvidenceRecord
from aasm.external_machine import MachineBinding, MachineStateObservation, external_machine_contract
from aasm.external_machine_runtime import EXTERNAL_MACHINE_CAPABILITIES, external_machine_runtime_contract
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.state_authority import StateClaim
from aasm.state_authority_runtime import STATE_AUTHORITY_CAPABILITIES
from aasm.typed_protocol import CapabilityContract


OBSERVER_CAPABILITY = "machine.observe"
OPERATOR_CAPABILITY = "machine.operate"


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, "root", "workspace-a", "root", tuple(capabilities))
    )


def bootstrapped_engine(*, store=None, grant_binding=True, grant_observation=True):
    engine = AASMEngine(ProblemSpec("external machine binding"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord(
            kind="trust_anchor",
            statement="operator admitted workspace root identity",
            source="fixture.root-of-trust",
        ),
        reason="external machine fixture trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace("workspace-a", "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    _grant(engine, "root", "identity.register")
    engine.register_scoped_principal(
        Principal("sensor-a", "MACHINE"),
        workspace_id="workspace-a",
        actor_principal_id="root",
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
    root_caps = []
    if grant_binding:
        root_caps.append(EXTERNAL_MACHINE_CAPABILITIES["binding_register"])
    if root_caps:
        _grant(engine, "root", *root_caps)
    sensor_caps = [STATE_AUTHORITY_CAPABILITIES["claim_observed"], STATE_AUTHORITY_CAPABILITIES["claim_predicted"]]
    if grant_observation:
        sensor_caps.append(EXTERNAL_MACHINE_CAPABILITIES["observation_record"])
    _grant(engine, "sensor-a", *sensor_caps)
    return engine


def binding(**overrides):
    values = {
        "workspace_id": "workspace-a",
        "scope_id": "root",
        "external_machine_id": "machine-a",
        "subject_id": "device-a",
        "state_namespaces": ("temperature.c", "humidity.relative"),
        "observer_capability_id": OBSERVER_CAPABILITY,
        "executor_capability_id": OPERATOR_CAPABILITY,
        "external_revision_id": "device-rev-1",
    }
    values.update(overrides)
    return MachineBinding(**values)


def observed_claim(*, namespace="temperature.c", subject_id="device-a", external_revision_id="device-rev-1", value=21.5):
    return StateClaim(
        "OBSERVED",
        "workspace-a",
        "root",
        subject_id,
        namespace,
        value,
        "sensor-a",
        external_revision_id=external_revision_id,
    )


def machine_observation(bound: MachineBinding, claim: StateClaim, **overrides):
    values = {
        "binding_id": bound.binding_id,
        "state_claim_id": claim.claim_id,
        "observer_principal_id": "sensor-a",
        "observer_capability_id": OBSERVER_CAPABILITY,
        "external_revision_id": "device-rev-1",
        "receipt_id": "receipt-1",
        "correlation_id": "sample-1",
    }
    values.update(overrides)
    return MachineStateObservation(**values)


def test_external_machine_contract_is_reference_only_and_grants_no_authority():
    semantic = external_machine_contract()
    runtime = external_machine_runtime_contract()
    assert semantic["binding_role"] == "REFERENCE_AND_CORRELATION_ONLY_NOT_EXTERNAL_STATE_COPY"
    assert semantic["state_truth_source"] == "PR1_STATE_CLAIM_EVIDENCE_ONLY"
    assert semantic["binding_grants_fact_authority"] is False
    assert semantic["binding_grants_effect_authority"] is False
    assert semantic["capability_reference_grants_authority"] is False
    assert semantic["external_state_table"] == "NONE"
    assert semantic["executor_invocation"] == "NONE_BY_THIS_FOUNDATION"
    assert semantic["postcondition_achievement_claim"] == "NOT_YET_CLAIMED_PR2C"
    assert runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert runtime["external_state_table"] == "NONE"
    assert runtime["effect_dispatch"] == "NONE"
    assert runtime["machine_state_mutation"] == "NONE"


def test_machine_binding_and_observation_are_deterministic_and_schema_valid():
    bound = binding()
    bound2 = MachineBinding.from_dict(bound.to_dict())
    assert bound2 == bound
    assert bound2.fingerprint == bound.fingerprint
    observation = MachineStateObservation(
        bound.binding_id,
        "state-claim-1",
        "sensor-a",
        OBSERVER_CAPABILITY,
        "device-rev-1",
        receipt_id="receipt-1",
    )
    observation2 = MachineStateObservation.from_dict(observation.to_dict())
    assert observation2 == observation
    assert observation2.fingerprint == observation.fingerprint
    root = Path(__file__).resolve().parents[1]
    Draft202012Validator(json.loads((root / "schemas" / "machine-binding.schema.json").read_text())).validate(bound.to_dict())
    Draft202012Validator(json.loads((root / "schemas" / "machine-state-observation.schema.json").read_text())).validate(observation.to_dict())


def test_binding_registration_requires_existing_scoped_authority():
    engine = bootstrapped_engine(grant_binding=False)
    with pytest.raises(PermissionError, match="machine.binding.register"):
        engine.register_machine_binding(binding(), actor_principal_id="root")
    assert engine.external_machine_report()["bindings"] == {}


def test_binding_requires_admitted_observer_and_operator_capability_types():
    engine = bootstrapped_engine()
    with pytest.raises(KeyError, match="unknown machine capability reference"):
        engine.register_machine_binding(
            binding(observer_capability_id="machine.missing"),
            actor_principal_id="root",
        )
    with pytest.raises(ValueError, match="must be OPERATOR"):
        engine.register_machine_binding(
            binding(executor_capability_id=OBSERVER_CAPABILITY),
            actor_principal_id="root",
        )
    with pytest.raises(ValueError, match="must be OBSERVER"):
        engine.register_machine_binding(
            binding(observer_capability_id=OPERATOR_CAPABILITY),
            actor_principal_id="root",
        )


def test_binding_references_do_not_create_fact_authority_or_effect_authority():
    engine = bootstrapped_engine()
    before_authorities = deepcopy(engine.state_authority_report()["authorities"])
    before_state = engine.snapshot.state
    before_active_values = deepcopy(engine.calculus_report()["active_values"])
    result = engine.register_machine_binding(binding(), actor_principal_id="root")
    assert result["binding"]["binding_id"]
    assert engine.state_authority_report()["authorities"] == before_authorities == {}
    report = engine.external_machine_report()
    assert report["fact_authority"] == "NONE_GRANTED"
    assert report["effect_authority"] == "NONE_GRANTED"
    assert report["executor_invocation"] == "NONE"
    assert report["effect_dispatch"] == "NONE"
    assert engine.snapshot.state == before_state
    assert engine.calculus_report()["active_values"] == before_active_values


def test_binding_rejects_unknown_fact_authority_reference_without_creating_one():
    engine = bootstrapped_engine()
    with pytest.raises(KeyError, match="unknown fact authority references"):
        engine.register_machine_binding(
            binding(fact_authority_ids=("fact-authority-missing",)),
            actor_principal_id="root",
        )
    assert engine.state_authority_report()["authorities"] == {}
    assert engine.external_machine_report()["bindings"] == {}


def test_machine_observation_requires_durable_observed_state_claim_and_existing_binding():
    engine = bootstrapped_engine()
    bound = binding()
    engine.register_machine_binding(bound, actor_principal_id="root")
    predicted = StateClaim(
        "PREDICTED",
        "workspace-a",
        "root",
        "device-a",
        "temperature.c",
        22.0,
        "sensor-a",
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(predicted, actor_principal_id="sensor-a")
    with pytest.raises(ValueError, match="durable OBSERVED state claim"):
        engine.record_machine_state_observation(
            machine_observation(bound, predicted),
            actor_principal_id="sensor-a",
        )
    observation = observed_claim()
    engine.record_state_claim(observation, actor_principal_id="sensor-a")
    missing = MachineStateObservation(
        "binding-missing",
        observation.claim_id,
        "sensor-a",
        OBSERVER_CAPABILITY,
        "device-rev-1",
    )
    with pytest.raises(KeyError, match="unknown machine binding"):
        engine.record_machine_state_observation(missing, actor_principal_id="sensor-a")


def test_machine_observation_rejects_subject_namespace_revision_and_capability_laundering():
    engine = bootstrapped_engine()
    bound = binding()
    engine.register_machine_binding(bound, actor_principal_id="root")

    wrong_subject = observed_claim(subject_id="device-b")
    engine.record_state_claim(wrong_subject, actor_principal_id="sensor-a")
    with pytest.raises(ValueError, match="subject does not match"):
        engine.record_machine_state_observation(machine_observation(bound, wrong_subject), actor_principal_id="sensor-a")

    wrong_namespace = observed_claim(namespace="pressure.kpa")
    engine.record_state_claim(wrong_namespace, actor_principal_id="sensor-a")
    with pytest.raises(ValueError, match="namespace is not supported"):
        engine.record_machine_state_observation(machine_observation(bound, wrong_namespace), actor_principal_id="sensor-a")

    wrong_revision = observed_claim(external_revision_id="device-rev-2")
    engine.record_state_claim(wrong_revision, actor_principal_id="sensor-a")
    with pytest.raises(ValueError, match="source claim external revision"):
        engine.record_machine_state_observation(machine_observation(bound, wrong_revision), actor_principal_id="sensor-a")

    correct = observed_claim()
    engine.record_state_claim(correct, actor_principal_id="sensor-a")
    with pytest.raises(ValueError, match="capability does not match binding"):
        engine.record_machine_state_observation(
            machine_observation(bound, correct, observer_capability_id=OPERATOR_CAPABILITY),
            actor_principal_id="sensor-a",
        )
    with pytest.raises(ValueError, match="external revision does not match binding"):
        engine.record_machine_state_observation(
            machine_observation(bound, correct, external_revision_id="device-rev-2"),
            actor_principal_id="sensor-a",
        )


def test_machine_observation_source_principal_cannot_be_impersonated_and_scoped_authority_is_required():
    engine = bootstrapped_engine(grant_observation=False)
    bound = binding()
    engine.register_machine_binding(bound, actor_principal_id="root")
    claim = observed_claim()
    engine.record_state_claim(claim, actor_principal_id="sensor-a")
    item = machine_observation(bound, claim)
    with pytest.raises(PermissionError, match="actor must equal observer_principal_id"):
        engine.record_machine_state_observation(item, actor_principal_id="root")
    with pytest.raises(PermissionError, match="machine.observation.record"):
        engine.record_machine_state_observation(item, actor_principal_id="sensor-a")
    assert engine.external_machine_report(bound.binding_id)["observations"] == {}


def test_valid_machine_observation_correlates_existing_claim_without_mutating_core_state_or_granting_authority():
    engine = bootstrapped_engine()
    bound = binding()
    engine.register_machine_binding(bound, actor_principal_id="root")
    claim = observed_claim()
    state_claim_result = engine.record_state_claim(claim, actor_principal_id="sensor-a")
    before_state = engine.snapshot.state
    before_active_values = deepcopy(engine.calculus_report()["active_values"])
    before_fact_authorities = deepcopy(engine.state_authority_report()["authorities"])
    result = engine.record_machine_state_observation(
        machine_observation(bound, claim),
        actor_principal_id="sensor-a",
    )
    assert result["state_claim"]["claim_id"] == claim.claim_id
    assert result["fact_authority_granted"] is False
    assert result["effect_authority_granted"] is False
    assert result["executor_invoked"] is False
    assert state_claim_result["evidence_id"] in next(
        row["derived_from"]
        for row in engine.snapshot.evidence["records"]
        if row["evidence_id"] == result["evidence_id"]
    )
    report = engine.external_machine_report(bound.binding_id)
    assert len(report["observations"]) == 1
    assert report["external_state_table"] == "NONE"
    assert report["effect_dispatch"] == "NONE"
    assert report["postcondition_verification"] == "NOT_IMPLEMENTED_PR2A"
    assert engine.state_authority_report()["authorities"] == before_fact_authorities
    assert engine.snapshot.state == before_state
    assert engine.calculus_report()["active_values"] == before_active_values
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_sqlite_restart_reconstructs_bindings_and_observation_correlations_from_evidence(tmp_path: Path):
    path = tmp_path / "external-machine.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    bound = binding()
    engine.register_machine_binding(bound, actor_principal_id="root")
    claim = observed_claim()
    engine.record_state_claim(claim, actor_principal_id="sensor-a")
    observation = machine_observation(bound, claim)
    engine.record_machine_state_observation(observation, actor_principal_id="sensor-a")
    before = engine.external_machine_report()
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, reopened)
    after = resumed.external_machine_report()
    assert after["bindings"] == before["bindings"]
    assert after["observations"] == before["observations"]
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
