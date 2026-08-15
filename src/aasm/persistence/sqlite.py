from __future__ import annotations

from copy import deepcopy
import json
import sqlite3
import threading
import time
from pathlib import Path

from ..checkpoint import Checkpoint
from ..core.reducer import reduce_event
from ..model import Event, EventType, MachineSnapshot, MachineState, new_id
from ..effects import EffectExecutionError, EffectRecord, EffectStatus, EffectUnknownOutcome
from .serde import event_from_dict, event_to_dict, snapshot_from_dict, snapshot_to_dict
from .effect_serde import effect_from_dict, effect_to_dict


class SQLiteStore:
    """Crash-safe local persistence using only Python's standard library."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA synchronous=FULL")
        self._migrate()

    def _migrate(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    machine_id TEXT PRIMARY KEY,
                    snapshot_json TEXT NOT NULL,
                    state TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    machine_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_id TEXT NOT NULL UNIQUE,
                    event_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY (machine_id, sequence),
                    FOREIGN KEY (machine_id) REFERENCES runs(machine_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,
                    machine_id TEXT NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    FOREIGN KEY (machine_id) REFERENCES runs(machine_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS effects (
                    effect_id TEXT PRIMARY KEY,
                    machine_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    status TEXT NOT NULL,
                    effect_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    UNIQUE(machine_id, idempotency_key),
                    FOREIGN KEY (machine_id) REFERENCES runs(machine_id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS task_claims (
                    machine_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    lease_id TEXT NOT NULL,
                    worker_id TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    resource_id TEXT,
                    demand REAL NOT NULL DEFAULT 0,
                    PRIMARY KEY (machine_id, task_id),
                    UNIQUE(machine_id, lease_id),
                    FOREIGN KEY (machine_id) REFERENCES runs(machine_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_events_machine ON events(machine_id, sequence);
                CREATE INDEX IF NOT EXISTS idx_runs_state ON runs(state);
                CREATE INDEX IF NOT EXISTS idx_effects_machine ON effects(machine_id, status);
                CREATE INDEX IF NOT EXISTS idx_claims_expiry ON task_claims(machine_id, expires_at);
                CREATE INDEX IF NOT EXISTS idx_claims_resource ON task_claims(machine_id, resource_id, expires_at);
                """
            )
            columns={row[1] for row in self._conn.execute("PRAGMA table_info(task_claims)").fetchall()}
            if "resource_id" not in columns: self._conn.execute("ALTER TABLE task_claims ADD COLUMN resource_id TEXT")
            if "demand" not in columns: self._conn.execute("ALTER TABLE task_claims ADD COLUMN demand REAL NOT NULL DEFAULT 0")

    def initialize_run(self, snapshot: MachineSnapshot) -> None:
        ts=time.time(); payload=json.dumps(snapshot_to_dict(snapshot),sort_keys=True)
        with self._lock,self._conn:
            self._conn.execute("INSERT OR IGNORE INTO runs(machine_id,snapshot_json,state,version,created_at,updated_at) VALUES(?,?,?,?,?,?)",(snapshot.machine_id,payload,snapshot.state,snapshot.version,ts,ts))

    @staticmethod
    def _replace_snapshot(target:MachineSnapshot,source:MachineSnapshot):
        target.__dict__.clear(); target.__dict__.update(deepcopy(source.__dict__))

    def append(self,machine_id:str,event:Event,snapshot:MachineSnapshot)->Event:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                run=self._conn.execute("SELECT snapshot_json FROM runs WHERE machine_id=?",(machine_id,)).fetchone()
                if run is None: raise KeyError(machine_id)
                last_sequence=int(self._conn.execute("SELECT COALESCE(MAX(sequence),0) FROM events WHERE machine_id=?",(machine_id,)).fetchone()[0])
                canonical=None if last_sequence==0 else snapshot_from_dict(json.loads(run["snapshot_json"]))
                event.machine_id=machine_id; event.sequence=last_sequence+1
                expected_version=event.data.get("expected_machine_version")
                if canonical is not None and expected_version is not None and canonical.version!=int(expected_version): raise ValueError(f"Stale machine version: event expected {int(expected_version)}, canonical version is {canonical.version}")
                if canonical is not None and event.event_type==EventType.TRANSITION_COMMITTED.value and event.from_state is not None and canonical.state!=event.from_state:
                    raise ValueError(f"Stale transition: event expected {event.from_state}, canonical state is {canonical.state}")
                canonical=reduce_event(canonical,event)
                self._conn.execute("INSERT INTO events(machine_id,sequence,event_id,event_json,created_at) VALUES(?,?,?,?,?)",(machine_id,event.sequence,event.event_id,json.dumps(event_to_dict(event),sort_keys=True),event.ts))
                self._conn.execute("UPDATE runs SET snapshot_json=?,state=?,version=?,updated_at=? WHERE machine_id=?",(json.dumps(snapshot_to_dict(canonical),sort_keys=True),canonical.state,canonical.version,time.time(),machine_id))
                self._conn.commit()
            except Exception:
                self._conn.rollback(); raise
        self._replace_snapshot(snapshot,canonical); return event

    def load_snapshot(self,machine_id:str)->MachineSnapshot:
        row=self._conn.execute("SELECT snapshot_json FROM runs WHERE machine_id=?",(machine_id,)).fetchone()
        if row is None: raise KeyError(machine_id)
        return snapshot_from_dict(json.loads(row["snapshot_json"]))
    def load_events(self,machine_id:str,after_sequence:int=0)->list[Event]:
        rows=self._conn.execute("SELECT event_json FROM events WHERE machine_id=? AND sequence>? ORDER BY sequence",(machine_id,after_sequence)).fetchall()
        return [event_from_dict(json.loads(row["event_json"])) for row in rows]
    def load_first_event(self,machine_id:str)->Event:
        row=self._conn.execute("SELECT event_json FROM events WHERE machine_id=? ORDER BY sequence LIMIT 1",(machine_id,)).fetchone()
        if row is None: raise KeyError(machine_id)
        return event_from_dict(json.loads(row["event_json"]))
    def last_event_sequence(self,machine_id:str)->int:
        return int(self._conn.execute("SELECT COALESCE(MAX(sequence),0) FROM events WHERE machine_id=?",(machine_id,)).fetchone()[0])

    def list_unfinished(self)->list[str]:
        rows=self._conn.execute("SELECT machine_id,snapshot_json,state FROM runs ORDER BY updated_at").fetchall(); unfinished=[]
        for row in rows:
            snap=snapshot_from_dict(json.loads(row["snapshot_json"])); terminal=set(snap.metadata.get("machine_definition",{}).get("terminal_states",[MachineState.COMPLETE.value,MachineState.FAIL.value]))
            if row["state"] not in terminal: unfinished.append(row["machine_id"])
        return unfinished

    def save_checkpoint(self,machine_id:str,checkpoint:Checkpoint)->None:
        with self._lock,self._conn:
            self._conn.execute("INSERT OR REPLACE INTO checkpoints(checkpoint_id,machine_id,snapshot_json,reason,created_at) VALUES(?,?,?,?,?)",(checkpoint.checkpoint_id,machine_id,json.dumps(snapshot_to_dict(checkpoint.snapshot),sort_keys=True),checkpoint.reason,time.time()))
    def load_checkpoint(self,machine_id:str,checkpoint_id:str)->Checkpoint:
        row=self._conn.execute("SELECT snapshot_json,reason FROM checkpoints WHERE machine_id=? AND checkpoint_id=?",(machine_id,checkpoint_id)).fetchone()
        if row is None: raise KeyError(checkpoint_id)
        return Checkpoint(checkpoint_id,snapshot_from_dict(json.loads(row["snapshot_json"])),row["reason"])

    def save_effect(self,record:EffectRecord)->None:
        payload=json.dumps(effect_to_dict(record),sort_keys=True)
        with self._lock,self._conn:
            self._conn.execute("INSERT INTO effects(effect_id,machine_id,idempotency_key,status,effect_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(effect_id) DO UPDATE SET status=excluded.status,effect_json=excluded.effect_json,updated_at=excluded.updated_at",(record.spec.effect_id,record.machine_id,record.spec.idempotency_key,record.status,payload,record.created_at,record.updated_at))
    def load_effect(self,machine_id:str,effect_id:str)->EffectRecord:
        row=self._conn.execute("SELECT effect_json FROM effects WHERE machine_id=? AND effect_id=?",(machine_id,effect_id)).fetchone()
        if row is None: raise KeyError(effect_id)
        return effect_from_dict(json.loads(row["effect_json"]))
    def find_effect_by_idempotency(self,machine_id:str,idempotency_key:str)->EffectRecord|None:
        row=self._conn.execute("SELECT effect_json FROM effects WHERE machine_id=? AND idempotency_key=?",(machine_id,idempotency_key)).fetchone()
        return None if row is None else effect_from_dict(json.loads(row["effect_json"]))
    def list_effects(self,machine_id:str)->list[EffectRecord]:
        rows=self._conn.execute("SELECT effect_json FROM effects WHERE machine_id=? ORDER BY created_at,effect_id",(machine_id,)).fetchall()
        return [effect_from_dict(json.loads(row["effect_json"])) for row in rows]

    @staticmethod
    def _prepare_effect_attempt(record:EffectRecord)->EffectRecord:
        if record.status==EffectStatus.SUCCEEDED.value: return record
        if record.status==EffectStatus.UNKNOWN.value:
            if not record.spec.retry_policy.retry_on_unknown: raise EffectUnknownOutcome(f"Effect {record.spec.effect_id} has an unknown prior outcome; reconcile before retry")
            record.status=EffectStatus.AUTHORIZED.value
        if record.status==EffectStatus.FAILED.value:
            if not record.spec.retry_policy.retry_on_failure: raise EffectExecutionError(f"Effect {record.spec.effect_id} failed and retry_on_failure is disabled")
            record.status=EffectStatus.AUTHORIZED.value
        if record.status==EffectStatus.RUNNING.value: raise EffectExecutionError(f"Effect {record.spec.effect_id} is already RUNNING on another executor")
        if record.status!=EffectStatus.AUTHORIZED.value: raise ValueError(f"Effect {record.spec.effect_id} is not authorized (status={record.status})")
        if record.attempts>=max(1,record.spec.retry_policy.max_attempts): raise EffectExecutionError(f"Effect {record.spec.effect_id} exhausted retry attempts")
        record.attempts+=1; record.execution_id=new_id("exec"); record.status=EffectStatus.RUNNING.value; record.updated_at=time.time(); return record

    def claim_effect_attempt(self,machine_id:str,effect_id:str)->EffectRecord:
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row=self._conn.execute("SELECT effect_json FROM effects WHERE machine_id=? AND effect_id=?",(machine_id,effect_id)).fetchone()
                if row is None: raise KeyError(effect_id)
                record=self._prepare_effect_attempt(effect_from_dict(json.loads(row["effect_json"])))
                if record.status!=EffectStatus.SUCCEEDED.value:
                    self._conn.execute("UPDATE effects SET status=?,effect_json=?,updated_at=? WHERE machine_id=? AND effect_id=?",(record.status,json.dumps(effect_to_dict(record),sort_keys=True),record.updated_at,machine_id,effect_id))
                self._conn.commit(); return record
            except Exception:
                self._conn.rollback(); raise

    def finish_effect_attempt(self,record:EffectRecord,execution_id:str)->EffectRecord:
        if record.status not in {EffectStatus.SUCCEEDED.value,EffectStatus.FAILED.value}: raise ValueError("effect finalization requires SUCCEEDED or FAILED")
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                row=self._conn.execute("SELECT effect_json FROM effects WHERE machine_id=? AND effect_id=?",(record.machine_id,record.spec.effect_id)).fetchone()
                if row is None: raise KeyError(record.spec.effect_id)
                current=effect_from_dict(json.loads(row["effect_json"]))
                if current.status!=EffectStatus.RUNNING.value or current.execution_id!=execution_id or current.attempts!=record.attempts:
                    raise EffectExecutionError(f"Effect {record.spec.effect_id} lost execution ownership before durable finalization; reconcile external outcome")
                current.status=record.status; current.result=deepcopy(record.result); current.error=record.error; current.evidence=deepcopy(record.evidence); current.updated_at=record.updated_at
                self._conn.execute("UPDATE effects SET status=?,effect_json=?,updated_at=? WHERE machine_id=? AND effect_id=?",(current.status,json.dumps(effect_to_dict(current),sort_keys=True),current.updated_at,current.machine_id,current.spec.effect_id))
                self._conn.commit(); return current
            except Exception:
                self._conn.rollback(); raise

    def mark_running_effects_unknown(self,machine_id:str)->list[EffectRecord]:
        changed=[]
        for record in self.list_effects(machine_id):
            if record.status==EffectStatus.RUNNING.value:
                record.status=EffectStatus.UNKNOWN.value; record.error="process ended while effect outcome was unresolved"; record.updated_at=time.time(); self.save_effect(record); changed.append(record)
        return changed

    @staticmethod
    def _check_claim_limits(active,*,worker_id,resource_id,demand,resource_capacity,quotas):
        if resource_id is not None and resource_capacity is not None:
            used=sum(float(row["demand"] or 0) for row in active if row["resource_id"]==resource_id)
            if used+demand>float(resource_capacity)+1e-12: raise ValueError(f"Resource capacity exhausted: {resource_id}")
        for raw in quotas or []:
            if not raw.get("enabled",True): continue
            scope=raw.get("scope","machine"); target=raw.get("target_id")
            relevant=scope=="machine" or (scope=="worker" and target==worker_id) or (scope=="resource" and target==resource_id)
            if not relevant: continue
            selected=[row for row in active if scope=="machine" or (scope=="worker" and row["worker_id"]==worker_id) or (scope=="resource" and row["resource_id"]==resource_id)]
            max_leases=raw.get("max_active_leases")
            if max_leases is not None and len(selected)>=int(max_leases): raise ValueError(f"Quota exceeded: {raw.get('quota_id')}")
            max_units=raw.get("max_capacity_units")
            if max_units is not None and sum(float(row["demand"] or 0) for row in selected)+demand>float(max_units)+1e-12: raise ValueError(f"Quota exceeded: {raw.get('quota_id')}")

    @staticmethod
    def _canonical_claim_policy(snapshot:MachineSnapshot,worker_id:str,requested_resource_id:str|None,at_time:float):
        resources=snapshot.resources or {}; worker=next((x for x in resources.get("workers",[]) if x.get("worker_id")==worker_id),None)
        if worker is None: raise KeyError(worker_id)
        if worker.get("status")!="ACTIVE": raise ValueError(f"Worker {worker_id} is not ACTIVE")
        if at_time>float(worker.get("last_heartbeat",0) or 0)+float(worker.get("heartbeat_timeout",60) or 60): raise ValueError(f"Worker {worker_id} is stale")
        resource_id=worker.get("resource_id")
        if requested_resource_id is not None and requested_resource_id!=resource_id: raise ValueError(f"Stale worker resource mapping: requested {requested_resource_id}, canonical is {resource_id}")
        resource=next((x for x in resources.get("registry",[]) if x.get("resource_id")==resource_id),None)
        if resource is None: raise KeyError(resource_id)
        if not resource.get("enabled",True): raise ValueError(f"Resource {resource_id} is disabled")
        return resource_id,float(resource.get("capacity",0) or 0),deepcopy(resources.get("quotas",[]))

    def acquire_task_claim(self,machine_id:str,task_id:str,lease_id:str,worker_id:str,expires_at:float,at_time:float,*,resource_id:str|None=None,demand:float=0.0,resource_capacity:float|None=None,quotas:list[dict]|None=None)->bool:
        del resource_capacity,quotas
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                run=self._conn.execute("SELECT snapshot_json FROM runs WHERE machine_id=?",(machine_id,)).fetchone()
                if run is None: raise KeyError(machine_id)
                canonical_resource,canonical_capacity,canonical_quotas=self._canonical_claim_policy(snapshot_from_dict(json.loads(run["snapshot_json"])),worker_id,resource_id,float(at_time))
                self._conn.execute("DELETE FROM task_claims WHERE machine_id=? AND expires_at<=?",(machine_id,at_time))
                if self._conn.execute("SELECT 1 FROM task_claims WHERE machine_id=? AND task_id=?",(machine_id,task_id)).fetchone() is not None:
                    self._conn.rollback(); return False
                active=self._conn.execute("SELECT worker_id,resource_id,demand FROM task_claims WHERE machine_id=? AND expires_at>?",(machine_id,at_time)).fetchall()
                self._check_claim_limits(active,worker_id=worker_id,resource_id=canonical_resource,demand=float(demand),resource_capacity=canonical_capacity,quotas=canonical_quotas)
                self._conn.execute("INSERT INTO task_claims(machine_id,task_id,lease_id,worker_id,expires_at,resource_id,demand) VALUES(?,?,?,?,?,?,?)",(machine_id,task_id,lease_id,worker_id,expires_at,canonical_resource,float(demand)))
                self._conn.commit(); return True
            except Exception:
                self._conn.rollback(); raise

    def renew_task_claim(self,machine_id:str,lease_id:str,expires_at:float)->bool:
        with self._lock,self._conn:
            cur=self._conn.execute("UPDATE task_claims SET expires_at=? WHERE machine_id=? AND lease_id=?",(expires_at,machine_id,lease_id)); return cur.rowcount==1
    def release_task_claim(self,machine_id:str,lease_id:str)->None:
        with self._lock,self._conn: self._conn.execute("DELETE FROM task_claims WHERE machine_id=? AND lease_id=?",(machine_id,lease_id))
    def close(self)->None: self._conn.close()
