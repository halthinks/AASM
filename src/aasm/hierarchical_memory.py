from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
import json
from typing import Any, Mapping, Sequence

from .semantic_result import canonical_semantic_json, semantic_fingerprint
from .scopes import ROOT_SCOPE_ID, scope_flow_allowed

HIERARCHICAL_MEMORY_CONTRACT_ID = "aasm.memory.hierarchical.v1"
HIERARCHICAL_MEMORY_CONTRACT_VERSION = "0.1.0"
MEMORY_INDEX_CONTRACT_ID = "aasm.memory.index.v1"
MEMORY_INDEX_CONTRACT_VERSION = "0.1.0"
REASONING_FRONTIER_CONTRACT_ID = "aasm.reasoning.frontier.v1"
REASONING_FRONTIER_CONTRACT_VERSION = "0.1.0"
CONTEXT_PROJECTION_CONTRACT_ID = "aasm.context.projection.v1"
CONTEXT_PROJECTION_CONTRACT_VERSION = "0.1.0"

MEMORY_KINDS = ("SENSORY", "WORKING", "EPISODIC", "SEMANTIC", "PROCEDURAL")
MEMORY_SUBSTRATES = ("TEXT_RECORD", "STRUCTURED", "REFERENCE", "EXECUTION_SNAPSHOT")
MEMORY_OPERATIONS = ("STORE", "UPDATE", "COMPRESS", "CONSOLIDATE", "FORGET")
MEMORY_PRIVACY_LEVELS = ("AGENT", "USER", "SHARED", "PUBLIC")
MEMORY_INDEX_KINDS = ("VECTOR", "LEXICAL", "GRAPH", "TREE", "RERANK")
_TERMINAL_REASONING = {"STALE", "REFUTED", "REJECTED"}
_STRENGTH = {None: 0.0, "": 0.0, "SOLVER_VERDICT": .25, "MULTI_SOLVER_AGREEMENT": .5, "CHECKED_CERTIFICATE": .75, "TRUSTED_KERNEL": 1.0}


