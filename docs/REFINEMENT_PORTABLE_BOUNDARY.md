# AASM S5.7 — Portable Refinement Boundary

## Purpose

S5.7 freezes the **reference boundary** that a future portable AASM kernel must be able to carry for governed refinement. It does not implement Machine IR, a language-independent reducer, Rust execution, solver adapters, or engineering engines; those begin in S6 and later stages.

The boundary answers one narrow question:

> What must survive transport so refinement history remains semantically attributable without transporting the Python runtime or the engines that produced the work?

## Carried semantics

`aasm.refinement.portable-boundary.v1` carries only:

- workspace, scope, and problem identity;
- `ProblemRevision` IDs and semantic fingerprints;
- refinement proposal IDs;
- validation IDs;
- application IDs;
- termination IDs;
- Evidence references;
- obligation references;
- conflict/core references;
- `ProblemDelta` transition IDs/fingerprints plus base/target revision refs and transition Evidence refs.

All collections are canonicalized to deterministic reference sets. Revision and delta fingerprints remain exact SHA-256 semantic identities.

## Explicit exclusions

The transport carries no embedded:

```text
LLM
solver
CAD engine
SPICE engine
EM engine
physics engine
```

It also carries no proposed semantic payload, solver model, geometry blob, provider-specific result, executable callback, authority token, effect capability, artifact acceptance, or mutable runtime state.

`embedded_engines` is canonically empty and `authority_claim` is canonically `NONE`.

## Projection source

The boundary is derived only from the existing S5.1 durable refinement projection. It does not create a parallel store.

For the selected workspace/scope/problem, the projector:

1. requires a valid S5.1 refinement projection;
2. requires valid semantic-evolution history;
3. selects exact problem revision refs;
4. selects refinement records whose base revision and workspace/scope match;
5. preserves their durable Evidence references;
6. preserves impacted obligation, conflict, and core references;
7. projects canonical problem-transition references;
8. discards embedded proposal, tool, solver, and domain payloads.

Cross-scope proposals are not transported into the selected boundary.

## Authority ceiling

```text
fact authority                   = NONE
effect authority                 = NONE
refinement application authority = NONE
problem mutation                 = NONE
artifact acceptance              = NONE
solver execution                 = NONE
runtime admission                = PRE_ADMISSION_ONLY
public admission                 = PRE_ADMISSION_ONLY
```

The portable boundary is evidence/provenance transport, never an authorization bearer.

## S6 boundary

S5.7 intentionally stops before portable execution semantics.

S6 begins the next layer:

- invariant taxonomy;
- `aasm.machine.ir.v1`;
- explicit transition timing semantics;
- canonical language-independent serialization and hashing;
- deterministic portable reducer behavior;
- stable portable errors;
- proof-carrying configuration;
- replay fingerprints and Python-oracle differential vectors.

Therefore S5.7 closes S5 without prematurely designing the S6 machine language inside a refinement transport object.

## Qualification

The existing aggregate `aasm/refinement` gate is extended to compile and test the S5.7 boundary in the same job that qualifies the S5.1 model, durable runtime, and assurance layer. This ensures the portable projection remains subordinate to the original governed refinement semantics rather than becoming a detached transport format.
