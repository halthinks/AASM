# AASM — Governed Physical Reality Integration Plan

**Status:** active implementation plan  
**Date:** 2026-08-16  
**Architecture basis:** `docs/architecture/GOVERNED_PHYSICAL_DISTRIBUTED_REALITY_RECONCILIATION.md`  
**Execution ledger:** `docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md`  
**Version policy:** `docs/VERSIONING.md`

---

## 1. Objective

Extend AASM from governed computational/external-tool execution into governed interaction with authoritative external and physical state **without creating a second truth system, authority system, scheduler, resource ledger, effect lifecycle, or knowledge plane**.

The implementation target is one continuous semantic path:

```text
proposal / reasoning
        ->
AASM authority + Evidence + resources
        ->
existing effect ownership boundary
        ->
external machine / simulator / device
        ->
observation
        ->
fact-authority resolution
        ->
postcondition verification / conflict
        ->
authoritative-state admission
        ->
refinement / obligations / knowledge
```

The embedded/Rust profile is a later implementation of these same semantics. It is not a separate AASM product.

---

## 2. Permanent implementation constraints

Every work package in this plan must preserve these invariants:

1. **Information does not carry authority with it.** Transport, aggregation, memory, solver agreement, sensor fusion, replay, or translation cannot elevate authority.
2. **Command is not achievement.** Successful dispatch/ACK cannot itself establish achieved external state.
3. **Observed is not authoritative by default.** Observation enters as Evidence. Authority must be explicitly resolved.
4. **Reasoning is proposal-only unless independently authorized.** No intelligence/model gains direct actuator authority.
5. **No parallel truth store.** New physical/external semantics project from existing durable Evidence/event history.
6. **No parallel effect lifecycle.** Physical/external actuation extends the existing Effect intent/ownership/result/reconciliation plane.
7. **No parallel resource system.** Physical energy, wear, occupancy, quotas, money, and compute use the existing resource governance plane with richer resource kinds.
8. **No parallel authority evaluator.** New capabilities are enforced through existing scoped authority plus narrowly defined semantic contracts.
9. **No hidden mutable configuration.** Behavior-changing configuration requires identity, revision, provenance, scope, and authority.
10. **No package version per work package.** Exact development identity is Git SHA. Contract versions evolve independently. Package SemVer changes only at a deliberate coherent release boundary.
11. **No new chronology implementation modules.** New implementation paths use stable semantic names rather than `runtime_v57.py`, `_runtime_v58_*`, etc.
12. **Dormant code is not delivered capability.** Only admitted, tested, gated runtime/public semantics count.

---

# 3. Program structure

The integration is divided into eight dependency-ordered programs.

```text
PR-1  Authoritative State Claims
  |
PR-2  External Machine Supervision + Postconditions
  |
PR-3  Physical Authority + Bounded Effect Capabilities
  |
PR-4  Temporal / Identity / Calibration / Observation Epistemics
  |
PR-5  Safety / Risk / Degraded Autonomy / Epistemic Debt
  |
PR-6  Governed Experiments + Physical Refinement
  |
PR-7  Portable Machine IR + Kernel Boundary
  |
PR-8  Rust / no_std / HIL / Physical Qualification
```

Programs may overlap in design, but a dependent runtime claim cannot advance until its prerequisite semantic boundary is landed and qualified.

---

# 4. PR-1 — Authoritative State Claims

**Purpose:** establish a generic, durable distinction between desired, predicted, observed, and authoritative state before AASM is allowed to supervise physical/external machines.

## PR-1A — Fact authority contract

Land stable semantic module:

```text
src/aasm/state_authority.py
```

Contracts:

```text
aasm.fact.authority.v1
aasm.state.claim.v1
```

`FactAuthority` must bind at minimum:

```text
authority_id
workspace_id
scope_id
subject_id
state_namespace
authority_principal_id
valid_from
expires_at
problem_revision_id (optional)
external_revision_id (optional)
metadata
fingerprint
```

Properties:

