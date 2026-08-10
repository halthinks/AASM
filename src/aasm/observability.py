from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, asdict
from typing import Any, Iterable


@dataclass
class ObservableGraph:
    graph_id: str
    kind: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sorted_dict_values(mapping: dict[str, Any], id_key: str) -> list[dict[str, Any]]:
    return [
        deepcopy(mapping[key])
        for key in sorted(mapping, key=lambda item: str(mapping[item].get(id_key, item)))
    ]


def decision_graph(snapshot: Any) -> ObservableGraph:
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    nodes = []
    for decision in _sorted_dict_values(calculus.get("decisions", {}), "decision_id"):
        nodes.append({
            "id": decision.get("decision_id"),
            "kind": "decision",
            "label": decision.get("subject"),
            "status": decision.get("status"),
            "value": deepcopy(decision.get("value")),
            "level": decision.get("level", 0),
            "pinned": bool(decision.get("pinned", False)),
            "scope": deepcopy(decision.get("scope") or {}),
            "plan_node_ids": list(decision.get("plan_node_ids") or []),
        })
    edges = [
        {
            "src": edge.get("src"),
            "dst": edge.get("dst"),
            "relation": edge.get("relation", "DEPENDS_ON"),
        }
        for edge in calculus.get("decision_edges", [])
    ]
    return ObservableGraph(
        graph_id="decision-graph",
        kind="DECISION",
        nodes=nodes,
        edges=sorted(edges, key=lambda edge: (str(edge["src"]), str(edge["dst"]), str(edge["relation"]))),
        metadata={"active_model": deepcopy(calculus.get("active_model", {})), "epoch": calculus.get("epoch", 0)},
    )


def obligation_graph(snapshot: Any) -> ObservableGraph:
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    nodes = []
    for obligation in _sorted_dict_values(calculus.get("obligations", {}), "obligation_id"):
        nodes.append({
            "id": obligation.get("obligation_id"),
            "kind": "obligation",
            "label": obligation.get("statement"),
            "status": obligation.get("status"),
            "mandatory": bool(obligation.get("mandatory", True)),
            "persistent": bool(obligation.get("persistent", True)),
            "activation_condition": deepcopy(obligation.get("activation_condition") or {"const": True}),
            "evidence_ids": list(obligation.get("evidence_ids") or []),
            "artifact_ids": list(obligation.get("artifact_ids") or []),
            "plan_node_ids": list(obligation.get("plan_node_ids") or []),
        })
    edges = []
    for edge in calculus.get("obligation_edges", []):
        edges.append({"src": edge.get("src"), "dst": edge.get("dst"), "relation": edge.get("relation", "DEPENDS_ON")})
    for obligation in calculus.get("obligations", {}).values():
        target = obligation.get("obligation_id")
        for decision_id in obligation.get("decision_dependencies", []):
            edges.append({"src": decision_id, "dst": target, "relation": "AUTHORIZED_BY"})
    return ObservableGraph(
        graph_id="obligation-graph",
        kind="OBLIGATION",
        nodes=nodes,
        edges=sorted(edges, key=lambda edge: (str(edge["src"]), str(edge["dst"]), str(edge["relation"]))),
        metadata={},
    )


def evidence_graph(snapshot: Any) -> ObservableGraph:
    records = list((getattr(snapshot, "evidence", {}) or {}).get("records", []))
    nodes = []
    edges = []
    for record in sorted(records, key=lambda item: str(item.get("evidence_id", ""))):
        evidence_id = record.get("evidence_id")
        nodes.append({
            "id": evidence_id,
            "kind": "evidence",
            "label": record.get("claim") or record.get("summary") or record.get("kind"),
            "status": record.get("status"),
            "evidence_kind": record.get("kind"),
            "valid": record.get("valid", True),
            "metadata": deepcopy(record.get("metadata") or {}),
        })
        relations = record.get("relations") or {}
        if isinstance(relations, dict):
            for relation in ("supports", "contradicts", "derived_from"):
                values = relations.get(relation) or []
                if isinstance(values, str):
                    values = [values]
                for target in values:
                    edges.append({"src": evidence_id, "dst": target, "relation": relation.upper()})
        for target in record.get("supports", []) if isinstance(record.get("supports"), list) else []:
            edges.append({"src": evidence_id, "dst": target, "relation": "SUPPORTS"})
        for target in record.get("contradicts", []) if isinstance(record.get("contradicts"), list) else []:
            edges.append({"src": evidence_id, "dst": target, "relation": "CONTRADICTS"})
    return ObservableGraph(
        graph_id="evidence-graph",
        kind="EVIDENCE",
        nodes=nodes,
        edges=sorted(edges, key=lambda edge: (str(edge["src"]), str(edge["dst"]), str(edge["relation"]))),
        metadata={"record_count": len(records)},
    )


