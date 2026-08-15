from aasm.cross_run_knowledge import CrossRunPrincipalMap
from aasm.scoped_authority import (
    AUTHORITY_WILDCARD,
    AuthorityRequest,
    Principal,
    ScopedAuthorityGrant,
    Workspace,
    evaluate_scoped_authority,
    scoped_authority_contract,
    validate_grant_admission,
)
from aasm._scopes_model import DecisionScope, ScopeDependency, default_scope_state


def scope_state(*, isolated=False, dependency=False):
    state = default_scope_state()
    state["records"]["architecture"] = DecisionScope(
        "architecture",
        kind="ARCHITECTURE",
        parent_scope_id="root",
        inheritance="ISOLATED" if isolated else "INHERIT",
    ).to_dict()
    state["records"]["implementation"] = DecisionScope(
        "implementation",
        kind="IMPLEMENTATION",
        parent_scope_id="architecture",
    ).to_dict()
    if dependency:
        dep = ScopeDependency(
            "root-authorizes-architecture",
            "root",
            "architecture",
            relation="AUTHORIZES",
            invalidation_policy="NONE",
        )
        state["dependencies"][dep.dependency_id] = dep.to_dict()
    return state


def identities():
    principals = [
        Principal("fabric-root", "SYSTEM"),
        Principal("alice", "HUMAN"),
        Principal("builder", "MACHINE"),
        Principal("outsider", "SERVICE"),
    ]
    workspaces = [
        Workspace("workspace-a", "fabric-root", owner_principal_id="alice"),
        Workspace("workspace-b", "fabric-root", owner_principal_id="outsider"),
    ]
    return principals, workspaces


def bootstrap(subject, capabilities, *, effect="ALLOW", scope_id="root", delegable=False, depth=0, expires_at=None, nondelegable=False):
    return ScopedAuthorityGrant(
        subject,
        "fabric-root",
        "workspace-a",
        scope_id,
        tuple(capabilities),
        effect=effect,
        delegable=delegable,
        remaining_delegation_depth=depth,
        expires_at=expires_at,
        nondelegable=nondelegable,
    )


def test_contract_freezes_identity_scope_and_non_authority_boundaries():
    contract = scoped_authority_contract()
    assert contract["contract_id"] == "aasm.authority.scoped.v1"
    assert contract["identity_contract_id"] == "aasm.identity.scoped.v1"
    assert contract["workspace_boundary"] == "EXACT_MATCH_FAIL_CLOSED"
    assert contract["scope_flow"] == "EXISTING_AASM_SCOPE_FLOW_ONLY"
    assert contract["deny_precedence"] == "ANY_MATCHING_DENY_OVERRIDES_ALLOW"
    assert contract["resource_state_grants_authority"] is False
    assert contract["cross_run_authority_transfer"] == "NEVER"
    assert contract["default"] == "DENY"


def test_no_grant_means_deny_even_for_workspace_root():
    principals, workspaces = identities()
    decision = evaluate_scoped_authority(
        AuthorityRequest("fabric-root", "workspace-a", "root", "workspace.admin"),
        principals=principals,
        workspaces=workspaces,
        grants=[],
        scope_state=scope_state(),
    )
    assert decision.allowed is False
    assert decision.reason == "NO_APPLICABLE_GRANT"


def test_explicit_allow_flows_down_inherited_scope():
    principals, workspaces = identities()
    grant = bootstrap("alice", ("code.write",))
    decision = evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-a", "implementation", "code.write"),
        principals=principals,
        workspaces=workspaces,
        grants=[grant],
        scope_state=scope_state(),
    )
    assert decision.allowed is True
    assert decision.allow_grant_ids == (grant.grant_id,)


def test_isolated_scope_blocks_ancestor_grant_without_explicit_dependency():
    principals, workspaces = identities()
    grant = bootstrap("alice", ("code.write",))
    denied = evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-a", "architecture", "code.write"),
        principals=principals,
        workspaces=workspaces,
        grants=[grant],
        scope_state=scope_state(isolated=True),
    )
    assert denied.allowed is False
    assert denied.reason == "NO_APPLICABLE_GRANT"

    allowed = evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-a", "architecture", "code.write"),
        principals=principals,
        workspaces=workspaces,
        grants=[grant],
        scope_state=scope_state(isolated=True, dependency=True),
    )
    assert allowed.allowed is True


def test_any_matching_deny_overrides_allow():
    principals, workspaces = identities()
    allow = bootstrap("alice", ("code.write",))
    deny = bootstrap("alice", ("code.write",), effect="DENY", scope_id="architecture", nondelegable=True)
    decision = evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-a", "implementation", "code.write"),
        principals=principals,
        workspaces=workspaces,
        grants=[allow, deny],
        scope_state=scope_state(),
    )
    assert decision.allowed is False
    assert decision.reason == "EXPLICIT_DENY"
    assert allow.grant_id in decision.allow_grant_ids
    assert deny.grant_id in decision.deny_grant_ids


def test_expired_grant_fails_closed():
    principals, workspaces = identities()
    grant = bootstrap("alice", ("code.write",), expires_at=10)
    assert evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-a", "root", "code.write", at_time=9),
        principals=principals,
        workspaces=workspaces,
        grants=[grant],
        scope_state=scope_state(),
    ).allowed is True
    expired = evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-a", "root", "code.write", at_time=10),
        principals=principals,
        workspaces=workspaces,
        grants=[grant],
        scope_state=scope_state(),
    )
    assert expired.allowed is False
    assert expired.reason == "NO_APPLICABLE_GRANT"


