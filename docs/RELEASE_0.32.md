# AASM v0.32.0 — Runtime/Formal Trace Conformance

AASM v0.32.0 adds a read-only formal trace layer over the existing authoritative durable event history.

## Contracts

```text
package/runtime:          0.32.0
adoption contract:        aasm.adoption.v1 / 0.8.0
scope contract:           aasm.scopes.v1 / 0.1.0
trace contract:           aasm.trace.v1 / 0.1.0
semantic trace contract:  aasm.trace.semantic.v1 / 0.1.0
remote protocol:          aasm.remote.v1 / 0.19.0
```

## What changed

- every source event is represented in the projection;
- exact event ID and source sequence are preserved;
- each source event receives a canonical SHA-256 digest;
- the complete ordered source trace receives a deterministic digest;
- unknown event types are explicit `UNSUPPORTED` steps rather than silently discarded;
- snapshot-only input is rejected because a snapshot cannot prove its generating transition history;
- semantic pre/post witnesses can produce exact event-linked counterexamples;
- missing semantic witnesses remain `INCONCLUSIVE` instead of being guessed into conformance;
- deterministic trace corpora bind multiple representative histories to exact fingerprints;
- bounded TLA+ and Promela models check lossless projection, ordering, and explicit unsupported handling.

## Authority boundary

```text
authoritative durable events
        ↓
read-only trace projector
        ↓
versioned abstraction
        ↓
semantic witness checker
        ↓
formal correspondence report
```

No new reducer, event store, scheduler, effect ledger, lease system, or alternate machine authority was introduced.

## Next

**v0.33.0 — Signed Provenance and Verifiable Exports** makes run evidence portable and independently checkable offline.
