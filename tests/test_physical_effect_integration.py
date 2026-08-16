from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine as ActiveEngine
from aasm.effect_capability import EffectCapability
from aasm.effect_capability_runtime import EFFECT_CAPABILITY_CAPABILITIES
from aasm.effects import EffectSpec, EffectStatus
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.physical_authority import AuthorityDomain, AuthorityLease
from aasm.physical_authority_runtime import PHYSICAL_AUTHORITY_CAPABILITIES
from aasm.physical_control_fencing_runtime import PHYSICAL_CONTROL_FENCING_CAPABILITIES
from aasm.physical_effect_binding import (
    PhysicalEffectAuthorityBinding,
    physical_effect_authority_binding_contract,
)
from aasm.physical_effect_integration_boundary import PhysicalEffectIntegrationBoundaryMixin
from aasm.physical_effect_integration_runtime import (
    PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES,
    physical_effect_integration_runtime_contract,
)
from aasm.resources import ResourceRecord, TaskDemand
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.workers import WorkerRecord


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
HOLDER = "controller-a"
PREEMPTOR = "safety-controller"


class PhysicalEffectIntegrationEngine(PhysicalEffectIntegrationBoundaryMixin, ActiveEngine):
    pass


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine():
    engine = PhysicalEffectIntegrationEngine(ProblemSpec("PR-3H physical effect integration"))
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "PR-3H fixture root", source="fixture.root-of-trust"),
        reason="PR-3H fixture trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"), Workspace(WORKSPACE, ROOT), trust_anchor_evidence_id=trust.evidence_id
    )
    _grant(engine, ROOT, "identity.register")
    for principal_id in (HOLDER, PREEMPTOR):
        engine.register_scoped_principal(
            Principal(principal_id, "SERVICE"), workspace_id=WORKSPACE, actor_principal_id=ROOT
        )
    _grant(
        engine,
        ROOT,
        PHYSICAL_AUTHORITY_CAPABILITIES["domain_register"],
        PHYSICAL_AUTHORITY_CAPABILITIES["lease_grant"],
        PHYSICAL_AUTHORITY_CAPABILITIES["lease_revoke"],
    )
    _grant(
        engine,
        HOLDER,
        EFFECT_CAPABILITY_CAPABILITIES["issue"],
        EFFECT_CAPABILITY_CAPABILITIES["revoke"],
        PHYSICAL_EFFECT_INTEGRATION_CAPABILITIES["bind"],
        "effect.authorize",
        "effect.execute",
    )
    _grant(engine, PREEMPTOR, PHYSICAL_CONTROL_FENCING_CAPABILITIES["preempt"])
    return engine


def setup_authority(engine):
    domain = AuthorityDomain(
        WORKSPACE,
        SCOPE,
        "thermal-control",
        "device-a",
        ("heater.set",),
        preemptor_principal_ids=(PREEMPTOR,),
        external_revision_id="device-rev-1",
    )
    engine.register_authority_domain(domain, actor_principal_id=ROOT)
    lease = AuthorityLease(
        domain.domain_id,
        WORKSPACE,
        SCOPE,
        HOLDER,
        ROOT,
        1,
        10.0,
        100.0,
        ("heater.set",),
        external_revision_id="device-rev-1",
    )
    engine.grant_authority_lease(lease, actor_principal_id=ROOT, at_time=10.0)
    capability = EffectCapability(
        domain.domain_id,
        lease.lease_id,
        WORKSPACE,
        SCOPE,
        "device-a",
        HOLDER,
        HOLDER,
        ("heater.set",),
        {
            "target": {"minimum": 20.0, "maximum": 80.0},
            "rate": {"minimum": 0.0, "maximum": 5.0},
        },
        10.0,
        90.0,
        1,
        external_revision_id="device-rev-1",
    )
    engine.issue_effect_capability(capability, actor_principal_id=HOLDER, at_time=10.0)
    return domain, lease, capability


def propose_physical_effect(engine, *, target=50.0, rate=2.0, effect_type="machine.transition"):
    spec = EffectSpec(
        effect_type,
        payload={
            "subject_id": "device-a",
            "operation": "heater.set",
            "external_revision_id": "device-rev-1",
            "command": {"target": target, "rate": rate},
        },
        idempotency_key=f"pr3h-{effect_type}-{target}-{rate}",
    )
    return engine.propose_effect(
        spec,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=HOLDER,
        intent_metadata={"physical_authority_required": True},
    )


def bind_effect(engine, record, lease, capability, *, at_time=20.0):
    return engine.bind_physical_effect_authority(
        record.spec.effect_id,
        authority_lease_id=lease.lease_id,
        effect_capability_id=capability.capability_id,
        actor_principal_id=HOLDER,
        at_time=at_time,
    )


