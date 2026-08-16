from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine
from aasm.effect_capability import EffectCapability
from aasm.effect_capability_runtime import EFFECT_CAPABILITY_CAPABILITIES
from aasm.effect_capability_use import EffectCapabilityUse, effect_capability_use_contract
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.physical_authority import AuthorityDomain, AuthorityLease
from aasm.physical_authority_runtime import PHYSICAL_AUTHORITY_CAPABILITIES
from aasm.physical_control_fencing_runtime import (
    PHYSICAL_CONTROL_FENCING_CAPABILITIES,
    physical_control_fencing_runtime_contract,
)
from aasm.physical_preemption import AuthorityPreemption, authority_preemption_contract
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
HOLDER = "controller-a"
OTHER = "controller-b"
PREEMPTOR = "safety-controller"
UNLISTED = "unlisted-controller"


ControlFencingEngine = AASMEngine


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None, grant_preempt=True):
    engine = ControlFencingEngine(ProblemSpec("physical control fencing"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "control fencing fixture root", source="fixture.root-of-trust"),
        reason="control fencing trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"), Workspace(WORKSPACE, ROOT), trust_anchor_evidence_id=trust.evidence_id
    )
    _grant(engine, ROOT, "identity.register")
    for principal_id in (HOLDER, OTHER, PREEMPTOR, UNLISTED):
        engine.register_scoped_principal(
            Principal(principal_id, "SERVICE"), workspace_id=WORKSPACE, actor_principal_id=ROOT
        )
    _grant(
        engine, ROOT,
        PHYSICAL_AUTHORITY_CAPABILITIES["domain_register"],
        PHYSICAL_AUTHORITY_CAPABILITIES["lease_grant"],
        PHYSICAL_AUTHORITY_CAPABILITIES["lease_revoke"],
    )
    _grant(
        engine, HOLDER,
        EFFECT_CAPABILITY_CAPABILITIES["issue"],
        EFFECT_CAPABILITY_CAPABILITIES["delegate"],
        EFFECT_CAPABILITY_CAPABILITIES["revoke"],
    )
    if grant_preempt:
        _grant(engine, PREEMPTOR, PHYSICAL_CONTROL_FENCING_CAPABILITIES["preempt"])
        _grant(engine, UNLISTED, PHYSICAL_CONTROL_FENCING_CAPABILITIES["preempt"])
    return engine


def setup_chain(engine):
    domain = AuthorityDomain(
        WORKSPACE, SCOPE, "thermal-control", "device-a",
        ("heater.set", "heater.disable"),
        preemptor_principal_ids=(PREEMPTOR,),
        external_revision_id="device-rev-1",
    )
    engine.register_authority_domain(domain, actor_principal_id=ROOT)
    lease = AuthorityLease(
        domain.domain_id, WORKSPACE, SCOPE, HOLDER, ROOT, 1, 10.0, 100.0,
        ("heater.set", "heater.disable"), external_revision_id="device-rev-1",
    )
    engine.grant_authority_lease(lease, actor_principal_id=ROOT, at_time=10.0)
    capability = EffectCapability(
        domain.domain_id, lease.lease_id, WORKSPACE, SCOPE, "device-a", HOLDER, HOLDER,
        ("heater.set",),
        {"target": {"minimum": 20.0, "maximum": 80.0}, "rate": {"minimum": 0.0, "maximum": 5.0}},
        10.0, 90.0, 1,
        external_revision_id="device-rev-1",
        remaining_delegation_depth=1,
    )
    engine.issue_effect_capability(capability, actor_principal_id=HOLDER, at_time=10.0)
    return domain, lease, capability


def use_for(engine, lease, capability, *, actor=HOLDER, operation="heater.set", values=None, epoch=1, generation=0, cap_fp=None, lease_fp=None, at_time=20.0, scope=SCOPE, external_revision_id="device-rev-1"):
    return EffectCapabilityUse(
        capability.capability_id,
        capability.fingerprint if cap_fp is None else cap_fp,
        lease.lease_id,
        lease.fingerprint if lease_fp is None else lease_fp,
        capability.domain_id,
        WORKSPACE,
        scope,
        capability.subject_id,
        actor,
        operation,
        {"target": 50.0, "rate": 2.0} if values is None else values,
        epoch,
        generation,
        at_time,
        external_revision_id=external_revision_id,
    )


