# AASM v0.21.0 — Formal Conflict-Learning Calculus

AASM v0.21.0 integrates the AVATAR-inspired deterministic execution calculus into the production runtime.

## Delivered

- backward-compatible `MachineSnapshot.calculus` state;
- named decisions and active decision models;
- conditional persistent obligations and evidence contracts;
- explicit model-relative locks with automatic restoration;
- first-class conflicts and causal explanations;
- guarded hard/soft learned no-goods;
- deterministic graph-directed non-chronological backjumping;
- selective reuse of the existing information-change checkpoint path;
- knowledge-preserving search restart;
- bounded cross-model fairness with Planner review;
- Planner-authorized recovery under the PBV profile;
- schema and replay compatibility;
- CLI inspection and dashboard summary;
- public v0.21 runtime and server wiring.

## Compatibility

Existing machine states, declarative machine definitions, effect semantics, stores, workers, leases, PBV directives, mission controls, and remote routes remain available. Old snapshots lacking `calculus` are migrated in memory to the default v0.21 calculus state during deserialization.

The new calculus state is persisted inside the existing snapshot JSON/JSONB, so no SQL migration is required.

## Correctness boundary

AASM validates explanation provenance and enforces deterministic projection/backjump rules. The truth of domain evidence still belongs to the test, verifier, simulator, formal proof, or human authority that produced it. Only validated/proven assumption conflicts may create hard exclusions; uncertain evidence remains soft.

## Validation

The v0.21 tests cover:

- legacy snapshot migration;
- condition and guarded no-good semantics;
- hard-versus-soft projection;
- causal backjumping with unrelated-work preservation;
- lock break and obligation restoration;
- persistent-obligation fairness;
- active-model constraint invariants;
- SQLite replay and restart retention in the full repository suite.
