from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from .core.reducer import reduce_event, replay_events
from .model import EventType
from .runtime import AASMEngine as V07Engine
from .model_routing import ModelProfile, ModelRouteRequest, ModelStrengthRouter


class AASMEngine(V07Engine):
    """v0.8 runtime: v0.7 durable workers plus model-aware routing."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs); self.model_router=ModelStrengthRouter()

    @classmethod
    def _hydrate(cls,snapshot,events,store,authority=None,definition=None):
        self=super()._hydrate(snapshot,events,store,authority=authority,definition=definition); self.model_router=ModelStrengthRouter(); return self

    @classmethod
    def resume(cls,machine_id,store,authority=None,*,recover_effects=False):
        """Rehydrate a run without treating ordinary inspection as a crash.

        `recover_effects=True` is reserved for an actual process-recovery path:
        only then are durable RUNNING effects converted to UNKNOWN for explicit
        reconciliation. Stateless HTTP/CLI inspection can safely resume with the
        default `False` without disturbing work that another host is still doing.
        """
        events=store.load_events(machine_id)
        if not events: raise KeyError(machine_id)
        self=cls._hydrate(replay_events(events),events,store,authority=authority)
        if recover_effects:
            marker=getattr(store,"mark_running_effects_unknown",None)
            if marker:
                for record in marker(machine_id):
                    self.emit(
                        EventType.EFFECT_UNKNOWN.value,
                        self.state_value,
                        self.state_value,
                        "recovered unresolved effect",
                        data={"effect_id":record.spec.effect_id,"idempotency_key":record.spec.idempotency_key},
                    )
        return self

    @classmethod
    def recover_unfinished(cls,store,authority=None):
        return [
            cls.resume(mid,store,authority=authority,recover_effects=True)
            for mid in store.list_unfinished()
        ]

    def _commit(self,event):
        """Adopt state only after the durable append succeeds.

        A concurrent durable store can reject a stale/invalid event. Reducing
        into a candidate first prevents an uncommitted local "ghost" state.
        Stores such as SQLite/PostgreSQL may replace the candidate with their
        database-canonical reduction during append.
        """
        machine_id=self.snapshot.machine_id
        candidate=reduce_event(self.snapshot,event)
        try:
            stored=self.store.append(machine_id,event,candidate)
        except Exception:
            # The live snapshot was never replaced by the candidate. Refresh
            # when possible so the caller immediately sees authoritative state.
            try:
                self.snapshot=self.store.load_snapshot(machine_id)
                self.events=self.store.load_events(machine_id)
                self._refresh_runtime_views()
            except Exception:
                pass
            raise
        self.snapshot=candidate
        self._sync_after_append()
        return stored

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

    def claim_next_task(self,worker_id:str,*,lease_seconds:float=60.0):
        """Claim the highest-priority scheduled task this worker can execute."""
        finished={x.get("task_id") for x in self.snapshot.resources.get("leases",[]) if x.get("status")=="COMPLETED"}
        active={x.get("task_id") for x in self.snapshot.resources.get("leases",[]) if x.get("status")=="ACTIVE"}
        raw_tasks=[deepcopy(x) for x in self.snapshot.resources.get("tasks",[]) if x.get("task_id") not in finished|active]
        raw_tasks.sort(key=lambda x:(-int(x.get("priority",0)),x.get("task_id","")))
        from .resources import TaskDemand
        for raw in raw_tasks:
            try: return self.claim_task(TaskDemand(**raw),worker_id,lease_seconds=lease_seconds)
            except (ValueError,KeyError): continue
        return None
