# AASM — Governed Physical and Distributed Reality Reconciliation

**Status:** canonical architecture reconciliation before implementation planning  
**Date:** 2026-08-15  
**Latest immutable public release:** `v0.56.0`  
**Current development target:** `0.56.1` on `main`; exact unreleased identity is Git SHA  
**Parent doctrine:** `GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`  
**Execution ledger:** `../implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md`  
**Version policy:** `../VERSIONING.md`

---

## 1. Purpose

This document reconciles the complete Embedded/Physical architecture exploration against the **actual current AASM repository**, rather than treating the earlier architecture papers as a greenfield design.

The original exploration produced thirty primary architecture papers and a second set of thirty consequential additions. None is discarded here. Each is classified against current code and canonical roadmap intent as one of:

- **IMPLEMENTED** — the required semantic plane exists in active AASM and is tested/gated at the claimed level;
- **PARTIAL_SAME_PLANE** — AASM already has the correct underlying authority/truth/resource/effect/revision plane, but the proposed higher-level semantic contract is still missing;
- **DESIGNED_CANONICAL** — the contract has already been designed in the canonical Governed Semantic Evolution architecture but is not yet active implementation;
- **MISSING_CONTRACT** — the destination is now known but the generic public semantic contract has not yet been designed/landed;
- **DORMANT_NONAUTHORITATIVE** — source exists but is not active public runtime truth and must not be treated as delivered;
- **LATER_RUNTIME_PROFILE** — the semantic prerequisite should be designed now, but the concrete Rust/embedded/HIL implementation belongs after the portable semantic boundary is qualified.

The central conclusion is that the Embedded/Physical work does **not** require a second AASM architecture.

Current AASM already contains most of the difficult substrate:

```text
scoped identity + authority
        +
explicit machine/calculus state
        +
typed capabilities/providers
        +
Evidence and reasoning artifacts
        +
semantic dependency truth maintenance
        +
problem revisions and deltas
        +
external effect intent / ownership / UNKNOWN reconciliation
        +
governed resources / reservation / settlement
        +
proof and verification planes
        +
portable semantic archives
        +
applicability-scoped cross-run knowledge
```

The physical/distributed program is therefore primarily a **semantic elevation and boundary-hardening program**, not a foundational rewrite.

---

## 2. Non-negotiable architectural rule

The new integration must preserve one governing stack:

```text
Intelligence / Human / Solver / Planner
                |
             PROPOSE
                v
       AASM semantic governance
                |
      authority + Evidence + resources
                |
             AUTHORIZE
                v
        existing Effect boundary
                |
       durable ownership first
                |
             DISPATCH
                v
 authoritative external machine / tool / device
                |
             OBSERVE
                v
              Evidence
                |
      VERIFY / RECONCILE / REFINE
                |
             COMMIT
```

The integration is forbidden from introducing any of the following:

```text
second physical truth store
second authority evaluator
second resource ledger
second scheduler
second effect-dispatch lifecycle
second knowledge/admission plane
second problem-revision system
second refinement truth path
embedded device state copied into a competing AASM truth
LLM/model direct-to-actuator authority
```

AASM may gain new **contracts** and **profiles**. It must not gain parallel foundational semantics.

---

# Part I — Reconciliation of the original thirty architecture papers

## Paper 1 — Typestate and AASM Transition Calculus

**Status:** PARTIAL_SAME_PLANE

### Already present

- `typed_protocol.py` and the v0.39 typed protocol runtime define typed event schemas, pattern machines, scoped legal transitions, guard compilation, and authority-gated activation.
- The calculus already separates proposed decisions/obligations from legal activation.
- Formal and typed-capability conformance already test illegal inputs and unauthorized transitions.

### Gap

AASM currently expresses transition legality dynamically in Python/runtime contracts. It does not yet distinguish a portable subset that can be compiled into a static typestate API for Rust/embedded targets.

### Target

Define transition metadata in a language-neutral machine IR with explicit classes:

```text
structural legality
static capability requirement
dynamic AASM guard
required evidence
postcondition obligation
failure/recovery transition
```

The future Rust compiler may make the statically provable subset unrepresentable while leaving evidence/authority-dependent legality in the runtime kernel.

### Integration rule

Rust typestate strengthens the existing calculus; it never becomes a second transition definition.

---

## Paper 2 — Static and Dynamic Invariants

**Status:** PARTIAL_SAME_PLANE

### Already present

- typed schemas and typed protocol validation;
- machine/calculus invariants;
- formal assurance models;
- semantic problem/model admission;
- effect and resource invariants;
- proof/claim ceilings.

### Gap

There is no first-class invariant classification saying **where** an invariant must be enforced.

### Target contract

Proposed generic contract:

```text
aasm.invariant.v1
```

with classes:

```text
REPRESENTATIONAL
STATIC_PROTOCOL
DYNAMIC_KERNEL
EMPIRICAL
```

This prevents two opposite errors:

- implementing statically knowable illegality only as runtime `if` statements;
- treating a compile-time type as proof of an empirical physical fact.

