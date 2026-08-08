from __future__ import annotations

import json
import sqlite3
import threading
import time
from pathlib import Path

from ..checkpoint import Checkpoint
from ..model import Event, MachineSnapshot, MachineState
from .serde import event_from_dict, event_to_dict, snapshot_from_dict, snapshot_to_dict


class SQLiteStore:
    """Crash-safe local persistence using only Python's standard library.

    Event append and snapshot update occur in one SQLite transaction. WAL mode
    allows readers while a run is active and provides robust process-crash
    recovery for local AASM workflows.
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
                CREATE INDEX IF NOT EXISTS idx_events_machine ON events(machine_id, sequence);
                CREATE INDEX IF NOT EXISTS idx_runs_state ON runs(state);
                """
            )

    def initialize_run(self, snapshot: MachineSnapshot) -> None:
        now = time.time()
        payload = json.dumps(snapshot_to_dict(snapshot), sort_keys=True)
        with self._lock, self._conn:
            self._conn.execute(
                """INSERT OR IGNORE INTO runs
                   (machine_id, snapshot_json, state, version, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (snapshot.machine_id, payload, snapshot.state, snapshot.version, now, now),
            )

    def append(self, machine_id: str, event: Event, snapshot: MachineSnapshot) -> Event:
        with self._lock, self._conn:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(sequence), 0) AS seq FROM events WHERE machine_id=?",
                (machine_id,),
            ).fetchone()
            sequence = int(row["seq"]) + 1
            event.machine_id = machine_id
            event.sequence = sequence
            event_json = json.dumps(event_to_dict(event), sort_keys=True)
            snapshot_json = json.dumps(snapshot_to_dict(snapshot), sort_keys=True)
            self._conn.execute(
                "INSERT INTO events(machine_id, sequence, event_id, event_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (machine_id, sequence, event.event_id, event_json, event.ts),
            )
            self._conn.execute(
                """UPDATE runs SET snapshot_json=?, state=?, version=?, updated_at=?
                   WHERE machine_id=?""",
                (snapshot_json, snapshot.state, snapshot.version, time.time(), machine_id),
            )
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
        terminal = (MachineState.COMPLETE.value, MachineState.FAIL.value)
        rows = self._conn.execute(
            "SELECT machine_id FROM runs WHERE state NOT IN (?, ?) ORDER BY updated_at",
            terminal,
        ).fetchall()
        return [row["machine_id"] for row in rows]

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

    def close(self) -> None:
        self._conn.close()
