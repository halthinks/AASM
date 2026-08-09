from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import hashlib
import json
from typing import Any, Iterable


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


def decision_values(calculus: dict[str, Any], active_model: dict[str, str] | None = None) -> dict[str, Any]:
    model = active_model if active_model is not None else calculus.get("active_model", {})
    decisions = calculus.get("decisions", {})
    out: dict[str, Any] = {}
    for subject, decision_id in model.items():
        record = decisions.get(decision_id)
        if record is not None and record.get("status") == "ACTIVE":
            out[subject] = record.get("value")
    return out


def literal_holds(literal: dict[str, Any], values: dict[str, Any]) -> bool:
    item = DecisionLiteral(**deepcopy(literal))
    if item.subject not in values:
        return False
    equal = values[item.subject] == item.value
    return equal if item.op == "EQ" else not equal


def condition_holds(condition: dict[str, Any] | None, values: dict[str, Any]) -> bool:
    if condition is None:
        return True
    if "const" in condition:
        return bool(condition["const"])
    if "decision" in condition:
        return literal_holds(condition["decision"], values)
    if "all" in condition:
        return all(condition_holds(item, values) for item in condition["all"])
    if "any" in condition:
        return any(condition_holds(item, values) for item in condition["any"])
    if "not" in condition:
        return not condition_holds(condition["not"], values)
    raise ValueError(f"unknown condition form: {sorted(condition)}")


def constraint_violated(constraint: dict[str, Any], values: dict[str, Any]) -> bool:
    if constraint.get("status") != "ACTIVE" or constraint.get("strength") != "HARD":
        return False
    return condition_holds(constraint.get("guard"), values) and all(
        literal_holds(literal, values) for literal in constraint.get("body", [])
    )


def violated_hard_constraints(calculus: dict[str, Any], values: dict[str, Any]) -> list[str]:
    return sorted(
        constraint_id
        for constraint_id, constraint in calculus.get("constraints", {}).items()
        if constraint_violated(constraint, values)
    )


def _literal_key(literal: dict[str, Any]) -> str:
    return canonical_json({"subject": literal["subject"], "op": literal["op"], "value": literal.get("value")})


def validate_explanation(calculus: dict[str, Any], explanation: dict[str, Any]) -> None:
    record = ExplanationRecord(**deepcopy(explanation))
    conflict = calculus.get("conflicts", {}).get(record.conflict_id)
    if conflict is None:
        raise KeyError(record.conflict_id)
    evidence = set(conflict.get("evidence_ids", []))
    if not set(record.evidence_ids).issubset(evidence):
        raise ValueError("explanation evidence must be drawn from its conflict")
    seen: dict[str, str] = {}
    snapshot = conflict.get("active_model_snapshot", {})
    decisions = calculus.get("decisions", {})
    for raw in record.assumption_literals:
        literal = DecisionLiteral(**raw)
        if literal.decision_id is None:
            raise ValueError("explanation literals require decision_id provenance")
        decision = decisions.get(literal.decision_id)
        if decision is None:
            raise KeyError(literal.decision_id)
        if snapshot.get(literal.subject) != literal.decision_id:
            raise ValueError("explanation literal was not active in the conflict snapshot")
        if decision.get("subject") != literal.subject or decision.get("value") != literal.value:
            raise ValueError("explanation literal does not match its decision")
        if literal.op != "EQ":
            raise ValueError("conflict explanations must name active assignment literals with EQ")
        prior = seen.get(literal.subject)
        key = _literal_key(raw)
        if prior is not None and prior != key:
            raise ValueError("explanation contains contradictory literals for one subject")
        seen[literal.subject] = key
    if record.status == "PROVEN" and not record.certificate:
        raise ValueError("PROVEN explanation requires a certificate")


