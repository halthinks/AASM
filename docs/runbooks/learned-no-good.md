# Inspect and act on a learned no-good

## Starting state

A validated contradiction has produced an explanation and a learned constraint.

## Execute the drill

```bash
aasm runbook learned-no-good
```

## Procedure

1. Open the conflict and verify it is resolved rather than merely hidden.
2. Inspect the explanation literals and evidence IDs.
3. Inspect the projected constraint body and guard.
4. Confirm the constraint is `ACTIVE` and `HARD` only after independent certificate verification.
5. Inspect the causal backjump target.
6. Attempting the rejected model must be blocked by the kernel.

## Expected evidence

- conflict `C-retrieval-only` resolved;
- constraint `LC-retrieval-only` active and hard;
- certificate `CERT-retrieval-only` verified;
- failed model blocked;
- causal backjump target recorded.

## Failure indicators

- hard status without a certificate;
- certificate fingerprint mismatch;
- repeated activation of the blocked model;
- unrelated decisions invalidated without causal dependency.

## Reset

The runbook creates a fresh deterministic reference machine each time.