- exact workspace/scope/subject/namespace binding;
- fail closed when inactive/expired;
- registering fact authority requires existing scoped authority;
- fact authority grants no effect/actuator capability;
- cross-run transport does not inherit fact authority;
- fact authority is revision-bindable and may later gain authority epochs without changing the basic truth boundary.

## PR-1B — Four state-claim kinds

`StateClaim` kinds:

```text
DESIRED
PREDICTED
OBSERVED
AUTHORITATIVE
```

Required semantic rules:

```text
DESIRED      = intent / target only
PREDICTED    = model/simulation expectation only
OBSERVED     = empirical/source Evidence only
AUTHORITATIVE= explicit admitted fact under matching FactAuthority
```

Every claim binds:

```text
claim_id
claim_kind
workspace_id
scope_id
subject_id
state_namespace
value
source_principal_id
problem_revision_id
external_revision_id
source_claim_ids
evidence_ids
metadata
fingerprint
```

Hard invariants:

- DESIRED cannot overwrite OBSERVED;
- PREDICTED cannot overwrite OBSERVED;
- OBSERVED cannot become AUTHORITATIVE merely because multiple observations agree;
- AUTHORITATIVE requires explicit fact authority and at least one durable source observation/claim;
- state claims are append-only Evidence projections;
- recording any claim does **not** mutate core AASM machine state or `active_values`;
- no claim grants effect authority;
- authority resolution is explicit and inspectable.

## PR-1C — Durable runtime projection

Land stable runtime mixin:

```text
src/aasm/state_authority_runtime.py
```

Runtime methods:

```text
state_authority_contract_report()
register_fact_authority(...)
revoke_fact_authority(...)
record_state_claim(...)
state_authority_report(...)
state_claim_report(...)
```

Durability:

```text
EXISTING_AASM_EVIDENCE_EVENT_REPLAY
```

No separate SQL table or store.

Scoped authority capabilities:

```text
state.fact-authority.register
state.fact-authority.revoke
state.claim.desired
state.claim.predicted
state.claim.observed
state.claim.authoritative
```

## PR-1D — Schemas and adversarial tests

Schemas:

```text
schemas/fact-authority.schema.json
schemas/state-claim.schema.json
```

Required negative fixtures:

- unknown workspace/scope;
- unauthorized fact-authority registration;
- expired authority;
- subject/namespace mismatch;
- authoritative claim by wrong principal;
- authoritative claim with no observed source;
- cross-scope claim attempt;
- claim identity collision;
- forged fingerprint/document metadata;
- command/desired claim followed by no observation must remain non-authoritative;
- two agreeing observations without explicit authority must remain observations;
- Evidence replay must reproduce exact projection;
- state claim registration must not alter core AASM machine state.

**PR-1 completion condition:** all four state kinds exist as durable public semantics and `AUTHORITATIVE` can be reached only through explicit fact authority; no external actuation is introduced yet.

---

# 5. PR-2 — External Machine Supervision and Postconditions

**Purpose:** make AASM capable of supervising an external authoritative state machine without mirroring or inventing its truth.

## PR-2A — Machine binding

Contracts:

```text
aasm.machine.binding.v1
aasm.machine.state-observation.v1
```

A `MachineBinding` identifies:

```text
binding_id
workspace/scope
external machine identity
semantic machine/profile identity
external revision source
observer capability
executor capability
fact-authority bindings
problem revision applicability
```

AASM stores the binding and observations, not a competing authoritative copy of the external machine.

## PR-2B — Transition attempt over existing Effect plane

Contract:

```text
aasm.machine.transition.v1
```

A transition attempt binds:

```text
expected pre-state claim/revision
requested target state / postconditions
EffectIntent / effect_id
executor capability
resource reservations
problem revision
external revision
```

Do not create a second dispatcher.

## PR-2C — Postcondition verifier

Add generic postcondition verification:

```text
DISPATCH_SUCCEEDED
    !=
POSTCONDITION_VERIFIED
```

Postcondition verification must require:

- correlated observation Evidence;
- correct subject/namespace;
- acceptable observation freshness;
- correct revision/context;
- appropriate fact authority;
- explicit postcondition satisfaction.

