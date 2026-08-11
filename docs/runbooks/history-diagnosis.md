# Diagnose a failed durable-history verification

## Starting state

A history check reports `FAIL`, or a replica/backup event stream disagrees with the persisted snapshot.

## Execute the drill

```bash
aasm runbook history-diagnosis
```

## Procedure

1. Stop state mutation against the suspect copy.
2. Preserve the authoritative store and exact event bytes.
3. Run the checker against a copied event stream.
4. Record the first issue code and sequence.
5. Compare with the last known-good backup, replica, or release artifact.
6. Do not rewrite events to make the report pass.
7. Verify the canonical source remains unchanged.

## Expected evidence

- copied history rejected;
- issue code `NON_CONTIGUOUS_SEQUENCE` in the drill;
- canonical history still `PASS`;
- machine identity retained in the report.

## Failure indicators

- deleting the offending event;
- renumbering authoritative history;
- accepting a persisted snapshot that replay cannot reproduce;
- continuing writes before the source of divergence is known.

## Reset

The drill corrupts only an in-memory copy. The canonical machine remains valid.
