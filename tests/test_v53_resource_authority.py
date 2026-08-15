from threading import Event, Thread

import pytest

from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence import MemoryStore
from aasm.persistence.sqlite import SQLiteStore
from aasm.resource_governance import CapacityWindowKind, ResourceCapacity, ResourceDemandEstimate
from aasm.resource_routing import ResourceAwareCandidate, ResourceRoutingPolicy
from aasm.runtime_v53 import AASMEngine, RESOURCE_AUTHORITY_CAPABILITIES
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace


def engine_with_workspace_and_root(*capabilities, store=None):
    engine = AASMEngine(ProblemSpec("v0.53 resource authority"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement="fixture root", source="fixture"),
        reason="fixture root recorded",
    )
    engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace("workspace-a", "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    if capabilities:
        engine.admit_scoped_authority_grant(
            ScopedAuthorityGrant(
                "root",
                "root",
                "workspace-a",
                "root",
                tuple(capabilities),
                delegable=True,
                remaining_delegation_depth=4,
            )
        )
    return engine


def capacity():
    return ResourceCapacity(
        resource_id="expert-weekly",
        resource_class="EXPERT_MODEL_ALLOWANCE",
        unit="credits",
        owner_principal_id="root",
        workspace_id="workspace-a",
        scope_id="root",
        provider="fixture",
        window_kind=CapacityWindowKind.FIXED,
        total=100.0,
        protected_reserve=20.0,
    )


def candidate(amount=10.0):
    return ResourceAwareCandidate(
        "expert",
        correctness=.95,
        evidence_quality=.95,
        expected_progress=.9,
        provider_quota_burn=amount,
        scarce_expert_usage=amount,
        demands=(
            ResourceDemandEstimate(
                "EXPERT_MODEL_ALLOWANCE",
                amount,
                "credits",
                resource_id="expert-weekly",
                upper_bound=amount,
            ),
        ),
    )


def test_v53_resource_capacity_registration_requires_actor_workspace_and_scope_authority():
    engine = engine_with_workspace_and_root(RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"])
    with pytest.raises(PermissionError, match="actor_principal_id"):
        engine.register_resource_capacity(capacity())
    assert engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")["capacities"] == {}

    result = engine.register_resource_capacity(capacity(), actor_principal_id="root")
    assert result["capacity"]["resource_id"] == "expert-weekly"
    assert result["authority_decision_evidence_id"]
    assert result["authority_binding_evidence_id"]
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_denied_reservation_is_durable_authority_evidence_but_never_resource_commitment():
    engine = engine_with_workspace_and_root(RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"])
    engine.register_resource_capacity(capacity(), actor_principal_id="root")
    before_resource = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")
    before_authority = engine.scoped_authority_report(workspace_id="workspace-a")

    with pytest.raises(PermissionError, match="resource.reserve"):
        engine.select_and_reserve_resource_candidate(
            [candidate()],
            ResourceRoutingPolicy(),
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )

    after_resource = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")
    after_authority = engine.scoped_authority_report(workspace_id="workspace-a")
    assert after_resource["reservations"] == before_resource["reservations"] == {}
    assert len(after_authority["decisions"]) == len(before_authority["decisions"]) + 1
    assert any(
        row["decision"]["reason"] == "NO_APPLICABLE_GRANT"
        for row in after_authority["decisions"].values()
    )


def test_authorized_reservation_transaction_derives_from_authority_decision():
    engine = engine_with_workspace_and_root(
        RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],
        RESOURCE_AUTHORITY_CAPABILITIES["reserve"],
    )
    engine.register_resource_capacity(capacity(), actor_principal_id="root")
    result = engine.select_and_reserve_resource_candidate(
        [candidate()],
        ResourceRoutingPolicy(),
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    authority_evidence_id = result["authority_decision_evidence_id"]
    transaction_evidence_id = result["evidence_id"]
    transaction_evidence = next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == transaction_evidence_id
    )
    assert authority_evidence_id in transaction_evidence["derived_from"]
    reservation = result["transaction"]["reservation"]
    assert reservation["status"] == "ACTIVE"
    assert reservation["total_reserved"] == 10.0
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_resource_principal_history_is_derived_from_exact_authority_evidence():
    engine = engine_with_workspace_and_root(
        RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],
        RESOURCE_AUTHORITY_CAPABILITIES["reserve"],
        RESOURCE_AUTHORITY_CAPABILITIES["settle"],
    )
    registered = engine.register_resource_capacity(capacity(), actor_principal_id="root")
    reserved = engine.select_and_reserve_resource_candidate(
        [candidate()],
        ResourceRoutingPolicy(),
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    reservation_id = reserved["transaction"]["reservation"]["reservation_id"]
    settled = engine.settle_resource_reservation(
        reservation_id,
        {"expert-weekly": 7.0},
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )

    report = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")
    assert report["contract"]["principal_history"] == "DERIVED_FROM_SCOPED_AUTHORITY_EVIDENCE"
    assert report["contract"]["concurrent_commit_guard"] == "V53_OPTIMISTIC_MACHINE_VERSION_FAIL_CLOSED"
    history = report["principal_history"]

    capacity_row = next(
        row for row in history
        if row["record_type"] == "capacity" and row["evidence_id"] == registered["evidence_id"]
    )
    assert capacity_row["actor_principal_id"] == "root"
    assert capacity_row["authority_action"] == "capacity_register"
    assert capacity_row["authority_decision_evidence_id"] == registered["authority_decision_evidence_id"]

    routing_row = next(row for row in history if row["record_type"] == "routing_transaction")
    assert routing_row["actor_principal_id"] == "root"
    assert routing_row["authority_action"] == RESOURCE_AUTHORITY_CAPABILITIES["reserve"]
    assert routing_row["authority_decision_evidence_id"] == reserved["authority_decision_evidence_id"]

    settlement_row = next(row for row in history if row["record_type"] == "settlement_transaction")
    assert settlement_row["actor_principal_id"] == "root"
    assert settlement_row["authority_action"] == RESOURCE_AUTHORITY_CAPABILITIES["settle"]
    assert settlement_row["authority_decision_evidence_id"] == settled["authority_decision_evidence_id"]


def test_two_hosts_cannot_commit_reservations_from_same_stale_resource_snapshot():
    store = MemoryStore()
    seed = engine_with_workspace_and_root(
        RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],
        RESOURCE_AUTHORITY_CAPABILITIES["reserve"],
        store=store,
    )
    seed.register_resource_capacity(capacity(), actor_principal_id="root")
    machine_id = seed.snapshot.machine_id

    host_a = AASMEngine.resume(machine_id, store)
    host_b = AASMEngine.resume(machine_id, store)
    reached_commit = Event()
    release_commit = Event()
    outcome = {}
    original_record = host_b._record_resource_document

    def blocked_record(*, record_type, **kwargs):
        if record_type == "routing_transaction":
            reached_commit.set()
            if not release_commit.wait(10):
                raise TimeoutError("stale reservation test was not released")
        return original_record(record_type=record_type, **kwargs)

    host_b._record_resource_document = blocked_record

    def run_stale_host():
        try:
            outcome["result"] = host_b.select_and_reserve_resource_candidate(
                [candidate(50)],
                ResourceRoutingPolicy(),
                workspace_id="workspace-a",
                scope_id="root",
                actor_principal_id="root",
            )
        except Exception as exc:
            outcome["error"] = exc

    thread = Thread(target=run_stale_host, daemon=True)
    thread.start()
    try:
        assert reached_commit.wait(10), "host B never reached the guarded resource commit"
        first = host_a.select_and_reserve_resource_candidate(
            [candidate(50)],
            ResourceRoutingPolicy(),
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
        assert first["transaction"]["reservation"]["total_reserved"] == 50.0
    finally:
        release_commit.set()
        thread.join(10)

    assert not thread.is_alive()
    assert "result" not in outcome
    assert isinstance(outcome.get("error"), ValueError)
    assert "Stale machine version" in str(outcome["error"])

    canonical = store.load_snapshot(machine_id)
    assert host_b.snapshot.canonical_hash() == canonical.canonical_hash()
    report = host_b.resource_governance_report(workspace_id="workspace-a", scope_id="root")
    assert len(report["reservations"]) == 1
    reservation = next(iter(report["reservations"].values()))
    assert reservation["total_reserved"] == 50.0
    assert report["capacities"]["expert-weekly"]["committed"] == 50.0
    assert host_b.replay().canonical_hash() == canonical.canonical_hash()


def test_sqlite_two_connections_reject_same_stale_resource_commit(tmp_path):
    database = tmp_path / "v53-resource-cas.db"
    seed_store = SQLiteStore(database)
    seed = engine_with_workspace_and_root(
        RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],
        RESOURCE_AUTHORITY_CAPABILITIES["reserve"],
        store=seed_store,
    )
    seed.register_resource_capacity(capacity(), actor_principal_id="root")
    machine_id = seed.snapshot.machine_id
    seed_store.close()

    store_a = SQLiteStore(database)
    store_b = SQLiteStore(database)
    host_a = AASMEngine.resume(machine_id, store_a)
    host_b = AASMEngine.resume(machine_id, store_b)
    reached_commit = Event()
    release_commit = Event()
    outcome = {}
    original_record = host_b._record_resource_document

    def blocked_record(*, record_type, **kwargs):
        if record_type == "routing_transaction":
            reached_commit.set()
            if not release_commit.wait(10):
                raise TimeoutError("SQLite stale reservation test was not released")
        return original_record(record_type=record_type, **kwargs)

    host_b._record_resource_document = blocked_record

    def run_stale_host():
        try:
            outcome["result"] = host_b.select_and_reserve_resource_candidate(
                [candidate(50)],
                ResourceRoutingPolicy(),
                workspace_id="workspace-a",
                scope_id="root",
                actor_principal_id="root",
            )
        except Exception as exc:
            outcome["error"] = exc

    thread = Thread(target=run_stale_host, daemon=True)
    thread.start()
    try:
        assert reached_commit.wait(10), "SQLite host B never reached guarded resource commit"
        first = host_a.select_and_reserve_resource_candidate(
            [candidate(50)],
            ResourceRoutingPolicy(),
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
        assert first["transaction"]["reservation"]["total_reserved"] == 50.0
    finally:
        release_commit.set()
        thread.join(10)

    try:
        assert not thread.is_alive()
        assert "result" not in outcome
        assert isinstance(outcome.get("error"), ValueError)
        assert "Stale machine version" in str(outcome["error"])
        canonical = store_a.load_snapshot(machine_id)
        assert host_b.snapshot.canonical_hash() == canonical.canonical_hash()
        report = host_b.resource_governance_report(workspace_id="workspace-a", scope_id="root")
        assert len(report["reservations"]) == 1
        assert report["capacities"]["expert-weekly"]["committed"] == 50.0
        assert host_b.replay().canonical_hash() == canonical.canonical_hash()
    finally:
        store_a.close()
        store_b.close()


def test_settlement_has_independent_capability_and_preserves_reservation_when_denied():
    engine = engine_with_workspace_and_root(
        RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"],
        RESOURCE_AUTHORITY_CAPABILITIES["reserve"],
    )
    engine.register_resource_capacity(capacity(), actor_principal_id="root")
    reserved = engine.select_and_reserve_resource_candidate(
        [candidate()],
        ResourceRoutingPolicy(),
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    reservation_id = reserved["transaction"]["reservation"]["reservation_id"]
    with pytest.raises(PermissionError, match="resource.settle"):
        engine.settle_resource_reservation(
            reservation_id,
            {"expert-weekly": 7.0},
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
    report = engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")
    assert report["reservations"][reservation_id]["status"] == "ACTIVE"
    assert report["settlements"] == {}

    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "root",
            "root",
            "workspace-a",
            "root",
            (RESOURCE_AUTHORITY_CAPABILITIES["settle"],),
        )
    )
    settled = engine.settle_resource_reservation(
        reservation_id,
        {"expert-weekly": 7.0},
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    settlement_evidence = next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == settled["evidence_id"]
    )
    assert settled["authority_decision_evidence_id"] in settlement_evidence["derived_from"]
    assert engine.resource_governance_report(workspace_id="workspace-a", scope_id="root")["reservations"][reservation_id]["status"] == "SETTLED"


def test_v53_rejects_unscoped_resource_capacity_instead_of_falling_back_to_v52_bypass():
    engine = engine_with_workspace_and_root(RESOURCE_AUTHORITY_CAPABILITIES["capacity_register"])
    unscoped = ResourceCapacity(
        "legacy-global",
        "CPU_SECONDS",
        "seconds",
        window_kind=CapacityWindowKind.FIXED,
        total=10,
    )
    with pytest.raises(PermissionError, match="workspace_id, and scope_id"):
        engine.register_resource_capacity(unscoped, actor_principal_id="root")