def test_control_fencing_contracts_preserve_no_effect_authority_and_pr3h_recheck():
    use_semantic = effect_capability_use_contract()
    preempt_semantic = authority_preemption_contract()
    runtime = physical_control_fencing_runtime_contract()
    assert use_semantic["role"] == "POINT_IN_TIME_STALE_COMMAND_FENCE_NOT_DURABLE_EFFECT_AUTHORIZATION"
    assert use_semantic["validation_grants_effect_authority"] is False
    assert use_semantic["validation_is_reusable_authorization_token"] is False
    assert use_semantic["required_recheck"] == "PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES"
    assert use_semantic["effect_authorization_integration"] == "NOT_YET_PR3H"
    assert preempt_semantic["identity_reference_grants_authority"] is False
    assert preempt_semantic["authorization"] == "EXISTING_SCOPED_PHYSICAL_AUTHORITY_PREEMPT_REQUIRED"
    assert preempt_semantic["effect"] == "CANONICAL_AUTHORITY_LEASE_REVOCATION_PLUS_PREEMPTION_EVIDENCE"
    assert preempt_semantic["preemption_grants_new_effect_authority"] is False
    assert runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert runtime["use_numeric_parameters"] == "EXACT_CAPABILITY_BOUND_NAME_SET_REQUIRED_FOUNDATION"
    assert runtime["preemption_effect"] == "EXISTING_AUTHORITY_LEASE_REVOCATION_REPRESENTATION"
    assert runtime["effect_authorization_integration"] == "NONE_PR3E_PR3F_PR3G_FOUNDATION"
    assert runtime["effect_dispatch"] == "NONE"
    assert runtime["parallel_authority_evaluator"] == "NONE"
    assert runtime["parallel_effect_lifecycle"] == "NONE"


def test_use_and_preemption_objects_round_trip_and_validate_schema():
    engine = bootstrapped_engine(); domain, lease, capability = setup_chain(engine)
    use = use_for(engine, lease, capability)
    assert EffectCapabilityUse.from_dict(use.to_dict()) == use
    preemption = AuthorityPreemption(
        domain.domain_id, lease.lease_id, lease.fingerprint, WORKSPACE, SCOPE,
        PREEMPTOR, HOLDER, 1, 2, 30.0, "SAFETY_ENVELOPE",
    )
    assert AuthorityPreemption.from_dict(preemption.to_dict()) == preemption
    root=Path(__file__).resolve().parents[1]
    Draft202012Validator(json.loads((root/"schemas"/"effect-capability-use.schema.json").read_text())).validate(use.to_dict())
    Draft202012Validator(json.loads((root/"schemas"/"authority-preemption.schema.json").read_text())).validate(preemption.to_dict())


def test_valid_use_fence_is_evidence_only_not_reusable_authorization():
    engine = bootstrapped_engine(); _, lease, capability = setup_chain(engine)
    use = use_for(engine, lease, capability)
    result = engine.validate_effect_capability_use(use)
    assert result["effect_authority_granted"] is False
    assert result["reusable_authorization_token"] is False
    assert result["required_recheck"] == "PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES"
    again = engine.validate_effect_capability_use(use)
    assert again["already_validated"] is True
    assert engine.effect_capability_use_report(use.use_id)["use"]["fingerprint"] == use.fingerprint


def test_use_fence_rejects_stale_identity_holder_epoch_generation_operation_bounds_scope_and_revision():
    engine = bootstrapped_engine(); _, lease, capability = setup_chain(engine)
    cases = [
        (use_for(engine, lease, capability, cap_fp="f"*64), "fingerprint"),
        (use_for(engine, lease, capability, actor=OTHER), "actor"),
        (use_for(engine, lease, capability, lease_fp="e"*64), "lease fingerprint"),
        (use_for(engine, lease, capability, epoch=2), "epoch"),
        (use_for(engine, lease, capability, generation=1), "generation"),
        (use_for(engine, lease, capability, operation="heater.disable"), "operation"),
        (use_for(engine, lease, capability, values={"target": 90.0, "rate": 2.0}), "exceed"),
        (use_for(engine, lease, capability, values={"target": 50.0}), "exactly match"),
        (use_for(engine, lease, capability, values={"target": 50.0, "rate": 2.0, "extra": 1.0}), "exactly match"),
        (use_for(engine, lease, capability, scope="other"), "scope_id"),
        (use_for(engine, lease, capability, external_revision_id="wrong"), "external_revision_id"),
    ]
    for item, expected in cases:
        with pytest.raises(PermissionError, match=expected):
            engine.validate_effect_capability_use(item)


