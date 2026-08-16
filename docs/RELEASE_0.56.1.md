# AASM v0.56.1 — Execution Profiles + Runtime Provenance

**Work package:** 56.2  
**Parent release:** v0.56.0 / Solver Outcome v2  
**Adoption contract:** `aasm.adoption.v1 / 0.32.1`

v0.56.1 makes solver execution configuration a governed, replayable Evidence artifact instead of an informal log field.

## Released contracts

- `aasm.solver.execution-profile.v1`
- `aasm.solver.runtime-provenance.v1`
- `aasm.solver.profile-evaluation.v1`
- runtime `aasm.solver.runtime-provenance.runtime.v1`
- internal provider observation bridge `aasm.solver.execution-observation.internal.v1`

## What provenance records

A runtime provenance record binds the exact durable provider result and, for v0.44 optimization runs, the exact durable Solver Outcome v2. It records:

- provider ID, implementation and version;
- AASM adapter ID and version;
- exact solver command identity;
- requested options separately from effective options;
- worker count and thread count, with UNKNOWN represented explicitly rather than guessed;
- platform identity and runtime environment fingerprint;
- solver/library identity;
- build fingerprint;
- optional exact formulation ID/fingerprint;
- optional exact problem-revision ID/fingerprint;
- optional numeric/tolerance-policy ID/fingerprint;
- provider-status-map ID/fingerprint where applicable;
- dependency fingerprints and durable Evidence lineage.

## Caller authority boundary

The caller may select a `SolverExecutionProfile`. The caller may **not** assert the effective configuration that actually ran.

For supported providers, AASM derives the execution observation from the exact durable request/result and the provider adapter configuration. The runtime API therefore has no `effective_options=` argument.

## Provider qualification

The exact-head provenance gate qualifies real execution observation for:

- CaDiCaL through PySAT;
- OR-Tools CP-SAT;
- HiGHS;
- CVXPY using an actually selected installed backend.

Where the current adapter cannot observe a backend thread count, the provenance records the count as unknown (`null`) and records an explicit diagnostic. It never fabricates a deterministic thread count.

## Strict profile evaluation

A strict profile can require exact effective options, worker/thread counts, provider/adapter identity, environment, formulation, problem revision, and numeric policy. Deviations are durable typed evaluation records; they do not disappear into logs.

## Durability

Profiles, provenance records, and profile evaluations are stored through the existing AASM Evidence/event/reducer path. SQLite restart/replay is covered. There is no provenance side table or second truth store.

## Claim ceilings

- provenance itself does **not** prove reproducibility;
- matching configuration does **not** prove matching outcome;
- provenance grants no truth or policy authority;
- CVXPY backend provenance does not claim backend-specific thread determinism when that information is unavailable;
- interrupted `solver_provenance_v2` work is dormant, non-authoritative, and not exposed by the v0.56.1 public contract.

Reproducibility certification remains work package 56.3 and is targeted for v0.56.2.
