from aasm import AASMEngine, GovernanceBudgetPolicy, GovernanceContext, ModelUsageRecord, ProblemSpec
from aasm.economics import CallPurpose

engine=AASMEngine(ProblemSpec("governance economics demo"))
engine.configure_governance_budget(GovernanceBudgetPolicy(max_permission_review_calls=5))

# One observed reviewer call establishes a workload-local counterfactual baseline.
engine.record_model_usage(ModelUsageRecord(
    "gpt-5.6-luna",
    CallPurpose.PERMISSION_REVIEW.value,
    input_tokens=1000,
    output_tokens=100,
))

context=GovernanceContext(
    "architecture_choice",
    scope="backend",
    action_signature="architecture-v1",
    assumption_revision="A1",
    evidence_revision="E1",
)

first=engine.governance_decide(context)
print("first:",first["action"])
engine.complete_governance_review(first["decision_id"],evidence=["review accepted"])

second=engine.governance_decide(context)
print("second:",second["action"])
print(engine.governance_report())
