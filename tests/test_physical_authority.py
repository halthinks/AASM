from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine
from aasm.effects import EffectSpec
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.physical_authority import AuthorityDomain, AuthorityLease, physical_authority_contract
from aasm.physical_authority_runtime import (
    PHYSICAL_AUTHORITY_CAPABILITIES,
    PhysicalAuthorityRuntimeMixin,
    physical_authority_runtime_contract,
)
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
HOLDER = "controller-a"
OTHER = "controller-b"
PREEMPTOR = "safety-controller"


class PhysicalAuthorityEngine(PhysicalAuthorityRuntimeMixin, AASMEngine):
    pass


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None):
    engine = PhysicalAuthorityEngine(ProblemSpec("physical authority foundation"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "physical authority fixture root", source="fixture.root-of-trust"),
        reason="physical authority trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    _grant(engine, ROOT, "identity.register")
    for principal_id in (HOLDER, OTHER, PREEMPTOR):
        engine.register_scoped_principal(
            Principal(principal_id, "SERVICE"),
            workspace_id=WORKSPACE,
            actor_principal_id=ROOT,
        )
    _grant(
        engine,
        ROOT,
        PHYSICAL_AUTHORITY_CAPABILITIES["domain_register"],
        PHYSICAL_AUTHORITY_CAPABILITIES["lease_grant"],
        PHYSICAL_AUTHORITY_CAPABILITIES["lease_revoke"],
    )
    return engine


def domain(*, effect_classes=("heater.set", "heater.disable"), preemptors=(PREEMPTOR,)):
    return AuthorityDomain(
        WORKSPACE,
        SCOPE,
        "thermal-control",
        "device-a",
        tuple(effect_classes),
        tuple(preemptors),
        external_revision_id="device-rev-1",
    )


def lease(domain_id: str, *, epoch=1, holder=HOLDER, valid_from=10.0, expires_at=20.0, effect_classes=("heater.set",)):
    return AuthorityLease(
        domain_id,
        WORKSPACE,
        SCOPE,
        holder,
        ROOT,
        epoch,
        valid_from,
        expires_at,
        tuple(effect_classes),
        external_revision_id="device-rev-1",
    )


def test_physical_authority_contract_has_no_parallel_authority_or_effect_grant():
    semantic = physical_authority_contract()
    runtime = physical_authority_runtime_contract()
    assert semantic["domain_role"] == "BOUNDED_EFFECT_AUTHORITY_NAMESPACE_NOT_AUTHORITY_GRANT"
    assert semantic["lease_role"] == "EXCLUSIVE_TIME_BOUNDED_DOMAIN_HOLDER_NOT_EFFECT_PERMISSION_BY_EXISTENCE"
    assert semantic["lease_exclusivity"] == "AT_MOST_ONE_ACTIVE_LEASE_PER_DOMAIN"
    assert semantic["authority_epoch"] == "STRICTLY_MONOTONIC_PER_DOMAIN"
    assert semantic["domain_existence_grants_effect_authority"] is False
    assert semantic["lease_existence_grants_effect_authority"] is False
    assert semantic["parallel_authority_evaluator"] == "NONE"
    assert semantic["parallel_effect_lifecycle"] == "NONE"
    assert semantic["effect_authorization_integration"] == "NOT_YET_PR3H"
    assert runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert runtime["lease_exclusivity"] == "NON_OVERLAPPING_EFFECTIVE_INTERVALS_PER_DOMAIN"
    assert runtime["effect_authorization_integration"] == "NONE_PR3A_PR3B_FOUNDATION"
    assert runtime["effect_dispatch"] == "NONE"
    assert runtime["machine_state_mutation"] == "NONE"


def test_authority_domain_and_lease_round_trip_and_schema_validation():
    item = domain()
    item_copy = AuthorityDomain.from_dict(item.to_dict())
    assert item_copy == item
    assert item_copy.fingerprint == item.fingerprint
    lease_item = lease(item.domain_id)
    lease_copy = AuthorityLease.from_dict(lease_item.to_dict())
    assert lease_copy == lease_item
    assert lease_copy.active_at(10.0) is True
    assert lease_copy.active_at(20.0) is False
    root = Path(__file__).resolve().parents[1]
    Draft202012Validator(json.loads((root / "schemas" / "authority-domain.schema.json").read_text())).validate(item.to_dict())
    Draft202012Validator(json.loads((root / "schemas" / "authority-lease.schema.json").read_text())).validate(lease_item.to_dict())


def test_domain_registration_requires_existing_scoped_authority_and_known_preemptors():
    engine = bootstrapped_engine()
    item = domain()
    with pytest.raises(PermissionError, match="physical.authority.domain.register"):
        engine.register_authority_domain(item, actor_principal_id=HOLDER)
    bad = domain(preemptors=("missing-preemptor",))
    with pytest.raises(KeyError, match="unknown authority-domain preemptor"):
        engine.register_authority_domain(bad, actor_principal_id=ROOT)
    result = engine.register_authority_domain(item, actor_principal_id=ROOT)
    assert result["effect_authority_granted"] is False
    again = engine.register_authority_domain(item, actor_principal_id=ROOT)
    assert again["already_registered"] is True


def test_lease_grant_requires_exact_domain_scope_revision_holder_and_non_amplifying_effect_classes():
    engine = bootstrapped_engine()
    item = domain()
    engine.register_authority_domain(item, actor_principal_id=ROOT)
    with pytest.raises(PermissionError, match="actor must equal issuer_principal_id"):
        engine.grant_authority_lease(
            AuthorityLease(item.domain_id, WORKSPACE, SCOPE, HOLDER, ROOT, 1, 10.0, 20.0, ("heater.set",), external_revision_id="device-rev-1"),
            actor_principal_id=OTHER,
            at_time=10.0,
        )
    with pytest.raises(ValueError, match="subset of domain"):
        engine.grant_authority_lease(
            lease(item.domain_id, effect_classes=("heater.destroy",)),
            actor_principal_id=ROOT,
            at_time=10.0,
        )
    with pytest.raises(ValueError, match="external revision must match domain"):
        engine.grant_authority_lease(
            AuthorityLease(item.domain_id, WORKSPACE, SCOPE, HOLDER, ROOT, 1, 10.0, 20.0, ("heater.set",), external_revision_id="wrong-rev"),
            actor_principal_id=ROOT,
            at_time=10.0,
        )
    with pytest.raises(KeyError, match="unknown authority-lease holder"):
        engine.grant_authority_lease(
            AuthorityLease(item.domain_id, WORKSPACE, SCOPE, "missing-holder", ROOT, 1, 10.0, 20.0, ("heater.set",), external_revision_id="device-rev-1"),
            actor_principal_id=ROOT,
            at_time=10.0,
        )


def test_authority_lease_epoch_is_strictly_monotonic_and_intervals_cannot_overlap():
    engine = bootstrapped_engine()
    item = domain()
    engine.register_authority_domain(item, actor_principal_id=ROOT)
    first = lease(item.domain_id, epoch=1, valid_from=10.0, expires_at=20.0)
    engine.grant_authority_lease(first, actor_principal_id=ROOT, at_time=10.0)
    with pytest.raises(ValueError, match="next monotonic domain epoch"):
        engine.grant_authority_lease(
            lease(item.domain_id, epoch=1, valid_from=20.0, expires_at=30.0),
            actor_principal_id=ROOT,
            at_time=20.0,
        )
    with pytest.raises(ValueError, match="overlaps existing domain lease"):
        engine.grant_authority_lease(
            lease(item.domain_id, epoch=2, holder=OTHER, valid_from=19.0, expires_at=30.0),
            actor_principal_id=ROOT,
            at_time=19.0,
        )
    second = lease(item.domain_id, epoch=2, holder=OTHER, valid_from=20.0, expires_at=30.0)
    granted = engine.grant_authority_lease(second, actor_principal_id=ROOT, at_time=20.0)
    assert granted["lease"]["epoch"] == 2
    assert granted["effect_authority_granted"] is False


def test_revocation_is_append_only_closes_effective_interval_and_next_epoch_can_begin():
    engine = bootstrapped_engine()
    item = domain()
    engine.register_authority_domain(item, actor_principal_id=ROOT)
    first = lease(item.domain_id, epoch=1, valid_from=10.0, expires_at=30.0)
    engine.grant_authority_lease(first, actor_principal_id=ROOT, at_time=10.0)
    revoked = engine.revoke_authority_lease(first.lease_id, actor_principal_id=ROOT, at_time=15.0)
    assert revoked["revocation"]["revocation_generation"] == 1
    assert revoked["effect_history_rewritten"] is False
    assert engine.authority_lease_report(first.lease_id, at_time=14.0)["active_at_time"] is True
    assert engine.authority_lease_report(first.lease_id, at_time=15.0)["active_at_time"] is False
    again = engine.revoke_authority_lease(first.lease_id, actor_principal_id=ROOT, at_time=16.0)
    assert again["already_revoked"] is True
    second = lease(item.domain_id, epoch=2, holder=OTHER, valid_from=15.0, expires_at=25.0)
    engine.grant_authority_lease(second, actor_principal_id=ROOT, at_time=15.0)
    assert engine.authority_lease_report(second.lease_id, at_time=15.0)["active_at_time"] is True


def test_authority_domain_or_lease_never_grants_existing_effect_authority():
    engine = bootstrapped_engine()
    item = domain()
    engine.register_authority_domain(item, actor_principal_id=ROOT)
    lease_item = lease(item.domain_id, epoch=1, valid_from=10.0, expires_at=20.0)
    engine.grant_authority_lease(lease_item, actor_principal_id=ROOT, at_time=10.0)
    effect = engine.propose_effect(
        EffectSpec("heater.set", idempotency_key="lease-does-not-authorize"),
        workspace_id=WORKSPACE,
        scope_id=SCOPE,
        proposer_principal_id=HOLDER,
    )
    with pytest.raises(PermissionError, match="effect.authorize"):
        engine.authorize_effect(
            effect.spec.effect_id,
            workspace_id=WORKSPACE,
            scope_id=SCOPE,
            actor_principal_id=HOLDER,
        )
    assert engine.authority_lease_report(lease_item.lease_id, at_time=10.0)["effect_authority_granted"] is False


def test_physical_authority_records_do_not_mutate_core_machine_state():
    engine = bootstrapped_engine()
    before_state = engine.snapshot.state
    before_active_values = deepcopy(engine.calculus_report()["active_values"])
    item = domain()
    engine.register_authority_domain(item, actor_principal_id=ROOT)
    engine.grant_authority_lease(lease(item.domain_id), actor_principal_id=ROOT, at_time=10.0)
    assert engine.snapshot.state == before_state
    assert engine.calculus_report()["active_values"] == before_active_values


def test_sqlite_restart_reconstructs_domains_leases_revocations_and_exact_replay(tmp_path: Path):
    path = tmp_path / "physical-authority.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    item = domain()
    engine.register_authority_domain(item, actor_principal_id=ROOT)
    lease_item = lease(item.domain_id, valid_from=10.0, expires_at=30.0)
    engine.grant_authority_lease(lease_item, actor_principal_id=ROOT, at_time=10.0)
    engine.revoke_authority_lease(lease_item.lease_id, actor_principal_id=ROOT, at_time=15.0)
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = PhysicalAuthorityEngine.resume(machine_id, reopened)
    report = resumed.physical_authority_report(at_time=16.0)
    assert item.domain_id in report["domains"]
    assert lease_item.lease_id in report["leases"]
    assert report["leases"][lease_item.lease_id]["active_at_time"] is False
    assert report["revocations"][lease_item.lease_id]["revocation"]["revocation_generation"] == 1
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