def conflict_timeline(snapshot: Any) -> list[dict[str, Any]]:
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    rows = []
    for conflict in calculus.get("conflicts", {}).values():
        rows.append({
            "sequence": int(conflict.get("created_sequence", 0)),
            "type": "CONFLICT",
            "conflict_id": conflict.get("conflict_id"),
            "kind": conflict.get("kind"),
            "status": conflict.get("status"),
            "implicated_decision_ids": list(conflict.get("implicated_decision_ids") or []),
            "explanation_ids": list(conflict.get("explanation_ids") or []),
            "learned_constraint_ids": list(conflict.get("learned_constraint_ids") or []),
            "backjump": deepcopy(conflict.get("backjump")),
        })
    return sorted(rows, key=lambda row: (row["sequence"], str(row["conflict_id"])))


def fairness_debt(snapshot: Any) -> list[dict[str, Any]]:
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    records = calculus.get("fairness", {}).get("records", {})
    rows = []
    for obligation_id, record in records.items():
        rows.append({
            "obligation_id": obligation_id,
            "status": record.get("status", "NORMAL"),
            "hidden_epochs": int(record.get("hidden_epochs", 0)),
            "continuous_lock_epochs": int(record.get("continuous_lock_epochs", 0)),
            "lock_count": int(record.get("lock_count", 0)),
            "last_considered_epoch": record.get("last_considered_epoch"),
            "last_enabled_epoch": record.get("last_enabled_epoch"),
            "last_reviewed_epoch": record.get("last_reviewed_epoch"),
        })
    order = {"OVERDUE": 0, "DUE": 1, "NORMAL": 2}
    return sorted(rows, key=lambda row: (order.get(str(row["status"]), 3), -row["hidden_epochs"], row["obligation_id"]))


def event_timeline(events: Iterable[Any]) -> list[dict[str, Any]]:
    rows = []
    for event in events:
        reason = str(getattr(event, "reason", ""))
        event_type = str(getattr(event, "event_type", ""))
        lowered = reason.lower()
        category = None
        if "backjump" in lowered:
            category = "BACKJUMP"
        elif "restart" in lowered:
            category = "RESTART"
        elif "profile evolution" in lowered or "profile" in lowered and "bound" in lowered:
            category = "PROFILE"
        elif "candidate" in lowered:
            category = "CANDIDATE"
        elif "certificate" in lowered or "assurance" in lowered:
            category = "ASSURANCE"
        if category is None:
            continue
        rows.append({
            "sequence": int(getattr(event, "sequence", 0)),
            "ts": float(getattr(event, "ts", 0.0)),
            "category": category,
            "event_type": event_type,
            "from_state": getattr(event, "from_state", None),
            "to_state": getattr(event, "to_state", None),
            "reason": reason,
            "data": deepcopy(getattr(event, "data", {}) or {}),
        })
    return sorted(rows, key=lambda row: (row["sequence"], row["ts"]))


def package_history(snapshot: Any) -> dict[str, Any]:
    binding = deepcopy(getattr(snapshot, "profile_binding", {}) or {})
    return {
        "current": binding,
        "evolution_history": deepcopy(binding.get("evolution_history") or []),
        "evolution_proposals": deepcopy(binding.get("evolution_proposals") or []),
        "configuration_history": deepcopy((binding.get("metadata") or {}).get("configuration_history") or []),
    }


def observability_report(snapshot: Any, events: Iterable[Any]) -> dict[str, Any]:
    candidate_state = deepcopy(getattr(snapshot, "candidate_state", {}) or {})
    assurance_state = deepcopy(getattr(snapshot, "assurance_state", {}) or {})
    return {
        "machine_id": getattr(snapshot, "machine_id", ""),
        "machine_state": getattr(snapshot, "state", ""),
        "machine_version": getattr(snapshot, "version", 0),
        "decision_graph": decision_graph(snapshot).to_dict(),
        "obligation_graph": obligation_graph(snapshot).to_dict(),
        "evidence_graph": evidence_graph(snapshot).to_dict(),
        "conflict_timeline": conflict_timeline(snapshot),
        "fairness_debt": fairness_debt(snapshot),
        "event_timeline": event_timeline(events),
        "package_history": package_history(snapshot),
        "candidate_summary": {
            "selected_candidate_id": candidate_state.get("selected_candidate_id"),
            "activated_candidate_id": candidate_state.get("activated_candidate_id"),
            "candidate_count": len(candidate_state.get("candidates", {})),
            "backend_history": deepcopy(candidate_state.get("backend_history", [])),
        },
        "assurance_summary": {
            "certificate_count": len(assurance_state.get("certificates", {})),
            "verification_count": len(assurance_state.get("verifications", {})),
            "history_check_count": len(assurance_state.get("history_checks", [])),
            "minimization_count": len(assurance_state.get("minimizations", {})),
        },
    }
