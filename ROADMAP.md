# AASM Roadmap

AASM's latest immutable public release is **v0.56.0 — Truthful Solver Outcomes + Governed Semantic Evolution + Engineering Mathematical IR**.

**Current development package on `main`:** `0.56.1`  
**Current active adoption contract:** `aasm.adoption.v1 / 0.32.17`  
**Qualified development boundary:** PR-1, PR-2, complete PR-3 / PHY-01, complete S3 reality/artifact/entity semantics, plus the S4 `aasm.quantity.v1` and `aasm.rule.v1` public semantic foundations  
**Exact qualified S4 Rule code boundary before documentation-only synchronization:** `7c808fc504fa91edb8fe9af13f12568b745f9762` — all 29 current custom qualification contexts green  
**Immediate unfinished boundary:** **S4.3 — semantic projection/equivalence: one explicit, versioned meaning of “same/equivalent,” with no implicit “same enough”**

Package SemVer is not an architecture-progress counter. Exact unreleased identity is the Git SHA. Future capabilities below are milestone identities, not reserved package versions. See [`docs/VERSIONING.md`](docs/VERSIONING.md).

## Canonical direction

AASM is being built as a **governed reasoning and supervisory-control kernel over authoritative external state machines, typed engineering artifacts, heterogeneous solvers, verification/refinement loops, and a portable deterministic kernel that can be implemented in Python, Rust `std`, and constrained Rust `no_std` profiles without changing the governing semantics**.

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
9. **Revision-bound applicability.** Solver, verifier, artifact, external-machine, calibration, observation, refinement, quantity, rule, and learned results bind to exact applicable revisions/environments.
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
- **S3 execution environment:** explicit `MODEL | SIMULATION | SIL | HIL | BENCH | CONTROLLED_PHYSICAL | OPERATIONAL` evidence context with exact identity/revision binding; levels are labels, not ordinal truth/authority ranks; simulation cannot silently satisfy a physical evidence requirement.
- **S3 observation lifecycle/fusion:** append-only `RAW -> NORMALIZED -> CALIBRATED -> DERIVED -> VALIDATED` processing lineage plus fusion/disposition Evidence; exact source fingerprints, explicit calibration/environment/freshness references, no stage skips, no consensus voting, and no authority/admission by a `VALIDATED` label.
- **S3 artifact revision lineage:** backend-independent immutable revision identity over content/semantic hashes and provenance, exact parent ID+fingerprint lineage, separate storage-binding fingerprint, Evidence-backed replay, and no hidden current-artifact or acceptance authority.
- **S3 entity evolution:** exact predecessor/successor representation binding across `UNCHANGED | MODIFIED | GENERATED | SPLIT | MERGED | REPLACED | DELETED | AMBIGUOUS`; ambiguity is durable and fail-closed for hard automatic reuse; no current-entity truth table or authority minting.
- **S4 engineering quantity/unit/tolerance foundation:** `aasm.quantity.v1` exact integer/rational/canonical-decimal/interval/measured representations, canonical dimension vectors, exact affine source-to-canonical unit transforms, explicit tolerance/quantization/rounding/source precision/uncertainty/provenance, deterministic fingerprints, and fail-closed dimensional compatibility. It is qualified as public semantic IR while runtime engine-state admission remains `PRE_ADMISSION_ONLY`.
- **S4 engineering Rule applicability/precedence foundation:** `aasm.rule.v1` stable rule/clause/source-authority/external-reference identity; portable tri-state applicability; exact problem/external revision applicability; `HARD_FLOOR | HARD | POLICY | PREFERENCE | ADVISORY` strength; explicit precedence, specificity, priority and waiver/override structural policy; deterministic fingerprints; and fail-closed separation from `LearnedConstraint(HARD|SOFT)`. It is qualified as public semantic IR while runtime engine-state admission remains `PRE_ADMISSION_ONLY`.

PR-3H preserves the existing scoped `effect.authorize`, resource reservations, Worker/TaskLease path, durable `EffectOwnership`, dispatch, `UNKNOWN`, and reconciliation. A prior capability-use validation record remains Evidence only and cannot become a reusable bearer token.

Quantity likewise preserves existing semantics rather than shadow-redefining them: `aasm.numeric.tolerance.v1` remains the existing solver tolerance-policy contract and `EffectCapability` retains its existing `NumericInterval` behavior until an explicit later quantity integration contract is qualified.

Rule preserves existing semantics rather than creating another policy or constraint engine: it adds no engine methods/state, no current-rule registry, no authority evaluator, no implicit waiver/override authorization, and no automatic lowering into the formal conflict-learning calculus.

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
        |       execution/qualification environment ------------- GATED
        |       observation lifecycle/fusion -------------------- GATED
        |       artifact revision/entity evolution -------------- GATED
        |
        v
