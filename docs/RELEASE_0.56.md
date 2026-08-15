# AASM v0.56.0 — Truthful Solver Outcomes

**Release family:** v0.56 Truthful Solver Evidence + Governed Knowledge Application  
**Work package completed by this release:** 56.1 — Normalized Solver Outcome v2  
**Parent:** v0.55.0 Governed Semantic Evolution and Engineering IR

## What shipped

- `aasm.solver.outcome.v2`
- `aasm.solver.status.v2`
- `aasm.solver.termination.v2`
- `aasm.solver.evidence-grade.v1`
- `aasm.solver.status-v1-projection.v1`
- `aasm.solver.provider-status-map.v1`
- `aasm.solver.outcome-v2.runtime.v1`
- active `public_v56` / `runtime_v56.AASMEngine`
- adoption contract `aasm.adoption.v1 / 0.32.0`

## Truthful result semantics

Solver termination, solution state, incumbent state, incumbent validation, optimality claim, proof status, evidence grade, provider raw status/code, best bound, relative gap, diagnostics, and compatibility projection are represented independently rather than compressed into one overloaded status.

Detailed v2 status is authoritative for new v0.56 features. The old status remains fingerprint-bound for compatibility and is available only through an explicit one-way projection from v2.

## Incumbent admission

Any nonempty assignment is independently validated against the exact durable `OptimizationRequest` and model before AASM accepts a `*_WITH_INCUMBENT`, `SAT`, `OPTIMAL`, or `FEASIBLE_NOT_PROVEN_OPTIMAL` result. Objective values are independently reconstructed and checked when an objective exists.

The local validation is durable Evidence. Outcome normalization itself grants no truth or policy authority.

## Provider mappings

The release qualifies exact native status identity for:

- CaDiCaL through PySAT;
- OR-Tools CP-SAT;
- HiGHS.

Fuzzy and substring-based status inference are forbidden. Unknown future provider statuses remain unknown rather than being guessed from text fragments.

## Terminal/failure classes

The release corpus covers:

- time limit;
- node limit;
- iteration limit;
- solution limit;
- memory limit;
- objective bound/target termination;
- user interrupt;
- numerical failure;
- invalid model;
- provider unavailable;
- unsupported feature;
- stale result;
- unknown future status;
- unbounded and infeasible-or-unbounded outcomes.

Limit outcomes preserve whether a validated incumbent exists.

## Claim ceilings

- provider `OPTIMAL` is not independent proof certification;
- provider negative status is not automatically proof-grade infeasibility;
- solver outcome normalization grants `truth_authority = NONE`;
- unknown provider statuses are not guessed;
- v1 compatibility projection may be lossy and says so explicitly;
- v0.56.0 does not claim runtime reproducibility certification.

## Durability

Outcome v2 is persisted as ordinary AASM Evidence derived from the exact request/result and local validation. There is no second solver-result table, scheduler, reducer, or truth store.

## Release qualification

The `aasm/v56` exact-SHA gate covers:

- source contract and JSON-schema checks;
- full Solver Outcome v2 fixture corpus;
- independent incumbent validation attacks;
- all roadmap-mandated terminal classes;
- v2→v1 projection rules;
- provider-map ambiguity/fuzzy-mapping rejection;
- real CaDiCaL/PySAT, OR-Tools CP-SAT, and HiGHS status qualification;
- active v0.56 root and frozen v0.55 parent compatibility.

The normal CI/formal/solver/proof/resource/authority gates remain mandatory for immutable release publication.

## Cumulative v0.56 family plan

The v0.56 family is cumulative so each completed work package can end in a clean immutable GitHub release:

- `v0.56.0` — 56.1 Solver Outcome v2;
- `v0.56.1` — 56.2 Execution Profiles + Runtime Provenance;
- `v0.56.2` — 56.3 Reproducibility Certification;
- `v0.56.3` — 56.4 Governed Knowledge Applicability/Application;
- `v0.56.4` — 56.5 Integrated Core/Conflict Pipeline.

Each patch release must preserve all earlier v0.56 contracts and may not weaken the v0.55 parent boundary.
