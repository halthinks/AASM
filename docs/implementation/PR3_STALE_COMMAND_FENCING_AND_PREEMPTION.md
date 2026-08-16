# PR-3E/F/G — Stale Command Fencing and Semantic Preemption

**Program:** `physical-authority-capabilities` / PHY-01  
**Package target:** 0.56.1  
**Prerequisites:** PR-3A/3B authority domains/leases and PR-3C/3D bounded effect capabilities  
**Status:** implementation/qualification candidate; no public-admission or parent-GATED claim in this document

## Purpose

PR-3E/F/G closes two physical-control authority gaps before the Effect subsystem may consume bounded capabilities:

1. a command must be fenced against stale capability, stale lease, stale authority epoch, stale revocation generation, scope/revision escape, operation escape, and numeric-bound escape **at the time the capability is used**; and
2. an authorized safety/preemption principal must be able to terminate the current authority lease using the same canonical lease-revocation representation already consumed by AASM.

Neither function authorizes or dispatches an Effect.

## `aasm.effect.capability-use.v1`

`EffectCapabilityUse` binds the proposed point-in-time use to:

```text
capability_id + fingerprint
authority_lease_id + fingerprint
domain/workspace/scope/subject
actor principal
operation
named numeric parameters
authority epoch
current effective capability revocation generation
use time
problem/external revision
```

Validation fails closed unless all of the following remain current:

```text
capability is active
capability fingerprint matches
actor == current capability holder
lease is active
lease fingerprint matches
domain/scope/subject/revision match
authority epoch matches both capability and lease
captured capability revocation generation == current effective generation
operation is allowed
numeric parameter names exactly match the capability's current named bounds
all numeric values fall inside those closed intervals
```

A successful validation creates audit Evidence only.

```text
validation_grants_effect_authority = false
validation_is_reusable_authorization_token = false
required_recheck = PR3H_MUST_RECHECK_AT_EFFECT_AUTHORIZATION_AND_EXECUTION_BOUNDARIES
```

This is critical: a validation at time `t0` cannot be replayed as authority after revocation/preemption at `t1`.

## `aasm.authority.preemption.v1`

A preemption references the exact active lease by:

```text
lease_id
lease_fingerprint
authority_epoch
```

and records:

```text
preemptor principal
preempted holder
preempted_at
reason_code
required_next_epoch = preempted_epoch + 1
```

Preemption requires **both**:

```text
preemptor principal is listed in AuthorityDomain.preemptor_principal_ids
AND
existing scoped physical.authority.preempt authorization passes
```

The domain list is identity/policy metadata, not permission by existence.

## Canonical revocation integration

Semantic preemption does not invent another lease-state machine. After its scoped authority check, it writes the same `AUTHORITY_LEASE_REVOCATION` representation already consumed by `physical_authority_runtime`.

Consequences:

- existing `authority_lease_report(...)` becomes inactive at the preemption boundary;
- existing `effect_capability_report(...)` sees the underlying lease as inactive;
- bounded capabilities rooted in the lease become inactive without history rewrite;
- the next lease naturally requires the next monotonic domain epoch;
- no parallel authority evaluator or lease lifecycle is created.

## Crash recovery

The preemption operation creates semantic preemption Evidence and canonical lease-revocation Evidence. Those are two durable writes and are **not assumed atomic**.

`PhysicalPreemptionRecoveryGuardMixin` handles the fail-stop case where:

```text
preemption Evidence is durable
CRASH
lease-revocation Evidence is missing
```

An exact retry/resume must:

1. recognize the matching durable preemption;
2. verify the referenced lease identity/fingerprint/epoch still matches;
3. repair the missing canonical lease-revocation Evidence;
4. only then return idempotent success.

A non-identical retry fails closed.

The dedicated recovery test injects a crash at exactly this boundary and requires exact replay after repair.

## Numeric semantics ceiling

The use fence applies named scalar numeric bounds only. It still does not interpret units, dimensions, tolerances, calibration, or measurement uncertainty.

```text
numeric_units = NOT_INTERPRETED_UNTIL_QUANTITY_CONTRACT
```

## Authority and execution firewall

PR-3E/F/G preserves:

```text
use validation != effect.authorize
use validation != reusable authorization token
preemptor identity != preemption authority
preemption != new effect authority
preemption != new lease authority
resource availability != authority
Effect dispatch = NONE
machine-state mutation = NONE
parallel authority evaluator = NONE
parallel Effect lifecycle = NONE
```

## Dedicated qualification contexts

```text
aasm/physical-control-fencing
aasm/physical-preemption-recovery
```

Public admission must not occur until both dedicated contexts and the cumulative inherited matrix pass on the relevant exact head.

## PR-3H remains last

Only after PR-3A through PR-3G are qualified may PR-3H connect this model to the existing Effect plane.

PR-3H must **recheck**, not trust a previously recorded use-validation event, at the existing Effect authorization/execution boundaries:

```text
current lease
current authority epoch
current capability fingerprint
current effective revocation generation
current holder
current operation/bounds/scope/revision
```

PR-3H must reuse the existing v0.54 EffectIntent, TaskLease, resource governance, ownership, dispatch, UNKNOWN outcome, and reconciliation machinery. It must not introduce a second dispatcher or Effect lifecycle.
