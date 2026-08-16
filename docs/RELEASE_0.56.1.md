# AASM 0.56.1 Development Candidate — Provenance + State Authority + External Machine Binding

**Status:** UNRELEASED DEVELOPMENT TARGET  
**Active milestones:** `execution-profiles-runtime-provenance`, `authoritative-state-claims`, `external-machine-supervision`  
**Historical provenance work-package label:** 56.2  
**Physical integration programs:** PR-1 / PHY-02 and PR-2A / 57.1  
**Parent published release:** v0.56.0 / Solver Outcome v2  
**Candidate adoption contract:** `aasm.adoption.v1 / 0.32.3`

This document describes the current 0.56.1 candidate scope on `main`. It is **not evidence that v0.56.1 has been published**. The latest immutable published release remains v0.56.0 until an explicit release operation passes all exact-head gates and creates the corresponding tag/assets.

The candidate now contains three additive qualified foundations:

1. evidence-grade solver execution profiles/runtime provenance;
2. governed fact authority plus explicit `DESIRED`, `PREDICTED`, `OBSERVED`, and `AUTHORITATIVE` state claims; and
3. external-machine binding and durable correlation of machine observations to existing PR-1 `OBSERVED` state claims.

The package version remains `0.56.1`. The independent adoption contract advanced from `0.32.1` to `0.32.2` for state authority and to `0.32.3` for external-machine binding. Under [`VERSIONING.md`](VERSIONING.md), package SemVer, Git development identity, architecture milestones, and semantic contract identity are distinct planes.

## Candidate contracts

### Solver execution provenance

- `aasm.solver.execution-profile.v1`
- `aasm.solver.runtime-provenance.v1`
- `aasm.solver.profile-evaluation.v1`
- runtime `aasm.solver.runtime-provenance.runtime.v1`
- internal provider observation bridge `aasm.solver.execution-observation.internal.v1`

### Governed state authority

- `aasm.fact.authority.v1`
- `aasm.state.claim.v1`
- runtime `aasm.state.authority.runtime.v1`

### External machine binding

- `aasm.machine.binding.v1`
- `aasm.machine.state-observation.v1`
- runtime `aasm.machine.external.runtime.v1`

Contract identity is independent from package SemVer. These contracts can be developed and qualified without allocating another future package number.

## What provenance records

A runtime provenance record binds the exact durable provider result and, for v0.44 optimization runs, the exact durable Solver Outcome v2. It records provider/implementation/version, adapter identity, command identity, requested and observed effective options, worker/thread counts where observable, platform/runtime fingerprints, formulation/problem-revision/numeric-policy references, provider-status-map identity, dependency fingerprints, and durable Evidence lineage.

The caller may select a `SolverExecutionProfile`. The caller may **not** assert the effective configuration that actually ran.

The exact-head provenance gate qualifies real execution observation for CaDiCaL through PySAT, OR-Tools CP-SAT, HiGHS, and CVXPY. Where a backend property cannot be observed, provenance records UNKNOWN rather than inventing a value.

## Governed State Authority Foundation — PR-1

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

A `FactAuthority` binds an exact workspace, scope, subject, state namespace, authority principal, validity interval, and optional problem/external revision. An `AUTHORITATIVE` state claim requires a durable `OBSERVED` source claim and an active matching `FactAuthority`.

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

Dedicated exact-head qualification context:

```text
aasm/state-authority
```

## External Machine Binding Foundation — PR-2A

PR-2A gives AASM a governed way to **reference and correlate** an authoritative external machine without copying that machine into a second truth store.

A `MachineBinding` binds:

- workspace and scope;
- external machine identity;
- semantic subject identity;
- supported state namespaces;
- one admitted AASM `OBSERVER` capability reference;
- one admitted AASM `OPERATOR` capability reference;
- exact external revision identity;
- optional problem-revision and fact-authority references; and
- deterministic binding identity/fingerprint.

The capability references describe the semantic interfaces associated with the machine. They **do not grant authority**.

