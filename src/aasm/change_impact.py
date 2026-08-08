from __future__ import annotations

from dataclasses import asdict, dataclass, field
from collections import defaultdict, deque
from typing import Any

from .graph import PlanGraph


class ChangeKind:
    USER_STEERING = "user_steering"
    ASSUMPTION_CHANGED = "assumption_changed"
    EVIDENCE_CHANGED = "evidence_changed"
    VERIFICATION_FAILED = "verification_failed"
    CONTRADICTION = "contradiction"
    RISK_ESCALATION = "risk_escalation"
    EXTERNAL_DEPENDENCY = "external_dependency"


@dataclass
class ChangeSignal:
    kind: str
    note: str
    seed_nodes: list[str] = field(default_factory=list)
    assumption_ids: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    risk_class: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.kind or not self.note:
            raise ValueError("kind and note are required")
        self.seed_nodes=sorted(set(self.seed_nodes))
        self.assumption_ids=sorted(set(self.assumption_ids))
        self.evidence_ids=sorted(set(self.evidence_ids))


@dataclass
class ImpactAnalysis:
    signal: ChangeSignal
    affected_nodes: list[str]
    unaffected_nodes: list[str]
    affected_active_tasks: list[str]
    preserved_active_tasks: list[str]
    requires_plan_interrupt: bool
    reason: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        raw=asdict(self)
        raw["signal"]=asdict(self.signal)
        return raw


class ChangeImpactAnalyzer:
    """Map changed information onto the dependent region of a plan graph."""

    PLAN_REVIEW_KINDS={
        ChangeKind.USER_STEERING,
        ChangeKind.ASSUMPTION_CHANGED,
        ChangeKind.EVIDENCE_CHANGED,
        ChangeKind.VERIFICATION_FAILED,
        ChangeKind.CONTRADICTION,
        ChangeKind.RISK_ESCALATION,
    }

    @staticmethod
    def _descendants(graph:PlanGraph,seeds:set[str])->set[str]:
        adj=defaultdict(list)
        for edge in graph.edges:
            adj[edge.src].append(edge.dst)
        seen=set(seeds); q=deque(sorted(seeds))
        while q:
            node=q.popleft()
            for nxt in adj[node]:
                if nxt not in seen:
                    seen.add(nxt); q.append(nxt)
        return seen

    def analyze(self, graph:PlanGraph, signal:ChangeSignal, active_task_ids:list[str]|None=None)->ImpactAnalysis:
        if graph.nodes:
            graph.topological_order()
        known=set(graph.nodes)
        unknown=sorted(set(signal.seed_nodes)-known)
        if unknown:
            raise KeyError(f"Unknown impact seed nodes: {unknown}")
        seeds=set(signal.seed_nodes)
        # When the signal has no explicit graph anchor, conservatively require
        # Planner attention without pretending the whole plan is invalid.
        affected=self._descendants(graph,seeds) if seeds else set()
        all_nodes=set(graph.nodes)
        active=set(active_task_ids or [])
        affected_active=sorted(active & affected)
        preserved_active=sorted(active - affected)
        requires=signal.kind in self.PLAN_REVIEW_KINDS
        if seeds:
            reason="changed information affects seeded plan nodes and their downstream dependents"
        else:
            reason="changed information is unanchored; Planner review required without invalidating unrelated plan nodes"
        return ImpactAnalysis(
            signal=signal,
            affected_nodes=sorted(affected),
            unaffected_nodes=sorted(all_nodes-affected),
            affected_active_tasks=affected_active,
            preserved_active_tasks=preserved_active,
            requires_plan_interrupt=requires,
            reason=reason,
            metadata={"unknown_seed_nodes":unknown},
        )
