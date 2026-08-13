from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

TRACE_CONTRACT_ID = "aasm.trace.v1"
TRACE_CONTRACT_VERSION = "0.1.0"
SEMANTIC_TRACE_CONTRACT_ID = "aasm.trace.semantic.v1"
SEMANTIC_TRACE_CONTRACT_VERSION = "0.1.0"

KNOWN_EVENT_TYPES = {
    "machine_created", "machine_forked", "transition_committed", "snapshot_patched",
    "checkpoint_created", "checkpoint_restored", "goal_received", "proposal", "authorized",
    "result", "test_passed", "test_failed", "invariant_failed", "assumption_invalidated",
    "dependency_discovered", "better_path_found", "resource_exhausted", "user_interrupt",
    "acceptance_satisfied", "effect_proposed", "effect_authorized", "effect_started",
    "effect_succeeded", "effect_failed", "effect_unknown", "effect_cancelled", "effect_reconciled",
    "plan_node_added", "plan_edge_added", "plan_node_updated", "plan_node_pruned", "memory_put",
    "memory_invalidated", "evidence_added", "evidence_invalidated", "resource_registered",
    "resource_updated", "schedule_computed", "worker_registered", "worker_updated",
    "worker_heartbeat", "quota_set", "lease_claimed", "lease_heartbeat", "lease_completed",
    "lease_failed", "lease_released", "lease_expired",
}

TRANSITION_CLASSES = {
    "machine_created": "MACHINE_LIFECYCLE",
    "machine_forked": "MACHINE_LIFECYCLE",
    "transition_committed": "STATE_TRANSITION",
    "snapshot_patched": "CANONICAL_PATCH",
    "checkpoint_created": "CHECKPOINT",
    "checkpoint_restored": "CHECKPOINT",
    "evidence_added": "EVIDENCE",
    "evidence_invalidated": "EVIDENCE",
    "effect_proposed": "EFFECT",
    "effect_authorized": "EFFECT",
    "effect_started": "EFFECT",
    "effect_succeeded": "EFFECT",
    "effect_failed": "EFFECT",
    "effect_unknown": "EFFECT",
    "effect_cancelled": "EFFECT",
    "effect_reconciled": "EFFECT",
    "lease_claimed": "LEASE",
    "lease_heartbeat": "LEASE",
    "lease_completed": "LEASE",
    "lease_failed": "LEASE",
    "lease_released": "LEASE",
    "lease_expired": "LEASE",
}

SEMANTIC_RULES = {
    "hard_constraint_certified": "HARD_CONSTRAINT_WITHOUT_VERIFIED_CERTIFICATE",
    "candidate_activation_atomic": "PARTIAL_CANDIDATE_ACTIVATION",
    "restart_retains_hard_knowledge": "RESTART_LOST_HARD_KNOWLEDGE",
    "restart_retains_pinned_decisions": "RESTART_LOST_PINNED_DECISION",
    "completion_resolves_mandatory": "COMPLETION_WITH_UNRESOLVED_MANDATORY",
    "backjump_deactivates_target": "BACKJUMP_TARGET_REMAINS_ACTIVE",
    "operational_event_preserves_calculus": "OPERATIONAL_EVENT_CHANGED_CALCULUS_ABSTRACTION",
}


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _event_mapping(event: Any) -> dict[str, Any]:
    if isinstance(event, Mapping):
        return dict(event)
    if is_dataclass(event):
        return asdict(event)
    if hasattr(event, "to_dict"):
        value = event.to_dict()
        if isinstance(value, Mapping):
            return dict(value)
    if hasattr(event, "__dict__"):
        return dict(vars(event))
    raise TypeError(f"unsupported event representation: {type(event)!r}")


def _normalized_event(event: Any, index: int) -> dict[str, Any]:
    raw = _event_mapping(event)
    event_id = str(raw.get("event_id") or raw.get("id") or f"event-{index}")
    sequence = int(raw.get("sequence") or raw.get("seq") or index + 1)
    event_type = str(raw.get("event_type") or raw.get("type") or "UNKNOWN")
    machine_id = str(raw.get("machine_id") or "")
    return {
        "event_id": event_id,
        "sequence": sequence,
        "event_type": event_type,
        "machine_id": machine_id,
        "source_event": raw,
    }


def _events_from_source(source: Any) -> list[Any]:
    if isinstance(source, Mapping):
        if isinstance(source.get("events"), Sequence):
            return list(source["events"])
        raise ValueError("snapshot-only input is not a production event history")
    if isinstance(source, Sequence) and not isinstance(source, (str, bytes, bytearray)):
        return list(source)
    events = getattr(source, "events", None)
    if events is not None:
        return list(events)
    raise TypeError("trace projection requires ordered durable events or an engine exposing .events")


@dataclass(frozen=True)
class TraceIssue:
    code: str
    event_id: str
    sequence: int
    message: str
    severity: str = "ERROR"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def trace_contract() -> dict[str, Any]:
    return {
        "contract_id": TRACE_CONTRACT_ID,
        "contract_version": TRACE_CONTRACT_VERSION,
        "semantic_contract_id": SEMANTIC_TRACE_CONTRACT_ID,
        "semantic_contract_version": SEMANTIC_TRACE_CONTRACT_VERSION,
        "source": "AUTHORITATIVE_DURABLE_EVENT_HISTORY",
        "unknown_transition_policy": "UNSUPPORTED_EXPLICIT",
        "snapshot_only_input": "REJECTED",
        "ordering": "SOURCE_ORDER_PRESERVED",
        "digest": "SHA-256_CANONICAL_JSON",
    }


