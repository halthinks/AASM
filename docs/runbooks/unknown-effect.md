# Reconcile an UNKNOWN external effect

## Starting state

An external effect entered `RUNNING`, the process ended, and AASM cannot know whether the external system applied it.

## Execute the drill

```bash
aasm runbook unknown-effect
```

## Procedure

1. Resume with effect recovery enabled.
2. Confirm the unresolved running attempt becomes `UNKNOWN`.
3. Do not automatically retry when `retry_on_unknown` is false.
4. Inspect the external system using its own authoritative query or idempotency key.
5. Record explicit evidence of the observed outcome.
6. Reconcile the effect as succeeded or failed.

## Expected evidence

- prior attempt identity;
- status `UNKNOWN` after recovery;
- unsafe retry blocked;
- explicit reconciliation evidence;
- terminal effect status.

## Failure indicators

- guessing success from local state;
- retrying a non-idempotent effect;
- changing `UNKNOWN` without external evidence;
- accepting a stale execution owner.

## Reset

The drill creates a new effect and machine. Preserve the old effect record for audit.
