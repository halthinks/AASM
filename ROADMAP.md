# AASM Roadmap

AASM's latest immutable public release is **v0.56.0 — Truthful Solver Outcomes + Governed Semantic Evolution + Engineering Mathematical IR**.

**Current development package on `main`:** `0.56.1`  
**Current active adoption contract:** `aasm.adoption.v1 / 0.32.11`  
**Qualified development boundary:** PR-1, PR-2, complete PR-3 / PHY-01, plus S3 state conflict, causal event identity, observation freshness, physical identity, calibration, and source trust  
**Exact S3 reality-evidence qualification head:** `6dbd62dc704b15fccb86a61053ce7bfdcdea477a` — all 23 current custom contexts green  
**Immediate unfinished boundary:** **U4 / S3 execution/qualification environment (`aasm.execution.environment.v1`)**

Package SemVer is not an architecture-progress counter. Exact unreleased identity is the Git SHA. Future capabilities below are milestone identities, not reserved package versions. See [`docs/VERSIONING.md`](docs/VERSIONING.md).

## Canonical direction

AASM is being built as a **governed reasoning and supervisory-control kernel over authoritative external state machines, typed engineering artifacts, heterogeneous solvers, verification/refinement loops, and eventually a portable deterministic kernel that can be implemented in Python, Rust `std`, and constrained Rust `no_std` profiles without changing the governing semantics**.

This is one architecture, not three projects.

- **TextPCB** is the primary demanding engineering qualification consumer. TextPCB remains authoritative for its project truth, CAD/PCB/domain state, artifacts, and domain rules. AASM governs lineage, authority, resources, solver/verifier use, evidence, revision-aware transitions, refinement admission, and readiness.
- **Physical/distributed AASM** extends the same authority, Evidence, resource, effect, revision, obligation, and knowledge planes to authoritative external/physical reality.
- **Rust / `no_std` AASM** is a conforming implementation of a frozen portable semantic kernel. It is not a second runtime architecture and must not redefine machine truth, authority, effects, or transition legality.

The permanent product-backward rule is:

> **Known portable/embedded requirements constrain contracts now. Broad Rust implementation waits for a stable portable kernel; portability requirements do not.**

## Canonical implementation sources

1. [`docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`](docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md) — **single canonical merged execution roadmap** for TextPCB compatibility, physical/distributed semantics, portable kernel, and Rust/embedded conformance.
2. [`docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`](docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md) — TextPCB/general engineering architecture and governed semantic evolution doctrine.
3. [`docs/architecture/GOVERNED_PHYSICAL_DISTRIBUTED_REALITY_RECONCILIATION.md`](docs/architecture/GOVERNED_PHYSICAL_DISTRIBUTED_REALITY_RECONCILIATION.md) — reconciliation of the embedded/physical/Rust research against real AASM substrate.
4. [`docs/implementation/GOVERNED_PHYSICAL_REALITY_INTEGRATION_PLAN.md`](docs/implementation/GOVERNED_PHYSICAL_REALITY_INTEGRATION_PLAN.md) — detailed physical-program contract requirements. Its historical first-slice queue is subordinate to the current canonical roadmap and execution ledger.
5. [`docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md`](docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md) — live evidence-backed implementation state.
6. [`docs/source_material/SOURCE_LOCK_MANIFEST.md`](docs/source_material/SOURCE_LOCK_MANIFEST.md) — locked source hashes, precedence, and no-drift rules.

## Permanent public invariants

