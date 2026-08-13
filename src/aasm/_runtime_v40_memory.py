from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Sequence

from .evidence import EvidenceRecord
from .hierarchical_memory import (
    CONTEXT_PROJECTION_CONTRACT_ID, HIERARCHICAL_MEMORY_CONTRACT_ID, MEMORY_INDEX_CONTRACT_ID,
    ContextProjectionRequest, MemoryIndexEntry, MemoryObject, MemoryTombstone,
    hierarchical_memory_contract, memory_document, project_context, project_memory_evidence,
    project_reasoning_frontier,
)
from .memory_operations import MemoryOperationDecision, MemoryOperationObligation, memory_obligation_id
from .semantic_result import canonical_semantic_json, semantic_fingerprint


class HierarchicalMemoryRuntimeMixin:
    """v0.40 governed hierarchical memory and bounded context projection."""

    def hierarchical_memory_contract_report(self) -> dict[str, Any]:
        return hierarchical_memory_contract()

    def _memory_reasoning_states(self) -> dict[str, str]:
        return {aid: str(entry.get("state")) for aid, entry in self.reasoning_report().get("artifacts", {}).items()}

    def _memory_semantic_signals(self) -> dict[str, dict[str, Any]]:
        report = self.semantic_memory_projection_signals()
        return deepcopy(report.get("signals", report if isinstance(report, dict) else {}))

    def hierarchical_memory_report(self, *, as_of: float | None = None) -> dict[str, Any]:
        return project_memory_evidence(
            self.snapshot.evidence.get("records", []),
            reasoning_states=self._memory_reasoning_states(),
            semantic_signals=self._memory_semantic_signals(),
            as_of=as_of,
        )

    def _known_memory(self, memory_id: str, *, as_of: float | None = None) -> dict[str, Any]:
        report = self.hierarchical_memory_report(as_of=as_of)
        if not report["valid"]:
            raise RuntimeError(f"invalid hierarchical memory projection: {report['issues']}")
        try:
            return deepcopy(report["memories"][memory_id])
        except KeyError:
            raise KeyError(memory_id) from None

    def propose_memory_operation(
        self,
        operation: str,
        *,
        scope_id: str,
        proposer_id: str,
        kind: str = "WORKING",
        substrate: str = "STRUCTURED",
        content: Any = None,
        source_evidence_ids: Sequence[str] = (),
        semantic_artifact_ids: Sequence[str] = (),
        causal_parent_memory_ids: Sequence[str] = (),
        target_memory_ids: Sequence[str] = (),
        retention_policy: str = "permanent",
        privacy_level: str = "AGENT",
        compatibility_fingerprint: str = "",
        metadata: Mapping[str, Any] | None = None,
        reason: str = "hierarchical memory operation proposed",
    ) -> dict[str, Any]:
        if operation not in {"STORE", "UPDATE", "COMPRESS", "CONSOLIDATE"}:
            raise ValueError("use propose_memory_forget for FORGET")
        if not proposer_id or not scope_id:
            raise ValueError("memory operation requires proposer_id and scope_id")
        calculus = self.calculus_report()
        if scope_id not in calculus["scope_state"]["records"]:
            raise KeyError(f"unknown memory scope: {scope_id}")
        source_evidence = self._require_evidence_ids(source_evidence_ids)
        reasoning = self.reasoning_report()
        artifact_ids = sorted(set(map(str, semantic_artifact_ids)))
        missing_artifacts = sorted(set(artifact_ids) - set(reasoning.get("artifacts", {})))
        if missing_artifacts:
            raise KeyError(f"unknown semantic memory artifacts: {missing_artifacts}")
        if kind == "SEMANTIC":
            unauthorized = [aid for aid in artifact_ids if reasoning["artifacts"][aid]["state"] != "AUTHORIZED"]
            if unauthorized:
                raise ValueError(f"semantic memory requires AUTHORIZED reasoning artifacts: {unauthorized}")
        target_ids = sorted(set(map(str, target_memory_ids)))
        parents = sorted(set(map(str, causal_parent_memory_ids)))
        memory_report = self.hierarchical_memory_report()
        for mid in sorted(set([*target_ids, *parents])):
            if mid not in memory_report["memories"]:
                raise KeyError(f"unknown memory reference: {mid}")
        if operation == "UPDATE" and len(target_ids) != 1:
            raise ValueError("UPDATE requires exactly one target memory")
        if operation in {"COMPRESS", "CONSOLIDATE"} and not target_ids:
            raise ValueError(f"{operation} requires target memories")
        seed = {
            "operation": operation, "scope_id": scope_id, "proposer_id": proposer_id,
            "kind": kind, "substrate": substrate, "content": deepcopy(content),
            "source_evidence_ids": source_evidence, "semantic_artifact_ids": artifact_ids,
            "causal_parent_memory_ids": parents, "target_memory_ids": target_ids,
            "retention_policy": retention_policy, "privacy_level": privacy_level,
            "compatibility_fingerprint": compatibility_fingerprint, "metadata": deepcopy(dict(metadata or {})),
        }
        decision_id = "memory-decision-" + semantic_fingerprint(seed)[:20]
        supersedes = target_ids if operation in {"UPDATE", "COMPRESS", "CONSOLIDATE"} else []
        memory = MemoryObject(
            scope_id=scope_id, kind=kind, substrate=substrate, content=deepcopy(content),
            created_by_decision=decision_id, source_evidence_ids=tuple(source_evidence),
            semantic_artifact_ids=tuple(artifact_ids), causal_parent_memory_ids=tuple(parents),
            supersedes_memory_ids=tuple(supersedes), retention_policy=retention_policy,
            privacy_level=privacy_level, compatibility_fingerprint=compatibility_fingerprint,
            metadata=deepcopy(dict(metadata or {})),
            version=1 + max([int(memory_report["memories"][mid]["memory"].get("version", 1)) for mid in target_ids] or [0]),
        )
        decision = MemoryOperationDecision(
            decision_id=decision_id,
            subject=f"memory.operation:{memory.memory_id}",
            value={"operation": operation, "memory": memory.to_dict()},
            kind="EXPLICIT", status="PROPOSED", evidence_ids=list(source_evidence),
            scope={"scope_id": scope_id}, operation=operation, memory_id=memory.memory_id,
            target_memory_ids=target_ids, proposed_memory=memory.to_dict(), proposer_id=proposer_id,
        )
        if decision_id in calculus["decisions"]:
            existing = calculus["decisions"][decision_id]
            return {"contract": hierarchical_memory_contract(), "decision": existing, "memory": deepcopy(existing.get("proposed_memory")), "already_proposed": True}
        registered = self.register_decision(decision, reason=reason)
        return {"contract": hierarchical_memory_contract(), "decision": registered, "memory": memory.to_dict(), "already_proposed": False}

    def propose_memory_forget(self, memory_id: str, *, proposer_id: str, reason: str, mode: str = "VISIBILITY_REVOKED", metadata: Mapping[str, Any] | None = None) -> dict[str, Any]:
        current = self._known_memory(memory_id)
        if current["status"] == "REVOKED":
            return {"contract": hierarchical_memory_contract(), "memory_id": memory_id, "already_revoked": True}
        if not proposer_id or not reason.strip():
            raise ValueError("memory forget requires proposer_id and reason")
        scope_id = str(current["memory"]["scope_id"])
        seed = {"operation": "FORGET", "memory_id": memory_id, "proposer_id": proposer_id, "reason": reason, "mode": mode, "metadata": deepcopy(dict(metadata or {}))}
        decision_id = "memory-decision-" + semantic_fingerprint(seed)[:20]
        decision = MemoryOperationDecision(
            decision_id=decision_id, subject=f"memory.forget:{memory_id}", value=deepcopy(seed),
            kind="EXPLICIT", status="PROPOSED", scope={"scope_id": scope_id}, operation="FORGET",
            memory_id=memory_id, target_memory_ids=[memory_id], proposed_memory=None, proposer_id=proposer_id,
        )
        if decision_id not in self.calculus_report()["decisions"]:
            self.register_decision(decision, reason="memory forget proposed")
        return {"contract": hierarchical_memory_contract(), "decision": deepcopy(self.calculus_report()["decisions"][decision_id]), "memory_id": memory_id, "reason": reason, "mode": mode, "already_revoked": False}

    def authorize_memory_operation(self, decision_id: str, *, authority_id: str, authority_class: str, reason: str = "hierarchical memory operation authorized") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("memory operation authorization requires POLICY or CONTROLLER authority")
        state = self.calculus_report()
        decision = state["decisions"].get(decision_id)
        if decision is None:
            raise KeyError(decision_id)
        if "operation" not in decision or "memory_id" not in decision:
            raise ValueError("decision is not a v0.40 memory operation")
        obligation_id = memory_obligation_id(decision_id)
        if decision.get("status") == "PROPOSED":
            self.activate_decision(decision_id, reason=reason)
        elif decision.get("status") != "ACTIVE":
            raise ValueError(f"memory decision cannot authorize from {decision.get('status')}")
        state = self.calculus_report()
        if obligation_id not in state["obligations"]:
            proposed = decision.get("proposed_memory") or {}
            evidence_type = "hierarchical_memory_tombstone" if decision["operation"] == "FORGET" else "hierarchical_memory_object"
            obligation = MemoryOperationObligation(
                obligation_id=obligation_id, statement=f"memory.{decision['operation'].lower()}:{decision['memory_id']}",
                status="AVAILABLE", decision_dependencies=[decision_id], required_evidence_types=[evidence_type],
                scope=deepcopy(decision.get("scope") or {}), operation=decision["operation"],
                memory_id=decision["memory_id"], memory_decision_id=decision_id,
                privacy_level=str(proposed.get("privacy_level", "AGENT")),
                retention_policy=str(proposed.get("retention_policy", "permanent")),
            )
            self.register_obligation(obligation, reason="memory operation obligation created")
        auth = self.add_evidence(EvidenceRecord(
            kind="hierarchical_memory_authorization",
            statement=canonical_semantic_json({"decision_id": decision_id, "obligation_id": obligation_id, "authority_id": authority_id, "authority_class": authority_class}),
            source=HIERARCHICAL_MEMORY_CONTRACT_ID,
            metadata={"memory_record_type": "AUTHORIZATION", "memory_contract_id": HIERARCHICAL_MEMORY_CONTRACT_ID, "decision_id": decision_id, "obligation_id": obligation_id, "authority_id": authority_id, "authority_class": authority_class},
        ), reason=reason)
        return {"contract": hierarchical_memory_contract(), "decision": deepcopy(self.calculus_report()["decisions"][decision_id]), "obligation": deepcopy(self.calculus_report()["obligations"][obligation_id]), "authorization_evidence_id": auth.evidence_id}

    def commit_memory_operation(self, decision_id: str, *, worker_id: str, result_metadata: Mapping[str, Any] | None = None, reason: str = "hierarchical memory operation committed") -> dict[str, Any]:
        if not worker_id:
            raise ValueError("memory operation commit requires worker_id")
        calculus = self.calculus_report()
        decision = calculus["decisions"].get(decision_id)
        if decision is None:
            raise KeyError(decision_id)
        if decision.get("status") != "ACTIVE":
            raise ValueError("memory operation requires ACTIVE authorized decision")
        obligation_id = memory_obligation_id(decision_id)
        obligation = calculus["obligations"].get(obligation_id)
        if obligation is None:
            raise KeyError(obligation_id)
        operation = str(decision["operation"])
        memory_id = str(decision["memory_id"])
        projection = self.hierarchical_memory_report()
        if operation != "FORGET" and memory_id in projection["memories"]:
            prior = projection["memories"][memory_id]
            proposed = MemoryObject.from_dict(decision["proposed_memory"])
            if prior["memory"]["fingerprint"] != proposed.fingerprint:
                raise ValueError("canonical memory ID collision")
            return {"contract": hierarchical_memory_contract(), "memory": deepcopy(prior), "already_committed": True}
        if obligation["status"] == "AVAILABLE":
            self.enable_obligation(obligation_id, reason="memory worker enabled")
        if self.calculus_report()["obligations"][obligation_id]["status"] == "ENABLED":
            self.set_obligation_status(obligation_id, "IN_PROGRESS", reason="memory worker started")
        if operation == "FORGET":
            current = self._known_memory(memory_id)
            if current["status"] == "REVOKED":
                return {"contract": hierarchical_memory_contract(), "memory": current, "already_committed": True}
            value = decision.get("value") or {}
            tombstone = MemoryTombstone(memory_id, decision_id, str(value.get("reason") or "memory revoked"), str(value.get("mode") or "VISIBILITY_REVOKED"), deepcopy(value.get("metadata") or {}))
            stored = self.add_evidence(EvidenceRecord(
                kind="hierarchical_memory_tombstone", statement=memory_document(tombstone), source=HIERARCHICAL_MEMORY_CONTRACT_ID,
                metadata={"memory_record_type": "TOMBSTONE", "memory_contract_id": HIERARCHICAL_MEMORY_CONTRACT_ID, "memory_id": memory_id, "tombstone_id": tombstone.tombstone_id, "tombstone_fingerprint": tombstone.fingerprint, "decision_id": decision_id, "obligation_id": obligation_id, "worker_id": worker_id, "result_metadata": deepcopy(dict(result_metadata or {}))},
            ), reason=reason)
            committed_value = tombstone.to_dict()
        else:
            memory = MemoryObject.from_dict(decision["proposed_memory"])
            if memory.created_by_decision != decision_id:
                raise ValueError("memory object decision provenance mismatch")
            self._require_evidence_ids(memory.source_evidence_ids)
            stored = self.add_evidence(EvidenceRecord(
                kind="hierarchical_memory_object", statement=memory_document(memory), source=HIERARCHICAL_MEMORY_CONTRACT_ID,
                derived_from=list(memory.source_evidence_ids),
                metadata={"memory_record_type": "OBJECT", "memory_contract_id": HIERARCHICAL_MEMORY_CONTRACT_ID, "memory_id": memory.memory_id, "memory_fingerprint": memory.fingerprint, "memory_kind": memory.kind, "scope_id": memory.scope_id, "privacy_level": memory.privacy_level, "decision_id": decision_id, "obligation_id": obligation_id, "worker_id": worker_id, "result_metadata": deepcopy(dict(result_metadata or {}))},
            ), reason=reason)
            committed_value = memory.to_dict()
        self.set_obligation_status(obligation_id, "VERIFYING", evidence_ids=[stored.evidence_id], reason="memory operation evidence under verification")
        self.set_obligation_status(obligation_id, "VERIFIED", evidence_ids=[stored.evidence_id], reason="memory operation evidence verified")
        self.set_obligation_status(obligation_id, "COMMITTED", evidence_ids=[stored.evidence_id], reason="memory operation committed")
        projection = self.hierarchical_memory_report()
        return {"contract": hierarchical_memory_contract(), "operation": operation, "committed": committed_value, "evidence_id": stored.evidence_id, "memory": deepcopy(projection["memories"].get(memory_id)), "already_committed": False}

    def admit_memory_index(self, entry: MemoryIndexEntry | Mapping[str, Any], *, authority_id: str, authority_class: str, reason: str = "derived memory index admitted") -> dict[str, Any]:
        if authority_class not in {"POLICY", "CONTROLLER"}:
            raise PermissionError("derived memory index admission requires POLICY or CONTROLLER authority")
        entry = entry if isinstance(entry, MemoryIndexEntry) else MemoryIndexEntry.from_dict(entry)
        current = self._known_memory(entry.memory_id)
        if current["memory"]["fingerprint"] != entry.memory_fingerprint:
            raise ValueError("derived index cannot change or misidentify canonical memory")
        for row in current.get("indexes", []):
            if row["index"]["index_entry_id"] == entry.index_entry_id:
                if row["index"]["fingerprint"] != entry.fingerprint:
                    raise ValueError("memory index ID collision")
                return {"contract": hierarchical_memory_contract(), "index": deepcopy(row), "already_admitted": True}
        stored = self.add_evidence(EvidenceRecord(
            kind="hierarchical_memory_index", statement=memory_document(entry), source=MEMORY_INDEX_CONTRACT_ID,
            derived_from=[current["evidence_id"]],
            metadata={"memory_record_type": "INDEX", "memory_index_contract_id": MEMORY_INDEX_CONTRACT_ID, "memory_id": entry.memory_id, "memory_fingerprint": entry.memory_fingerprint, "index_entry_id": entry.index_entry_id, "index_fingerprint": entry.fingerprint, "index_kind": entry.index_kind, "indexer_id": entry.indexer_id, "indexer_version": entry.indexer_version, "authority_id": authority_id, "authority_class": authority_class},
        ), reason=reason)
        return {"contract": hierarchical_memory_contract(), "index": entry.to_dict(), "evidence_id": stored.evidence_id, "already_admitted": False, "canonical_memory_fingerprint": current["memory"]["fingerprint"]}

    def reasoning_frontier(self, request: ContextProjectionRequest | Mapping[str, Any]) -> dict[str, Any]:
        request = request if isinstance(request, ContextProjectionRequest) else ContextProjectionRequest(**deepcopy(dict(request)))
        calculus = self.calculus_report()
        return project_reasoning_frontier(self.reasoning_report(), calculus, self._memory_semantic_signals(), calculus["scope_state"], request)

    def context_projection(self, request: ContextProjectionRequest | Mapping[str, Any]) -> dict[str, Any]:
        request = request if isinstance(request, ContextProjectionRequest) else ContextProjectionRequest(**deepcopy(dict(request)))
        calculus = self.calculus_report()
        signals = self._memory_semantic_signals()
        memory = self.hierarchical_memory_report(as_of=request.as_of)
        if not memory["valid"]:
            raise RuntimeError(f"invalid hierarchical memory projection: {memory['issues']}")
        return project_context(memory, self.reasoning_report(), calculus, signals, calculus["scope_state"], request)

    def record_context_projection(self, request: ContextProjectionRequest | Mapping[str, Any], *, actor_id: str, reason: str = "context projection recorded") -> dict[str, Any]:
        if not actor_id:
            raise ValueError("context projection actor_id is required")
        projection = self.context_projection(request)
        stored = self.add_evidence(EvidenceRecord(
            kind="context_projection", statement=canonical_semantic_json(projection), source=CONTEXT_PROJECTION_CONTRACT_ID,
            metadata={"memory_record_type": "CONTEXT_PROJECTION", "context_contract_id": CONTEXT_PROJECTION_CONTRACT_ID, "projection_fingerprint": projection["projection_fingerprint"], "actor_id": actor_id, "scope_id": projection["request"]["scope_id"]},
        ), reason=reason)
        return {**projection, "evidence_id": stored.evidence_id}


__all__ = ["HierarchicalMemoryRuntimeMixin"]
