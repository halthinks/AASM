import pytest

from aasm.cross_run_knowledge import CrossRunKnowledgeEnvelope, CrossRunPrincipalMap
from aasm.model import ProblemSpec
from aasm.runtime_v48 import AASMEngine
from aasm.sii_governance import SIIPrincipalBinding


def _admit(engine, envelope):
    proposed = engine.propose_cross_run_admission(envelope, proposer_id="receiver", target_scope_id="root")
    decision_id = proposed["decision"]["decision_id"]
    engine.authorize_cross_run_admission(decision_id, authority_id="policy", authority_class="POLICY")
    engine.commit_cross_run_admission(decision_id, worker_id="import-worker")


def test_cross_run_sii_reputation_requires_exact_source_principal_mapping():
    engine = AASMEngine(ProblemSpec("cross-run reputation identity"))
    engine.bind_sii_principal(
        SIIPrincipalBinding("local-agent", "PROPOSER", can_propose=True),
        authority_id="policy",
        authority_class="POLICY",
    )
    engine.map_cross_run_principal(
        CrossRunPrincipalMap("foreign-run", "foreign-agent-a", "local-agent"),
        authority_id="policy",
        authority_class="POLICY",
    )
    envelope = CrossRunKnowledgeEnvelope(
        source_run_id="foreign-run",
        source_machine_id="foreign-machine",
        source_scope_id="root",
        knowledge_kind="SII_REPUTATION",
        content={"terminal_samples": 100, "verified_utility": 1.0},
        privacy_level="PUBLIC",
        applicability_scope_ids=("root",),
        metadata={"source_principal_id": "foreign-agent-b"},
    )
    _admit(engine, envelope)
    with pytest.raises(ValueError, match="does not match admitted stable principal mapping"):
        engine.admit_cross_run_sii_reputation(
            envelope.envelope_id,
            local_principal_id="local-agent",
            authority_id="policy",
            authority_class="POLICY",
        )
