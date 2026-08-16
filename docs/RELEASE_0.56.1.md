# AASM 0.56.1 Development Candidate — Execution Profiles + Runtime Provenance

**Status:** UNRELEASED DEVELOPMENT TARGET  
**Milestone:** `execution-profiles-runtime-provenance`  
**Historical work-package label:** 56.2  
**Parent published release:** v0.56.0 / Solver Outcome v2  
**Candidate adoption contract:** `aasm.adoption.v1 / 0.32.1`

This document describes the current 0.56.1 candidate scope on `main`. It is **not evidence that v0.56.1 has been published**. The latest immutable published release remains v0.56.0 until an explicit release operation passes all exact-head gates and creates the corresponding tag/assets.

The candidate makes solver execution configuration a governed, replayable Evidence artifact instead of an informal log field.

## Candidate contracts

- `aasm.solver.execution-profile.v1`
- `aasm.solver.runtime-provenance.v1`
- `aasm.solver.profile-evaluation.v1`
- runtime `aasm.solver.runtime-provenance.runtime.v1`
- internal provider observation bridge `aasm.solver.execution-observation.internal.v1`

Contract identity is independent from package SemVer. These contracts can be developed and qualified without allocating another future package number.

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

## Provider qualification target

The exact-head provenance gate is intended to qualify real execution observation for:

- CaDiCaL through PySAT;
- OR-Tools CP-SAT;
- HiGHS;
- CVXPY using an actually selected installed backend.

Where the current adapter cannot observe a backend thread count, provenance records the count as unknown (`null`) and records an explicit diagnostic. It must never fabricate a deterministic thread count.

## Strict profile evaluation

A strict profile can require exact effective options, worker/thread counts, provider/adapter identity, environment, formulation, problem revision, and numeric policy. Deviations are durable typed evaluation records; they do not disappear into logs.

## Durability

Profiles, provenance records, and profile evaluations use the existing AASM Evidence/event/reducer path. SQLite restart/replay is part of the candidate qualification surface. There is no provenance side table or second truth store.

## Claim ceilings

- provenance itself does **not** prove reproducibility;
- matching configuration does **not** prove matching outcome;
- provenance grants no truth or policy authority;
- CVXPY backend provenance does not claim backend-specific thread determinism when that information is unavailable;
- interrupted `solver_provenance_v2` work remains dormant, non-authoritative, and outside the candidate public contract unless separately reconciled and admitted.

## Release criterion

This candidate may become a published package release only through the deliberate release process defined in [`VERSIONING.md`](VERSIONING.md) and [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).

Until then:

```text
package target on main: 0.56.1
published release:       0.56.0
exact development state: Git SHA
```

Subsequent architecture work is tracked by named milestones rather than reserving `v0.56.2`, `v0.57`, or any other package number in advance.
