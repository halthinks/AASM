from __future__ import annotations

import pytest

from aasm import AASMEngine
from aasm.effect_capability import EffectCapability
from aasm.effect_capability_runtime import EFFECT_CAPABILITY_CAPABILITIES
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.physical_authority import AuthorityDomain, AuthorityLease
from aasm.physical_authority_runtime import PHYSICAL_AUTHORITY_CAPABILITIES
from aasm.physical_control_fencing_runtime import PHYSICAL_CONTROL_FENCING_CAPABILITIES
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace


WORKSPACE="workspace-a"; SCOPE="root"; ROOT="root"; HOLDER="controller-a"; PREEMPTOR="safety-controller"
RecoveryEngine = AASMEngine


def grant(engine,subject,*caps):
    return engine.admit_scoped_authority_grant(ScopedAuthorityGrant(subject,ROOT,WORKSPACE,SCOPE,tuple(caps)))


def boot():
    engine=RecoveryEngine(ProblemSpec("preemption crash recovery"))
    trust=engine.add_evidence(EvidenceRecord("trust_anchor","preemption recovery root",source="fixture.root"),reason="fixture")
    engine.bootstrap_scoped_workspace(Principal(ROOT,"SYSTEM"),Workspace(WORKSPACE,ROOT),trust_anchor_evidence_id=trust.evidence_id)
    grant(engine,ROOT,"identity.register")
    for principal_id in (HOLDER,PREEMPTOR):
        engine.register_scoped_principal(Principal(principal_id,"SERVICE"),workspace_id=WORKSPACE,actor_principal_id=ROOT)
    grant(engine,ROOT,PHYSICAL_AUTHORITY_CAPABILITIES["domain_register"],PHYSICAL_AUTHORITY_CAPABILITIES["lease_grant"],PHYSICAL_AUTHORITY_CAPABILITIES["lease_revoke"])
    grant(engine,HOLDER,EFFECT_CAPABILITY_CAPABILITIES["issue"],EFFECT_CAPABILITY_CAPABILITIES["revoke"])
    grant(engine,PREEMPTOR,PHYSICAL_CONTROL_FENCING_CAPABILITIES["preempt"])
    domain=AuthorityDomain(WORKSPACE,SCOPE,"thermal-control","device-a",("heater.set",),preemptor_principal_ids=(PREEMPTOR,),external_revision_id="device-rev-1")
    engine.register_authority_domain(domain,actor_principal_id=ROOT)
    lease=AuthorityLease(domain.domain_id,WORKSPACE,SCOPE,HOLDER,ROOT,1,10.0,100.0,("heater.set",),external_revision_id="device-rev-1")
    engine.grant_authority_lease(lease,actor_principal_id=ROOT,at_time=10.0)
    capability=EffectCapability(domain.domain_id,lease.lease_id,WORKSPACE,SCOPE,"device-a",HOLDER,HOLDER,("heater.set",),{"target":{"minimum":0.0,"maximum":100.0}},10.0,90.0,1,external_revision_id="device-rev-1")
    engine.issue_effect_capability(capability,actor_principal_id=HOLDER,at_time=10.0)
    return engine,lease,capability


def test_retry_repairs_canonical_lease_revocation_after_crash_between_preemption_records(monkeypatch):
    engine,lease,capability=boot()
    original=engine._record_physical_authority_document

    def crash_before_lease_revocation(**kwargs):
        raise RuntimeError("simulated crash after durable preemption Evidence")

    monkeypatch.setattr(engine,"_record_physical_authority_document",crash_before_lease_revocation)
    with pytest.raises(RuntimeError,match="simulated crash"):
        engine.preempt_authority_lease(
            lease.lease_id,
            authority_lease_fingerprint=lease.fingerprint,
            authority_epoch=1,
            actor_principal_id=PREEMPTOR,
            at_time=30.0,
            reason_code="SAFETY_ENVELOPE",
        )

    control=engine.physical_control_fencing_report()
    assert len(control["preemptions"])==1
    assert engine.physical_authority_report(at_time=30.0)["revocations"]=={}
    assert engine.authority_lease_report(lease.lease_id,at_time=30.0)["active_at_time"] is True
    assert engine.effect_capability_report(capability.capability_id,at_time=30.0)["active_at_time"] is True

    monkeypatch.setattr(engine,"_record_physical_authority_document",original)
    repaired=engine.preempt_authority_lease(
        lease.lease_id,
        authority_lease_fingerprint=lease.fingerprint,
        authority_epoch=1,
        actor_principal_id=PREEMPTOR,
        at_time=30.0,
        reason_code="SAFETY_ENVELOPE",
    )
    assert repaired["already_preempted"] is True
    assert repaired["lease_revocation_repaired"] is True
    assert repaired["lease_revocation_evidence_id"]
    assert engine.authority_lease_report(lease.lease_id,at_time=30.0)["active_at_time"] is False
    assert engine.effect_capability_report(capability.capability_id,at_time=30.0)["active_at_time"] is False
    assert engine.replay().canonical_hash()==engine.snapshot.canonical_hash()
