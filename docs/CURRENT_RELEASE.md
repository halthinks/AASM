# AASM v0.38.0 — Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance

v0.38.0 connects v0.37 admitted reasoning to the decisions, obligations, and downstream work that depend on it.

## Contracts

```text
aasm.semantic.dependencies.v1 / 0.1.0
aasm.truth.maintenance.v1      / 0.1.0
aasm.reactive.obligation.v1    / 0.1.0
aasm.causal.decision.v1        / 0.1.0
aasm.reasoning.artifact.v1     / 0.1.0
aasm.reasoning.admission.v1    / 0.1.0
```

## Delivered

- deterministic typed semantic graph projection over the existing authoritative AASM state;
- forward impact and backward lineage queries;
- propagating-edge DAG enforcement and explicitly non-propagating descriptive cycles;
- `CausalDecisionRecord` extending the existing decision calculus with rejected alternatives, confidence, reasoning, event provenance, and reasoning-artifact provenance;
- policy/controller admission for explicit dependency edges and reactive rules;
- reactive rules derive ordinary AASM obligations from durable events and never execute handlers;
- durable plan-before-apply truth maintenance;
- affected-descendant-only stale propagation with unrelated sibling preservation;
- causal-decision invalidation and removal from active models;
- consumed work reopening as `NEEDS_REVALIDATION` through the existing obligation transition contract;
- existing lock reevaluation after truth change;
- idempotent truth-maintenance replay and crash recovery via `resume_truth_maintenance`;
- deterministic v0.40 memory/context projection inputs without implementing a second memory truth system;
- JSON schemas, CLI/inspection surfaces, executable conformance, and bounded TLC/SPIN assurance.

## Authority boundary

```text
models / workers propose
        ↓
v0.37 epistemic admission
        ↓
authorized / durable reasoning
        ↓
v0.38 dependency projection
        ↓
verifier / policy truth change
        ↓
durable TruthMaintenancePlan
        ↓
ordinary AASM state transitions
```

There is no dependency-owned database, event log, reducer, scheduler, or handler executor.

```text
package/runtime: 0.38.0
adoption:         aasm.adoption.v1 / 0.14.0
remote:           aasm.remote.v1 / 0.19.0
next:             v0.39.0 Typed Event/Transition Protocol and Capability ABI
```
