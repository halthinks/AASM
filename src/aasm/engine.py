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
from .core.reducer import reduce_event, replay_events
from .persistence import MemoryStore
from .persistence.serde import problem_to_dict, snapshot_to_dict
from .effects import EffectRecord, EffectSpec, EffectStatus, EffectExecutionError, EffectUnknownOutcome

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
    """AASM runtime with an event-sourced authoritative state path.

    v0.1 call sites remain valid. Supplying a Store makes the run durable.
    """

    def __init__(self, problem:ProblemSpec, authority=None, store=None, machine_id:str|None=None):
        self.store=store or MemoryStore()
        self.events=[]; self.router=AlgorithmRouter(); self.graph=PlanGraph(); self.memory=DPMemory(); self.checkpoints=CheckpointStore()
        self.flow=ResourceFlowAllocator(); self.adversary=default_verifier(); self.authority=authority or SingleControllerAuthority(); self.agents={}
        mid=machine_id or new_id("machine")
        seed=MachineSnapshot(mid,0,MachineState.INGEST.value,problem)
        self.store.initialize_run(seed)
        created=Event(new_id("evt"),now(),EventType.MACHINE_CREATED.value,None,MachineState.INGEST.value,"machine initialized",data={"machine_id":mid,"state":MachineState.INGEST.value,"problem":problem_to_dict(problem)},machine_id=mid)
        self.snapshot=reduce_event(None,created)
        self._append_existing(created)
        self.emit(EventType.GOAL_RECEIVED.value,None,MachineState.INGEST.value,"goal initialized",data={"goal":problem.goal})

    @classmethod
    def resume(cls, machine_id:str, store, authority=None):
        """Recover an unfinished or completed run from its durable event stream."""
        events=store.load_events(machine_id)
        if not events:
            raise KeyError(machine_id)
        snapshot=replay_events(events)
        self=cls.__new__(cls)
        self.store=store; self.events=list(events); self.snapshot=snapshot
        self.router=AlgorithmRouter(); self.graph=PlanGraph(); self.memory=DPMemory(); self.checkpoints=CheckpointStore()
        self.flow=ResourceFlowAllocator(); self.adversary=default_verifier(); self.authority=authority or SingleControllerAuthority(); self.agents={}
        marker=getattr(store, "mark_running_effects_unknown", None)
        if marker:
            for record in marker(machine_id):
                self.emit(EventType.EFFECT_UNKNOWN.value,self.state.value,self.state.value,"recovered unresolved effect",data={"effect_id":record.spec.effect_id,"idempotency_key":record.spec.idempotency_key})
        return self

    @classmethod
    def recover_unfinished(cls, store, authority=None):
        return [cls.resume(machine_id,store,authority=authority) for machine_id in store.list_unfinished()]

    def register_agent(self,agent): self.agents[agent.agent_id]=agent
    @property
    def state(self): return MachineState(self.snapshot.state)
    def allowed(self): return sorted(x.value for x in TRANSITIONS[self.state])

    def _append_existing(self,event:Event):
        stored=self.store.append(self.snapshot.machine_id,event,self.snapshot)
        self.events.append(stored)
        return stored

    def _commit(self,event:Event):
        self.snapshot=reduce_event(self.snapshot,event)
        stored=self.store.append(self.snapshot.machine_id,event,self.snapshot)
        self.events.append(stored)
        return stored

    def transition(self,to:MachineState|str,reason:str,evidence=None,data=None):
        to=MachineState(to)
        if to not in TRANSITIONS[self.state]: raise ValueError(f"Illegal transition {self.state.value}->{to.value}; allowed={self.allowed()}")
        old=self.state
        event=Event(new_id("evt"),now(),EventType.TRANSITION_COMMITTED.value,old.value,to.value,reason,evidence or [],data or {},machine_id=self.snapshot.machine_id)
        self._commit(event)
        return self.snapshot

    def patch_snapshot(self,patch:dict,reason:str="snapshot update"):
        event=Event(new_id("evt"),now(),EventType.SNAPSHOT_PATCHED.value,self.state.value,self.state.value,reason,data={"patch":patch},machine_id=self.snapshot.machine_id)
        self._commit(event)
        return self.snapshot

    def emit(self,event_type,from_state,to_state,reason,evidence=None,data=None):
        e=Event(new_id("evt"),now(),event_type,from_state,to_state,reason,evidence or [],data or {},machine_id=self.snapshot.machine_id)
        return self._append_existing(e)

    def classify(self):
        d=self.router.route(self.snapshot.problem)
        self.patch_snapshot({"metadata":{"algorithm_route":asdict(d)}},"algorithm route selected")
        return d

    def checkpoint(self,reason=""):
        cp=self.checkpoints.save(self.snapshot,reason)
        self.store.save_checkpoint(self.snapshot.machine_id,cp)
        self.emit(EventType.CHECKPOINT_CREATED.value,self.state.value,self.state.value,reason or "checkpoint created",data={"checkpoint_id":cp.checkpoint_id})
        return cp

    def backtrack(self,checkpoint_id,reason="backtrack"):
        if self.state!=MachineState.BACKTRACK: self.transition(MachineState.BACKTRACK,reason)
        try:
            cp=self.store.load_checkpoint(self.snapshot.machine_id,checkpoint_id)
            restored=cp.snapshot
        except KeyError:
            restored=self.checkpoints.restore(checkpoint_id)
        event=Event(new_id("evt"),now(),EventType.CHECKPOINT_RESTORED.value,MachineState.BACKTRACK.value,restored.state,reason,data={"checkpoint_id":checkpoint_id,"snapshot":snapshot_to_dict(restored)},machine_id=self.snapshot.machine_id)
        self._commit(event)
        return self.snapshot

    def propose_effect(self, spec:EffectSpec) -> EffectRecord:
        existing=self.store.find_effect_by_idempotency(self.snapshot.machine_id,spec.idempotency_key)
        if existing is not None:
            return existing
        record=EffectRecord(self.snapshot.machine_id,spec)
        self.store.save_effect(record)
        self.emit(EventType.EFFECT_PROPOSED.value,self.state.value,self.state.value,"effect proposed",data={"effect_id":spec.effect_id,"effect_type":spec.effect_type,"idempotency_key":spec.idempotency_key})
        return record

    def authorize_effect(self,effect_id:str,authority:str="controller") -> EffectRecord:
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status == EffectStatus.SUCCEEDED.value:
            return record
        if record.status not in {EffectStatus.PROPOSED.value,EffectStatus.FAILED.value}:
            raise ValueError(f"Cannot authorize effect from status {record.status}")
        record.status=EffectStatus.AUTHORIZED.value; record.authorization_id=new_id("auth"); record.authority=authority; record.updated_at=now()
        self.store.save_effect(record)
        self.emit(EventType.EFFECT_AUTHORIZED.value,self.state.value,self.state.value,"effect authorized",data={"effect_id":effect_id,"authorization_id":record.authorization_id,"authority":authority})
        return record

    def execute_effect(self,effect_id:str,executor) -> EffectRecord:
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status == EffectStatus.SUCCEEDED.value:
            return record
        if record.status == EffectStatus.UNKNOWN.value:
            if not record.spec.retry_policy.retry_on_unknown:
                raise EffectUnknownOutcome(f"Effect {effect_id} has an unknown prior outcome; reconcile before retry")
            record.status=EffectStatus.AUTHORIZED.value
        if record.status == EffectStatus.FAILED.value:
            if not record.spec.retry_policy.retry_on_failure:
                raise EffectExecutionError(f"Effect {effect_id} failed and retry_on_failure is disabled")
            record.status=EffectStatus.AUTHORIZED.value
        if record.status != EffectStatus.AUTHORIZED.value:
            raise ValueError(f"Effect {effect_id} is not authorized (status={record.status})")
        if record.attempts >= max(1,record.spec.retry_policy.max_attempts):
            raise EffectExecutionError(f"Effect {effect_id} exhausted retry attempts")
        record.attempts += 1; record.status=EffectStatus.RUNNING.value; record.updated_at=now(); self.store.save_effect(record)
        self.emit(EventType.EFFECT_STARTED.value,self.state.value,self.state.value,"effect started",data={"effect_id":effect_id,"attempt":record.attempts,"idempotency_key":record.spec.idempotency_key})
        try:
            result=executor(record.spec,record.spec.idempotency_key)
        except Exception as exc:
            record.status=EffectStatus.FAILED.value; record.error=f"{type(exc).__name__}: {exc}"; record.updated_at=now(); self.store.save_effect(record)
            self.emit(EventType.EFFECT_FAILED.value,self.state.value,self.state.value,"effect failed",data={"effect_id":effect_id,"attempt":record.attempts,"error":record.error})
            return record
        record.status=EffectStatus.SUCCEEDED.value; record.result=dict(result or {}); record.error=None; record.updated_at=now(); self.store.save_effect(record)
        self.emit(EventType.EFFECT_SUCCEEDED.value,self.state.value,self.state.value,"effect succeeded",data={"effect_id":effect_id,"attempt":record.attempts,"result":record.result})
        return record

    def reconcile_effect(self,effect_id:str,*,succeeded:bool,result:dict|None=None,evidence:list[str]|None=None,error:str|None=None) -> EffectRecord:
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status != EffectStatus.UNKNOWN.value:
            raise ValueError("Only UNKNOWN effects require reconciliation")
        record.status=EffectStatus.SUCCEEDED.value if succeeded else EffectStatus.FAILED.value
        record.result=dict(result or {}) if succeeded else None; record.error=error; record.evidence=list(evidence or []); record.updated_at=now(); self.store.save_effect(record)
        self.emit(EventType.EFFECT_RECONCILED.value,self.state.value,self.state.value,"effect reconciled",record.evidence,{"effect_id":effect_id,"status":record.status,"result":record.result,"error":record.error})
        return record

    def list_effects(self):
        return self.store.list_effects(self.snapshot.machine_id)

    def propose_and_execute(self,agent_id,*,votes=None):
        agent=self.agents[agent_id]; proposal=agent.propose(deepcopy(self.snapshot)); self.emit(EventType.PROPOSAL.value,self.state.value,self.state.value,proposal.rationale,data=asdict(proposal))
        auth=self.authority.authorize(proposal,votes=votes); self.emit(EventType.AUTHORIZED.value,self.state.value,self.state.value,"proposal authorized",data={"authority":auth.authority})
        result=agent.execute(auth); self.emit(EventType.RESULT.value,self.state.value,self.state.value,"agent result",result.evidence,asdict(result)); return result
    def verify(self,context:dict): return self.adversary.verify(context)
    def replay(self): return replay_events(self.store.load_events(self.snapshot.machine_id))
    def export(self): return {"snapshot":asdict(self.snapshot),"events":[asdict(e) for e in self.events],"allowed_transitions":self.allowed()}
