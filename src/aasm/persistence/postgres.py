from __future__ import annotations
import json, time
from ..checkpoint import Checkpoint
from ..effects import EffectRecord, EffectStatus
from ..model import Event, MachineSnapshot, MachineState
from .serde import event_from_dict, event_to_dict, snapshot_from_dict, snapshot_to_dict
from .effect_serde import effect_from_dict, effect_to_dict

try:
    import psycopg
except ImportError as exc:
    psycopg=None; _IMPORT_ERROR=exc
else:
    _IMPORT_ERROR=None


class PostgresStore:
    """PostgreSQL coordination store for multi-host AASM control planes.

    Event sequence allocation is serialized with a transaction-scoped advisory
    lock. Task claims use a unique machine/task key and atomic expired-claim
    replacement, so workers on different hosts cannot both own one live task.
    """
    def __init__(self,dsn:str):
        if psycopg is None: raise RuntimeError("PostgresStore requires `pip install 'aasm-runtime[postgres]'`") from _IMPORT_ERROR
        self.dsn=dsn; self._conn=psycopg.connect(dsn,autocommit=False); self._migrate()

    def _migrate(self):
        ddl="""
        CREATE TABLE IF NOT EXISTS aasm_runs(machine_id TEXT PRIMARY KEY,snapshot_json JSONB NOT NULL,state TEXT NOT NULL,version BIGINT NOT NULL,created_at DOUBLE PRECISION NOT NULL,updated_at DOUBLE PRECISION NOT NULL);
        CREATE TABLE IF NOT EXISTS aasm_events(machine_id TEXT NOT NULL,sequence BIGINT NOT NULL,event_id TEXT NOT NULL UNIQUE,event_json JSONB NOT NULL,created_at DOUBLE PRECISION NOT NULL,PRIMARY KEY(machine_id,sequence),FOREIGN KEY(machine_id) REFERENCES aasm_runs(machine_id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS aasm_checkpoints(checkpoint_id TEXT PRIMARY KEY,machine_id TEXT NOT NULL,snapshot_json JSONB NOT NULL,reason TEXT NOT NULL,created_at DOUBLE PRECISION NOT NULL,FOREIGN KEY(machine_id) REFERENCES aasm_runs(machine_id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS aasm_effects(effect_id TEXT PRIMARY KEY,machine_id TEXT NOT NULL,idempotency_key TEXT NOT NULL,status TEXT NOT NULL,effect_json JSONB NOT NULL,created_at DOUBLE PRECISION NOT NULL,updated_at DOUBLE PRECISION NOT NULL,UNIQUE(machine_id,idempotency_key),FOREIGN KEY(machine_id) REFERENCES aasm_runs(machine_id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS aasm_task_claims(machine_id TEXT NOT NULL,task_id TEXT NOT NULL,lease_id TEXT NOT NULL,worker_id TEXT NOT NULL,expires_at DOUBLE PRECISION NOT NULL,PRIMARY KEY(machine_id,task_id),UNIQUE(machine_id,lease_id),FOREIGN KEY(machine_id) REFERENCES aasm_runs(machine_id) ON DELETE CASCADE);
        CREATE INDEX IF NOT EXISTS aasm_events_machine_idx ON aasm_events(machine_id,sequence);
        CREATE INDEX IF NOT EXISTS aasm_claim_expiry_idx ON aasm_task_claims(machine_id,expires_at);
        """
        with self._conn.transaction():
            with self._conn.cursor() as cur: cur.execute(ddl)

    @staticmethod
    def _j(data): return json.dumps(data,sort_keys=True)
    @staticmethod
    def _obj(value): return value if isinstance(value,dict) else json.loads(value)

    def initialize_run(self,snapshot:MachineSnapshot):
        ts=time.time()
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute("INSERT INTO aasm_runs(machine_id,snapshot_json,state,version,created_at,updated_at) VALUES(%s,%s::jsonb,%s,%s,%s,%s) ON CONFLICT(machine_id) DO NOTHING",(snapshot.machine_id,self._j(snapshot_to_dict(snapshot)),snapshot.state,snapshot.version,ts,ts))

    def append(self,machine_id:str,event:Event,snapshot:MachineSnapshot)->Event:
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",(machine_id,))
                cur.execute("SELECT COALESCE(MAX(sequence),0)+1 FROM aasm_events WHERE machine_id=%s",(machine_id,)); seq=int(cur.fetchone()[0])
                event.machine_id=machine_id; event.sequence=seq
                cur.execute("INSERT INTO aasm_events(machine_id,sequence,event_id,event_json,created_at) VALUES(%s,%s,%s,%s::jsonb,%s)",(machine_id,seq,event.event_id,self._j(event_to_dict(event)),event.ts))
                cur.execute("UPDATE aasm_runs SET snapshot_json=%s::jsonb,state=%s,version=%s,updated_at=%s WHERE machine_id=%s",(self._j(snapshot_to_dict(snapshot)),snapshot.state,snapshot.version,time.time(),machine_id))
        return event

    def load_snapshot(self,machine_id):
        with self._conn.cursor() as cur: cur.execute("SELECT snapshot_json FROM aasm_runs WHERE machine_id=%s",(machine_id,)); row=cur.fetchone()
        if row is None: raise KeyError(machine_id)
        return snapshot_from_dict(self._obj(row[0]))

    def load_events(self,machine_id,after_sequence=0):
        with self._conn.cursor() as cur: cur.execute("SELECT event_json FROM aasm_events WHERE machine_id=%s AND sequence>%s ORDER BY sequence",(machine_id,after_sequence)); rows=cur.fetchall()
        return [event_from_dict(self._obj(r[0])) for r in rows]

    def list_unfinished(self):
        with self._conn.cursor() as cur: cur.execute("SELECT machine_id,snapshot_json,state FROM aasm_runs ORDER BY updated_at"); rows=cur.fetchall()
        out=[]
        for mid,raw,state in rows:
            snap=snapshot_from_dict(self._obj(raw)); terminals=set(snap.metadata.get("machine_definition",{}).get("terminal_states",[MachineState.COMPLETE.value,MachineState.FAIL.value]))
            if state not in terminals: out.append(mid)
        return out

    def save_checkpoint(self,machine_id,checkpoint):
        with self._conn.transaction():
            with self._conn.cursor() as cur: cur.execute("INSERT INTO aasm_checkpoints(checkpoint_id,machine_id,snapshot_json,reason,created_at) VALUES(%s,%s,%s::jsonb,%s,%s) ON CONFLICT(checkpoint_id) DO UPDATE SET snapshot_json=excluded.snapshot_json,reason=excluded.reason",(checkpoint.checkpoint_id,machine_id,self._j(snapshot_to_dict(checkpoint.snapshot)),checkpoint.reason,time.time()))

    def load_checkpoint(self,machine_id,checkpoint_id):
        with self._conn.cursor() as cur: cur.execute("SELECT snapshot_json,reason FROM aasm_checkpoints WHERE machine_id=%s AND checkpoint_id=%s",(machine_id,checkpoint_id)); row=cur.fetchone()
        if row is None: raise KeyError(checkpoint_id)
        return Checkpoint(checkpoint_id,snapshot_from_dict(self._obj(row[0])),row[1])

    def save_effect(self,record:EffectRecord):
        with self._conn.transaction():
            with self._conn.cursor() as cur: cur.execute("INSERT INTO aasm_effects(effect_id,machine_id,idempotency_key,status,effect_json,created_at,updated_at) VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s) ON CONFLICT(effect_id) DO UPDATE SET status=excluded.status,effect_json=excluded.effect_json,updated_at=excluded.updated_at",(record.spec.effect_id,record.machine_id,record.spec.idempotency_key,record.status,self._j(effect_to_dict(record)),record.created_at,record.updated_at))

    def load_effect(self,machine_id,effect_id):
        with self._conn.cursor() as cur: cur.execute("SELECT effect_json FROM aasm_effects WHERE machine_id=%s AND effect_id=%s",(machine_id,effect_id)); row=cur.fetchone()
        if row is None: raise KeyError(effect_id)
        return effect_from_dict(self._obj(row[0]))

    def find_effect_by_idempotency(self,machine_id,idempotency_key):
        with self._conn.cursor() as cur: cur.execute("SELECT effect_json FROM aasm_effects WHERE machine_id=%s AND idempotency_key=%s",(machine_id,idempotency_key)); row=cur.fetchone()
        return None if row is None else effect_from_dict(self._obj(row[0]))

    def list_effects(self,machine_id):
        with self._conn.cursor() as cur: cur.execute("SELECT effect_json FROM aasm_effects WHERE machine_id=%s ORDER BY created_at,effect_id",(machine_id,)); rows=cur.fetchall()
        return [effect_from_dict(self._obj(r[0])) for r in rows]

    def mark_running_effects_unknown(self,machine_id):
        changed=[]
        for record in self.list_effects(machine_id):
            if record.status==EffectStatus.RUNNING.value:
                record.status=EffectStatus.UNKNOWN.value; record.error="process ended while effect outcome was unresolved"; record.updated_at=time.time(); self.save_effect(record); changed.append(record)
        return changed

    def acquire_task_claim(self,machine_id,task_id,lease_id,worker_id,expires_at,at_time):
        sql="""INSERT INTO aasm_task_claims(machine_id,task_id,lease_id,worker_id,expires_at) VALUES(%s,%s,%s,%s,%s)
        ON CONFLICT(machine_id,task_id) DO UPDATE SET lease_id=excluded.lease_id,worker_id=excluded.worker_id,expires_at=excluded.expires_at
        WHERE aasm_task_claims.expires_at <= %s RETURNING lease_id"""
        with self._conn.transaction():
            with self._conn.cursor() as cur: cur.execute(sql,(machine_id,task_id,lease_id,worker_id,expires_at,at_time)); return cur.fetchone() is not None

    def renew_task_claim(self,machine_id,lease_id,expires_at):
        with self._conn.transaction():
            with self._conn.cursor() as cur: cur.execute("UPDATE aasm_task_claims SET expires_at=%s WHERE machine_id=%s AND lease_id=%s",(expires_at,machine_id,lease_id)); return cur.rowcount==1

    def release_task_claim(self,machine_id,lease_id):
        with self._conn.transaction():
            with self._conn.cursor() as cur: cur.execute("DELETE FROM aasm_task_claims WHERE machine_id=%s AND lease_id=%s",(machine_id,lease_id))

    def close(self): self._conn.close()