1. **One truth path.** No parallel TextPCB truth, physical truth table, Rust truth table, hosted-only truth, or direct domain mutation path may bypass AASM admission semantics.
2. **Information does not carry authority.** Transport, repetition, memory, aggregation, translation, sensor fusion, solver agreement, simulation, replay, or execution cannot elevate authority by themselves.
3. **Command is not achievement.** Effect success/ACK is not proof that an external or physical postcondition was achieved.
4. **Scoped identity and authority remain distinct.** Principal / Workspace / Scope / Machine / external subject identities remain explicit; resource rights and effect rights are separate.
5. **Proposal/commit remains explicit.** Humans, models, solvers, verifiers, TextPCB, simulators, external machines, and imported knowledge may propose or observe. Governed AASM transitions commit.
6. **No second scheduler, resource ledger, effect lifecycle, revision system, knowledge plane, refinement truth path, or authority evaluator.** New semantics extend the existing planes.
7. **Lease/reservation before consumption; durable ownership before external effects.** Resource availability never grants authority; authority never grants unlimited resources.
8. **UNKNOWN remains first class.** Unknown external-effect outcomes block unsafe retries/dependent readiness until reconciliation.
9. **Revision-bound applicability.** Solver, verifier, artifact, external-machine, calibration, observation, refinement, and learned results bind to exact applicable revisions/environments.
10. **No silent unsupported lowering.** Exact, translated, approximate, verifier-only, and unsupported semantics stay distinguishable and fail closed when required meaning cannot be preserved.
11. **Hard semantics dominate optimization/scarcity.** Quota, money, time, provider availability, or expert-model scarcity may change strategy but never hard requirements/evidence floors.
12. **Cross-backend or cross-sensor agreement never votes truth.** Agreement is corroboration; contradiction is conflict; authority comes from explicit governed evidence/admission.
13. **Portable identity is canonical, never implementation accidental.** No public portable identity may depend on Python object identity, `repr`, memory address, insertion accident, pickle location, Rust address, or platform-specific serialization.
14. **Rust typestate may strengthen legality but may not redefine it.** Compile-time legality is generated from canonical machine semantics; empirical facts and dynamic authority/evidence remain runtime-governed.
15. **TextPCB remains a consumer/conformance target, not kernel logic.** No TextPCB-specific type enters the AASM kernel merely to make the adapter easier.
16. **Readiness is deterministic and explainable.** Blocking stale evidence, unresolved conflicts, UNKNOWN effects, missing required verification, safety/risk obligations, or profile-conformance debt block readiness.
17. **No invisible mutable configuration.** Behavior-changing configuration has identity, revision, provenance, scope, authority, and applicability.
18. **No package version per milestone.** Contract versions and architecture milestones evolve independently; package SemVer is assigned only to an intentionally frozen release scope.

## What is already real

The released substrate through v0.56.0 already provides semantic problems/reasoning artifacts, semantic dependency truth maintenance, typed capability/provider contracts, formal verification workers, hierarchical memory/context, heterogeneous solvers, proof claims, solution pools, multi-objective/resource governance, scoped authority, durable solver learning, EffectIntent/ownership/UNKNOWN reconciliation, portable semantic archives, problem revisions/deltas, generalized mathematical IR, and truthful solver outcomes.

The active 0.56.1 development line has additionally qualified:

- **PR-1 / authoritative state:** `FactAuthority`; `DESIRED | PREDICTED | OBSERVED | AUTHORITATIVE` state claims; no consensus/transport authority laundering.
- **PR-2 / external-machine supervision:** machine binding, transition proposal through existing `EffectIntent`, execution-correlated postcondition verification, and `SUCCEEDED != achieved state`.
- **PR-3 / PHY-01 physical authority and effect-boundary integration:** authority domains, exclusive leases/epochs, bounded effect capabilities, non-amplifying delegation, stale-command fencing, semantic preemption, crash-safe preemption recovery, and mandatory current authority/capability rechecks at the inherited `authorize_effect` and `execute_effect` boundaries.
- **S3 state conflict:** immutable expectation-vs-actual conflict Evidence over existing state claims, exact portable JSON/revision comparison, no claim/truth overwrite, and TextPCB-style out-of-band project revision fixtures.
- **S3 causal event identity:** source node + boot epoch + local sequence identity, explicit integer-nanosecond clock coordinates, portable 63-bit bounds, and no replacement of the AASM replay event log.
- **S3 observation freshness:** explicit `FRESH | STALE | UNKNOWN` assessments bound to an exact observation/claim/causal event/policy context, with explicit receipt fallback and no authority elevation or universal admission.
- **S3 physical identity:** exact subject-instance/configuration identity Evidence with same-context divergence fenced until an explicit problem/external revision change; identity existence grants no FactAuthority, effect authority, or source trust.
- **S3 calibration:** exact physical-identity-bound calibration Evidence with explicit nanosecond validity and append-only revocation; no hidden current calibration, no observation rewriting, and no authority/trust by existence.
- **S3 source trust:** explicit source-policy Evidence bound to exact principals/subjects/identity/calibration/revisions; no reputation score or voting; `TRUSTED` does not admit claims, grant effect authority, or replace `FactAuthority`.

PR-3H preserves the existing scoped `effect.authorize`, resource reservations, Worker/TaskLease path, durable `EffectOwnership`, dispatch, `UNKNOWN`, and reconciliation. A prior capability-use validation record remains Evidence only and cannot become a reusable bearer token.

## Unified merged dependency graph

