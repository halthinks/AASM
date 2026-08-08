from __future__ import annotations
from dataclasses import dataclass
from typing import Callable,Any

@dataclass
class Challenge:
    assumption:str; counterexample:Any; severity:str="blocking"; evidence:list[str]|None=None

class AdversarialVerifier:
    def __init__(self): self.rules:list[Callable[[dict],Challenge|None]]=[]
    def add_rule(self,fn): self.rules.append(fn); return fn
    def verify(self, context:dict):
        challenges=[]
        for rule in self.rules:
            c=rule(context)
            if c is not None: challenges.append(c)
        return {"ok":not challenges,"challenges":[vars(c) for c in challenges]}


def default_verifier():
    v=AdversarialVerifier()
    @v.add_rule
    def unsupported_claim(ctx):
        for c in ctx.get("claims",[]):
            if c.get("requires_evidence") and not c.get("evidence"):
                return Challenge(c.get("text","claim"),"No supporting evidence attached",evidence=[])
    @v.add_rule
    def untested_irreversible(ctx):
        a=ctx.get("proposed_action",{})
        if not a.get("reversible",True) and not ctx.get("verification_passed",False):
            return Challenge("irreversible action is safe","Verification has not passed")
    return v
