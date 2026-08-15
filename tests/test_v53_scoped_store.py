import pytest

from aasm.effects import EffectSpec
from aasm.engine import AASMEngine as BaseEngine
from aasm.evidence import EvidenceRecord
from aasm.model import ProblemSpec
from aasm.persistence import MemoryStore
from aasm.runtime_v53 import AASMEngine
from aasm.scoped_authority import Principal, ScopedAuthorityGrant, Workspace
from aasm.scoped_store import STORE_CAPABILITIES, ScopedStoreAccess, ScopedStoreView, scoped_store_contract


def machine(store, workspace_id, *capabilities):
    engine = AASMEngine(ProblemSpec(f"scoped store {workspace_id}"), store=store)
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement=f"{workspace_id} trust", source="fixture"),
        reason="fixture scoped store trust anchor",
    )
    engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace(workspace_id, "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    if capabilities:
        engine.admit_scoped_authority_grant(
            ScopedAuthorityGrant(
                "root",
                "root",
                workspace_id,
                "root",
                tuple(capabilities),
                delegable=True,
                remaining_delegation_depth=4,
            )
        )
    return engine


def test_scoped_store_contract_forbids_direct_writes_and_ambiguous_raw_access():
    contract = scoped_store_contract()
    assert contract["contract_id"] == "aasm.store.scoped.v1"
    assert contract["raw_snapshot_access"] == "ROOT_SCOPE_SINGLE_WORKSPACE_ONLY"
    assert contract["multi_workspace_raw_access"] == "FAIL_CLOSED_USE_SCOPED_PROJECTIONS"
    assert contract["legacy_unscoped_effect_access"] == "FAIL_CLOSED"
    assert contract["direct_store_write"] == "FORBIDDEN_USE_GOVERNED_RUNTIME_TRANSITIONS"


def test_raw_machine_reads_fail_closed_across_workspaces():
    store = MemoryStore()
    a = machine(
        store,
        "workspace-a",
        STORE_CAPABILITIES["snapshot_read"],
        STORE_CAPABILITIES["events_read"],
        STORE_CAPABILITIES["checkpoint_read"],
    )
    b = machine(
        store,
        "workspace-b",
        STORE_CAPABILITIES["snapshot_read"],
        STORE_CAPABILITIES["events_read"],
        STORE_CAPABILITIES["checkpoint_read"],
    )
    checkpoint = a.checkpoint("workspace-a checkpoint")
    view = ScopedStoreView(store, ScopedStoreAccess("root", "workspace-a", "root"))

    assert view.load_snapshot(a.snapshot.machine_id).machine_id == a.snapshot.machine_id
    assert view.load_events(a.snapshot.machine_id)
    assert view.load_checkpoint(a.snapshot.machine_id, checkpoint.checkpoint_id).checkpoint_id == checkpoint.checkpoint_id

    with pytest.raises(PermissionError, match="does not own this machine"):
        view.load_snapshot(b.snapshot.machine_id)
    with pytest.raises(PermissionError, match="does not own this machine"):
        view.load_events(b.snapshot.machine_id)


def test_raw_store_access_requires_root_scope_even_when_principal_has_root_grant():
    store = MemoryStore()
    engine = machine(store, "workspace-a", STORE_CAPABILITIES["snapshot_read"])
    view = ScopedStoreView(store, ScopedStoreAccess("root", "workspace-a", "child-scope"))
    with pytest.raises(PermissionError, match="raw store access requires root scope"):
        view.load_snapshot(engine.snapshot.machine_id)


def test_multi_workspace_machine_cannot_be_returned_as_raw_snapshot():
    store = MemoryStore()
    engine = machine(store, "workspace-a", STORE_CAPABILITIES["snapshot_read"])
    trust = engine.add_evidence(
        EvidenceRecord(kind="trust_anchor", statement="second workspace trust", source="fixture"),
        reason="second workspace trust",
    )
    engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace("workspace-b", "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    view = ScopedStoreView(store, ScopedStoreAccess("root", "workspace-a", "root"))
    with pytest.raises(PermissionError, match="multi-workspace machines"):
        view.load_snapshot(engine.snapshot.machine_id)


def test_unfinished_machine_listing_does_not_leak_other_workspace_machine_ids():
    store = MemoryStore()
    a = machine(store, "workspace-a", STORE_CAPABILITIES["unfinished_list"])
    b = machine(store, "workspace-b", STORE_CAPABILITIES["unfinished_list"])
    view = ScopedStoreView(store, ScopedStoreAccess("root", "workspace-a", "root"))
    assert view.list_unfinished() == [a.snapshot.machine_id]
    assert b.snapshot.machine_id not in view.list_unfinished()


def test_effect_reads_require_v53_binding_and_scoped_read_authority():
    store = MemoryStore()
    engine = machine(store, "workspace-a", STORE_CAPABILITIES["effects_read"])
    scoped = engine.propose_effect(
        EffectSpec("external-write", idempotency_key="scoped-effect"),
        workspace_id="workspace-a",
        scope_id="root",
        proposer_principal_id="root",
    )
    legacy = BaseEngine.propose_effect(
        engine,
        EffectSpec("legacy-write", idempotency_key="legacy-unscoped-effect"),
    )
    view = ScopedStoreView(store, ScopedStoreAccess("root", "workspace-a", "root"))

    rows = view.list_effects(engine.snapshot.machine_id)
    assert [row.spec.effect_id for row in rows] == [scoped.spec.effect_id]
    assert view.load_effect(engine.snapshot.machine_id, scoped.spec.effect_id).spec.effect_id == scoped.spec.effect_id
    assert view.find_effect_by_idempotency(engine.snapshot.machine_id, "scoped-effect").spec.effect_id == scoped.spec.effect_id
    assert view.find_effect_by_idempotency(engine.snapshot.machine_id, "legacy-unscoped-effect") is None
    with pytest.raises(PermissionError, match="outside scoped store access"):
        view.load_effect(engine.snapshot.machine_id, legacy.spec.effect_id)


def test_scoped_store_view_exposes_no_direct_append_or_mutation_surface():
    store = MemoryStore()
    machine(store, "workspace-a", STORE_CAPABILITIES["snapshot_read"])
    view = ScopedStoreView(store, ScopedStoreAccess("root", "workspace-a", "root"))
    assert not hasattr(view, "append")
    assert not hasattr(view, "save_effect")
    assert not hasattr(view, "initialize_run")
