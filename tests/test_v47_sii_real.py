import os
import pytest

from aasm.advanced_optimization import default_advanced_providers, reference_advanced_problems
from aasm.model import ProblemSpec
from aasm.runtime_v47 import AASMEngine
from aasm.sii_governance import SIIPrincipalBinding


pytestmark = pytest.mark.skipif(
    os.environ.get("AASM_REQUIRE_SII_BACKENDS") != "1",
    reason="real governed SII/native solver integration runs only in the dedicated optimization workflow",
)


def test_real_incremental_cadical_executes_through_governed_sii_resource_tasklease_and_evidence_path():
    engine = AASMEngine(ProblemSpec("v0.47 real governed SII solver lifecycle"))
    engine.install_default_sii_scoring_policy(authority_id="policy", authority_class="POLICY")
    engine.bind_sii_principal(
        SIIPrincipalBinding("real-reasoner", "PROPOSER", can_propose=True),
        authority_id="policy",
        authority_class="POLICY",
    )
    registered = engine.register_sii_proposer(
        principal_id="real-reasoner",
        name="real governed reasoner",
        kind="solver",
        provider="aasm-test",
        model_id="incremental-sat",
    )
    proposer_id = registered["identity"]["proposer_id"]

    engine.install_default_advanced_optimization_capabilities(authority_id="policy", authority_class="POLICY")
    provider = next(row for row in default_advanced_providers() if row.provider_id == "cadical-incremental")
    engine.register_advanced_optimization_provider_runtime(provider, authority_id="policy", authority_class="POLICY")

    problem = reference_advanced_problems()["INCREMENTAL_SAT"]
    requested = engine.request_sii_advanced_optimization(proposer_id, problem, timeout_ms=999_999)

    # Tier-one governance is compiled into the canonical request/problem before
    # the native worker is leased.
    assert requested["effective_problem"]["conflict_budget"] == 10_000
    assert requested["effective_problem"]["decision_budget"] == 20_000
    assert requested["request"]["timeout_ms"] == 15_000
    assert requested["task"]["priority"] == 40

    lease = engine.claim_next_task("worker-cadical-incremental", lease_seconds=120)
    assert lease["metadata"]["sii_proposer_id"] == proposer_id
    assert lease["metadata"]["sii_resource_lease_id"] == requested["resource_lease"]["lease_id"]
    assert lease["metadata"]["sii_policy_id"] == requested["resource_lease"]["policy_id"]
    assert lease["metadata"]["sii_enforcement_evidence_id"] == requested["enforcement_evidence_id"]
    assert lease["metadata"]["authority_reward"] == "NEVER"

    committed = engine.execute_advanced_optimization_lease(lease["lease_id"])
    assert committed["result"]["status"] == "UNSAT", committed
    assert committed["result"]["unsat_core"]
    assert committed["satisfied"] is True

    evidence = next(row for row in engine.snapshot.evidence["records"] if row["evidence_id"] == committed["result_evidence_id"])
    assert evidence["metadata"]["result_authority"] == "EVIDENCE_ONLY"

    governance = engine.sii_governance_report()
    assert any(row["target_id"] == requested["request"]["request_id"] for row in governance["enforcement"])
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
