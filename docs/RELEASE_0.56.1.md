# AASM 0.56.1 Development Candidate — Execution Provenance + Governed State Authority

**Status:** UNRELEASED DEVELOPMENT TARGET  
**Active milestones:** `execution-profiles-runtime-provenance`, `authoritative-state-claims`  
**Historical provenance work-package label:** 56.2  
**Physical integration program:** PR-1 / PHY-02 — Authoritative State Claims  
**Parent published release:** v0.56.0 / Solver Outcome v2  
**Candidate adoption contract:** `aasm.adoption.v1 / 0.32.2`

This document describes the current 0.56.1 candidate scope on `main`. It is **not evidence that v0.56.1 has been published**. The latest immutable published release remains v0.56.0 until an explicit release operation passes all exact-head gates and creates the corresponding tag/assets.

The candidate now contains two additive qualified capability foundations:

1. evidence-grade solver execution profiles/runtime provenance; and
2. governed fact authority plus explicit `DESIRED`, `PREDICTED`, `OBSERVED`, and `AUTHORITATIVE` state claims.

The package version remains `0.56.1`; the independent adoption contract advanced from `0.32.1` to `0.32.2` when the state-authority public surface was admitted. This is intentional under [`VERSIONING.md`](VERSIONING.md): package SemVer, Git development identity, architecture milestones, and semantic contract identity are distinct planes.

## Candidate contracts

### Solver execution provenance

- `aasm.solver.execution-profile.v1`
- `aasm.solver.runtime-provenance.v1`
- `aasm.solver.profile-evaluation.v1`
- runtime `aasm.solver.runtime-provenance.runtime.v1`
- internal provider observation bridge `aasm.solver.execution-observation.internal.v1`

### Governed state authority

- `aasm.fact.authority.v1`
- `aasm.state.claim.v1`
- runtime `aasm.state.authority.runtime.v1`

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

## Caller authority boundary for solver provenance

The caller may select a `SolverExecutionProfile`. The caller may **not** assert the effective configuration that actually ran.

For supported providers, AASM derives the execution observation from the exact durable request/result and the provider adapter configuration. The runtime API therefore has no `effective_options=` argument.

## Provider qualification target

The exact-head provenance gate qualifies real execution observation for:

- CaDiCaL through PySAT;
- OR-Tools CP-SAT;
- HiGHS;
- CVXPY using an actually selected installed backend.

Where the current adapter cannot observe a backend thread count, provenance records the count as unknown (`null`) and records an explicit diagnostic. It must never fabricate a deterministic thread count.

## Strict profile evaluation

A strict profile can require exact effective options, worker/thread counts, provider/adapter identity, environment, formulation, problem revision, and numeric policy. Deviations are durable typed evaluation records; they do not disappear into logs.

## Governed State Authority Foundation

The state-authority foundation establishes the truth boundary required before AASM can safely supervise authoritative external or physical machines.

AASM now distinguishes four state-claim kinds:

```text
DESIRED
    intent / target only

PREDICTED
    model or simulation expectation only

OBSERVED
    empirical/source Evidence only

AUTHORITATIVE
    explicitly admitted fact under matching FactAuthority
```

A `FactAuthority` binds an exact workspace, scope, subject, state namespace, authority principal, validity interval, and optional problem/external revision. An `AUTHORITATIVE` state claim is admitted only when:

- its source principal is the acting principal;
- at least one durable source claim is `OBSERVED`;
- source claim context matches workspace/scope/subject/namespace;
- bound revisions are compatible; and
- an active, unrevoked matching `FactAuthority` exists.

The foundation deliberately does **not** yet dispatch external-machine effects or verify postconditions. Those are PR-2 / PHY-03 work.

### State-authority firewall

The active contracts explicitly guarantee:

```text
observation existence != authority
observation agreement != authority
prediction != observation
desired state != observed state
FactAuthority != effect authority
StateClaim != effect authority
state-claim recording != core AASM machine-state mutation
```

Two agreeing observations cannot vote themselves into authority. Fact authority cannot grant actuator rights. State claims are stored through existing Evidence/event/replay semantics; there is no parallel truth table.

### State-authority durability and enforcement

The runtime uses:

- existing AASM scoped authority for fact-authority registration/revocation and claim admission;
- existing AASM Evidence/event/reducer durability;
- append-only revocation Evidence;
- deterministic claim/authority fingerprints;
- SQLite restart/replay qualification;
- adversarial fixtures for authority absence, expiry, revocation, source-principal impersonation, namespace/revision laundering, and observation-consensus laundering.

Dedicated exact-head qualification context:

```text
aasm/state-authority
```

The cumulative `aasm/v56` gate also checks the state-authority firewall so the capability cannot become detached from the active public runtime.

## Shared durability rule

Solver profiles, runtime provenance, fact authorities, revocations, and state claims all use existing AASM Evidence/event/reducer paths. There is no provenance side table, no physical truth side table, and no alternate authority evaluator.

## Claim ceilings

### Provenance

- provenance itself does **not** prove reproducibility;
- matching configuration does **not** prove matching outcome;
- provenance grants no truth or policy authority;
- CVXPY backend provenance does not claim backend-specific thread determinism when that information is unavailable;
- interrupted `solver_provenance_v2` work remains dormant, non-authoritative, and outside the candidate public contract unless separately reconciled and admitted.

### State authority

- `DESIRED` is not evidence that the target was achieved;
- `PREDICTED` is not empirical observation;
- `OBSERVED` is not automatically authoritative;
- multiple agreeing observations do not gain authority by aggregation;
- `AUTHORITATIVE` is only an admitted state fact within the exact `FactAuthority` scope/revision binding;
- fact authority grants no execution/effect authority;
- the state-authority foundation does not yet prove external command achievement, postconditions, calibration validity, causal freshness, or physical-device identity.

Those stronger semantics belong to later integration programs and must be separately qualified.

## Release criterion

This candidate may become a published package release only through the deliberate release process defined in [`VERSIONING.md`](VERSIONING.md) and [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).

The deliberate release path now requires both the existing provenance/cumulative gates and the `aasm/state-authority` gate on the exact release SHA.

Until then:

```text
package target on main: 0.56.1
adoption contract:       aasm.adoption.v1 / 0.32.2
published release:       0.56.0
exact development state: Git SHA
```

Subsequent architecture work is tracked by named milestones rather than reserving `v0.56.2`, `v0.57`, or any other package number in advance.
