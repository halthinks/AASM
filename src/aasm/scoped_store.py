from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from ._scopes_graph import scope_flow_allowed
from .effects import EffectRecord
from .scoped_authority import (
    AuthorityRequest,
    Principal,
    ScopedAuthorityGrant,
    Workspace,
    evaluate_scoped_authority,
)


SCOPED_STORE_CONTRACT_ID = "aasm.store.scoped.v1"
SCOPED_STORE_CONTRACT_VERSION = "0.1.0"
SCOPED_STORE_STABILITY = "FOUNDATION_EXPERIMENTAL"

STORE_CAPABILITIES = {
    "snapshot_read": "store.snapshot.read",
    "events_read": "store.events.read",
    "checkpoint_read": "store.checkpoint.read",
    "effects_read": "store.effects.read",
    "unfinished_list": "store.unfinished.list",
}

_AUTHORITY_RECORD_TYPE = "aasm_scoped_authority_record_type"
_AUTHORITY_DOCUMENT = "document"


def scoped_store_contract() -> dict[str, Any]:
    return {
        "contract_id": SCOPED_STORE_CONTRACT_ID,
        "contract_version": SCOPED_STORE_CONTRACT_VERSION,
        "stability": SCOPED_STORE_STABILITY,
        "read_boundary": "EXPLICIT_PRINCIPAL_WORKSPACE_SCOPE_CAPABILITY",
        "raw_snapshot_access": "ROOT_SCOPE_SINGLE_WORKSPACE_ONLY",
        "raw_event_access": "ROOT_SCOPE_SINGLE_WORKSPACE_ONLY",
        "raw_checkpoint_access": "ROOT_SCOPE_SINGLE_WORKSPACE_ONLY",
        "effect_access": "V53_EFFECT_BINDING_AND_SCOPE_FLOW_ONLY",
        "multi_workspace_raw_access": "FAIL_CLOSED_USE_SCOPED_PROJECTIONS",
        "legacy_unscoped_effect_access": "FAIL_CLOSED",
        "direct_store_write": "FORBIDDEN_USE_GOVERNED_RUNTIME_TRANSITIONS",
        "authority_source": "DURABLE_V53_SCOPED_AUTHORITY_EVIDENCE",
        "scope_source": "DURABLE_AASM_CALCULUS_SCOPE_STATE",
    }


@dataclass(frozen=True)
class ScopedStoreAccess:
    principal_id: str
    workspace_id: str
    scope_id: str = "root"
    at_time: float = 0.0

    def __post_init__(self) -> None:
        if not self.principal_id.strip() or not self.workspace_id.strip() or not self.scope_id.strip():
            raise ValueError("scoped store access requires principal, workspace, and scope")
        if float(self.at_time) < 0:
            raise ValueError("scoped store access at_time must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "workspace_id": self.workspace_id,
            "scope_id": self.scope_id,
            "at_time": float(self.at_time),
        }


def _without_fingerprint(value: Mapping[str, Any]) -> dict[str, Any]:
    return {key: deepcopy(item) for key, item in value.items() if key != "fingerprint"}


def _active_authority_records(snapshot) -> Iterable[tuple[str, dict[str, Any], str]]:
    for row in snapshot.evidence.get("records", []):
        if row.get("status", "active") != "active":
            continue
        metadata = row.get("metadata") or {}
        record_type = metadata.get(_AUTHORITY_RECORD_TYPE)
        document = metadata.get(_AUTHORITY_DOCUMENT)
        if record_type and isinstance(document, dict):
            yield str(record_type), deepcopy(document), str(row.get("evidence_id") or "")


def _authority_inputs(snapshot, workspace_id: str):
    workspaces: dict[str, Workspace] = {}
    principals: dict[str, Principal] = {}
    grants: dict[str, ScopedAuthorityGrant] = {}
    for record_type, document, _ in _active_authority_records(snapshot):
        if record_type == "workspace_bootstrap":
            workspace = Workspace(**_without_fingerprint(document["workspace"]))
            root = Principal(**_without_fingerprint(document["root_principal"]))
            workspaces[workspace.workspace_id] = workspace
            if workspace.workspace_id == workspace_id:
                principals[root.principal_id] = root
        elif record_type == "principal" and str(document.get("workspace_id")) == workspace_id:
            principal = Principal(**_without_fingerprint(document["principal"]))
            principals[principal.principal_id] = principal
        elif record_type == "grant":
            grant = ScopedAuthorityGrant.from_dict(document["grant"])
            if grant.workspace_id == workspace_id:
                grants[grant.grant_id] = grant
    return principals, workspaces, grants


def _workspace_ids(snapshot) -> tuple[str, ...]:
    ids = []
    for record_type, document, _ in _active_authority_records(snapshot):
        if record_type == "workspace_bootstrap":
            ids.append(str(document["workspace"]["workspace_id"]))
    return tuple(sorted(set(ids)))


