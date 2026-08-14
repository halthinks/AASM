from aasm import AASMEngine, ProblemSpec
from aasm.optimization import default_optimization_providers, reference_optimization_models


engine = AASMEngine(ProblemSpec("heterogeneous optimization portfolio"))
engine.install_default_optimization_capability_contracts(
    authority_id="policy",
    authority_class="POLICY",
)
for provider in default_optimization_providers():
    engine.register_optimization_provider_runtime(
        provider,
        authority_id="policy",
        authority_class="POLICY",
    )

provider_for = {"SAT": "cadical", "CP_SAT": "ortools-cp-sat", "MILP": "highs"}

for family, model in reference_optimization_models().items():
    engine.admit_optimization_model(model)
    request = engine.request_optimization(
        model.model_id,
        requester_id="example",
        required_provider=provider_for[family],
    )
    lease = engine.claim_next_task(f"worker-{provider_for[family]}", lease_seconds=60)
    result = engine.execute_optimization_lease(lease["lease_id"])
    print(family, result["result"]["status"], result["result"].get("objective_value"))

assert engine.replay().canonical_hash() == engine.snapshot.canonical_hash()