---

## Paper 3 — Ownership as a Model for Authority

**Status:** PARTIAL_SAME_PLANE

### Already present

- `scoped_authority.py`: scoped grants, allow/deny, delegation, expiry/not-before, deny precedence;
- task leases;
- durable effect ownership;
- provider/resource ownership-like boundaries.

### Gap

There is no first-class **exclusive authority-domain lease** for semantic/physical control.

### Target

```text
aasm.authority.domain.v1
aasm.authority.lease.v1
```

An authority lease must identify:

```text
domain
holder
scope
permitted effect classes
epoch/generation
validity interval
preemptors
source authority evidence
```

It must reuse scoped authority for authorization rather than replacing it.

---

## Paper 4 — Capability-Based AASM

**Status:** PARTIAL_SAME_PLANE

### Already present

The v0.39 capability ABI governs capability providers, provider tokens, resources, versioned contracts, and existing task-lease boundaries.

### Important distinction

Current AASM capability objects primarily answer:

> What capability does this admitted provider/resource implement?

The proposed physical capability token answers:

> What exact bounded effect may this holder currently cause?

Those are related but not identical.

### Target

Add bounded effect capabilities with:

```text
operations
subject/effect domain
scope
quantitative bounds
validity interval
authority epoch
delegation depth
problem/external revision binding
revocation generation
```

Formal invariants:

```text
child rights ⊆ parent rights
stale epoch => reject
expired capability => reject
scope escape => reject
revocation generation mismatch => reject
```

Do not create a second capability registry; extend the existing capability/authority planes.

---

## Paper 5 — `no_std` as an Architectural Discipline

**Status:** LATER_RUNTIME_PROFILE

### Already present

- deterministic event/reducer semantics;
- typed public contracts;
- semantic fingerprints;
- portable semantic evolution archive;
- formal models;
- explicit persistence/replay boundaries.

### Gap

The active runtime still assumes Python and host facilities. The repository has not yet frozen the **minimum language-neutral kernel**.

### Required-before-Rust target

Define a portable kernel specification that knows only:

```text
IDs
machine state
events
transitions
guards
authority/capability refs
obligations
resource reservation refs
Evidence refs
effect refs
conflicts
revision IDs
canonical hashes
```

No Rust port should begin by translating the entire current Python package.

---

## Paper 6 — Identity Independent of Python Objects

**Status:** PARTIAL_SAME_PLANE

### Already present

AASM extensively uses explicit IDs and deterministic semantic fingerprints across Evidence, revisions, solver requests/results, knowledge, resources, effects, artifacts, reasoning objects, and archives.

### Gap

A canonical language-independent wire/binary representation for the future portable kernel has not yet been frozen.

### Target

A portable semantic object must have identity derived from canonical protocol representation, never from Python object identity, `repr`, insertion accident, object address, or pickle location.

The portable archive is the starting substrate; the machine/kernel ABI must be separately specified before Rust implementation.

---

## Paper 7 — An `embedded-hal` Equivalent for AASM

**Status:** PARTIAL_SAME_PLANE

### Already present

- capability-provider contracts;
- solver/provider manifests;
- domain adapters;
- supervisor adapters;
- effect executors.

These already establish the principle **depend on declared semantic capability, not provider brand**.

### Gap

There is not yet a generic external-machine semantic executor interface such as:

```text
MotorActuator
PositionSensor
MachineObserver
MachineExecutor
ArtifactProducer
```

### Target

The canonical machine transition refers to an abstract semantic capability. An adapter binds it to simulation, CAN, EtherCAT, GPIO/PWM, REST, HIL, or another executor.

Interface compatibility must not imply evidence equivalence.

---

## Paper 8 — Simulation → HIL → Physical Continuity

**Status:** MISSING_CONTRACT

### Already present

AASM can bind environment fingerprints, provider identities, solver evidence, revisions, and verification strength.

### Gap

There is no generic execution/qualification environment ladder that prevents simulation evidence from being silently treated as physical evidence.

### Target

```text
aasm.execution.environment.v1
aasm.qualification.level.v1
```

Suggested levels:

```text
MODEL
SIMULATION
SIL
HIL
BENCH
CONTROLLED_PHYSICAL
OPERATIONAL
```

Evidence must bind environment + hardware/firmware/artifact revision + calibration/trust context.

---

## Paper 9 — The Refinement Loop Becomes Physical

**Status:** DESIGNED_CANONICAL

### Already present

- `ProblemRevision` / `ProblemDelta`;
- Evidence;
- semantic dependency truth maintenance;
- applicability-scoped knowledge;
- solver learning;
- canonical planned `aasm.refinement.proposal.v1` / `aasm.refinement.loop.v1`.

### Gap

Physical observations are not yet a generic evaluator class in the refinement plane.

### Target

The same governed loop accepts solver, simulation, verification, physical measurement, manufacturing inspection, or human-review evidence, but **no evaluator may directly mutate the canonical problem**.

---

## Paper 10 — Governed Power Converter Example

