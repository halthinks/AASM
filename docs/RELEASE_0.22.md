# AASM v0.22.0 — Domain-Neutral Profile Packages

AASM v0.22.0 turns the v0.21 calculus into an extensible substrate for arbitrary use cases without teaching the kernel any one domain.

## Delivered

- versioned `AASMProfile` and `AASMPackageManifest` contracts;
- immutable profile fingerprints and explicit machine bindings;
- independent decision, obligation, validation, explanation, and certification adapter protocols;
- opt-in installed-profile discovery through `aasm.profiles` entry points;
- solver-neutral `DecisionRequest`, `CandidateModel`, and deterministic candidate validation;
- generic `SemanticResultEnvelope` and durable result recording;
- static profile/package conformance plus optional adapter determinism probes;
- built-in `aasm.bare` and domain-neutral `aasm.evolve` profiles;
- a non-software field-study example;
- explicit profile-evolution proposals and versioned migrations;
- CLI commands for discovery, validation, binding, candidate validation, evolution, and semantic results;
- backward-compatible snapshot migration for profile bindings and semantic results;
- v0.22 runtime, CLI, and server wiring.

## Package evolution boundary

Packages may improve through evidence-backed, versioned revisions. They do not silently mutate. A run can adapt under a stable profile through decisions, constraints, backjumping, and restart. Changing the profile contract requires a new version, conformance, migration, and explicit activation.

## Compatibility

Existing v0.21 machines load with an empty profile binding and semantic-result ledger. No SQL migration is required because the new fields are stored in the existing snapshot JSON/JSONB. Existing machine definitions, calculus state, effects, workers, leases, mission controls, PBV profile, replay, and forks remain available.
