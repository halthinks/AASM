# S5.7 Portable Refinement Boundary Qualification

**Date:** 2026-08-20  
**Qualified implementation commit:** `cb11050d76fa39ce28573a892d991f16a9617b5c`  
**Aggregate gate:** `aasm/refinement`  
**GitHub Actions run:** `32411061114`  
**Result:** `SUCCESS`  
**Contract:** `aasm.refinement.portable-boundary.v1 / 0.1.0`  
**Admission:** `PRE_ADMISSION_ONLY`

## Result

S5.7 passes as an extension of the existing governed-refinement qualification rather than as a detached transport subsystem. The aggregate job compiles and runs the S5.1 proposal/loop, durable runtime, assurance layer, and S5.7 portable-boundary checker/tests together.

## Qualified transport

The boundary carries only:

- workspace/scope/problem identity;
- `ProblemRevision` IDs and semantic fingerprints;
- proposal, validation, application, and termination IDs;
- Evidence references;
- obligation references;
- conflict/core references;
- `ProblemDelta` transition IDs/fingerprints, base/target revision refs, and transition Evidence refs.

## Explicit exclusions

The qualified transport embeds no LLM, solver, CAD, SPICE, EM, or physics engine. It does not transport proposed semantic payloads, solver payloads, CAD geometry, provider-specific execution state, executable callbacks, authority tokens, effect capabilities, or artifact-acceptance state.

`embedded_engines` is canonically empty and `authority_claim` is canonically `NONE`.

## Projection rule

The S5.7 boundary is projected from the existing valid S5.1 durable refinement projection and valid semantic-evolution history. Cross-scope proposals are excluded. Evidence, obligation, conflict/core, revision, and transition references are preserved while embedded engine/domain payloads are discarded.

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

## S6 separation

This qualification intentionally does not claim `aasm.machine.ir.v1`, portable reducer semantics, portable timing, Rust execution, or language-independent kernel conformance. Those remain S6+ work. S5.7 freezes only the refinement reference ABI needed so those later layers do not have to reconstruct refinement provenance after the fact.
