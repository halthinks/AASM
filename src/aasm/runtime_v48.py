from .runtime_v47 import AASMEngine as V47Engine
from ._runtime_v48_knowledge import CrossRunKnowledgeRuntimeMixin
from .cross_run_knowledge import CrossRunKnowledgeEnvelope


class AASMEngine(CrossRunKnowledgeRuntimeMixin, V47Engine):
    """AASM v0.48 runtime: v0.47 plus governed cross-run knowledge admission."""

    def lookup_reuse(self, request, **kwargs):
        result = super().lookup_reuse(request, **kwargs)
        if not result.get("hit"):
            return result
        metadata = (result.get("candidate") or {}).get("metadata") or {}
        if not metadata.get("cross_run"):
            return result
        envelope_id = str(metadata.get("cross_run_envelope_id") or "")
        row = self.cross_run_knowledge_report().get("envelopes", {}).get(envelope_id)
        if row is None or row.get("status") != "ACTIVE":
            blocked = dict(result)
            blocked["hit"] = False
            blocked["reason"] = "cross_run_source_not_active"
            blocked["certificate"] = None
            blocked["blocked_cross_run_envelope_id"] = envelope_id
            blocked["blocked_cross_run_status"] = None if row is None else row.get("status")
            return blocked
        if row["envelope"]["fingerprint"] != metadata.get("cross_run_envelope_fingerprint"):
            blocked = dict(result)
            blocked["hit"] = False
            blocked["reason"] = "cross_run_envelope_fingerprint_changed"
            blocked["certificate"] = None
            return blocked
        return result

    def apply_cross_run_signal(self, signal, *, authority_id: str, authority_class: str):
        result = super().apply_cross_run_signal(signal, authority_id=authority_id, authority_class=authority_class)
        signal_payload = result.get("signal") or {}
        if "signal" in signal_payload:
            signal_payload = signal_payload["signal"]
        envelope_id = str(signal_payload.get("envelope_id") or "")
        revoked = []
        for memory_id, row in sorted(self.hierarchical_memory_report().get("memories", {}).items()):
            metadata = row["memory"].get("metadata") or {}
            if metadata.get("cross_run_envelope_id") != envelope_id or row.get("status") != "ACTIVE":
                continue
            proposed = self.propose_memory_forget(
                memory_id,
                proposer_id=authority_id,
                reason=f"cross-run source signal invalidated materialized memory: {signal_payload.get('action', 'SIGNAL')}",
                metadata={"cross_run_envelope_id": envelope_id, "cross_run_signal_evidence_id": result.get("evidence_id")},
            )
            decision_id = proposed["decision"]["decision_id"]
            self.authorize_memory_operation(decision_id, authority_id=authority_id, authority_class=authority_class)
            committed = self.commit_memory_operation(decision_id, worker_id="cross-run-signal")
            revoked.append({"memory_id": memory_id, "decision_id": decision_id, "evidence_id": committed.get("evidence_id")})
        result["materialized_memory_revocations"] = revoked
        return result

    def admit_cross_run_sii_reputation(self, envelope_id: str, *, local_principal_id: str, authority_id: str, authority_class: str):
        report = self.cross_run_knowledge_report()
        row = report.get("envelopes", {}).get(envelope_id)
        if row is None:
            raise KeyError(envelope_id)
        envelope = CrossRunKnowledgeEnvelope.from_dict(row["envelope"])
        source_principal_id = str((envelope.metadata or {}).get("source_principal_id") or "")
        if not source_principal_id:
            raise ValueError("cross-run SII reputation requires source_principal_id metadata")
        exact_mapping = any(
            item["mapping"]["source_run_id"] == envelope.source_run_id
            and item["mapping"]["source_principal_id"] == source_principal_id
            and item["mapping"]["local_principal_id"] == local_principal_id
            for item in report.get("principal_maps", {}).values()
        )
        if not exact_mapping:
            raise ValueError("cross-run SII reputation source principal does not match admitted stable principal mapping")
        return super().admit_cross_run_sii_reputation(
            envelope_id,
            local_principal_id=local_principal_id,
            authority_id=authority_id,
            authority_class=authority_class,
        )


__all__ = ["AASMEngine"]