**Status:** LATER_RUNTIME_PROFILE / CONFORMANCE TARGET

The power-converter example requires no special kernel subsystem.

It should become an engineering conformance scenario exercising:

```text
predicted state/quantity
physical observation
measurement/calibration provenance
residual/conflict
hypothesis discrimination
experiment planning
ProblemDelta admission
knowledge applicability
```

The example should be built only after the generic contracts exist.

---

## Paper 11 — Interrupts as Authoritative Events

**Status:** PARTIAL_SAME_PLANE

### Already present

AASM events already carry event identity, machine identity, sequence, timestamp, event type, reason, and data. Durable event ordering is a core runtime property.

### Gap

There is no bounded embedded interrupt/event-ingress contract with boot epoch, monotonic local sequence, overflow semantics, or explicit acknowledgement behavior.

### Target

An embedded ISR bridge should capture minimal bounded facts and enqueue a canonical event. Hard real-time safety reactions that cannot tolerate AASM latency remain in hardware/local control and are later reconciled into AASM Evidence/state.

---

## Paper 12 — Semantic Priority and Preemption

**Status:** MISSING_CONTRACT

### Existing substrate

Scoped authority, deny precedence, obligations, task leases, effects, and resource priority are already present.

### Missing semantic primitive

AASM lacks a declared partial order in which a higher authority class can invalidate conflicting lower-domain capabilities without rewriting history.

### Target

```text
aasm.authority.preemption.v1
```

Preemption must:

```text
advance affected authority epoch
invalidate future lower-authority effects
cancel work not yet dispatched
reconcile already dispatched effects
activate higher-priority obligations
```

A dispatched effect never becomes “unhappened” because authority changed.

---

## Paper 13 — Mapping AASM Semantics to RTIC

**Status:** LATER_RUNTIME_PROFILE

AASM semantic priority and an RTIC/NVIC execution priority must remain separate concepts.

The prerequisite contract is a generic transition timing requirement:

```text
aasm.transition.timing.v1
```

with deadline and maximum event→guard→authorization→dispatch latency semantics.

Only then may an embedded compiler map those requirements to RTIC or another real-time scheduler.

---

## Paper 14 — Autonomous Robot Example

**Status:** LATER_RUNTIME_PROFILE / CONFORMANCE TARGET

No robotics-specific kernel is required.

The robot scenario should qualify:

```text
global mission authority
local safety authority
bounded drive capability
stale-command epoch rejection
network partition
local-only/degraded behavior
obstacle-triggered preemption
out-of-band physical movement
reconciliation after reconnect
```

---

## Paper 15 — General Resource Governance

**Status:** IMPLEMENTED

This is one of the strongest already-realized pieces of the earlier proposal.

Current resource governance already provides:

```text
capacity observation
measurement authority
protected reserve
routing/selection
reservation
re-estimation
settlement/reconciliation
release
scoped authority separation
```

It already treats correctness/evidence/progress, wall time, monetary cost, and scarce expert usage as route-selection dimensions.

### Remaining extension

Physical resources expose richer resource **kinds**, but not a new resource plane.

---

## Paper 16 — Battery and Model Quota Under One Algebra

**Status:** PARTIAL_SAME_PLANE

The common governance idea is already correct and implemented generically.

### Gap

The resource model should explicitly classify resource dynamics such as:

```text
STOCK
RATE
OCCUPANCY
WEAR
THERMAL_MARGIN
ENERGY
```

This is needed for battery, thermal dissipation, flash endurance, machine occupancy, API quota, money, and solver capacity without pretending their physics are identical.

---

## Paper 17 — Hierarchical Authoritative State

**Status:** DESIGNED_CANONICAL / PARTIAL_SAME_PLANE

### Already present

- hierarchical scopes;
- scoped authority;
- Evidence source identity;
- problem/external revisions;
- planned external-machine bindings.

### Gap

AASM does not yet have a general **fact authority** contract identifying which source is authoritative for which state namespace.

### Target

```text
aasm.fact.authority.v1
```

A device may be authoritative for measured motor fault while the mission machine remains authoritative for mission intent. Observation authority does not imply decision authority.

---

## Paper 18 — Conflicting Truth as a First-Class Object

**Status:** PARTIAL_SAME_PLANE

AASM already has:

- contradictions/conflicts;
- reasoning artifacts and contested/refuted/stale states;
- truth-maintenance propagation;
- solver disagreement treated as conflict rather than voting.

### Gap

It lacks a generic external-state **expectation violation** object preserving desired, predicted, observed, and admitted authoritative values together.

### Target

```text
aasm.state.conflict.v1
```

Contradiction remains Evidence and may trigger diagnosis/refinement; no value is silently overwritten to make the mismatch disappear.

---

## Paper 19 — Four Kinds of State

**Status:** MISSING_CONTRACT

This remains a major required semantic elevation.

AASM must explicitly distinguish:

```text
Desired
Predicted
Observed
Authoritative
```

A command updates desired state and may produce a prediction. Observation updates observed claims. Only verification/reconciliation under the relevant fact authority may update admitted authoritative state.