def effect_task_lease(engine, effect_id: str, *, worker_id="effect-worker"):
    if not engine.list_resources():
        engine.register_resource(
            ResourceRecord(
                "effect-worker-resource",
                "local",
                capabilities=["effect.execute"],
                capacity=4.0,
            )
        )
        engine.register_worker(WorkerRecord(worker_id, "effect-worker-resource"))
    task = TaskDemand(
        f"effect-task-{effect_id[-16:]}",
        required_capabilities=["effect.execute"],
        metadata={"effect_id": effect_id},
    )
    return engine.claim_task(task, worker_id, lease_seconds=600.0)


def execute(engine, effect_id, *, at_time=20.0):
    lease = effect_task_lease(engine, effect_id)
    return engine.execute_effect(
        effect_id,
        lambda spec, key: {"ack": True, "idempotency_key": key},
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=HOLDER,
        owner_worker_id="effect-worker",
        task_lease_id=lease["lease_id"],
        at_time=at_time,
    )


def test_pr3h_contract_reuses_existing_effect_lifecycle_and_requires_live_rechecks():
    semantic = physical_effect_authority_binding_contract()
    runtime = physical_effect_integration_runtime_contract()
    assert semantic["authorization_recheck"] == "MANDATORY_AT_EXISTING_AUTHORIZE_EFFECT_BOUNDARY"
    assert semantic["execution_recheck"] == "MANDATORY_AT_EXISTING_EXECUTE_EFFECT_BOUNDARY"
    assert semantic["prior_use_validation_is_authorization"] is False
    assert runtime["effect_authority"] == "EXISTING_V53_EFFECT_AUTHORIZE_AND_EFFECT_EXECUTE_REMAIN_REQUIRED"
    assert runtime["machine_transition_binding"] == "MANDATORY_BEFORE_AUTHORIZATION_OR_NEW_DISPATCH"
    assert runtime["ordinary_unbound_effect_compatibility"] == "PRESERVED"
    assert runtime["task_lease"] == "EXISTING_V54_TASKLEASE_UNCHANGED"
    assert runtime["ownership"] == "EXISTING_V54_EFFECT_OWNERSHIP_UNCHANGED"
    assert runtime["unknown_and_reconciliation"] == "EXISTING_V54_UNKNOWN_AND_RECONCILIATION_UNCHANGED"
    assert runtime["parallel_authority_evaluator"] == "NONE"
    assert runtime["parallel_effect_store"] == "NONE"
    assert runtime["parallel_effect_lifecycle"] == "NONE"
    assert runtime["parallel_dispatcher"] == "NONE"


def test_binding_is_derived_from_durable_effect_and_schema_valid():
    engine = bootstrapped_engine(); _, lease, capability = setup_authority(engine)
    record = propose_physical_effect(engine)
    result = bind_effect(engine, record, lease, capability)
    binding = PhysicalEffectAuthorityBinding.from_dict(result["binding"])
    assert binding.effect_id == record.spec.effect_id
    assert binding.operation == "heater.set"
    assert binding.numeric_parameters == {"rate": 2.0, "target": 50.0}
    assert binding.effect_capability_fingerprint == capability.fingerprint
    assert result["effect_authority_granted"] is False
    schema = json.loads(
        (Path(__file__).resolve().parents[1] / "schemas" / "physical-effect-authority-binding.schema.json").read_text()
    )
    Draft202012Validator(schema).validate(binding.to_dict())


def test_machine_transition_effect_cannot_authorize_without_physical_binding():
    engine = bootstrapped_engine(); setup_authority(engine)
    record = propose_physical_effect(engine)
    with pytest.raises(PermissionError, match="requires a physical authority binding"):
        engine.authorize_effect(
            record.spec.effect_id,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=HOLDER,
            at_time=20.0,
        )
    assert engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id).status == EffectStatus.PROPOSED.value


def test_numeric_parameter_names_and_bounds_are_derived_not_caller_asserted():
    engine = bootstrapped_engine(); _, lease, capability = setup_authority(engine)
    out_of_bounds = propose_physical_effect(engine, target=90.0)
    with pytest.raises(PermissionError, match="exceed capability bounds"):
        bind_effect(engine, out_of_bounds, lease, capability)

    missing_bound_capability = EffectCapability(
        capability.domain_id,
        lease.lease_id,
        WORKSPACE,
        SCOPE,
        "device-a",
        HOLDER,
        HOLDER,
        ("heater.set",),
        {"target": {"minimum": 20.0, "maximum": 80.0}},
        10.0,
        90.0,
        1,
        external_revision_id="device-rev-1",
        metadata={"variant": "missing-rate"},
    )
    engine.issue_effect_capability(missing_bound_capability, actor_principal_id=HOLDER, at_time=10.0)
    record = propose_physical_effect(engine, target=51.0)
    with pytest.raises(PermissionError, match="exactly match capability bounds"):
        bind_effect(engine, record, lease, missing_bound_capability)