def test_workspace_authority_never_crosses_workspace_boundary():
    principals, workspaces = identities()
    grant = bootstrap("alice", ("code.write",))
    decision = evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-b", "root", "code.write"),
        principals=principals,
        workspaces=workspaces,
        grants=[grant],
        scope_state=scope_state(),
    )
    assert decision.allowed is False
    assert decision.reason == "NO_APPLICABLE_GRANT"


def test_only_workspace_root_can_bootstrap_parentless_grant():
    principals, workspaces = identities()
    illegal = ScopedAuthorityGrant("builder", "alice", "workspace-a", "root", ("code.write",))
    report = validate_grant_admission(
        illegal,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[],
        scope_state=scope_state(),
    )
    assert report["valid"] is False
    assert "ONLY_WORKSPACE_ROOT_MAY_BOOTSTRAP_GRANT" in report["errors"]


def test_delegation_cannot_exceed_parent_capability_or_scope():
    principals, workspaces = identities()
    parent = bootstrap("alice", ("code.write",), scope_id="architecture", delegable=True, depth=2)
    assert validate_grant_admission(
        parent,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[],
        scope_state=scope_state(),
    )["valid"] is True

    valid_child = ScopedAuthorityGrant(
        "builder",
        "alice",
        "workspace-a",
        "implementation",
        ("code.write",),
        delegable=True,
        remaining_delegation_depth=1,
        parent_grant_id=parent.grant_id,
    )
    valid = validate_grant_admission(
        valid_child,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[parent],
        scope_state=scope_state(),
    )
    assert valid["valid"] is True, valid

    capability_escape = ScopedAuthorityGrant(
        "builder",
        "alice",
        "workspace-a",
        "implementation",
        ("history.delete",),
        parent_grant_id=parent.grant_id,
    )
    report = validate_grant_admission(
        capability_escape,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[parent],
        scope_state=scope_state(),
    )
    assert report["valid"] is False
    assert "CHILD_CAPABILITY_EXCEEDS_PARENT" in report["errors"]

    scope_escape = ScopedAuthorityGrant(
        "builder",
        "alice",
        "workspace-a",
        "root",
        ("code.write",),
        parent_grant_id=parent.grant_id,
    )
    report = validate_grant_admission(
        scope_escape,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[parent],
        scope_state=scope_state(),
    )
    assert report["valid"] is False
    assert "CHILD_SCOPE_EXCEEDS_PARENT" in report["errors"]


def test_delegation_depth_and_nondelegable_parent_are_enforced():
    principals, workspaces = identities()
    parent = bootstrap("alice", ("code.write",), delegable=True, depth=1)
    too_deep = ScopedAuthorityGrant(
        "builder",
        "alice",
        "workspace-a",
        "root",
        ("code.write",),
        delegable=True,
        remaining_delegation_depth=1,
        parent_grant_id=parent.grant_id,
    )
    report = validate_grant_admission(
        too_deep,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[parent],
        scope_state=scope_state(),
    )
    assert report["valid"] is False
    assert "CHILD_DELEGATION_DEPTH_EXCEEDS_PARENT" in report["errors"]

    fixed = bootstrap("alice", ("code.write",), nondelegable=True)
    child = ScopedAuthorityGrant(
        "builder",
        "alice",
        "workspace-a",
        "root",
        ("code.write",),
        parent_grant_id=fixed.grant_id,
    )
    report = validate_grant_admission(
        child,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[fixed],
        scope_state=scope_state(),
    )
    assert report["valid"] is False
    assert "PARENT_GRANT_NOT_DELEGABLE" in report["errors"]


def test_wildcard_parent_may_delegate_specific_capability_but_specific_parent_cannot_delegate_wildcard():
    principals, workspaces = identities()
    wildcard = bootstrap("alice", (AUTHORITY_WILDCARD,), delegable=True, depth=2)
    child = ScopedAuthorityGrant(
        "builder",
        "alice",
        "workspace-a",
        "root",
        ("code.write",),
        parent_grant_id=wildcard.grant_id,
    )
    assert validate_grant_admission(
        child,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[wildcard],
        scope_state=scope_state(),
    )["valid"] is True

    specific = bootstrap("alice", ("code.write",), delegable=True, depth=2)
    escalation = ScopedAuthorityGrant(
        "builder",
        "alice",
        "workspace-a",
        "root",
        (AUTHORITY_WILDCARD,),
        parent_grant_id=specific.grant_id,
    )
    report = validate_grant_admission(
        escalation,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[specific],
        scope_state=scope_state(),
    )
    assert report["valid"] is False
    assert "CHILD_CAPABILITY_EXCEEDS_PARENT" in report["errors"]


def test_cross_run_principal_mapping_does_not_create_local_authority():
    principals, workspaces = identities()
    mapping = CrossRunPrincipalMap("foreign-run", "foreign-controller", "alice")
    assert mapping.local_principal_id == "alice"
    decision = evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-a", "root", "code.write"),
        principals=principals,
        workspaces=workspaces,
        grants=[],
        scope_state=scope_state(),
    )
    assert decision.allowed is False
    assert decision.reason == "NO_APPLICABLE_GRANT"


def test_resource_presence_is_not_an_input_to_authorization():
    principals, workspaces = identities()
    grant = bootstrap("alice", ("code.write",))
    without_resource_state = evaluate_scoped_authority(
        AuthorityRequest("alice", "workspace-a", "root", "code.write"),
        principals=principals,
        workspaces=workspaces,
        grants=[grant],
        scope_state=scope_state(),
    )
    # Resource capacity is intentionally absent from the evaluator contract.
    assert without_resource_state.allowed is True
    assert "resource" not in scoped_authority_contract()
