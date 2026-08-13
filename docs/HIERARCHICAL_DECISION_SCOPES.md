# Hierarchical Decision Scopes

AASM v0.31.0 separates strategy, architecture, implementation, and workstream reasoning while retaining **one authoritative machine, one append-only event history, and one causal conflict graph**.

```text
root
└── strategy
    ├── architecture-a
    │   └── implementation-a
    └── architecture-b
        └── implementation-b
```

## Contract

```text
aasm.scopes.v1 / 0.1.0
```

The package/runtime is `0.31.0`; the adoption contract is `aasm.adoption.v1 / 0.7.0`; the remote protocol remains `aasm.remote.v1 / 0.19.0`.

## What a scope contains

Every durable Decision, Obligation, lock, conflict, explanation, and learned constraint has a scope. Evidence records its producing scope. The kernel remains domain neutral.

Built-in kinds:

```text
ROOT  STRATEGY  ARCHITECTURE  IMPLEMENTATION  WORKSTREAM  CUSTOM
```

## Register a hierarchy

```python
from aasm import AASMEngine, DecisionScope, ProblemSpec

engine = AASMEngine(ProblemSpec("scoped delivery"))
engine.register_scope(DecisionScope("strategy", "Strategy", kind="STRATEGY"))
engine.register_scope(DecisionScope(
    "architecture-api", "API architecture",
    kind="ARCHITECTURE", parent_scope_id="strategy",
))
engine.register_scope(DecisionScope(
    "implementation-api", "API implementation",
    kind="IMPLEMENTATION", parent_scope_id="architecture-api",
))
```

Every machine has a permanent `root` scope. Historical flat records remain valid as root-scoped records.

## Inheritance and override

A non-root scope is `INHERIT` or `ISOLATED`. An inheriting scope sees active ancestor decisions as effective context.

A scope is `EXPLICIT` or `DENY` for local override. Under `EXPLICIT`, replacing an inherited subject requires:

```python
scope={"scope_id": "implementation-api", "override": True}
```

The parent decision is never mutated.

## Cross-scope dependencies

Parent-to-child flow is permitted by hierarchy. Upward or sibling flow requires a durable `ScopeDependency`:

```python
from aasm import ScopeDependency

engine.register_scope_dependency(ScopeDependency(
    "SD-security-api",
    "security-workstream",
    "architecture-api",
    relation="CONSTRAINS",
    invalidation_policy="REVALIDATE",
))
```

Relations: `AUTHORIZES`, `CONSTRAINS`, `DEPENDS_ON`, `REFINES`.

Invalidation: `NONE`, `REVALIDATE`, `INVALIDATE`.

The combined hierarchy/dependency graph must be acyclic.

## Causal branch recovery

```text
strategy
├── architecture-a
│   └── implementation-a   ← contradiction
└── architecture-b
    └── implementation-b   ← preserved
```

If the explanation identifies an `architecture-a` decision as the causal pivot, AASM invalidates that branch, reopens its dependent obligations, and preserves strategy plus the complete `architecture-b` subtree.

## Scoped restart

```python
engine.restart_scope("architecture-a")
```

Scoped restart suspends speculative decisions in the selected subtree while retaining parent scopes, unrelated siblings, pinned decisions, evidence, certified hard knowledge, and append-only history.

## Atomic multi-scope candidates

A candidate spanning multiple scopes is staged, checked after all supersessions, and committed once. If it makes one of its own required parents inactive, no assignment becomes durable.

## Migration

```bash
aasm scope-migrate MACHINE_ID --store runs.db
```

Migration adds missing root metadata through the normal event/reducer path. It does not rewrite historical events or invent higher-level scopes.

## Inspection

```bash
aasm scope-report MACHINE_ID --store runs.db
aasm scope-context MACHINE_ID --store runs.db architecture-api
aasm inspect MACHINE_ID --store runs.db --surface scopes
```

```text
GET /v1/machines/{machine_id}/scopes
GET /v1/machines/{machine_id}/inspect/scopes
GET /v1/machines/{machine_id}/inspect/scope-hierarchy
```

The existing Control Center shows hierarchy, lineage, dependencies, local/effective models, object counts, fairness debt, and migration state.

## Formal boundary

The bounded TLA+ and Promela models check root/strategy authority retention, pinned-parent and certified-hard-knowledge retention, local override isolation, causal branch invalidation, sibling preservation, and scoped restart.

They are bounded abstractions. They do not prove arbitrary domain evidence, adapter code, or external services correct.
