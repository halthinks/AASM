from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .governance import GovernanceBudgetPolicy, GovernanceContext, GovernanceEconomicsController
from .model import new_id
from .runtime_v11 import AASMEngine as V11Engine


class AASMEngine(V11Engine):
    """v0.12 runtime: adaptive execution plus durable governance economics."""

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self._rebuild_governance_controller()

    @classmethod
    def _hydrate(cls,snapshot,events,store,authority=None,definition=None):
        self=super()._hydrate(snapshot,events,store,authority=authority,definition=definition)
        self._rebuild_governance_controller()
        return self

    def _refresh_runtime_views(self):
        super()._refresh_runtime_views()
        if hasattr(self,"snapshot"):
            self._rebuild_governance_controller()

    def _rebuild_governance_controller(self):
        governance=deepcopy(self.snapshot.resources.get("governance",{})) if hasattr(self,"snapshot") else {}
        budget=GovernanceBudgetPolicy(**deepcopy(governance.get("budget",{}))) if governance.get("budget") else GovernanceBudgetPolicy()
        decisions=deepcopy(governance.get("decisions",[]))
        self.governance_controller=GovernanceEconomicsController(getattr(self,"review_policy",None),budget,decisions)

    def configure_governance_budget(self,policy:GovernanceBudgetPolicy,*,reason="governance budget configured"):
        resources=deepcopy(self.snapshot.resources); governance=resources.setdefault("governance",{}); governance["budget"]=asdict(policy)
        self.patch_snapshot({"resources":resources},reason); return deepcopy(governance["budget"])

    def governance_decide(self,context:GovernanceContext,*,reason="governance review gate evaluated"):
        decision=self.governance_controller.decide(context,self.economics_summary())
        raw=decision.to_dict(); raw["decision_id"]=new_id("gov"); raw["context"]=asdict(context); raw["review_completed"]=False; raw["review_evidence"]=[]
        resources=deepcopy(self.snapshot.resources); governance=resources.setdefault("governance",{}); governance.setdefault("budget",asdict(self.governance_controller.budget)); governance.setdefault("decisions",[]).append(raw)
        self.patch_snapshot({"resources":resources},reason); return deepcopy(raw)

    def complete_governance_review(self,decision_id:str,*,evidence:list[str]|None=None,reason="governance model review completed"):
        resources=deepcopy(self.snapshot.resources); decisions=resources.setdefault("governance",{}).setdefault("decisions",[])
        target=next((x for x in decisions if x.get("decision_id")==decision_id),None)
        if target is None: raise KeyError(decision_id)
        if target.get("action")!="MODEL_REVIEW_REQUIRED": raise ValueError("only MODEL_REVIEW_REQUIRED decisions can be completed as model reviews")
        target["review_completed"]=True; target["review_evidence"]=list(evidence or [])
        self.patch_snapshot({"resources":resources},reason); return deepcopy(target)

    def governance_report(self):
        return self.governance_controller.report(self.economics_summary())

    def review_gate(self,action_class:str,**signals):
        context=GovernanceContext(
            action_class,
            scope=str(signals.pop("scope","") or ""),
            action_signature=str(signals.pop("action_signature","") or ""),
            policy_revision=str(signals.pop("policy_revision","1") or "1"),
            assumption_revision=str(signals.pop("assumption_revision","") or ""),
            evidence_revision=str(signals.pop("evidence_revision","") or ""),
            assumption_changed=bool(signals.pop("assumption_changed",False)),
            tests_failed=bool(signals.pop("tests_failed",False)),
            diff_lines=int(signals.pop("diff_lines",0) or 0),
            metadata=deepcopy(signals),
        )
        return self.governance_decide(context)

    def dashboard(self):
        out=super().dashboard(); out["governance"]=self.governance_report(); out["governance_decisions"]=deepcopy(self.snapshot.resources.get("governance",{}).get("decisions",[])); return out
