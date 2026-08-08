from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from .runtime import AASMEngine as V07Engine
from .model_routing import ModelProfile, ModelRouteRequest, ModelStrengthRouter


class AASMEngine(V07Engine):
    """v0.8 runtime: v0.7 durable workers plus model-aware routing."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.model_router=ModelStrengthRouter()

    @classmethod
    def _hydrate(cls,snapshot,events,store,authority=None,definition=None):
        self=super()._hydrate(snapshot,events,store,authority=authority,definition=definition); self.model_router=ModelStrengthRouter(); return self

    def register_model_profile(self,profile:ModelProfile,*,reason="model profile registered"):
        resources=deepcopy(self.snapshot.resources); models=resources.setdefault("models",[])
        if any(x.get("model_id")==profile.model_id for x in models): raise ValueError(f"Model already exists: {profile.model_id}")
        models.append(asdict(profile)); self.patch_snapshot({"resources":resources},reason); return deepcopy(models[-1])

    def update_model_profile(self,model_id:str,patch:dict,*,reason="model profile updated"):
        resources=deepcopy(self.snapshot.resources); models=resources.setdefault("models",[]); current=next((x for x in models if x.get("model_id")==model_id),None)
        if current is None: raise KeyError(model_id)
        candidate=deepcopy(current); candidate.update(deepcopy(patch)); ModelProfile(**candidate); current.update(deepcopy(patch)); self.patch_snapshot({"resources":resources},reason); return deepcopy(current)

    def list_model_profiles(self): return deepcopy(self.snapshot.resources.get("models",[]))

    def route_model(self,request:ModelRouteRequest,*,reason="model route computed"):
        result=self.model_router.route([ModelProfile(**deepcopy(x)) for x in self.list_model_profiles()],request)
        resources=deepcopy(self.snapshot.resources); resources["last_model_route"]={"request":asdict(request),"result":result.to_dict()}; self.patch_snapshot({"resources":resources},reason); return result

    def last_model_route(self): return deepcopy(self.snapshot.resources.get("last_model_route"))
