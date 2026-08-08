from aasm import AASMEngine, ProblemSpec, ResourceRecord, TaskDemand

engine = AASMEngine(ProblemSpec("Allocate a specialist team"))
engine.register_resource(ResourceRecord("researcher", "agent", ["retrieval", "evidence"], capacity=1))
engine.register_resource(ResourceRecord("builder", "agent", ["python", "implementation"], capacity=2))
engine.register_resource(ResourceRecord("verifier", "agent", ["testing", "verify"], capacity=1))

result = engine.schedule([
    TaskDemand("research", ["retrieval"], priority=10),
    TaskDemand("implement", ["python"], priority=8),
    TaskDemand("verify-a", ["verify"], priority=6),
    TaskDemand("verify-b", ["verify"], priority=5),
])

print(result.to_dict())
