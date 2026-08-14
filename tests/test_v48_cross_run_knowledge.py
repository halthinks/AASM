from __future__ import annotations

import pytest

from aasm.cross_run_knowledge import (
    CrossRunKnowledgeEnvelope,
    CrossRunKnowledgeSignal,
    CrossRunPrincipalMap,
)
from aasm.model import ProblemSpec
from aasm.reuse_model import ReuseRequest
from aasm.runtime_v48 import AASMEngine
from aasm.sii_governance import SIIPrincipalBinding


def commit_procedural_memory(engine: AASMEngine, content):
    proposed = engine.propose_memory_operation(
        "STORE",
        scope_id="root",
        proposer_id="agent",
        kind="PROCEDURAL",
        substrate="STRUCTURED",
        content=content,
        privacy_level="PUBLIC",
    )
    decision_id = proposed["decision"]["decision_id"]
    engine.authorize_memory_operation(decision_id, authority_id="policy", authority_class="POLICY")
    committed = engine.commit_memory_operation(decision_id, worker_id="memory-worker")
    return committed["memory"]["memory"]["memory_id"]


def admit(receiver: AASMEngine, envelope: CrossRunKnowledgeEnvelope):
    proposed = receiver.propose_cross_run_admission(envelope, proposer_id="receiver", target_scope_id="root")
    decision_id = proposed["decision"]["decision_id"]
    receiver.authorize_cross_run_admission(decision_id, authority_id="policy", authority_class="POLICY")
    return receiver.commit_cross_run_admission(decision_id, worker_id="import-worker")


def test_cross_run_validator_rejects_same_run_and_incompatible_context():
    engine = AASMEngine(ProblemSpec("cross-run validation"))
    envelope = CrossRunKnowledgeEnvelope(
        source_run_id=engine.snapshot.machine_id,
        source_machine_id=engine.snapshot.machine_id,
        source_scope_id="root",
        knowledge_kind="PROCEDURAL",
        content={"step": "x"},
        environment_fingerprint="env-a",
        dependency_fingerprints=("dep-a",),
        verification_strength="CHECKED_CERTIFICATE",
        privacy_level="USER",
        privacy_principal_id="alice",
        applicability_scope_ids=("root",),
    )
    report = engine.inspect_cross_run_envelope(
        envelope,
        target_scope_id="root",
        privacy_principal_id="bob",
        environment_fingerprint="env-b",
        dependency_fingerprints=(),
        required_strength="TRUSTED_KERNEL",
    )
    checks = report["certificate"]["checks"]
    assert checks["foreign_source_run"] is False
    assert checks["privacy_compatible"] is False
    assert checks["environment_compatible"] is False
    assert checks["dependencies_available"] is False
    assert checks["verification_strength_sufficient"] is False
    assert report["certificate"]["valid"] is False
    with pytest.raises(ValueError, match="not admissible"):
        engine.propose_cross_run_admission(
            envelope,
            proposer_id="agent",
            target_scope_id="root",
            privacy_principal_id="bob",
            environment_fingerprint="env-b",
            required_strength="TRUSTED_KERNEL",
        )


def test_export_admit_materialize_and_source_revocation_tombstones_local_memory():
    source = AASMEngine(ProblemSpec("source run"))
    source_memory_id = commit_procedural_memory(source, {"procedure": ["inspect", "verify", "commit"]})
    exported = source.export_cross_run_knowledge([source_memory_id])
    envelope = CrossRunKnowledgeEnvelope.from_dict(exported["bundle"]["envelopes"][0])

    receiver = AASMEngine(ProblemSpec("receiver run"))
    admitted = admit(receiver, envelope)
    assert admitted["entry"]["status"] == "ACTIVE"
    assert admitted["entry"]["source_authority_inherited"] is False

    materialized = receiver.materialize_cross_run_knowledge(envelope.envelope_id, proposer_id="receiver")
    memory_decision_id = materialized["materialization"]["decision"]["decision_id"]
    receiver.authorize_memory_operation(memory_decision_id, authority_id="policy", authority_class="POLICY")
    committed = receiver.commit_memory_operation(memory_decision_id, worker_id="memory-worker")
    local_memory_id = committed["memory"]["memory"]["memory_id"]
    assert receiver.hierarchical_memory_report()["memories"][local_memory_id]["status"] == "ACTIVE"

    signal = source.make_cross_run_signal(
        envelope.envelope_id,
        action="REVOKE",
        reason="source procedure withdrawn",
        authority_id="source-policy",
        authority_class="POLICY",
    )["signal"]
    applied = receiver.apply_cross_run_signal(signal, authority_id="policy", authority_class="POLICY")
    assert applied["entry"]["status"] == "REVOKED"
    assert applied["materialized_memory_revocations"][0]["memory_id"] == local_memory_id
    assert receiver.hierarchical_memory_report()["memories"][local_memory_id]["status"] == "REVOKED"
    assert receiver.replay().canonical_hash() == receiver.snapshot.canonical_hash()


