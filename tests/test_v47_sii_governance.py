from dataclasses import replace
import pytest

from aasm.advanced_optimization import default_advanced_providers, reference_advanced_problems
from aasm.model import ProblemSpec
from aasm.runtime_v47 import AASMEngine
from aasm.sii import StructuredProposal
from aasm.sii_governance import (
    SIIPrincipalBinding,
    default_sii_scoring_policy,
    governed_sii_contract,
)


def configured_engine():
    engine = AASMEngine(ProblemSpec("v0.47 governed SII"))
    engine.install_default_sii_scoring_policy(authority_id="policy", authority_class="POLICY")
    engine.bind_sii_principal(SIIPrincipalBinding("reasoner", "PROPOSER", can_propose=True), authority_id="policy", authority_class="POLICY")
    engine.bind_sii_principal(SIIPrincipalBinding("verifier", "VERIFIER", can_measure=True), authority_id="policy", authority_class="POLICY")
    registered = engine.register_sii_proposer(principal_id="reasoner", name="reasoner", kind="llm", provider="fixture", model_id="m")
    return engine, registered["identity"]["proposer_id"]


def install_advanced(engine):
    engine.install_default_advanced_optimization_capabilities(authority_id="policy", authority_class="POLICY")
    for provider in default_advanced_providers():
        engine.register_advanced_optimization_provider_runtime(provider, authority_id="policy", authority_class="POLICY")


def test_governed_contract_closes_preview_graduation_gaps_without_authority_reward():
    contract = governed_sii_contract()
    assert contract["contract_id"] == "aasm.sii.v1"
    assert contract["contract_version"] == "0.3.0"
    assert contract["stability"] == "GOVERNED_ENFORCED"
    assert contract["principal_binding"] == "DURABLE_POLICY_OR_CONTROLLER_ADMISSION"
    assert contract["measurement_identity_binding"] == "RESOLVED_FROM_DURABLE_PRINCIPAL_BINDING"
    assert contract["resource_enforcement"] == "EXISTING_CONTEXT_CAPABILITY_SCHEDULER_TASKLEASE_NATIVE_SOLVER_PATHS"
    assert contract["mandatory_verification"] == "NEVER_REDUCED_BY_SII"
    assert contract["authority_reward"] == "NEVER"
    assert contract["self_verification"] == "REJECTED"
    assert contract["direct_state_mutation"] == "REJECTED"


def test_principal_and_scoring_policy_admission_require_existing_policy_authority():
    engine = AASMEngine(ProblemSpec("v0.47 governance authority"))
    binding = SIIPrincipalBinding("reasoner", "PROPOSER", can_propose=True)
    with pytest.raises(PermissionError, match="POLICY or CONTROLLER"):
        engine.bind_sii_principal(binding, authority_id="agent", authority_class="PROPOSER")
    policy = default_sii_scoring_policy()
    with pytest.raises(PermissionError, match="POLICY or CONTROLLER"):
        engine.admit_sii_scoring_policy(policy, authority_id="agent", authority_class="PROPOSER")
    admitted = engine.admit_sii_scoring_policy(policy, authority_id="policy", authority_class="POLICY")
    activated = engine.activate_sii_scoring_policy(policy.policy_id, authority_id="policy", authority_class="POLICY")
    assert admitted["policy"]["version"] == "1.0.0"
    assert activated["policy_id"] == policy.policy_id


def test_stable_principal_cannot_be_rebound_to_gain_measurement_authority():
    engine = AASMEngine(ProblemSpec("v0.47 principal rebinding"))
    engine.bind_sii_principal(SIIPrincipalBinding("p", "PROPOSER", can_propose=True), authority_id="policy", authority_class="POLICY")
    with pytest.raises(ValueError, match="already bound differently"):
        engine.bind_sii_principal(SIIPrincipalBinding("p", "VERIFIER", can_measure=True), authority_id="policy", authority_class="POLICY")


