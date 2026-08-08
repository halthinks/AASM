from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from .core.reducer import reduce_event, replay_events
from .effects import EffectExecutionError, EffectStatus
from .model import EventType, now
from .runtime import AASMEngine as V07Engine
from .model_routing import ModelProfile, ModelRouteRequest, ModelStrengthRouter


class AASMEngine(V07Engine):
    """v0.8 runtime: v0.7 durable workers plus model-aware routing."""
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.model_router=ModelStrengthRouter()
        self._last_sequence=self.events[-1].sequence if self.events else 0
        self._history_loaded=True

    @classmethod
    def _hydrate(cls,snapshot,events,store,authority=None,definition=None):
        self=super()._hydrate(snapshot,events,store,authority=authority,definition=definition)
        self.model_router=ModelStrengthRouter()
        self._last_sequence=events[-1].sequence if events else 0
        self._history_loaded=True
        return self

    @classmethod
    def resume(cls,machine_id,store,authority=None,*,recover_effects=False,load_history=True):
        if load_history:
            events=store.load_events(machine_id)
            if not events: raise KeyError(machine_id)
            self=cls._hydrate(replay_events(events),events,store,authority=authority)
        else:
            snapshot=store.load_snapshot(machine_id)
            first_loader=getattr(store,"load_first_event",None)
            last_loader=getattr(store,"last_event_sequence",None)
            if first_loader is None or last_loader is None:
                events=store.load_events(machine_id)
                if not events: raise KeyError(machine_id)
                first=events[0]; last_sequence=events[-1].sequence
            else:
                first=first_loader(machine_id); last_sequence=last_loader(machine_id)
            definition=cls._definition_from_events([first])
            self=cls._hydrate(snapshot,[],store,authority=authority,definition=definition)
            self._last_sequence=last_sequence
            self._history_loaded=False
        if recover_effects:
            marker=getattr(store,"mark_running_effects_unknown",None)
            if marker:
                for record in marker(machine_id):
                    self.emit(EventType.EFFECT_UNKNOWN.value,self.state_value,self.state_value,"recovered unresolved effect",data={"effect_id":record.spec.effect_id,"idempotency_key":record.spec.idempotency_key})
        return self

    @classmethod
    def recover_unfinished(cls,store,authority=None,*,recover_effects=False,load_history=True):
        return [cls.resume(mid,store,authority=authority,recover_effects=recover_effects,load_history=load_history) for mid in store.list_unfinished()]

    def _sync_after_append(self):
        after=getattr(self,"_last_sequence",self.events[-1].sequence if self.events else 0)
        fresh=self.store.load_events(self.snapshot.machine_id,after_sequence=after)
        if fresh:
            self.events.extend(fresh); self._last_sequence=fresh[-1].sequence
        self._refresh_runtime_views()

    def _commit(self,event):
        machine_id=self.snapshot.machine_id
        candidate=reduce_event(self.snapshot,event)
        try:
            stored=self.store.append(machine_id,event,candidate)
        except Exception:
            try:
                self.snapshot=self.store.load_snapshot(machine_id)
                if self._history_loaded:
                    self.events=self.store.load_events(machine_id); self._last_sequence=self.events[-1].sequence if self.events else 0
                else:
                    last_loader=getattr(self.store,"last_event_sequence",None); self._last_sequence=last_loader(machine_id) if last_loader else self._last_sequence; self.events=[]
                self._refresh_runtime_views()
            except Exception:
                pass
            raise
        self.snapshot=candidate; self._sync_after_append(); return stored

    def export(self):
        if not getattr(self,"_history_loaded",True):
            self.events=self.store.load_events(self.snapshot.machine_id); self._last_sequence=self.events[-1].sequence if self.events else 0; self._history_loaded=True
        return super().export()

    def _finish_claimed_effect(self,record):
        finisher=getattr(self.store,"finish_effect_attempt",None)
        if finisher is None:
            self.store.save_effect(record); return record
        if not record.execution_id:
            raise EffectExecutionError(f"Effect {record.spec.effect_id} has no execution ownership token")
        return finisher(record,record.execution_id)

    def execute_effect(self,effect_id,executor):
        claim=getattr(self.store,"claim_effect_attempt",None)
        if claim is None:
            return super().execute_effect(effect_id,executor)
        record=claim(self.snapshot.machine_id,effect_id)
        if record.status==EffectStatus.SUCCEEDED.value: return record
        if record.status!=EffectStatus.RUNNING.value: raise ValueError(f"Effect {effect_id} did not enter RUNNING (status={record.status})")
        self.emit(EventType.EFFECT_STARTED.value,self.state_value,self.state_value,"effect started",data={"effect_id":effect_id,"attempt":record.attempts,"execution_id":record.execution_id,"idempotency_key":record.spec.idempotency_key})
        try:
            result=executor(record.spec,record.spec.idempotency_key)
        except Exception as exc:
            record.status=EffectStatus.FAILED.value; record.error=f"{type(exc).__name__}: {exc}"; record.updated_at=now()
            record=self._finish_claimed_effect(record)
            self.emit(EventType.EFFECT_FAILED.value,self.state_value,self.state_value,"effect failed",data={"effect_id":effect_id,"attempt":record.attempts,"execution_id":record.execution_id,"error":record.error}); return record
        record.status=EffectStatus.SUCCEEDED.value; record.result=dict(result or {}); record.error=None; record.updated_at=now()
        record=self._finish_claimed_effect(record)
        self.emit(EventType.EFFECT_SUCCEEDED.value,self.state_value,self.state_value,"effect succeeded",data={"effect_id":effect_id,"attempt":record.attempts,"execution_id":record.execution_id,"result":record.result}); return record

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
        result=self.model_router.route([ModelProfile(**deepcopy(x)) for x in self.list_model_profiles()],request); resources=deepcopy(self.snapshot.resources); resources["last_model_route"]={"request":asdict(request),"result":result.to_dict()}; self.patch_snapshot({"resources":resources},reason); return result
    def last_model_route(self): return deepcopy(self.snapshot.resources.get("last_model_route"))
    def claim_next_task(self,worker_id:str,*,lease_seconds:float=60.0):
        finished={x.get("task_id") for x in self.snapshot.resources.get("leases",[]) if x.get("status")=="COMPLETED"}; active={x.get("task_id") for x in self.snapshot.resources.get("leases",[]) if x.get("status")=="ACTIVE"}; raw_tasks=[deepcopy(x) for x in self.snapshot.resources.get("tasks",[]) if x.get("task_id") not in finished|active]; raw_tasks.sort(key=lambda x:(-int(x.get("priority",0)),x.get("task_id","")))
        from .resources import TaskDemand
        for raw in raw_tasks:
            try: return self.claim_task(TaskDemand(**raw),worker_id,lease_seconds=lease_seconds)
            except (ValueError,KeyError): continue
        return None