def test_previously_valid_use_evidence_does_not_authorize_after_capability_revocation():
    engine=bootstrapped_engine(); _, lease, capability=setup_chain(engine)
    use=use_for(engine, lease, capability, at_time=20.0)
    prior=engine.validate_effect_capability_use(use)
    engine.revoke_effect_capability(capability.capability_id, actor_principal_id=HOLDER, at_time=30.0)
    assert engine.effect_capability_use_report(use.use_id)["evidence_id"] == prior["evidence_id"]
    stale=use_for(engine, lease, capability, at_time=30.0, generation=0)
    with pytest.raises(PermissionError, match="not active"):
        engine.validate_effect_capability_use(stale)


def test_preemptor_reference_without_scoped_preempt_authority_is_denied():
    engine=bootstrapped_engine(grant_preempt=False); _, lease, capability=setup_chain(engine)
    with pytest.raises(PermissionError, match="physical.authority.preempt"):
        engine.preempt_authority_lease(
            lease.lease_id,
            authority_lease_fingerprint=lease.fingerprint,
            authority_epoch=1,
            actor_principal_id=PREEMPTOR,
            at_time=30.0,
            reason_code="SAFETY_ENVELOPE",
        )
    assert engine.authority_lease_report(lease.lease_id, at_time=30.0)["active_at_time"] is True
    assert engine.effect_capability_report(capability.capability_id, at_time=30.0)["active_at_time"] is True


def test_scoped_preempt_authority_without_domain_preemptor_identity_is_denied():
    engine=bootstrapped_engine(); _, lease, _=setup_chain(engine)
    with pytest.raises(PermissionError, match="not listed"):
        engine.preempt_authority_lease(
            lease.lease_id,
            authority_lease_fingerprint=lease.fingerprint,
            authority_epoch=1,
            actor_principal_id=UNLISTED,
            at_time=30.0,
            reason_code="UNLISTED",
        )


def test_preemption_rejects_stale_lease_fingerprint_and_epoch():
    engine=bootstrapped_engine(); _, lease, _=setup_chain(engine)
    with pytest.raises(PermissionError, match="fingerprint"):
        engine.preempt_authority_lease(
            lease.lease_id, authority_lease_fingerprint="a"*64, authority_epoch=1,
            actor_principal_id=PREEMPTOR, at_time=30.0, reason_code="SAFETY_ENVELOPE",
        )
    with pytest.raises(PermissionError, match="epoch"):
        engine.preempt_authority_lease(
            lease.lease_id, authority_lease_fingerprint=lease.fingerprint, authority_epoch=2,
            actor_principal_id=PREEMPTOR, at_time=30.0, reason_code="SAFETY_ENVELOPE",
        )


def test_semantic_preemption_uses_canonical_lease_revocation_invalidates_capability_and_allows_next_epoch():
    engine=bootstrapped_engine(); domain, lease, capability=setup_chain(engine)
    result=engine.preempt_authority_lease(
        lease.lease_id,
        authority_lease_fingerprint=lease.fingerprint,
        authority_epoch=1,
        actor_principal_id=PREEMPTOR,
        at_time=30.0,
        reason_code="SAFETY_ENVELOPE",
    )
    assert result["effect_authority_granted"] is False
    assert result["required_next_epoch"] == 2
    assert engine.authority_lease_report(lease.lease_id, at_time=29.0)["active_at_time"] is True
    assert engine.authority_lease_report(lease.lease_id, at_time=30.0)["active_at_time"] is False
    assert engine.effect_capability_report(capability.capability_id, at_time=30.0)["active_at_time"] is False
    rev=engine.physical_authority_report(at_time=30.0)["revocations"][lease.lease_id]["revocation"]
    assert rev["reason"] == "PREEMPTION:SAFETY_ENVELOPE"
    second=AuthorityLease(
        domain.domain_id, WORKSPACE, SCOPE, OTHER, ROOT, 2, 30.0, 60.0,
        ("heater.set",), external_revision_id="device-rev-1",
    )
    engine.grant_authority_lease(second, actor_principal_id=ROOT, at_time=30.0)
    assert engine.authority_lease_report(second.lease_id, at_time=30.0)["active_at_time"] is True
    assert result["preemption"]["required_next_epoch"] == second.epoch


