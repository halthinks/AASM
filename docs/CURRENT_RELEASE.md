# AASM v0.35.0 — Semantic Problem Model Foundations

v0.35.0 begins the Semantic Solver Program without creating another runtime.

## Contracts

```text
aasm.semantic.problem.v1 / 0.1.0
aasm.domain.v1           / 0.1.0
aasm.problem.v1          / 0.1.0
```

## Delivered

- immutable/value-style domain-neutral semantic objects;
- canonical JSON and deterministic fingerprints;
- `DomainPackage`, `ProblemDefinition`, `ProblemModel`, and `ProblemInstance`;
- entities, predicates, objectives, operators, observers, and verifiers;
- duplicate-ID and referential-integrity checks;
- decision-variable-domain checks;
- compile-time contradiction detection;
- explicit compile lifecycle and unresolved specification;
- event-sourced admission using ordinary AASM Evidence;
- replay-safe domain/problem inspection;
- Python and CLI inspection surfaces.

Malformed or contradictory semantic problems cannot be admitted. Missing capabilities remain explicit instead of being guessed away.

```text
package/runtime: 0.35.0
adoption:         aasm.adoption.v1 / 0.11.0
remote:           aasm.remote.v1 / 0.19.0
next:             v0.36.0 Semantic Compiler SDK
```
