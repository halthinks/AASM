# AASM v0.31.0 — Hierarchical Decision Scopes

AASM v0.31.0 separates strategy, architecture, implementation, and workstream reasoning inside **one authoritative machine**.

## Delivered contract

```text
aasm.scopes.v1 / 0.1.0
```

The release adds:

- a permanent canonical root scope;
- generic scope kinds and lifecycle states;
- explicit inheritance and override policy;
- scope-local Decisions, Obligations, evidence, locks, conflicts, explanations, constraints, and fairness debt;
- validated cross-scope dependencies and invalidation policies;
- acyclic hierarchy plus dependency-flow validation;
- effective inherited decision context;
- evidence-flow checks;
- causal cross-scope backjumping;
- scoped restart preserving parents, siblings, evidence, and hard knowledge;
- atomic multi-scope candidate activation;
- explicit migration of historical flat records into `root` metadata;
- Python, CLI, authenticated HTTP, inspection, and Control Center surfaces;
- JSON schemas and bounded TLA+/Promela scope models.

## Causal branch recovery

```text
strategy
├── architecture-a
│   └── implementation-a   ← contradiction
└── architecture-b
    └── implementation-b   ← preserved
```

A contradiction in implementation-a may backjump to the responsible architecture-a decision. AASM invalidates that branch, reopens affected obligations, and preserves strategy plus the complete architecture-b sibling subtree.

Legacy flat histories remain compatible: a root-scoped backjump follows the original decision dependency closure rather than treating every root decision as causally related.

## Atomic candidates

A multi-scope candidate is staged and validated as a complete model. If its own supersessions make a parent inactive, activation fails without committing any assignment.

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

## Formal scope properties

The new bounded models check root/strategy retention, pinned parent retention, certified hard-knowledge retention, local override isolation, causal branch invalidation, sibling preservation, and scoped restart.

## Next release

**v0.32.0 — Runtime/Formal Trace Conformance** will project production event histories into a versioned formal vocabulary and link violations to exact durable event IDs.