def test_preemption_is_idempotent_but_non_identical_second_preemption_fails():
    engine=bootstrapped_engine(); _, lease, _=setup_chain(engine)
    first=engine.preempt_authority_lease(
        lease.lease_id, authority_lease_fingerprint=lease.fingerprint, authority_epoch=1,
        actor_principal_id=PREEMPTOR, at_time=30.0, reason_code="SAFETY_ENVELOPE",
    )
    again=engine.preempt_authority_lease(
        lease.lease_id, authority_lease_fingerprint=lease.fingerprint, authority_epoch=1,
        actor_principal_id=PREEMPTOR, at_time=30.0, reason_code="SAFETY_ENVELOPE",
    )
    assert again["already_preempted"] is True
    assert again["preemption"]["preemption_id"] == first["preemption"]["preemption_id"]
    with pytest.raises(ValueError, match="non-identical preemption"):
        engine.preempt_authority_lease(
            lease.lease_id, authority_lease_fingerprint=lease.fingerprint, authority_epoch=1,
            actor_principal_id=PREEMPTOR, at_time=31.0, reason_code="DIFFERENT",
        )


def test_control_fencing_records_do_not_mutate_core_machine_state_or_grant_effect_authority():
    engine=bootstrapped_engine(); _, lease, capability=setup_chain(engine)
    before_state=engine.snapshot.state; before_values=deepcopy(engine.calculus_report()["active_values"])
    result=engine.validate_effect_capability_use(use_for(engine, lease, capability))
    assert result["effect_authority_granted"] is False
    engine.preempt_authority_lease(
        lease.lease_id, authority_lease_fingerprint=lease.fingerprint, authority_epoch=1,
        actor_principal_id=PREEMPTOR, at_time=30.0, reason_code="SAFETY_ENVELOPE",
    )
    assert engine.snapshot.state == before_state
    assert engine.calculus_report()["active_values"] == before_values


def test_sqlite_restart_reconstructs_use_and_preemption_and_exact_replay(tmp_path: Path):
    path=tmp_path/"control-fencing.db"; store=SQLiteStore(str(path)); engine=bootstrapped_engine(store=store)
    machine_id=engine.snapshot.machine_id; _, lease, capability=setup_chain(engine)
    use=use_for(engine, lease, capability); validated=engine.validate_effect_capability_use(use)
    preempted=engine.preempt_authority_lease(
        lease.lease_id, authority_lease_fingerprint=lease.fingerprint, authority_epoch=1,
        actor_principal_id=PREEMPTOR, at_time=30.0, reason_code="SAFETY_ENVELOPE",
    )
    before_hash=engine.snapshot.canonical_hash(); store.close()
    reopened=SQLiteStore(str(path)); resumed=ControlFencingEngine.resume(machine_id,reopened)
    assert resumed.effect_capability_use_report(use.use_id)["evidence_id"] == validated["evidence_id"]
    assert resumed.authority_preemption_report(preempted["preemption"]["preemption_id"])["preemption"]["required_next_epoch"] == 2
    assert resumed.authority_lease_report(lease.lease_id,at_time=30.0)["active_at_time"] is False
    assert resumed.effect_capability_report(capability.capability_id,at_time=30.0)["active_at_time"] is False
    assert resumed.snapshot.canonical_hash()==before_hash
    assert resumed.replay().canonical_hash()==resumed.snapshot.canonical_hash()
    reopened.close()
