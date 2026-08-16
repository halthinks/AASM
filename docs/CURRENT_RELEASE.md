# AASM v0.56.0 — Truthful Solver Outcomes

**Latest immutable published release:** v0.56.0  
**Current development target on `main`:** 0.56.1 — Execution Profiles + Runtime Provenance  
**Released adoption contract:** `aasm.adoption.v1 / 0.32.0`

AASM v0.56.0 is the latest published GitHub package/runtime release. Unreleased `main` may expose the 0.56.1 development target and its candidate contracts, but that does **not** make v0.56.1 a published release. Exact unreleased source identity is the Git commit SHA.

The stable remote wire protocol remains **`aasm.remote.v1 / 0.19.0`** and is independent of package SemVer.

```text
latest published package: 0.56.0
published public surface: public_v56 / 0.32.0 at the v0.56.0 tag
current development target: 0.56.1 / 0.32.1 on main
parent published release: v0.55.0
```

## Released v0.56.0 contracts

Truthful solver outcomes:

- `aasm.solver.outcome.v2`
- `aasm.solver.status.v2`
- `aasm.solver.termination.v2`
- `aasm.solver.evidence-grade.v1`
- `aasm.solver.status-v1-projection.v1`
- `aasm.solver.provider-status-map.v1`
- runtime `aasm.solver.outcome-v2.runtime.v1`

v0.56.0 preserves the complete v0.55 semantic-evolution, formulation, engineering-IR, and portable-archive foundation.

## What v0.56.0 changed

Solver outcome semantics no longer overload one status value with termination, feasibility, incumbent, proof, and provider-specific meaning.

A v0.56 outcome separates:

```text
termination cause
solution / feasibility state
incumbent presence
incumbent validation
optimality claim
bounds / relative gap
proof status
evidence grade
raw provider status + code
provider mapping identity
explicit legacy projection
```

A provider-returned assignment is not accepted as an incumbent merely because the provider returned values. AASM independently validates the assignment against the exact durable source model/request before it can support an incumbent-bearing outcome.

Provider status mapping is exact and versioned. Fuzzy or substring inference is forbidden; unknown future provider states remain unknown rather than being promoted from text fragments.

## Proof boundary

A provider `OPTIMAL` status plus an independently validated incumbent is still a provider optimality claim. It is not an independently checked proof of global optimality. The stronger proof/certificate boundary remains separate.

Likewise, a negative provider status does not silently become proof-grade infeasibility.

## Durability and authority

Solver Outcome v2 records use the existing AASM Evidence/event/reducer path. There is no parallel solver-result truth table.

```text
solver outcome normalization truth authority = NONE
provider claim != independent proof
```

## Current development after v0.56.0

`main` currently develops **Execution Profiles + Runtime Provenance** under the already-established 0.56.1 target. Candidate contracts include:

- `aasm.solver.execution-profile.v1`
- `aasm.solver.runtime-provenance.v1`
- `aasm.solver.profile-evaluation.v1`
- runtime `aasm.solver.runtime-provenance.runtime.v1`

These are development/candidate capabilities until the selected release scope passes the exact-head qualification process and an explicit release operation publishes an immutable tag and artifacts.

See [`RELEASE_0.56.1.md`](RELEASE_0.56.1.md) for the candidate scope and [`VERSIONING.md`](VERSIONING.md) for the development/release identity policy.

## Release discipline

AASM no longer treats architecture milestones as automatic package releases.

A published package requires:

```text
deliberate release intent
        +
exact main SHA
        +
all required qualification gates
        +
strict tracked-file inventory
        +
reproducible build
        +
immutable tag/assets
        +
remote asset verification
```

Normal development is identified by Git SHA and named capability milestones. Package SemVer advances only at a deliberate release boundary.

AASM remains an `0.x` active-development project. License: Apache-2.0 project-wide under `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
