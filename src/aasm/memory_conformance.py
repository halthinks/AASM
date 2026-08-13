from __future__ import annotations

from .hierarchical_memory import ContextProjectionRequest, MemoryIndexEntry, MemoryObject, MemoryTombstone, hierarchical_memory_contract, memory_document, project_context, project_memory_evidence
from .scopes import default_scope_state
from .semantic_result import semantic_fingerprint


def _row(evidence_id, kind, statement, metadata, created_at):
    return {"evidence_id": evidence_id, "kind": kind, "statement": statement, "metadata": metadata, "created_at": float(created_at), "status": "active"}


def run_hierarchical_memory_conformance() -> dict:
    checks = {}
    memory = MemoryObject("root", "WORKING", "STRUCTURED", {"answer": 42}, "D1", retention_policy="ttl:10", privacy_level="PUBLIC")
    object_row = _row("E1", "hierarchical_memory_object", memory_document(memory), {"memory_record_type": "OBJECT", "memory_fingerprint": memory.fingerprint}, 100)
    projection = project_memory_evidence([object_row], as_of=105)
    checks["canonical_memory_active_before_ttl"] = projection["memories"][memory.memory_id]["status"] == "ACTIVE"
    checks["ttl_uses_explicit_durable_time"] = project_memory_evidence([object_row], as_of=111)["memories"][memory.memory_id]["status"] == "EXPIRED"
    index = MemoryIndexEntry(memory.memory_id, memory.fingerprint, "VECTOR", "embedder", "1", score=.8, payload=[.1, .2])
    index_row = _row("E2", "hierarchical_memory_index", memory_document(index), {"memory_record_type": "INDEX", "index_fingerprint": index.fingerprint}, 101)
    indexed = project_memory_evidence([object_row, index_row], as_of=105)
    checks["derived_index_does_not_change_memory_identity"] = indexed["memories"][memory.memory_id]["memory"]["fingerprint"] == memory.fingerprint
    tombstone = MemoryTombstone(memory.memory_id, "D2", "forget requested")
    tombstone_row = _row("E3", "hierarchical_memory_tombstone", memory_document(tombstone), {"memory_record_type": "TOMBSTONE", "tombstone_fingerprint": tombstone.fingerprint}, 102)
    revoked = project_memory_evidence([object_row, tombstone_row], as_of=105)
    checks["forgetting_is_tombstone_not_deletion"] = memory.memory_id in revoked["memories"] and revoked["memories"][memory.memory_id]["status"] == "REVOKED"
    context = project_context(indexed, {"artifacts": {}}, {"decisions": {}, "obligations": {}}, {}, default_scope_state(), ContextProjectionRequest(scope_id="root", query="answer", allowed_privacy_levels=("PUBLIC",), max_memory_items=1, max_frontier_items=0, max_chars=100))
    checks["context_projection_is_bounded"] = context["used_chars"] <= context["budget_chars"] and len(context["memory_items"]) <= 1
    contract = hierarchical_memory_contract()
    checks["stale_default_is_excluded"] = contract["stale_default"] == "EXCLUDED"
    checks["mutation_path_is_governed"] = contract["mutation_path"] == "DECISION_TO_OBLIGATION_TO_EVIDENCE"
    checks["embeddings_are_derived_only"] = contract["embeddings"] == "DERIVED_INDEX_ONLY"
    checks["legacy_dp_memory_preserved"] = contract["legacy_dp_memory"] == "PRESERVED_COMPATIBILITY_CACHE"
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "contract": contract, "report_fingerprint": semantic_fingerprint(checks)}


__all__ = ["run_hierarchical_memory_conformance"]
