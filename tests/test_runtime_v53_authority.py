import pytest

from aasm.evidence import EvidenceRecord
from aasm.effects import EffectSpec, EffectStatus, RetryPolicy
from aasm.model import ProblemSpec
from aasm.runtime_v53 import AASMEngine, EFFECT_AUTHORITY_CAPABILITIES
from aasm.scoped_authority import (
    AuthorityRequest,
    Principal,
    ScopedAuthorityGrant,
    Workspace,
)


def bootstrapped_engine():
    engine = AASMEngine(ProblemSpec("v0.53 durable authority"))
    trust = engine.add_evidence(
        EvidenceRecord(
            kind="trust_anchor",
            statement="operator admitted workspace root identity",
            source="fixture.root-of-trust",
        ),
        reason="fixture trust anchor recorded",
    )
    boot = engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace("workspace-a", "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    return engine, trust, boot


def grant_root_identity_registration(engine):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "root",
            "root",
            "workspace-a",
            "root",
            ("identity.register",),
            delegable=True,
            remaining_delegation_depth=4,
        )
    )


def grant_root_effect_capabilities(engine, *capabilities, expires_at=None):
    return engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "root",
            "root",
            "workspace-a",
            "root",
            tuple(capabilities),
            expires_at=expires_at,
        )
    )


def test_workspace_bootstrap_requires_existing_explicit_trust_anchor_evidence():
    engine = AASMEngine(ProblemSpec("trust anchor required"))
    with pytest.raises(KeyError, match="trust anchor"):
        engine.bootstrap_scoped_workspace(
            Principal("root", "SYSTEM"),
            Workspace("workspace-a", "root"),
            trust_anchor_evidence_id="missing-evidence",
        )
    assert engine.scoped_authority_report(workspace_id="workspace-a")["workspace"] is None


def test_bootstrap_is_atomic_and_replayable_but_root_has_no_implicit_operational_authority():
    engine, trust, boot = bootstrapped_engine()
    assert boot["evidence_id"] in [row["evidence_id"] for row in engine.snapshot.evidence["records"]]
    assert trust.evidence_id in next(
        row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == boot["evidence_id"]
    )["derived_from"]

    decision = engine.authorize_scoped_request(
        AuthorityRequest("root", "workspace-a", "root", "workspace.admin")
    )
    assert decision["decision"]["allowed"] is False
    assert decision["decision"]["reason"] == "NO_APPLICABLE_GRANT"
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_principal_registration_requires_durable_scoped_authority_and_denials_are_recorded():
    engine, _, _ = bootstrapped_engine()
    before = len(engine.snapshot.evidence["records"])
    with pytest.raises(PermissionError, match="principal registration denied"):
        engine.register_scoped_principal(
            Principal("alice", "HUMAN"),
            workspace_id="workspace-a",
            actor_principal_id="root",
        )
    after = len(engine.snapshot.evidence["records"])
    assert after == before + 1
    report = engine.scoped_authority_report(workspace_id="workspace-a")
    assert "alice" not in report["principals"]
    assert any(row["decision"]["allowed"] is False for row in report["decisions"].values())

    grant_root_identity_registration(engine)
    registered = engine.register_scoped_principal(
        Principal("alice", "HUMAN"),
        workspace_id="workspace-a",
        actor_principal_id="root",
    )
    assert registered["principal"]["principal_id"] == "alice"
    assert registered["authorized_by_decision_evidence_id"] if "authorized_by_decision_evidence_id" in registered else registered["evidence_id"]
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_valid_delegated_grant_and_explicit_deny_are_durable_and_replayable():
    engine, _, _ = bootstrapped_engine()
    grant_root_identity_registration(engine)
    engine.register_scoped_principal(Principal("alice", "HUMAN"), workspace_id="workspace-a", actor_principal_id="root")
    engine.register_scoped_principal(Principal("builder", "MACHINE"), workspace_id="workspace-a", actor_principal_id="root")

    alice_parent = engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "alice",
            "root",
            "workspace-a",
            "root",
            ("code.write",),
            delegable=True,
            remaining_delegation_depth=2,
        )
    )
    child = engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "builder",
            "alice",
            "workspace-a",
            "root",
            ("code.write",),
            parent_grant_id=alice_parent["grant"]["grant_id"],
        )
    )
    assert child["admission"]["valid"] is True

    allowed = engine.authorize_scoped_request(
        AuthorityRequest("builder", "workspace-a", "root", "code.write")
    )
    assert allowed["decision"]["allowed"] is True

    deny = engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "builder",
            "root",
            "workspace-a",
            "root",
            ("code.write",),
            effect="DENY",
            nondelegable=True,
        )
    )
    denied = engine.authorize_scoped_request(
        AuthorityRequest("builder", "workspace-a", "root", "code.write")
    )
    assert denied["decision"]["allowed"] is False
    assert denied["decision"]["reason"] == "EXPLICIT_DENY"
    assert deny["grant"]["grant_id"] in denied["decision"]["deny_grant_ids"]
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_invalid_delegation_has_no_authority_evidence_side_effect():
    engine, _, _ = bootstrapped_engine()
    grant_root_identity_registration(engine)
    engine.register_scoped_principal(Principal("alice", "HUMAN"), workspace_id="workspace-a", actor_principal_id="root")
    engine.register_scoped_principal(Principal("builder", "MACHINE"), workspace_id="workspace-a", actor_principal_id="root")
    parent = engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant(
            "alice",
            "root",
            "workspace-a",
            "root",
            ("code.write",),
            delegable=True,
            remaining_delegation_depth=2,
        )
    )
    before = len(engine.snapshot.evidence["records"])
    with pytest.raises(PermissionError, match="CHILD_CAPABILITY_EXCEEDS_PARENT"):
        engine.admit_scoped_authority_grant(
            ScopedAuthorityGrant(
                "builder",
                "alice",
                "workspace-a",
                "root",
                ("history.delete",),
                parent_grant_id=parent["grant"]["grant_id"],
            )
        )
    assert len(engine.snapshot.evidence["records"]) == before