def project_trace(source: Any) -> dict[str, Any]:
    events = _events_from_source(source)
    rows: list[dict[str, Any]] = []
    issues: list[TraceIssue] = []
    prior_sequence: int | None = None
    machine_ids: set[str] = set()
    for index, event in enumerate(events):
        normalized = _normalized_event(event, index)
        sequence = normalized["sequence"]
        event_id = normalized["event_id"]
        event_type = normalized["event_type"]
        machine_id = normalized["machine_id"]
        if machine_id:
            machine_ids.add(machine_id)
        if prior_sequence is not None and sequence <= prior_sequence:
            issues.append(TraceIssue(
                "NON_MONOTONIC_SEQUENCE", event_id, sequence,
                f"event sequence {sequence} does not follow {prior_sequence}",
            ))
        prior_sequence = sequence
        supported = event_type in KNOWN_EVENT_TYPES
        transition_class = TRANSITION_CLASSES.get(event_type, "OPERATIONAL" if supported else "UNSUPPORTED")
        if not supported:
            issues.append(TraceIssue(
                "UNSUPPORTED_TRANSITION", event_id, sequence,
                f"event type {event_type!r} has no declared trace abstraction",
                severity="WARNING",
            ))
        digest = _sha256(normalized["source_event"])
        rows.append({
            "event_id": event_id,
            "source_sequence": sequence,
            "event_type": event_type,
            "transition_class": transition_class,
            "support_status": "SUPPORTED" if supported else "UNSUPPORTED",
            "source_sha256": digest,
            "source_event": normalized["source_event"],
        })
    if len(machine_ids) > 1:
        issues.append(TraceIssue(
            "MULTIPLE_MACHINE_IDS", rows[0]["event_id"] if rows else "", rows[0]["source_sequence"] if rows else 0,
            f"trace contains events from multiple machines: {sorted(machine_ids)}",
        ))
    source_trace_hash = _sha256([
        {"event_id": row["event_id"], "sequence": row["source_sequence"], "sha256": row["source_sha256"]}
        for row in rows
    ])
    projection_hash = _sha256([
        {k: row[k] for k in ("event_id", "source_sequence", "event_type", "transition_class", "support_status", "source_sha256")}
        for row in rows
    ])
    return {
        "contract_id": TRACE_CONTRACT_ID,
        "contract_version": TRACE_CONTRACT_VERSION,
        "schema_version": 1,
        "event_count": len(rows),
        "machine_ids": sorted(machine_ids),
        "source_trace_sha256": source_trace_hash,
        "projection_sha256": projection_hash,
        "steps": rows,
        "issues": [issue.to_dict() for issue in issues],
        "unsupported_event_types": sorted({row["event_type"] for row in rows if row["support_status"] == "UNSUPPORTED"}),
        "valid": not any(issue.severity == "ERROR" for issue in issues),
    }


def semantic_trace_check(source: Any) -> dict[str, Any]:
    projection = project_trace(source)
    issues: list[dict[str, Any]] = []
    checked = 0
    unsupported: list[dict[str, Any]] = []
    for step in projection["steps"]:
        event = step["source_event"]
        data = event.get("data") or {}
        witness = data.get("semantic_witness") if isinstance(data, Mapping) else None
        if not isinstance(witness, Mapping):
            unsupported.append({
                "event_id": step["event_id"],
                "source_sequence": step["source_sequence"],
                "reason": "NO_SEMANTIC_WITNESS",
            })
            continue
        checked += 1
        pre_hash = _sha256(witness.get("pre_state", {}))
        post_hash = _sha256(witness.get("post_state", {}))
        properties = witness.get("properties") or {}
        for property_name, issue_code in SEMANTIC_RULES.items():
            if property_name not in properties:
                continue
            if bool(properties[property_name]):
                continue
            issues.append({
                "event_id": step["event_id"],
                "source_sequence": step["source_sequence"],
                "issue_code": issue_code,
                "message": f"semantic witness failed property {property_name}",
                "pre_state_fingerprint": pre_hash,
                "post_state_fingerprint": post_hash,
            })
    payload = {
        "contract_id": SEMANTIC_TRACE_CONTRACT_ID,
        "contract_version": SEMANTIC_TRACE_CONTRACT_VERSION,
        "schema_version": 1,
        "source_trace_sha256": projection["source_trace_sha256"],
        "checked_event_count": checked,
        "unsupported_event_count": len(unsupported),
        "unsupported": unsupported,
        "issues": issues,
        "status": "FAIL" if issues else ("INCONCLUSIVE" if checked == 0 and projection["event_count"] else "PASS"),
    }
    payload["report_sha256"] = _sha256(payload)
    return payload


def build_trace_corpus(histories: Mapping[str, Any]) -> dict[str, Any]:
    entries = []
    for name in sorted(histories):
        projection = project_trace(histories[name])
        semantic = semantic_trace_check(histories[name])
        entries.append({
            "name": name,
            "source_trace_sha256": projection["source_trace_sha256"],
            "projection_sha256": projection["projection_sha256"],
            "semantic_report_sha256": semantic["report_sha256"],
            "event_count": projection["event_count"],
            "unsupported_event_types": projection["unsupported_event_types"],
            "semantic_status": semantic["status"],
        })
    corpus = {
        "contract_id": "aasm.trace.corpus.v1",
        "contract_version": "0.1.0",
        "schema_version": 1,
        "entries": entries,
    }
    corpus["corpus_sha256"] = _sha256(entries)
    return corpus


__all__ = [
    "TRACE_CONTRACT_ID", "TRACE_CONTRACT_VERSION", "SEMANTIC_TRACE_CONTRACT_ID",
    "SEMANTIC_TRACE_CONTRACT_VERSION", "TraceIssue", "trace_contract", "project_trace",
    "semantic_trace_check", "build_trace_corpus",
]
