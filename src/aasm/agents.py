from __future__ import annotations
from abc import ABC, abstractmethod
from .model import CapabilitySet, TaskEnvelope, MachineSnapshot, Proposal, AuthorizedAction, Result

class AASMAgent(ABC):
    @property
    @abstractmethod
    def agent_id(self) -> str: ...
    @abstractmethod
    def capabilities(self) -> CapabilitySet: ...
    def accept_task(self, task: TaskEnvelope) -> None: self._task = task
    @abstractmethod
    def propose(self, context: MachineSnapshot) -> Proposal: ...
    @abstractmethod
    def execute(self, action: AuthorizedAction) -> Result: ...

class FunctionAgent(AASMAgent):
    def __init__(self, agent_id: str, capabilities: set[str], proposer, executor):
        self._id=agent_id; self._caps=CapabilitySet(frozenset(capabilities)); self._proposer=proposer; self._executor=executor
    @property
    def agent_id(self): return self._id
    def capabilities(self): return self._caps
    def propose(self, context): return self._proposer(self, context)
    def execute(self, action): return self._executor(self, action)
