from __future__ import annotations

from .cross_run_knowledge import CrossRunKnowledgeEnvelope, CrossRunKnowledgeSignal
from .model import ProblemSpec
from .reuse_model import ReuseRequest
from .runtime_v48 import AASMEngine


def _admit(engine, envelope):
    proposed = engine.propose_cross_run_admission(envelope, proposer_id="conformance", target_scope_id="root")
    decision_id = proposed["decision"]["decision_id"]
    engine.authorize_cross_run_admission(decision_id, authority_id="policy", authority_class="POLICY")
    return engine.commit_cross_run_admission(decision_id, worker_id="conformance-worker")


def run_cross_run_knowledge_conformance() -> dict:
    receiver = AASMEngine(ProblemSpec("cross-run conformance"))
    payload = {"result": "stable", "value": 7}
    envelope = CrossRunKnowledgeEnvelope(
        source_run_id="foreign-conformance-run",
        source_machine_id="foreign-conformance-machine",
        source_scope_id="root",
        knowledge_kind="REUSE_RESULT",
        content=payload,
        verification_strength="CHECKED_CERTIFICATE",
        privacy_level="PUBLIC",
        applicability_scope_ids=("root",),
    )
    admitted = _admit(receiver, envelope)
    request = ReuseRequest(
        kind="SUBPROBLEM_RESULT",
        semantic_payload=payload,
        required_strength="CHECKED_CERTIFICATE",
    )
    receiver.register_cross_run_reuse_candidate(envelope.envelope_id, request, authority_id="policy", authority_class="POLICY")
    before = receiver.lookup_reuse(request)
    signal = CrossRunKnowledgeSignal(
        source_run_id=envelope.source_run_id,
        envelope_id=envelope.envelope_id,
        envelope_fingerprint=envelope.fingerprint,
        action="REVOKE",
        reason="conformance revocation",
    )
    receiver.apply_cross_run_signal(signal, authority_id="policy", authority_class="POLICY")
    after = receiver.lookup_reuse(request)
    checks = {
        "foreign_authority_not_inherited": admitted["entry"]["source_authority_inherited"] is False,
        "receiving_admission_active": admitted["entry"]["status"] == "ACTIVE",
        "existing_reuse_certificate_used": bool(before.get("hit") and before.get("certificate")),
        "reuse_certificate_carries_cross_run_validator": bool((before.get("certificate") or {}).get("metadata", {}).get("cross_run", {}).get("admission_validator_version")),
        "revocation_blocks_existing_reuse": after.get("hit") is False and after.get("reason") == "cross_run_source_not_active",
        "exact_replay": receiver.replay().canonical_hash() == receiver.snapshot.canonical_hash(),
    }
    return {
        "contract_id": "aasm.cross-run.conformance.v1",
        "contract_version": "0.1.0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "projection_fingerprint": receiver.cross_run_knowledge_report()["projection_fingerprint"],
    }


__all__ = ["run_cross_run_knowledge_conformance"]
