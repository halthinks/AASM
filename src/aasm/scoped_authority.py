from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ._scopes_graph import scope_flow_allowed
from ._scopes_model import normalize_scope_state
from .semantic_result import semantic_fingerprint


SCOPED_IDENTITY_CONTRACT_ID = "aasm.identity.scoped.v1"
SCOPED_AUTHORITY_CONTRACT_ID = "aasm.authority.scoped.v1"
SCOPED_AUTHORITY_CONTRACT_VERSION = "0.1.0"
SCOPED_AUTHORITY_STABILITY = "FOUNDATION_EXPERIMENTAL"

PRINCIPAL_KINDS = ("HUMAN", "SERVICE", "MACHINE", "OPERATOR", "SYSTEM")
AUTHORITY_EFFECTS = ("ALLOW", "DENY")
AUTHORITY_WILDCARD = "*"


def _uniq(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({str(value) for value in values}))


def _require(value: str, name: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


@dataclass(frozen=True)
class Principal:
    principal_id: str
    kind: str = "SERVICE"
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "principal_id", _require(self.principal_id, "principal_id"))
        if self.kind not in PRINCIPAL_KINDS:
            raise ValueError(f"invalid principal kind: {self.kind}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "principal_id": self.principal_id,
            "kind": self.kind,
            "active": bool(self.active),
            "metadata": dict(self.metadata),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


@dataclass(frozen=True)
class Workspace:
    workspace_id: str
    root_principal_id: str
    owner_principal_id: str = ""
    active: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "workspace_id", _require(self.workspace_id, "workspace_id"))
        object.__setattr__(self, "root_principal_id", _require(self.root_principal_id, "root_principal_id"))
        if not self.owner_principal_id:
            object.__setattr__(self, "owner_principal_id", self.root_principal_id)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "workspace_id": self.workspace_id,
            "root_principal_id": self.root_principal_id,
            "owner_principal_id": self.owner_principal_id,
            "active": bool(self.active),
            "metadata": dict(self.metadata),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


@dataclass(frozen=True)
class ScopedAuthorityGrant:
    subject_principal_id: str
    issuer_principal_id: str
    workspace_id: str
    scope_id: str
    capabilities: tuple[str, ...]
    effect: str = "ALLOW"
    delegable: bool = False
    remaining_delegation_depth: int = 0
    parent_grant_id: str = ""
    not_before: float = 0.0
    expires_at: float | None = None
    nondelegable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)
    grant_id: str = ""

    def __post_init__(self) -> None:
        for name in ("subject_principal_id", "issuer_principal_id", "workspace_id", "scope_id"):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        capabilities = _uniq(self.capabilities)
        if not capabilities:
            raise ValueError("authority grant requires at least one capability")
        if self.effect not in AUTHORITY_EFFECTS:
            raise ValueError(f"invalid authority effect: {self.effect}")
        if int(self.remaining_delegation_depth) < 0:
            raise ValueError("remaining_delegation_depth must be non-negative")
        if self.delegable and int(self.remaining_delegation_depth) <= 0:
            raise ValueError("delegable grant requires positive remaining_delegation_depth")
        if self.nondelegable and self.delegable:
            raise ValueError("nondelegable grant cannot also be delegable")
        if float(self.not_before) < 0:
            raise ValueError("not_before must be non-negative")
        if self.expires_at is not None and float(self.expires_at) <= float(self.not_before):
            raise ValueError("expires_at must be greater than not_before")
        object.__setattr__(self, "capabilities", capabilities)
        object.__setattr__(self, "remaining_delegation_depth", int(self.remaining_delegation_depth))
        if not self.grant_id:
            object.__setattr__(self, "grant_id", f"authority-grant-{semantic_fingerprint(self.identity_payload())[:24]}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "subject_principal_id": self.subject_principal_id,
            "issuer_principal_id": self.issuer_principal_id,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "capabilities": list(self.capabilities),
            "effect": self.effect,
            "delegable": bool(self.delegable),
            "remaining_delegation_depth": self.remaining_delegation_depth,
            "parent_grant_id": self.parent_grant_id,
            "not_before": float(self.not_before),
            "expires_at": None if self.expires_at is None else float(self.expires_at),
            "nondelegable": bool(self.nondelegable),
            "metadata": dict(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"grant_id": self.grant_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"grant_id": self.grant_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ScopedAuthorityGrant":
        payload = dict(value)
        payload.pop("fingerprint", None)
        payload["capabilities"] = tuple(payload.get("capabilities") or ())
        return cls(**payload)

    def active_at(self, at_time: float) -> bool:
        when = float(at_time)
        if when < float(self.not_before):
            return False
        return self.expires_at is None or when < float(self.expires_at)


@dataclass(frozen=True)
class AuthorityRequest:
    principal_id: str
    workspace_id: str
    scope_id: str
    capability: str
    at_time: float = 0.0
    machine_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for name in ("principal_id", "workspace_id", "scope_id", "capability"):
            object.__setattr__(self, name, _require(getattr(self, name), name))
        if float(self.at_time) < 0:
            raise ValueError("at_time must be non-negative")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "principal_id": self.principal_id,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "capability": self.capability,
            "at_time": float(self.at_time),
            "machine_id": self.machine_id,
            "metadata": dict(self.metadata),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


@dataclass(frozen=True)
class AuthorityDecision:
    request_fingerprint: str
    allowed: bool
    reason: str
    allow_grant_ids: tuple[str, ...] = ()
    deny_grant_ids: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "allow_grant_ids", _uniq(self.allow_grant_ids))
        object.__setattr__(self, "deny_grant_ids", _uniq(self.deny_grant_ids))
        object.__setattr__(self, "diagnostics", tuple(map(str, self.diagnostics)))

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict(include_fingerprint=False))

    def to_dict(self, *, include_fingerprint: bool = True) -> dict[str, Any]:
        out = {
            "contract_id": SCOPED_AUTHORITY_CONTRACT_ID,
            "contract_version": SCOPED_AUTHORITY_CONTRACT_VERSION,
            "request_fingerprint": self.request_fingerprint,
            "allowed": bool(self.allowed),
            "reason": self.reason,
            "allow_grant_ids": list(self.allow_grant_ids),
            "deny_grant_ids": list(self.deny_grant_ids),
            "diagnostics": list(self.diagnostics),
        }
        if include_fingerprint:
            out["fingerprint"] = semantic_fingerprint(out)
        return out