U4/S3 Reality identity + time + artifact lineage + observation epistemics -- GATED
        |
        v
U5/S4 Engineering semantics + safety + uncertainty ------------- ACTIVE
        |       quantity/unit/tolerance semantic foundation ------ GATED
        |       rule applicability/precedence -------------------- GATED
        |       semantic projection/equivalence ----------------- NEXT
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

PR-3H is implemented in the active `AASMEngine` and qualified at exact head `b910549677ec6f84a32e39ad625c131f68d4348c` together with all inherited release-required contexts. The complete PR-3 / PHY-01 program remains qualified on the later cumulative boundaries through `7c808fc504fa91edb8fe9af13f12568b745f9762`.

A bounded physical effect is rechecked at authorization and execution against the current authority domain/lease identity, lease fingerprint/holder, authority epoch, capability identity/fingerprint and revocation generation, operation/bounds, workspace/scope/subject, problem/external revisions, and current validity time. An earlier `EffectCapabilityUse` validation remains Evidence only.

The integration reuses the existing v0.54 `EffectIntent`, scoped `effect.authorize`, TaskLease/resource governance, durable `EffectOwnership`, dispatch, `UNKNOWN`, and reconciliation pathways. It introduces no second dispatcher, effect store, lifecycle, resource ledger, or authority evaluator.

**Gate:** `aasm/physical-effect-integration` — GATED.

### U4 — Reality Identity, Time, Artifact Lineage, and Observation Epistemics

**Status: GATED.**

Current exact cumulative qualification boundary: `7c808fc504fa91edb8fe9af13f12568b745f9762`, adoption `0.32.17`, with all 29 current custom contexts green.

This merged the old external-machine artifact/entity work with the physical/distributed evidence program without creating another truth, artifact, entity, or authority plane.

Qualified contracts/seams include:

- `aasm.state.conflict.v1` / expectation violation — **GATED**;
- `aasm.event.causality.v1` — **GATED**;
- `aasm.observation.freshness.v1` — **GATED**;
- `aasm.physical.identity.v1` — **GATED**;
- `aasm.calibration.v1` — **GATED**;
- `aasm.source.trust.v1` — **GATED**;
- `aasm.execution.environment.v1` and qualification level — **GATED**;
- `aasm.observation.lifecycle.v1` — **GATED**;
- `aasm.observation.fusion.v1` — **GATED**;
- `aasm.artifact.revision.v1` / `aasm.artifact-lineage.runtime.v1` — **GATED**;
- `aasm.entity.evolution.v1` / `aasm.entity-evolution.runtime.v1` — **GATED**.

TextPCB qualification exercises project/artifact revisions, stable requirement/net/component/entity references, generated board/CAD artifacts, stale DRC/ERC or solver feedback, ambiguous entity evolution, and out-of-band external changes without copying TextPCB project truth into AASM.

Embedded/physical qualification exercises reboot epochs, out-of-order receipt, local causal sequence, clock quality/uncertainty, identity changes, calibration state, stale/uncalibrated observations, source-trust changes, environment/qualification changes, and multi-source processing without allowing transport metadata, processing labels, consensus, or proximity to hardware to mint authority.

Portable constraints remain active: all IDs, enumerations, causal references, revisions, fingerprints, bounded integers, and state transitions use canonical language-independent representations suitable for the future machine/kernel IR.

**Gates:** `aasm/physical-evidence`, `aasm/identity-calibration-trust`, `aasm/execution-environment`, `aasm/observation-epistemics`, `aasm/artifact-lineage`, `aasm/entity-evolution` — GATED.

### U5 — Engineering Semantics, Safety, Risk, and Uncertainty

**Status: ACTIVE.**

Current qualified seams:

- `aasm.quantity.v1` — **GATED / PUBLIC SEMANTIC IR** under `aasm/engineering-quantity`.
- `aasm.rule.v1` — **GATED / PUBLIC SEMANTIC IR** under `aasm/engineering-rule`.

Quantity defines exact integer/rational/canonical-decimal/interval/measured/estimated values; explicit dimension vectors; exact affine source/canonical unit binding; absolute/relative/asymmetric tolerance; quantization/grid and rounding; source precision; uncertainty reference; provenance; canonical projection; and deterministic fingerprints. Dimensional inconsistency fails closed.

Its public admission does **not** imply runtime integration. The active engine does not gain Quantity state, a unit registry, or new truth/effect authority. Existing solver `aasm.numeric.tolerance.v1` and `EffectCapability.NumericInterval` semantics remain unchanged until an explicit later translation/admission contract is qualified.

