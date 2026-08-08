from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from .model import *
from .router import AlgorithmRouter
from .graph import PlanGraph, PlanNode, PlanEdge
from .memory import DPMemory
from .evidence import EvidenceLedger, EvidenceRecord
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

TRANSITIONS={MachineState(k): {MachineState(v) for v in values} for k, values in default_machine_definition().transitions.items()}

class AASMEngine:
    def __init__(self, problem:ProblemSpec, authority=None, store=None, machine_id:str|None=None, definition:MachineDefinition|None=None):
        self.store=store or MemoryStore(); self.definition=definition or default_machine_definition(); report=check_machine(self.definition)
        if not report.valid:
            errors='; '.join(issue.message for issue in report.issues if issue.severity=='error'); raise ValueError(f'Invalid machine definition: {errors}')
        self.events=[]; self.router=AlgorithmRouter(); self.graph=PlanGraph(); self.memory=DPMemory(); self.evidence_ledger=EvidenceLedger(); self.checkpoints=CheckpointStore()
        self.flow=ResourceFlowAllocator(); self.adversary=default_verifier(); self.authority=authority or SingleControllerAuthority(); self.agents={}
        mid=machine_id or new_id('machine'); seed=MachineSnapshot(mid,0,self.definition.start_state,problem); self.store.initialize_run(seed)
        created=Event(new_id('evt'),now(),EventType.MACHINE_CREATED.value,None,self.definition.start_state,'machine initialized',data={'machine_id':mid,'state':self.definition.start_state,'problem':problem_to_dict(problem),'machine_definition':self.definition.to_dict()},machine_id=mid)
        self.snapshot=reduce_event(None,created); self._append_existing(created); self.emit(EventType.GOAL_RECEIVED.value,None,self.definition.start_state,'goal initialized',data={'goal':problem.goal})

    @staticmethod
    def _definition_from_events(events:list[Event])->MachineDefinition:
        if events:
            raw=events[0].data.get('machine_definition')
            if raw: return MachineDefinition.from_dict(raw)
        return default_machine_definition()

    @classmethod
    def _hydrate(cls,snapshot,events,store,authority=None,definition=None):
        self=cls.__new__(cls); self.store=store; self.events=list(events); self.snapshot=snapshot; self.definition=definition or cls._definition_from_events(events)
        self.router=AlgorithmRouter(); self.graph=PlanGraph.from_dict(snapshot.graph); self.memory=DPMemory(snapshot.memory); self.evidence_ledger=EvidenceLedger.from_dict(snapshot.evidence); self.checkpoints=CheckpointStore()
        self.flow=ResourceFlowAllocator(); self.adversary=default_verifier(); self.authority=authority or SingleControllerAuthority(); self.agents={}; return self

    @classmethod
    def resume(cls,machine_id,store,authority=None):
        events=store.load_events(machine_id)
        if not events: raise KeyError(machine_id)
        self=cls._hydrate(replay_events(events),events,store,authority=authority); marker=getattr(store,'mark_running_effects_unknown',None)
        if marker:
            for record in marker(machine_id): self.emit(EventType.EFFECT_UNKNOWN.value,self.state_value,self.state_value,'recovered unresolved effect',data={'effect_id':record.spec.effect_id,'idempotency_key':record.spec.idempotency_key})
        return self

    @classmethod
    def recover_unfinished(cls,store,authority=None): return [cls.resume(mid,store,authority=authority) for mid in store.list_unfinished()]
    def register_agent(self,agent): self.agents[agent.agent_id]=agent
    @property
    def state_value(self): return self.snapshot.state
    @property
    def state(self):
        try:return MachineState(self.snapshot.state)
        except ValueError:return self.snapshot.state
    def allowed(self): return sorted(self.definition.allowed(self.state_value))
    def _append_existing(self,event): stored=self.store.append(self.snapshot.machine_id,event,self.snapshot); self.events.append(stored); return stored
    def _refresh_runtime_views(self): self.graph=PlanGraph.from_dict(self.snapshot.graph); self.memory=DPMemory(self.snapshot.memory); self.evidence_ledger=EvidenceLedger.from_dict(self.snapshot.evidence)
    def _commit(self,event): self.snapshot=reduce_event(self.snapshot,event); stored=self.store.append(self.snapshot.machine_id,event,self.snapshot); self.events.append(stored); self._refresh_runtime_views(); return stored

    def transition(self,to,reason,evidence=None,data=None):
        target=to.value if isinstance(to,MachineState) else str(to)
        if target not in self.definition.allowed(self.state_value): raise ValueError(f'Illegal transition {self.state_value}->{target}; allowed={self.allowed()}')
        old=self.state_value; self._commit(Event(new_id('evt'),now(),EventType.TRANSITION_COMMITTED.value,old,target,reason,evidence or [],data or {},machine_id=self.snapshot.machine_id)); return self.snapshot
    def patch_snapshot(self,patch,reason='snapshot update'): self._commit(Event(new_id('evt'),now(),EventType.SNAPSHOT_PATCHED.value,self.state_value,self.state_value,reason,data={'patch':patch},machine_id=self.snapshot.machine_id)); return self.snapshot
    def emit(self,event_type,from_state,to_state,reason,evidence=None,data=None): return self._append_existing(Event(new_id('evt'),now(),event_type,from_state,to_state,reason,evidence or [],data or {},machine_id=self.snapshot.machine_id))
    def classify(self): d=self.router.route(self.snapshot.problem); self.patch_snapshot({'metadata':{'algorithm_route':asdict(d)}},'algorithm route selected'); return d
    def checkpoint(self,reason=''): cp=self.checkpoints.save(self.snapshot,reason); self.store.save_checkpoint(self.snapshot.machine_id,cp); self.emit(EventType.CHECKPOINT_CREATED.value,self.state_value,self.state_value,reason or 'checkpoint created',data={'checkpoint_id':cp.checkpoint_id}); return cp
    def backtrack(self,checkpoint_id,reason='backtrack'):
        if self.state_value!=MachineState.BACKTRACK.value:self.transition(MachineState.BACKTRACK,reason)
        try:restored=self.store.load_checkpoint(self.snapshot.machine_id,checkpoint_id).snapshot
        except KeyError:restored=self.checkpoints.restore(checkpoint_id)
        self._commit(Event(new_id('evt'),now(),EventType.CHECKPOINT_RESTORED.value,MachineState.BACKTRACK.value,restored.state,reason,data={'checkpoint_id':checkpoint_id,'snapshot':snapshot_to_dict(restored)},machine_id=self.snapshot.machine_id)); return self.snapshot
    def replay(self,at_sequence=None):
        events=self.store.load_events(self.snapshot.machine_id)
        if at_sequence is not None:
            events=[e for e in events if e.sequence<=at_sequence]
            if not events: raise ValueError('Fork/replay sequence precedes the first event')
        return replay_events(events)
    def fork(self,at_sequence,*,store=None,machine_id=None):
        selected=[e for e in self.store.load_events(self.snapshot.machine_id) if e.sequence<=at_sequence]
        if not selected: raise ValueError('Fork sequence precedes the first event')
        source_snapshot=replay_events(selected); target_store=store or self.store; new_mid=machine_id or new_id('machine'); fork_snapshot=deepcopy(source_snapshot); fork_snapshot.machine_id=new_mid; fork_snapshot.metadata=deepcopy(fork_snapshot.metadata); fork_snapshot.metadata['lineage']={'source_machine_id':self.snapshot.machine_id,'source_sequence':at_sequence,'source_event_id':selected[-1].event_id}; target_store.initialize_run(fork_snapshot)
        event=Event(new_id('evt'),now(),EventType.MACHINE_FORKED.value,None,fork_snapshot.state,'machine forked',data={'snapshot':snapshot_to_dict(fork_snapshot),'source_machine_id':self.snapshot.machine_id,'source_sequence':at_sequence,'source_event_id':selected[-1].event_id,'machine_definition':self.definition.to_dict()},machine_id=new_mid); snapshot=reduce_event(None,event); stored=target_store.append(new_mid,event,snapshot); return self._hydrate(snapshot,[stored],target_store,authority=self.authority,definition=self.definition)

    def plan_add_node(self,node:PlanNode,*,frontier=True,reason='plan node added'):
        self._commit(Event(new_id('evt'),now(),EventType.PLAN_NODE_ADDED.value,self.state_value,self.state_value,reason,data={'node':asdict(node)},machine_id=self.snapshot.machine_id))
        if frontier and node.node_id not in self.snapshot.frontier:self.patch_snapshot({'frontier':self.snapshot.frontier+[node.node_id]},'plan frontier updated')
        return self.graph.nodes[node.node_id]
    def plan_add_edge(self,edge:PlanEdge,*,reason='plan edge added'): self._commit(Event(new_id('evt'),now(),EventType.PLAN_EDGE_ADDED.value,self.state_value,self.state_value,reason,data={'edge':asdict(edge)},machine_id=self.snapshot.machine_id)); return edge
    def plan_update_node(self,node_id,patch,*,reason='plan node updated'): self._commit(Event(new_id('evt'),now(),EventType.PLAN_NODE_UPDATED.value,self.state_value,self.state_value,reason,data={'node_id':node_id,'patch':deepcopy(patch)},machine_id=self.snapshot.machine_id)); return self.graph.nodes[node_id]
    def plan_mark_visited(self,node_id,*,reason='plan node visited'):
        if node_id not in self.graph.nodes: raise KeyError(node_id)
        visited=list(self.snapshot.visited)
        if node_id not in visited:visited.append(node_id)
        self.patch_snapshot({'visited':visited,'frontier':[x for x in self.snapshot.frontier if x!=node_id]},reason); return self.graph.nodes[node_id]
    def plan_prune_node(self,node_id,*,reason='plan branch pruned'):
        if node_id not in self.graph.nodes: raise KeyError(node_id)
        self._commit(Event(new_id('evt'),now(),EventType.PLAN_NODE_PRUNED.value,self.state_value,self.state_value,reason,data={'node_id':node_id},machine_id=self.snapshot.machine_id)); return self.graph.nodes[node_id]
    def memo_put(self,key,value,*,scope=None,proof=None,metadata=None,reason='memoized subproblem'):
        record=self.memory.put(key,value,scope=scope,proof=proof,metadata=metadata,created_at=now()); self._commit(Event(new_id('evt'),now(),EventType.MEMORY_PUT.value,self.state_value,self.state_value,reason,data={'key':key,'record':record},machine_id=self.snapshot.machine_id)); return deepcopy(record)
    def memo_get(self,key,*,scope=None): return self.memory.get(key,scope=scope)
    def memo_invalidate(self,key,reason='assumption changed'):
        record=self.memory.invalidate(key,reason,invalidated_at=now()); self._commit(Event(new_id('evt'),now(),EventType.MEMORY_INVALIDATED.value,self.state_value,self.state_value,reason,data={'key':key,'record':record},machine_id=self.snapshot.machine_id)); return deepcopy(record)
    def add_evidence(self,record:EvidenceRecord,*,reason='evidence recorded'):
        self.evidence_ledger.add(record); self._commit(Event(new_id('evt'),now(),EventType.EVIDENCE_ADDED.value,self.state_value,self.state_value,reason,evidence=[record.evidence_id],data={'record':asdict(record)},machine_id=self.snapshot.machine_id)); return self.evidence_ledger.get(record.evidence_id)
    def add_claim(self,statement,**kwargs): return self.add_evidence(EvidenceRecord('claim',statement,**kwargs),reason='claim recorded')
    def add_observation(self,statement,**kwargs): return self.add_evidence(EvidenceRecord('observation',statement,**kwargs),reason='observation recorded')
    def add_assumption(self,statement,**kwargs): return self.add_evidence(EvidenceRecord('assumption',statement,**kwargs),reason='assumption recorded')
    def add_contradiction(self,statement,**kwargs): return self.add_evidence(EvidenceRecord('contradiction',statement,**kwargs),reason='contradiction recorded')
    def invalidate_evidence(self,evidence_id,reason):
        record=self.evidence_ledger.invalidate(evidence_id,reason); self._commit(Event(new_id('evt'),now(),EventType.EVIDENCE_INVALIDATED.value,self.state_value,self.state_value,reason,evidence=[evidence_id],data={'evidence_id':evidence_id,'record':asdict(record)},machine_id=self.snapshot.machine_id)); return self.evidence_ledger.get(evidence_id)
    def evidence_lineage(self,evidence_id): return self.evidence_ledger.lineage(evidence_id)

    def propose_effect(self,spec):
        existing=self.store.find_effect_by_idempotency(self.snapshot.machine_id,spec.idempotency_key)
        if existing is not None:return existing
        record=EffectRecord(self.snapshot.machine_id,spec); self.store.save_effect(record); self.emit(EventType.EFFECT_PROPOSED.value,self.state_value,self.state_value,'effect proposed',data={'effect_id':spec.effect_id,'effect_type':spec.effect_type,'idempotency_key':spec.idempotency_key}); return record
    def authorize_effect(self,effect_id,authority='controller'):
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status==EffectStatus.SUCCEEDED.value:return record
        if record.status not in {EffectStatus.PROPOSED.value,EffectStatus.FAILED.value}:raise ValueError(f'Cannot authorize effect from status {record.status}')
        record.status=EffectStatus.AUTHORIZED.value; record.authorization_id=new_id('auth'); record.authority=authority; record.updated_at=now(); self.store.save_effect(record); self.emit(EventType.EFFECT_AUTHORIZED.value,self.state_value,self.state_value,'effect authorized',data={'effect_id':effect_id,'authorization_id':record.authorization_id,'authority':authority}); return record
    def execute_effect(self,effect_id,executor):
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status==EffectStatus.SUCCEEDED.value:return record
        if record.status==EffectStatus.UNKNOWN.value:
            if not record.spec.retry_policy.retry_on_unknown:raise EffectUnknownOutcome(f'Effect {effect_id} has an unknown prior outcome; reconcile before retry')
            record.status=EffectStatus.AUTHORIZED.value
        if record.status==EffectStatus.FAILED.value:
            if not record.spec.retry_policy.retry_on_failure:raise EffectExecutionError(f'Effect {effect_id} failed and retry_on_failure is disabled')
            record.status=EffectStatus.AUTHORIZED.value
        if record.status!=EffectStatus.AUTHORIZED.value:raise ValueError(f'Effect {effect_id} is not authorized (status={record.status})')
        if record.attempts>=max(1,record.spec.retry_policy.max_attempts):raise EffectExecutionError(f'Effect {effect_id} exhausted retry attempts')
        record.attempts+=1; record.status=EffectStatus.RUNNING.value; record.updated_at=now(); self.store.save_effect(record); self.emit(EventType.EFFECT_STARTED.value,self.state_value,self.state_value,'effect started',data={'effect_id':effect_id,'attempt':record.attempts,'idempotency_key':record.spec.idempotency_key})
        try:result=executor(record.spec,record.spec.idempotency_key)
        except Exception as exc:
            record.status=EffectStatus.FAILED.value; record.error=f'{type(exc).__name__}: {exc}'; record.updated_at=now(); self.store.save_effect(record); self.emit(EventType.EFFECT_FAILED.value,self.state_value,self.state_value,'effect failed',data={'effect_id':effect_id,'attempt':record.attempts,'error':record.error}); return record
        record.status=EffectStatus.SUCCEEDED.value; record.result=dict(result or {}); record.error=None; record.updated_at=now(); self.store.save_effect(record); self.emit(EventType.EFFECT_SUCCEEDED.value,self.state_value,self.state_value,'effect succeeded',data={'effect_id':effect_id,'attempt':record.attempts,'result':record.result}); return record
    def reconcile_effect(self,effect_id,*,succeeded,result=None,evidence=None,error=None):
        record=self.store.load_effect(self.snapshot.machine_id,effect_id)
        if record.status!=EffectStatus.UNKNOWN.value:raise ValueError('Only UNKNOWN effects require reconciliation')
        record.status=EffectStatus.SUCCEEDED.value if succeeded else EffectStatus.FAILED.value; record.result=dict(result or {}) if succeeded else None; record.error=error; record.evidence=list(evidence or []); record.updated_at=now(); self.store.save_effect(record); self.emit(EventType.EFFECT_RECONCILED.value,self.state_value,self.state_value,'effect reconciled',record.evidence,{'effect_id':effect_id,'status':record.status,'result':record.result,'error':record.error}); return record
    def list_effects(self): return self.store.list_effects(self.snapshot.machine_id)
    def propose_and_execute(self,agent_id,*,votes=None):
        agent=self.agents[agent_id]; proposal=agent.propose(deepcopy(self.snapshot)); self.emit(EventType.PROPOSAL.value,self.state_value,self.state_value,proposal.rationale,data=asdict(proposal)); auth=self.authority.authorize(proposal,votes=votes); self.emit(EventType.AUTHORIZED.value,self.state_value,self.state_value,'proposal authorized',data={'authority':auth.authority}); result=agent.execute(auth); self.emit(EventType.RESULT.value,self.state_value,self.state_value,'agent result',result.evidence,asdict(result)); return result
    def verify(self,context): return self.adversary.verify(context)
    def export(self): return {'snapshot':asdict(self.snapshot),'events':[asdict(e) for e in self.events],'allowed_transitions':self.allowed(),'machine_definition':self.definition.to_dict()}