def _authorize(snapshot, access: ScopedStoreAccess, capability: str, *, request_scope_id: str | None = None) -> None:
    principals, workspaces, grants = _authority_inputs(snapshot, access.workspace_id)
    decision = evaluate_scoped_authority(
        AuthorityRequest(
            access.principal_id,
            access.workspace_id,
            request_scope_id or access.scope_id,
            capability,
            at_time=access.at_time,
            machine_id=snapshot.machine_id,
        ),
        principals=principals.values(),
        workspaces=workspaces.values(),
        grants=grants.values(),
        scope_state=snapshot.calculus.get("scope_state") or {},
    )
    if not decision.allowed:
        raise PermissionError(f"scoped store access denied {capability}: {decision.reason}")


def _require_raw_machine_access(snapshot, access: ScopedStoreAccess, capability: str) -> None:
    workspace_ids = _workspace_ids(snapshot)
    if workspace_ids != (access.workspace_id,):
        if access.workspace_id not in workspace_ids:
            raise PermissionError("scoped store workspace does not own this machine")
        raise PermissionError("raw store access is forbidden for multi-workspace machines; use scoped projections")
    if access.scope_id != "root":
        raise PermissionError("raw store access requires root scope; use scoped projections for child scopes")
    _authorize(snapshot, access, capability, request_scope_id="root")


def _effect_bindings(snapshot) -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for record_type, document, evidence_id in _active_authority_records(snapshot):
        if record_type != "effect_proposal":
            continue
        effect_id = str(document.get("effect_id") or "")
        if not effect_id:
            continue
        current = bindings.get(effect_id)
        if current is not None and (
            current["workspace_id"] != document.get("workspace_id")
            or current["scope_id"] != document.get("scope_id")
        ):
            raise ValueError(f"conflicting scoped effect bindings: {effect_id}")
        bindings[effect_id] = {
            "effect_id": effect_id,
            "workspace_id": str(document.get("workspace_id") or ""),
            "scope_id": str(document.get("scope_id") or ""),
            "binding_evidence_id": evidence_id,
        }
    return bindings


def _effect_visible(snapshot, access: ScopedStoreAccess, effect_id: str) -> bool:
    binding = _effect_bindings(snapshot).get(effect_id)
    if binding is None or binding["workspace_id"] != access.workspace_id:
        return False
    try:
        if not scope_flow_allowed(snapshot.calculus.get("scope_state") or {}, access.scope_id, binding["scope_id"]):
            return False
        _authorize(snapshot, access, STORE_CAPABILITIES["effects_read"], request_scope_id=binding["scope_id"])
    except (KeyError, PermissionError):
        return False
    return True


class ScopedStoreView:
    """Read-only v0.53 persistence facade that fails closed on scope ambiguity."""

    def __init__(self, store, access: ScopedStoreAccess):
        self.store = store
        self.access = access

    def load_snapshot(self, machine_id: str):
        snapshot = self.store.load_snapshot(machine_id)
        _require_raw_machine_access(snapshot, self.access, STORE_CAPABILITIES["snapshot_read"])
        return deepcopy(snapshot)

    def load_events(self, machine_id: str, after_sequence: int = 0):
        snapshot = self.store.load_snapshot(machine_id)
        _require_raw_machine_access(snapshot, self.access, STORE_CAPABILITIES["events_read"])
        return deepcopy(self.store.load_events(machine_id, after_sequence))

    def load_checkpoint(self, machine_id: str, checkpoint_id: str):
        snapshot = self.store.load_snapshot(machine_id)
        _require_raw_machine_access(snapshot, self.access, STORE_CAPABILITIES["checkpoint_read"])
        return deepcopy(self.store.load_checkpoint(machine_id, checkpoint_id))

    def list_unfinished(self) -> list[str]:
        visible: list[str] = []
        for machine_id in self.store.list_unfinished():
            try:
                snapshot = self.store.load_snapshot(machine_id)
                _require_raw_machine_access(snapshot, self.access, STORE_CAPABILITIES["unfinished_list"])
            except (KeyError, PermissionError):
                continue
            visible.append(machine_id)
        return sorted(visible)

    def load_effect(self, machine_id: str, effect_id: str) -> EffectRecord:
        snapshot = self.store.load_snapshot(machine_id)
        if not _effect_visible(snapshot, self.access, effect_id):
            raise PermissionError("effect is outside scoped store access")
        return deepcopy(self.store.load_effect(machine_id, effect_id))

    def find_effect_by_idempotency(self, machine_id: str, idempotency_key: str) -> EffectRecord | None:
        snapshot = self.store.load_snapshot(machine_id)
        record = self.store.find_effect_by_idempotency(machine_id, idempotency_key)
        if record is None:
            return None
        if not _effect_visible(snapshot, self.access, record.spec.effect_id):
            return None
        return deepcopy(record)

    def list_effects(self, machine_id: str) -> list[EffectRecord]:
        snapshot = self.store.load_snapshot(machine_id)
        return [
            deepcopy(record)
            for record in self.store.list_effects(machine_id)
            if _effect_visible(snapshot, self.access, record.spec.effect_id)
        ]


__all__ = [
    "SCOPED_STORE_CONTRACT_ID",
    "SCOPED_STORE_CONTRACT_VERSION",
    "SCOPED_STORE_STABILITY",
    "STORE_CAPABILITIES",
    "ScopedStoreAccess",
    "ScopedStoreView",
    "scoped_store_contract",
]