Possible terminal projections:

```text
ACHIEVED_VERIFIED
ACHIEVEMENT_FAILED
ACHIEVEMENT_UNKNOWN
STALE_OBSERVATION
REVISION_CONFLICT
```

`UNKNOWN` continues to use existing effect reconciliation semantics.

## PR-2D — Out-of-band changes

A new authoritative observation that contradicts AASM's desired/predicted state is recorded as conflict/expectation-violation Evidence. It does not get overwritten by the prior command.

**PR-2 completion condition:** AASM can command an external mock machine through existing Effects and only commit achieved-state semantics after authoritative observation-backed postcondition verification.

---

# 6. PR-3 — Physical Authority and Bounded Effect Capabilities

**Purpose:** make authority to cause external effects explicit, bounded, revocable, and stale-command resistant.

Contracts:

```text
aasm.authority.domain.v1
aasm.authority.lease.v1
aasm.effect.capability.v1
aasm.authority.preemption.v1
```

## Authority domain / lease

Bind:

```text
domain
holder
workspace/scope
epoch
validity interval
permitted effect classes
preemptors
authority evidence
```

## Bounded effect capability

Bind:

```text
operation set
subject/effect domain
quantitative bounds
scope
validity interval
authority epoch
problem/external revision
delegation depth
revocation generation
```

Hard invariants:

```text
child rights ⊆ parent rights
expired => reject
stale epoch => reject
scope escape => reject
revision mismatch => reject
revoked generation => reject
resource availability != authority
fact authority != effect authority
```

Semantic preemption advances authority epoch and blocks future stale commands. Already dispatched effects move through reconciliation; history is never rewritten.

---

# 7. PR-4 — Temporal, Identity, Calibration, and Observation Epistemics

**Purpose:** prevent stale, misidentified, uncalibrated, or causally ambiguous physical Evidence from masquerading as current truth.

Contracts:

```text
aasm.event.causality.v1
aasm.observation.freshness.v1
aasm.physical.identity.v1
aasm.calibration.v1
aasm.source.trust.v1
aasm.execution.environment.v1
aasm.observation.lifecycle.v1
aasm.observation.fusion.v1
```

Required semantics include:

```text
boot epoch
monotonic local sequence
caused-by / happens-before / concurrent / order-unknown
clock quality
observation age
freshness threshold
device/component/fixture/firmware identity
calibration status and validity range
source authority declaration
SIMULATION / SIL / HIL / BENCH / PHYSICAL qualification level
RAW -> NORMALIZED -> CALIBRATED -> DERIVED -> FUSED -> VALIDATED
```

Sensor fusion is evidence transformation, never voting for authority.

---

# 8. PR-5 — Safety, Risk, Degraded Autonomy, and Epistemic Debt

**Purpose:** make physically consequential operation fail closed under uncertainty without collapsing safety semantics into resource cost.

Contracts:

```text
aasm.degraded.operation.v1
aasm.risk.envelope.v1
aasm.effect.irreversibility.v1
aasm.obligation.phase.v1
aasm.safety.envelope.v1
aasm.hybrid.state.v1
aasm.epistemic.debt.v1
aasm.manual.override.v1
```

Required principles:

- risk is not resource cost;
- hard hazards dominate optimization;
- irreversible actions can require stronger evidence/authority;
- loss of upstream intelligence never grants new authority;
- degraded modes are explicit machine states/policies;
- continuous safety envelopes compose with discrete modes but do not turn AASM into a physics solver;
- epistemic debt propagates through the existing semantic dependency graph;
- override preserves the exact waived rule, principal, reason, scope, duration, accepted risk, and resulting obligations.

---

# 9. PR-6 — Governed Experiments and Physical Refinement

**Purpose:** allow AASM to improve models/designs from physical evidence without ungoverned self-modification.

Contracts:

```text
aasm.experiment.v1
aasm.refinement.proposal.v1
aasm.refinement.loop.v1
aasm.verification.plan.v1
aasm.verification.debt.v1
```

Experiment object binds:

