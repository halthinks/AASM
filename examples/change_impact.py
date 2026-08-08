from aasm import AASMEngine, ChangeKind, ChangeSignal, PlanEdge, PlanNode, ProblemSpec

engine=AASMEngine(ProblemSpec("Add FreeCAD compatibility without discarding unrelated work"))
for node_id in ["importer","cad_adapter","assembly_manual","docs"]:
    engine.plan_add_node(PlanNode(node_id,"task"))
engine.plan_add_edge(PlanEdge("cad_adapter","assembly_manual"))

impact=engine.analyze_change(ChangeSignal(
    ChangeKind.USER_STEERING,
    "also support FreeCAD",
    seed_nodes=["cad_adapter"],
    metadata={"source":"user"},
))

print("affected:",impact["affected_nodes"])
print("unaffected:",impact["unaffected_nodes"])
print("paused:",engine.paused_tasks())