def test_workspace_reports_are_isolated_and_cross_run_mapping_is_not_consulted():
    engine, _, _ = bootstrapped_engine()
    grant_root_identity_registration(engine)
    engine.register_scoped_principal(Principal("alice", "HUMAN"), workspace_id="workspace-a", actor_principal_id="root")
    engine.admit_scoped_authority_grant(
        ScopedAuthorityGrant("alice", "root", "workspace-a", "root", ("code.write",))
    )
    visible = engine.scoped_authority_report(workspace_id="workspace-a")
    hidden = engine.scoped_authority_report(workspace_id="workspace-b")
    assert "alice" in visible["principals"]
    assert hidden["workspace"] is None
    assert hidden["grants"] == {}

    # No cross-run principal map or resource ledger is an input to this decision.
    decision = engine.evaluate_scoped_request(
        AuthorityRequest("alice", "workspace-a", "root", "code.write")
    )
    assert decision.allowed is True


def test_effect_proposal_is_scope_bound_without_requiring_execution_authority():
    engine, trust, _ = bootstrapped_engine()
    spec = EffectSpec("external-write", idempotency_key="effect-scope-bound")
    record = engine.propose_effect(
        spec,
        workspace_id="workspace-a",
        scope_id="root",
        proposer_principal_id="root",
    )
    assert record.status == EffectStatus.PROPOSED.value
    report = engine.effect_authority_report(workspace_id="workspace-a", scope_id="root")
    assert len(report["proposals"]) == 1
    proposal = next(iter(report["proposals"].values()))["document"]
    assert proposal["effect_id"] == record.spec.effect_id
    assert proposal["metadata"]["idempotency_key"] == "effect-scope-bound"

    engine.bootstrap_scoped_workspace(
        Principal("root", "SYSTEM"),
        Workspace("workspace-b", "root"),
        trust_anchor_evidence_id=trust.evidence_id,
    )
    with pytest.raises(PermissionError, match="idempotent effect reuse crosses"):
        engine.propose_effect(
            EffectSpec("external-write", idempotency_key="effect-scope-bound"),
            workspace_id="workspace-b",
            scope_id="root",
            proposer_principal_id="root",
        )
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()


