from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .calculus import DecisionRecord, ObligationRecord
from .semantic_result import canonical_semantic_json, semantic_fingerprint


SEMANTIC_DEPENDENCY_CONTRACT_ID = "aasm.semantic.dependencies.v1"
SEMANTIC_DEPENDENCY_CONTRACT_VERSION = "0.1.0"
TRUTH_MAINTENANCE_CONTRACT_ID = "aasm.truth.maintenance.v1"
TRUTH_MAINTENANCE_CONTRACT_VERSION = "0.1.0"
REACTIVE_OBLIGATION_CONTRACT_ID = "aasm.reactive.obligation.v1"
REACTIVE_OBLIGATION_CONTRACT_VERSION = "0.1.0"
CAUSAL_DECISION_CONTRACT_ID = "aasm.causal.decision.v1"
CAUSAL_DECISION_CONTRACT_VERSION = "0.1.0"

SEMANTIC_NODE_TYPES = (
    "ENTITY",
    "PREDICATE",
    "OBJECTIVE",
    "ARTIFACT",
    "EVIDENCE",
    "EVENT",
    "VERIFIER",
    "OBSERVER",
    "CERTIFICATE",
    "CONSTRAINT",
    "DECISION",
    "OBLIGATION",
    "OPERATOR",
    "EFFECT",
    "RULE",
)

SEMANTIC_DEPENDENCY_RELATIONS = (
    "DEPENDS_ON",
    "DERIVES",
    "GROUNDS",
    "SUPPORTS",
    "REFUTES",
    "VERIFIES",
    "CERTIFIES",
    "CONSTRAINS",
    "SELECTS",
    "REQUIRES",
    "EXECUTES",
    "CAUSES",
    "OBSERVES",
    "SUPERSEDES",
)

TRUTH_AUTHORITIES = {"VERIFIER", "POLICY", "CONTROLLER"}
POLICY_AUTHORITIES = {"POLICY", "CONTROLLER"}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"):
        return _jsonable(value.to_dict())
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"semantic dependency value is not JSON serializable: {type(value)!r}")


@dataclass(frozen=True)
class SemanticNodeRef:
    node_type: str
    node_id: str

    def __post_init__(self):
        node_type = str(self.node_type).upper()
        object.__setattr__(self, "node_type", node_type)
        if node_type not in SEMANTIC_NODE_TYPES:
            raise ValueError(f"invalid semantic node type: {node_type}")
        if not str(self.node_id):
            raise ValueError("semantic node_id is required")
        object.__setattr__(self, "node_id", str(self.node_id))

    @property
    def key(self) -> str:
        return f"{self.node_type}:{self.node_id}"

    def to_dict(self) -> dict[str, Any]:
        return {"node_type": self.node_type, "node_id": self.node_id, "key": self.key}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticNodeRef":
        return cls(str(data["node_type"]), str(data["node_id"]))


