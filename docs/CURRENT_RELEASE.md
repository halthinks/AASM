# AASM v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection

Contracts:

```text
aasm.memory.hierarchical.v1 / 0.1.0
aasm.memory.index.v1 / 0.1.0
aasm.reasoning.frontier.v1 / 0.1.0
aasm.context.projection.v1 / 0.1.0
```

V0.40 adds durable governed long-horizon memory on the existing AASM authority path. Canonical memory mutations are `Decision → Obligation → Evidence`; semantic memory references only V37 `AUTHORIZED` reasoning; V38 stale/refuted state suppresses semantic memory; scope and principal privacy are applied before retrieval; retention is deterministic; forgetting is tombstone-based; and vector/lexical/graph/tree/rerank indexes are derived rather than memory identity.

Legacy `DPMemory` remains the algorithmic memoization cache.

Release identity:

```text
package/runtime: 0.40.0
adoption: aasm.adoption.v1 / 0.16.0
remote: aasm.remote.v1 / 0.19.0
next: v0.41.0 Domain-Neutral Autonomous Solver Loop
```
