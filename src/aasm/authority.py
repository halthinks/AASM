from __future__ import annotations
from dataclasses import dataclass, field
from .model import Proposal, AuthorizedAction, new_id

class AuthorityPolicy:
    name="base"
    def authorize(self, proposal: Proposal, *, votes: dict[str,bool]|None=None) -> AuthorizedAction:
        raise NotImplementedError

@dataclass
class SingleControllerAuthority(AuthorityPolicy):
    controller_id: str="controller"
    name: str="single_controller"
    def authorize(self, proposal, **_): return AuthorizedAction(proposal,new_id("auth"),self.controller_id)

@dataclass
class AutonomousAuthority(AuthorityPolicy):
    allowed_actions: set[str]=field(default_factory=lambda:{"inspect","read","compute","local_repair"})
    name: str="autonomous"
    def authorize(self, proposal, **_):
        if proposal.action not in self.allowed_actions or not proposal.reversible:
            raise PermissionError(f"Action {proposal.action!r} is not autonomously authorized")
        return AuthorizedAction(proposal,new_id("auth"),"autonomous_policy")

@dataclass
class QuorumAuthority(AuthorityPolicy):
    required_votes: int=2
    name: str="quorum"
    def authorize(self, proposal, *, votes=None, **_):
        votes=votes or {}
        if sum(bool(v) for v in votes.values()) < self.required_votes: raise PermissionError("Quorum not reached")
        return AuthorizedAction(proposal,new_id("auth"),f"quorum:{self.required_votes}")

@dataclass
class HierarchicalAuthority(AuthorityPolicy):
    action_authorities: dict[str,str]=field(default_factory=dict)
    default_authority: str="controller"
    name: str="hierarchical"
    def authorize(self, proposal, **_):
        who=self.action_authorities.get(proposal.action,self.default_authority)
        return AuthorizedAction(proposal,new_id("auth"),who)
