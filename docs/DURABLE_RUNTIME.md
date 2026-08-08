# Durable Runtime

AASM v0.2 moves authoritative machine-state changes onto an event-sourced write path and adds a standard persistence contract.

## Write path

For state-changing operations the runtime follows:

```text
intent -> typed event -> reducer -> derived snapshot -> atomic store append
```

The model or worker does not directly own durable state. The event stream is the historical record; the snapshot is a materialized view used for fast access.

## SQLite

`SQLiteStore` uses Python's standard library, WAL journaling, foreign keys, and `synchronous=FULL`. Event append and materialized-snapshot update are performed in the same database transaction.

```python
from aasm import AASMEngine, ProblemSpec, SQLiteStore

store = SQLiteStore("runs.db")
engine = AASMEngine(ProblemSpec("durable work"), store=store)
machine_id = engine.snapshot.machine_id
```

After a process restart:

```python
store = SQLiteStore("runs.db")
engine = AASMEngine.resume(machine_id, store)
```

`AASMEngine.recover_unfinished(store)` reconstructs all non-terminal runs in a database.

## Replay

`engine.replay()` reduces the persisted event stream from `machine_created` forward. For event-sourced fields, replay must produce the same canonical snapshot as live execution.

CLI:

```bash
aasm replay MACHINE_ID --db runs.db
aasm inspect MACHINE_ID --db runs.db --events
aasm runs --db runs.db
```

## Checkpoints

Checkpoints are persisted independently from process memory. A recovered engine can restore a checkpoint created by an earlier process.

## Current boundary

v0.2's event core covers machine creation, legal transitions, snapshot metadata patches used by algorithm routing, checkpoint creation/restoration, and the existing proposal/authorization/result provenance events. Graph mutation, DP-memory mutation, external effects, and distributed leases are intentionally the next durability layers rather than being presented as complete today.

This boundary is deliberate: AASM should expand its event vocabulary only with explicit schemas and replay tests.