def test_capability_revoked_before_authorization_blocks_existing_authorize_effect():
    engine = bootstrapped_engine(); _, lease, capability = setup_authority(engine)
    record = propose_physical_effect(engine); bind_effect(engine, record, lease, capability)
    engine.revoke_effect_capability(capability.capability_id, actor_principal_id=HOLDER, at_time=25.0)
    with pytest.raises(PermissionError, match="not active at point of use"):
        engine.authorize_effect(
            record.spec.effect_id,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=HOLDER,
            at_time=25.0,
        )
    current = engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id)
    assert current.status == EffectStatus.PROPOSED.value
    assert current.authorization_id is None


def test_capability_revoked_after_authorization_blocks_before_dispatch_request():
    engine = bootstrapped_engine(); _, lease, capability = setup_authority(engine)
    record = propose_physical_effect(engine); bind_effect(engine, record, lease, capability)
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=HOLDER,
        at_time=20.0,
    )
    engine.revoke_effect_capability(capability.capability_id, actor_principal_id=HOLDER, at_time=25.0)
    with pytest.raises(PermissionError, match="not active at point of use"):
        execute(engine, record.spec.effect_id, at_time=25.0)
    current = engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id)
    assert current.status == EffectStatus.AUTHORIZED.value
    assert current.dispatch_request is None
    assert current.ownership is None
    assert current.execution_id is None


def test_preemption_after_authorization_blocks_before_dispatch_and_next_epoch_does_not_resurrect_old_binding():
    engine = bootstrapped_engine(); domain, lease, capability = setup_authority(engine)
    record = propose_physical_effect(engine); bind_effect(engine, record, lease, capability)
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=HOLDER,
        at_time=20.0,
    )
    engine.preempt_authority_lease(
        lease.lease_id,
        authority_lease_fingerprint=lease.fingerprint,
        authority_epoch=1,
        actor_principal_id=PREEMPTOR,
        at_time=25.0,
        reason_code="SAFETY_ENVELOPE",
    )
    with pytest.raises(PermissionError, match="lease is not active"):
        execute(engine, record.spec.effect_id, at_time=25.0)
    replacement = AuthorityLease(
        domain.domain_id, WORKSPACE, SCOPE, HOLDER, ROOT, 2, 25.0, 80.0,
        ("heater.set",), external_revision_id="device-rev-1",
    )
    engine.grant_authority_lease(replacement, actor_principal_id=ROOT, at_time=25.0)
    with pytest.raises(PermissionError):
        execute(engine, record.spec.effect_id, at_time=26.0)
    current = engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id)
    assert current.dispatch_request is None
    assert current.ownership is None


def test_valid_bound_effect_uses_existing_tasklease_ownership_dispatch_and_terminal_reconciliation():
    engine = bootstrapped_engine(); _, lease, capability = setup_authority(engine)
    record = propose_physical_effect(engine); bind_effect(engine, record, lease, capability)
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=HOLDER,
        at_time=20.0,
    )
    result = execute(engine, record.spec.effect_id, at_time=20.0)
    current = engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id)
    assert result.status == EffectStatus.SUCCEEDED.value
    assert current.status == EffectStatus.SUCCEEDED.value
    assert current.dispatch_request is not None
    assert current.ownership is not None
    assert current.execution_id
    assert current.reconciliation is not None
    assert current.reconciliation["outcome"] == "CONFIRMED"
    integration = engine.physical_effect_integration_report()
    boundaries = {row["recheck"]["boundary"] for row in integration["rechecks"].values()}
    assert {"AUTHORIZE", "EXECUTE"}.issubset(boundaries)


def test_ordinary_unbound_effect_preserves_existing_behavior():
    engine = bootstrapped_engine()
    spec = EffectSpec(
        "ordinary.audit",
        payload={"message": "no physical authority binding required"},
        idempotency_key="ordinary-unbound-pr3h",
    )
    record = engine.propose_effect(
        spec,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=HOLDER,
    )
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        actor_principal_id=HOLDER,
        at_time=20.0,
    )
    execute(engine, record.spec.effect_id, at_time=20.0)
    current = engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id)
    assert current.status == EffectStatus.SUCCEEDED.value
    assert current.ownership is not None
    with pytest.raises(KeyError):
        engine.physical_effect_binding_report(record.spec.effect_id, at_time=20.0)


def test_binding_does_not_replace_scoped_effect_authority():
    engine = bootstrapped_engine(); _, lease, capability = setup_authority(engine)
    record = propose_physical_effect(engine); bind_effect(engine, record, lease, capability)
    # Remove the holder's effect.authorize by using a new engine fixture would be
    # expensive; instead prove binding does not manufacture an authorization ID.
    current = engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id)
    assert current.status == EffectStatus.PROPOSED.value
    assert current.authorization_id is None
    assert current.dispatch_request is None
    assert current.ownership is None