def scoped_authority_contract() -> dict[str, Any]:
    return {
        "contract_id": SCOPED_AUTHORITY_CONTRACT_ID,
        "contract_version": SCOPED_AUTHORITY_CONTRACT_VERSION,
        "stability": SCOPED_AUTHORITY_STABILITY,
        "identity_contract_id": SCOPED_IDENTITY_CONTRACT_ID,
        "workspace_boundary": "EXACT_MATCH_FAIL_CLOSED",
        "scope_flow": "EXISTING_AASM_SCOPE_FLOW_ONLY",
        "deny_precedence": "ANY_MATCHING_DENY_OVERRIDES_ALLOW",
        "delegation": "ISSUER_CANNOT_GRANT_MORE_THAN_ACTIVE_DELEGABLE_PARENT",
        "delegated_wildcard": "FORBIDDEN",
        "root_bootstrap": "EXPLICIT_WORKSPACE_ROOT_PRINCIPAL_ONLY",
        "resource_state_grants_authority": False,
        "cross_run_authority_transfer": "NEVER",
        "default": "DENY",
    }


def _capability_matches(grant: ScopedAuthorityGrant, capability: str) -> bool:
    return AUTHORITY_WILDCARD in grant.capabilities or capability in grant.capabilities


def _scope_is_active(scope_state: Mapping[str, Any], scope_id: str) -> bool:
    state = normalize_scope_state(dict(scope_state))
    record = state["records"].get(scope_id)
    return bool(record and record.get("status") == "ACTIVE")


def _grant_matches_request(grant: ScopedAuthorityGrant, request: AuthorityRequest, scope_state: Mapping[str, Any]) -> bool:
    if (
        grant.subject_principal_id != request.principal_id
        or grant.workspace_id != request.workspace_id
        or not grant.active_at(request.at_time)
        or not _capability_matches(grant, request.capability)
    ):
        return False
    try:
        return scope_flow_allowed(dict(scope_state), grant.scope_id, request.scope_id)
    except KeyError:
        return False


def evaluate_scoped_authority(
    request: AuthorityRequest,
    *,
    principals: Iterable[Principal],
    workspaces: Iterable[Workspace],
    grants: Iterable[ScopedAuthorityGrant],
    scope_state: Mapping[str, Any],
) -> AuthorityDecision:
    principal_map = {row.principal_id: row for row in principals}
    workspace_map = {row.workspace_id: row for row in workspaces}
    principal = principal_map.get(request.principal_id)
    if principal is None:
        return AuthorityDecision(request.fingerprint, False, "UNKNOWN_PRINCIPAL")
    if not principal.active:
        return AuthorityDecision(request.fingerprint, False, "INACTIVE_PRINCIPAL")
    workspace = workspace_map.get(request.workspace_id)
    if workspace is None:
        return AuthorityDecision(request.fingerprint, False, "UNKNOWN_WORKSPACE")
    if not workspace.active:
        return AuthorityDecision(request.fingerprint, False, "INACTIVE_WORKSPACE")
    if not _scope_is_active(scope_state, request.scope_id):
        return AuthorityDecision(request.fingerprint, False, "INACTIVE_OR_UNKNOWN_SCOPE")

    matched = [row for row in grants if _grant_matches_request(row, request, scope_state)]
    denies = tuple(row.grant_id for row in matched if row.effect == "DENY")
    allows = tuple(row.grant_id for row in matched if row.effect == "ALLOW")
    if denies:
        return AuthorityDecision(request.fingerprint, False, "EXPLICIT_DENY", allows, denies)
    if allows:
        return AuthorityDecision(request.fingerprint, True, "EXPLICIT_ALLOW", allows, ())
    return AuthorityDecision(request.fingerprint, False, "NO_APPLICABLE_GRANT")


