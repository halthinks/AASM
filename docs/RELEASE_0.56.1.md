# AASM 0.56.1 Development Candidate — Provenance + Governed External Reality + Physical Authority

**Status:** UNRELEASED DEVELOPMENT TARGET  
**Active milestones:** `execution-profiles-runtime-provenance`, `authoritative-state-claims`, `external-machine-supervision`, `physical-authority-capabilities`  
**Historical provenance work-package label:** 56.2  
**Physical integration programs:** PR-1 / PHY-02, PR-2 / PHY-03, and PR-3A/3B / PHY-01 foundation  
**Parent published release:** v0.56.0 / Solver Outcome v2  
**Candidate adoption contract:** `aasm.adoption.v1 / 0.32.6`

This document describes the current 0.56.1 candidate scope on `main`. It is **not evidence that v0.56.1 has been published**. The latest immutable published release remains v0.56.0 until an explicit release operation passes all exact-head gates and creates the corresponding tag/assets.

The package version remains `0.56.1`. Semantic/adoption contracts continue to advance independently; the active adoption contract is now `0.32.6`.

## Qualified candidate foundations

The active candidate now contains:

1. truthful Solver Outcome v2 compatibility plus evidence-grade execution provenance;
2. PR-1 governed fact authority and explicit `DESIRED`, `PREDICTED`, `OBSERVED`, `AUTHORITATIVE` state claims;
3. PR-2 external-machine binding, revision-safe transition proposals over the existing Effect plane, and observation-backed postcondition verification; and
4. **PR-3A/3B physical-authority foundation:** bounded authority domains plus exclusive, revocable, epoch-bearing authority leases.

## Active semantic contracts

### PR-1 — authoritative state

- `aasm.fact.authority.v1`
- `aasm.state.claim.v1`
- `aasm.state.authority.runtime.v1`

### PR-2 — external reality supervision

- `aasm.machine.binding.v1`
- `aasm.machine.state-observation.v1`
- `aasm.machine.external.runtime.v1`
- `aasm.machine.transition.v1`
- `aasm.machine.transition.runtime.v1`
- `aasm.machine.postcondition-verification.v1`
- `aasm.machine.postcondition-verification.runtime.v1`

### PR-3A/3B — physical authority foundation

- `aasm.authority.domain.v1`
- `aasm.authority.lease.v1`
- `aasm.physical.authority.runtime.v1`

## PR-1 — Governed State Authority

AASM distinguishes:

```text
DESIRED       intent / target only
PREDICTED     model or simulation expectation only
OBSERVED      empirical/source Evidence only
AUTHORITATIVE explicitly admitted fact under matching FactAuthority
```

Observation existence, observation agreement, prediction, or desired state do not create authority. `FactAuthority` does not create effect authority. Recording a state claim does not mutate AASM's core machine state.

Qualification context:

```text
aasm/state-authority
```

## PR-2 — External Machine Supervision

PR-2 supervises an external authoritative state machine without copying its truth into a second AASM state table.

The governed path is:

```text
AUTHORITATIVE pre-state + DESIRED target
        |
        v
MachineTransitionIntent
        |
        v
existing propose_effect() / EffectIntent
        |
        v
existing authorize_effect()
        |
        v
existing TaskLease + execute_effect()
        |
        +-- durable dispatch request
        +-- durable ownership Evidence
        +-- SUCCEEDED / FAILED / UNKNOWN / CANCELLED
        |
        v
if UNKNOWN -> existing Effect reconciliation
        |
        v
correlated post-effect OBSERVED state
        |
        v
independent PR-1 AUTHORITATIVE admission
        |
        v
PR-2C VERIFIED | MISMATCH
```

The key invariant remains:

> **`EffectStatus.SUCCEEDED` does not prove that the desired physical/external state was achieved.**

Postcondition observations must correlate to the exact existing `EffectRecord.execution_id`, and achieved state must already be an independently governed `AUTHORITATIVE` claim derived from a supplied correlated observation.