```text
RELEASED/GATED AASM SUBSTRATE
        |
        +--> PR-1 authoritative state --------------------------- GATED
        |
        +--> PR-2 external-machine supervision ----------------- GATED
        |
        +--> PR-3 physical authority/capabilities
        |       PR-3A-G ----------------------------------------- GATED
        |       PR-3H effect-boundary integration --------------- GATED
        |
        +--> U4/S3 state conflict ------------------------------- GATED
        |       causal event identity --------------------------- GATED
        |       observation freshness --------------------------- GATED
        |       physical identity/calibration/source trust ------ GATED
        |       execution/qualification environment ------------- NEXT
        |       observation lifecycle/fusion -------------------- QUEUED
        |       artifact revision/entity evolution -------------- QUEUED
        |
        v
U4  Reality identity + time + artifact lineage + observation epistemics ---- ACTIVE
        |\
        | +--> TextPCB artifact/entity/revision qualification
        | +--> portable identity/serialization constraints active
        v
U5  Engineering semantics + safety + uncertainty
        |\
        | +--> TextPCB quantities/rules/scenarios/safety fixtures
        | +--> invariant taxonomy / portable numerical boundaries
        v
U6  Governed refinement + experiments + verification planning
        |\
        | +--> TextPCB DRC/ERC/SPICE/EM/thermal feedback loops
        | +--> refinement/evidence represented as portable references
        v
U7  Portable machine IR + kernel boundary + machine compiler
        |\
        | +--> Python reference interpreter + deterministic trace corpus
        | +--> representative TextPCB supervisory workflow compiled to IR
        v
U8  Rust std reference kernel
        |
        +--> differential replay/fingerprint equivalence vs Python
        v
U9  Rust no_std + bounded journal/queues + executor traits + real-time backend
        |
        v
U10 SIM -> SIL -> HIL -> BENCH -> CONTROLLED_PHYSICAL qualification
        |\
        | +--> generic embedded conformance
        | +--> TextPCB engineering adapter conformance/readiness
        v
U11 permanent cross-capability stress corpus + hosted-foundation review
```

The rails are deliberately merged: **TextPCB continuously pressures the generic semantic contracts, while portability continuously constrains their representation.** Rust implementation is not allowed to drift into a separate model later.

## Current execution programs

### U3 — Physical Authority at the Existing Effect Boundary

**Status: GATED.**

PR-3H is implemented in the active `AASMEngine` and qualified at exact head `b910549677ec6f84a32e39ad625c131f68d4348c` together with all inherited release-required contexts. The complete PR-3 / PHY-01 program remains qualified on the later cumulative boundary `6dbd62dc704b15fccb86a61053ce7bfdcdea477a`.

A bounded physical effect is rechecked at authorization and execution against the current authority domain/lease identity, lease fingerprint/holder, authority epoch, capability identity/fingerprint and revocation generation, operation/bounds, workspace/scope/subject, problem/external revisions, and current validity time. An earlier `EffectCapabilityUse` validation remains Evidence only.

The integration reuses the existing v0.54 `EffectIntent`, scoped `effect.authorize`, TaskLease/resource governance, durable `EffectOwnership`, dispatch, `UNKNOWN`, and reconciliation pathways. It introduces no second dispatcher, effect store, lifecycle, resource ledger, or authority evaluator.

**Gate:** `aasm/physical-effect-integration` — GATED.

### U4 — Reality Identity, Time, Artifact Lineage, and Observation Epistemics

**Status: ACTIVE.**

Current exact qualification boundary: `6dbd62dc704b15fccb86a61053ce7bfdcdea477a`, adoption `0.32.11`, with all 23 current custom contexts green.

This merges the old external-machine artifact/entity work with the physical/distributed evidence program.

Required contracts/seams:

- `aasm.state.conflict.v1` / expectation violation — **GATED**;
- `aasm.event.causality.v1` — **GATED**;
- `aasm.observation.freshness.v1` — **GATED**;
- `aasm.physical.identity.v1` — **GATED**;
- `aasm.calibration.v1` — **GATED**;
- `aasm.source.trust.v1` — **GATED**;
- `aasm.execution.environment.v1` and qualification level — **NEXT**;
- `aasm.observation.lifecycle.v1` — **QUEUED**;
- `aasm.observation.fusion.v1` — **QUEUED**;
- `aasm.artifact.revision.v1` — **QUEUED under `aasm/artifact-lineage`**;
- `aasm.entity.evolution.v1` — **QUEUED under `aasm/artifact-lineage`**.

TextPCB qualification must exercise project/artifact revisions, stable requirement/net/component/entity references, generated board/CAD artifacts, stale DRC/ERC or solver feedback, ambiguous entity evolution, and out-of-band external changes without copying TextPCB project truth into AASM.

