from __future__ import annotations

from copy import deepcopy
import json
import sqlite3
import threading
import time
from pathlib import Path

from ..checkpoint import Checkpoint
from ..core.reducer import reduce_event, replay_events
from ..model import Event, MachineSnapshot, MachineState
from ..effects import EffectRecord, EffectStatus
from .serde import event_from_dict, event_to_dict, snapshot_from_dict, snapshot_to_dict
from .effect_serde import effect_from_dict, effect_to_dict


class SQLiteStore:
    """Crash-safe local persistence using only Python's standard library.

    Event append and snapshot reduction occur in one `BEGIN IMMEDIATE`
    transaction. That makes the event stream authoritative even when multiple
    local processes advance the same machine concurrently.
    """

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
            columns = {row[1] for row in self._conn.execute("PRAGMA table_info(task_claims)").fetchall()}
            if "resource_id" not in columns:
                self._conn.execute("ALTER TABLE task_claims ADD COLUMN resource_id TEXT")
            if "demand" not in columns:
                self._conn.execute("ALTER TABLE task_claims ADD COLUMN demand REAL NOT NULL DEFAULT 0")

    def initialize_run(self, snapshot: MachineSnapshot) -> None:
        ts = time.time()
        payload = json.dumps(snapshot_to_dict(snapshot), sort_keys=True)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT OR IGNORE INTO runs
                   (machine_id, snapshot_json, state, version, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (snapshot.machine_id, payload, snapshot.state, snapshot.version, ts, ts),
            )

    @staticmethod
    def _replace_snapshot(target: MachineSnapshot, source: MachineSnapshot) -> None:
        target.__dict__.clear()
        target.__dict__.update(deepcopy(source.__dict__))

    def append(self, machine_id: str, event: Event, snapshot: MachineSnapshot) -> Event:
        """Append one event and materialize the canonical reduced state atomically."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                rows = self._conn.execute(
                    "SELECT event_json FROM events WHERE machine_id=? ORDER BY sequence",
                    (machine_id,),
                ).fetchall()
                existing = [event_from_dict(json.loads(row["event_json"])) for row in rows]
                canonical = replay_events(existing) if existing else None
                sequence = len(existing) + 1
                event.machine_id = machine_id
                event.sequence = sequence
                canonical = reduce_event(canonical, event)
                event_json = json.dumps(event_to_dict(event), sort_keys=True)
                snapshot_json = json.dumps(snapshot_to_dict(canonical), sort_keys=True)
                self._conn.execute(
                    "INSERT INTO events(machine_id, sequence, event_id, event_json, created_at) VALUES (?, ?, ?, ?, ?)",
                    (machine_id, sequence, event.event_id, event_json, event.ts),
                )
                self._conn.execute(
                    """UPDATE runs SET snapshot_json=?, state=?, version=?, updated_at=?
                       WHERE machine_id=?""",
                    (snapshot_json, canonical.state, canonical.version, time.time(), machine_id),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
        self._replace_snapshot(snapshot, canonical)
        return event

    def load_snapshot(self, machine_id: str) -> MachineSnapshot:
        row = self._conn.execute("SELECT snapshot_json FROM runs WHERE machine_id=?", (machine_id,)).fetchone()
        if row is None:
            raise KeyError(machine_id)
        return snapshot_from_dict(json.loads(row["snapshot_json"]))

    def load_events(self, machine_id: str, after_sequence: int = 0) -> list[Event]:
        rows = self._conn.execute(
            "SELECT event_json FROM events WHERE machine_id=? AND sequence>? ORDER BY sequence",
            (machine_id, after_sequence),
        ).fetchall()
        return [event_from_dict(json.loads(row["event_json"])) for row in rows]

    def list_unfinished(self) -> list[str]:
        rows = self._conn.execute("SELECT machine_id, snapshot_json, state FROM runs ORDER BY updated_at").fetchall()
        unfinished=[]
        for row in rows:
            snap=snapshot_from_dict(json.loads(row["snapshot_json"]))
            definition=snap.metadata.get("machine_definition", {})
            terminal=set(definition.get("terminal_states", [MachineState.COMPLETE.value, MachineState.FAIL.value]))
            if row["state"] not in terminal:
                unfinished.append(row["machine_id"])
        return unfinished

    def save_checkpoint(self, machine_id: str, checkpoint: Checkpoint) -> None:
        payload = json.dumps(snapshot_to_dict(checkpoint.snapshot), sort_keys=True)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT OR REPLACE INTO checkpoints
                   (checkpoint_id, machine_id, snapshot_json, reason, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (checkpoint.checkpoint_id, machine_id, payload, checkpoint.reason, time.time()),
            )

    def load_checkpoint(self, machine_id: str, checkpoint_id: str) -> Checkpoint:
        row = self._conn.execute(
            "SELECT snapshot_json, reason FROM checkpoints WHERE machine_id=? AND checkpoint_id=?",
            (machine_id, checkpoint_id),
        ).fetchone()
        if row is None:
            raise KeyError(checkpoint_id)
        return Checkpoint(checkpoint_id, snapshot_from_dict(json.loads(row["snapshot_json"])), row["reason"])

    def save_effect(self, record: EffectRecord) -> None:
        payload = json.dumps(effect_to_dict(record), sort_keys=True)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT INTO effects(effect_id, machine_id, idempotency_key, status, effect_json, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(effect_id) DO UPDATE SET
                     status=excluded.status, effect_json=excluded.effect_json, updated_at=excluded.updated_at""",
                (record.spec.effect_id, record.machine_id, record.spec.idempotency_key, record.status, payload, record.created_at, record.updated_at),
            )

    def load_effect(self, machine_id: str, effect_id: str) -> EffectRecord:
        row = self._conn.execute(
            "SELECT effect_json FROM effects WHERE machine_id=? AND effect_id=?",
            (machine_id, effect_id),
        ).fetchone()
        if row is None:
            raise KeyError(effect_id)
        return effect_from_dict(json.loads(row["effect_json"]))

    def find_effect_by_idempotency(self, machine_id: str, idempotency_key: str) -> EffectRecord | None:
        row = self._conn.execute(
            "SELECT effect_json FROM effects WHERE machine_id=? AND idempotency_key=?",
            (machine_id, idempotency_key),
        ).fetchone()
        return None if row is None else effect_from_dict(json.loads(row["effect_json"]))

    def list_effects(self, machine_id: str) -> list[EffectRecord]:
        rows = self._conn.execute(
            "SELECT effect_json FROM effects WHERE machine_id=? ORDER BY created_at, effect_id",
            (machine_id,),
        ).fetchall()
        return [effect_from_dict(json.loads(r["effect_json"])) for r in rows]

    def mark_running_effects_unknown(self, machine_id: str) -> list[EffectRecord]:
        changed=[]
        for record in self.list_effects(machine_id):
            if record.status == EffectStatus.RUNNING.value:
                record.status = EffectStatus.UNKNOWN.value
                record.error = "process ended while effect outcome was unresolved"
                record.updated_at = time.time()
                self.save_effect(record)
                changed.append(record)
        return changed

    @staticmethod
    def _check_claim_limits(active, *, worker_id, resource_id, demand, resource_capacity, quotas):
        if resource_id is not None and resource_capacity is not None:
            used=sum(float(row["demand"] or 0) for row in active if row["resource_id"] == resource_id)
            if used + demand > float(resource_capacity) + 1e-12:
                raise ValueError(f"Resource capacity exhausted: {resource_id}")
        for raw in quotas or []:
            if not raw.get("enabled", True):
                continue
            scope=raw.get("scope", "machine")
            target=raw.get("target_id")
            relevant = scope == "machine" or (scope == "worker" and target == worker_id) or (scope == "resource" and target == resource_id)
            if not relevant:
                continue
            selected=[
                row for row in active
                if scope == "machine"
                or (scope == "worker" and row["worker_id"] == worker_id)
                or (scope == "resource" and row["resource_id"] == resource_id)
            ]
            max_leases=raw.get("max_active_leases")
            if max_leases is not None and len(selected) >= int(max_leases):
                raise ValueError(f"Quota exceeded: {raw.get('quota_id')}")
            max_units=raw.get("max_capacity_units")
            if max_units is not None and sum(float(row["demand"] or 0) for row in selected) + demand > float(max_units) + 1e-12:
                raise ValueError(f"Quota exceeded: {raw.get('quota_id')}")

    def acquire_task_claim(
        self,
        machine_id: str,
        task_id: str,
        lease_id: str,
        worker_id: str,
        expires_at: float,
        at_time: float,
        *,
        resource_id: str | None = None,
        demand: float = 0.0,
        resource_capacity: float | None = None,
        quotas: list[dict] | None = None,
    ) -> bool:
        """Atomically reserve task ownership and enforce shared capacity/quotas."""
        with self._lock:
            self._conn.execute("BEGIN IMMEDIATE")
            try:
                self._conn.execute("DELETE FROM task_claims WHERE machine_id=? AND expires_at<=?", (machine_id, at_time))
                existing=self._conn.execute(
                    "SELECT 1 FROM task_claims WHERE machine_id=? AND task_id=?",
                    (machine_id, task_id),
                ).fetchone()
                if existing is not None:
                    self._conn.rollback()
                    return False
                active=self._conn.execute(
                    "SELECT worker_id, resource_id, demand FROM task_claims WHERE machine_id=? AND expires_at>?",
                    (machine_id, at_time),
                ).fetchall()
                self._check_claim_limits(
                    active,
                    worker_id=worker_id,
                    resource_id=resource_id,
                    demand=float(demand),
                    resource_capacity=resource_capacity,
                    quotas=quotas,
                )
                self._conn.execute(
                    """INSERT INTO task_claims(machine_id, task_id, lease_id, worker_id, expires_at, resource_id, demand)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (machine_id, task_id, lease_id, worker_id, expires_at, resource_id, float(demand)),
                )
                self._conn.commit()
                return True
            except Exception:
                self._conn.rollback()
                raise

    def renew_task_claim(self, machine_id: str, lease_id: str, expires_at: float) -> bool:
        with self._lock, self._conn:
            cur=self._conn.execute("UPDATE task_claims SET expires_at=? WHERE machine_id=? AND lease_id=?", (expires_at, machine_id, lease_id))
            return cur.rowcount == 1

    def release_task_claim(self, machine_id: str, lease_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM task_claims WHERE machine_id=? AND lease_id=?", (machine_id, lease_id))

    def close(self) -> None:
        self._conn.close()