def _jsonable(value: Any) -> Any:
    if hasattr(value, "to_dict"): return _jsonable(value.to_dict())
    if isinstance(value, Mapping): return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)): return [_jsonable(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None: return value
    raise TypeError(f"hierarchical memory value is not JSON serializable: {type(value)!r}")


def _uniq(values: Sequence[str]) -> tuple[str, ...]: return tuple(sorted(set(map(str, values))))


def _retention(policy: str) -> tuple[str, int | None]:
    raw = str(policy or "permanent").lower()
    if raw in {"permanent", "forgettable"}: return raw, None
    if raw.startswith("ttl:"):
        try: seconds = int(raw.split(":", 1)[1])
        except Exception as exc: raise ValueError("ttl retention must be ttl:<positive-seconds>") from exc
        if seconds <= 0: raise ValueError("ttl retention must be positive")
        return "ttl", seconds
    raise ValueError("retention_policy must be permanent, forgettable, or ttl:<seconds>")


@dataclass(frozen=True)
class MemoryObject:
    scope_id: str
    kind: str
    substrate: str
    content: Any
    created_by_decision: str
    source_evidence_ids: tuple[str, ...] = ()
    semantic_artifact_ids: tuple[str, ...] = ()
    causal_parent_memory_ids: tuple[str, ...] = ()
    supersedes_memory_ids: tuple[str, ...] = ()
    retention_policy: str = "permanent"
    privacy_level: str = "AGENT"
    compatibility_fingerprint: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    version: int = 1
    memory_id: str = ""

    def __post_init__(self):
        if not self.scope_id or not self.created_by_decision: raise ValueError("memory scope_id and created_by_decision are required")
        if self.kind not in MEMORY_KINDS: raise ValueError(f"invalid memory kind: {self.kind}")
        if self.substrate not in MEMORY_SUBSTRATES: raise ValueError(f"invalid memory substrate: {self.substrate}")
        if self.privacy_level not in MEMORY_PRIVACY_LEVELS: raise ValueError(f"invalid memory privacy level: {self.privacy_level}")
        if self.version < 1: raise ValueError("memory version must be >= 1")
        _retention(self.retention_policy)
        object.__setattr__(self, "source_evidence_ids", _uniq(self.source_evidence_ids))
        object.__setattr__(self, "semantic_artifact_ids", _uniq(self.semantic_artifact_ids))
        object.__setattr__(self, "causal_parent_memory_ids", _uniq(self.causal_parent_memory_ids))
        object.__setattr__(self, "supersedes_memory_ids", _uniq(self.supersedes_memory_ids))
        _jsonable(self.content); _jsonable(self.metadata)
        if self.substrate == "EXECUTION_SNAPSHOT" and not self.compatibility_fingerprint: raise ValueError("execution snapshots require compatibility_fingerprint")
        if self.kind == "SEMANTIC" and not self.semantic_artifact_ids: raise ValueError("semantic memory must reference admitted reasoning artifacts")
        if not self.memory_id: object.__setattr__(self, "memory_id", f"memory-{semantic_fingerprint(self.identity_payload())[:20]}")

    def identity_payload(self):
        return {"scope_id": self.scope_id, "kind": self.kind, "substrate": self.substrate, "content": _jsonable(self.content), "created_by_decision": self.created_by_decision, "source_evidence_ids": list(self.source_evidence_ids), "semantic_artifact_ids": list(self.semantic_artifact_ids), "causal_parent_memory_ids": list(self.causal_parent_memory_ids), "supersedes_memory_ids": list(self.supersedes_memory_ids), "retention_policy": self.retention_policy, "privacy_level": self.privacy_level, "compatibility_fingerprint": self.compatibility_fingerprint, "metadata": _jsonable(self.metadata), "version": self.version}
    @property
    def fingerprint(self): return semantic_fingerprint({"memory_id": self.memory_id, **self.identity_payload()})
    def to_dict(self): return {"memory_id": self.memory_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data):
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class MemoryTombstone:
    memory_id: str
    decision_id: str
    reason: str
    mode: str = "VISIBILITY_REVOKED"
    metadata: dict[str, Any] = field(default_factory=dict)
    tombstone_id: str = ""
    def __post_init__(self):
        if not self.memory_id or not self.decision_id or not self.reason.strip(): raise ValueError("memory tombstone requires memory_id, decision_id, and reason")
        if self.mode not in {"VISIBILITY_REVOKED", "CRYPTO_ERASURE_REQUESTED", "RETENTION_EXPIRED"}: raise ValueError("invalid memory tombstone mode")
        _jsonable(self.metadata)
        if not self.tombstone_id: object.__setattr__(self, "tombstone_id", f"memory-tombstone-{semantic_fingerprint(self.payload())[:20]}")
    def payload(self): return {"memory_id": self.memory_id, "decision_id": self.decision_id, "reason": self.reason, "mode": self.mode, "metadata": _jsonable(self.metadata)}
    @property
    def fingerprint(self): return semantic_fingerprint({"tombstone_id": self.tombstone_id, **self.payload()})
    def to_dict(self): return {"tombstone_id": self.tombstone_id, **self.payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data):
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class MemoryIndexEntry:
    memory_id: str
    memory_fingerprint: str
    index_kind: str
    indexer_id: str
    indexer_version: str
    score: float | None = None
    payload: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)
    index_entry_id: str = ""
    def __post_init__(self):
        if not all((self.memory_id, self.memory_fingerprint, self.indexer_id, self.indexer_version)): raise ValueError("memory index identity fields are required")
        if self.index_kind not in MEMORY_INDEX_KINDS: raise ValueError(f"invalid memory index kind: {self.index_kind}")
        if self.score is not None and not 0 <= self.score <= 1: raise ValueError("memory index score must be in [0,1]")
        _jsonable(self.payload); _jsonable(self.metadata)
        if not self.index_entry_id: object.__setattr__(self, "index_entry_id", f"memory-index-{semantic_fingerprint(self.identity_payload())[:20]}")
    def identity_payload(self): return {"memory_id": self.memory_id, "memory_fingerprint": self.memory_fingerprint, "index_kind": self.index_kind, "indexer_id": self.indexer_id, "indexer_version": self.indexer_version, "score": self.score, "payload": _jsonable(self.payload), "metadata": _jsonable(self.metadata)}
    @property
    def fingerprint(self): return semantic_fingerprint({"index_entry_id": self.index_entry_id, **self.identity_payload()})
    def to_dict(self): return {"index_entry_id": self.index_entry_id, **self.identity_payload(), "fingerprint": self.fingerprint}
    @classmethod
    def from_dict(cls, data):
        payload = deepcopy(dict(data)); payload.pop("fingerprint", None); return cls(**payload)


@dataclass(frozen=True)
class ContextProjectionRequest:
    scope_id: str = ROOT_SCOPE_ID
    query: str = ""
    allowed_privacy_levels: tuple[str, ...] = ("AGENT", "USER", "SHARED", "PUBLIC")
    memory_kinds: tuple[str, ...] = ()
    objective_node_ids: tuple[str, ...] = ()
    max_memory_items: int = 20
    max_frontier_items: int = 20
    max_chars: int = 12000
    include_stale: bool = False
    as_of: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def __post_init__(self):
        if not self.scope_id: raise ValueError("context scope_id is required")
        object.__setattr__(self, "allowed_privacy_levels", _uniq(self.allowed_privacy_levels)); object.__setattr__(self, "memory_kinds", _uniq(self.memory_kinds)); object.__setattr__(self, "objective_node_ids", _uniq(self.objective_node_ids))
        if not set(self.allowed_privacy_levels).issubset(MEMORY_PRIVACY_LEVELS): raise ValueError("invalid context privacy level")
        if self.memory_kinds and not set(self.memory_kinds).issubset(MEMORY_KINDS): raise ValueError("invalid context memory kind")
        if min(self.max_memory_items, self.max_frontier_items, self.max_chars) < 0: raise ValueError("context budgets must be non-negative")
        _jsonable(self.metadata)
    @property
    def fingerprint(self): return semantic_fingerprint(self.to_dict())
    def to_dict(self): return _jsonable(asdict(self))


def hierarchical_memory_contract():
    return {"contract_id": HIERARCHICAL_MEMORY_CONTRACT_ID, "contract_version": HIERARCHICAL_MEMORY_CONTRACT_VERSION, "index_contract_id": MEMORY_INDEX_CONTRACT_ID, "index_contract_version": MEMORY_INDEX_CONTRACT_VERSION, "frontier_contract_id": REASONING_FRONTIER_CONTRACT_ID, "frontier_contract_version": REASONING_FRONTIER_CONTRACT_VERSION, "context_contract_id": CONTEXT_PROJECTION_CONTRACT_ID, "context_contract_version": CONTEXT_PROJECTION_CONTRACT_VERSION, "mutation_path": "DECISION_TO_OBLIGATION_TO_EVIDENCE", "semantic_memory_truth": "REFERENCES_V37_ADMITTED_REASONING", "derived_indexes": "NOT_MEMORY_IDENTITY", "embeddings": "DERIVED_INDEX_ONLY", "forgetting": "TOMBSTONE_NOT_HISTORY_DELETION", "legacy_dp_memory": "PRESERVED_COMPATIBILITY_CACHE", "stale_default": "EXCLUDED", "scope_policy": "AASM_SCOPES_FLOW", "context_budget": "DETERMINISTIC_BOUNDED", "retention_clock": "EXPLICIT_OR_DURABLE_EVENT_TIME"}


def memory_document(value): return canonical_semantic_json(value.to_dict())


def project_memory_evidence(records, *, reasoning_states=None, semantic_signals=None, as_of=None):
    reasoning_states = dict(reasoning_states or {}); semantic_signals = dict(semantic_signals or {})
    memories, tombstones, indexes, issues = {}, {}, {}, []
    effective_as_of = float(as_of) if as_of is not None else max([float(r.get("created_at", 0) or 0) for r in records] or [0.0])
    for row in records:
        meta, kind = row.get("metadata") or {}, row.get("kind")
        try:
            data = json.loads(str(row.get("statement") or "{}"))
            if kind == "hierarchical_memory_object" and meta.get("memory_record_type") == "OBJECT":
                item = MemoryObject.from_dict(data)
                if item.fingerprint != meta.get("memory_fingerprint"): raise ValueError("memory fingerprint mismatch")
                if item.memory_id in memories and memories[item.memory_id]["memory"]["fingerprint"] != item.fingerprint: raise ValueError("memory ID collision")
                memories[item.memory_id] = {"memory": item.to_dict(), "evidence_id": str(row.get("evidence_id")), "created_at": float(row.get("created_at", 0) or 0)}
            elif kind == "hierarchical_memory_tombstone" and meta.get("memory_record_type") == "TOMBSTONE":
                item = MemoryTombstone.from_dict(data)
                if item.fingerprint != meta.get("tombstone_fingerprint"): raise ValueError("memory tombstone fingerprint mismatch")
                tombstones.setdefault(item.memory_id, []).append({"tombstone": item.to_dict(), "evidence_id": str(row.get("evidence_id"))})
            elif kind == "hierarchical_memory_index" and meta.get("memory_record_type") == "INDEX":
                item = MemoryIndexEntry.from_dict(data)
                if item.fingerprint != meta.get("index_fingerprint"): raise ValueError("memory index fingerprint mismatch")
                indexes.setdefault(item.memory_id, []).append({"index": item.to_dict(), "evidence_id": str(row.get("evidence_id"))})
        except Exception as exc:
            if kind in {"hierarchical_memory_object", "hierarchical_memory_tombstone", "hierarchical_memory_index"}: issues.append(f"{row.get('evidence_id', '?')}: {exc}")
    superseded = {mid for row in memories.values() for mid in row["memory"].get("supersedes_memory_ids", [])}
    current = {}
    for mid, row in sorted(memories.items()):
        mem = row["memory"]
        for idx in indexes.get(mid, []):
            if idx["index"]["memory_fingerprint"] != mem["fingerprint"]: issues.append(f"index fingerprint does not match canonical memory: {mid}")
        retention_kind, ttl = _retention(mem["retention_policy"])
        expired = retention_kind == "ttl" and effective_as_of >= row["created_at"] + float(ttl or 0)
        states = [reasoning_states.get(aid, "UNKNOWN") for aid in mem.get("semantic_artifact_ids", [])]
        stale = any(s in _TERMINAL_REASONING for s in states)
        status = "REVOKED" if tombstones.get(mid) else "EXPIRED" if expired else "SUPERSEDED" if mid in superseded else "STALE" if stale else "ACTIVE"
        current[mid] = {**deepcopy(row), "status": status, "semantic_states": states, "semantic_signals": {aid: deepcopy(semantic_signals.get(f"ARTIFACT:{aid}", {})) for aid in mem.get("semantic_artifact_ids", [])}, "tombstones": deepcopy(tombstones.get(mid, [])), "indexes": deepcopy(indexes.get(mid, []))}
    fingerprint = semantic_fingerprint({k: {"memory": v["memory"], "status": v["status"]} for k, v in sorted(current.items())})
    return {"contract": hierarchical_memory_contract(), "valid": not issues, "issues": issues, "as_of": effective_as_of, "memories": current, "counts": {"total": len(current), "active": sum(v["status"] == "ACTIVE" for v in current.values()), "revoked": sum(v["status"] == "REVOKED" for v in current.values()), "stale": sum(v["status"] == "STALE" for v in current.values()), "expired": sum(v["status"] == "EXPIRED" for v in current.values())}, "projection_fingerprint": fingerprint}


def _terms(value): return {x for x in "".join(ch.lower() if ch.isalnum() else " " for ch in str(value)).split() if x}
def _lexical(query, value):
    q = _terms(query)
    return 0.0 if not q else len(q & _terms(canonical_semantic_json(_jsonable(value)))) / len(q)


def select_memory_context(projection, scope_state, request):
    rows = []
    for mid, entry in projection.get("memories", {}).items():
        mem = entry["memory"]
        if entry["status"] != "ACTIVE" and not request.include_stale: continue
        if mem["privacy_level"] not in request.allowed_privacy_levels: continue
        if request.memory_kinds and mem["kind"] not in request.memory_kinds: continue
        try:
            if not scope_flow_allowed(dict(scope_state), mem["scope_id"], request.scope_id): continue
        except KeyError: continue
        signals = list((entry.get("semantic_signals") or {}).values())
        components = {"lexical": _lexical(request.query, mem.get("content")), "causal": max([float(s.get("causal_relevance", 0) or 0) for s in signals] or [0]), "objective": max([float(s.get("objective_relevance", 0) or 0) for s in signals] or [0]), "verification": max([_STRENGTH.get(s.get("verification_strength"), 0) for s in signals] or [0]), "derived_index": max([float(i["index"].get("score") or 0) for i in entry.get("indexes", [])] or [0])}
        score = round(.35*components["lexical"]+.2*components["causal"]+.2*components["objective"]+.15*components["verification"]+.1*components["derived_index"], 12)
        rows.append({"memory_id": mid, "score": score, "score_components": components, "status": entry["status"], "memory": deepcopy(mem), "evidence_id": entry["evidence_id"]})
    rows.sort(key=lambda r: (-r["score"], r["memory_id"]))
    selected, chars = [], 0
    for row in rows:
        if len(selected) >= request.max_memory_items: break
        cost = len(canonical_semantic_json(row["memory"].get("content")))
        if chars + cost <= request.max_chars: selected.append(row); chars += cost
    return selected


def project_reasoning_frontier(reasoning, calculus, signals, scope_state, request):
    rows = []
    for aid, entry in reasoning.get("artifacts", {}).items():
        state, art = str(entry.get("state")), entry.get("artifact") or {}
        if state in _TERMINAL_REASONING and not request.include_stale: continue
        scope = str((art.get("scope") or {}).get("scope_id", ROOT_SCOPE_ID))
        try:
            if not scope_flow_allowed(dict(scope_state), scope, request.scope_id): continue
        except KeyError: continue
        sig = deepcopy(signals.get(f"ARTIFACT:{aid}", {})); score = round(.4*_lexical(request.query, art.get("statement", ""))+.25*float(sig.get("causal_relevance", 0) or 0)+.2*float(sig.get("objective_relevance", 0) or 0)+.15*_STRENGTH.get(sig.get("verification_strength"), 0), 12)
        rows.append({"key": f"ARTIFACT:{aid}", "node_type": "ARTIFACT", "node_id": aid, "score": score, "state": state, "scope_id": scope, "content": art.get("statement", ""), "signal": sig})
    for node_type, collection, terminal in (("DECISION", calculus.get("decisions", {}), {"PROPOSED","SUSPENDED","SUPERSEDED","INVALIDATED","REJECTED","HISTORICAL"}), ("OBLIGATION", calculus.get("obligations", {}), {"REJECTED","SUPERSEDED","IMPOSSIBLE","COMMITTED"})):
        for nid, row in collection.items():
            if row.get("status") in terminal: continue
            scope = str((row.get("scope") or {}).get("scope_id", ROOT_SCOPE_ID))
            try:
                if not scope_flow_allowed(dict(scope_state), scope, request.scope_id): continue
            except KeyError: continue
            content = {"subject": row.get("subject"), "value": row.get("value")} if node_type == "DECISION" else row.get("statement", "")
            sig = deepcopy(signals.get(f"{node_type}:{nid}", {})); score = round(.5*_lexical(request.query, content)+.25*float(sig.get("causal_relevance", 0) or 0)+.25*float(sig.get("objective_relevance", 0) or 0), 12)
            rows.append({"key": f"{node_type}:{nid}", "node_type": node_type, "node_id": nid, "score": score, "state": row.get("status"), "scope_id": scope, "content": deepcopy(content), "signal": sig})
    rows.sort(key=lambda r: (-r["score"], r["key"])); rows = rows[:request.max_frontier_items]
    return {"contract_id": REASONING_FRONTIER_CONTRACT_ID, "contract_version": REASONING_FRONTIER_CONTRACT_VERSION, "scope_id": request.scope_id, "items": rows, "count": len(rows), "frontier_fingerprint": semantic_fingerprint(rows)}


def project_context(memory_projection, reasoning, calculus, signals, scope_state, request):
    memories = select_memory_context(memory_projection, scope_state, request); chars = sum(len(canonical_semantic_json(x["memory"].get("content"))) for x in memories)
    frontier = project_reasoning_frontier(reasoning, calculus, signals, scope_state, request); selected = []
    for row in frontier["items"]:
        cost = len(canonical_semantic_json(row["content"]))
        if chars + cost <= request.max_chars: selected.append(row); chars += cost
    frontier["items"] = selected; frontier["count"] = len(selected); frontier["frontier_fingerprint"] = semantic_fingerprint(selected)
    payload = {"request": request.to_dict(), "memory_items": memories, "reasoning_frontier": frontier, "used_chars": chars, "budget_chars": request.max_chars}
    return {"contract_id": CONTEXT_PROJECTION_CONTRACT_ID, "contract_version": CONTEXT_PROJECTION_CONTRACT_VERSION, **payload, "projection_fingerprint": semantic_fingerprint(payload)}

__all__ = [name for name in globals() if not name.startswith("_")]
