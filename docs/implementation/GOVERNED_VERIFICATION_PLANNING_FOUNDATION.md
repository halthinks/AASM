# S5.3 Governed Verification Plan and Debt Foundation

**Status:** pre-admission semantic/assurance foundation  
**Contracts:** `aasm.verification.plan.v1`, `aasm.verification.debt.v1`  
**Assurance:** `aasm.verification.planning.assurance.v1`  
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

- fidelity;
- named evidence grade;
- exact execution-environment reference;
- exact numerical-policy reference;
- exact existing resource-demand references;
- explicit soundness and completeness claim slots;
- declared formal verification strengths where applicable;
- cache/reuse eligibility;
- supporting Evidence references.

These are planning declarations. They do not execute the verifier and do not
turn a verifier claim into truth.

Soundness/completeness states are deliberately `DECLARED | EVIDENCE_BACKED |
UNKNOWN | NOT_APPLICABLE`; there is no `PROVEN` shortcut. Existing proof and
certificate systems remain authoritative for proof-grade claims.

## No hidden evidence-grade or fidelity ordering

AASM currently has no canonical universal evidence-grade ladder. S5.3 therefore
uses opaque named evidence grades and exact acceptable sets. `GRADE_Z` does not
implicitly outrank `GRADE_A` and cannot satisfy a `GRADE_A` requirement unless a
separate policy explicitly lists it as acceptable.

Likewise fidelity values are named applicability categories, not a universal
numeric order:

`EXACT | BOUNDED | APPROXIMATE | EMPIRICAL | UNKNOWN`

Formal `verification_strength` continues to use the existing AASM formal
verification vocabulary; S5.3 does not redefine or rank it.

## Verification plan

A plan is exact-revision and exact-calculus-state bound. It contains:

- one requirement for every unresolved canonical obligation that already
  requires Evidence;
- exact existing verifier capability profiles;
- zero or more compatible verifier assignments;
- producer and supporting Evidence provenance.

Assignments are proposal-only. Leaving a requirement unassigned is permitted so
planning can represent incapacity honestly. The requirement itself may not be
omitted. Unassigned requirements become visible verification debt when no
applicable Evidence already satisfies them.

## Verification debt

`project_verification_debt()` is a deterministic projection. It does not mutate
obligation status.

The projection compares:

1. the exact canonical obligation graph;
2. the exact verification plan;
3. existing Evidence records and active/invalidated status;
4. explicit revision-bound evidence-applicability assessments.

Only Evidence already attached to the canonical obligation can clear its debt.
An unattached observation or an unassessed attached observation does not become
applicable implicitly.

Debt reasons expose missing verifier coverage, absent or stale Evidence,
unassessed/indeterminate applicability, evidence type/fidelity/grade mismatch,
environment/numerical-policy mismatch, formal-strength mismatch, and terminal
unresolved obligations.

A `VERIFIED` or `COMMITTED` existing obligation leaves the projection because the
canonical lifecycle—not the debt projection—says it is satisfied.

There is deliberately no scalar debt score.

## Cross-history applicability assurance

The base debt projection consumes typed applicability assessments. The assurance
layer prevents those typed records from becoming a semantic laundering path.
Before current-world debt projection it checks:

- the referenced Evidence exists;
- the applicability `evidence_type` equals the existing Evidence `kind`;
- an `APPLICABLE` assertion carries explicit assessment Evidence;
- applicability-assessment Evidence exists and is active;
- plan, verifier-profile, environment, numerical-policy, resource-demand, and
  Evidence-backed soundness/completeness support Evidence exists and is active.

A bad or stale applicability assertion is downgraded to `INDETERMINATE`, which
leaves the verification debt visible. Stale/missing plan support fails closed and
requires replanning rather than silently trusting an obsolete assignment.

The invalidation of the *result Evidence itself* is different: it is not an input
error. It becomes `STALE_EVIDENCE` debt, preserving the distinction between a
stale result and a stale applicability assessment.

Historical audit can still use the base projection to reconstruct what was
believed at the time; the assured projection is the current-world gate.

## Authority ceiling

S5.3 grants no:

- verifier execution authority;
- FactAuthority;
- effect authority;
- resource reservation;
- obligation transition authority;
- problem mutation authority.

Cache/reuse is performance-only unless a separate existing certification path
proves semantic reuse safe. A plan never converts cached output into truth.

## Admission boundary

All S5.3 contracts remain `PRE_ADMISSION_ONLY` and absent from the active public
root. Runtime durability/admission is a separate qualification step after this
semantic and assurance foundation passes its adversarial corpus.