def project_constraint(
    calculus: dict[str, Any],
    explanation: dict[str, Any],
    constraint_id: str,
    *,
    requested_strength: str = "HARD",
    created_sequence: int = 0,
) -> dict[str, Any]:
    validate_explanation(calculus, explanation)
    conflict = calculus["conflicts"][explanation["conflict_id"]]
    status = explanation.get("status")
    hard_allowed = (
        conflict.get("kind") == "ASSUMPTION_CONFLICT"
        and status in {"VALIDATED", "PROVEN"}
    )
    strength = "HARD" if requested_strength == "HARD" and hard_allowed else "SOFT"
    validation = "PROVEN" if status == "PROVEN" else ("VALIDATED" if status == "VALIDATED" else "HEURISTIC")
    body = sorted(
        [DecisionLiteral(**raw).to_dict() for raw in explanation.get("assumption_literals", [])],
        key=_literal_key,
    )
    record = LearnedConstraint(
        constraint_id=constraint_id,
        body=body,
        guard=deepcopy(explanation.get("guard") or {"const": True}),
        strength=strength,
        status="ACTIVE" if strength == "HARD" else "SOFT",
        validation=validation,
        source_conflict_id=explanation["conflict_id"],
        source_explanation_id=explanation["explanation_id"],
        evidence_ids=list(explanation.get("evidence_ids", [])),
        scope=deepcopy(explanation.get("scope") or {}),
        created_sequence=created_sequence,
    )
    return record.to_dict()


def _active_decision_children(calculus: dict[str, Any]) -> dict[str, set[str]]:
    children: dict[str, set[str]] = {decision_id: set() for decision_id in calculus.get("decisions", {})}
    for decision_id, decision in calculus.get("decisions", {}).items():
        if decision.get("status") != "ACTIVE":
            continue
        for parent_id in decision.get("parent_ids", []):
            children.setdefault(parent_id, set()).add(decision_id)
    for edge in calculus.get("decision_edges", []):
        if edge.get("relation") in {"DEPENDS_ON", "DERIVES"}:
            children.setdefault(edge.get("src"), set()).add(edge.get("dst"))
    return children


def decision_descendants(calculus: dict[str, Any], root_id: str) -> set[str]:
    children = _active_decision_children(calculus)
    seen = {root_id}
    todo = [root_id]
    while todo:
        current = todo.pop()
        for child in children.get(current, set()):
            if child not in seen:
                seen.add(child)
                todo.append(child)
    return seen


def causal_roots(calculus: dict[str, Any], decision_id: str) -> set[str]:
    decisions = calculus.get("decisions", {})
    seen: set[str] = set()

    def visit(current_id: str) -> set[str]:
        if current_id in seen:
            return set()
        seen.add(current_id)
        current = decisions.get(current_id)
        if current is None:
            return set()
        parents = [parent for parent in current.get("parent_ids", []) if parent in decisions]
        if current.get("kind") != "DERIVED" or not parents:
            return {current_id}
        roots: set[str] = set()
        for parent in parents:
            roots.update(visit(parent))
        return roots

    return visit(decision_id)


def compute_backjump(calculus: dict[str, Any], conflict_id: str, explanation_id: str | None = None) -> dict[str, Any]:
    conflict = calculus.get("conflicts", {}).get(conflict_id)
    if conflict is None:
        raise KeyError(conflict_id)
    if explanation_id is None:
        candidates = [
            item for item in conflict.get("explanation_ids", [])
            if calculus.get("explanations", {}).get(item, {}).get("status") in {"VALIDATED", "PROVEN"}
        ]
        if not candidates:
            raise ValueError("backjump requires a validated explanation")
        explanation_id = sorted(candidates)[0]
    explanation = calculus.get("explanations", {}).get(explanation_id)
    if explanation is None:
        raise KeyError(explanation_id)
    validate_explanation(calculus, explanation)

    root_ids: set[str] = set()
    for literal in explanation.get("assumption_literals", []):
        root_ids.update(causal_roots(calculus, literal["decision_id"]))
    decisions = calculus.get("decisions", {})
    revisable = [
        decision_id for decision_id in root_ids
        if decision_id in decisions
        and decisions[decision_id].get("status") == "ACTIVE"
        and not decisions[decision_id].get("pinned", False)
        and decisions[decision_id].get("kind") not in {"ROOT", "PINNED"}
    ]
    if not revisable:
        return {
            "conflict_id": conflict_id,
            "explanation_id": explanation_id,
            "pivot_decision_id": None,
            "invalidated_decision_ids": [],
            "impacted_obligation_ids": [],
            "impacted_plan_node_ids": [],
            "reason": "no revisable causal pivot",
        }

    closures = {decision_id: decision_descendants(calculus, decision_id) for decision_id in revisable}
    pivot = sorted(
        revisable,
        key=lambda decision_id: (
            -int(decisions[decision_id].get("level", 0)),
            len(closures[decision_id]),
            decision_id,
        ),
    )[0]
    invalidated = closures[pivot]
    obligations = calculus.get("obligations", {})
    impacted_obligations = sorted(
        obligation_id
        for obligation_id, obligation in obligations.items()
        if set(obligation.get("decision_dependencies", [])) & invalidated
    )
    plan_nodes: set[str] = set(decisions[pivot].get("plan_node_ids", []))
    for decision_id in invalidated:
        plan_nodes.update(decisions.get(decision_id, {}).get("plan_node_ids", []))
    for obligation_id in impacted_obligations:
        plan_nodes.update(obligations[obligation_id].get("plan_node_ids", []))
    return {
        "conflict_id": conflict_id,
        "explanation_id": explanation_id,
        "pivot_decision_id": pivot,
        "invalidated_decision_ids": sorted(invalidated),
        "impacted_obligation_ids": impacted_obligations,
        "impacted_plan_node_ids": sorted(plan_nodes),
        "reason": "deepest revisable causal pivot with smallest dependent closure",
    }