def _parent_covers_capabilities(parent: ScopedAuthorityGrant, child: ScopedAuthorityGrant) -> bool:
    if AUTHORITY_WILDCARD in child.capabilities:
        return False
    if AUTHORITY_WILDCARD in parent.capabilities:
        return True
    return set(child.capabilities).issubset(set(parent.capabilities))


def validate_grant_admission(
    grant: ScopedAuthorityGrant,
    *,
    principals: Iterable[Principal],
    workspaces: Iterable[Workspace],
    existing_grants: Iterable[ScopedAuthorityGrant],
    scope_state: Mapping[str, Any],
    at_time: float = 0.0,
) -> dict[str, Any]:
    principal_map = {row.principal_id: row for row in principals}
    workspace_map = {row.workspace_id: row for row in workspaces}
    grant_map = {row.grant_id: row for row in existing_grants}
    errors: list[str] = []

    subject = principal_map.get(grant.subject_principal_id)
    issuer = principal_map.get(grant.issuer_principal_id)
    workspace = workspace_map.get(grant.workspace_id)
    if subject is None or not subject.active:
        errors.append("SUBJECT_PRINCIPAL_NOT_ACTIVE")
    if issuer is None or not issuer.active:
        errors.append("ISSUER_PRINCIPAL_NOT_ACTIVE")
    if workspace is None or not workspace.active:
        errors.append("WORKSPACE_NOT_ACTIVE")
    if not _scope_is_active(scope_state, grant.scope_id):
        errors.append("GRANT_SCOPE_NOT_ACTIVE")

    if workspace is not None and not grant.parent_grant_id:
        if grant.issuer_principal_id != workspace.root_principal_id:
            errors.append("ONLY_WORKSPACE_ROOT_MAY_BOOTSTRAP_GRANT")
    elif grant.parent_grant_id:
        if AUTHORITY_WILDCARD in grant.capabilities:
            errors.append("DELEGATED_WILDCARD_FORBIDDEN")
        parent = grant_map.get(grant.parent_grant_id)
        if parent is None:
            errors.append("UNKNOWN_PARENT_GRANT")
        else:
            if parent.effect != "ALLOW":
                errors.append("PARENT_GRANT_MUST_ALLOW")
            if parent.subject_principal_id != grant.issuer_principal_id:
                errors.append("PARENT_GRANT_DOES_NOT_BELONG_TO_ISSUER")
            if parent.workspace_id != grant.workspace_id:
                errors.append("PARENT_WORKSPACE_MISMATCH")
            if not parent.active_at(at_time):
                errors.append("PARENT_GRANT_NOT_ACTIVE")
            if not parent.delegable or parent.nondelegable:
                errors.append("PARENT_GRANT_NOT_DELEGABLE")
            if parent.remaining_delegation_depth <= 0:
                errors.append("PARENT_DELEGATION_DEPTH_EXHAUSTED")
            if grant.remaining_delegation_depth > max(0, parent.remaining_delegation_depth - 1):
                errors.append("CHILD_DELEGATION_DEPTH_EXCEEDS_PARENT")
            if not _parent_covers_capabilities(parent, grant):
                errors.append("CHILD_CAPABILITY_EXCEEDS_PARENT")
            try:
                if not scope_flow_allowed(dict(scope_state), parent.scope_id, grant.scope_id):
                    errors.append("CHILD_SCOPE_EXCEEDS_PARENT")
            except KeyError:
                errors.append("CHILD_SCOPE_EXCEEDS_PARENT")

            if issuer is not None and workspace is not None:
                for capability in grant.capabilities:
                    if capability == AUTHORITY_WILDCARD:
                        continue
                    decision = evaluate_scoped_authority(
                        AuthorityRequest(
                            grant.issuer_principal_id,
                            grant.workspace_id,
                            grant.scope_id,
                            capability,
                            at_time=at_time,
                        ),
                        principals=principal_map.values(),
                        workspaces=workspace_map.values(),
                        grants=grant_map.values(),
                        scope_state=scope_state,
                    )
                    if not decision.allowed:
                        errors.append(f"ISSUER_NOT_AUTHORIZED:{capability}")

    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "grant_id": grant.grant_id,
        "grant_fingerprint": grant.fingerprint,
        "authority_inherited_from_cross_run": False,
    }


__all__ = [
    "SCOPED_IDENTITY_CONTRACT_ID",
    "SCOPED_AUTHORITY_CONTRACT_ID",
    "SCOPED_AUTHORITY_CONTRACT_VERSION",
    "SCOPED_AUTHORITY_STABILITY",
    "PRINCIPAL_KINDS",
    "AUTHORITY_EFFECTS",
    "AUTHORITY_WILDCARD",
    "Principal",
    "Workspace",
    "ScopedAuthorityGrant",
    "AuthorityRequest",
    "AuthorityDecision",
    "scoped_authority_contract",
    "evaluate_scoped_authority",
    "validate_grant_admission",
]
