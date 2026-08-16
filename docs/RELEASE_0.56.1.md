# AASM 0.56.1 Development Candidate — Provenance + Governed External Reality

**Status:** UNRELEASED DEVELOPMENT TARGET  
**Active milestones:** `execution-profiles-runtime-provenance`, `authoritative-state-claims`, `external-machine-supervision`  
**Historical provenance work-package label:** 56.2  
**Physical integration programs:** PR-1 / PHY-02 and PR-2A/2B/2C / PHY-03  
**Parent published release:** v0.56.0 / Solver Outcome v2  
**Candidate adoption contract:** `aasm.adoption.v1 / 0.32.5`

This document describes the current 0.56.1 candidate scope on `main`. It is **not evidence that v0.56.1 has been published**. The latest immutable published release remains v0.56.0 until an explicit release operation passes all exact-head gates and creates the corresponding tag/assets.

The candidate now contains four additive foundations:

1. evidence-grade solver execution profiles/runtime provenance, including real-provider qualification for CaDiCaL/PySAT, OR-Tools CP-SAT, HiGHS, and CVXPY;
2. governed fact authority plus explicit `DESIRED`, `PREDICTED`, `OBSERVED`, and `AUTHORITATIVE` state claims;
3. external-machine binding and durable correlation of machine observations to existing PR-1 `OBSERVED` state claims; and
4. external-machine transition proposal and observation-backed postcondition verification over the **existing v0.54 Effect lifecycle**.

The package version remains `0.56.1`. The independent adoption contract advanced additively to `0.32.5`. Package SemVer, Git development identity, architecture milestones, and semantic contract identity remain distinct planes under [`VERSIONING.md`](VERSIONING.md).

## Candidate contracts

### Solver execution provenance

- `aasm.solver.execution-profile.v1`
- `aasm.solver.runtime-provenance.v1`
- `aasm.solver.profile-evaluation.v1`
- runtime `aasm.solver.runtime-provenance.runtime.v1`
- internal provider observation bridge `aasm.solver.execution-observation.internal.v1`

### Governed state authority — PR-1

- `aasm.fact.authority.v1`
- `aasm.state.claim.v1`
- runtime `aasm.state.authority.runtime.v1`

### External machine binding — PR-2A

- `aasm.machine.binding.v1`
- `aasm.machine.state-observation.v1`
- runtime `aasm.machine.external.runtime.v1`

### Machine transition proposal — PR-2B

- `aasm.machine.transition.v1`
- runtime `aasm.machine.transition.runtime.v1`

### Postcondition verification — PR-2C

- `aasm.machine.postcondition-verification.v1`
- runtime `aasm.machine.postcondition-verification.runtime.v1`

Contract identity is independent from package SemVer. These contracts can be qualified without allocating another package number.

## PR-1 — Governed State Authority

AASM distinguishes four state-claim kinds:

```text
DESIRED
    intent / target only

PREDICTED
    model or simulation expectation only

OBSERVED
    empirical/source Evidence only

AUTHORITATIVE
    explicitly admitted fact under matching FactAuthority
```

A `FactAuthority` binds an exact workspace, scope, subject, state namespace, authority principal, validity interval, and optional problem/external revision. An `AUTHORITATIVE` claim requires a durable source claim and an active matching `FactAuthority`.

The state-authority firewall guarantees:

```text
observation existence != authority
observation agreement != authority
prediction != observation
desired state != observed state
FactAuthority != effect authority
StateClaim != effect authority
state-claim recording != core AASM machine-state mutation
```

Dedicated qualification context:

```text
aasm/state-authority
```

## PR-2A — External Machine Binding

PR-2A lets AASM reference and correlate an authoritative external machine without copying that machine into a second truth store.

A `MachineBinding` binds workspace/scope, external machine identity, semantic subject identity, supported state namespaces, typed OBSERVER/OPERATOR capability references, exact external revision identity, and optional problem/fact-authority references.

A `MachineStateObservation` binds that machine reference to an already-durable PR-1 `StateClaim` whose kind is exactly `OBSERVED`.

The capability references describe semantic interfaces. They **do not grant authority**.

PR-2A guarantees:

```text
MachineBinding != external state copy
MachineBinding != FactAuthority
MachineBinding != effect authority
observer capability reference != observation authority
operator capability reference != actuator authority
MachineStateObservation != FactAuthority
MachineStateObservation requires existing OBSERVED StateClaim
machine binding/observation != core AASM machine-state mutation
```

PR-2A performs no effect dispatch and invokes no executor.

Dedicated qualification context:

```text
aasm/external-machine
```

## PR-2B — Machine Transition Proposal over the Existing Effect Plane

PR-2B does **not** create another dispatcher, effect store, ownership model, or transition lifecycle.

A `MachineTransitionIntent` requires:

- an existing durable `MachineBinding`;
- exact external revision agreement;
- exact durable `AUTHORITATIVE` pre-state claims;
- exact durable `DESIRED` target-state claims;
- target namespaces covered by the authoritative pre-state;
- separate scoped `machine.transition.propose` authority; and
- deterministic operation/payload identity.

The runtime lowers the transition proposal into the existing v0.54 effect path:

```text
MachineTransitionIntent
        |
        v
existing EffectSpec
        |
        v
existing propose_effect()
        |
        v
existing EffectIntent / PROPOSED
```

PR-2B intentionally does **not** perform:

```text
authorize_effect
execute_effect
effect ownership creation
reconciliation
postcondition verification
```

Those remain the authority of the existing effect subsystem. Transition reporting derives status from the existing `EffectRecord`; there is no parallel transition status table.

The transition proposal itself grants no effect authority.

Dedicated qualification context:

```text
aasm/machine-transition
```

## PR-2C — Command Success Is Not Achieved State

PR-2C closes the external-reality truth gap:

> **An existing effect reaching `SUCCEEDED` does not prove that the requested external state was achieved.**

Postcondition verification consumes already-governed records:

```text
PR-2B MachineTransitionIntent
        +
existing v0.54 EffectRecord / execution_id
        +
PR-2A MachineStateObservation
        +
PR-1 AUTHORITATIVE StateClaim
```

The existing effect must be `SUCCEEDED`. `UNKNOWN` remains blocked behind the existing effect reconciliation path. Failed, cancelled, proposed, authorized, or running effects cannot support an achievement verdict.

### Execution correlation

The supplied post-effect observation must satisfy:

```text
MachineStateObservation.correlation_id
    ==
existing EffectRecord.execution_id
```

This prevents an unrelated or old matching observation from being accepted merely because its value equals the target.

That correlation is **not** being misrepresented as full freshness or distributed-clock semantics. Those remain later work.

### Independently authoritative achieved state

The achieved-state input must already be a PR-1 `AUTHORITATIVE` claim. PR-2C cannot create a `FactAuthority` or `StateClaim`.

The authoritative claim must derive from an `OBSERVED` source claim referenced by one of the supplied PR-2A machine observations for the same binding/revision.

Therefore neither of these alone is sufficient:

```text
effect SUCCEEDED
```

or:

```text
correlated OBSERVED value
```

Achievement verification requires independent authoritative-state admission.

### Comparison semantics

This foundation deliberately supports only:

```text
EXACT_CANONICAL_VALUE_EQUALITY
```

The durable verdict is:

```text
VERIFIED
or
MISMATCH
```

A mismatch is Evidence. It does not rewrite the observed state and does not retroactively mutate the existing effect from `SUCCEEDED` to `FAILED`.

### PR-2C firewall

```text
Effect SUCCEEDED != achieved state
postcondition verification != FactAuthority creation
postcondition verification != StateClaim creation
postcondition verification != effect outcome mutation
postcondition verification != core machine-state mutation
postcondition verification != effect authority
verification Evidence != parallel truth table
verification Evidence != parallel effect lifecycle
```

Dedicated qualification context:

```text
aasm/machine-postcondition
```

The qualification suite executes the underlying effect through the genuine v0.54 resource/worker/`TaskDemand`/`TaskLease`/ownership/dispatch path. PR-2C is therefore tested after a governed external-effect attempt rather than against a fabricated terminal `EffectRecord`.

## Existing Effect Lifecycle Remains Authoritative for Execution

The complete path is:

```text
AUTHORITATIVE pre-state + DESIRED target
        |
        v
MachineTransitionIntent
        |
        v
existing EffectIntent / PROPOSED
        |
        v
existing authorize_effect()
        |
        v
existing TaskLease + execute_effect()
        |
        +-- durable dispatch request
        +-- durable ownership Evidence before executor call
        +-- SUCCEEDED / FAILED / UNKNOWN / CANCELLED
        |
        v
if UNKNOWN -> existing Effect reconciliation
        |
        v
PR-2A post-execution OBSERVED correlation
        |
        v
PR-1 AUTHORITATIVE achieved-state admission
        |
        v
PR-2C VERIFIED | MISMATCH
```

No PR-2 component introduces a second executor, dispatcher, ownership record, reconciliation plane, authority evaluator, or truth store.

## Shared durability rule

Solver profiles, provenance, fact authorities, state claims, machine bindings, observation correlations, machine transition intents, and postcondition verifications use existing AASM durability/evidence paths where appropriate. Existing effects remain governed by the existing Effect store/lifecycle.

## Claim ceilings

The 0.56.1 candidate does **not** yet claim:

- tolerance-aware or unit-aware postcondition comparison;
- measurement uncertainty envelopes;
- general observation freshness semantics;
- distributed clock-quality or causal-order semantics beyond explicit execution correlation;
- sensor calibration lifecycle or calibration compensation;
- physical identity / assembly / configuration provenance;
- safety-envelope or degraded-autonomy policy;
- bounded revocable physical effect capabilities or authority epochs;
- automatic actuation authority from a machine binding or OPERATOR capability reference;
- automatic FactAuthority or authoritative-state creation from executor success;
- reproducibility from provenance alone.

The postcondition contract explicitly records:

```text
freshness_semantics:   NOT_YET_CLAIMED_PR4
calibration_semantics: NOT_YET_CLAIMED_PR4
```

These are intentional boundaries, not missing implicit behavior.

## Release criterion

This candidate may become a published package release only through the deliberate release process defined in [`VERSIONING.md`](VERSIONING.md) and [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).

The deliberate release path requires the inherited exact-head gates plus:

```text
aasm/state-authority
aasm/external-machine
aasm/machine-transition
aasm/machine-postcondition
```

Until then:

```text
package target on main: 0.56.1
adoption contract:       aasm.adoption.v1 / 0.32.5
published release:       0.56.0
exact development state: Git SHA
```

Subsequent architecture work is tracked by named milestones rather than reserving `v0.56.2`, `v0.57`, or another package number in advance.
