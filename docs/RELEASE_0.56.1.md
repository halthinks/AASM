# AASM 0.56.1 Development Candidate — Governed External Reality + Physical Control

**Status:** UNRELEASED DEVELOPMENT TARGET  
**Package target:** `0.56.1`  
**Latest immutable published release:** `v0.56.0`  
**Active adoption contract:** `aasm.adoption.v1 / 0.32.7`  
**Active milestones:** solver provenance, authoritative state, external-machine supervision, physical authority/capability/preemption  
**PR-3 boundary:** PR-3A through PR-3G active; PR-3H Effect authorization/execution integration intentionally not yet implemented

This document describes the current development surface on `main`. It is not a published-release claim. Package SemVer remains `0.56.1`; semantic/adoption contracts advance independently under `docs/VERSIONING.md`.

## Active architecture

The current active root is a stable additive overlay over the frozen v0.56 base. It preserves one AASM truth/authority/resource/effect system while admitting the physical-control semantics that were previously only source candidates.

### PR-1 — governed state authority

Active contracts:

```text
aasm.fact.authority.v1
aasm.state.claim.v1
aasm.state.authority.runtime.v1
```

State claims remain distinct:

```text
DESIRED
PREDICTED
OBSERVED
AUTHORITATIVE
```

Observation existence or agreement does not create authority. `FactAuthority` does not create effect authority.

### PR-2 — external machine supervision

Active contracts:

```text
aasm.machine.binding.v1
aasm.machine.state-observation.v1
aasm.machine.external.runtime.v1
aasm.machine.transition.v1
aasm.machine.transition.runtime.v1
aasm.machine.postcondition-verification.v1
aasm.machine.postcondition-verification.runtime.v1
```

The existing Effect plane remains authoritative for execution:

```text
AUTHORITATIVE pre-state + DESIRED target
        -> MachineTransitionIntent
        -> existing propose_effect / EffectIntent
        -> existing authorize_effect
        -> existing TaskLease + execute_effect
        -> existing ownership / SUCCEEDED|FAILED|UNKNOWN|CANCELLED
        -> existing reconciliation if UNKNOWN
        -> correlated OBSERVED state
        -> independent AUTHORITATIVE admission
        -> VERIFIED | MISMATCH
```

`EffectStatus.SUCCEEDED` does not prove achieved external state.

### PR-3A/3B — physical authority domain + exclusive lease

Active contracts:

```text
aasm.authority.domain.v1
aasm.authority.lease.v1
aasm.physical.authority.runtime.v1
```

The runtime enforces:

```text
one non-overlapping active lease per domain
strictly monotonic authority epoch
append-only lease revocation
exact scope / subject / revision binding
lease effect classes subset of domain effect classes
preemptor reference != authority by existence
```

A valid domain or lease still does not grant existing `effect.authorize`.

### PR-3C/3D — bounded effect capability

Active contracts:

```text
aasm.effect.capability.v1
aasm.effect.capability.runtime.v1
```

`EffectCapability` binds:

```text
authority domain + lease
holder + issuer
allowed operations
named closed numeric intervals
validity interval
authority epoch
problem/external revision
remaining delegation depth
revocation generation
parent capability fingerprint/generation
```

Delegation is fail-closed non-amplifying:

```text
child operations subset parent
child bounds preserve or narrow every parent bound
child validity subset parent
scope/subject/revision/epoch exact
remaining delegation depth decreases
parent fingerprint + revocation generation captured
```

Time-correct revocation is part of the active runtime: a future revocation does not retroactively invalidate historical queries before its revocation time.

Capability existence still does not grant effect authority.

### PR-3E/F — point-in-time stale-command fencing

Active contracts:

```text
aasm.effect.capability-use.v1
aasm.physical.control-fencing.runtime.v1
```

A capability use is bound to the exact current:

```text
capability ID + fingerprint
lease ID + fingerprint
domain/workspace/scope/subject
holder/actor
operation
named numeric parameters
authority epoch
effective capability revocation generation
problem/external revision
use time
```

Validation fails closed on stale capability, stale lease, stale epoch/generation, holder mismatch, scope/revision escape, operation escape, or numeric-bound escape.

A successful use-validation record is audit Evidence only:

```text
validation_grants_effect_authority = false
validation_is_reusable_authorization_token = false
required_recheck = PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES
```

### PR-3G — semantic preemption + crash repair

Active contracts/runtime:

```text
aasm.authority.preemption.v1
aasm.physical.control-fencing.runtime.v1
PhysicalPreemptionRecoveryGuardMixin
```

Preemption requires both:

```text
principal is listed by AuthorityDomain as a preemptor
AND
existing scoped physical.authority.preempt authorization succeeds
```

The preemption target is the exact active lease ID, fingerprint and authority epoch. Preemption writes semantic Evidence and the same canonical `AUTHORITY_LEASE_REVOCATION` representation already consumed by the physical-authority runtime.

Therefore:

```text
preemption -> canonical lease revocation
           -> current lease inactive
           -> capabilities rooted in it inactive
           -> next lease requires the next monotonic epoch
```

Crash recovery covers the two-write boundary where preemption Evidence became durable but lease-revocation Evidence did not. Exact retry repairs the missing canonical revocation; non-identical retry fails closed.

## No parallel control plane

Across PR-1 through PR-3G:

```text
scoped authority remains the permission evaluator
existing resources/workers/TaskLease remain execution-resource governance
existing EffectIntent/authorization/ownership/dispatch/reconciliation remain the Effect lifecycle
Evidence/event/reducer replay remains semantic durability
```

There is no second:

```text
authority evaluator
dispatcher
Effect ownership model
Effect lifecycle
resource ledger
external truth table
```

## PR-3H remains deliberately unimplemented

The current active surface explicitly stops before connecting bounded physical capability semantics to existing Effect authorization/execution.

PR-3H must recheck at the actual existing Effect boundaries:

```text
current AuthorityLease identity/fingerprint/epoch
current EffectCapability identity/fingerprint
current effective revocation generation
current holder
current operation + numeric bounds
current workspace/scope/subject
current problem/external revision
```

It must not trust an earlier capability-use validation record as a reusable bearer token.

PR-3H must reuse existing:

```text
effect.authorize
EffectIntent
TaskLease
resource governance
EffectOwnership
external dispatch
UNKNOWN handling
reconciliation
```

## Current claim ceilings

The candidate does not yet claim:

- PR-3H physical capability enforcement inside `authorize_effect` / `execute_effect`;
- quantity/unit interpretation for capability numeric bounds;
- observation freshness, clock-quality or distributed causal ordering;
- calibration lifecycle or measurement uncertainty;
- tolerance-aware postcondition verification;
- hybrid continuous/discrete safety envelopes.

These remain explicit later integration programs.

## Qualification contexts

The deliberate release path now requires the inherited gates plus:

```text
aasm/state-authority
aasm/external-machine
aasm/machine-transition
aasm/machine-postcondition
aasm/physical-authority
aasm/effect-capability
aasm/physical-control-fencing
aasm/physical-preemption-recovery
```

Until a deliberate package release occurs:

```text
package target on main: 0.56.1
active adoption contract: aasm.adoption.v1 / 0.32.7
published release: v0.56.0
exact development identity: Git SHA
```