def test_effect_authorization_requires_scoped_capability_and_denial_does_not_authorize():
    engine, _, _ = bootstrapped_engine()
    record = engine.propose_effect(
        EffectSpec("external-write", idempotency_key="authorize-scope"),
        workspace_id="workspace-a",
        scope_id="root",
        proposer_principal_id="root",
    )
    before = len(engine.scoped_authority_report(workspace_id="workspace-a")["decisions"])
    with pytest.raises(PermissionError, match="effect.authorize"):
        engine.authorize_effect(
            record.spec.effect_id,
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
    assert engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id).status == EffectStatus.PROPOSED.value
    after = engine.scoped_authority_report(workspace_id="workspace-a")["decisions"]
    assert len(after) == before + 1
    assert any(row["decision"]["reason"] == "NO_APPLICABLE_GRANT" for row in after.values())

    grant_root_effect_capabilities(engine, EFFECT_AUTHORITY_CAPABILITIES["authorize"])
    authorized = engine.authorize_effect(
        record.spec.effect_id,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert authorized.status == EffectStatus.AUTHORIZED.value
    assert authorized.authority.startswith("scoped:scoped-authority-evidence-")
    report = engine.effect_authority_report(workspace_id="workspace-a", scope_id="root")
    assert len(report["authorizations"]) == 1


def test_effect_execution_requires_fresh_authority_on_every_attempt_and_expiry_blocks_retry():
    engine, _, _ = bootstrapped_engine()
    grant_root_effect_capabilities(engine, EFFECT_AUTHORITY_CAPABILITIES["authorize"])
    grant_root_effect_capabilities(engine, EFFECT_AUTHORITY_CAPABILITIES["execute"], expires_at=5)
    record = engine.propose_effect(
        EffectSpec(
            "external-write",
            idempotency_key="fresh-execute-authority",
            retry_policy=RetryPolicy(max_attempts=2, retry_on_failure=True),
        ),
        workspace_id="workspace-a",
        scope_id="root",
        proposer_principal_id="root",
    )
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
        at_time=1,
    )
    calls = []

    def failing_executor(spec, key):
        calls.append((spec.effect_id, key))
        raise RuntimeError("first attempt fails")

    failed = engine.execute_effect(
        record.spec.effect_id,
        failing_executor,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
        at_time=1,
    )
    assert failed.status == EffectStatus.FAILED.value
    assert len(calls) == 1

    with pytest.raises(PermissionError, match="effect.execute"):
        engine.execute_effect(
            record.spec.effect_id,
            failing_executor,
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
            at_time=6,
        )
    assert len(calls) == 1
    assert engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id).status == EffectStatus.FAILED.value
    execution_rows = engine.effect_authority_report(workspace_id="workspace-a", scope_id="root")["execution_authorities"]
    assert len(execution_rows) == 1


def test_effect_reconciliation_requires_independent_scoped_capability():
    engine, _, _ = bootstrapped_engine()
    grant_root_effect_capabilities(engine, EFFECT_AUTHORITY_CAPABILITIES["authorize"])
    record = engine.propose_effect(
        EffectSpec("external-write", idempotency_key="reconcile-authority"),
        workspace_id="workspace-a",
        scope_id="root",
        proposer_principal_id="root",
    )
    engine.authorize_effect(
        record.spec.effect_id,
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    stored = engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id)
    stored.status = EffectStatus.UNKNOWN.value
    engine.store.save_effect(stored)

    with pytest.raises(PermissionError, match="effect.reconcile"):
        engine.reconcile_effect(
            record.spec.effect_id,
            succeeded=True,
            result={"observed": True},
            workspace_id="workspace-a",
            scope_id="root",
            actor_principal_id="root",
        )
    assert engine.store.load_effect(engine.snapshot.machine_id, record.spec.effect_id).status == EffectStatus.UNKNOWN.value

    grant_root_effect_capabilities(engine, EFFECT_AUTHORITY_CAPABILITIES["reconcile"])
    reconciled = engine.reconcile_effect(
        record.spec.effect_id,
        succeeded=True,
        result={"observed": True},
        workspace_id="workspace-a",
        scope_id="root",
        actor_principal_id="root",
    )
    assert reconciled.status == EffectStatus.SUCCEEDED.value
    report = engine.effect_authority_report(workspace_id="workspace-a", scope_id="root")
    assert len(report["reconcile_authorities"]) == 1
    binding_id = next(iter(report["reconcile_authorities"]))
    assert binding_id in reconciled.evidence
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
