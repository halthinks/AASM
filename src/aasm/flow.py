from __future__ import annotations
from collections import defaultdict,deque

class ResourceFlowAllocator:
    """Small Edmonds-Karp max-flow/min-cut engine for agent/tool capacity graphs."""
    def solve(self, capacities:dict[str,dict[str,float]], source:str, sink:str):
        residual=defaultdict(dict); original={}
        for u,vs in capacities.items():
            for v,c in vs.items():
                c=float(c)
                if c < 0: raise ValueError("capacities must be non-negative")
                residual[u][v]=c; residual[v].setdefault(u,0.0); original[(u,v)]=c
        total=0.0
        while True:
            parent={source:None}; q=deque([source])
            while q and sink not in parent:
                u=q.popleft()
                for v,c in residual[u].items():
                    if c>1e-12 and v not in parent: parent[v]=u; q.append(v)
            if sink not in parent: break
            f=float("inf"); v=sink
            while parent[v] is not None: u=parent[v]; f=min(f,residual[u][v]); v=u
            v=sink
            while parent[v] is not None:
                u=parent[v]; residual[u][v]-=f; residual[v][u]=residual[v].get(u,0)+f; v=u
            total+=f
        reachable={source}; q=deque([source])
        while q:
            u=q.popleft()
            for v,c in residual[u].items():
                if c>1e-12 and v not in reachable: reachable.add(v); q.append(v)
        cut=[]
        for u,vs in capacities.items():
            for v,c in vs.items():
                if u in reachable and v not in reachable and c>0: cut.append((u,v,float(c)))
        flows={}
        for (u,v),cap in original.items():
            used=cap-residual[u].get(v,0.0)
            if used>1e-12: flows[f"{u}->{v}"]=used
        return {"max_flow":total,"min_cut_edges":cut,"reachable":sorted(reachable),"flows":flows}
