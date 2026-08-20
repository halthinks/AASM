# S5.3 Governed Verification Plan and Debt Foundation

**Status:** pre-admission semantic/assurance/lifecycle/durable-runtime foundation  
**Contracts:** `aasm.verification.plan.v1`, `aasm.verification.debt.v1`  
**Assurance:** `aasm.verification.planning.assurance.v1`  
**Lifecycle:** `aasm.verification.plan.lifecycle.v1`  
**Runtime:** `aasm.verification.planning.runtime.v1`  
**Qualification:** `aasm/verification-planning`

## Purpose

S5.3 makes verification work explicit without creating a second obligation,
Evidence, authority, resource, or truth system.

The canonical source of verification requirements remains the existing AASM
calculus obligation graph. An unresolved obligation participates in S5.3 when
its existing `required_evidence_types` is non-empty. A verification plan must
carry that exact obligation set and exact obligation semantic fingerprints.
The planner may add fidelity, grade, environment, numerical-policy, and formal
verification-strength constraints, but it may not delete or weaken the existing
required evidence types.

## Existing verifier ABI, not a new executor

`VerifierCapabilityProfile` composes the existing `CapabilityContract` and
requires its type to be `VERIFIER`. The profile adds planning declarations:
fidelity, named evidence grade, environment, numerical policy, existing
resource-demand references, soundness/completeness claim slots, formal
verification strengths, cache/reuse eligibility, and supporting Evidence.

These are planning declarations. They do not execute the verifier and do not
turn a verifier claim into truth. There is no `PROVEN` shortcut in the claim
slot; proof/certificate authority stays in the existing AASM assurance systems.

## No hidden evidence-grade or fidelity ordering

AASM has no canonical universal evidence-grade ladder. S5.3 uses opaque named
grades and exact acceptable sets. Fidelity values are also named applicability
categories, not a universal numeric order:

`EXACT | BOUNDED | APPROXIMATE | EMPIRICAL | UNKNOWN`

Formal verification strength retains the existing AASM vocabulary.

## Planning snapshot versus current applicability

A plan is exact-revision and exact-calculus-state bound at planning time. The
whole-calculus fingerprint is immutable provenance, not a demand that state never
changes.

Verification can legitimately attach Evidence or advance obligation lifecycle.
Current applicability therefore rechecks exact obligation semantic fingerprints
and required Evidence types while allowing status/evidence attachment evolution.
A new verification obligation, obligation semantic drift, or stale plan support
requires replanning.

The original plan ID, fingerprint, and planning snapshot fingerprint are never
rewritten.

## Durable proposal/history runtime

The runtime records only two append-only Evidence record types:

- `VERIFICATION_PLAN`
- `VERIFICATION_EVIDENCE_APPLICABILITY`

There is no verification-plan table, no verifier-execution queue, and no debt
store.

A new plan must:

- exactly validate against the current calculus planning snapshot;
- bind the exact current `ProblemRevision` head;
- avoid a pending truth-maintenance boundary;
- have active plan/profile/reference/claim support Evidence.

A new applicability assessment must:

- reference a durable plan;
- remain semantically applicable to the current obligation graph;
- bind an exact plan requirement and problem revision;
- pass Evidence-kind and applicability-provenance assurance;
- use active current plan support.

Only one active applicability assessment may exist for a given
`(plan_id, obligation_id, evidence_id)` semantic key. Reassessment uses the
existing Evidence lifecycle: invalidate the old applicability Evidence, then
record the new assessment. This avoids a second mutable applicability state
machine.

## Current verification debt

`verification_debt_report(plan_id)` recomputes debt from:

- current canonical calculus obligations;
- the immutable durable plan;
- current Evidence active/invalidated state;
- active durable applicability assessments.

The report retains the original plan ID/fingerprint while recording the current
calculus-state fingerprint. If result Evidence becomes stale, debt reappears. If
applicability-assessment Evidence becomes stale, that applicability is downgraded
to `INDETERMINATE` and debt reappears. If plan/profile/reference support becomes
stale, current use fails closed and replanning is required.

A debt report is never persisted as current truth. It is a recomputable
projection only.

## Authority ceiling

S5.3 grants no verifier execution, FactAuthority, effect authority, resource
reservation, obligation transition authority, or problem mutation authority.
Recording a plan or applicability assessment leaves the calculus unchanged.

Cache/reuse is performance-only unless a separate existing certification path
proves semantic reuse safe.

## Admission boundary

S5.3 remains `PRE_ADMISSION_ONLY` and absent from the active public root until
the full foundation/assurance/lifecycle/runtime adversarial corpus qualifies.
