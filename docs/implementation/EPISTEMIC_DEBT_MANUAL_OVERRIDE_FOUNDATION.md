# S4.9 Epistemic Debt and Manual Override Foundation

**Status:** implemented as a pre-admission semantic foundation  
**Contracts:** `aasm.epistemic.debt.v1`, `aasm.manual.override.v1`, `aasm.manual.override.assessment.v1`  
**Runtime/public admission:** `PRE_ADMISSION_ONLY`

## Purpose

S4.9 makes unresolved engineering knowledge and exceptional human intervention explicit without creating a second truth, obligation, authority, risk, or waiver plane.

Epistemic debt is a deterministic projection of the existing AASM calculus obligation graph. A manual override is an immutable, scope-bound, duration-bound record that references an exact existing Rule, RiskAssessment, scoped-authority reference, evidence, and resulting existing obligations. Neither object performs an override.

## Epistemic debt

`EpistemicDebtProjection` is regenerated from the exact existing `aasm.calculus.v1` state. It preserves:

- existing `obligation_id` identity;
- the S4.7 obligation semantic fingerprint;
- the existing status machine;
- exact `REQUIRES` dependencies;
- required and attached evidence references;
- mandatory/persistent flags and scope;
- optional S4.7 phase bindings;
- exact ProblemRevision and calculus-state fingerprints.

`VERIFIED` and `COMMITTED` obligations are absent from debt. Other live states are `OUTSTANDING`; `REJECTED`, `SUPERSEDED`, and `IMPOSSIBLE` are retained as `TERMINAL_UNRESOLVED` rather than disappearing from the knowledge record.

Debt has no scalar score, forgiveness switch, resource-cost collapse, hidden registry, or independent lifecycle. Resource scarcity and objective improvement cannot erase it.

## Manual override

A `ManualOverride` records:

- principal identity;
- exact Rule revision, fingerprint, and scope selector;
- explicit reason;
- exact ProblemRevision;
- explicit logical clock and bounded integer sequence window;
- exact accepted RiskAssessment and hazard IDs;
- exact existing scoped-authority reference and evidence IDs;
- exact resulting existing obligation IDs and S4.7 semantic fingerprints;
- additional Evidence references and portable metadata.

`HARD_FLOOR` rules are unconditionally non-overridable. Other rules require their existing `RuleControlPolicy.waiver_mode` to be `EXPLICIT_AUTHORIZED`, and the supplied authority capability must exactly match the Rule policy. Accepted risk must be an exact `REQUIRES_EXPLICIT_ACCEPTANCE` assessment with no hard blocker or unresolved mitigation. Resulting obligations must already exist in the canonical calculus store and remain outstanding and nonterminal.

The assessment result `ADMISSIBLE_FOR_AUTHORIZATION_REVIEW` is deliberately not authorization. The existing authority plane must revalidate the grant at point of use, and any later effect must still traverse the existing Effect lifecycle and point-of-use authority checks.

## Claim ceiling

S4.9 performs none of the following:

- creates a second debt or obligation graph;
- mutates obligation status or evidence;
- waives, edits, deletes, or supersedes a Rule;
- grants scoped or effect authority;
- activates a current override;
- dispatches an Effect;
- deletes or rewrites history;
- treats an authority reference as authority proof;
- weakens a hard floor, evidence floor, or assurance requirement;
- hides wall-clock semantics in durable identity.

All records are immutable, revision-bound, deterministic, closed-schema, and binary-float-free. Later runtime admission must compose through the existing Rule, RiskAssessment, authority, calculus, Evidence, and Effect systems rather than bypassing them.
