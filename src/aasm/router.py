from __future__ import annotations
from dataclasses import dataclass
from .model import ProblemSpec

@dataclass(frozen=True)
class RouteDecision:
    primary: str
    operators: tuple[str,...]
    reasons: tuple[str,...]

class AlgorithmRouter:
    """Deterministic feature-based router. Features are supplied during formalization; no LLM is required."""
    def route(self, p: ProblemSpec) -> RouteDecision:
        f=p.features; ops=[]; why=[]
        if f.get("recursive_structure"): ops.append("recursion"); why.append("self-similar subproblems")
        if f.get("overlapping_subproblems"): ops.append("dynamic_programming"); why.append("repeated states can be memoized")
        if f.get("branching_choices") or f.get("constraint_search"): ops.append("backtracking"); why.append("candidate branches require pruning/restoration")
        if f.get("dependency_graph"): ops.append("graph_planning"); why.append("dependencies require graph traversal/topological ordering")
        if f.get("weighted_paths"): ops.append("shortest_path"); why.append("weighted plan alternatives exist")
        if f.get("local_choice_safe"): ops.append("greedy"); why.append("local-choice invariant declared")
        if f.get("capacity_constraints"): ops.append("max_flow_min_cut"); why.append("bounded shared resources")
        if f.get("uncertain_assumptions", True): ops.append("adversarial_verification"); why.append("challenge assumptions before commit")
        if not ops: ops=["graph_planning","adversarial_verification"]; why=["safe general-purpose defaults"]
        return RouteDecision(ops[0],tuple(dict.fromkeys(ops)),tuple(why))