This should be implemented as typed claims/projections over the existing Evidence/state planes rather than four independent databases.

---

## Paper 20 — Verification of Achieved State

**Status:** PARTIAL_SAME_PLANE

### Already present

`EffectSpec` already contains preconditions and postconditions; v0.54 effect semantics already separate intent, authorization, dispatch ownership, outcomes, UNKNOWN, and reconciliation.

### Gap

A generic postcondition verifier does not yet establish:

```text
command acknowledged != state achieved
```

### Target

A transition may not commit an achieved external state merely because the executor call succeeded. Expected postconditions must be correlated with authoritative observations/evidence under explicit timing/freshness rules.

---

## Paper 21 — Generalized Transition Lifecycle

**Status:** PARTIAL_SAME_PLANE

AASM already owns most of the lifecycle:

```text
PROPOSED
AUTHORIZED
RUNNING / dispatched ownership
SUCCEEDED / FAILED / UNKNOWN / CANCELLED
RECONCILIATION
```

The missing elevation is to add explicit observation/postcondition verification and state-commit semantics without replacing the existing Effect lifecycle.

Desired target projection:

```text
PROPOSED
VALIDATED
AUTHORIZED
OWNED
DISPATCHED
ACTUATING
OBSERVED
VERIFIED
COMMITTED
```

Not every effect profile must expose every stage; collapse is legal only when semantic equivalence is explicit.

---

## Paper 22 — `RefinementLoop` as a Universal Primitive

**Status:** DESIGNED_CANONICAL

This remains fully supported by current architecture and should not be narrowed to SPICE/EM/FEA or physical systems.

The evaluator may produce evidence and a refinement proposal. It may never directly apply a problem delta.

No-progress, oscillation, resource exhaustion, inconclusive, conflict, and goal-satisfied termination semantics must be explicit.

---

## Paper 23 — Minimal Embedded AASM Kernel

**Status:** LATER_RUNTIME_PROFILE

The repository now has enough portable contracts to make this plausible, but the kernel boundary is not frozen.

Do not port the host runtime wholesale.

First define the minimal kernel and differential conformance traces. Embedded persistence should be a bounded journal/adapter over the same event semantics, not an independent state model.

---

## Paper 24 — Compile Portable Machine Definitions

**Status:** MISSING_CONTRACT, strategically high priority

AASM has multiple IRs but not yet one canonical **machine execution IR** from which Python, Rust, formal model, graph, docs, and test vectors can all be generated.

Target:

```text
aasm.machine.ir.v1
```

with source/target states, events, guards, capabilities, evidence/postcondition requirements, timing requirements, resource requirements, and recovery semantics.

This contract must precede a Rust machine compiler.

---

## Paper 25 — AASM as a Machine Compiler

**Status:** LATER_RUNTIME_PROFILE dependent on Paper 24

Once `aasm.machine.ir.v1` exists, generators may produce:

```text
Python reference runtime
Rust std runtime
Rust no_std runtime
formal transition model
graph visualization
test vectors
documentation
observability schema
```

The canonical IR defines meaning. Generated implementations do not.

---

## Paper 26 — Closed-Loop Robotic Mechanism Engineering

**Status:** LATER CONFORMANCE TARGET

This becomes a cross-capability demonstrator after artifact lineage, external machine supervision, physical observation, governed experiments, refinement, and knowledge applicability are implemented.

It is valuable specifically because it exercises the full DESIGN→VERIFY→BUILD→OPERATE→OBSERVE→LEARN→REDESIGN loop without requiring robot-specific kernel semantics.

---

## Paper 27 — Safety-Critical Development Path

**Status:** LATER_RUNTIME_PROFILE / MISSING SAFETY PROFILE

AASM already has evidence, provenance, revision, authority, formal checks, immutable history, proof strength, and fail-closed admission concepts useful to high-assurance development.

A future safety profile must constrain rather than expand semantics:

```text
bounded resources/queues
controlled allocation
no dynamic code loading
strict unsafe-code policy
configuration control
toolchain provenance
requirements traceability
independent checker strategy
hardware safety mechanism integration
```

Certification is a system/process property; no language or AASM profile may claim it automatically.

---

## Paper 28 — Unified AASM Architecture

**Status:** IMPLEMENTED DIRECTION / architecture doctrine

The current Governed Semantic Evolution architecture already supports the intended unified structure:

```text
reasoning / semantic evolution
        |
AASM governance
        |
portable deterministic semantics
        |
host / external machine profiles
        |
authoritative external systems
        |
Evidence / verification / reconciliation / refinement
```

The physical program extends this same system.

---

## Paper 29 — Immediate Architecture Changes

**Status:** IN PROGRESS / RECORDED

The current reconciliation has already changed the roadmap/execution ledger so the destination is represented now rather than deferred.

The `PHY-01` through `PHY-11` rows are the durable record of the physical/distributed seams.

Before Rust implementation, the priority semantic additions are:

```text
fact/state authority
four state-claim kinds
postcondition verification
authority domains/epochs/bounded effect capabilities
temporal/causal semantics
physical identity/calibration/trust
degraded/safety envelope semantics
observation lifecycle/fusion
epistemic debt/risk/irreversibility
experiment contract
portable machine IR + kernel boundary
```

---

## Paper 30 — Governed Epistemic Control Architecture

**Status:** IMPLEMENTED DIRECTION / permanent doctrine

The deepest claim survives current-source review.

AASM already separates proposal, authority, Evidence, solver claims, verification, effect ownership, resources, admission, and reusable knowledge strongly enough that the next architecture can state a permanent law:

> **Reasoning may become more capable without automatically becoming more authoritative.**

The physical integration must preserve that asymmetry down to device effect boundaries.

---

# Part II — Reconciliation of the thirty second-order additions

## Addition 1 — Authority over time

**Status:** PARTIAL_SAME_PLANE

Current grants/leases have time validity and machine events have sequence/timestamps. Missing: generic observation age, authority epoch, monotonic device boot epoch, deadline, and clock-quality semantics.

Target: `PHY-04 temporal-causal-semantics`.

---

## Addition 2 — Causal consistency separate from chronology

**Status:** PARTIAL_SAME_PLANE

AASM has `CausalDecisionRecord` and causal event/artifact provenance, but that describes semantic causation, not distributed event partial order.

Missing generic relations:

```text
CAUSED_BY
HAPPENS_BEFORE
CONCURRENT_WITH
ORDER_UNKNOWN
```

with node/boot epoch and monotonic sequence evidence.

---

## Addition 3 — Physical identity

**Status:** MISSING_CONTRACT

`ExternalReference`, runtime provenance, artifact fingerprints, and environment fingerprints provide strong substrate.

Missing generic physical identity/assembly contract for board/device/sensor/actuator/fixture/calibration/firmware association.

Target: `PHY-05`.

---

## Addition 4 — Calibration lifecycle

**Status:** MISSING_CONTRACT

Measurement authority exists. Calibration lifecycle does not.

Target states should include:

```text
VALID
DUE
EXPIRED
INVALID
OUT_OF_RANGE
SUPERSEDED
```

Calibration validity affects evidence admissibility/grade; it does not erase historical measurements.

---

## Addition 5 — Generalized trust boundary model

**Status:** PARTIAL_SAME_PLANE

AASM already distinguishes proposer/verifier/policy/controller roles, provider identity, measurement authority, evidence strength, and source provenance.

Missing: explicit source trust declaration describing what a source is authoritative to assert and what it is not.

This should compose with fact authority, not become a generic “trust score.”

---

## Addition 6 — Hardware-rooted identity and attestation

**Status:** LATER_RUNTIME_PROFILE with contract seam required now

Reserve attestation fields for:

```text
secure boot state
firmware measurement
hardware-backed key identity
anti-rollback counter
attestation evidence
```

Do not make a specific TPM/TEE/vendor the kernel abstraction.

---

## Addition 7 — Degraded autonomy doctrine

**Status:** MISSING_CONTRACT

AASM has explicit machine states and authority/resource/effect boundaries, but no generic degraded-operation policy.

Target modes may include:

```text
FULL_OPERATION
DEGRADED_OPERATION
LOCAL_ONLY
SAFE_HOLD
RETURN_TO_SAFE_STATE
EMERGENCY
```

Loss of upstream intelligence should reduce/reshape authority according to policy, never create implicit authority.

---

## Addition 8 — Monotonic authority degradation under uncertainty

**Status:** MISSING FORMAL POLICY

For safety-sensitive profiles, define and verify where appropriate:

```text
weaker evidence / lost dependencies
    =>
new permissible effect set ⊆ old permissible effect set
```

Exceptions require explicit policy justification.

This is a candidate formal invariant, not a universal rule for every non-safety domain.

---

## Addition 9 — Observation lifecycle

**Status:** PARTIAL_SAME_PLANE

Reasoning `Observation` artifacts and Evidence exist, including verified/stale/refuted lifecycle semantics.

Missing physical observation transformation chain:

```text
RAW
NORMALIZED
CALIBRATED
DERIVED
FUSED
VALIDATED
REJECTED
SUPERSEDED
STALE
DISPUTED
```

Derived observations must reference source observations; they do not overwrite them.

---

## Addition 10 — Sensor fusion must not become voting for truth

**Status:** ARCHITECTURAL DOCTRINE; MISSING FUSION CONTRACT

AASM already enforces the analogous solver rule: agreement does not vote truth.

A future fusion contract must represent source independence, uncertainty, calibration, model identity, authority, and evidence grade.

Three low-grade correlated sensors must not automatically defeat one independently calibrated authoritative source.

---

## Addition 11 — Epistemic debt

**Status:** PARTIAL_SAME_PLANE / DESIGNED_CANONICAL

The canonical roadmap already includes verification debt. Reasoning artifacts can be assumptions/stale/contested, and dependency truth maintenance propagates staleness.