Embedded/physical qualification must exercise reboot epochs, out-of-order receipt, local causal sequence, clock quality/uncertainty, identity changes, calibration state, stale/uncalibrated observations, source-trust changes, and environment/qualification changes without allowing transport metadata or proximity to hardware to mint authority.

Portable constraint active in U4: all new IDs, enumerations, causal references, revisions, fingerprints, bounded integers, and state transitions must have canonical language-independent representations suitable for the future machine/kernel IR.

**Gates:** `aasm/physical-evidence`, `aasm/identity-calibration-trust`, `aasm/artifact-lineage`.

### U5 — Engineering Semantics, Safety, Risk, and Uncertainty

Required contracts/seams:

- `aasm.quantity.v1` including unit/tolerance/quantization/uncertainty semantics;
- `aasm.rule.v1` including hard-floor/hard/policy/preference/advisory and waiver/precedence semantics;
- semantic projection/equivalence;
- uncertainty/scenario/trace-property semantics;
- degraded operation;
- risk/hazard envelope;
- effect irreversibility and evidence escalation;
- obligation phase taxonomy;
- continuous safety envelope + hybrid-state composition;
- generalized epistemic debt;
- manual override with exact provenance.

TextPCB qualification must exercise dimensions/units, manufacturing/design rules, DRC/ERC constraints, operating scenarios, artifact tolerances, waiver provenance, and multi-fidelity electrical/thermal/mechanical evidence without turning AASM into a CAD/physics solver.

Portable constraint active in U5: canonical quantitative representation and invariant classification must identify what can be statically represented, what remains a dynamic kernel guard, and what remains empirical Evidence.

**Gates:** `aasm/engineering-semantics`, `aasm/safety-governance`.

### U6 — Governed Refinement, Experiments, Verification Planning, and Knowledge Application

Required contracts/seams:

- `aasm.refinement.proposal.v1`;
- `aasm.refinement.loop.v1`;
- `aasm.experiment.v1`;
- `aasm.verification.plan.v1`;
- `aasm.verification.debt.v1`;
- generic knowledge applicability/application;
- integrated core/conflict explanation pipeline;
- anti-loop/no-progress/oscillation/inconclusive semantics.

The evaluator may produce Evidence and `ProblemDelta` proposals. It never applies its own delta.

TextPCB is the principal refinement consumer: DRC/ERC, SPICE, EM, thermal, mechanical, manufacturability, external measurements, and artifact feedback become heterogeneous evaluators feeding one generic `solve -> verify -> diagnose -> propose -> authorize -> revise -> re-solve` architecture. No SPICE/EM/TextPCB special case enters the kernel.

The portable kernel later carries refinement/evidence/revision references and obligations; it does not run LLMs, solvers, CAD, SPICE, or physics itself.

**Gate:** `aasm/refinement`.

### U7 — Portable Machine IR, Kernel Boundary, and Machine Compiler

Portability becomes an executable contract here, but its constraints have already shaped U3-U6.

Required contracts:

- `aasm.invariant.v1` with `REPRESENTATIONAL | STATIC_PROTOCOL | DYNAMIC_KERNEL | EMPIRICAL`;
- `aasm.machine.ir.v1`;
- `aasm.transition.timing.v1`;
- `aasm.kernel.portable.v1`;
- canonical wire/serialization/identity rules;
- proof-carrying generated configuration package;
- deterministic trace/fingerprint corpus;
- Python reference interpreter/compiler for the portable subset.

The portable kernel contains IDs, states, events, transitions, guards, authority/capability refs, obligations, resource/effect refs, Evidence refs, conflicts, revisions, timing requirements, and canonical hashes. It must not require Python object identity, filesystem, SQL, network, an LLM, OS process identity, or host wall clock as truth.

A representative TextPCB supervisory machine must compile to the same generic machine IR used by non-TextPCB fixtures. That proves TextPCB pressure improved the generic kernel rather than contaminating it.

**Gate:** `aasm/portable-kernel`.

### U8 — Rust `std` Reference Kernel

Implement **only the frozen portable kernel**, not a broad port of the Python package.

Required work:

- Rust data/contract representation for the portable subset;
- canonical serialization/fingerprints identical to Python reference vectors;
- deterministic reducer/transition execution;
- authority/capability/reference checking required by the portable kernel;
- trace replay;
- property/adversarial tests;
- Python <-> Rust differential replay.

Rust typestate may make the statically provable subset of illegal transitions unrepresentable, but the generated typestate API is derived from `aasm.machine.ir.v1`; it does not become a second transition definition.

**Gate:** `aasm/rust-kernel`.

### U9 — Rust `no_std`, Bounded Runtime, Executor Traits, and Real-Time Profile

Required work:

