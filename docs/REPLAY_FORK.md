# Historical replay and durable forks

AASM's append-only event stream can now be inspected at an exact historical boundary and used to start an alternate future.

## Replay at a sequence

```python
historical = engine.replay(at_sequence=17)
```

or:

```bash
aasm replay MACHINE_ID --db runs.db --at 17
```

The returned snapshot is reduced only from events whose machine-local sequence is less than or equal to the requested boundary. External effects are not re-executed during replay.

## Fork a run

```python
forked = engine.fork(17)
```

or:

```bash
aasm fork MACHINE_ID --db runs.db --at 17
```

A fork:

- receives a new machine ID;
- starts from the source snapshot at the selected event boundary;
- records `source_machine_id`, `source_sequence`, and `source_event_id` under `snapshot.metadata.lineage`;
- preserves the source machine definition;
- writes a `machine_forked` genesis event for the new history;
- does **not** copy or re-run the source run's external effects.

The source and fork then evolve independently.

## Why effects are not copied

An event-history fork is a reasoning/control-state operation, not permission to duplicate real-world actions. Copying a prior effect record into a new run could make an already-performed external action look pending or retryable. A fork must explicitly propose and authorize any new external effect it intends to perform.
