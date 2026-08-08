from __future__ import annotations

from copy import deepcopy
import json
import time

from ..checkpoint import Checkpoint
from ..core.reducer import reduce_event, replay_events
from ..effects import EffectRecord, EffectStatus
from ..model import Event, EventType, MachineSnapshot, MachineState
from .serde import event_from_dict, event_to_dict, snapshot_from_dict, snapshot_to_dict
from .effect_serde import effect_from_dict, effect_to_dict

try:
    import psycopg
except ImportError as exc:
    psycopg=None
    _IMPORT_ERROR=exc
else:
    _IMPORT_ERROR=None


class PostgresStore:
    """PostgreSQL coordination store for multi-host AASM control planes.

    Per-machine advisory locks serialize authoritative event reduction. Claims
    acquire the same event lock before the claim lock, read the current durable
    machine snapshot, and enforce worker/resource/quota policy from PostgreSQL.
    A stale worker process therefore cannot claim using obsolete capacity or
    quota configuration.
    """

    def __init__(self, dsn: str):
        if psycopg is None:
            raise RuntimeError("PostgresStore requires `pip install 'aasm-runtime[postgres]'`") from _IMPORT_ERROR
        self.dsn=dsn
        self._conn=psycopg.connect(dsn, autocommit=True)
        self._migrate()

    def _migrate(self):
        ddl="""
        CREATE TABLE IF NOT EXISTS aasm_runs(
            machine_id TEXT PRIMARY KEY,
            snapshot_json JSONB NOT NULL,
            state TEXT NOT NULL,
            version BIGINT NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            updated_at DOUBLE PRECISION NOT NULL
        );
        CREATE TABLE IF NOT EXISTS aasm_events(
            machine_id TEXT NOT NULL,
            sequence BIGINT NOT NULL,
            event_id TEXT NOT NULL UNIQUE,
            event_json JSONB NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            PRIMARY KEY(machine_id,sequence),
            FOREIGN KEY(machine_id) REFERENCES aasm_runs(machine_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS aasm_checkpoints(
            checkpoint_id TEXT PRIMARY KEY,
            machine_id TEXT NOT NULL,
            snapshot_json JSONB NOT NULL,
            reason TEXT NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            FOREIGN KEY(machine_id) REFERENCES aasm_runs(machine_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS aasm_effects(
            effect_id TEXT PRIMARY KEY,
            machine_id TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            status TEXT NOT NULL,
            effect_json JSONB NOT NULL,
            created_at DOUBLE PRECISION NOT NULL,
            updated_at DOUBLE PRECISION NOT NULL,
            UNIQUE(machine_id,idempotency_key),
            FOREIGN KEY(machine_id) REFERENCES aasm_runs(machine_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS aasm_task_claims(
            machine_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            lease_id TEXT NOT NULL,
            worker_id TEXT NOT NULL,
            expires_at DOUBLE PRECISION NOT NULL,
            resource_id TEXT,
            demand DOUBLE PRECISION NOT NULL DEFAULT 0,
            PRIMARY KEY(machine_id,task_id),
            UNIQUE(machine_id,lease_id),
            FOREIGN KEY(machine_id) REFERENCES aasm_runs(machine_id) ON DELETE CASCADE
        );
        ALTER TABLE aasm_task_claims ADD COLUMN IF NOT EXISTS resource_id TEXT;
        ALTER TABLE aasm_task_claims ADD COLUMN IF NOT EXISTS demand DOUBLE PRECISION NOT NULL DEFAULT 0;
        CREATE INDEX IF NOT EXISTS aasm_events_machine_idx ON aasm_events(machine_id,sequence);
        CREATE INDEX IF NOT EXISTS aasm_claim_expiry_idx ON aasm_task_claims(machine_id,expires_at);
        CREATE INDEX IF NOT EXISTS aasm_claim_resource_idx ON aasm_task_claims(machine_id,resource_id,expires_at);
        """
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute(ddl)

    @staticmethod
    def _j(data):
        return json.dumps(data, sort_keys=True)

    @staticmethod
    def _obj(value):
        return value if isinstance(value, dict) else json.loads(value)

    @staticmethod
    def _replace_snapshot(target: MachineSnapshot, source: MachineSnapshot):
        target.__dict__.clear()
        target.__dict__.update(deepcopy(source.__dict__))

    @staticmethod
    def _event_lock_key(machine_id: str) -> str:
        return f"event:{machine_id}"

    @staticmethod
    def _claim_lock_key(machine_id: str) -> str:
        return f"claims:{machine_id}"

    def initialize_run(self, snapshot: MachineSnapshot):
        ts=time.time()
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO aasm_runs(machine_id,snapshot_json,state,version,created_at,updated_at)
                       VALUES(%s,%s::jsonb,%s,%s,%s,%s)
                       ON CONFLICT(machine_id) DO NOTHING""",
                    (snapshot.machine_id,self._j(snapshot_to_dict(snapshot)),snapshot.state,snapshot.version,ts,ts),
                )

    def append(self, machine_id: str, event: Event, snapshot: MachineSnapshot) -> Event:
        """Append one event against database-canonical state under a machine lock."""
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (self._event_lock_key(machine_id),))
                cur.execute(
                    "SELECT event_json FROM aasm_events WHERE machine_id=%s ORDER BY sequence",
                    (machine_id,),
                )
                rows=cur.fetchall()
                existing=[event_from_dict(self._obj(row[0])) for row in rows]
                canonical=replay_events(existing) if existing else None
                event.machine_id=machine_id
                event.sequence=len(existing)+1
                if (
                    canonical is not None
                    and event.event_type == EventType.TRANSITION_COMMITTED.value
                    and event.from_state is not None
                    and canonical.state != event.from_state
                ):
                    raise ValueError(
                        f"Stale transition: event expected {event.from_state}, canonical state is {canonical.state}"
                    )
                canonical=reduce_event(canonical,event)
                cur.execute(
                    """INSERT INTO aasm_events(machine_id,sequence,event_id,event_json,created_at)
                       VALUES(%s,%s,%s,%s::jsonb,%s)""",
                    (machine_id,event.sequence,event.event_id,self._j(event_to_dict(event)),event.ts),
                )
                cur.execute(
                    """UPDATE aasm_runs
                       SET snapshot_json=%s::jsonb,state=%s,version=%s,updated_at=%s
                       WHERE machine_id=%s""",
                    (self._j(snapshot_to_dict(canonical)),canonical.state,canonical.version,time.time(),machine_id),
                )
        self._replace_snapshot(snapshot,canonical)
        return event

    def load_snapshot(self,machine_id):
        with self._conn.cursor() as cur:
            cur.execute("SELECT snapshot_json FROM aasm_runs WHERE machine_id=%s",(machine_id,))
            row=cur.fetchone()
        if row is None:
            raise KeyError(machine_id)
        return snapshot_from_dict(self._obj(row[0]))

    def load_events(self,machine_id,after_sequence=0):
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT event_json FROM aasm_events WHERE machine_id=%s AND sequence>%s ORDER BY sequence",
                (machine_id,after_sequence),
            )
            rows=cur.fetchall()
        return [event_from_dict(self._obj(r[0])) for r in rows]

    def list_unfinished(self):
        with self._conn.cursor() as cur:
            cur.execute("SELECT machine_id,snapshot_json,state FROM aasm_runs ORDER BY updated_at")
            rows=cur.fetchall()
        out=[]
        for mid,raw,state in rows:
            snap=snapshot_from_dict(self._obj(raw))
            terminals=set(snap.metadata.get("machine_definition",{}).get("terminal_states",[MachineState.COMPLETE.value,MachineState.FAIL.value]))
            if state not in terminals:
                out.append(mid)
        return out

    def save_checkpoint(self,machine_id,checkpoint):
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO aasm_checkpoints(checkpoint_id,machine_id,snapshot_json,reason,created_at)
                       VALUES(%s,%s,%s::jsonb,%s,%s)
                       ON CONFLICT(checkpoint_id) DO UPDATE
                       SET snapshot_json=excluded.snapshot_json,reason=excluded.reason""",
                    (checkpoint.checkpoint_id,machine_id,self._j(snapshot_to_dict(checkpoint.snapshot)),checkpoint.reason,time.time()),
                )

    def load_checkpoint(self,machine_id,checkpoint_id):
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT snapshot_json,reason FROM aasm_checkpoints WHERE machine_id=%s AND checkpoint_id=%s",
                (machine_id,checkpoint_id),
            )
            row=cur.fetchone()
        if row is None:
            raise KeyError(checkpoint_id)
        return Checkpoint(checkpoint_id,snapshot_from_dict(self._obj(row[0])),row[1])

    def save_effect(self,record:EffectRecord):
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO aasm_effects(effect_id,machine_id,idempotency_key,status,effect_json,created_at,updated_at)
                       VALUES(%s,%s,%s,%s,%s::jsonb,%s,%s)
                       ON CONFLICT(effect_id) DO UPDATE
                       SET status=excluded.status,effect_json=excluded.effect_json,updated_at=excluded.updated_at""",
                    (record.spec.effect_id,record.machine_id,record.spec.idempotency_key,record.status,self._j(effect_to_dict(record)),record.created_at,record.updated_at),
                )

    def load_effect(self,machine_id,effect_id):
        with self._conn.cursor() as cur:
            cur.execute("SELECT effect_json FROM aasm_effects WHERE machine_id=%s AND effect_id=%s",(machine_id,effect_id))
            row=cur.fetchone()
        if row is None:
            raise KeyError(effect_id)
        return effect_from_dict(self._obj(row[0]))

    def find_effect_by_idempotency(self,machine_id,idempotency_key):
        with self._conn.cursor() as cur:
            cur.execute("SELECT effect_json FROM aasm_effects WHERE machine_id=%s AND idempotency_key=%s",(machine_id,idempotency_key))
            row=cur.fetchone()
        return None if row is None else effect_from_dict(self._obj(row[0]))

    def list_effects(self,machine_id):
        with self._conn.cursor() as cur:
            cur.execute("SELECT effect_json FROM aasm_effects WHERE machine_id=%s ORDER BY created_at,effect_id",(machine_id,))
            rows=cur.fetchall()
        return [effect_from_dict(self._obj(r[0])) for r in rows]

    def mark_running_effects_unknown(self,machine_id):
        changed=[]
        for record in self.list_effects(machine_id):
            if record.status==EffectStatus.RUNNING.value:
                record.status=EffectStatus.UNKNOWN.value
                record.error="process ended while effect outcome was unresolved"
                record.updated_at=time.time()
                self.save_effect(record)
                changed.append(record)
        return changed

    @staticmethod
    def _check_claim_limits(active, *, worker_id, resource_id, demand, resource_capacity, quotas):
        if resource_id is not None and resource_capacity is not None:
            used=sum(float(row[2] or 0) for row in active if row[1] == resource_id)
            if used + demand > float(resource_capacity) + 1e-12:
                raise ValueError(f"Resource capacity exhausted: {resource_id}")
        for raw in quotas or []:
            if not raw.get("enabled",True):
                continue
            scope=raw.get("scope","machine")
            target=raw.get("target_id")
            relevant=scope=="machine" or (scope=="worker" and target==worker_id) or (scope=="resource" and target==resource_id)
            if not relevant:
                continue
            selected=[
                row for row in active
                if scope=="machine"
                or (scope=="worker" and row[0]==worker_id)
                or (scope=="resource" and row[1]==resource_id)
            ]
            max_leases=raw.get("max_active_leases")
            if max_leases is not None and len(selected) >= int(max_leases):
                raise ValueError(f"Quota exceeded: {raw.get('quota_id')}")
            max_units=raw.get("max_capacity_units")
            if max_units is not None and sum(float(row[2] or 0) for row in selected)+demand > float(max_units)+1e-12:
                raise ValueError(f"Quota exceeded: {raw.get('quota_id')}")

    @staticmethod
    def _canonical_claim_policy(snapshot: MachineSnapshot, worker_id: str, requested_resource_id: str | None, at_time: float):
        resources=snapshot.resources or {}
        worker=next((x for x in resources.get("workers",[]) if x.get("worker_id")==worker_id),None)
        if worker is None:
            raise KeyError(worker_id)
        if worker.get("status") != "ACTIVE":
            raise ValueError(f"Worker {worker_id} is not ACTIVE")
        heartbeat=float(worker.get("last_heartbeat",0) or 0)
        timeout=float(worker.get("heartbeat_timeout",60) or 60)
        if at_time > heartbeat + timeout:
            raise ValueError(f"Worker {worker_id} is stale")
        resource_id=worker.get("resource_id")
        if requested_resource_id is not None and requested_resource_id != resource_id:
            raise ValueError(
                f"Stale worker resource mapping: requested {requested_resource_id}, canonical is {resource_id}"
            )
        resource=next((x for x in resources.get("registry",[]) if x.get("resource_id")==resource_id),None)
        if resource is None:
            raise KeyError(resource_id)
        if not resource.get("enabled",True):
            raise ValueError(f"Resource {resource_id} is disabled")
        return resource_id,float(resource.get("capacity",0) or 0),deepcopy(resources.get("quotas",[]))

    def acquire_task_claim(
        self,
        machine_id,
        task_id,
        lease_id,
        worker_id,
        expires_at,
        at_time,
        *,
        resource_id=None,
        demand=0.0,
        resource_capacity=None,
        quotas=None,
    ):
        """Reserve ownership using only current canonical PostgreSQL policy.

        Caller-supplied capacity/quotas are accepted for protocol compatibility
        but never trusted when a durable machine snapshot exists.
        """
        del resource_capacity,quotas
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                # Always take locks in event -> claims order. Appends only need
                # the event lock, so capacity/quota configuration cannot change
                # while this transaction reads and applies it.
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",(self._event_lock_key(machine_id),))
                cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",(self._claim_lock_key(machine_id),))
                cur.execute("SELECT snapshot_json FROM aasm_runs WHERE machine_id=%s FOR UPDATE",(machine_id,))
                row=cur.fetchone()
                if row is None:
                    raise KeyError(machine_id)
                canonical=snapshot_from_dict(self._obj(row[0]))
                canonical_resource,canonical_capacity,canonical_quotas=self._canonical_claim_policy(
                    canonical,worker_id,resource_id,float(at_time)
                )

                cur.execute("DELETE FROM aasm_task_claims WHERE machine_id=%s AND expires_at<=%s",(machine_id,at_time))
                cur.execute("SELECT 1 FROM aasm_task_claims WHERE machine_id=%s AND task_id=%s",(machine_id,task_id))
                if cur.fetchone() is not None:
                    return False
                cur.execute(
                    """SELECT worker_id,resource_id,demand
                       FROM aasm_task_claims
                       WHERE machine_id=%s AND expires_at>%s""",
                    (machine_id,at_time),
                )
                active=cur.fetchall()
                self._check_claim_limits(
                    active,
                    worker_id=worker_id,
                    resource_id=canonical_resource,
                    demand=float(demand),
                    resource_capacity=canonical_capacity,
                    quotas=canonical_quotas,
                )
                cur.execute(
                    """INSERT INTO aasm_task_claims(machine_id,task_id,lease_id,worker_id,expires_at,resource_id,demand)
                       VALUES(%s,%s,%s,%s,%s,%s,%s)""",
                    (machine_id,task_id,lease_id,worker_id,expires_at,canonical_resource,float(demand)),
                )
                return True

    def renew_task_claim(self,machine_id,lease_id,expires_at):
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute("UPDATE aasm_task_claims SET expires_at=%s WHERE machine_id=%s AND lease_id=%s",(expires_at,machine_id,lease_id))
                return cur.rowcount==1

    def release_task_claim(self,machine_id,lease_id):
        with self._conn.transaction():
            with self._conn.cursor() as cur:
                cur.execute("DELETE FROM aasm_task_claims WHERE machine_id=%s AND lease_id=%s",(machine_id,lease_id))

    def close(self):
        self._conn.close()
