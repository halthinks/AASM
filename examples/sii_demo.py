from aasm import AASMEngine, ArtifactProposal, ProblemSpec, StructuredProposal, create_sii
from aasm.reuse_metrics import ReuseMetrics


engine = AASMEngine(ProblemSpec("Demonstrate governed symbiotic reasoning"))
sii = create_sii(engine)
identity = sii.register(
    principal_id="provider:model:stable-principal",
    name="Example reasoner",
    kind="llm",
    provider="example",
    model_id="reasoner-x",
    version="1",
)
proposer_id = identity["identity"]["proposer_id"]

proposal = StructuredProposal(
    proposer_id=proposer_id,
    decision_name="choose_strategy",
    scope_id="root",
    chosen={"strategy": "reuse-first"},
    confidence=.82,
    task_class="software_reasoning",
    artifacts=(
        ArtifactProposal(
            kind="Hypothesis",
            statement="A reuse-first strategy will avoid redundant solver work.",
            verifier_ids=("independent-verifier",),
            confidence=.82,
        ),
    ),
    rationale_summary="Concise public rationale only; no raw chain-of-thought.",
)

submitted = sii.submit(proposal)
artifact_id = submitted["compiled_artifact_ids"][0]

obs = engine.add_observation(
    "Independent test reproduced the predicted reuse behavior.",
    source="example-test",
)
engine.request_verification(
    artifact_id,
    verifier_ids=("independent-verifier",),
    requester_id=proposer_id,
)
engine.record_verification(
    artifact_id,
    verifier_id="independent-verifier",
    verdict="PASS",
    evidence_ids=(obs.evidence_id,),
)
engine.authorize_artifact(
    artifact_id,
    authority_id="policy",
    authority_class="POLICY",
)

reuse = engine.record_reuse_metrics(
    ReuseMetrics(
        exact_hits=1,
        model_calls_avoided=1,
        solver_runs_avoided=1,
        input_units_avoided=4000,
        output_units_avoided=1000,
    ),
    actor_id="reuse-meter",
)

feedback = sii.measure_proposal_outcome(
    proposal.proposal_id,
    measured_by="independent-meter",
    authority_class="VERIFIER",
    reuse_metrics_evidence_ids=(reuse["evidence_id"],),
    actual_input_tokens=1200,
    actual_output_tokens=300,
    downstream_reuse_hits=1,
    reusable_artifact_ids=(artifact_id,),
)

print(feedback.to_dict())
print(sii.context_for(proposer_id, scope_id="root", query="What remains unresolved?"))
print("NOTE: v0.43 ResourceLease is a policy projection; enforcement graduates in v0.44.")