Missing a generalized `EpistemicDebt` contract covering unresolved assumption, stale calibration, approximate model, missing physical test, uncertain postcondition, unresolved mapping/conflict, etc.

---

## Addition 12 — Debt propagation

**Status:** PARTIAL_SAME_PLANE

Semantic dependencies already provide affected-descendant truth maintenance and preserve unrelated siblings.

This is exactly the plane to extend. Do not create a separate debt graph.

Required distinction:

```text
FALSE
STALE
INSUFFICIENTLY_JUSTIFIED
UNKNOWN
```

---

## Addition 13 — Assumptions as explicit dependencies

**Status:** PARTIAL_SAME_PLANE

`Assumption` already exists as a reasoning artifact; semantic dependencies already connect artifacts/decisions/obligations.

The missing work is ergonomic/public composition: make solver/experiment/artifact/machine results declare assumption dependencies so invalidation propagates precisely.

---

## Addition 14 — Counterfactual execution

**Status:** PARTIAL_SAME_PLANE / MISSING GENERIC CONTRACT

AASM already supports planners, optimization, formal verification, simulation-like providers, and resource-aware selection.

A generic high-impact precommit contract should ask:

```text
predicted consequences
reachable hazards
new obligations
resource consumption
uncertainty/evidence strength
```

Counterfactual analysis remains evidence; it never grants execution authority.

---

## Addition 15 — Risk separate from resource cost

**Status:** MISSING_CONTRACT

The resource plane must not absorb risk.

Target:

```text
aasm.risk.envelope.v1
```

with hazard, severity, exposure, mitigation, residual risk, evidence and authority.

---

## Addition 16 — Hard hazard constraints dominate optimization

**Status:** PARTIAL_SAME_PLANE

AASM already has the correct principle: hard floors and hard semantics are not weighted objectives; scarcity cannot lower correctness/evidence requirements.

Risk/hazard constraints must use the same doctrine.

---

## Addition 17 — Irreversible-transition semantics

**Status:** PARTIAL_SAME_PLANE

`EffectSpec` already has `reversible` and `compensation`.

Missing: explicit irreversible-action classification and precommit evidence/escalation policy.

Examples include material cutting, one-time deployment, fuse programming, or other non-compensable effects.

---

## Addition 18 — Irreversibility raises evidence requirements

**Status:** MISSING POLICY over existing Effect/Evidence planes

Formalize a policy family where greater irreversibility may require stronger evidence/authority before effect ownership is acquired.

This must remain profile/policy driven, not a magical global scalar.

---

## Addition 19 — Precommit and postcommit obligations

**Status:** PARTIAL_SAME_PLANE

AASM has obligations and effect pre/postconditions but no general obligation phase taxonomy.

Target phases:

```text
PRE_AUTHORIZE
PRE_DISPATCH
POST_DISPATCH
POST_OBSERVE
POST_VERIFY
RECOVERY
```

Use the existing obligation graph/lifecycle.

---

## Addition 20 — Safety envelope beyond discrete states

**Status:** PARTIAL_SAME_PLANE

`continuous_ir.py` provides deterministic continuous mathematical representation, but not an operational safety-envelope contract attached to external machine state.

Target: reusable continuous predicates + scenario/mode bindings + violation transitions.

---

## Addition 21 — Hybrid discrete/continuous semantics

**Status:** MISSING COMPOSITION CONTRACT

AASM already has discrete machine state and continuous mathematical IR. It should not become an ODE solver.

Target:

```text
aasm.hybrid.state.v1
```

that binds discrete mode to observed continuous quantities/envelopes and external solver/evidence sources.

---

## Addition 22 — Proof-carrying configuration

**Status:** PARTIAL_SAME_PLANE

AASM already has proof claims, fingerprints, versioned contracts, provider/runtime provenance, formal assurance, and artifact identity.

Missing a generic deployable machine/configuration package containing configuration fingerprint, compiler identity, compatibility profile, verification evidence, and authorization.

This later feeds the machine compiler/embedded profile.

---

## Addition 23 — Firmware/configuration rollout as an AASM machine

**Status:** PARTIAL_SAME_PLANE / LATER PROFILE

AASM can already model this lifecycle generically.

The physical integration should supply a reference rollout pattern:

```text
CANDIDATE -> VERIFIED -> STAGED -> DEPLOYING -> BOOT_VERIFIED -> ACCEPTED
                                      \-> ROLLBACK_REQUIRED
```

No firmware-specific kernel state is necessary.

---

## Addition 24 — No invisible mutable configuration

**Status:** ARCHITECTURAL INVARIANT

Any behavior-changing configuration participating in authoritative operation should have identity, revision, provenance, authority, and applicability binding.

Runtime provenance already establishes this principle for solver execution. The physical program must generalize it to devices/controllers/config packages.

---

## Addition 25 — Human intervention uses the same semantics

**Status:** PARTIAL_SAME_PLANE

AASM already has human decision backends, authority classes, Evidence, and explicit operators.

Physical/manual observations and overrides must enter as typed Evidence/authority/effects, not magical exceptions.

---

