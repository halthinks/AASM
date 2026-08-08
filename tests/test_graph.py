from aasm.graph import PlanGraph,PlanNode,PlanEdge

def test_topological_and_shortest_path_and_relax():
    g=PlanGraph()
    for n in "ABCD": g.add_node(PlanNode(n,"task"))
    g.add_edge(PlanEdge("A","B",cost=5)); g.add_edge(PlanEdge("A","C",cost=1)); g.add_edge(PlanEdge("C","B",cost=1)); g.add_edge(PlanEdge("B","D",cost=1))
    assert g.topological_order()[0]=="A"
    cost,path=g.shortest_path("A","D"); assert cost==3 and path==["A","C","B","D"]
    old,new=g.relax_edge("A","B",0.5); assert old==5 and new==0.5
