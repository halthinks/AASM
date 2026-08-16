from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine, FactAuthority, StateClaim
from aasm.effect_capability import EffectCapability
from aasm.effect_capability_runtime import EFFECT_CAPABILITY_CAPABILITIES
from aasm.effects import EffectStatus
from aasm.evidence import EvidenceRecord
from aasm.external_machine import MachineBinding, MachineStateObservation
from aasm.external_machine_postcondition import (
    MachinePostconditionVerification,
    machine_postcondition_verification_contract,
)
from aasm.external_machine_postcondition_runtime import (
    MACHINE_POSTCONDITION_CAPABILITIES,
    machine_postcondition_runtime_contract,
)
from aasm.external_machine_runtime import EXTERNAL_MACHINE_CAPABILITIES
from aasm.external_machine_transition_runtime import MACHINE_TRANSITION_CAPABILITIES
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.physical_authority import AuthorityDomain, AuthorityLease
from aasm.physical_authority_runtime import PHYSICAL_AUTHORITY_CAPABILITIES
from aasm.physical_effect_integration_runtime import PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES
from aasm.resources import ResourceRecord, TaskDemand
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.state_authority_runtime import STATE_AUTHORITY_CAPABILITIES
from aasm.typed_protocol import CapabilityContract
from aasm.workers import WorkerRecord


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
SENSOR = "sensor-a"
VERIFIER = "verifier-a"
OBSERVER_CAPABILITY = "machine.observe"
OPERATOR_CAPABILITY = "machine.operate"

