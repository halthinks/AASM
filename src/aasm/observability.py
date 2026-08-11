from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
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


def _closed_graph(
    graph_id: str,
    kind: str,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> ObservableGraph:
    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        node_id = str(node.get("id") or "")
        if not node_id:
            continue
        by_id.setdefault(node_id, deepcopy(node))
    for edge in edges:
        for endpoint in ("src", "dst"):
            node_id = str(edge.get(endpoint) or "")
            if node_id and node_id not in by_id:
                by_id[node_id] = {
                    "id": node_id,
                    "kind": "reference",
                    "label": node_id,
                    "status": "EXTERNAL_REFERENCE",
                }
    normalized_edges = [
        {
            "src": str(edge.get("src")),
            "dst": str(edge.get("dst")),
            "relation": str(edge.get("relation", "RELATED_TO")),
            **({"metadata": deepcopy(edge["metadata"])} if edge.get("metadata") else {}),
        }
        for edge in edges
        if edge.get("src") and edge.get("dst")
    ]
    return ObservableGraph(
        graph_id=graph_id,
        kind=kind,
        nodes=sorted(by_id.values(), key=lambda node: (str(node.get("kind")), str(node.get("id")))),
        edges=sorted(
            normalized_edges,
            key=lambda edge: (str(edge["src"]), str(edge["dst"]), str(edge["relation"])),
        ),
        metadata=deepcopy(metadata or {}),
    )


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
    return _closed_graph(
        "decision-graph",
        "DECISION",
        nodes,
        edges,
        {"active_model": deepcopy(calculus.get("active_model", {})), "epoch": calculus.get("epoch", 0)},
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
        edges.append({
            "src": edge.get("src"),
            "dst": edge.get("dst"),
            "relation": edge.get("relation", "DEPENDS_ON"),
        })
    for obligation in calculus.get("obligations", {}).values():
        target = obligation.get("obligation_id")
        for decision_id in obligation.get("decision_dependencies", []):
            decision = calculus.get("decisions", {}).get(decision_id, {})
            nodes.append({
                "id": decision_id,
                "kind": "decision",
                "label": decision.get("subject", decision_id),
                "status": decision.get("status", "UNKNOWN"),
                "value": deepcopy(decision.get("value")),
            })
            edges.append({"src": decision_id, "dst": target, "relation": "AUTHORIZED_BY"})
    return _closed_graph("obligation-graph", "OBLIGATION", nodes, edges)


def evidence_graph(snapshot: Any) -> ObservableGraph:
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    assurance = deepcopy(getattr(snapshot, "assurance_state", {}) or {})
    records = list((getattr(snapshot, "evidence", {}) or {}).get("records", []))
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for record in sorted(records, key=lambda item: str(item.get("evidence_id", ""))):
        evidence_id = record.get("evidence_id")
        nodes.append({
            "id": evidence_id,
            "kind": "evidence",
            "label": record.get("statement") or record.get("claim") or record.get("summary") or record.get("kind"),
            "status": record.get("status"),
            "evidence_kind": record.get("kind"),
            "confidence": record.get("confidence"),
            "metadata": deepcopy(record.get("metadata") or {}),
        })
        for relation in ("supports", "contradicts", "derived_from"):
            values = record.get(relation) or []
            if isinstance(values, str):
                values = [values]
            for target in values:
                edges.append({"src": evidence_id, "dst": target, "relation": relation.upper()})

    object_groups = (
        ("decisions", "decision", "decision_id", "SUPPORTS_DECISION"),
        ("obligations", "obligation", "obligation_id", "SUPPORTS_OBLIGATION"),
        ("conflicts", "conflict", "conflict_id", "SUPPORTS_CONFLICT"),
        ("explanations", "explanation", "explanation_id", "SUPPORTS_EXPLANATION"),
        ("constraints", "constraint", "constraint_id", "SUPPORTS_CONSTRAINT"),
    )
    for group_name, kind, id_key, relation in object_groups:
        for row in calculus.get(group_name, {}).values():
            object_id = row.get(id_key)
            nodes.append({
                "id": object_id,
                "kind": kind,
                "label": row.get("statement") or row.get("subject") or object_id,
                "status": row.get("status"),
            })
            for evidence_id in row.get("evidence_ids", []):
                edges.append({"src": evidence_id, "dst": object_id, "relation": relation})
    for certificate in assurance.get("certificates", {}).values():
        certificate_id = certificate.get("certificate_id")
        nodes.append({
            "id": certificate_id,
            "kind": "certificate",
            "label": certificate.get("kind"),
            "status": certificate.get("status"),
        })
        for evidence_id in (certificate.get("payload") or {}).get("evidence_ids", []):
            edges.append({
                "src": evidence_id,
                "dst": certificate_id,
                "relation": "SUPPORTS_CERTIFICATE",
            })
    return _closed_graph(
        "evidence-graph",
        "EVIDENCE",
        nodes,
        edges,
        {"record_count": len(records)},
    )


def causal_graph(snapshot: Any) -> ObservableGraph:
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    assurance = deepcopy(getattr(snapshot, "assurance_state", {}) or {})
    candidate_state = deepcopy(getattr(snapshot, "candidate_state", {}) or {})
    evidence = evidence_graph(snapshot)
    nodes = deepcopy(evidence.nodes)
    edges = deepcopy(evidence.edges)

    for edge in calculus.get("decision_edges", []):
        edges.append({"src": edge.get("src"), "dst": edge.get("dst"), "relation": edge.get("relation", "DEPENDS_ON")})
    for edge in calculus.get("obligation_edges", []):
        edges.append({"src": edge.get("src"), "dst": edge.get("dst"), "relation": edge.get("relation", "REQUIRES")})

    for obligation in calculus.get("obligations", {}).values():
        obligation_id = obligation.get("obligation_id")
        for decision_id in obligation.get("decision_dependencies", []):
            edges.append({"src": decision_id, "dst": obligation_id, "relation": "AUTHORIZES"})
        for lock_id in obligation.get("lock_ids", []):
            edges.append({"src": lock_id, "dst": obligation_id, "relation": "LOCKS"})

    for lock in calculus.get("locks", {}).values():
        lock_id = lock.get("lock_id")
        nodes.append({
            "id": lock_id,
            "kind": "lock",
            "label": lock.get("reason"),
            "status": lock.get("status"),
            "condition": deepcopy(lock.get("condition")),
        })
        edges.append({"src": lock.get("origin_decision_id"), "dst": lock_id, "relation": "CREATES_LOCK"})

    for conflict in calculus.get("conflicts", {}).values():
        conflict_id = conflict.get("conflict_id")
        for decision_id in conflict.get("implicated_decision_ids", []):
            edges.append({"src": decision_id, "dst": conflict_id, "relation": "IMPLICATED_IN"})
        for explanation_id in conflict.get("explanation_ids", []):
            edges.append({"src": conflict_id, "dst": explanation_id, "relation": "EXPLAINED_BY"})
        for constraint_id in conflict.get("learned_constraint_ids", []):
            edges.append({"src": conflict_id, "dst": constraint_id, "relation": "LEARNS"})

    for explanation in calculus.get("explanations", {}).values():
        explanation_id = explanation.get("explanation_id")
        for literal in explanation.get("assumption_literals", []):
            if literal.get("decision_id"):
                edges.append({
                    "src": literal.get("decision_id"),
                    "dst": explanation_id,
                    "relation": "CAUSAL_LITERAL",
                })
        predecessor = explanation.get("supersedes_explanation_id")
        if predecessor:
            edges.append({"src": predecessor, "dst": explanation_id, "relation": "SUPERSEDED_BY"})

    for constraint in calculus.get("constraints", {}).values():
        constraint_id = constraint.get("constraint_id")
        edges.append({
            "src": constraint.get("source_explanation_id"),
            "dst": constraint_id,
            "relation": "PROJECTS_TO",
        })
        if constraint.get("certificate_id"):
            edges.append({
                "src": constraint_id,
                "dst": constraint.get("certificate_id"),
                "relation": "CERTIFIED_BY",
            })

    for certificate in assurance.get("certificates", {}).values():
        certificate_id = certificate.get("certificate_id")
        verification_id = certificate.get("verification_id")
        if verification_id:
            edges.append({"src": certificate_id, "dst": verification_id, "relation": "VERIFIED_BY"})
    for verification in assurance.get("verifications", {}).values():
        nodes.append({
            "id": verification.get("verification_id"),
            "kind": "verification",
            "label": verification.get("verifier_id"),
            "status": "ACCEPTED" if verification.get("valid") is True else "REJECTED",
            "level": verification.get("level"),
        })

    for lifecycle in candidate_state.get("candidates", {}).values():
        candidate = lifecycle.get("candidate", {})
        candidate_id = candidate.get("candidate_id")
        nodes.append({
            "id": candidate_id,
            "kind": "candidate",
            "label": candidate.get("backend_id"),
            "status": lifecycle.get("status"),
            "score": candidate.get("score"),
        })
        for subject, decision_id in (candidate.get("assignments") or {}).items():
            edges.append({
                "src": candidate_id,
                "dst": decision_id,
                "relation": "PROPOSES",
                "metadata": {"subject": subject},
            })

    return _closed_graph(
        "causal-graph",
        "CAUSAL",
        nodes,
        edges,
        {
            "machine_id": getattr(snapshot, "machine_id", ""),
            "epoch": calculus.get("epoch", 0),
        },
    )


def conflict_timeline(snapshot: Any) -> list[dict[str, Any]]:
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    rows: list[dict[str, Any]] = []
    for conflict in calculus.get("conflicts", {}).values():
        conflict_id = conflict.get("conflict_id")
        rows.append({
            "sequence": int(conflict.get("created_sequence", 0)),
            "type": "CONFLICT_CREATED",
            "conflict_id": conflict_id,
            "kind": conflict.get("kind"),
            "status": "OPEN",
            "implicated_decision_ids": list(conflict.get("implicated_decision_ids") or []),
        })
        for explanation_id in conflict.get("explanation_ids", []):
            explanation = calculus.get("explanations", {}).get(explanation_id, {})
            rows.append({
                "sequence": int(explanation.get("created_sequence", 0)),
                "type": "CONFLICT_EXPLAINED",
                "conflict_id": conflict_id,
                "explanation_id": explanation_id,
                "status": explanation.get("status"),
                "minimality": explanation.get("minimality"),
            })
        for constraint_id in conflict.get("learned_constraint_ids", []):
            constraint = calculus.get("constraints", {}).get(constraint_id, {})
            rows.append({
                "sequence": int(constraint.get("created_sequence", 0)),
                "type": "CONSTRAINT_LEARNED",
                "conflict_id": conflict_id,
                "constraint_id": constraint_id,
                "status": constraint.get("status"),
                "strength": constraint.get("strength"),
            })
        if conflict.get("resolved_sequence") is not None:
            rows.append({
                "sequence": int(conflict.get("resolved_sequence", 0)),
                "type": "CONFLICT_BACKJUMPED" if conflict.get("backjump") else "CONFLICT_RESOLVED",
                "conflict_id": conflict_id,
                "status": conflict.get("status"),
                "backjump": deepcopy(conflict.get("backjump")),
            })
    return sorted(
        rows,
        key=lambda row: (int(row.get("sequence", 0)), str(row.get("conflict_id")), str(row.get("type"))),
    )


def fairness_debt(snapshot: Any) -> list[dict[str, Any]]:
    calculus = deepcopy(getattr(snapshot, "calculus", {}) or {})
    fairness = calculus.get("fairness", {})
    policy = deepcopy(fairness.get("policy") or {})
    records = fairness.get("records", {})
    rows = []
    for obligation_id, record in records.items():
        obligation = calculus.get("obligations", {}).get(obligation_id, {})
        active_lock_ids = [
            lock_id
            for lock_id in obligation.get("lock_ids", [])
            if calculus.get("locks", {}).get(lock_id, {}).get("status") == "ACTIVE"
        ]
        active_lock_reasons = [
            calculus["locks"][lock_id].get("reason") for lock_id in active_lock_ids
        ]
        hidden = int(record.get("hidden_epochs", 0))
        lock_age = int(record.get("continuous_lock_epochs", 0))
        lock_count = int(record.get("lock_count", 0))
        status = record.get("fairness_status", record.get("status", "NORMAL"))
        next_action = "NONE"
        if status == "OVERDUE":
            next_action = "EXPOSE_OR_DISPOSITION"
        elif status == "DUE":
            next_action = "REVIEW"
        rows.append({
            "obligation_id": obligation_id,
            "obligation_status": obligation.get("status"),
            "status": status,
            "hidden_epochs": hidden,
            "continuous_lock_epochs": lock_age,
            "lock_count": lock_count,
            "thresholds": {
                "max_hidden_epochs": policy.get("max_hidden_epochs"),
                "max_lock_age_epochs": policy.get("max_lock_age_epochs"),
                "max_lock_count": policy.get("max_lock_count"),
            },
            "over_by": {
                "hidden_epochs": max(0, hidden - int(policy.get("max_hidden_epochs", hidden))),
                "lock_age_epochs": max(0, lock_age - int(policy.get("max_lock_age_epochs", lock_age))),
                "lock_count": max(0, lock_count - int(policy.get("max_lock_count", lock_count))),
            },
            "active_lock_ids": active_lock_ids,
            "active_lock_reasons": active_lock_reasons,
            "last_considered_epoch": record.get("last_considered_epoch"),
            "last_enabled_epoch": record.get("last_enabled_epoch"),
            "last_reviewed_epoch": record.get("last_reviewed_epoch"),
            "next_action": next_action,
        })
    order = {"OVERDUE": 0, "DUE": 1, "NORMAL": 2}
    return sorted(rows, key=lambda row: (order.get(str(row["status"]), 3), -row["hidden_epochs"], row["obligation_id"]))


def _event_operation(event: Any) -> str | None:
    data = deepcopy(getattr(event, "data", {}) or {})
    operation = data.get("operation")
    if operation:
        return str(operation)
    patch = data.get("patch") or {}
    candidate_history = (patch.get("candidate_state") or {}).get("backend_history") or []
    if candidate_history and candidate_history[-1].get("operation"):
        return str(candidate_history[-1]["operation"])
    return None


def event_timeline(events: Iterable[Any]) -> list[dict[str, Any]]:
    rows = []
    operation_categories = {
        "CANDIDATE_BATCH_GENERATED": "CANDIDATE",
        "CANDIDATE_ACTIVATED": "CANDIDATE",
        "SEARCH_BACKJUMPED": "BACKJUMP",
        "SEARCH_RESTARTED": "RESTART",
        "CERTIFICATE_REGISTERED": "ASSURANCE",
        "CERTIFICATE_VERIFIED": "ASSURANCE",
        "HISTORY_CHECKED": "ASSURANCE",
        "PROFILE_BOUND": "PROFILE",
    }
    for event in events:
        reason = str(getattr(event, "reason", ""))
        event_type = str(getattr(event, "event_type", ""))
        operation = _event_operation(event)
        category = operation_categories.get(operation or "")
        if category is None:
            lowered = reason.lower()
            if "backjump" in lowered:
                category = "BACKJUMP"
            elif "restart" in lowered:
                category = "RESTART"
            elif "profile evolution" in lowered or ("profile" in lowered and "bound" in lowered):
                category = "PROFILE"
            elif "candidate" in lowered:
                category = "CANDIDATE"
            elif "certificate" in lowered or "assurance" in lowered or "history" in lowered:
                category = "ASSURANCE"
        if category is None:
            continue
        rows.append({
            "sequence": int(getattr(event, "sequence", 0)),
            "ts": float(getattr(event, "ts", 0.0)),
            "category": category,
            "operation": operation,
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
        "causal_graph": causal_graph(snapshot).to_dict(),
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
