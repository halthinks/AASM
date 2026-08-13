from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Iterable

from .scopes import (
    ROOT_SCOPE_ID,
    assert_scope_calculus_invariants,
    default_scope_state,
    effective_scope_decisions,
    effective_scope_values,
    normalize_scope_active_models,
    normalize_scope_state,
    scope_ancestors,
    scope_id_from,
    scope_id_from_record,
    scope_decision_values,
    scope_reachable,
    scoped_subject_key,
    validate_scope_state,
    with_scope,
)


DECISION_KINDS = {"ROOT", "PINNED", "EXPLICIT", "DERIVED"}
DECISION_STATUSES = {"PROPOSED", "ACTIVE", "SUSPENDED", "SUPERSEDED", "INVALIDATED", "REJECTED", "HISTORICAL"}
OBLIGATION_STATUSES = {
    "AVAILABLE", "ENABLED", "IN_PROGRESS", "VERIFYING", "VERIFIED", "COMMITTED",
    "BLOCKED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE",
}
OBLIGATION_TRANSITIONS = {
    "AVAILABLE": {"ENABLED", "BLOCKED", "LOCKED", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "ENABLED": {"IN_PROGRESS", "BLOCKED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "IN_PROGRESS": {"VERIFYING", "BLOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "VERIFYING": {"VERIFIED", "BLOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "VERIFIED": {"COMMITTED", "NEEDS_REVALIDATION", "SUPERSEDED"},
    "COMMITTED": {"NEEDS_REVALIDATION", "SUPERSEDED"},
    "BLOCKED": {"AVAILABLE", "ENABLED", "LOCKED", "NEEDS_REVALIDATION", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "LOCKED": {"AVAILABLE", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "NEEDS_REVALIDATION": {"AVAILABLE", "ENABLED", "VERIFYING", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"},
    "REJECTED": set(),
    "SUPERSEDED": set(),
    "IMPOSSIBLE": set(),
}
TERMINAL_OBLIGATION_STATUSES = {"COMMITTED", "REJECTED", "SUPERSEDED", "IMPOSSIBLE"}
EXPLANATION_STATUSES = {"PROPOSED", "VALIDATED", "PROVEN", "REJECTED"}
CONSTRAINT_STATUSES = {"PROPOSED", "ACTIVE", "SOFT", "EXPIRED", "SUPERSEDED", "REJECTED"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def content_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _unique(values: Iterable[str]) -> list[str]:
    return sorted(set(str(value) for value in values))


def default_fairness_policy() -> dict[str, Any]:
    return {
        "max_hidden_epochs": 3,
        "max_lock_age_epochs": 3,
        "max_lock_count": 3,
        "max_deferral_epochs": 3,
        "enforcement": "BLOCK_PLANNING",
        "review_batch_size": 1,
    }


def default_calculus_state() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "epoch": 0,
        "active_model": {},
        "decisions": {},
        "decision_edges": [],
        "obligations": {},
        "obligation_edges": [],
        "locks": {},
        "conflicts": {},
        "explanations": {},
        "constraints": {},
        "fairness": {"policy": default_fairness_policy(), "records": {}},
        "search_local": {},
        "scope_state": default_scope_state(),
        "scope_active_models": {ROOT_SCOPE_ID: {}},
    }


def normalize_calculus_state(raw: dict[str, Any] | None) -> dict[str, Any]:
    base = default_calculus_state()
    if not raw:
        return base
    out = deepcopy(base)
    for key, value in raw.items():
        if key == "fairness":
            fairness = deepcopy(base["fairness"])
            fairness.update(deepcopy(value or {}))
            policy = deepcopy(default_fairness_policy())
            policy.update(deepcopy(fairness.get("policy") or {}))
            fairness["policy"] = policy
            fairness.setdefault("records", {})
            out["fairness"] = fairness
        else:
            out[key] = deepcopy(value)
    out["scope_state"] = normalize_scope_state(out.get("scope_state"))
    legacy_root_model = deepcopy(out.get("active_model") or {})
    out["scope_active_models"] = normalize_scope_active_models(
        out["scope_state"],
        out.get("scope_active_models"),
        legacy_root_model,
    )
    out["scope_active_models"][ROOT_SCOPE_ID] = legacy_root_model
    out["active_model"] = deepcopy(legacy_root_model)
    for collection in (
        "decisions",
        "obligations",
        "locks",
        "conflicts",
        "explanations",
        "constraints",
    ):
        for identity, record in list(out.get(collection, {}).items()):
            scope_id = scope_id_from(record)
            out[collection][identity] = deepcopy(record)
            out[collection][identity]["scope"] = with_scope(
                out[collection][identity].get("scope"), scope_id
            )
    return out


@dataclass
class DecisionLiteral:
    subject: str
    op: str
    value: Any
    decision_id: str | None = None

    def __post_init__(self):
        if not self.subject:
            raise ValueError("decision literal subject is required")
        if self.op not in {"EQ", "NEQ"}:
            raise ValueError("decision literal op must be EQ or NEQ")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionRecord:
    decision_id: str
    subject: str
    value: Any
    kind: str = "EXPLICIT"
    status: str = "PROPOSED"
    level: int = 0
    parent_ids: list[str] = field(default_factory=list)
    antecedent_constraint_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    plan_node_ids: list[str] = field(default_factory=list)
    scope: dict[str, Any] = field(default_factory=dict)
    pinned: bool = False
    created_sequence: int = 0
    activated_sequence: int | None = None
    invalidated_by_conflict_id: str | None = None
    superseded_by: str | None = None

    def __post_init__(self):
        if not self.decision_id or not self.subject:
            raise ValueError("decision_id and subject are required")
        if self.kind not in DECISION_KINDS:
            raise ValueError(f"invalid decision kind: {self.kind}")
        if self.status not in DECISION_STATUSES:
            raise ValueError(f"invalid decision status: {self.status}")
        if self.level < 0:
            raise ValueError("decision level must be non-negative")
        self.parent_ids = _unique(self.parent_ids)
        self.antecedent_constraint_ids = _unique(self.antecedent_constraint_ids)
        self.evidence_ids = _unique(self.evidence_ids)
        self.plan_node_ids = _unique(self.plan_node_ids)
        if self.kind in {"ROOT", "PINNED"}:
            self.level = 0
            self.pinned = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ObligationRecord:
    obligation_id: str
    statement: str
    activation_condition: dict[str, Any] = field(default_factory=lambda: {"const": True})
    status: str = "AVAILABLE"
    dependencies: list[str] = field(default_factory=list)
    decision_dependencies: list[str] = field(default_factory=list)
    plan_node_ids: list[str] = field(default_factory=list)
    required_evidence_types: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    artifact_ids: list[str] = field(default_factory=list)
    lock_ids: list[str] = field(default_factory=list)
    persistent: bool = True
    mandatory: bool = True
    attempt_count: int = 0
    created_sequence: int = 0
    last_state_change_sequence: int = 0
    disposition_reason: str | None = None
    scope: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.obligation_id or not self.statement:
            raise ValueError("obligation_id and statement are required")
        if self.status not in OBLIGATION_STATUSES:
            raise ValueError(f"invalid obligation status: {self.status}")
        if self.attempt_count < 0:
            raise ValueError("attempt_count must be non-negative")
        self.dependencies = _unique(self.dependencies)
        self.decision_dependencies = _unique(self.decision_dependencies)
        self.plan_node_ids = _unique(self.plan_node_ids)
        self.required_evidence_types = _unique(self.required_evidence_types)
        self.evidence_ids = _unique(self.evidence_ids)
        self.artifact_ids = _unique(self.artifact_ids)
        self.lock_ids = _unique(self.lock_ids)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LockRecord:
    lock_id: str
    obligation_id: str
    condition: dict[str, Any]
    reason: str
    origin_decision_id: str
    status: str = "ACTIVE"
    created_epoch: int = 0
    broken_epoch: int | None = None
    evidence_ids: list[str] = field(default_factory=list)
    scope: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not all([self.lock_id, self.obligation_id, self.reason, self.origin_decision_id]):
            raise ValueError("lock_id, obligation_id, reason, and origin_decision_id are required")
        if self.status not in {"ACTIVE", "BROKEN", "EXPIRED", "SUPERSEDED"}:
            raise ValueError(f"invalid lock status: {self.status}")
        self.evidence_ids = _unique(self.evidence_ids)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ConflictRecord:
    conflict_id: str
    kind: str
    evidence_ids: list[str]
    active_model_snapshot: dict[str, str] = field(default_factory=dict)
    decision_levels: dict[str, int] = field(default_factory=dict)
    scope: dict[str, Any] = field(default_factory=dict)
    status: str = "OPEN"
    observed_at_obligation_id: str | None = None
    implicated_decision_ids: list[str] = field(default_factory=list)
    explanation_ids: list[str] = field(default_factory=list)
    learned_constraint_ids: list[str] = field(default_factory=list)
    created_sequence: int = 0
    resolved_sequence: int | None = None
    backjump: dict[str, Any] | None = None

    def __post_init__(self):
        if not self.conflict_id or not self.evidence_ids:
            raise ValueError("conflict_id and evidence_ids are required")
        if self.kind not in {"ASSUMPTION_CONFLICT", "EVIDENCE_CONFLICT", "ROOT_CONFLICT", "POLICY_CONFLICT"}:
            raise ValueError(f"invalid conflict kind: {self.kind}")
        if self.status not in {"OPEN", "EXPLAINED", "LEARNED", "RESOLVED", "REJECTED"}:
            raise ValueError(f"invalid conflict status: {self.status}")
        self.evidence_ids = _unique(self.evidence_ids)
        self.implicated_decision_ids = _unique(self.implicated_decision_ids)
        self.explanation_ids = _unique(self.explanation_ids)
        self.learned_constraint_ids = _unique(self.learned_constraint_ids)

    def to_dict(self) -> dict[str, Any]:
        raw = asdict(self)
        raw["candidate_snapshot_hash"] = content_hash(self.active_model_snapshot)
        return raw


@dataclass
class ExplanationRecord:
    explanation_id: str
    conflict_id: str
    assumption_literals: list[dict[str, Any]]
    evidence_ids: list[str]
    method: str = "DEPENDENCY_TRACE"
    status: str = "PROPOSED"
    minimality: str = "NONE"
    guard: dict[str, Any] = field(default_factory=lambda: {"const": True})
    dependency_edges: list[dict[str, str]] = field(default_factory=list)
    certificate: dict[str, Any] = field(default_factory=dict)
    scope: dict[str, Any] = field(default_factory=dict)
    created_sequence: int = 0

    def __post_init__(self):
        if not self.explanation_id or not self.conflict_id:
            raise ValueError("explanation_id and conflict_id are required")
        if self.status not in EXPLANATION_STATUSES:
            raise ValueError(f"invalid explanation status: {self.status}")
        if self.method not in {"DEPENDENCY_TRACE", "PROOF", "DELTA_DEBUGGING", "REPRODUCTION", "MANUAL_REVIEW"}:
            raise ValueError(f"invalid explanation method: {self.method}")
        if self.minimality not in {"NONE", "IRREDUCIBLE", "PROVEN_MINIMAL"}:
            raise ValueError(f"invalid explanation minimality: {self.minimality}")
        self.assumption_literals = [DecisionLiteral(**deepcopy(raw)).to_dict() for raw in self.assumption_literals]
        if not self.assumption_literals and self.status != "REJECTED":
            raise ValueError("non-rejected explanation requires at least one assumption literal")
        self.evidence_ids = _unique(self.evidence_ids)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class LearnedConstraint:
    constraint_id: str
    body: list[dict[str, Any]]
    source_conflict_id: str
    source_explanation_id: str
    evidence_ids: list[str]
    guard: dict[str, Any] = field(default_factory=lambda: {"const": True})
    strength: str = "HARD"
    status: str = "PROPOSED"
    validation: str = "VALIDATED"
    scope: dict[str, Any] = field(default_factory=dict)
    created_sequence: int = 0
    reuse_count: int = 0
    superseded_by: str | None = None

    def __post_init__(self):
        if not all([self.constraint_id, self.source_conflict_id, self.source_explanation_id]):
            raise ValueError("constraint and source IDs are required")
        self.body = [DecisionLiteral(**deepcopy(raw)).to_dict() for raw in self.body]
        if not self.body:
            raise ValueError("learned no-good requires a non-empty body")
        if self.strength not in {"HARD", "SOFT"}:
            raise ValueError("constraint strength must be HARD or SOFT")
        if self.status not in CONSTRAINT_STATUSES:
            raise ValueError(f"invalid constraint status: {self.status}")
        if self.validation not in {"PROPOSED", "VALIDATED", "PROVEN", "HEURISTIC"}:
            raise ValueError(f"invalid constraint validation: {self.validation}")
        self.evidence_ids = _unique(self.evidence_ids)
        if self.reuse_count < 0:
            raise ValueError("reuse_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FairnessPolicy:
    max_hidden_epochs: int = 3
    max_lock_age_epochs: int = 3
    max_lock_count: int = 3
    max_deferral_epochs: int = 3
    enforcement: str = "BLOCK_PLANNING"
    review_batch_size: int = 1

    def __post_init__(self):
        for name in ("max_hidden_epochs", "max_lock_age_epochs", "max_lock_count", "max_deferral_epochs", "review_batch_size"):
            if int(getattr(self, name)) < 1:
                raise ValueError(f"{name} must be positive")
        if self.enforcement not in {"WARN", "BLOCK_PLANNING"}:
            raise ValueError("fairness enforcement must be WARN or BLOCK_PLANNING")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RecoveryDecision:
    planner_id: str
    action: str
    conflict_id: str | None = None
    constraint_id: str | None = None
    reason: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.planner_id or not self.reason:
            raise ValueError("planner_id and reason are required")
        if self.action not in {"BACKJUMP", "RESTART_SEARCH"}:
            raise ValueError("recovery action must be BACKJUMP or RESTART_SEARCH")
        if self.action == "BACKJUMP" and not self.conflict_id:
            raise ValueError("BACKJUMP requires conflict_id")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

__all__ = [name for name in globals() if not name.startswith("_")]
