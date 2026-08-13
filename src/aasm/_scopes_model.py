from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable


SCOPE_CONTRACT_ID = "aasm.scopes.v1"
SCOPE_CONTRACT_VERSION = "0.1.0"
ROOT_SCOPE_ID = "root"

SCOPE_KINDS = {
    "ROOT",
    "STRATEGY",
    "ARCHITECTURE",
    "IMPLEMENTATION",
    "WORKSTREAM",
    "CUSTOM",
}
SCOPE_STATUSES = {"ACTIVE", "SUSPENDED", "NEEDS_REVALIDATION", "INVALIDATED", "RETIRED"}
INHERITANCE_POLICIES = {"INHERIT", "ISOLATED"}
OVERRIDE_POLICIES = {"EXPLICIT", "DENY"}
DEPENDENCY_RELATIONS = {"AUTHORIZES", "CONSTRAINS", "DEPENDS_ON", "REFINES"}
INVALIDATION_POLICIES = {"NONE", "REVALIDATE", "INVALIDATE"}


def _unique(values: Iterable[str]) -> list[str]:
    return sorted({str(value) for value in values})


@dataclass
class DecisionScope:
    scope_id: str
    name: str = ""
    kind: str = "CUSTOM"
    parent_scope_id: str | None = ROOT_SCOPE_ID
    status: str = "ACTIVE"
    inheritance: str = "INHERIT"
    override_policy: str = "EXPLICIT"
    created_sequence: int = 0
    updated_sequence: int = 0
    suspended_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.scope_id:
            raise ValueError("scope_id is required")
        if not self.name:
            self.name = self.scope_id
        if self.kind not in SCOPE_KINDS:
            raise ValueError(f"invalid scope kind: {self.kind}")
        if self.status not in SCOPE_STATUSES:
            raise ValueError(f"invalid scope status: {self.status}")
        if self.inheritance not in INHERITANCE_POLICIES:
            raise ValueError(f"invalid inheritance policy: {self.inheritance}")
        if self.override_policy not in OVERRIDE_POLICIES:
            raise ValueError(f"invalid override policy: {self.override_policy}")
        if int(self.created_sequence) < 0:
            raise ValueError("created_sequence must be non-negative")
        if int(self.updated_sequence) < 0:
            raise ValueError("updated_sequence must be non-negative")
        if self.scope_id == ROOT_SCOPE_ID:
            self.name = self.name or "Root"
            self.kind = "ROOT"
            self.parent_scope_id = None
            self.status = "ACTIVE"
            self.inheritance = "ISOLATED"
            self.override_policy = "DENY"
            self.suspended_reason = None
        elif not self.parent_scope_id:
            raise ValueError("non-root scopes require parent_scope_id")

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value.pop("updated_sequence", None)
        return value


@dataclass
class ScopeDependency:
    dependency_id: str
    upstream_scope_id: str
    downstream_scope_id: str
    relation: str = "DEPENDS_ON"
    invalidation_policy: str = "REVALIDATE"
    evidence_ids: list[str] = field(default_factory=list)
    created_sequence: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.dependency_id:
            raise ValueError("dependency_id is required")
        if not self.upstream_scope_id or not self.downstream_scope_id:
            raise ValueError("scope dependency endpoints are required")
        if self.upstream_scope_id == self.downstream_scope_id:
            raise ValueError("scope dependency cannot be self-referential")
        if self.relation not in DEPENDENCY_RELATIONS:
            raise ValueError(f"invalid scope dependency relation: {self.relation}")
        if self.invalidation_policy not in INVALIDATION_POLICIES:
            raise ValueError(
                f"invalid scope invalidation policy: {self.invalidation_policy}"
            )
        if int(self.created_sequence) < 0:
            raise ValueError("created_sequence must be non-negative")
        self.evidence_ids = _unique(self.evidence_ids)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def root_scope_record() -> dict[str, Any]:
    return DecisionScope(
        scope_id=ROOT_SCOPE_ID,
        name="Root",
        kind="ROOT",
        parent_scope_id=None,
        status="ACTIVE",
        inheritance="ISOLATED",
        override_policy="DENY",
        metadata={"canonical": True, "legacy_flat_default": True},
    ).to_dict()


def default_scope_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "contract_id": SCOPE_CONTRACT_ID,
        "contract_version": SCOPE_CONTRACT_VERSION,
        "root_scope_id": ROOT_SCOPE_ID,
        "records": {ROOT_SCOPE_ID: root_scope_record()},
        "dependencies": {},
        "migration": {
            "legacy_flat_state_migrated": False,
            "migrated_sequence": None,
        },
    }


def normalize_scope_state(raw: dict[str, Any] | None) -> dict[str, Any]:
    out = default_scope_state()
    if raw:
        for key, value in raw.items():
            if key in {"records", "dependencies", "migration"}:
                continue
            out[key] = deepcopy(value)
        out["records"].update(deepcopy(raw.get("records") or {}))
        out["dependencies"].update(deepcopy(raw.get("dependencies") or {}))
        migration = deepcopy(raw.get("migration") or {})
        # Accept the short-lived draft field names if encountered in a local
        # pre-release snapshot, but normalize to the published contract.
        if "legacy_flat_migrated" in migration:
            migration.setdefault(
                "legacy_flat_state_migrated",
                bool(migration.pop("legacy_flat_migrated")),
            )
        if "migration_sequence" in migration:
            migration.setdefault("migrated_sequence", migration.pop("migration_sequence"))
        out["migration"].update(migration)
    out["schema_version"] = 1
    out["contract_id"] = SCOPE_CONTRACT_ID
    out["contract_version"] = SCOPE_CONTRACT_VERSION
    out["root_scope_id"] = ROOT_SCOPE_ID
    out["records"][ROOT_SCOPE_ID] = root_scope_record()
    return out


def scope_id_from(record: dict[str, Any] | None) -> str:
    raw = record or {}
    scope = raw.get("scope") if isinstance(raw, dict) else None
    if isinstance(scope, dict) and scope.get("scope_id"):
        return str(scope["scope_id"])
    if isinstance(raw, dict) and raw.get("scope_id"):
        return str(raw["scope_id"])
    metadata = raw.get("metadata") if isinstance(raw, dict) else None
    if isinstance(metadata, dict) and metadata.get("scope_id"):
        return str(metadata["scope_id"])
    return ROOT_SCOPE_ID


scope_id_from_record = scope_id_from


def with_scope(scope: dict[str, Any] | None, scope_id: str) -> dict[str, Any]:
    out = deepcopy(scope or {})
    out["scope_id"] = str(scope_id)
    return out

__all__ = [name for name in globals() if not name.startswith("_")]
