# AASM v0.31.0 — Hierarchical Decision Scopes

AASM v0.31.0 separates strategy, architecture, implementation, and workstream reasoning inside **one authoritative machine**.

## Delivered contract

```text
aasm.scopes.v1 / 0.1.0
```

The release adds a permanent root scope; generic scope kinds; explicit inheritance and override policy; scope-local Decisions, Obligations, evidence, locks, conflicts, explanations, constraints, and fairness debt; validated cross-scope dependencies; causal cross-scope backjumping; scoped restart; atomic multi-scope candidates; legacy-flat migration; Python, CLI, HTTP, inspection, and Control Center surfaces; schemas; and bounded TLA+/Promela scope models.

## Existing authority path retained

```text
public AASM operation
    → existing event creation
    → existing pure reducer
    → existing canonical snapshot
    → Memory / SQLite / PostgreSQL
```

v0.31.0 adds no alternate runtime, duplicate scheduler, private database mutation path, per-scope event store, or framework-owned machine truth.

## Compatibility identities

```text
package/runtime:       aasm-runtime 0.31.0
adoption contract:     aasm.adoption.v1 / 0.7.0
scope contract:        aasm.scopes.v1 / 0.1.0
LangGraph adapter:     aasm.langgraph.v1 / 0.1.0
adapter conformance:   aasm.adapter.conformance.v1 / 0.1.0
remote protocol:       aasm.remote.v1 / 0.19.0
```

## Next release

**v0.32.0 — Runtime/Formal Trace Conformance** will project production event histories into a versioned formal vocabulary and link violations to exact durable event IDs.
