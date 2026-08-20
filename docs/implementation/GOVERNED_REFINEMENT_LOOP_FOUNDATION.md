# S5.1 Governed Refinement Loop — Durable Runtime Closure

**Status:** pre-admission foundation; qualified only by `aasm/refinement`  
**Contract family:** `aasm.refinement.proposal.v1`, `aasm.refinement.loop.v1`  
**Runtime assurance:** `aasm.refinement.runtime.assurance.v1`  
**Canonical mutation path:** existing `ProblemDelta -> ProblemRevision` semantic-evolution runtime

## Purpose

S5.1 closes the generic refinement cycle without creating a second truth,
authority, resource, solver, or revision system:

`solve -> verify -> diagnose -> propose -> validate applicability -> authorize -> ProblemDelta -> ProblemRevision -> invalidate affected work -> replan/re-solve/re-verify`

The evaluator/producer that discovers a defect may propose a semantic
refinement. It may not directly apply its own delta.

## Durable records

The runtime records four refinement record types as ordinary append-only AASM
Evidence:

- `REFINEMENT_PROPOSAL`
- `REFINEMENT_VALIDATION`
- `REFINEMENT_APPLICATION`
- `REFINEMENT_TERMINATION`

There is no mutable refinement side table. Current refinement state is rebuilt
from Evidence replay.

## Authority boundary

Application requires an existing scoped-authority decision for:

`problem.refinement.apply`

The decision must bind the exact actor, workspace, and scope of the proposal and
must be `ALLOW`. The application record is provenance only; it is not itself an
authorization token.

The actor that applies a refinement must differ from the proposal producer.
Canonical revision commit authority remains the pre-existing
`POLICY | CONTROLLER` authority boundary.

The assurance projector additionally proves that the principal named by the
refinement application is the same principal recorded as authority on the
canonical revision transition. A second scoped `ALLOW` cannot be substituted for
the authority that actually committed the transition.

## Canonical mutation and invalidation

S5.1 does not implement another problem-revision engine.

A validated and authorized application calls the existing semantic-evolution
runtime to commit the exact `ProblemDelta` and resulting `ProblemRevision`.
If the delta has truth-change roots, the existing semantic dependency
truth-maintenance runtime must complete before the refinement application can
be durably recorded.

A crash after the revision transition but before truth maintenance or the
refinement application record is recoverable: the existing transition is
reused, pending truth maintenance is resumed idempotently, and only then is the
application record written.

The assurance layer binds the recorded truth-impact Evidence id to the exact
canonical impact application. A refinement may not claim unrelated invalidation
or carry spurious truth-impact provenance.

## Validation freshness

A `VALID` refinement validation may be recorded only while its supporting
Evidence is active. More importantly, supporting Evidence must still be active
when a *new* semantic refinement is applied.

If the supporting Evidence is later invalidated, it does not rewrite history or
erase an already committed refinement application. Exact retry remains
idempotent. It does, however, prevent stale validation from authorizing another
new revision transition.

## Anti-loop behavior

The semantic application key is:

`fingerprint(base_revision_id, base_revision_fingerprint, semantic_refinement_fingerprint)`

The same semantic refinement may not be applied more than once to the same
exact base revision. Exact retry of an already recorded application is
idempotent; a conflicting repeat fails closed.

`NO_PROGRESS` and `OSCILLATION` remain explicit non-success termination reasons
and require blocking-obligation references under the base S5.1 model contract.

## History projection and assurance

`project_refinement_evidence()` reconstructs proposals, validations,
applications, terminations, and semantic application keys from durable Evidence.

`assure_refinement_projection()` adds cross-history checks against authoritative
AASM state. It verifies:

- proposal base revision identity and exact fingerprint;
- proposal dependency applicability to that durable base;
- the exact proposal and independent validation;
- the canonical semantic refinement fingerprint;
- the existing `ProblemDelta` transition;
- the exact target `ProblemRevision`;
- the durable transition Evidence id;
- the durable scoped-authority `ALLOW` decision;
- the transition authority principal and authority class;
- exact completed truth-maintenance impact provenance when truth-change roots exist;
- exact termination base/head revision fingerprints;
- the duplicate-application key.

A forged application cannot become valid merely by carrying internally
consistent refinement fields or by presenting a different authorized principal.

## Admission boundary

This work remains `PRE_ADMISSION_ONLY`.

It does not alter the active public root and does not add:

- a second revision store;
- a second authority evaluator;
- a second truth-maintenance graph;
- a second resource plane;
- direct solver mutation;
- hidden mutable refinement-loop state.

Public/runtime admission is a separate qualification decision.
