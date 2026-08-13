# AASM v0.41.0 — Domain-Neutral Solver Loop and Deterministic Reuse Plane

Contracts:

```text
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.solver.loop.v1 / 0.1.0
aasm.memory.hierarchical.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.semantic.dependencies.v1 / 0.1.0
aasm.reasoning.admission.v1 / 0.1.0
```

V0.41 validates canonical prior work before expensive model, tool, solver, or capability execution. Reuse candidates reference existing Evidence, Reasoning Artifacts, or Hierarchical Memory and require durable POLICY/CONTROLLER admission. Exact reuse, idempotent receipts, explicit subsumption, and certified equivalence are supported; similarity alone is never sufficient. Scope, principal privacy, environment, dependencies, freshness, effect safety, and current source validity are checked before a `ReuseCertificate` can be committed.

The process-local hot reuse index is disposable and cannot change machine truth. V36 compiler caching, legacy `DPMemory`, V37 reasoning, V39 formal verification, V40 memory/context, and learned no-goods remain canonical in their existing subsystems.

Release identity:

```text
package/runtime: 0.41.0
adoption: aasm.adoption.v1 / 0.17.0
remote: aasm.remote.v1 / 0.19.0
next: v0.42.0 Reference Domains & Reuse/Memory/Reasoning Stress Tests
```