def apply_backjump(calculus: dict[str, Any], plan: dict[str, Any], *, sequence: int = 0) -> dict[str, Any]:
    out = normalize_calculus_state(calculus)
    conflict = out["conflicts"][plan["conflict_id"]]
    invalidated = set(plan.get("invalidated_decision_ids", []))
    for decision_id in invalidated:
        decision = out["decisions"][decision_id]
        decision["status"] = "INVALIDATED"
        decision["invalidated_by_conflict_id"] = plan["conflict_id"]
    out["active_model"] = {
        subject: decision_id
        for subject, decision_id in out.get("active_model", {}).items()
        if decision_id not in invalidated
    }
    for obligation_id in plan.get("impacted_obligation_ids", []):
        obligation = out["obligations"][obligation_id]
        if obligation.get("status") not in {"REJECTED", "SUPERSEDED", "IMPOSSIBLE"}:
            obligation["status"] = "NEEDS_REVALIDATION"
            obligation["last_state_change_sequence"] = sequence
    conflict["status"] = "RESOLVED"
    conflict["resolved_sequence"] = sequence
    conflict["backjump"] = deepcopy(plan)
    out["epoch"] = int(out.get("epoch", 0)) + 1
    out["search_local"] = {}
    return out


def reevaluate_locks(calculus: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    out = normalize_calculus_state(calculus)
    values = decision_values(out)
    broken: list[str] = []
    for lock_id, lock in out.get("locks", {}).items():
        if lock.get("status") != "ACTIVE":
            continue
        if not condition_holds(lock.get("condition"), values):
            lock["status"] = "BROKEN"
            lock["broken_epoch"] = int(out.get("epoch", 0))
            broken.append(lock_id)
    for obligation in out.get("obligations", {}).values():
        active_locks = [
            lock_id for lock_id in obligation.get("lock_ids", [])
            if out.get("locks", {}).get(lock_id, {}).get("status") == "ACTIVE"
        ]
        if obligation.get("status") == "LOCKED" and not active_locks:
            obligation["status"] = "AVAILABLE"
    return out, sorted(broken)


def audit_fairness(calculus: dict[str, Any]) -> tuple[dict[str, Any], dict[str, list[str]]]:
    out = normalize_calculus_state(calculus)
    epoch = int(out.get("epoch", 0))
    policy = FairnessPolicy(**deepcopy(out["fairness"]["policy"]))
    records = out["fairness"].setdefault("records", {})
    values = decision_values(out)
    due: list[str] = []
    overdue: list[str] = []
    for obligation_id, obligation in out.get("obligations", {}).items():
        record = records.setdefault(
            obligation_id,
            {
                "created_epoch": epoch,
                "last_considered_epoch": epoch,
                "last_enabled_epoch": None,
                "last_reviewed_epoch": None,
                "current_lock_start_epoch": None,
                "lock_count": 0,
                "hidden_epochs": 0,
                "continuous_lock_epochs": 0,
                "fairness_status": "NORMAL",
                "explicit_deferral_until_epoch": None,
            },
        )
        if obligation.get("status") in TERMINAL_OBLIGATION_STATUSES or not obligation.get("persistent", True):
            record["fairness_status"] = "NORMAL"
            continue
        if obligation.get("status") in {"ENABLED", "IN_PROGRESS", "VERIFYING", "VERIFIED", "COMMITTED"}:
            record["last_enabled_epoch"] = epoch
            record["last_considered_epoch"] = epoch
            record["hidden_epochs"] = 0
            record["fairness_status"] = "NORMAL"
            continue
        active_locks = [
            lock_id for lock_id in obligation.get("lock_ids", [])
            if out.get("locks", {}).get(lock_id, {}).get("status") == "ACTIVE"
        ]
        if active_locks:
            starts = [int(out["locks"][lock_id].get("created_epoch", epoch)) for lock_id in active_locks]
            record["current_lock_start_epoch"] = min(starts)
            record["continuous_lock_epochs"] = epoch - record["current_lock_start_epoch"]
            record["lock_count"] = max(int(record.get("lock_count", 0)), len(obligation.get("lock_ids", [])))
        else:
            record["current_lock_start_epoch"] = None
            record["continuous_lock_epochs"] = 0
        record["hidden_epochs"] = epoch - int(record.get("last_considered_epoch", record["created_epoch"]))
        deferred_until = record.get("explicit_deferral_until_epoch")
        if deferred_until is not None and epoch <= int(deferred_until):
            record["fairness_status"] = "NORMAL"
            continue
        score_due = (
            record["hidden_epochs"] >= policy.max_hidden_epochs
            or record["continuous_lock_epochs"] >= policy.max_lock_age_epochs
            or record["lock_count"] >= policy.max_lock_count
        )
        score_overdue = (
            record["hidden_epochs"] > policy.max_hidden_epochs
            or record["continuous_lock_epochs"] > policy.max_lock_age_epochs
            or record["lock_count"] > policy.max_lock_count
        )
        if score_overdue:
            record["fairness_status"] = "OVERDUE"
            overdue.append(obligation_id)
        elif score_due:
            record["fairness_status"] = "DUE"
            due.append(obligation_id)
        else:
            record["fairness_status"] = "NORMAL"
    return out, {"due": sorted(due), "overdue": sorted(overdue)}


def candidate_exposes_overdue(
    calculus: dict[str, Any],
    values: dict[str, Any],
    *,
    previous_values: dict[str, Any] | None = None,
) -> bool:
    overdue = [
        obligation_id for obligation_id, record in calculus.get("fairness", {}).get("records", {}).items()
        if record.get("fairness_status") == "OVERDUE"
    ]
    if not overdue:
        return True
    previous_values = previous_values or {}
    for obligation_id in overdue:
        obligation = calculus.get("obligations", {}).get(obligation_id, {})
        now_exposed = condition_holds(obligation.get("activation_condition"), values)
        already_exposed = condition_holds(obligation.get("activation_condition"), previous_values)
        if now_exposed and not already_exposed:
            return True
    return False


def assert_calculus_invariants(calculus: dict[str, Any]) -> None:
    state = normalize_calculus_state(calculus)
    decisions = state["decisions"]
    for subject, decision_id in state["active_model"].items():
        decision = decisions.get(decision_id)
        if decision is None:
            raise ValueError(f"active model references unknown decision: {decision_id}")
        if decision.get("status") != "ACTIVE":
            raise ValueError(f"active model references non-active decision: {decision_id}")
        if decision.get("subject") != subject:
            raise ValueError(f"active model subject mismatch for {decision_id}")
    values = decision_values(state)
    violations = violated_hard_constraints(state, values)
    unresolved = []
    for constraint_id in violations:
        constraint = state["constraints"][constraint_id]
        conflict = state["conflicts"].get(constraint.get("source_conflict_id"), {})
        if conflict.get("status") not in {"OPEN", "EXPLAINED", "LEARNED"}:
            unresolved.append(constraint_id)
    if unresolved:
        raise ValueError(f"active model violates hard constraints without an unresolved source conflict: {unresolved}")
    for lock_id, lock in state["locks"].items():
        if lock.get("obligation_id") not in state["obligations"]:
            raise ValueError(f"lock {lock_id} references unknown obligation")
        if lock.get("origin_decision_id") not in decisions:
            raise ValueError(f"lock {lock_id} references unknown decision")
    for constraint_id, constraint in state["constraints"].items():
        if constraint.get("strength") == "HARD" and constraint.get("status") == "ACTIVE":
            if constraint.get("validation") not in {"VALIDATED", "PROVEN"}:
                raise ValueError(f"hard constraint {constraint_id} lacks validated provenance")
            if constraint.get("source_explanation_id") not in state["explanations"]:
                raise ValueError(f"constraint {constraint_id} references unknown explanation")
            if constraint.get("source_conflict_id") not in state["conflicts"]:
                raise ValueError(f"constraint {constraint_id} references unknown conflict")