A `MachineStateObservation` binds a machine binding to an already-durable PR-1 `StateClaim` whose kind is exactly `OBSERVED`. Runtime admission requires exact agreement on:

- workspace and scope;
- subject;
- supported state namespace;
- observer principal;
- observer capability;
- external revision; and
- problem revision when the binding declares one.

The observation envelope can also carry receipt/correlation identity. Temporal freshness and clock-quality semantics are deliberately not claimed yet; those belong to PR-4.

### PR-2A authority and truth firewall

The active contracts explicitly guarantee:

```text
MachineBinding != external state copy
MachineBinding != FactAuthority
MachineBinding != effect authority
observer capability reference != observation authority by itself
operator capability reference != actuator authority
MachineStateObservation != FactAuthority
MachineStateObservation requires existing OBSERVED StateClaim
MachineStateObservation != postcondition proof
machine binding/observation != core AASM machine-state mutation
```

The runtime uses only:

- existing AASM scoped authority;
- existing typed capability ABI;
- existing PR-1 durable state claims; and
- existing Evidence/event/replay durability.

There is no external-machine state table and no alternate machine truth store.

### No-dispatch boundary

PR-2A **does not dispatch effects and does not invoke an executor**.

The source contract checker mechanically forbids the PR-2A runtime from importing or using the Effect dispatch/ownership execution objects. The runtime contract reports:

```text
external_state_table: NONE
effect_dispatch: NONE
executor_invocation: NONE
machine_state_mutation: NONE
postcondition_verification: NOT_IMPLEMENTED_PR2A
```

This is intentional. PR-2B/PR-2C will attach requested transitions and observation-backed postcondition verification to the already-existing v0.54 Effect intent/ownership/reconciliation path. They must not create a second dispatcher.

Dedicated exact-head qualification context:

```text
aasm/external-machine
```

Adversarial qualification includes unauthorized binding, unknown/wrong capability types, unknown fact-authority references, non-`OBSERVED` claim laundering, wrong subject/namespace/revision, observer-principal impersonation, missing scoped authority, no fact/effect-authority amplification, no machine-state mutation, and SQLite replay/restart.

## Shared durability rule

Solver profiles, runtime provenance, fact authorities, state claims, machine bindings, and machine observation correlations all use existing AASM Evidence/event/reducer paths. There is no provenance side table, physical truth side table, external-machine truth side table, or alternate authority evaluator.

## Claim ceilings

### Provenance

- provenance itself does **not** prove reproducibility;
- matching configuration does **not** prove matching outcome;
- provenance grants no truth or policy authority;
- unknown backend details remain unknown;
- dormant provenance-v2 work remains non-authoritative unless separately admitted.

### State authority

- `DESIRED` is not evidence that a target was achieved;
- `PREDICTED` is not empirical observation;
- `OBSERVED` is not automatically authoritative;
- agreeing observations do not gain authority by aggregation;
- fact authority grants no execution/effect authority.

### External machine binding

- binding a machine does not prove its current state;
- an `OBSERVER` capability reference does not prove that a particular observation is correct;
- an `OPERATOR` capability reference does not grant authority to execute it;
- recording a machine observation does not establish an authoritative fact unless PR-1 authority admission separately does so;
- machine observation does not prove a command was achieved;
- PR-2A does not perform external effect dispatch;
- postcondition verification, command/ACK correlation, stale-command protection, freshness/causal ordering, calibration validity, and physical identity are not yet claimed.

Those stronger semantics belong to PR-2B/2C and later physical integration programs.

## Release criterion

This candidate may become a published package release only through the deliberate release process defined in [`VERSIONING.md`](VERSIONING.md) and [`RELEASE_PROCESS.md`](RELEASE_PROCESS.md).

The deliberate release path requires the existing exact-head gates plus:

```text
aasm/state-authority
aasm/external-machine
```

Until then:

```text
package target on main: 0.56.1
adoption contract:       aasm.adoption.v1 / 0.32.3
published release:       0.56.0
exact development state: Git SHA
```

Subsequent architecture work is tracked by named milestones rather than reserving `v0.56.2`, `v0.57`, or any other package number in advance.
