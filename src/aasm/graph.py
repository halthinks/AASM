from __future__ import annotations
from dataclasses import dataclass, field
from collections import defaultdict, deque
import heapq, math

@dataclass
class PlanNode:
    node_id: str
    kind: str
    payload: dict = field(default_factory=dict)

@dataclass
class PlanEdge:
    src: str; dst: str; relation: str="requires"; cost: float=1.0

class PlanGraph:
    def __init__(self): self.nodes={}; self.edges=[]
    def add_node(self,node:PlanNode): self.nodes[node.node_id]=node
    def add_edge(self,edge:PlanEdge):
        if edge.src not in self.nodes or edge.dst not in self.nodes: raise KeyError("Both edge endpoints must exist")
        self.edges.append(edge)
    def adjacency(self):
        a=defaultdict(list)
        for e in self.edges: a[e.src].append(e)
        return a
    def topological_order(self):
        indeg={n:0 for n in self.nodes}; a=self.adjacency()
        for e in self.edges: indeg[e.dst]+=1
        q=deque(sorted(n for n,d in indeg.items() if d==0)); out=[]
        while q:
            n=q.popleft(); out.append(n)
            for e in a[n]:
                indeg[e.dst]-=1
                if indeg[e.dst]==0:q.append(e.dst)
        if len(out)!=len(self.nodes): raise ValueError("Plan graph contains a cycle")
        return out
    def shortest_path(self,start,goal):
        a=self.adjacency(); dist={n:math.inf for n in self.nodes}; prev={}; dist[start]=0; pq=[(0,start)]
        while pq:
            d,u=heapq.heappop(pq)
            if d!=dist[u]: continue
            if u==goal: break
            for e in a[u]:
                nd=d+e.cost
                if nd<dist[e.dst]: dist[e.dst]=nd; prev[e.dst]=u; heapq.heappush(pq,(nd,e.dst))
        if dist[goal]==math.inf:return math.inf,[]
        path=[goal]
        while path[-1]!=start:path.append(prev[path[-1]])
        path.reverse(); return dist[goal],path
    def relax_edge(self,src,dst,new_cost):
        for e in self.edges:
            if e.src==src and e.dst==dst:
                old=e.cost; e.cost=min(old,new_cost); return old,e.cost
        raise KeyError((src,dst))
    def to_dict(self): return {"nodes":[vars(n) for n in self.nodes.values()],"edges":[vars(e) for e in self.edges]}
