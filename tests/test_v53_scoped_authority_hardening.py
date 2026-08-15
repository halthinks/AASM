from aasm._scopes_model import default_scope_state
from aasm.scoped_authority import (
    AUTHORITY_WILDCARD,
    AuthorityRequest,
    Principal,
    ScopedAuthorityGrant,
    Workspace,
    evaluate_scoped_authority,
    validate_grant_admission,
)


def identities():
    return (
        [Principal("root", "SYSTEM"), Principal("issuer", "HUMAN"), Principal("child", "MACHINE")],
        [Workspace("workspace-a", "root", owner_principal_id="issuer")],
    )


def test_delegated_wildcard_is_forbidden_even_from_wildcard_parent():
    principals, workspaces = identities()
    parent = ScopedAuthorityGrant(
        "issuer",
        "root",
        "workspace-a",
        "root",
        (AUTHORITY_WILDCARD,),
        delegable=True,
        remaining_delegation_depth=2,
    )
    assert validate_grant_admission(
        parent,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[],
        scope_state=default_scope_state(),
    )["valid"] is True

    child = ScopedAuthorityGrant(
        "child",
        "issuer",
        "workspace-a",
        "root",
        (AUTHORITY_WILDCARD,),
        parent_grant_id=parent.grant_id,
    )
    report = validate_grant_admission(
        child,
        principals=principals,
        workspaces=workspaces,
        existing_grants=[parent],
        scope_state=default_scope_state(),
    )
    assert report["valid"] is False
    assert "DELEGATED_WILDCARD_FORBIDDEN" in report["errors"]
    assert "CHILD_CAPABILITY_EXCEEDS_PARENT" in report["errors"]


def test_malformed_grant_scope_never_crashes_authority_evaluation():
    principals, workspaces = identities()
    malformed = ScopedAuthorityGrant(
        "issuer",
        "root",
        "workspace-a",
        "missing-scope",
        ("code.write",),
    )
    decision = evaluate_scoped_authority(
        AuthorityRequest("issuer", "workspace-a", "root", "code.write"),
        principals=principals,
        workspaces=workspaces,
        grants=[malformed],
        scope_state=default_scope_state(),
    )
    assert decision.allowed is False
    assert decision.reason == "NO_APPLICABLE_GRANT"
