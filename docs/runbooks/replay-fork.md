# Safely replay and fork a machine

## Starting state

A source machine has a durable event history and must be explored without modifying that source.

## Execute the drill

```bash
aasm runbook replay-fork
```

## Procedure

1. Run `check_durable_history(persist=False)` on the source.
2. Stop if the report is not `PASS`.
3. Replay the full event stream and compare its canonical hash with the persisted source.
4. Choose the exact source sequence.
5. Fork through the public `fork()` operation.
6. Verify the fork has a new machine ID and lineage naming the source sequence and event.
7. Verify the source hash is unchanged.

## Expected evidence

- source history `PASS`;
- exact source replay hash;
- fork machine ID;
- lineage source machine ID and sequence;
- unchanged source snapshot hash.

## Failure indicators

- forking a failed history;
- direct copy without lineage;
- source mutation;
- fork replay that cannot reconstruct its own state.

## Reset

Discard the fork only through normal storage lifecycle policy. Do not edit the source history.
