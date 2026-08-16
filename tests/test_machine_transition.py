from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine, FactAuthority, StateClaim
from aasm.effects import EffectStatus
from aasm.evidence import EvidenceRecord
from aasm.external_machine import MachineBinding, MachineStateObservation
from aasm.external_machine_runtime import EXTERNAL_MACHINE_CAPABILITIES
from aasm.external_machine_transition import MachineTransitionIntent, machine_transition_contract
from aasm.external_machine_transition_runtime import MACHINE_TRANSITION_CAPABILITIES, machine_transition_runtime_contract
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.state_authority_runtime import STATE_AUTHORITY_CAPABILITIES
from aasm.typed_protocol import CapabilityContract


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
SENSOR = "sensor-a"
OBSERVER_CAPABILITY = "machine.observe"
OPERATOR_CAPABILITY = "machine.operate"


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None, grant_transition=True):
    engine = AASMEngine(ProblemSpec("machine transition proposal"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "operator admitted workspace root identity", source="fixture.root-of-trust"),
        reason="machine transition fixture trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    _grant(engine, ROOT, "identity.register")
    engine.register_scoped_principal(
        Principal(SENSOR, "MACHINE"),
        workspace_id=WORKSPACE,
        actor_principal_id=ROOT,
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
    root_capabilities = [
        STATE_AUTHORITY_CAPABILITIES["fact_authority_register"],
        STATE_AUTHORITY_CAPABILITIES["claim_desired"],
        EXTERNAL_MACHINE_CAPABILITIES["binding_register"],
    ]
    if grant_transition:
        root_capabilities.append(MACHINE_TRANSITION_CAPABILITIES["transition_propose"])
    _grant(engine, ROOT, *root_capabilities)
    _grant(
        engine,
        SENSOR,
        STATE_AUTHORITY_CAPABILITIES["claim_observed"],
        STATE_AUTHORITY_CAPABILITIES["claim_authoritative"],
        EXTERNAL_MACHINE_CAPABILITIES["observation_record"],
    )
    return engine


def prepare_machine(engine, *, namespace="temperature.c"):
    authority = FactAuthority(
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        SENSOR,
        external_revision_id="device-rev-1",
    )
    engine.register_fact_authority(authority, actor_principal_id=ROOT)
    binding = MachineBinding(
        WORKSPACE,
        SCOPE,
        "machine-a",
        "device-a",
        (namespace,),
        OBSERVER_CAPABILITY,
        OPERATOR_CAPABILITY,
        "device-rev-1",
        fact_authority_ids=(authority.authority_id,),
    )
    engine.register_machine_binding(binding, actor_principal_id=ROOT)
    observed = StateClaim(
        "OBSERVED",
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        21.5,
        SENSOR,
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(observed, actor_principal_id=SENSOR)
    engine.record_machine_state_observation(
        MachineStateObservation(
            binding.binding_id,
            observed.claim_id,
            SENSOR,
            OBSERVER_CAPABILITY,
            "device-rev-1",
            receipt_id="sample-1",
        ),
        actor_principal_id=SENSOR,
    )
    authoritative = StateClaim(
        "AUTHORITATIVE",
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        21.5,
        SENSOR,
        external_revision_id="device-rev-1",
        source_claim_ids=(observed.claim_id,),
    )
    engine.record_state_claim(authoritative, actor_principal_id=SENSOR)
    desired = StateClaim(
        "DESIRED",
        WORKSPACE,
        SCOPE,
        "device-a",
        namespace,
        25.0,
        ROOT,
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(desired, actor_principal_id=ROOT)
    return binding, observed, authoritative, desired


def propose(engine, binding, authoritative, desired, **overrides):
    kwargs = {
        "operation": "set-temperature",
        "expected_state_claim_ids": (authoritative.claim_id,),
        "target_state_claim_ids": (desired.claim_id,),
        "external_revision_id": "device-rev-1",
        "proposer_principal_id": ROOT,
        "payload": {"target_c": 25.0},
    }
    kwargs.update(overrides)
    return engine.propose_machine_transition(binding.binding_id, **kwargs)


def test_machine_transition_contract_reuses_existing_effect_lifecycle_and_never_equates_command_with_achievement():
    semantic = machine_transition_contract()
    runtime = machine_transition_runtime_contract()
    assert semantic["expected_prestate"] == "EXACT_DURABLE_AUTHORITATIVE_STATE_CLAIMS_REQUIRED"
    assert semantic["target_state"] == "EXACT_DURABLE_DESIRED_STATE_CLAIMS_REQUIRED"
    assert semantic["effect_proposal"] == "EXISTING_AASM_PROPOSE_EFFECT_AND_EFFECT_INTENT_ONLY"
    assert semantic["effect_authorization"] == "EXISTING_AASM_AUTHORIZE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT"
    assert semantic["effect_dispatch"] == "EXISTING_AASM_EXECUTE_EFFECT_ONLY_NOT_PERFORMED_BY_THIS_CONTRACT"
    assert semantic["parallel_dispatcher"] == "NONE"
    assert semantic["parallel_effect_store"] == "NONE"
    assert semantic["command_success_is_achievement"] is False
    assert semantic["postcondition_verification"] == "NOT_IMPLEMENTED_PR2B_RESERVED_FOR_PR2C"
    assert semantic["transition_proposal_grants_effect_authority"] is False
    assert runtime["effect_proposal_path"] == "EXISTING_AASM_PROPOSE_EFFECT_ONLY"
    assert runtime["effect_ownership"] == "NOT_CREATED_BY_THIS_RUNTIME"
    assert runtime["transition_status_store"] == "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD"
    assert runtime["machine_state_mutation"] == "NONE"


def test_machine_transition_intent_is_deterministic_and_schema_valid():
    item = MachineTransitionIntent(
        WORKSPACE,
        SCOPE,
        "binding-1",
        "set-temperature",
        ("claim-pre",),
        ("claim-target",),
        "device-rev-1",
        "effect-1",
        "effect-intent-1",
        "a" * 64,
        ROOT,
    )
    copy = MachineTransitionIntent.from_dict(item.to_dict())
    assert copy == item
    assert copy.fingerprint == item.fingerprint
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "machine-transition.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(item.to_dict())


def test_transition_proposal_requires_scoped_machine_transition_authority():
    engine = bootstrapped_engine(grant_transition=False)
    binding, _, authoritative, desired = prepare_machine(engine)
    with pytest.raises(PermissionError, match="machine.transition.propose"):
        propose(engine, binding, authoritative, desired)
    assert engine.machine_transitions_report()["transitions"] == {}
    assert engine.store.load_effects(engine.snapshot.machine_id) == []


def test_transition_requires_authoritative_prestate_and_desired_target():
    engine = bootstrapped_engine()
    binding, observed, authoritative, desired = prepare_machine(engine)
    with pytest.raises(ValueError, match="AUTHORITATIVE state requires AUTHORITATIVE"):
        engine.propose_machine_transition(
            binding.binding_id,
            operation="set-temperature",
            expected_state_claim_ids=(observed.claim_id,),
            target_state_claim_ids=(desired.claim_id,),
            external_revision_id="device-rev-1",
            proposer_principal_id=ROOT,
        )
    with pytest.raises(ValueError, match="DESIRED state requires DESIRED"):
        engine.propose_machine_transition(
            binding.binding_id,
            operation="set-temperature",
            expected_state_claim_ids=(authoritative.claim_id,),
            target_state_claim_ids=(observed.claim_id,),
            external_revision_id="device-rev-1",
            proposer_principal_id=ROOT,
        )
    assert engine.store.load_effects(engine.snapshot.machine_id) == []


def test_transition_rejects_binding_revision_and_namespace_laundering_before_effect_proposal():
    engine = bootstrapped_engine()
    binding, _, authoritative, desired = prepare_machine(engine)
    with pytest.raises(ValueError, match="external revision does not match binding"):
        propose(engine, binding, authoritative, desired, external_revision_id="device-rev-2")

    unrelated = StateClaim(
        "DESIRED",
        WORKSPACE,
        SCOPE,
        "device-a",
        "humidity.relative",
        40.0,
        ROOT,
        external_revision_id="device-rev-1",
    )
    engine.record_state_claim(unrelated, actor_principal_id=ROOT)
    with pytest.raises(ValueError, match="namespace is not supported by binding"):
        engine.propose_machine_transition(
            binding.binding_id,
            operation="set-humidity",
            expected_state_claim_ids=(authoritative.claim_id,),
            target_state_claim_ids=(unrelated.claim_id,),
            external_revision_id="device-rev-1",
            proposer_principal_id=ROOT,
        )
    assert engine.store.load_effects(engine.snapshot.machine_id) == []


def test_valid_transition_creates_only_existing_proposed_effect_intent_with_exact_claim_conditions():
    engine = bootstrapped_engine()
    binding, _, authoritative, desired = prepare_machine(engine)
    before_state = engine.snapshot.state
    before_active_values = deepcopy(engine.calculus_report()["active_values"])
    result = propose(engine, binding, authoritative, desired)

    transition = result["transition"]
    effect = engine.store.load_effect(engine.snapshot.machine_id, transition["effect_id"])
    assert effect.status == EffectStatus.PROPOSED.value
    assert effect.authorization_id is None
    assert effect.dispatch_request is None
    assert effect.ownership is None
    assert effect.reconciliation is None
    assert effect.execution_id is None
    assert effect.attempts == 0
    assert effect.spec.effect_type == "machine.transition"
    assert effect.spec.payload["binding_id"] == binding.binding_id
    assert effect.spec.payload["executor_capability_id"] == OPERATOR_CAPABILITY
    assert [row["claim_id"] for row in effect.spec.preconditions] == [authoritative.claim_id]
    assert [row["claim_kind"] for row in effect.spec.preconditions] == ["AUTHORITATIVE"]
    assert [row["claim_id"] for row in effect.spec.postconditions] == [desired.claim_id]
    assert [row["claim_kind"] for row in effect.spec.postconditions] == ["DESIRED"]
    assert effect.intent["intent_id"] == transition["effect_intent_id"]
    assert effect.intent["fingerprint"] == transition["effect_intent_fingerprint"]
    assert effect.intent["metadata"]["machine_transition_contract_id"] == "aasm.machine.transition.v1"
    assert result["effect_authority_granted"] is False
    assert result["effect_authorized"] is False
    assert result["effect_dispatched"] is False
    assert result["effect_ownership_created"] is False
    assert result["postcondition_verified"] is False
    assert engine.snapshot.state == before_state
    assert engine.calculus_report()["active_values"] == before_active_values

    report = engine.machine_transition_report(transition["transition_id"])
    assert report["effect"]["effect_status"] == EffectStatus.PROPOSED.value
    assert report["effect"]["status_source"] == "EXISTING_AASM_EFFECT_RECORD"
    assert report["runtime_contract"]["transition_status_store"] == "NONE_DERIVE_FROM_EXISTING_EFFECT_RECORD"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_transition_proposal_does_not_grant_effect_authority_and_existing_authorize_effect_remains_authority_boundary():
    engine = bootstrapped_engine()
    binding, _, authoritative, desired = prepare_machine(engine)
    result = propose(engine, binding, authoritative, desired)
    effect_id = result["transition"]["effect_id"]
    with pytest.raises(PermissionError, match="effect.authorize"):
        engine.authorize_effect(
            effect_id,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=ROOT,
        )
    assert engine.store.load_effect(engine.snapshot.machine_id, effect_id).status == EffectStatus.PROPOSED.value

    _grant(engine, ROOT, "effect.authorize")
    authorized = engine.authorize_effect(
        effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=ROOT,
    )
    assert authorized.status == EffectStatus.AUTHORIZED.value
    report = engine.machine_transition_report(result["transition"]["transition_id"])
    assert report["effect"]["effect_status"] == EffectStatus.AUTHORIZED.value
    assert report["effect"]["status_source"] == "EXISTING_AASM_EFFECT_RECORD"
    assert report["effect"]["dispatch_request"] is None
    assert report["effect"]["ownership"] is None


def test_transition_proposal_is_idempotent_and_does_not_duplicate_effect_or_transition():
    engine = bootstrapped_engine()
    binding, _, authoritative, desired = prepare_machine(engine)
    first = propose(engine, binding, authoritative, desired)
    second = propose(engine, binding, authoritative, desired)
    assert second["already_proposed"] is True
    assert second["transition"]["transition_id"] == first["transition"]["transition_id"]
    assert second["transition"]["effect_id"] == first["transition"]["effect_id"]
    assert len(engine.store.load_effects(engine.snapshot.machine_id)) == 1
    assert len(engine.machine_transitions_report()["transitions"]) == 1


def test_sqlite_restart_reconstructs_machine_transition_and_existing_effect_binding(tmp_path: Path):
    path = tmp_path / "machine-transition.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    binding, _, authoritative, desired = prepare_machine(engine)
    result = propose(engine, binding, authoritative, desired)
    transition_id = result["transition"]["transition_id"]
    effect_id = result["transition"]["effect_id"]
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = AASMEngine.resume(machine_id, reopened)
    report = resumed.machine_transition_report(transition_id)
    assert report["effect"]["effect_id"] == effect_id
    assert report["effect"]["effect_status"] == EffectStatus.PROPOSED.value
    assert report["effect"]["authorization_id"] is None
    assert report["effect"]["dispatch_request"] is None
    assert report["effect"]["ownership"] is None
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