- `no_std` kernel profile;
- bounded journal, queues, storage, and deterministic overflow behavior;
- bounded/static allocation profile where required;
- semantic executor/observer traits independent of transport brand;
- interrupt/event bridge with boot epoch + monotonic sequence;
- transition timing/deadline semantics;
- optional RTIC or equivalent backend after generic timing semantics;
- quarantined/explicit unsafe-code policy if hardware integration requires it;
- proof/configuration package identity and firmware/config rollout pattern.

Transports such as CAN, EtherCAT, GPIO/PWM, serial, REST gateways, or HIL adapters bind to semantic executor traits. They do not define AASM semantics.

**Gate:** `aasm/embedded-conformance`.

### U10 — Engineering and Physical Qualification

Run identical governed semantics through increasing evidence environments:

`MODEL -> SIMULATION -> SIL -> HIL -> BENCH -> CONTROLLED_PHYSICAL -> OPERATIONAL`.

Evidence authority may increase only through explicit environment/identity/calibration/verification policy, never because an adapter is closer to hardware.

Two principal conformance consumers:

1. a generic embedded/physical reference machine exercising authority, bounded effects, stale commands, timing, partitions, reboot epochs, degraded modes, safety envelopes, and postcondition verification;
2. the TextPCB adapter exercising requirements, artifact/entity lineage, quantities/rules, heterogeneous solvers/verifiers, refinement, alternative search, artifact generation, external project-state transitions, and deterministic readiness explanations.

**Gates:** `aasm/textpcb-conformance`, `aasm/embedded-conformance`, `aasm/readiness`.

### U11 — Permanent Stress Corpus and Hosted-Foundation Review

Permanent adversarial coverage includes forged lineage, stale revisions, stale authority epochs, expired/revoked capabilities, forged/uncalibrated observations, simulation-as-physical laundering, sensor/solver consensus laundering, command ACK without achievement, out-of-band transitions, network partition/reconnect, UNKNOWN effects, resource exhaustion, irreversible actions with inadequate evidence, poisoned knowledge, refinement self-authorization/no-progress/oscillation, artifact tampering, quantity/rule attacks, manual override without authority, portable serialization drift, Python/Rust trace divergence, bounded-queue overflow, reboot-epoch replay attacks, and false readiness.

The hosted-foundation review succeeds only if a private hosted fabric can consume these public semantics without inventing another truth, authority, resource, effect, revision, refinement, history, or machine-control system.

## Immediate builder queue

1. **U4/S3 execution environment:** implement `aasm.execution.environment.v1` with explicit `MODEL | SIMULATION | SIL | HIL | BENCH | CONTROLLED_PHYSICAL | OPERATIONAL` qualification levels, exact environment/configuration identity, problem/external revisions, and Evidence lineage. Environment proximity to hardware must never mint authority.
2. Add environment laundering attacks to `aasm/physical-evidence`: simulation presented as bench/physical, wrong environment revision/configuration, mismatched source identity/calibration/trust, stale environment evidence, and deterministic replay.
3. Implement `aasm.observation.lifecycle.v1` over existing observations/Evidence with explicit `RAW -> NORMALIZED -> CALIBRATED -> DERIVED -> FUSED -> VALIDATED` lineage plus rejected/superseded/stale/disputed outcomes.
4. Implement `aasm.observation.fusion.v1` as explicit derivation over source observation IDs/fingerprints; fusion never votes truth or creates FactAuthority.
5. Implement artifact revision and entity-evolution contracts under the separate cumulative `aasm/artifact-lineage` gate.
6. Continue applying canonical portable identity/serialization/bounded-integer rules to every U4 object so later Rust does not require contract redesign.
7. Proceed to U5 engineering quantity/rule/safety/uncertainty semantics with TextPCB engineering fixtures and explicit portable invariant classification.
8. Implement U6 `RefinementLoop`/Experiment/VerificationPlan/KnowledgeApplication using existing `ProblemDelta`, Evidence, scoped authority, resources, obligations, effects, and semantic dependencies.
9. Freeze U7 portable machine/kernel contracts and differential vectors before writing the broad Rust kernel.
10. Implement U8 Rust `std`, qualify against Python traces, then U9 `no_std`/real-time/executor profiles.
11. Complete TextPCB + embedded qualification and permanent stress corpus before claiming vertically complete engineering/physical conformance.

## Future capability milestones

Future capability names above are architecture/program identities only. They do not reserve package versions.

## Release discipline

No milestone above automatically changes package SemVer. A package release occurs only when a coherent selected scope is intentionally frozen and every required exact-head gate for that scope is green. Published tags/releases remain immutable.