## Addition 26 — Manual override preserves provenance

**Status:** MISSING OVERRIDE CONTRACT over existing authority/Evidence

An override should record:

```text
principal
exact waived rule
reason
scope
duration
risk acceptance
authority evidence
resulting obligations
```

Override never deletes the rule or history it bypassed.

---

## Addition 27 — Formal experiment object

**Status:** MISSING_CONTRACT

This is required to make physical refinement scientifically useful.

Target:

```text
aasm.experiment.v1
```

fields include hypothesis, controlled variables, measured variables, procedure, environment, calibration/fixture identity, expected discriminating result, evidence floor, resource demand, safety/risk constraints, and result provenance.

---

## Addition 28 — Experiment selection as optimization

**Status:** PARTIAL_SAME_PLANE

AASM already has heterogeneous optimization and governed resources.

After `aasm.experiment.v1`, candidate experiments can be selected using expected uncertainty reduction/information value under hard evidence/safety constraints and resource costs.

Selection remains a proposal; experiment authorization remains governed.

---

## Addition 29 — Scientific-discovery capability

**Status:** EMERGENT CAPABILITY, no special kernel subsystem

The generic loop:

```text
hypothesis
experiment
observation
conflict
refinement
knowledge admission
```

falls naturally out of reasoning artifacts + experiments + Evidence + refinement + applicability-scoped knowledge.

AASM need not become “a science AI” for the architecture to support governed empirical inquiry.

---

## Addition 30 — Epistemic containment

**Status:** STRONGLY PARTIAL / candidate permanent invariant

This principle is already visible across several real AASM subsystems:

- foreign cross-run knowledge explicitly does not inherit source authority;
- solver normalization grants no truth authority;
- provider optimality is not independent proof;
- cross-solver agreement never votes truth;
- capability/resource availability does not grant authority;
- Evidence transport and replay do not mutate truth by themselves.

The principle should be promoted to a permanent architecture invariant:

> **No component may cause a claim to acquire greater authority merely by transporting, repeating, aggregating, remembering, translating, fusing, or executing it.**

Authority may increase only through an explicit governed admission/verification/authorization process.

This is the generic defense against hallucination laundering, consensus laundering, memory laundering, solver laundering, simulation laundering, sensor-fusion laundering, and cross-run knowledge laundering.

---

# Part III — Reconciled target architecture

The repository should evolve toward the following single architecture:

```text
                    INTELLIGENCE / HUMANS / SOLVERS
                              |
                           proposal
                              v
                 AASM REASONING + SEMANTIC EVOLUTION
                              |
               claim / hypothesis / prediction / plan
                              v
                       AASM GOVERNANCE
        authority | capabilities | Evidence | resources | risk
                              |
                         effect intent
                              v
                EXISTING EFFECT OWNERSHIP BOUNDARY
                              |
                    durable ownership first
                              v
                       EXECUTOR ADAPTER
                              |
                 host / simulator / HIL / device
                              |
                       external reality
                              |
                          observation
                              v
               OBSERVATION / FACT AUTHORITY PLANE
                              |
                   postcondition verification
                              v
                 authoritative-state admission
                              |
                  commit / conflict / refinement
                              |
             applicability-scoped governed knowledge
```

The future portable kernel is a constrained implementation of these semantics, not a competing implementation model.

---

# Part IV — What must be designed before any Rust / `no_std` implementation

The order matters. The repository should **not** begin a broad Rust port before these public semantic contracts are stable enough to serve as differential-conformance targets.

## Semantic prerequisite set A — External reality

1. `aasm.fact.authority.v1`
2. `aasm.state.claim.v1` with desired/predicted/observed/authoritative kinds
3. `aasm.machine.binding.v1`
4. `aasm.machine.transition.v1`
5. `aasm.machine.state-observation.v1`
6. generic postcondition verification contract
7. state-conflict / expectation-violation contract

## Semantic prerequisite set B — Authority to affect reality

8. authority domain + exclusive authority lease
9. authority epoch/generation
10. bounded effect capability token
11. capability delegation/non-amplification
12. revocation/preemption semantics
13. stale-command rejection

## Semantic prerequisite set C — Time and physical evidence

14. causal/temporal event identity
15. observation freshness/age/clock-quality semantics
16. physical identity/assembly reference
17. calibration lifecycle
18. source trust/fact-authority declaration
19. execution/qualification environment level
20. observation transformation/fusion contract

## Semantic prerequisite set D — Safety and epistemic completeness

21. degraded-autonomy policy
22. risk/hazard envelope
23. irreversible-effect policy
24. obligation phase taxonomy
25. continuous safety envelope + hybrid-state composition
26. generalized epistemic debt + propagation
27. manual override contract
28. experiment contract

## Semantic prerequisite set E — Portability

29. invariant taxonomy
30. canonical machine IR
31. canonical kernel serialization/identity rules
32. transition timing requirements
33. portable kernel state boundary
34. cross-runtime deterministic trace/fingerprint corpus
35. generated-configuration/proof package format

Only after these contracts are sufficiently stable should implementation proceed into:

