from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from .adaptive_routing import AdaptiveModelRouter, ModelOutcomeLedger, ModelOutcomeRecord
from .model_routing import ModelProfile, ModelRouteRequest
from .runtime_v09 import AASMEngine as V10Engine


class AASMEngine(V10Engine):
    """v0.11 runtime: v0.10 execution stack plus empirical model routing."""

    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.outcome_ledger=ModelOutcomeLedger()
        self.adaptive_router=AdaptiveModelRouter(self.outcome_ledger,self.model_router)

    @classmethod
    def _hydrate(cls,snapshot,events,store,authority=None,definition=None):
        self=super()._hydrate(snapshot,events,store,authority=authority,definition=definition)
        records=deepcopy(snapshot.resources.get("model_outcomes",[]))
        self.outcome_ledger=ModelOutcomeLedger(records)
        self.adaptive_router=AdaptiveModelRouter(self.outcome_ledger,self.model_router)
        return self

    def _refresh_runtime_views(self):
        super()._refresh_runtime_views()
        if hasattr(self,"outcome_ledger"):
            self.outcome_ledger=ModelOutcomeLedger(deepcopy(self.snapshot.resources.get("model_outcomes",[])))
            self.adaptive_router=AdaptiveModelRouter(self.outcome_ledger,self.model_router)

    def record_model_outcome(self,record:ModelOutcomeRecord,*,reason="evaluated model outcome recorded"):
        resources=deepcopy(self.snapshot.resources)
        outcomes=resources.setdefault("model_outcomes",[])
        outcomes.append(asdict(record))
        self.patch_snapshot({"resources":resources},reason)
        return deepcopy(outcomes[-1])

    def model_performance(self,task_class:str|None=None):
        return [p.to_dict() for p in self.outcome_ledger.performance(task_class)]

    def route_model(self,request:ModelRouteRequest,*,reason="adaptive model route computed"):
        profiles=[ModelProfile(**deepcopy(x)) for x in self.list_model_profiles()]
        result=self.adaptive_router.route(profiles,request)
        resources=deepcopy(self.snapshot.resources)
        resources["last_model_route"]={"request":asdict(request),"result":result.to_dict()}
        self.patch_snapshot({"resources":resources},reason)
        return result