The current comparison is exact canonical equality only. Freshness, calibration, tolerance, uncertainty, and distributed-clock semantics remain outside PR-2.

Qualification contexts:

```text
aasm/external-machine
aasm/machine-transition
aasm/machine-postcondition
```

## PR-3A — Authority Domain

`AuthorityDomain` creates a stable semantic namespace for bounded physical/effect authority. It binds:

```text
workspace
scope
domain name
subject
permitted effect classes
preemptor principal references
problem revision
external revision
```

An authority domain is **not** an authority grant. Its existence does not permit any effect and does not bypass AASM scoped authority.

Domain invariants include:

```text
domain existence != effect authority
resource availability != authority
FactAuthority != effect authority
preemptor reference != preemption authority
parallel authority evaluator = NONE
parallel effect lifecycle = NONE
```

## PR-3B — Exclusive Revocable Authority Lease

`AuthorityLease` binds:

```text
domain
workspace/scope
holder principal
issuer principal
authority epoch
valid_from / expires_at
permitted effect classes
problem/external revision
revocation generation
```

The foundation enforces:

```text
lease effect classes ⊆ domain effect classes
one non-overlapping effective lease interval per domain
next lease epoch = prior maximum epoch + 1
holder/issuer must be known principals
actor granting lease == issuer
bound revision identity must match domain
revocation is append-only
revocation closes the effective lease interval
revocation does not rewrite effect history
```

Most importantly:

> **A valid `AuthorityLease` still does not grant existing `effect.authorize`.**

The adversarial suite proves this directly: a lease holder without the separate existing scoped `effect.authorize` permission is denied by the existing Effect authorization boundary.

This is deliberate. PR-3A/3B establish authority structure; they do not prematurely connect that structure to actuation.

Qualification context:

```text
aasm/physical-authority
```

The PR-3A/3B exact qualification head is:

```text
74d3c0b2f37e9563a8b1371836956bff35c1c360
```

On that head, all required inherited and current contexts are green, including full CI, formal assurance, cumulative v0.56, all PR-1/PR-2 gates, and `aasm/physical-authority`.

## PR-3 claim ceiling

The **whole PR-3 / PHY-01 program is not complete**. PR-3A/3B are a qualified child slice.

The candidate does **not** yet claim:

- `aasm.effect.capability.v1` bounded effect capabilities;
- operation/bound/sub-scope capability delegation;
- child-right non-amplification enforcement;
- stale capability-epoch fencing at the Effect boundary;
- revocation-generation fencing for commands;
- semantic preemption;
- safety-controller epoch advancement;
- PR-3H integration with existing `authorize_effect` / `execute_effect`;
- automatic actuation authority from `AuthorityDomain` or `AuthorityLease`;
- physical observation freshness/calibration/tolerance semantics.

The active contracts explicitly preserve these seams:

```text
bounded_effect_capability:         RESERVED_PR3C_PR3D
semantic_preemption:               RESERVED_PR3G
effect_authorization_integration:  NOT_YET_PR3H
```

## No parallel control plane

Across PR-1, PR-2, and PR-3A/3B, AASM still has exactly one authoritative permission/execution path:

- existing scoped authority evaluates permissions;
- existing resource/worker/TaskLease mechanisms govern execution resources;
- existing v0.54 EffectIntent/authorization/ownership/dispatch/reconciliation remain authoritative for effects;
- Evidence/event/reducer paths provide semantic durability and replay.

No second authority evaluator, dispatcher, ownership model, effect lifecycle, or external truth table has been introduced.

## Release criterion

The deliberate release path requires the inherited exact-head gates plus:

```text
aasm/state-authority
aasm/external-machine
aasm/machine-transition
aasm/machine-postcondition
aasm/physical-authority
```

Until a deliberate package release occurs:

```text
package target on main: 0.56.1
adoption contract:       aasm.adoption.v1 / 0.32.6
published release:       0.56.0
exact development state: Git SHA
```

The next active implementation slice is **PR-3C/3D — bounded effect capability**, followed by delegation/stale-command fencing/preemption and only then PR-3H Effect integration.
