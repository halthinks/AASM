from aasm import CollaborationPlanner, CollaborationPolicy, PlanGraph, PlanNode, ResourceRecord, TaskDemand


graph=PlanGraph()
for task_id in ["research","backend","frontend","tests","integration"]:
    graph.add_node(PlanNode(task_id,"task"))

tasks=[TaskDemand(x,["code"],metadata={"estimated_duration":1.0}) for x in graph.nodes]
resources=[ResourceRecord("coding-fleet","agent",["code"],capacity=20,cost_per_unit=.1)]

analysis=CollaborationPlanner().analyze(
    graph,
    resources,
    tasks,
    CollaborationPolicy(max_workers=100,coordination_overhead_per_extra_worker=.05),
)

print(analysis.to_dict())
