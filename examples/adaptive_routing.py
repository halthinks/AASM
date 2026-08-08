from aasm import AASMEngine, ModelOutcomeRecord, ModelProfile, ModelRouteRequest, ProblemSpec

engine=AASMEngine(ProblemSpec("adaptive routing demo"))
for profile in [
    ModelProfile("luna","openai",["code"],strength=.60,cost_per_1k_output=.2),
    ModelProfile("terra","openai",["code"],strength=.80,cost_per_1k_output=1.0),
    ModelProfile("sol","openai",["code"],strength=.95,cost_per_1k_output=4.0),
]:
    engine.register_model_profile(profile)

for i in range(8):
    engine.record_model_outcome(ModelOutcomeRecord(f"luna-{i}","routine_backend","luna",True,estimated_cost=.2))
    engine.record_model_outcome(ModelOutcomeRecord(f"terra-{i}","routine_backend","terra",i<7,repair_required=i==7,estimated_cost=1.0))

request=ModelRouteRequest(
    "next-backend-task",
    ["code"],
    min_strength=.5,
    metadata={
        "task_class":"routine_backend",
        "min_empirical_samples":5,
        "empirical_optimize":"cost_per_quality",
    },
)

print(engine.route_model(request).to_dict())
print(engine.model_performance("routine_backend"))
