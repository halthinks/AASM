from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from aasm import AASMEngine
from aasm.effect_capability import EffectCapability, NumericInterval, effect_capability_contract
from aasm.effect_capability_revocation_guard import EffectCapabilityRevocationGuardMixin
from aasm.effect_capability_runtime import (
    EFFECT_CAPABILITY_CAPABILITIES,
    EffectCapabilityRuntimeMixin,
    effect_capability_runtime_contract,
)
from aasm.effects import EffectSpec
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence.sqlite import SQLiteStore
from aasm.physical_authority import AuthorityDomain, AuthorityLease
from aasm.physical_authority_runtime import PHYSICAL_AUTHORITY_CAPABILITIES
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace


WORKSPACE = "workspace-a"
SCOPE = "root"
ROOT = "root"
HOLDER = "controller-a"
CHILD = "controller-b"
OTHER = "controller-c"


class EffectCapabilityEngine(
    EffectCapabilityRevocationGuardMixin,
    EffectCapabilityRuntimeMixin,
    AASMEngine,
):
    pass


def _grant(engine, subject: str, *capabilities: str):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(subject, ROOT, WORKSPACE, SCOPE, tuple(capabilities))
    )


def bootstrapped_engine(*, store=None):
    engine = EffectCapabilityEngine(ProblemSpec("bounded effect capabilities"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord("trust_anchor", "effect capability fixture root", source="fixture.root-of-trust"),
        reason="effect capability trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal(ROOT, "SYSTEM"),
        Workspace(WORKSPACE, ROOT),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    _grant(engine, ROOT, "identity.register")
    for principal_id in (HOLDER, CHILD, OTHER):
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
    _grant(
        engine,
        HOLDER,
        EFFECT_CAPABILITY_CAPABILITIES["issue"],
        EFFECT_CAPABILITY_CAPABILITIES["delegate"],
        EFFECT_CAPABILITY_CAPABILITIES["revoke"],
    )
    _grant(engine, CHILD, EFFECT_CAPABILITY_CAPABILITIES["delegate"], EFFECT_CAPABILITY_CAPABILITIES["revoke"])
    return engine


def setup_authority(engine):
    domain = AuthorityDomain(
        WORKSPACE,
        SCOPE,
        "thermal-control",
        "device-a",
        ("heater.set", "heater.disable"),
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
        ("heater.set", "heater.disable"),
        external_revision_id="device-rev-1",
    )
    engine.grant_authority_lease(lease, actor_principal_id=ROOT, at_time=10.0)
    return domain, lease


def root_capability(domain, lease, *, holder=HOLDER, operations=("heater.set", "heater.disable"), bounds=None, valid_from=10.0, expires_at=90.0, depth=2, epoch=1):
    return EffectCapability(
        domain.domain_id,
        lease.lease_id,
        WORKSPACE,
        SCOPE,
        "device-a",
        holder,
        HOLDER,
        tuple(operations),
        bounds or {"target": {"minimum": 0.0, "maximum": 100.0}, "rate": {"minimum": 0.0, "maximum": 10.0}},
        valid_from,
        expires_at,
        epoch,
        external_revision_id="device-rev-1",
        remaining_delegation_depth=depth,
    )


def child_capability(parent, *, holder=CHILD, operations=("heater.set",), bounds=None, valid_from=20.0, expires_at=80.0, depth=1, parent_generation=0, epoch=None, scope=SCOPE, external_revision_id="device-rev-1"):
    return EffectCapability(
        parent.domain_id,
        parent.authority_lease_id,
        WORKSPACE,
        scope,
        parent.subject_id,
        holder,
        parent.holder_principal_id,
        tuple(operations),
        bounds or {"target": {"minimum": 20.0, "maximum": 80.0}, "rate": {"minimum": 0.0, "maximum": 5.0}},
        valid_from,
        expires_at,
        parent.authority_epoch if epoch is None else epoch,
        external_revision_id=external_revision_id,
        remaining_delegation_depth=depth,
        parent_capability_id=parent.capability_id,
        parent_capability_fingerprint=parent.fingerprint,
        parent_revocation_generation=parent_generation,
    )


def test_effect_capability_contract_reserves_effect_integration_and_units():
    semantic = effect_capability_contract()
    runtime = effect_capability_runtime_contract()
    assert semantic["authority_source"] == "EXISTING_ACTIVE_AUTHORITY_LEASE_REQUIRED"
    assert semantic["operation_bound"] == "CAPABILITY_OPERATIONS_SUBSET_OF_LEASE_OR_PARENT"
    assert semantic["numeric_bound"] == "NAMED_CLOSED_NUMERIC_INTERVALS_ONLY"
    assert semantic["numeric_units"] == "NOT_INTERPRETED_UNTIL_QUANTITY_CONTRACT"
    assert semantic["delegation"] == "CHILD_RIGHTS_MUST_BE_SUBSET_AND_DEPTH_MUST_DECREASE"
    assert semantic["capability_existence_grants_effect_authority"] is False
    assert semantic["effect_authorization_integration"] == "NOT_YET_PR3H"
    assert semantic["semantic_preemption"] == "RESERVED_PR3G"
    assert runtime["authority"] == "EXISTING_AASM_SCOPED_AUTHORITY_ONLY"
    assert runtime["effect_authorization_integration"] == "NONE_PR3C_PR3D_FOUNDATION"
    assert runtime["effect_dispatch"] == "NONE"
    assert runtime["parallel_authority_evaluator"] == "NONE"
    assert runtime["parallel_effect_lifecycle"] == "NONE"


def test_effect_capability_round_trip_schema_and_numeric_interval_semantics():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    item = root_capability(domain, lease)
    copy = EffectCapability.from_dict(item.to_dict())
    assert copy == item
    assert copy.fingerprint == item.fingerprint
    assert copy.allows_operation("heater.set") is True
    assert copy.allows_operation("heater.destroy") is False
    assert copy.bounds_allow({"target": 25.0, "rate": 3.0}) is True
    assert copy.bounds_allow({"target": 125.0, "rate": 3.0}) is False
    assert NumericInterval(0.0, 100.0).contains_interval(NumericInterval(20.0, 80.0)) is True
    schema = json.loads((Path(__file__).resolve().parents[1] / "schemas" / "effect-capability.schema.json").read_text())
    Draft202012Validator(schema).validate(item.to_dict())


def test_root_capability_requires_active_lease_holder_scope_epoch_revision_and_non_amplifying_operations():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    with pytest.raises(PermissionError, match="issuer must equal active authority-lease holder"):
        engine.issue_effect_capability(
            EffectCapability(
                domain.domain_id, lease.lease_id, WORKSPACE, SCOPE, "device-a", CHILD, CHILD,
                ("heater.set",), {}, 10.0, 20.0, 1, external_revision_id="device-rev-1"
            ),
            actor_principal_id=CHILD,
            at_time=10.0,
        )
    with pytest.raises(ValueError, match="subset of authority lease effect classes"):
        engine.issue_effect_capability(
            root_capability(domain, lease, operations=("heater.destroy",)),
            actor_principal_id=HOLDER,
            at_time=10.0,
        )
    with pytest.raises(ValueError, match="authority_epoch"):
        engine.issue_effect_capability(
            root_capability(domain, lease, epoch=2),
            actor_principal_id=HOLDER,
            at_time=10.0,
        )
    with pytest.raises(ValueError, match="validity must be contained"):
        engine.issue_effect_capability(
            root_capability(domain, lease, valid_from=5.0),
            actor_principal_id=HOLDER,
            at_time=10.0,
        )
    wrong_revision = EffectCapability(
        domain.domain_id, lease.lease_id, WORKSPACE, SCOPE, "device-a", HOLDER, HOLDER,
        ("heater.set",), {}, 10.0, 20.0, 1, external_revision_id="wrong-rev"
    )
    with pytest.raises(ValueError, match="external revision"):
        engine.issue_effect_capability(wrong_revision, actor_principal_id=HOLDER, at_time=10.0)


def test_root_issue_requires_scoped_issue_authority_and_known_holder():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    with pytest.raises(PermissionError, match="physical.effect-capability.issue"):
        engine.issue_effect_capability(
            EffectCapability(
                domain.domain_id, lease.lease_id, WORKSPACE, SCOPE, "device-a", OTHER, HOLDER,
                ("heater.set",), {}, 10.0, 20.0, 1, external_revision_id="device-rev-1"
            ),
            actor_principal_id=OTHER,
            at_time=10.0,
        )
    missing_holder = EffectCapability(
        domain.domain_id, lease.lease_id, WORKSPACE, SCOPE, "device-a", "missing-holder", HOLDER,
        ("heater.set",), {}, 10.0, 20.0, 1, external_revision_id="device-rev-1"
    )
    with pytest.raises(KeyError, match="unknown effect-capability holder"):
        engine.issue_effect_capability(missing_holder, actor_principal_id=HOLDER, at_time=10.0)


def test_delegation_rejects_operation_bound_validity_scope_revision_epoch_and_depth_amplification():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    parent = root_capability(domain, lease)
    engine.issue_effect_capability(parent, actor_principal_id=HOLDER, at_time=10.0)

    bad_cases = [
        (child_capability(parent, operations=("heater.set", "heater.destroy")), "operations must be a subset"),
        (child_capability(parent, bounds={"target": {"minimum": -1.0, "maximum": 80.0}, "rate": {"minimum": 0.0, "maximum": 5.0}}), "numeric bounds"),
        (child_capability(parent, bounds={"rate": {"minimum": 0.0, "maximum": 5.0}}), "numeric bounds"),
        (child_capability(parent, valid_from=5.0), "validity must be contained"),
        (child_capability(parent, expires_at=95.0), "validity must be contained"),
        (child_capability(parent, depth=2), "decrease remaining delegation depth"),
        (child_capability(parent, epoch=2), "authority_epoch"),
        (child_capability(parent, scope="other-scope"), "scope_id"),
        (child_capability(parent, external_revision_id="wrong-rev"), "external_revision_id"),
    ]
    for child, expected in bad_cases:
        with pytest.raises((ValueError, PermissionError), match=expected):
            engine.delegate_effect_capability(child, actor_principal_id=HOLDER, at_time=20.0)

    valid = child_capability(parent)
    result = engine.delegate_effect_capability(valid, actor_principal_id=HOLDER, at_time=20.0)
    assert result["effect_authority_granted"] is False
    assert result["capability"]["remaining_delegation_depth"] == 1


def test_delegation_requires_active_parent_holder_and_scoped_delegate_authority():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    parent = root_capability(domain, lease)
    engine.issue_effect_capability(parent, actor_principal_id=HOLDER, at_time=10.0)
    child = child_capability(parent)
    with pytest.raises(PermissionError, match="issuer must be active parent holder and actor"):
        engine.delegate_effect_capability(child, actor_principal_id=OTHER, at_time=20.0)
    zero_depth_parent = root_capability(domain, lease, operations=("heater.set",), depth=0, bounds={"target": {"minimum": 0.0, "maximum": 100.0}}, valid_from=10.0, expires_at=85.0)
    engine.issue_effect_capability(zero_depth_parent, actor_principal_id=HOLDER, at_time=10.0)
    with pytest.raises(PermissionError, match="no remaining delegation depth"):
        engine.delegate_effect_capability(
            child_capability(zero_depth_parent, depth=0, bounds={"target": {"minimum": 10.0, "maximum": 90.0}}, expires_at=80.0),
            actor_principal_id=HOLDER,
            at_time=20.0,
        )


def test_parent_revocation_generation_fences_descendants_at_revocation_time_not_before():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    parent = root_capability(domain, lease)
    engine.issue_effect_capability(parent, actor_principal_id=HOLDER, at_time=10.0)
    child = child_capability(parent)
    engine.delegate_effect_capability(child, actor_principal_id=HOLDER, at_time=20.0)
    assert engine.effect_capability_report(child.capability_id, at_time=29.0)["active_at_time"] is True
    engine.revoke_effect_capability(parent.capability_id, actor_principal_id=HOLDER, at_time=30.0)
    parent_before = engine.effect_capability_report(parent.capability_id, at_time=29.0)
    child_before = engine.effect_capability_report(child.capability_id, at_time=29.0)
    assert parent_before["effective_revocation_generation"] == 0
    assert child_before["active_at_time"] is True
    parent_after = engine.effect_capability_report(parent.capability_id, at_time=30.0)
    child_after = engine.effect_capability_report(child.capability_id, at_time=30.0)
    assert parent_after["effective_revocation_generation"] == 1
    assert parent_after["active_at_time"] is False
    assert child_after["active_at_time"] is False
    assert child_after["parent_effective_revocation_generation"] == 1


def test_authority_lease_revocation_invalidates_capability_without_rewriting_capability_history():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    capability = root_capability(domain, lease)
    issued = engine.issue_effect_capability(capability, actor_principal_id=HOLDER, at_time=10.0)
    before = deepcopy(issued["capability"])
    assert engine.effect_capability_report(capability.capability_id, at_time=39.0)["active_at_time"] is True
    engine.revoke_authority_lease(lease.lease_id, actor_principal_id=ROOT, at_time=40.0)
    report = engine.effect_capability_report(capability.capability_id, at_time=40.0)
    assert report["active_at_time"] is False
    assert report["lease_active_at_time"] is False
    assert report["capability"] == before


def test_effect_capability_existence_still_does_not_grant_existing_effect_authority():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    capability = root_capability(domain, lease)
    engine.issue_effect_capability(capability, actor_principal_id=HOLDER, at_time=10.0)
    effect = engine.propose_effect(
        EffectSpec("heater.set", idempotency_key="capability-not-authorize"),
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
    assert engine.effect_capability_report(capability.capability_id, at_time=20.0)["effect_authority_granted"] is False


def test_effect_capability_records_do_not_mutate_core_machine_state():
    engine = bootstrapped_engine()
    domain, lease = setup_authority(engine)
    before_state = engine.snapshot.state
    before_values = deepcopy(engine.calculus_report()["active_values"])
    capability = root_capability(domain, lease)
    engine.issue_effect_capability(capability, actor_principal_id=HOLDER, at_time=10.0)
    engine.revoke_effect_capability(capability.capability_id, actor_principal_id=HOLDER, at_time=30.0)
    assert engine.snapshot.state == before_state
    assert engine.calculus_report()["active_values"] == before_values


def test_sqlite_restart_reconstructs_capability_tree_revocation_and_exact_replay(tmp_path: Path):
    path = tmp_path / "effect-capability.db"
    store = SQLiteStore(str(path))
    engine = bootstrapped_engine(store=store)
    machine_id = engine.snapshot.machine_id
    domain, lease = setup_authority(engine)
    parent = root_capability(domain, lease)
    engine.issue_effect_capability(parent, actor_principal_id=HOLDER, at_time=10.0)
    child = child_capability(parent)
    engine.delegate_effect_capability(child, actor_principal_id=HOLDER, at_time=20.0)
    engine.revoke_effect_capability(parent.capability_id, actor_principal_id=HOLDER, at_time=30.0)
    before_hash = engine.snapshot.canonical_hash()
    store.close()

    reopened = SQLiteStore(str(path))
    resumed = EffectCapabilityEngine.resume(machine_id, reopened)
    report = resumed.effect_capabilities_report(at_time=31.0)
    assert parent.capability_id in report["capabilities"]
    assert child.capability_id in report["capabilities"]
    assert report["capabilities"][parent.capability_id]["active_at_time"] is False
    assert report["capabilities"][child.capability_id]["active_at_time"] is False
    assert resumed.snapshot.canonical_hash() == before_hash
    assert resumed.replay().canonical_hash() == resumed.snapshot.canonical_hash()
    reopened.close()