```text
hypothesis
controlled variables
measured variables
procedure
environment
fixture/calibration identity
expected discriminating result
evidence floor
resource demand
risk/safety constraints
problem revision
```

Experiment selection may optimize expected information gain / uncertainty reduction under hard safety/evidence/resource constraints.

The evaluator may produce Evidence and `ProblemDelta` proposals. It never applies its own delta.

Termination must include:

```text
GOAL_SATISFIED
NO_PROGRESS
OSCILLATION
RESOURCE_EXHAUSTED
INCONCLUSIVE
CONFLICT
MANUAL_HOLD
```

---

# 10. PR-7 — Portable Machine IR and Kernel Boundary

**Purpose:** freeze AASM semantics independently of Python before implementing another runtime language.

Contracts:

```text
aasm.invariant.v1
aasm.machine.ir.v1
aasm.transition.timing.v1
aasm.kernel.portable.v1
```

The portable kernel includes only:

```text
IDs
states
events
transitions
guards
authority/capability references
obligations
resource/effect references
Evidence references
conflicts
revision IDs
canonical hashes
```

It must not require:

```text
Python object identity
filesystem
SQL database
network
LLM
OS process model
dynamic allocation
host wall clock as truth
```

Build deterministic cross-runtime trace/fingerprint corpus before Rust is admitted as a conforming implementation.

---

# 11. PR-8 — Rust, `no_std`, Real-Time, and Physical Qualification

**Purpose:** implement the portable semantics on constrained targets after the semantic contract is stable.

Sequence:

```text
Rust std reference kernel
    -> differential replay vs Python
Rust no_std kernel
    -> bounded journal / queues / storage
semantic executor traits
    -> simulator / CAN / EtherCAT / GPIO / etc.
interrupt/event bridge
transition timing backend / RTIC mapping
SIM -> SIL -> HIL -> BENCH -> CONTROLLED_PHYSICAL qualification
restricted safety profile
```

Rust typestate may make statically provable illegal transitions unrepresentable. Empirical facts, Evidence sufficiency, resource state, and external authority remain runtime semantics.

---

# 12. Qualification strategy

Each program receives a dedicated stable qualification context when its first runtime claim lands. Do not name gates after package versions.

Suggested contexts:

```text
aasm/state-authority
aasm/external-machine
aasm/physical-authority
aasm/physical-evidence
aasm/safety-governance
aasm/refinement
aasm/portable-kernel
aasm/embedded-conformance
```

Every gate must include adversarial fixtures and replay/restart where the capability is durable.

The permanent cross-capability corpus must include at least:

```text
stale revision
stale authority epoch
expired capability
forged observation
uncalibrated measurement
simulation-as-physical laundering
sensor-consensus laundering
command-ACK-without-achievement
out-of-band physical transition
network partition
reconnect/reconciliation
resource exhaustion
irreversible action with insufficient evidence
poisoned learned knowledge
refinement oscillation
manual override without authority
```

---

# 13. Immediate builder queue

Execute in this order:

1. **PR-1A/1B foundation:** `FactAuthority`, four `StateClaim` kinds, deterministic fingerprints, schemas.
2. **PR-1C runtime:** Evidence-backed registration/revocation/claim recording through current scoped authority.
3. **PR-1D tests/gate:** adversarial tests, replay, no-machine-state-mutation assertion, stable `aasm/state-authority` workflow.
4. Update the execution ledger from `DESIGNED` to the evidence-supported state only after the exact head gate passes.
5. Begin PR-2 only after PR-1 is qualified; reuse existing Effect ownership/reconciliation instead of adding dispatch infrastructure.

---

# 14. First-slice acceptance statement

PR-1 is acceptable only when the repository can prove all of the following:

```text
A desired value is not an observed fact.
A prediction is not an observed fact.
An observation is not authoritative merely because it exists or agrees with peers.
An authoritative fact requires a matching explicit fact-authority binding.
Fact authority does not grant effect authority.
Recording state claims never silently changes AASM machine state.
All state-authority semantics replay exactly from existing durable Evidence.
```

That boundary is the prerequisite for every subsequent physical/external integration.