@dataclass(frozen=True)
class SemanticDependency:
    source: SemanticNodeRef | dict[str, Any]
    target: SemanticNodeRef | dict[str, Any]
    relation: str = "DEPENDS_ON"
    propagates_stale: bool = True
    scope_id: str = "root"
    metadata: dict[str, Any] = field(default_factory=dict)
    dependency_id: str = ""

    def __post_init__(self):
        source = self.source if isinstance(self.source, SemanticNodeRef) else SemanticNodeRef.from_dict(self.source)
        target = self.target if isinstance(self.target, SemanticNodeRef) else SemanticNodeRef.from_dict(self.target)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "target", target)
        relation = str(self.relation).upper()
        object.__setattr__(self, "relation", relation)
        if relation not in SEMANTIC_DEPENDENCY_RELATIONS:
            raise ValueError(f"invalid semantic dependency relation: {relation}")
        if source.key == target.key and self.propagates_stale:
            raise ValueError("propagating semantic dependency cannot self-loop")
        if not self.scope_id:
            raise ValueError("scope_id is required")
        _jsonable(self.metadata)
        if not self.dependency_id:
            digest = semantic_fingerprint(self.identity_payload())[:20]
            object.__setattr__(self, "dependency_id", f"dependency-{digest}")

    def identity_payload(self) -> dict[str, Any]:
        return {
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "relation": self.relation,
            "propagates_stale": bool(self.propagates_stale),
            "scope_id": self.scope_id,
            "metadata": _jsonable(self.metadata),
        }

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint({"dependency_id": self.dependency_id, **self.identity_payload()})

    def to_dict(self) -> dict[str, Any]:
        return {"dependency_id": self.dependency_id, **self.identity_payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticDependency":
        payload = deepcopy(dict(data))
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass
class CausalDecisionRecord(DecisionRecord):
    rejected_alternatives: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 1.0
    reasoning: str = ""
    caused_by_event_ids: list[str] = field(default_factory=list)
    caused_by_artifact_ids: list[str] = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError("causal decision confidence must be between 0 and 1")
        self.caused_by_event_ids = sorted(set(str(value) for value in self.caused_by_event_ids))
        self.caused_by_artifact_ids = sorted(set(str(value) for value in self.caused_by_artifact_ids))
        self.rejected_alternatives = [_jsonable(value) for value in self.rejected_alternatives]
        if not isinstance(self.reasoning, str):
            raise ValueError("causal decision reasoning must be a string")

    @property
    def causal_fingerprint(self) -> str:
        return semantic_fingerprint(self.to_dict())


@dataclass(frozen=True)
class ReactiveObligationRule:
    rule_id: str
    watch_event_types: tuple[str, ...]
    statement: str
    handler_name: str
    scope_id: str = "root"
    once: bool = True
    event_data_equals: dict[str, Any] = field(default_factory=dict)
    required_evidence_types: tuple[str, ...] = ()
    decision_dependencies: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.rule_id or not self.statement.strip() or not self.handler_name:
            raise ValueError("rule_id, statement, and handler_name are required")
        object.__setattr__(self, "watch_event_types", tuple(sorted(set(str(value) for value in self.watch_event_types))))
        if not self.watch_event_types:
            raise ValueError("reactive rule requires watch_event_types")
        object.__setattr__(self, "required_evidence_types", tuple(sorted(set(str(value) for value in self.required_evidence_types))))
        object.__setattr__(self, "decision_dependencies", tuple(sorted(set(str(value) for value in self.decision_dependencies))))
        _jsonable(self.event_data_equals)
        _jsonable(self.metadata)

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.payload())

    def payload(self) -> dict[str, Any]:
        return _jsonable(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReactiveObligationRule":
        payload = deepcopy(dict(data))
        payload.pop("fingerprint", None)
        return cls(**payload)


@dataclass
class ReactiveObligationRecord(ObligationRecord):
    reactive_rule_id: str = ""
    trigger_event_id: str = ""
    trigger_event_type: str = ""
    handler_name: str = ""

    def __post_init__(self):
        super().__post_init__()
        if not all((self.reactive_rule_id, self.trigger_event_id, self.trigger_event_type, self.handler_name)):
            raise ValueError("reactive obligation requires rule, trigger event, event type, and handler name")


@dataclass(frozen=True)
class TruthMaintenancePlan:
    root: SemanticNodeRef | dict[str, Any]
    affected_nodes: tuple[SemanticNodeRef | dict[str, Any], ...]
    reason: str
    authority_id: str
    authority_class: str
    graph_fingerprint: str
    evidence_ids: tuple[str, ...] = ()
    plan_id: str = ""

    def __post_init__(self):
        root = self.root if isinstance(self.root, SemanticNodeRef) else SemanticNodeRef.from_dict(self.root)
        affected = tuple(
            value if isinstance(value, SemanticNodeRef) else SemanticNodeRef.from_dict(value)
            for value in self.affected_nodes
        )
        affected = tuple(sorted({value.key: value for value in affected}.values(), key=lambda row: row.key))
        object.__setattr__(self, "root", root)
        object.__setattr__(self, "affected_nodes", affected)
        object.__setattr__(self, "evidence_ids", tuple(sorted(set(str(value) for value in self.evidence_ids))))
        if not self.reason.strip():
            raise ValueError("truth-maintenance reason is required")
        if not self.authority_id:
            raise ValueError("truth-maintenance authority_id is required")
        if self.authority_class not in TRUTH_AUTHORITIES:
            raise PermissionError("truth maintenance requires VERIFIER, POLICY, or CONTROLLER authority")
        if not self.graph_fingerprint:
            raise ValueError("truth-maintenance graph_fingerprint is required")
        if not self.plan_id:
            digest = semantic_fingerprint({
                "root": root.to_dict(),
                "reason": self.reason,
                "authority_id": self.authority_id,
                "authority_class": self.authority_class,
                "evidence_ids": list(self.evidence_ids),
            })[:20]
            object.__setattr__(self, "plan_id", f"truth-plan-{digest}")

    @property
    def fingerprint(self) -> str:
        return semantic_fingerprint(self.payload())

    def payload(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "root": self.root.to_dict(),
            "affected_nodes": [row.to_dict() for row in self.affected_nodes],
            "reason": self.reason,
            "authority_id": self.authority_id,
            "authority_class": self.authority_class,
            "graph_fingerprint": self.graph_fingerprint,
            "evidence_ids": list(self.evidence_ids),
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.payload(), "fingerprint": self.fingerprint}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "TruthMaintenancePlan":
        payload = deepcopy(dict(data))
        payload.pop("fingerprint", None)
        return cls(**payload)


def semantic_dependency_contract() -> dict[str, Any]:
    return {
        "contract_id": SEMANTIC_DEPENDENCY_CONTRACT_ID,
        "contract_version": SEMANTIC_DEPENDENCY_CONTRACT_VERSION,
        "truth_maintenance_contract_id": TRUTH_MAINTENANCE_CONTRACT_ID,
        "truth_maintenance_contract_version": TRUTH_MAINTENANCE_CONTRACT_VERSION,
        "reactive_obligation_contract_id": REACTIVE_OBLIGATION_CONTRACT_ID,
        "reactive_obligation_contract_version": REACTIVE_OBLIGATION_CONTRACT_VERSION,
        "causal_decision_contract_id": CAUSAL_DECISION_CONTRACT_ID,
        "causal_decision_contract_version": CAUSAL_DECISION_CONTRACT_VERSION,
        "node_types": list(SEMANTIC_NODE_TYPES),
        "relations": list(SEMANTIC_DEPENDENCY_RELATIONS),
        "propagating_edge_policy": "DAG_REQUIRED",
        "descriptive_edge_policy": "CYCLES_ALLOWED_WHEN_PROPAGATES_STALE_FALSE",
        "truth_change_policy": "AFFECTED_DESCENDANTS_ONLY",
        "unrelated_sibling_policy": "PRESERVE",
        "obligation_policy": "REOPEN_AS_NEEDS_REVALIDATION",
        "reactive_policy": "DERIVE_OBLIGATION_NEVER_EXECUTE_HANDLER",
        "durability_boundary": "AASM_EVENT_REDUCER_ONLY",
        "dependency_records": "AASM_EVIDENCE",
        "memory_projection_inputs": [
            "VALID",
            "STALE",
            "REFUTED",
            "AUTHORIZED",
            "scope_visibility",
            "dependency_depth",
            "causal_relevance",
            "objective_relevance",
            "last_verified_at",
            "verification_strength",
            "superseded_by",
        ],
        "next_release_boundary": "V0.39_TYPED_EVENT_TRANSITION_PROTOCOL_AND_CAPABILITY_ABI",
    }


def _edge_id(source: SemanticNodeRef, target: SemanticNodeRef, relation: str, propagates_stale: bool, origin: str) -> str:
    return "edge-" + semantic_fingerprint({
        "source": source.key,
        "target": target.key,
        "relation": relation,
        "propagates_stale": propagates_stale,
        "origin": origin,
    })[:20]


def _derived_edge(
    source: SemanticNodeRef,
    target: SemanticNodeRef,
    relation: str,
    *,
    propagates_stale: bool = True,
    origin: str,
) -> dict[str, Any]:
    return {
        "dependency_id": _edge_id(source, target, relation, propagates_stale, origin),
        "source": source.to_dict(),
        "target": target.to_dict(),
        "relation": relation,
        "propagates_stale": propagates_stale,
        "scope_id": "root",
        "metadata": {"origin": origin, "derived": True},
        "fingerprint": semantic_fingerprint({
            "source": source.to_dict(),
            "target": target.to_dict(),
            "relation": relation,
            "propagates_stale": propagates_stale,
            "origin": origin,
        }),
    }


def _register_node(nodes: dict[str, dict[str, Any]], ref: SemanticNodeRef, **metadata: Any) -> None:
    row = nodes.setdefault(ref.key, {"node_type": ref.node_type, "node_id": ref.node_id, "key": ref.key})
    for key, value in metadata.items():
        if value is not None:
            row[key] = _jsonable(value)


def _add_edge(edges: dict[str, dict[str, Any]], nodes: dict[str, dict[str, Any]], edge: Mapping[str, Any]) -> None:
    dependency = SemanticDependency.from_dict(edge)
    _register_node(nodes, dependency.source)
    _register_node(nodes, dependency.target)
    existing = edges.get(dependency.dependency_id)
    value = dependency.to_dict()
    if existing is not None and existing != value:
        raise ValueError(f"semantic dependency ID collision: {dependency.dependency_id}")
    edges[dependency.dependency_id] = value


def explicit_dependency_edges(records: Iterable[Mapping[str, Any]]) -> list[SemanticDependency]:
    out: list[SemanticDependency] = []
    for row in records:
        metadata = dict(row.get("metadata") or {})
        if metadata.get("semantic_dependency_record_type") != "EDGE":
            continue
        if metadata.get("semantic_dependency_contract_id") != SEMANTIC_DEPENDENCY_CONTRACT_ID:
            continue
        try:
            payload = row.get("statement") or "{}"
            document = payload if isinstance(payload, Mapping) else __import__("json").loads(payload)
            dependency = SemanticDependency.from_dict(document)
            if metadata.get("dependency_fingerprint") != dependency.fingerprint:
                continue
            out.append(dependency)
        except Exception:
            continue
    return out


def reactive_rules_from_evidence(records: Iterable[Mapping[str, Any]]) -> list[tuple[ReactiveObligationRule, str]]:
    out: list[tuple[ReactiveObligationRule, str]] = []
    for row in records:
        metadata = dict(row.get("metadata") or {})
        if metadata.get("semantic_dependency_record_type") != "REACTIVE_RULE":
            continue
        if metadata.get("reactive_contract_id") != REACTIVE_OBLIGATION_CONTRACT_ID:
            continue
        try:
            payload = row.get("statement") or "{}"
            document = payload if isinstance(payload, Mapping) else __import__("json").loads(payload)
            rule = ReactiveObligationRule.from_dict(document)
            if metadata.get("rule_fingerprint") == rule.fingerprint:
                out.append((rule, str(row.get("evidence_id") or "")))
        except Exception:
            continue
    return out


def truth_records_from_evidence(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    plans: dict[str, dict[str, Any]] = {}
    applied: dict[str, dict[str, Any]] = {}
    for row in records:
        metadata = dict(row.get("metadata") or {})
        record_type = metadata.get("semantic_dependency_record_type")
        if record_type not in {"TRUTH_PLAN", "TRUTH_APPLIED"}:
            continue
        try:
            payload = row.get("statement") or "{}"
            document = payload if isinstance(payload, Mapping) else __import__("json").loads(payload)
        except Exception:
            continue
        if record_type == "TRUTH_PLAN":
            try:
                plan = TruthMaintenancePlan.from_dict(document)
            except Exception:
                continue
            if metadata.get("truth_contract_id") != TRUTH_MAINTENANCE_CONTRACT_ID:
                continue
            if metadata.get("plan_fingerprint") != plan.fingerprint:
                continue
            plans[plan.plan_id] = {"evidence_id": row.get("evidence_id"), "plan": plan.to_dict()}
        else:
            if metadata.get("truth_contract_id") != TRUTH_MAINTENANCE_CONTRACT_ID:
                continue
            if metadata.get("result_fingerprint") != semantic_fingerprint(document):
                continue
            plan_id = str(document.get("plan_id") or "")
            if plan_id:
                applied[plan_id] = {"evidence_id": row.get("evidence_id"), "result": deepcopy(document)}
    return {
        "plans": plans,
        "applied": applied,
        "pending_plan_ids": sorted(set(plans) - set(applied)),
    }


def _propagating_cycle(edges: Mapping[str, Mapping[str, Any]]) -> list[str] | None:
    adjacency: dict[str, list[str]] = {}
    for edge in edges.values():
        if not edge.get("propagates_stale", True):
            continue
        source = SemanticNodeRef.from_dict(edge["source"]).key
        target = SemanticNodeRef.from_dict(edge["target"]).key
        adjacency.setdefault(source, []).append(target)
    for key in adjacency:
        adjacency[key] = sorted(set(adjacency[key]))

    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in visiting:
            start = stack.index(node)
            return [*stack[start:], node]
        if node in visited:
            return None
        visiting.add(node)
        stack.append(node)
        for child in adjacency.get(node, []):
            cycle = visit(child)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for node in sorted(set(adjacency) | {v for values in adjacency.values() for v in values}):
        cycle = visit(node)
        if cycle:
            return cycle
    return None


def build_semantic_dependency_graph(
    *,
    reasoning: Mapping[str, Any] | None = None,
    calculus: Mapping[str, Any] | None = None,
    semantic_problem: Mapping[str, Any] | None = None,
    evidence_records: Sequence[Mapping[str, Any]] = (),
    events: Sequence[Any] = (),
    effects: Sequence[Any] = (),
    explicit_edges: Sequence[SemanticDependency | Mapping[str, Any]] = (),
) -> dict[str, Any]:
    reasoning = deepcopy(dict(reasoning or {}))
    calculus = deepcopy(dict(calculus or {}))
    semantic_problem = deepcopy(dict(semantic_problem or {}))
    nodes: dict[str, dict[str, Any]] = {}
    edges: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    evidence_by_id = {
        str(row.get("evidence_id")): row
        for row in evidence_records
        if row.get("evidence_id")
    }

    for row in evidence_records:
        evidence_id = str(row.get("evidence_id") or "")
        if evidence_id:
            evidence_ref = SemanticNodeRef("EVIDENCE", evidence_id)
            _register_node(
                nodes,
                evidence_ref,
                kind=row.get("kind"),
                status=row.get("status", "active"),
            )
            evidence_metadata = dict(row.get("metadata") or {})
            certificate_id = evidence_metadata.get("certificate_id")
            if certificate_id:
                certificate_ref = SemanticNodeRef("CERTIFICATE", str(certificate_id))
                _register_node(nodes, certificate_ref)
                _add_edge(
                    edges,
                    nodes,
                    _derived_edge(
                        evidence_ref,
                        certificate_ref,
                        "CERTIFIES",
                        origin="evidence.certificate",
                    ),
                )

    for event in events:
        event_id = str(getattr(event, "event_id", "") or (event.get("event_id") if isinstance(event, Mapping) else ""))
        if event_id:
            event_type = getattr(event, "event_type", None)
            if event_type is None and isinstance(event, Mapping):
                event_type = event.get("event_type")
            _register_node(nodes, SemanticNodeRef("EVENT", event_id), event_type=event_type)

    problem_model = semantic_problem.get("problem_model") or {}
    for row in problem_model.get("entities", []):
        _register_node(nodes, SemanticNodeRef("ENTITY", row["entity_id"]), kind=row.get("kind"))
    for row in problem_model.get("predicates", []):
        _register_node(nodes, SemanticNodeRef("PREDICATE", row["predicate_id"]), arity=row.get("arity"))
    for row in problem_model.get("objectives", []):
        objective = SemanticNodeRef("OBJECTIVE", row["objective_id"])
        predicate = SemanticNodeRef("PREDICATE", row["predicate_id"])
        _register_node(nodes, objective, direction=row.get("direction"))
        _add_edge(edges, nodes, _derived_edge(predicate, objective, "DEPENDS_ON", origin="semantic_problem.objective"))
    for row in problem_model.get("operators", []):
        _register_node(nodes, SemanticNodeRef("OPERATOR", row["operator_id"]))
    for row in problem_model.get("observers", []):
        observer = SemanticNodeRef("OBSERVER", row["observer_id"])
        _register_node(nodes, observer)
        for predicate_id in row.get("outputs", []):
            _add_edge(
                edges,
                nodes,
                _derived_edge(observer, SemanticNodeRef("PREDICATE", predicate_id), "OBSERVES", origin="semantic_problem.observer"),
            )
    for row in problem_model.get("verifiers", []):
        _register_node(nodes, SemanticNodeRef("VERIFIER", row["verifier_id"]))

    for artifact_id, entry in (reasoning.get("artifacts") or {}).items():
        artifact = entry.get("artifact") or {}
        ref = SemanticNodeRef("ARTIFACT", artifact_id)
        pass_verifications = [
            row for row in entry.get("verifications", [])
            if row.get("verdict") == "PASS"
        ]
        verification_times = [
            evidence_by_id.get(str(row.get("evidence_id")), {}).get("created_at")
            for row in pass_verifications
            if row.get("evidence_id")
        ]
        verification_times = [value for value in verification_times if value is not None]
        artifact_scope = artifact.get("scope") or {}
        _register_node(
            nodes,
            ref,
            artifact_kind=artifact.get("kind"),
            state=entry.get("state"),
            truth_state=entry.get("state"),
            scope=artifact_scope,
            scope_visibility=artifact_scope.get("scope_id", "root") if isinstance(artifact_scope, Mapping) else "root",
            fingerprint=artifact.get("fingerprint"),
            verification_strength=len(pass_verifications),
            last_verified_at=max(verification_times) if verification_times else None,
        )
        for evidence_id in artifact.get("evidence_ids", []):
            _add_edge(
                edges,
                nodes,
                _derived_edge(
                    SemanticNodeRef("EVIDENCE", evidence_id),
                    ref,
                    "GROUNDS",
                    origin="reasoning.artifact.evidence",
                ),
            )
        for premise_id in artifact.get("premise_artifact_ids", []):
            _add_edge(
                edges,
                nodes,
                _derived_edge(
                    SemanticNodeRef("ARTIFACT", premise_id),
                    ref,
                    "DERIVES",
                    origin="reasoning.artifact.premise",
                ),
            )
        for verification in entry.get("verifications", []):
            verifier_id = verification.get("actor_id")
            if verifier_id:
                _add_edge(
                    edges,
                    nodes,
                    _derived_edge(
                        SemanticNodeRef("VERIFIER", str(verifier_id)),
                        ref,
                        "VERIFIES",
                        propagates_stale=False,
                        origin="reasoning.verification",
                    ),
                )

    decisions = calculus.get("decisions") or {}
    constraints = calculus.get("constraints") or {}
    obligations = calculus.get("obligations") or {}
    for constraint_id, row in constraints.items():
        _register_node(nodes, SemanticNodeRef("CONSTRAINT", constraint_id), status=row.get("status"), strength=row.get("strength"))
    for decision_id, row in decisions.items():
        ref = SemanticNodeRef("DECISION", decision_id)
        _register_node(
            nodes,
            ref,
            status=row.get("status"),
            subject=row.get("subject"),
            value=row.get("value"),
            scope=row.get("scope"),
            confidence=row.get("confidence"),
            superseded_by=row.get("superseded_by"),
        )
        for parent_id in row.get("parent_ids", []):
            _add_edge(edges, nodes, _derived_edge(SemanticNodeRef("DECISION", parent_id), ref, "DERIVES", origin="calculus.decision.parent"))
        for constraint_id in row.get("antecedent_constraint_ids", []):
            _add_edge(edges, nodes, _derived_edge(SemanticNodeRef("CONSTRAINT", constraint_id), ref, "CONSTRAINS", origin="calculus.decision.constraint"))
        for evidence_id in row.get("evidence_ids", []):
            _add_edge(edges, nodes, _derived_edge(SemanticNodeRef("EVIDENCE", evidence_id), ref, "GROUNDS", origin="calculus.decision.evidence"))
        for event_id in row.get("caused_by_event_ids", []):
            _add_edge(edges, nodes, _derived_edge(SemanticNodeRef("EVENT", event_id), ref, "CAUSES", origin="causal_decision.event"))
        for artifact_id in row.get("caused_by_artifact_ids", []):
            _add_edge(edges, nodes, _derived_edge(SemanticNodeRef("ARTIFACT", artifact_id), ref, "CAUSES", origin="causal_decision.artifact"))

    for obligation_id, row in obligations.items():
        ref = SemanticNodeRef("OBLIGATION", obligation_id)
        _register_node(
            nodes,
            ref,
            status=row.get("status"),
            scope=row.get("scope"),
            reactive_rule_id=row.get("reactive_rule_id"),
            trigger_event_id=row.get("trigger_event_id"),
            handler_name=row.get("handler_name"),
        )
        for decision_id in row.get("decision_dependencies", []):
            _add_edge(edges, nodes, _derived_edge(SemanticNodeRef("DECISION", decision_id), ref, "REQUIRES", origin="calculus.obligation.decision"))
        for parent_id in row.get("dependencies", []):
            _add_edge(edges, nodes, _derived_edge(SemanticNodeRef("OBLIGATION", parent_id), ref, "REQUIRES", origin="calculus.obligation.parent"))
        trigger_event_id = row.get("trigger_event_id")
        if trigger_event_id:
            _add_edge(edges, nodes, _derived_edge(SemanticNodeRef("EVENT", trigger_event_id), ref, "CAUSES", origin="reactive_obligation.trigger"))

    for effect in effects:
        spec = getattr(effect, "spec", None)
        effect_id = getattr(spec, "effect_id", None)
        if effect_id:
            _register_node(nodes, SemanticNodeRef("EFFECT", str(effect_id)), status=getattr(effect, "status", None))

    for rule, evidence_id in reactive_rules_from_evidence(evidence_records):
        rule_ref = SemanticNodeRef("RULE", rule.rule_id)
        _register_node(nodes, rule_ref, handler_name=rule.handler_name, once=rule.once, scope_id=rule.scope_id)
        if evidence_id:
            _add_edge(
                edges,
                nodes,
                _derived_edge(SemanticNodeRef("EVIDENCE", evidence_id), rule_ref, "GROUNDS", propagates_stale=False, origin="reactive_rule.admission"),
            )

    supplied = [*explicit_dependency_edges(evidence_records), *explicit_edges]
    for raw in supplied:
        try:
            dependency = raw if isinstance(raw, SemanticDependency) else SemanticDependency.from_dict(raw)
            _add_edge(edges, nodes, dependency.to_dict())
        except Exception as exc:
            issues.append({"kind": "INVALID_EXPLICIT_DEPENDENCY", "error": f"{type(exc).__name__}: {exc}"})

    cycle = _propagating_cycle(edges)
    if cycle:
        issues.append({"kind": "PROPAGATING_CYCLE", "cycle": cycle})

    forward: dict[str, list[str]] = {key: [] for key in nodes}
    reverse: dict[str, list[str]] = {key: [] for key in nodes}
    for edge in edges.values():
        source = SemanticNodeRef.from_dict(edge["source"]).key
        target = SemanticNodeRef.from_dict(edge["target"]).key
        forward.setdefault(source, []).append(edge["dependency_id"])
        reverse.setdefault(target, []).append(edge["dependency_id"])
    forward = {key: sorted(set(value)) for key, value in sorted(forward.items())}
    reverse = {key: sorted(set(value)) for key, value in sorted(reverse.items())}
    ordered_nodes = {key: nodes[key] for key in sorted(nodes)}
    ordered_edges = {key: edges[key] for key in sorted(edges)}
    fingerprint = semantic_fingerprint({
        "nodes": ordered_nodes,
        "edges": ordered_edges,
        "issues": issues,
    })
    return {
        "contract": semantic_dependency_contract(),
        "valid": not issues,
        "issues": issues,
        "nodes": ordered_nodes,
        "edges": ordered_edges,
        "forward": forward,
        "reverse": reverse,
        "node_count": len(ordered_nodes),
        "edge_count": len(ordered_edges),
        "graph_fingerprint": fingerprint,
    }


def dependency_closure(
    graph: Mapping[str, Any],
    root: SemanticNodeRef | Mapping[str, Any],
    *,
    direction: str = "forward",
    propagating_only: bool = True,
) -> list[dict[str, Any]]:
    if not graph.get("valid", False):
        raise ValueError(f"semantic dependency graph is invalid: {graph.get('issues')}")
    root_ref = root if isinstance(root, SemanticNodeRef) else SemanticNodeRef.from_dict(root)
    if root_ref.key not in graph.get("nodes", {}):
        raise KeyError(root_ref.key)
    if direction not in {"forward", "reverse"}:
        raise ValueError("direction must be forward or reverse")
    index_name = "forward" if direction == "forward" else "reverse"
    seen = {root_ref.key}
    queue: list[tuple[str, int]] = [(root_ref.key, 0)]
    out: list[dict[str, Any]] = []
    while queue:
        current, depth = queue.pop(0)
        out.append({"key": current, "depth": depth, **deepcopy(graph["nodes"][current])})
        for edge_id in graph.get(index_name, {}).get(current, []):
            edge = graph["edges"][edge_id]
            if propagating_only and not edge.get("propagates_stale", True):
                continue
            source = SemanticNodeRef.from_dict(edge["source"]).key
            target = SemanticNodeRef.from_dict(edge["target"]).key
            neighbor = target if direction == "forward" else source
            if neighbor not in seen:
                seen.add(neighbor)
                queue.append((neighbor, depth + 1))
    return out


def dependency_impact_report(graph: Mapping[str, Any], root: SemanticNodeRef | Mapping[str, Any]) -> dict[str, Any]:
    root_ref = root if isinstance(root, SemanticNodeRef) else SemanticNodeRef.from_dict(root)
    closure = dependency_closure(graph, root_ref, direction="forward", propagating_only=True)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in closure:
        grouped.setdefault(row["node_type"], []).append(deepcopy(row))
    return {
        "contract_id": TRUTH_MAINTENANCE_CONTRACT_ID,
        "root": root_ref.to_dict(),
        "affected_nodes": closure,
        "affected_descendants": closure[1:],
        "by_type": {key: grouped[key] for key in sorted(grouped)},
        "affected_count": len(closure),
        "graph_fingerprint": graph["graph_fingerprint"],
        "impact_fingerprint": semantic_fingerprint({
            "root": root_ref.to_dict(),
            "affected": [(row["key"], row["depth"]) for row in closure],
            "graph_fingerprint": graph["graph_fingerprint"],
        }),
    }


def dependency_lineage_report(graph: Mapping[str, Any], target: SemanticNodeRef | Mapping[str, Any]) -> dict[str, Any]:
    target_ref = target if isinstance(target, SemanticNodeRef) else SemanticNodeRef.from_dict(target)
    closure = dependency_closure(graph, target_ref, direction="reverse", propagating_only=False)
    return {
        "contract_id": SEMANTIC_DEPENDENCY_CONTRACT_ID,
        "target": target_ref.to_dict(),
        "lineage": closure,
        "ancestor_count": max(0, len(closure) - 1),
        "graph_fingerprint": graph["graph_fingerprint"],
        "lineage_fingerprint": semantic_fingerprint({
            "target": target_ref.to_dict(),
            "lineage": [(row["key"], row["depth"]) for row in closure],
            "graph_fingerprint": graph["graph_fingerprint"],
        }),
    }


def dependency_memory_signals(graph: Mapping[str, Any]) -> dict[str, Any]:
    """Expose deterministic V40 memory/context inputs without implementing memory itself."""
    if not graph.get("valid", False):
        raise ValueError(f"semantic dependency graph is invalid: {graph.get('issues')}")
    signals: dict[str, dict[str, Any]] = {}
    for key, node in graph.get("nodes", {}).items():
        ref = SemanticNodeRef(node["node_type"], node["node_id"])
        closure = dependency_closure(graph, ref, direction="forward", propagating_only=True)
        descendants = closure[1:]
        max_depth = max([int(row["depth"]) for row in closure], default=0)
        objective_descendants = [row for row in descendants if row.get("node_type") == "OBJECTIVE"]
        truth_state = node.get("truth_state") or node.get("state") or node.get("status")
        valid = truth_state not in {"STALE", "REFUTED", "REJECTED", "INVALIDATED", "SUPERSEDED"}
        signals[key] = {
            "key": key,
            "node_type": node["node_type"],
            "node_id": node["node_id"],
            "VALID": bool(valid),
            "STALE": truth_state == "STALE",
            "REFUTED": truth_state == "REFUTED",
            "AUTHORIZED": truth_state == "AUTHORIZED",
            "scope_visibility": node.get("scope_visibility")
            or ((node.get("scope") or {}).get("scope_id") if isinstance(node.get("scope"), Mapping) else None)
            or "root",
            "dependency_depth": max_depth,
            "causal_relevance": len(descendants),
            "objective_relevance": len(objective_descendants),
            "last_verified_at": node.get("last_verified_at"),
            "verification_strength": node.get("verification_strength", 0),
            "superseded_by": node.get("superseded_by"),
        }
    ordered = {key: signals[key] for key in sorted(signals)}
    return {
        "contract_id": SEMANTIC_DEPENDENCY_CONTRACT_ID,
        "purpose": "V0.40_HIERARCHICAL_MEMORY_CONTEXT_PROJECTION_INPUTS",
        "signals": ordered,
        "graph_fingerprint": graph["graph_fingerprint"],
        "signals_fingerprint": semantic_fingerprint(ordered),
    }


def semantic_dependency_document(value: Any) -> str:
    return canonical_semantic_json(value.to_dict() if hasattr(value, "to_dict") else value)


__all__ = [
    "SEMANTIC_DEPENDENCY_CONTRACT_ID",
    "SEMANTIC_DEPENDENCY_CONTRACT_VERSION",
    "TRUTH_MAINTENANCE_CONTRACT_ID",
    "TRUTH_MAINTENANCE_CONTRACT_VERSION",
    "REACTIVE_OBLIGATION_CONTRACT_ID",
    "REACTIVE_OBLIGATION_CONTRACT_VERSION",
    "CAUSAL_DECISION_CONTRACT_ID",
    "CAUSAL_DECISION_CONTRACT_VERSION",
    "SEMANTIC_NODE_TYPES",
    "SEMANTIC_DEPENDENCY_RELATIONS",
    "SemanticNodeRef",
    "SemanticDependency",
    "CausalDecisionRecord",
    "ReactiveObligationRule",
    "ReactiveObligationRecord",
    "TruthMaintenancePlan",
    "semantic_dependency_contract",
    "explicit_dependency_edges",
    "reactive_rules_from_evidence",
    "truth_records_from_evidence",
    "build_semantic_dependency_graph",
    "dependency_closure",
    "dependency_impact_report",
    "dependency_lineage_report",
    "dependency_memory_signals",
    "semantic_dependency_document",
    "run_semantic_dependency_conformance",
]


def run_semantic_dependency_conformance() -> dict[str, Any]:
    """Exercise the v0.38 causal graph, truth maintenance, and reactive-obligation boundaries."""
    from .evidence import EvidenceRecord
    from .model import ProblemSpec
    from .reasoning import Claim, ReasoningProducer
    from .runtime_v32 import AASMEngine

    engine = AASMEngine(ProblemSpec("semantic dependency conformance"))
    observation = engine.add_evidence(EvidenceRecord(
        "observation",
        "root observation",
        source="v0.38-conformance",
    ))

    root = Claim(
        "root claim",
        ReasoningProducer("agent-root", "PROPOSER"),
        evidence_ids=(observation.evidence_id,),
    )
    dependent = Claim(
        "dependent claim",
        ReasoningProducer("agent-dependent", "PROPOSER"),
        premise_artifact_ids=(root.artifact_id,),
    )
    sibling = Claim(
        "unrelated sibling",
        ReasoningProducer("agent-sibling", "PROPOSER"),
    )
    engine.propose_artifact(root)
    engine.propose_artifact(dependent)
    engine.propose_artifact(sibling)

    decision = CausalDecisionRecord(
        decision_id="decision-v38",
        subject="implementation_mode",
        value="safe",
        caused_by_artifact_ids=[dependent.artifact_id],
        rejected_alternatives=[{"value": "fast", "reason": "less supported"}],
        confidence=0.9,
        reasoning="dependent claim establishes safe mode",
    )
    engine.register_causal_decision(decision)
    engine.activate_decision(decision.decision_id)

    rule = ReactiveObligationRule(
        rule_id="rule-v38",
        watch_event_types=("snapshot_patched",),
        statement="revalidate implementation after causal state change",
        handler_name="revalidate-implementation",
        decision_dependencies=(decision.decision_id,),
        once=True,
    )
    engine.register_reactive_obligation_rule(
        rule,
        authority_id="policy-v38",
        authority_class="POLICY",
    )
    derivation = engine.derive_reactive_obligations()
    if not derivation["created"]:
        raise AssertionError("reactive conformance rule did not derive an obligation")
    obligation_id = derivation["created"][0]["obligation"]["obligation_id"]
    engine.enable_obligation(obligation_id)
    engine.set_obligation_status(obligation_id, "IN_PROGRESS")
    engine.set_obligation_status(obligation_id, "VERIFYING")
    engine.set_obligation_status(obligation_id, "VERIFIED")
    engine.set_obligation_status(obligation_id, "COMMITTED")

    graph = engine.semantic_dependency_graph()
    impact = engine.semantic_dependency_impact("ARTIFACT", root.artifact_id)
    affected_keys = {row["key"] for row in impact["affected_nodes"]}
    expected = {
        f"ARTIFACT:{root.artifact_id}",
        f"ARTIFACT:{dependent.artifact_id}",
        f"DECISION:{decision.decision_id}",
        f"OBLIGATION:{obligation_id}",
    }

    propagating_cycle_rejected = False
    try:
        engine.register_semantic_dependency(
            SemanticDependency(
                SemanticNodeRef("ARTIFACT", dependent.artifact_id),
                SemanticNodeRef("ARTIFACT", root.artifact_id),
                "DEPENDS_ON",
                True,
            ),
            authority_id="policy-v38",
            authority_class="POLICY",
        )
    except ValueError:
        propagating_cycle_rejected = True

    descriptive_cycle = engine.register_semantic_dependency(
        SemanticDependency(
            SemanticNodeRef("ARTIFACT", dependent.artifact_id),
            SemanticNodeRef("ARTIFACT", root.artifact_id),
            "SUPPORTS",
            False,
        ),
        authority_id="policy-v38",
        authority_class="POLICY",
    )

    applied = engine.apply_truth_change(
        "ARTIFACT",
        root.artifact_id,
        reason="root claim invalidated by conformance fixture",
        authority_id="verifier-v38",
        authority_class="VERIFIER",
        evidence_ids=[observation.evidence_id],
    )
    repeated = engine.apply_truth_change(
        "ARTIFACT",
        root.artifact_id,
        reason="root claim invalidated by conformance fixture",
        authority_id="verifier-v38",
        authority_class="VERIFIER",
        evidence_ids=[observation.evidence_id],
    )

    final_reasoning = engine.reasoning_report()
    final_calculus = engine.calculus_report()
    lineage = engine.semantic_dependency_lineage("OBLIGATION", obligation_id)

    checks = {
        "graph_valid": graph["valid"] is True,
        "causal_closure_complete": expected.issubset(affected_keys),
        "unrelated_sibling_excluded": f"ARTIFACT:{sibling.artifact_id}" not in affected_keys,
        "propagating_cycle_rejected": propagating_cycle_rejected,
        "descriptive_cycle_allowed": descriptive_cycle["dependency"]["propagates_stale"] is False,
        "root_stale": final_reasoning["artifacts"][root.artifact_id]["state"] == "STALE",
        "dependent_stale": final_reasoning["artifacts"][dependent.artifact_id]["state"] == "STALE",
        "unrelated_sibling_preserved": final_reasoning["artifacts"][sibling.artifact_id]["state"] == "PROPOSED",
        "causal_decision_invalidated": final_calculus["decisions"][decision.decision_id]["status"] == "INVALIDATED",
        "reactive_obligation_reopened": final_calculus["obligations"][obligation_id]["status"] == "NEEDS_REVALIDATION",
        "reactive_handler_not_executed": derivation["handler_execution"] == "NONE",
        "truth_plan_idempotent": repeated["already_applied"] is True and repeated["plan"]["plan_id"] == applied["plan"]["plan_id"],
        "lineage_reaches_root": any(row["key"] == f"ARTIFACT:{root.artifact_id}" for row in lineage["lineage"]),
        "replay_exact": engine.replay().canonical_hash() == engine.snapshot.canonical_hash(),
    }
    report = {
        "contract_id": SEMANTIC_DEPENDENCY_CONTRACT_ID,
        "contract_version": SEMANTIC_DEPENDENCY_CONTRACT_VERSION,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "graph_fingerprint": engine.semantic_dependency_graph()["graph_fingerprint"],
        "truth_plan_id": applied["plan"]["plan_id"],
        "reactive_obligation_id": obligation_id,
    }
    report["report_sha256"] = semantic_fingerprint(report)
    return report