```text
Rust std reference kernel
        -> differential replay against Python
Rust no_std profile
        -> bounded storage / queues / resource limits
semantic executor traits
RTIC or other real-time backend
sim/SIL/HIL/physical conformance
safety-restricted profile
```

---

# Part V — Reuse map: where new semantics must attach

| New seam | Must extend/reuse | Must NOT create |
|---|---|---|
| authority domains/epochs | `scoped_authority.py`, task/effect authority evidence | second ACL/permission database |
| bounded effect capability | v0.39 capability ABI + scoped authority + EffectIntent | second tool-capability registry |
| four state claims | Evidence + semantic evolution + machine observation | four independent state stores |
| postcondition verification | `effects.py`, Evidence, obligations | new effect lifecycle |
| external machine binding | revisions + EffectIntent/Ownership/Reconciliation | mirrored external truth |
| physical identity/calibration | ExternalReference + Evidence/provenance | physical metadata side database |
| temporal causality | Event IDs/sequences + semantic dependency provenance | wall-clock-as-truth scheduler |
| degraded autonomy | existing machine states/authority/effects/resources | embedded-only policy engine |
| safety envelope | continuous IR + scenarios + Evidence | physics solver inside kernel |
| epistemic debt | obligations + reasoning artifacts + semantic dependencies | separate debt graph |
| experiment | reasoning + resources + effects + Evidence + refinement | lab-specific kernel |
| refinement | ProblemDelta + Evidence + authority + dependencies | evaluator direct model mutation |
| portable kernel | canonical contracts/archive/replay | rewritten independent AASM |
| machine compiler | canonical machine IR | implementation-defined semantics |

---

# Part VI — Reconciled implementation priority

This document is intentionally **not yet the final integration plan**, but source reconciliation establishes the correct dependency order.

### Priority 0 — Baseline integrity

- finish generic CI cleanup after development/release identity decoupling;
- keep 0.56.1 unpublished until the selected release scope is deliberately qualified;
- keep version-policy gate active;
- do not create new chronology modules.

### Priority 1 — External reality semantics

Implement fact authority + four state-claim kinds + external machine binding + postcondition verification over the existing effect plane.

This closes the largest correctness gap: **command is not achievement**.

### Priority 2 — Physical authority semantics

Implement authority domains/leases/epochs + bounded effect capabilities + preemption/revocation.

This closes the largest control gap: **reasoning is not actuator authority**.

### Priority 3 — Temporal/evidence provenance

Implement causal ordering, freshness/clock quality, physical identity, calibration, trust declarations, execution-environment levels, observation lifecycle/fusion.

This closes the largest distributed-truth gap: **a well-formed observation is not automatically current or authoritative**.

### Priority 4 — Safety/epistemic semantics

Implement degraded autonomy, risk/hazard envelopes, irreversibility/evidence escalation, obligation phases, hybrid safety envelopes, epistemic debt, manual overrides.

### Priority 5 — Governed experiments and physical refinement

Implement experiment object + verification/evidence acquisition + physical evaluator integration into `RefinementLoop` + applicability-scoped knowledge.

### Priority 6 — Portable kernel boundary and machine IR

Freeze the portable semantic kernel and machine IR, then build Python differential reference traces.

### Priority 7 — Rust / embedded profile

Only now implement Rust std, Rust `no_std`, semantic executor traits, interrupt/event bridge, timing backend/RTIC mapping, and embedded bounded-journal profile.

### Priority 8 — Qualification

Run one canonical machine across simulation → SIL → HIL → bench → controlled physical hardware, preserving the same machine semantics and increasing evidence authority only through explicit qualification rules.

---

# Part VII — Final reconciliation verdict

None of the Embedded/Physical proposals is superfluous.

The source review changes **where they belong**, not whether they matter.

The early whitepapers sometimes described them as if AASM needed entirely new foundations. Current AASM has advanced enough that many foundations now exist:

```text
resource governance          REAL
scoped authority             REAL
typed capability providers   REAL
effect ownership / UNKNOWN   REAL
Evidence / epistemic states  REAL
problem revisions/deltas     REAL
truth maintenance            REAL
proof/verification planes    REAL
portable archive             REAL
knowledge authority firewall REAL
```

What is missing is the disciplined elevation from computational governance to **authoritative external/physical reality**:

```text
fact authority
four state claims
postcondition verification
authority epochs / bounded effect rights
distributed causal time
physical identity / calibration / attestation
degraded authority and safety envelopes
observation/fusion provenance
epistemic debt / risk / irreversibility
experiments / physical refinement
portable machine IR / kernel
embedded real-time profile
```

The resulting direction is not “AASM becomes embedded.”

It is:

> **AASM becomes vertically complete enough that the same governed semantics can extend from high-level reasoning and heterogeneous solvers through authoritative external state machines and, eventually, down to a bounded embedded execution kernel immediately above physical hardware.**

And the permanent safety/epistemic rule tying all of it together is:

> **Information may move freely through AASM. Authority may not hitchhike with it.**
