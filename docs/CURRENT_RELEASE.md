# AASM v0.56.1 — Execution Profiles + Runtime Provenance

AASM v0.56.1 is the active cumulative v0.56 public package/runtime and advances the adoption contract to `aasm.adoption.v1 / 0.32.1`.

The stable remote wire protocol remains **`aasm.remote.v1 / 0.19.0`** and is independent of the package version.

```text
active public surface: public_v56
active runtime: runtime_v56.AASMEngine
parent immutable releases: v0.56.0, v0.55.0

truthful solver outcomes (56.1):
  aasm.solver.outcome.v2
  aasm.solver.status.v2
  aasm.solver.termination.v2
  aasm.solver.provider-status-map.v1

execution provenance (56.2):
  aasm.solver.execution-profile.v1
  aasm.solver.runtime-provenance.v1
  aasm.solver.profile-evaluation.v1
  aasm.solver.runtime-provenance.runtime.v1
```

v0.56.1 preserves the complete v0.56.0 Solver Outcome v2 contract and adds work package **56.2 — Execution Profiles + Runtime Provenance**.

## Provider-observed execution configuration

A caller may choose an execution profile, but the caller may not assert the configuration that actually ran. For qualified providers AASM reconstructs the exact durable request/result and derives the effective configuration from the provider adapter.

Runtime provenance records:

- provider ID, implementation, and version;
- adapter ID and version;
- exact solver command identity;
- requested options and effective options as separate fields;
- worker and thread counts, or explicit unknown where unavailable;
- platform identity and environment fingerprint;
- library/backend identity;
- build fingerprint;
- exact model fingerprint;
- optional formulation ID/fingerprint;
- optional problem revision ID/fingerprint;
- optional numeric/tolerance-policy ID/fingerprint;
- provider-status-map ID/fingerprint where applicable;
- durable dependency/evidence lineage.

## Strict execution profiles

A strict profile may require exact effective options, worker/thread counts, provider/adapter versions, environment, formulation, problem revision, and numeric policy. Any mismatch becomes an explicit `SolverProfileEvaluation` deviation rather than disappearing into logs.

## Real provider qualification

The v0.56.1 gate exercises real provenance capture for:

- CaDiCaL through PySAT;
- OR-Tools CP-SAT;
- HiGHS;
- CVXPY with an actually selected installed backend.

If the current AASM adapter cannot observe a backend thread count, the field is `null` and the provenance contains an explicit diagnostic. AASM does not invent deterministic configuration.

## Durability and authority

Execution profiles, runtime provenance, and profile evaluations are stored as ordinary AASM Evidence through the existing event/reducer path. They survive SQLite restart/replay. There is no provenance side table or alternate truth store.

```text
profile truth authority      = NONE
provenance truth authority   = NONE
provenance policy authority  = NONE
provenance proves reproducibility = false
```

Provenance answers **what execution configuration produced this result**. It does not by itself prove that another execution will reproduce the same result. That stronger claim remains work package 56.3.

## Interrupted provenance-v2 experiment

Earlier interrupted `solver_provenance_v2` / reproducibility files remain dormant and non-authoritative. They are not exposed by the v0.56.1 public contract and do not constitute released capability. The authoritative 56.2 contracts are the roadmap-mandated v1 contracts listed above.

## Release qualification

The cumulative `aasm/v56` gate retains all v0.56.0 Solver Outcome v2 checks and adds 56.2 provenance checks. Independent `aasm/v56-provenance` qualification covers:

- source contracts and JSON schemas;
- requested/effective option separation;
- adapter/provider/platform/library identity;
- worker/thread counts;
- formulation/problem/numeric-policy binding;
- caller-override rejection;
- SQLite restart/replay;
- real CaDiCaL, OR-Tools, HiGHS, and CVXPY provider observations;
- explicit no-reproducibility/no-authority claim ceilings.

Repository release publication additionally requires ordinary CI, formal assurance, Semantic Solver RC, proof claims, solution pools, optimization, scoped authority, solver learning, v0.54/v0.55 parent compatibility, cumulative `aasm/v56`, and `aasm/v56-provenance` on the same exact SHA.

Next cumulative release: **v0.56.2 — Reproducibility Certification (56.3)**.

AASM remains an `0.x` active-development project. License: Apache-2.0 project-wide under `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