def test_cross_run_reuse_uses_existing_certificate_and_revocation_blocks_hot_candidate():
    receiver = AASMEngine(ProblemSpec("cross-run reuse"))
    payload = {"answer": 42, "method": "certified"}
    envelope = CrossRunKnowledgeEnvelope(
        source_run_id="run-foreign",
        source_machine_id="machine-foreign",
        source_scope_id="root",
        knowledge_kind="REUSE_RESULT",
        content=payload,
        verification_strength="CHECKED_CERTIFICATE",
        privacy_level="PUBLIC",
        applicability_scope_ids=("root",),
    )
    admit(receiver, envelope)
    request = ReuseRequest(
        kind="SUBPROBLEM_RESULT",
        semantic_payload=payload,
        scope_id="root",
        privacy_level="PUBLIC",
        required_strength="SOLVER_VERDICT",
    )
    receiver.register_cross_run_reuse_candidate(envelope.envelope_id, request, authority_id="policy", authority_class="POLICY")
    lookup = receiver.lookup_reuse(request)
    assert lookup["hit"] is True
    assert lookup["certificate"]["metadata"]["cross_run"]["envelope_id"] == envelope.envelope_id
    assert lookup["certificate"]["metadata"]["cross_run"]["admission_validator_version"] == "0.1.0"
    assert lookup["certificate"]["metadata"]["cross_run"]["authority_inherited"] is False

    signal = CrossRunKnowledgeSignal(
        source_run_id=envelope.source_run_id,
        envelope_id=envelope.envelope_id,
        envelope_fingerprint=envelope.fingerprint,
        action="REVOKE",
        reason="source result revoked",
    )
    receiver.apply_cross_run_signal(signal, authority_id="policy", authority_class="POLICY")
    blocked = receiver.lookup_reuse(request)
    assert blocked["hit"] is False
    assert blocked["reason"] == "cross_run_source_not_active"


def test_foreign_semantic_content_cannot_become_local_semantic_memory_without_local_authorized_reasoning():
    receiver = AASMEngine(ProblemSpec("semantic receiving boundary"))
    envelope = CrossRunKnowledgeEnvelope(
        source_run_id="foreign-semantic-run",
        source_machine_id="foreign-machine",
        source_scope_id="root",
        knowledge_kind="SEMANTIC",
        content={"claim": "foreign claim"},
        privacy_level="PUBLIC",
        applicability_scope_ids=("root",),
    )
    admit(receiver, envelope)
    with pytest.raises(ValueError, match="local AUTHORIZED reasoning"):
        receiver.materialize_cross_run_knowledge(envelope.envelope_id, proposer_id="receiver")


def test_cross_run_principal_mapping_and_reputation_are_accounting_only():
    receiver = AASMEngine(ProblemSpec("cross-run reputation"))
    receiver.bind_sii_principal(
        SIIPrincipalBinding("local-agent", "PROPOSER", can_propose=True),
        authority_id="policy",
        authority_class="POLICY",
    )
    mapping = CrossRunPrincipalMap("foreign-run", "foreign-agent", "local-agent")
    mapped = receiver.map_cross_run_principal(mapping, authority_id="policy", authority_class="POLICY")
    assert mapped["mapping"]["authority_transfer"] == "NEVER"
    assert mapped["mapping"]["resource_entitlement_transfer"] == "NEVER"

    envelope = CrossRunKnowledgeEnvelope(
        source_run_id="foreign-run",
        source_machine_id="foreign-machine",
        source_scope_id="root",
        knowledge_kind="SII_REPUTATION",
        content={"terminal_samples": 100, "verified_utility": 1.0},
        privacy_level="PUBLIC",
        applicability_scope_ids=("root",),
        metadata={"source_principal_id": "foreign-agent"},
    )
    admit(receiver, envelope)
    reputation = receiver.admit_cross_run_sii_reputation(
        envelope.envelope_id,
        local_principal_id="local-agent",
        authority_id="policy",
        authority_class="POLICY",
    )
    assert reputation["reputation"]["truth_authority"] == "NONE"
    assert reputation["reputation"]["resource_entitlement"] == "NONE"
    rows = receiver.cross_run_knowledge_report()["sii_reputation"]
    assert rows[-1]["metadata"]["used_by_sii_resource_lease"] is False
    assert receiver.sii_governance_report()["principals"]["local-agent"]["binding"]["authority_class"] == "PROPOSER"
