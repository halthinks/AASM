# AASM S5.6 — TextPCB Refinement Qualification

## Purpose

S5.6 proves that TextPCB can consume AASM's generic governed refinement architecture without creating a TextPCB-specific truth plane, authority plane, mutation path, or solver lifecycle.

The domain cycle is:

```text
DESIGN -> VERIFY -> BUILD/GENERATE -> OPERATE/OBSERVE -> LEARN -> REDESIGN
```

The governed semantic path remains the existing S5.1 path:

```text
external/domain evaluator
        |
        v
Evidence + counterexample/diagnosis
        |
        v
RefinementProposal
        |
        v
independent RefinementValidation
        |
        v
existing scoped problem.refinement.apply authority
        |
        v
existing ProblemDelta / ProblemRevision transition
        |
        v
existing truth-maintenance invalidation
        |
        v
replan / re-solve / re-verify
```

TextPCB does not receive a shortcut around any arrow in that chain.

## Qualified evaluator domains

The permanent S5.6 corpus covers:

- `DRC_ERC`
- `SPICE`
- `EM`
- `THERMAL_PDN`
- `MECHANICAL_MANUFACTURING`
- `EXTERNAL_MEASUREMENT`
- `ARTIFACT_TOOL_FEEDBACK`

The adapter is deliberately solver-neutral. A DRC engine, SPICE simulator, field solver, thermal/PDN analyzer, CAD/manufacturing checker, measurement system, or artifact/tool integration may report a result. None becomes authoritative merely because it produced output.

## TextPCB evaluator result

`TextPCBEvaluatorResult` binds every domain finding to:

- evaluator identity;
- exact workspace and scope;
- exact base `ProblemRevision` ID and fingerprint;
- `PASS | FAIL | INCONCLUSIVE` result;
- one or more existing Evidence IDs;
- optional typed portable counterexamples;
- explicit diagnoses;
- artifact references without artifact-acceptance claims;
- at most one ordinary S5.1 `RefinementProposal`.

A proposal emitted by the evaluator must preserve the evaluator result's exact workspace, scope, base revision ID, base revision fingerprint, producer identity, and Evidence lineage.

## Result semantics

`PASS` is evidence only. It cannot carry a semantic refinement proposal and cannot accept an artifact.

`FAIL` requires an explicit diagnosis or counterexample. A failure may emit an ordinary S5.1 refinement proposal, but the proposal itself has no application authority.

`INCONCLUSIVE` remains inconclusive. It may only request `REQUIRED_OBSERVATION` or `VERIFICATION_ESCALATION`; it cannot be laundered directly into a semantic correction.

## Authority ceiling

```text
evaluator output authority          = NONE
evaluator direct problem mutation   = FORBIDDEN
evaluator direct artifact acceptance= FORBIDDEN
evaluator direct effect dispatch    = FORBIDDEN
proposal application authority      = existing S5.1 scoped authority only
revision transition                 = existing semantic-evolution runtime only
safety floor                        = existing AASM safety governance only
runtime admission                   = QUALIFICATION_ONLY_NO_RUNTIME_SURFACE
public admission                    = PRE_ADMISSION_ONLY
```

The S5.6 module intentionally imports `RefinementProposal` and `refinement_contract`; it does not import the semantic-evolution mutation API and exposes no `apply_refinement` or TextPCB runtime mixin.

## Safety continuity

S5.6 is pinned to the permanent TextPCB S4 safety corpus fingerprint:

```text
e53391300409d3a18a0dfca88b97c3ba758881228e5b670aecc970b1aa66b5d4
```

The qualification gate requires both:

```text
aasm/refinement
aasm/safety-governance
```

Therefore refinement feedback cannot weaken hard rules, hazard floors, evidence floors, uncertainty handling, irreversibility assurance, degraded-operation restrictions, or controlled-waiver provenance simply because a solver fails, a provider is absent, a resource budget is exhausted, or a redesign would otherwise be attractive.

## Permanent qualification corpus

`fixtures/textpcb/s5-refinement-qualification-fixtures.json` covers positive domain bindings plus adversarial cases for:

- stale revision findings;
- evaluator self-application;
- artifact/tool success being mistaken for acceptance;
- inconclusive analysis being mistaken for safety or correctness;
- missing Evidence lineage;
- resource pressure weakening safety;
- implicit authority transfer from external tools.

The fixture suite has a deterministic corpus fingerprint and explicitly references the permanent S4 safety suite fingerprint.

## Gate

The permanent workflow `.github/workflows/textpcb-refinement.yml` publishes:

```text
aasm/textpcb-refinement
```

It runs the S5.6 checker and adversarial tests together with the S5.1 refinement foundation/runtime/assurance corpus and the permanent TextPCB S4 safety corpus. S5.6 therefore qualifies integration with the existing architecture rather than only testing an isolated adapter.