PostconditionEngine = AASMEngine


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None):
    engine = PostconditionEngine(ProblemSpec("machine postcondition verification"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "operator admitted workspace root identity", source="fixture.root-of-trust"),
        reason="machine postcondition fixture trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    _grant(engine, ROOT, "identity.register")
    engine.register_scoped_principal(
        Principal(SENSOR, "MACHINE"), workspace_id=WORKSPACE, actor_principal_id=ROOT,
    )
    engine.register_scoped_principal(
        Principal(VERIFIER, "SERVICE"), workspace_id=WORKSPACE, actor_principal_id=ROOT,
    )
    engine.register_capability_contract(
        CapabilityContract(OBSERVER_CAPABILITY, "OBSERVER", "1.0.0"),
        authority_id="policy", authority_class="POLICY",
    )
    engine.register_capability_contract(
        CapabilityContract(OPERATOR_CAPABILITY, "OPERATOR", "1.0.0"),
        authority_id="policy", authority_class="POLICY",
    )
    _grant(
        engine,
        ROOT,
        STATE_AUTHORITY_CAPABILITIES["fact_authority_register"],
        STATE_AUTHORITY_CAPABILITIES["claim_desired"],
        EXTERNAL_MACHINE_CAPABILITIES["binding_register"],
        MACHINE_TRANSITION_CAPABILITIES["transition_propose"],
        PHYSICAL_AUTHORITY_CAPABILITIES["domain_register"],
        PHYSICAL_AUTHORITY_CAPABILITIES["lease_grant"],
        EFFECT_CAPABILITY_CAPABILITIES["issue"],
        PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES["bind"],
        "effect.authorize",
        "effect.execute",
    )
    _grant(
        engine,
        SENSOR,
        STATE_AUTHORITY_CAPABILITIES["claim_observed"],
        STATE_AUTHORITY_CAPABILITIES["claim_authoritative"],
        EXTERNAL_MACHINE_CAPABILITIES["observation_record"],
    )
    _grant(engine, VERIFIER, MACHINE_POSTCONDITION_CAPABILITIES["verify"])
    return engine


def _bind_transition_physical_authority(engine, effect_id: str):
    domain = AuthorityDomain(
        WORKSPACE,
        SCOPE,
        "postcondition-machine-control",
        "device-a",
        ("set-temperature",),
        external_revision_id="device-rev-1",
    )
    engine.register_authority_domain(domain, actor_principal_id=ROOT)
    lease = AuthorityLease(
        domain.domain_id,
        WORKSPACE,
        SCOPE,
        ROOT,
        ROOT,
        1,
        0.0,
        1000.0,
        ("set-temperature",),
        external_revision_id="device-rev-1",
    )
    engine.grant_authority_lease(lease, actor_principal_id=ROOT, at_time=0.0)
    capability = EffectCapability(
        domain.domain_id,
        lease.lease_id,
        WORKSPACE,
        SCOPE,
        "device-a",
        ROOT,
        ROOT,
        ("set-temperature",),
        {"target_c": {"minimum": 0.0, "maximum": 100.0}},
        0.0,
        1000.0,
        1,
        external_revision_id="device-rev-1",
    )
    engine.issue_effect_capability(capability, actor_principal_id=ROOT, at_time=0.0)
    result = engine.bind_physical_effect_authority(
        effect_id,
        authority_lease_id=lease.lease_id,
        effect_capability_id=capability.capability_id,
        actor_principal_id=ROOT,
        at_time=0.0,
    )
    assert result["effect_authority_granted"] is False
    return domain, lease, capability, result


def prepare_transition(engine):
    authority = FactAuthority(
        WORKSPACE, SCOPE, "device-a", "temperature.c", SENSOR,
        external_revision_id="device-rev-1",
    )
    engine.register_fact_authority(authority, actor_principal_id=ROOT)
    binding = MachineBinding(
        WORKSPACE,
        SCOPE,
        "machine-a",
        "device-a",
        ("temperature.c",),
        OBSERVER_CAPABILITY,
        OPERATOR_CAPABILITY,
        "device-rev-1",
        fact_authority_ids=(authority.authority_id,),
    )
    engine.register_machine_binding(binding, actor_principal_id=ROOT)

    pre_observed = StateClaim(
        "OBSERVED", WORKSPACE, SCOPE, "device-a", "temperature.c", 21.5, SENSOR,
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(pre_observed, actor_principal_id=SENSOR)
    pre_machine_observation = MachineStateObservation(
        binding.binding_id,
        pre_observed.claim_id,
        SENSOR,
        OBSERVER_CAPABILITY,
        "device-rev-1",
        receipt_id="pre-sample",
        correlation_id="pre-execution",
    )
    engine.record_machine_state_observation(pre_machine_observation, actor_principal_id=SENSOR)
    pre_authoritative = StateClaim(
        "AUTHORITATIVE", WORKSPACE, SCOPE, "device-a", "temperature.c", 21.5, SENSOR,
        external_revision_id="device-rev-1", source_claim_ids=(pre_observed.claim_id,),
    )
    engine.record_state_claim(pre_authoritative, actor_principal_id=SENSOR)
    desired = StateClaim(
        "DESIRED", WORKSPACE, SCOPE, "device-a", "temperature.c", 25.0, ROOT,
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(desired, actor_principal_id=ROOT)
    proposed = engine.propose_machine_transition(
        binding.binding_id,
        operation="set-temperature",
        expected_state_claim_ids=(pre_authoritative.claim_id,),
        target_state_claim_ids=(desired.claim_id,),
        external_revision_id="device-rev-1",
        proposer_principal_id=ROOT,
        payload={"target_c": 25.0},
    )
    _bind_transition_physical_authority(engine, proposed["transition"]["effect_id"])
    return binding, authority, pre_machine_observation, desired, proposed


def _effect_lease(engine, effect_id: str, *, worker_id="effect-worker"):
    if not engine.list_resources():
        engine.register_resource(
            ResourceRecord("effect-worker-resource", "local", capabilities=["effect.execute"], capacity=4.0)
        )
        engine.register_worker(WorkerRecord(worker_id, "effect-worker-resource"))
    task = TaskDemand(
        f"effect-task-{effect_id[-16:]}",
        required_capabilities=["effect.execute"],
        metadata={"effect_id": effect_id},
    )
    return engine.claim_task(task, worker_id, lease_seconds=600.0)


def _execute_existing_effect(engine, effect_id: str):
    engine.authorize_effect(
        effect_id, workspace_id=WORKSPACE, scope_id=SCOPE, actor_principal_id=ROOT,
    )
    lease = _effect_lease(engine, effect_id)
    result = engine.execute_effect(
        effect_id,
        lambda spec, key: {"ack": True, "idempotency_key": key},
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
        owner_worker_id="effect-worker",
        task_lease_id=lease["lease_id"],
    )
    record = engine.store.load_effect(engine.snapshot.machine_id, effect_id)
    assert record.status == EffectStatus.SUCCEEDED.value
    assert record.execution_id
    assert record.ownership is not None
    assert record.ownership["task_lease_id"] == lease["lease_id"]
    return result, record, lease


def record_achieved_state(engine, binding, *, execution_id: str, value=25.0, correlate=True):
    observed = StateClaim(
        "OBSERVED", WORKSPACE, SCOPE, "device-a", "temperature.c", value, SENSOR,
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(observed, actor_principal_id=SENSOR)
    observation = MachineStateObservation(
        binding.binding_id, observed.claim_id, SENSOR, OBSERVER_CAPABILITY, "device-rev-1",
        receipt_id="post-sample", correlation_id=execution_id if correlate else "wrong-execution",
    )
    engine.record_machine_state_observation(observation, actor_principal_id=SENSOR)
    authoritative = StateClaim(
        "AUTHORITATIVE", WORKSPACE, SCOPE, "device-a", "temperature.c", value, SENSOR,
        external_revision_id="device-rev-1", source_claim_ids=(observed.claim_id,),
    )
    engine.record_state_claim(authoritative, actor_principal_id=SENSOR)
    return observed, observation, authoritative


def test_postcondition_contract_keeps_effect_success_separate_from_achievement():
    semantic = machine_postcondition_verification_contract()
    runtime = machine_postcondition_runtime_contract()
    assert semantic["effect_status_requirement"] == "EXISTING_AASM_EFFECT_MUST_BE_SUCCEEDED"
    assert semantic["unknown_effect"] == "BLOCKED_USE_EXISTING_EFFECT_RECONCILIATION"
    assert semantic["target_source"] == "PR2B_DURABLE_DESIRED_STATE_CLAIMS"
    assert semantic["achieved_source"] == "PR1_DURABLE_AUTHORITATIVE_STATE_CLAIMS_ONLY"
    assert semantic["observation_correlation"] == "PR2A_MACHINE_STATE_OBSERVATION_CORRELATION_ID_MUST_EQUAL_EXISTING_EFFECT_EXECUTION_ID"
    assert semantic["comparison"] == "EXACT_CANONICAL_VALUE_EQUALITY_ONLY_NO_TOLERANCE_IN_THIS_FOUNDATION"
    assert semantic["effect_success_is_achievement"] is False
    assert semantic["verification_mints_fact_authority"] is False
    assert semantic["verification_mints_state_claim"] is False
    assert semantic["verification_mutates_effect_outcome"] is False
    assert semantic["parallel_truth_table"] == "NONE"
    assert runtime["effect_source"] == "EXISTING_AASM_EFFECT_RECORD_ONLY"
    assert runtime["effect_status_mutation"] == "NONE"
    assert runtime["state_claim_creation"] == "NONE"
    assert runtime["fact_authority_creation"] == "NONE"
    assert runtime["parallel_effect_lifecycle"] == "NONE"


def test_postcondition_verification_object_is_deterministic_and_schema_valid():
    item = MachinePostconditionVerification(
        "transition-1", "effect-1", "binding-1", VERIFIER, "VERIFIED",
        ("target-1",), ("achieved-1",), ("observation-1",),
        {"namespaces": {"temperature.c": {"match": True}}, "all_match": True},
    )
    copy = MachinePostconditionVerification.from_dict(item.to_dict())
    assert copy == item
    assert copy.fingerprint == item.fingerprint
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "machine-postcondition-verification.schema.json").read_text())
    Draft202012Validator(schema).validate(item.to_dict())


def test_proposed_or_authorized_effect_cannot_be_treated_as_achieved():
    engine = bootstrapped_engine()
    _, _, _, _, proposed = prepare_transition(engine)
    transition_id = proposed["transition"]["transition_id"]
    old_observation_id = next(iter(engine.external_machine_report()["observations"]))
    with pytest.raises(ValueError, match="must be SUCCEEDED"):
        engine.verify_machine_transition_postconditions(
            transition_id,
            achieved_state_claim_ids=(proposed["transition"]["expected_state_claim_ids"][0],),
            machine_observation_ids=(old_observation_id,),
            verifier_principal_id=VERIFIER,
        )
    engine.authorize_effect(
        proposed["transition"]["effect_id"], workspace_id=WORKSPACE, scope_id=SCOPE, actor_principal_id=ROOT,
    )
    with pytest.raises(ValueError, match="must be SUCCEEDED"):
        engine.verify_machine_transition_postconditions(
            transition_id,
            achieved_state_claim_ids=(proposed["transition"]["expected_state_claim_ids"][0],),
            machine_observation_ids=(old_observation_id,),
            verifier_principal_id=VERIFIER,
        )


def test_succeeded_effect_alone_is_insufficient_without_correlated_authoritative_observation():
    engine = bootstrapped_engine()
    _, _, pre_observation, _, proposed = prepare_transition(engine)
    _, effect, _ = _execute_existing_effect(engine, proposed["transition"]["effect_id"])
    assert effect.status == EffectStatus.SUCCEEDED.value
    with pytest.raises(ValueError, match="correlation_id must equal existing effect execution_id"):
        engine.verify_machine_transition_postconditions(
            proposed["transition"]["transition_id"],
            achieved_state_claim_ids=(proposed["transition"]["expected_state_claim_ids"][0],),
            machine_observation_ids=(pre_observation.observation_id,),
            verifier_principal_id=VERIFIER,
        )
    assert engine.machine_postconditions_report()["verifications"] == {}


def test_correlated_observation_without_authoritative_admission_cannot_verify():
    engine = bootstrapped_engine()
    binding, _, _, _, proposed = prepare_transition(engine)
    _, effect, _ = _execute_existing_effect(engine, proposed["transition"]["effect_id"])
    observed = StateClaim(
        "OBSERVED", WORKSPACE, SCOPE, "device-a", "temperature.c", 25.0, SENSOR,
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(observed, actor_principal_id=SENSOR)
    observation = MachineStateObservation(
        binding.binding_id, observed.claim_id, SENSOR, OBSERVER_CAPABILITY, "device-rev-1",
        receipt_id="post", correlation_id=effect.execution_id,
    )
    engine.record_machine_state_observation(observation, actor_principal_id=SENSOR)
    with pytest.raises(ValueError, match="requires AUTHORITATIVE state claim"):
        engine.verify_machine_transition_postconditions(
            proposed["transition"]["transition_id"],
            achieved_state_claim_ids=(observed.claim_id,),
            machine_observation_ids=(observation.observation_id,),
            verifier_principal_id=VERIFIER,
        )


def test_authoritative_claim_must_derive_from_supplied_correlated_observation():
    engine = bootstrapped_engine()
    binding, _, _, _, proposed = prepare_transition(engine)
    _, effect, _ = _execute_existing_effect(engine, proposed["transition"]["effect_id"])
    _, observation, authoritative = record_achieved_state(engine, binding, execution_id=effect.execution_id, value=25.0)
    other_observed = StateClaim(
        "OBSERVED", WORKSPACE, SCOPE, "device-a", "temperature.c", 25.0, SENSOR,
        external_revision_id="device-rev-1", metadata={"sample": "other"},
    )
    engine.record_state_claim(other_observed, actor_principal_id=SENSOR)
    other_authoritative = StateClaim(
        "AUTHORITATIVE", WORKSPACE, SCOPE, "device-a", "temperature.c", 25.0, SENSOR,
        external_revision_id="device-rev-1", source_claim_ids=(other_observed.claim_id,), metadata={"sample": "other"},
    )
    engine.record_state_claim(other_authoritative, actor_principal_id=SENSOR)
    with pytest.raises(ValueError, match="must derive from OBSERVED claim correlated"):
        engine.verify_machine_transition_postconditions(
            proposed["transition"]["transition_id"],
            achieved_state_claim_ids=(other_authoritative.claim_id,),
            machine_observation_ids=(observation.observation_id,),
            verifier_principal_id=VERIFIER,
        )
    assert authoritative.claim_id != other_authoritative.claim_id


def test_exact_matching_authoritative_state_verifies_without_mutating_effect_truth_or_core_state():
    engine = bootstrapped_engine()
    binding, authority, _, _, proposed = prepare_transition(engine)
    _, effect, _ = _execute_existing_effect(engine, proposed["transition"]["effect_id"])
    _, observation, authoritative = record_achieved_state(engine, binding, execution_id=effect.execution_id, value=25.0)
    before_claims = set(engine.state_authority_report()["claims"])
    before_authorities = deepcopy(engine.state_authority_report()["authorities"])
    before_machine_state = engine.snapshot.state
    before_active_values = deepcopy(engine.calculus_report()["active_values"])
    before_effect = engine.store.load_effect(engine.snapshot.machine_id, effect.spec.effect_id)

    result = engine.verify_machine_transition_postconditions(
        proposed["transition"]["transition_id"],
        achieved_state_claim_ids=(authoritative.claim_id,),
        machine_observation_ids=(observation.observation_id,),
        verifier_principal_id=VERIFIER,
    )
    assert result["verification"]["verdict"] == "VERIFIED"
    assert result["verification"]["comparison"]["all_match"] is True
    assert result["effect_status_unchanged"] == EffectStatus.SUCCEEDED.value
    assert result["state_claim_created"] is False
    assert result["fact_authority_created"] is False
    assert result["machine_state_mutated"] is False
    assert result["effect_authority_granted"] is False
    assert set(engine.state_authority_report()["claims"]) == before_claims
    assert engine.state_authority_report()["authorities"] == before_authorities
    assert authority.authority_id in before_authorities
    after_effect = engine.store.load_effect(engine.snapshot.machine_id, effect.spec.effect_id)
    assert after_effect.status == before_effect.status == EffectStatus.SUCCEEDED.value
    assert after_effect.execution_id == before_effect.execution_id
    assert after_effect.ownership == before_effect.ownership
    assert after_effect.reconciliation == before_effect.reconciliation
    assert engine.snapshot.state == before_machine_state
    assert engine.calculus_report()["active_values"] == before_active_values
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_exact_mismatch_is_durable_evidence_not_effect_failure_or_state_rewrite():
    engine = bootstrapped_engine()
    binding, _, _, _, proposed = prepare_transition(engine)
    _, effect, _ = _execute_existing_effect(engine, proposed["transition"]["effect_id"])
    _, observation, authoritative = record_achieved_state(engine, binding, execution_id=effect.execution_id, value=24.9)
    result = engine.verify_machine_transition_postconditions(
        proposed["transition"]["transition_id"],
        achieved_state_claim_ids=(authoritative.claim_id,),
        machine_observation_ids=(observation.observation_id,),
        verifier_principal_id=VERIFIER,
    )
    assert result["verification"]["verdict"] == "MISMATCH"
    assert result["verification"]["comparison"]["all_match"] is False
    assert engine.store.load_effect(engine.snapshot.machine_id, effect.spec.effect_id).status == EffectStatus.SUCCEEDED.value
    assert engine.state_claim_report(authoritative.claim_id)["claim"]["value"] == 24.9


def test_postcondition_verification_requires_scoped_verifier_authority():
    engine = bootstrapped_engine()
    binding, _, _, _, proposed = prepare_transition(engine)
    _, effect, _ = _execute_existing_effect(engine, proposed["transition"]["effect_id"])
    _, observation, authoritative = record_achieved_state(engine, binding, execution_id=effect.execution_id, value=25.0)
    with pytest.raises(PermissionError, match="machine.postcondition.verify"):
        engine.verify_machine_transition_postconditions(
            proposed["transition"]["transition_id"],
            achieved_state_claim_ids=(authoritative.claim_id,),
            machine_observation_ids=(observation.observation_id,),
            verifier_principal_id=ROOT,
        )


def test_postcondition_verification_is_idempotent_and_sqlite_replay_safe(tmp_path: Path):
    path = tmp_path / "machine-postcondition.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    binding, _, _, _, proposed = prepare_transition(engine)
    _, effect, _ = _execute_existing_effect(engine, proposed["transition"]["effect_id"])
    _, observation, authoritative = record_achieved_state(engine, binding, execution_id=effect.execution_id, value=25.0)
    first = engine.verify_machine_transition_postconditions(
        proposed["transition"]["transition_id"],
        achieved_state_claim_ids=(authoritative.claim_id,),
        machine_observation_ids=(observation.observation_id,),
        verifier_principal_id=VERIFIER,
    )
    second = engine.verify_machine_transition_postconditions(
        proposed["transition"]["transition_id"],
        achieved_state_claim_ids=(authoritative.claim_id,),
        machine_observation_ids=(observation.observation_id,),
        verifier_principal_id=VERIFIER,
    )
    assert second["already_verified"] is True
    assert second["verification"]["verification_id"] == first["verification"]["verification_id"]
    verification_id = first["verification"]["verification_id"]
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = PostconditionEngine.resume(machine_id, reopened)
    report = resumed.machine_postcondition_verification_report(verification_id)
    assert report["verification"]["verdict"] == "VERIFIED"
    assert resumed.store.load_effect(machine_id, effect.spec.effect_id).status == EffectStatus.SUCCEEDED.value
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