Rule defines stable rule/revision/clause/source-authority identity, exact external references, explicit applicability context/predicate, workspace/scope/subject selection, exact problem/external revision applicability, explicit strength/severity/precedence/specificity/priority, and structural waiver/override eligibility. `HARD_FLOOR` cannot be waived or overridden by the Rule model. Precedence never authorizes override. Structural eligibility never replaces existing scoped authorization.

Rule public admission likewise does **not** imply runtime integration. The active engine gains no Rule state or methods, no parallel registry or authority evaluator, and no implicit lowering into `LearnedConstraint(HARD|SOFT)`.

**Next seam: semantic projection/equivalence.** Required semantics:

- one explicit versioned projection/equivalence object instead of ad hoc “same enough” decisions;
- exact projection identity, source object type/contract identity, target semantic view, and revision/applicability binding;
- distinction between exact identity, equivalence under a declared projection, non-equivalence, and indeterminate/unsupported comparison;
- explicit preservation/loss claims so projection cannot silently discard hard semantics;
- deterministic canonical representation and fingerprints suitable for Python/Rust differential vectors;
- reuse across solution pools/top-K/diversity, cache/reuse, cross-provider comparison, artifact comparison, and TextPCB alternative design identity;
- no truth, authority, acceptance, or objective preference from equivalence by itself.

Remaining U5 seams:

- uncertainty/scenario/trace-property semantics;
- degraded operation;
- risk/hazard envelope;
- effect irreversibility and evidence escalation;
- obligation phase taxonomy;
- continuous safety envelope + hybrid-state composition;
- generalized epistemic debt;
- manual override with exact provenance.

TextPCB qualification must exercise dimensions/units, manufacturing/design rules, DRC/ERC constraints, operating scenarios, artifact tolerances, waiver provenance, and multi-fidelity electrical/thermal/mechanical evidence without turning AASM into a CAD/physics solver.

Portable constraint active in U5: canonical quantitative/rule/projection representation and invariant classification must identify what can be statically represented, what remains a dynamic kernel guard, and what remains empirical Evidence.

**Current gates:** `aasm/engineering-quantity`, `aasm/engineering-rule` — GATED.  
**Planned U5 aggregate gates:** `aasm/engineering-semantics`, `aasm/safety-governance`.

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

The portable kernel later carries refinement-related IDs/revisions/Evidence refs/obligations/state transitions. It does not run LLMs, solvers, CAD, SPICE, EM or physics engines.

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

1. **U5/S4.3 semantic projection/equivalence:** reconcile the existing narrow projections/fingerprints used by solution pools, reuse, solver/formulation comparison, artifacts, and semantic evolution; define one explicit generic projection/equivalence contract without creating a second truth or cache plane.
2. Define exact comparison outcomes and claim ceilings: identity is not equivalence; equivalence is always relative to an explicit projection; projection loss must be declared; unsupported or semantically lossy comparisons fail closed or remain indeterminate.
3. Add strict portable schema/data model, canonical ordering/fingerprints, adversarial projection-loss/revision/type-mismatch/forged-fingerprint fixtures, and a dedicated qualification gate before public admission.
4. Introduce the `aasm.invariant.v1` classification seam during S4 design (`REPRESENTATIONAL | STATIC_PROTOCOL | DYNAMIC_KERNEL | EMPIRICAL`) so the new projection contract explicitly states what equivalence can and cannot prove across future Python/Rust implementations.
5. Preserve Rule as public but runtime-pre-admission; do not create a current Rule registry, waiver/override authority path, or implicit Rule→`LearnedConstraint` lowering.
6. Keep Quantity public but runtime-pre-admission while designing explicit translation seams for later EffectCapability/postcondition/solver use; do not silently replace `aasm.numeric.tolerance.v1` or `NumericInterval`.
7. Add TextPCB-derived alternative-design/artifact equivalence fixtures only as conformance pressure; TextPCB identity/domain classes remain outside the kernel.
8. Continue U5 uncertainty/scenario/trace-property, degraded operation, risk/irreversibility, obligation phases, safety envelopes, and override/debt semantics after projection/equivalence qualifies.
9. Implement U6 `RefinementLoop`/Experiment/VerificationPlan/KnowledgeApplication using existing `ProblemDelta`, Evidence, scoped authority, resources, obligations, effects, and semantic dependencies.
10. Freeze U7 portable machine/kernel contracts and differential vectors before writing the broad Rust kernel.
11. Implement U8 Rust `std`, qualify against Python traces, then U9 `no_std`/real-time/executor profiles.
12. Complete TextPCB + embedded qualification and the permanent stress corpus before claiming vertically complete engineering/physical conformance.

## Future capability milestones

Future capability names above are architecture/program identities only. They do not reserve package versions.

## Release discipline

No milestone above automatically changes package SemVer. A package release occurs only when a coherent selected scope is intentionally frozen and every required exact-head gate for that scope is green. Published tags/releases remain immutable.
