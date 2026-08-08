from __future__ import annotations
from copy import deepcopy
from dataclasses import dataclass
from .model import MachineSnapshot,new_id

@dataclass
class Checkpoint:
    checkpoint_id:str; snapshot:MachineSnapshot; reason:str

class CheckpointStore:
    def __init__(self): self._items=[]
    def save(self,snapshot,reason=""):
        cp=Checkpoint(new_id("cp"),deepcopy(snapshot),reason); self._items.append(cp); return cp
    def restore(self,checkpoint_id):
        for cp in reversed(self._items):
            if cp.checkpoint_id==checkpoint_id:return deepcopy(cp.snapshot)
        raise KeyError(checkpoint_id)
    def latest(self): return self._items[-1] if self._items else None
    def branch_and_prune(self,snapshot,branch_id,valid:bool):
        if valid:
            if branch_id not in snapshot.visited:snapshot.visited.append(branch_id)
        else:
            if branch_id not in snapshot.pruned:snapshot.pruned.append(branch_id)
            snapshot.frontier=[x for x in snapshot.frontier if x!=branch_id]
        return snapshot
