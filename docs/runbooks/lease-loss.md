# Recover after lease loss

## Starting state

A worker owns an active lease but no longer heartbeats. The task itself is still required.

## Execute the drill

```bash
aasm runbook lease-loss
```

Persist the drill:

```bash
aasm runbook lease-loss --store operator-drills.db
```

## Procedure

1. Read the canonical worker and lease state.
2. Reap the stale worker only after its heartbeat deadline.
3. Confirm the old lease is `EXPIRED` or explicitly `RELEASED`.
4. Let a healthy worker claim the same task under a new lease ID.
5. Confirm the attempt counter increased.
6. Complete the recovery lease.

## Expected evidence

- stale worker ID;
- old lease status `EXPIRED`;
- new lease ID;
- incremented attempt;
- recovery lease status `COMPLETED`.

## Failure indicators

- two active leases for the same task;
- reuse of the old lease ID;
- completion accepted from a worker that lost ownership;
- task marked complete without a canonical completion event.

## Reset

The drill creates a new machine. Delete the local drill database only when its history is no longer needed.
