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
from .definitions import MachineDefinition, default_machine_definition
from .model_check import check_machine

# Backward-compatible public constant. New code should use MachineDefinition.
TRANSITIONS={
    MachineState(k): {MachineState(v) for v in values}
    for k, values in default_machine_definition().transitions.items()
}


class AASMEngine:
    """AASM runtime with event-sourced state, declarative machines, and durable effects."""

    def __init__(self, problem:ProblemSpec, authority=None, store=None, machine_id:str|None=None, definition:MachineDefinition|None=None):
        self.store=store or MemoryStore()
        self.definition=definition or default_machine_definition()
        report=check_machine(self.definition)
        if not report.valid:
            errors="; ".join(issue.message for issue in report.issues if issue.severity=="error")
            raise ValueError(f"Invalid machine definition: {errors}")
        self.events=[]; self.router=AlgorithmRouter(); self.graph=PlanGraph(); self.memory=DPMemory(); self.checkpoints=CheckpointStore()
        self.flow=ResourceFlowAllocator(); self.adversary=default_verifier(); self.authority=authority or SingleControllerAuthority(); self.agents={}
        mid=machine_id or new_id("machine")
        seed=MachineSnapshot(mid,0,self.definition.start_state,problem)
        self.store.initialize_run(seed)
        created=Event(new_id("evt"),now(),EventType.MACHINE_CREATED.value,None,self.definition.start_state,"machine initialized",data={"machine_id":mid,"state":self.definition.start_state,"problem":problem_to_dict(problem),"machine_definition":self.definition.to_dict()},machine_id=mid)
        self.snapshot=reduce_event(None,created)
        self._append_existing(created)
        self.emit(EventType.GOAL_RECEIVED.value,None,self.definition.start_state,"goal initialized",data={"goal":problem.goal})

    @staticmethod
    def _definition_from_events(events:list[Event]) -> MachineDefinition:
        if events:
            raw=events[0].data.get("machine_definition")
            if raw:
                return MachineDefinition.from_dict(raw)
        return default_machine_definition()

    @classmethod
    def _hydrate(cls, snapshot:MachineSnapshot, events:list[Event], store, authority=None, definition:MachineDefinition|None=None):
        self=cls.__new__(cls)
        self.store=store; self.events=list(events); self.snapshot=snapshot; self.definition=definition or cls._definition_from_events(events)
        self.router=AlgorithmRouter(); self.graph=PlanGraph(); self.memory=DPMemory(); self.checkpoints=CheckpointStore()
        self.flow=ResourceFlowAllocator(); self.adversary=default_verifier(); self.authority=authority or SingleControllerAuthority(); self.agents={}
        return self

    @classmethod
    def resume(cls, machine_id:str, store, authority=None):
        """Recover a run from its durable event stream."""
        events=store.load_events(machine_id)
        if not events:
            raise KeyError(machine_id)
        self=cls._hydrate(replay_events(events),events,store,authority=authority)
        marker=getattr(store,"mark_running_effects_unknown",None)
        if marker:
            for record in marker(machine_id):
                self.emit(EventType.EFFECT_UNKNOWN.value,self.state_value,self.state_value,"recovered unresolved effect",data={"effect_id":record.spec.effect_id,"idempotency_key":record.spec.idempotency_key})
        return self

    @classmethod
    def recover_unfinished(cls,store,authority=None):
        return [cls.resume(machine_id,store,authority=authority) for machine_id in store.list_unfinished()]

    def register_agent(self,agent): self.agents[agent.agent_id]=agent

    @property
    def state_value(self)->str: return self.snapshot.state

    @property
    def state(self):
        try: return MachineState(self.snapshot.state)
        except ValueError: return self.snapshot.state

    def allowed(self): return sorted(self.definition.allowed(self.state_value))

    def _append_existing(self,event:Event):
        stored=self.store.append(self.snapshot.machine_id,event,self.snapshot); self.events.append(stored); return stored

    def _commit(self,event:Event):
        self.snapshot=reduce_event(self.snapshot,event); stored=self.store.append(self.snapshot.machine_id,event,self.snapshot); self.events.append(stored); return stored

    def transition(self,to:MachineState|str,reason:str,evidence=None,data=None):
        target=to.value if isinstance(to,MachineState) else str(to)
        if target not in self.definition.allowed(self.state_value):
            raise ValueError(f"Illegal transition {self.state_value}->{target}; allowed={self.allowed()}")
        old=self.state_value
        event=Event(new_id("evt"),now(),EventType.TRANSITION_COMMITTED.value,old,target,reason,evidence or [],data or {},machine_id=self.snapshot.machine_id)
        self._commit(event); return self.snapshot

    def patch_snapshot(self,patch:dict,reason:str="snapshot update"):
        event=Event(new_id("evt"),now(),EventType.SNAPSHOT_PATCHED.value,self.state_value,self.state_value,reason,data={"patch":patch},machine_id=self.snapshot.machine_id)
        self._commit(event); return self.snapshot

    def emit(self,event_type,from_state,to_state,reason,evidence=None,data=None):
        e=Event(new_id("evt"),now(),event_type,from_state,to_state,reason,evidence or [],data or {},machine_id=self.snapshot.machine_id); return self._append_existing(e)

    def classify(self):
        d=self.router.route(self.snapshot.problem); self.patch_snapshot({"metadata":{"algorithm_route":asdict(d)}},"algorithm route selected"); return d

    def checkpoint(self,reason=""):
        cp=self.checkpoints.save(self.snapshot,reason); self.store.save_checkpoint(self.snapshot.machine_id,cp)
        self.emit(EventType.CHECKPOINT_CREATED.value,self.state_value,self.state_value,reason or "checkpoint created",data={"checkpoint_id":cp.checkpoint_id}); return cp

    def backtrack(self,checkpoint_id,reason="backtrack"):
        if self.state_value != MachineState.BACKTRACK.value:
            self.transition(MachineState.BACKTRACK,reason)
        try: restored=self.store.load_checkpoint(self.snapshot.machine_id,checkpoint_id).snapshot
        except KeyError: restored=self.checkpoints.restore(checkpoint_id)
        event=Event(new_id("evt"),now(),EventType.CHECKPOINT_RESTORED.value,MachineState.BACKTRACK.value,restored.state,reason,data={"checkpoint_id":checkpoint_id,"snapshot":snapshot_to_dict(restored)},machine_id=self.snapshot.machine_id)
        self._commit(event); return self.snapshot

    def replay(self,at_sequence:int|None=None):
        events=self.store.load_events(self.snapshot.machine_id)
        if at_sequence is not None:
            events=[event for event in events if event.sequence <= at_sequence]
            if not events: raise ValueError("Fork/replay sequence precedes the first event")
        return replay_events(events)

    def fork(self,at_sequence:int,*,store=None,machine_id:str|None=None):
        """Create a new durable machine from an earlier event boundary.

        Effects are intentionally not copied or executed. The fork records lineage
        to the source machine and sequence, then proceeds independently.
        """
        source_events=self.store.load_events(self.snapshot.machine_id)
        selected=[event for event in source_events if event.sequence <= at_sequence]
        if not selected: raise ValueError("Fork sequence precedes the first event")
        source_snapshot=replay_events(selected)
        target_store=store or self.store
        new_mid=machine_id or new_id("machine")
        fork_snapshot=deepcopy(source_snapshot); fork_snapshot.machine_id=new_mid
        fork_snapshot.metadata=deepcopy(fork_snapshot.metadata)
        fork_snapshot.metadata["lineage"]={"source_machine_id":self.snapshot.machine_id,"source_sequence":at_sequence,"source_event_id":selected[-1].event_id}
        target_store.initialize_run(fork_snapshot)
        event=Event(new_id("evt"),now(),EventType.MACHINE_FORKED.value,None,fork_snapshot.state,"machine forked",data={"snapshot":snapshot_to_dict(fork_snapshot),"source_machine_id":self.snapshot.machine_id,"source_sequence":at_sequence,"source_event_id":selected[-1].event_id,"machine_definition":self.definition.to_dict()},machine_id=new_mid)
        snapshot=reduce_event(None,event)
        stored=target_store.append(new_mid,event,snapshot)
        return self._hydrate(snapshot,[stored],target_store,authority=self.authority,definition=self.definition)

    def propose_effect(self,spec:EffectSpec)->EffectRecord:
        existing=self.store.find_effect_by_idempotency(self.snapshot.machine_id,spec.idempotency_key)
        if existing is not None: return existing
        record=EffectRecord(self.snapshot.machine_id,spec); self.store.save_effect(record)
        self.emit(EventType.EFFECT_PROPOSED.value,self.state_value,self.state_value,"effect proposed",data={"effect_id":spec.effect_id,"effect_type":spec.effect_type,"idempotency_key":spec.idempotency_key}); return record

    def authorize_effect(self,effect_id:str,authority:str="controller")->EffectRecord:
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status==EffectStatus.SUCCEEDED.value: return record
        if record.status not in {EffectStatus.PROPOSED.value,EffectStatus.FAILED.value}: raise ValueError(f"Cannot authorize effect from status {record.status}")
        record.status=EffectStatus.AUTHORIZED.value; record.authorization_id=new_id("auth"); record.authority=authority; record.updated_at=now(); self.store.save_effect(record)
        self.emit(EventType.EFFECT_AUTHORIZED.value,self.state_value,self.state_value,"effect authorized",data={"effect_id":effect_id,"authorization_id":record.authorization_id,"authority":authority}); return record

    def execute_effect(self,effect_id:str,executor)->EffectRecord:
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status==EffectStatus.SUCCEEDED.value: return record
        if record.status==EffectStatus.UNKNOWN.value:
            if not record.spec.retry_policy.retry_on_unknown: raise EffectUnknownOutcome(f"Effect {effect_id} has an unknown prior outcome; reconcile before retry")
            record.status=EffectStatus.AUTHORIZED.value
        if record.status==EffectStatus.FAILED.value:
            if not record.spec.retry_policy.retry_on_failure: raise EffectExecutionError(f"Effect {effect_id} failed and retry_on_failure is disabled")
            record.status=EffectStatus.AUTHORIZED.value
        if record.status!=EffectStatus.AUTHORIZED.value: raise ValueError(f"Effect {effect_id} is not authorized (status={record.status})")
        if record.attempts>=max(1,record.spec.retry_policy.max_attempts): raise EffectExecutionError(f"Effect {effect_id} exhausted retry attempts")
        record.attempts+=1; record.status=EffectStatus.RUNNING.value; record.updated_at=now(); self.store.save_effect(record)
        self.emit(EventType.EFFECT_STARTED.value,self.state_value,self.state_value,"effect started",data={"effect_id":effect_id,"attempt":record.attempts,"idempotency_key":record.spec.idempotency_key})
        try: result=executor(record.spec,record.spec.idempotency_key)
        except Exception as exc:
            record.status=EffectStatus.FAILED.value; record.error=f"{type(exc).__name__}: {exc}"; record.updated_at=now(); self.store.save_effect(record)
            self.emit(EventType.EFFECT_FAILED.value,self.state_value,self.state_value,"effect failed",data={"effect_id":effect_id,"attempt":record.attempts,"error":record.error}); return record
        record.status=EffectStatus.SUCCEEDED.value; record.result=dict(result or {}); record.error=None; record.updated_at=now(); self.store.save_effect(record)
        self.emit(EventType.EFFECT_SUCCEEDED.value,self.state_value,self.state_value,"effect succeeded",data={"effect_id":effect_id,"attempt":record.attempts,"result":record.result}); return record

    def reconcile_effect(self,effect_id:str,*,succeeded:bool,result:dict|None=None,evidence:list[str]|None=None,error:str|None=None)->EffectRecord:
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status!=EffectStatus.UNKNOWN.value: raise ValueError("Only UNKNOWN effects require reconciliation")
        record.status=EffectStatus.SUCCEEDED.value if succeeded else EffectStatus.FAILED.value
        record.result=dict(result or {}) if succeeded else None; record.error=error; record.evidence=list(evidence or []); record.updated_at=now(); self.store.save_effect(record)
        self.emit(EventType.EFFECT_RECONCILED.value,self.state_value,self.state_value,"effect reconciled",record.evidence,{"effect_id":effect_id,"status":record.status,"result":record.result,"error":record.error}); return record

    def list_effects(self): return self.store.list_effects(self.snapshot.machine_id)

    def propose_and_execute(self,agent_id,*,votes=None):
        agent=self.agents[agent_id]; proposal=agent.propose(deepcopy(self.snapshot)); self.emit(EventType.PROPOSAL.value,self.state_value,self.state_value,proposal.rationale,data=asdict(proposal))
        auth=self.authority.authorize(proposal,votes=votes); self.emit(EventType.AUTHORIZED.value,self.state_value,self.state_value,"proposal authorized",data={"authority":auth.authority})
        result=agent.execute(auth); self.emit(EventType.RESULT.value,self.state_value,self.state_value,"agent result",result.evidence,asdict(result)); return result

    def verify(self,context:dict): return self.adversary.verify(context)
    def export(self): return {"snapshot":asdict(self.snapshot),"events":[asdict(e) for e in self.events],"allowed_transitions":self.allowed(),"machine_definition":self.definition.to_dict()}
