from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from .model import *
from .router import AlgorithmRouter
from .graph import PlanGraph
from .memory import DPMemory
from .checkpoint import CheckpointStore
from .flow import ResourceFlowAllocator
from .adversary import default_verifier
from .authority import SingleControllerAuthority

TRANSITIONS={
 MachineState.INGEST:{MachineState.FORMALIZE,MachineState.PAUSE,MachineState.FAIL},
 MachineState.FORMALIZE:{MachineState.CLASSIFY,MachineState.INVESTIGATE,MachineState.FAIL},
 MachineState.CLASSIFY:{MachineState.DECOMPOSE,MachineState.PLAN,MachineState.FAIL},
 MachineState.DECOMPOSE:{MachineState.PLAN,MachineState.INVESTIGATE},
 MachineState.PLAN:{MachineState.SELECT,MachineState.INVESTIGATE,MachineState.PAUSE},
 MachineState.SELECT:{MachineState.EXECUTE,MachineState.PAUSE},
 MachineState.EXECUTE:{MachineState.OBSERVE,MachineState.FAIL},
 MachineState.OBSERVE:{MachineState.VERIFY,MachineState.INVESTIGATE},
 MachineState.VERIFY:{MachineState.COMMIT,MachineState.REPAIR,MachineState.BACKTRACK,MachineState.INVESTIGATE,MachineState.COMPLETE,MachineState.FAIL},
 MachineState.REPAIR:{MachineState.EXECUTE,MachineState.VERIFY,MachineState.BACKTRACK},
 MachineState.BACKTRACK:{MachineState.SELECT,MachineState.PLAN,MachineState.INVESTIGATE},
 MachineState.INVESTIGATE:{MachineState.FORMALIZE,MachineState.PLAN,MachineState.SELECT,MachineState.VERIFY,MachineState.PAUSE},
 MachineState.COMMIT:{MachineState.SELECT,MachineState.PLAN,MachineState.COMPLETE},
 MachineState.PAUSE:{MachineState.PLAN,MachineState.SELECT,MachineState.FAIL},
 MachineState.COMPLETE:set(), MachineState.FAIL:set(),
}

class AASMEngine:
    def __init__(self, problem:ProblemSpec, authority=None):
        self.snapshot=MachineSnapshot(new_id("machine"),0,MachineState.INGEST.value,problem)
        self.events=[]; self.router=AlgorithmRouter(); self.graph=PlanGraph(); self.memory=DPMemory(); self.checkpoints=CheckpointStore()
        self.flow=ResourceFlowAllocator(); self.adversary=default_verifier(); self.authority=authority or SingleControllerAuthority(); self.agents={}
        self.emit(EventType.GOAL_RECEIVED.value,None,MachineState.INGEST.value,"goal initialized")
    def register_agent(self,agent): self.agents[agent.agent_id]=agent
    @property
    def state(self): return MachineState(self.snapshot.state)
    def allowed(self): return sorted(x.value for x in TRANSITIONS[self.state])
    def transition(self,to:MachineState|str,reason:str,evidence=None,data=None):
        to=MachineState(to)
        if to not in TRANSITIONS[self.state]: raise ValueError(f"Illegal transition {self.state.value}->{to.value}; allowed={self.allowed()}")
        old=self.state; self.snapshot.state=to.value; self.snapshot.version+=1
        self.emit("transition",old.value,to.value,reason,evidence or [],data or {}); return self.snapshot
    def emit(self,event_type,from_state,to_state,reason,evidence=None,data=None):
        e=Event(new_id("evt"),now(),event_type,from_state,to_state,reason,evidence or [],data or {}); self.events.append(e); return e
    def classify(self):
        d=self.router.route(self.snapshot.problem); self.snapshot.metadata["algorithm_route"]=asdict(d); return d
    def checkpoint(self,reason=""): return self.checkpoints.save(self.snapshot,reason)
    def backtrack(self,checkpoint_id,reason="backtrack"):
        if self.state!=MachineState.BACKTRACK: self.transition(MachineState.BACKTRACK,reason)
        restored=self.checkpoints.restore(checkpoint_id); restored.version=self.snapshot.version+1; self.snapshot=restored
        self.emit("restore",MachineState.BACKTRACK.value,self.snapshot.state,reason,data={"checkpoint_id":checkpoint_id}); return self.snapshot
    def propose_and_execute(self,agent_id,*,votes=None):
        agent=self.agents[agent_id]; proposal=agent.propose(deepcopy(self.snapshot)); self.emit(EventType.PROPOSAL.value,self.state.value,self.state.value,proposal.rationale,data=asdict(proposal))
        auth=self.authority.authorize(proposal,votes=votes); self.emit(EventType.AUTHORIZED.value,self.state.value,self.state.value,"proposal authorized",data={"authority":auth.authority})
        result=agent.execute(auth); self.emit(EventType.RESULT.value,self.state.value,self.state.value,"agent result",result.evidence,asdict(result)); return result
    def verify(self,context:dict): return self.adversary.verify(context)
    def export(self): return {"snapshot":asdict(self.snapshot),"events":[asdict(e) for e in self.events],"allowed_transitions":self.allowed()}
