from __future__ import annotations
from dataclasses import dataclass,asdict
from .model import Proposal,Result

@dataclass
class AgentMessage:
    kind:str; sender:str; payload:dict; correlation_id:str|None=None

class GenericAgentAdapter:
    def proposal_message(self,p:Proposal): return AgentMessage("PROPOSAL",p.agent_id,asdict(p))
    def result_message(self,r:Result): return AgentMessage("RESULT",r.agent_id,asdict(r))

class PlannerBuilderAdapter(GenericAgentAdapter):
    """Compatibility adapter only; AASM core is not planner/builder-specific."""
    DECISIONS={"CONTINUE","REPAIR","INVESTIGATE","PAUSE","PLAN_INTERRUPT"}
    def controller_decision(self,decision:str,reason:str=""):
        if decision not in self.DECISIONS: raise ValueError(decision)
        return AgentMessage("CONTROLLER_DECISION","planner",{"decision":decision,"reason":reason})

class SwarmAdapter(GenericAgentAdapter):
    def task_broadcast(self,task_id,candidates): return AgentMessage("TASK_BROADCAST","controller",{"task_id":task_id,"candidates":list(candidates)})

class HumanToolAdapter(GenericAgentAdapter):
    def approval_request(self,action,reason): return AgentMessage("HUMAN_APPROVAL","controller",{"action":action,"reason":reason})