def test_measurement_authority_is_resolved_from_durable_principal_binding_not_caller_claim():
    engine, proposer_id = configured_engine()
    proposal = StructuredProposal(proposer_id, "candidate", "root", {"choice": 1}, .7)
    submitted = engine.submit_sii_proposal(proposal)
    with pytest.raises(KeyError, match="unbound governed SII principal"):
        engine.measure_sii_outcome(proposal.proposal_id, measured_by_principal_id="forged-meter", disposition="INCONCLUSIVE", verification_verdict="INCONCLUSIVE")
    feedback = engine.measure_sii_outcome(proposal.proposal_id, measured_by_principal_id="verifier", disposition="INCONCLUSIVE", verification_verdict="INCONCLUSIVE")
    assert feedback["proposal_id"] == proposal.proposal_id
    assert feedback["resource_lease"]["authority_class"] == "PROPOSER"
    assert feedback["resource_lease"]["direct_truth_promotion"] is False
    assert submitted["resource_lease"]["enforcement"].endswith("V047")


def test_same_governed_principal_cannot_measure_its_own_proposal_even_with_verifier_role():
    engine = AASMEngine(ProblemSpec("v0.47 self measure"))
    engine.install_default_sii_scoring_policy(authority_id="policy", authority_class="POLICY")
    engine.bind_sii_principal(SIIPrincipalBinding("hybrid", "VERIFIER", can_propose=True, can_measure=True), authority_id="policy", authority_class="POLICY")
    registered = engine.register_sii_proposer(principal_id="hybrid", name="hybrid", kind="human")
    proposer_id = registered["identity"]["proposer_id"]
    proposal = StructuredProposal(proposer_id, "candidate", "root", "x", .5)
    engine.submit_sii_proposal(proposal)
    with pytest.raises(ValueError, match="cannot measure its own proposal"):
        engine.measure_sii_outcome(proposal.proposal_id, measured_by_principal_id="hybrid", disposition="INCONCLUSIVE", verification_verdict="INCONCLUSIVE")


def test_tier_one_advanced_request_compiles_lease_into_native_sat_budgets_scheduler_priority_and_task_metadata():
    engine, proposer_id = configured_engine(); install_advanced(engine)
    base = reference_advanced_problems()["INCREMENTAL_SAT"]
    oversized = replace(base, conflict_budget=999_999, decision_budget=999_999)
    requested = engine.request_sii_advanced_optimization(proposer_id, oversized, timeout_ms=999_999)
    effective = requested["effective_problem"]
    assert effective["conflict_budget"] == 10_000
    assert effective["decision_budget"] == 20_000
    assert requested["request"]["timeout_ms"] == 15_000
    assert requested["task"]["priority"] == 40
    queued = next(row for row in engine.snapshot.resources["tasks"] if row["task_id"] == requested["task"]["task_id"])
    assert queued["metadata"]["sii_proposer_id"] == proposer_id
    assert queued["metadata"]["sii_resource_lease_id"] == requested["resource_lease"]["lease_id"]
    assert queued["metadata"]["sii_enforcement_evidence_id"] == requested["enforcement_evidence_id"]
    assert queued["metadata"]["authority_reward"] == "NEVER"


def test_tier_one_parallel_candidate_budget_is_enforced_before_queue_growth():
    engine, proposer_id = configured_engine(); install_advanced(engine)
    problems = reference_advanced_problems()
    engine.request_sii_advanced_optimization(proposer_id, problems["FAST_SAT"])
    engine.request_sii_advanced_optimization(proposer_id, problems["CP_SAT_SCHEDULING"])
    before = len(engine.snapshot.resources["tasks"])
    with pytest.raises(PermissionError, match="max_parallel_candidates"):
        engine.request_sii_advanced_optimization(proposer_id, problems["MILP_ADVANCED"])
    assert len(engine.snapshot.resources["tasks"]) == before


def test_scoring_policy_is_versioned_durable_and_resource_lease_is_replay_safe():
    engine, proposer_id = configured_engine()
    lease = engine.sii_resource_lease(proposer_id, persist=True)
    report = engine.sii_governance_report()
    assert report["active_policy_id"] == lease["lease"]["policy_id"]
    assert lease["lease"]["policy_version"] == "1.0.0"
    assert report["leases"][lease["lease"]["lease_id"]]["lease"]["fingerprint"] == lease["lease"]["fingerprint"]
    assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
