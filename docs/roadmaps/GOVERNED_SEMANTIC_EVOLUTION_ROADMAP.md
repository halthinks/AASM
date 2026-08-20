# AASM Governed Semantic Evolution — Unified Engineering and Portable Kernel Roadmap

**Date:** August 2026
**Latest immutable release:** v0.56.0
**Current development package:** 0.56.1
**Architecture status:** active governed-semantic evolution program

This roadmap is the canonical dependency-ordered implementation plan for evolving AASM from its existing governed reasoning/execution substrate into a domain-neutral supervisory-control kernel with typed engineering semantics, refinement/verification loops, a portable machine contract, and later independent Rust implementations.

Package SemVer and public-adoption-contract versions are independent. A public semantic contract can advance without falsely publishing a new immutable package release.

---

# 1. Architectural invariants

AASM remains a governed reasoning and supervisory-control kernel over authoritative external state machines, typed engineering artifacts, heterogeneous solvers, and verification/refinement loops, with a portable deterministic subset suitable for independent runtime implementations and embedded execution.

The following remain non-negotiable:

- one canonical truth/admission path;
- one scoped authority system;
- one resource-governance plane;
- one Effect lifecycle;
- one ProblemRevision system;
- one knowledge/admission plane;
- one semantic dependency graph;
- Evidence does not mint truth or authority;
- information cannot hitchhike authority;
- command success is not achievement;
- resource scarcity cannot weaken hard semantics;
- unsupported semantics fail closed or require explicit translation/approximation;
- applicability is revision-bound;
- durable identity is language/runtime independent;
- Rust typestate may strengthen but never redefine machine legality;
- invisible mutable configuration is forbidden;
- every public capability has an explicit claim ceiling and gate;
- known desired product outcomes constrain contracts now rather than being deferred to an architectural memory hole.

---

# 2. Dependency graph

```text
S0 state/fact authority                         DONE
S1 external machine supervision/postconditions DONE
S2 physical authority + Effect boundary         DONE
S3 physical evidence / identity / execution / observation / artifact / entity lineage
                                                DONE / GATED
S4 engineering semantics, safety, risk, uncertainty
    4.1 Quantity                                GATED
    4.2 Rule                                    GATED
    4.3 Semantic Projection / Equivalence       GATED
    4.4 Uncertainty / Scenario / Trace Property GATED
    4.5 Degraded Operation                      FOUNDATION GATED; PUBLIC PROMOTION IN QUALIFICATION
    4.6 Risk / Irreversibility                  FOUNDATION IMPLEMENTED; QUALIFICATION ACTIVE
    4.7 Obligation phases                       FOUNDATION GATED; PRE-ADMISSION
    4.8 Safety envelope / hybrid state             FOUNDATION GATED; PRE-ADMISSION
    4.9 Epistemic debt / manual override            FOUNDATION IMPLEMENTED; QUALIFICATION ACTIVE
S5 governed refinement / experiments / verification planning / knowledge application
S6 portable machine IR / kernel contract
S7 Rust std reference kernel
S8 Rust no_std / real-time kernel
S9 qualification continuum
S10 permanent stress corpus / production search expansion
S11 hosted-foundation review
```

The rest of this document gives the normative requirements for the active and upcoming stages. Earlier S0–S3 implementation details remain preserved in source, schemas, tests, release contracts, and their independent qualification gates.

---

# 3. S3 — Physical Evidence and Engineering Artifact Reality

**Status: GATED.**

The S3 implementation has already landed the physical-authority/effect boundary, causal/freshness semantics, physical identity/calibration/source trust, execution environment, observation lifecycle/fusion, artifact revision lineage, and entity evolution.

Core S3 contracts include:

- `aasm.state.conflict.v1`
- `aasm.event.causality.v1`
- `aasm.observation.freshness.v1`
- `aasm.physical.identity.v1`
- `aasm.calibration.v1`
- `aasm.source.trust.v1`
- `aasm.execution.environment.v1`
- `aasm.observation.lifecycle.v1`
- `aasm.observation.fusion.v1`
- `aasm.artifact.revision.v1`
- `aasm.entity.evolution.v1`

Artifact existence/generation does not imply authoritative acceptance. Entity evolution never silently rewrites historical identity. Ambiguous mappings fail closed for hard automatic reuse. Existing Evidence/event replay remains the durable substrate; no current-artifact/current-entity truth table was introduced.

---

# 4. S4 — Engineering Semantics, Safety, Risk and Uncertainty

**Status: ACTIVE.**

S4 adds explicit engineering and safety semantics without creating parallel authority, truth, objective, resource, artifact, or Effect systems.

## 4.1 Quantity/unit/tolerance semantics

**Status: GATED under `aasm/engineering-quantity`; public semantic IR, runtime engine-state admission remains `PRE_ADMISSION_ONLY`.**

Contract: `aasm.quantity.v1`.

Quantity provides exact integer/rational/canonical-decimal values, interval/measured representations, explicit dimensions, exact affine unit bindings, tolerance, quantization, source precision, provenance, and deterministic canonical projection. Binary floating-point durable identity and hidden mutable unit registries are forbidden.

Solver `aasm.numeric.tolerance.v1` and `EffectCapability.NumericInterval` remain distinct and unchanged unless an explicit later translation/admission contract says otherwise.

## 4.2 Rule applicability and precedence

**Status: GATED under `aasm/engineering-rule`; public semantic IR, runtime engine-state admission remains `PRE_ADMISSION_ONLY`.**

Contract: `aasm.rule.v1`.

Strength classes:

`HARD_FLOOR | HARD | POLICY | PREFERENCE | ADVISORY`

Rule precedence is not objective priority. A lower objective score cannot override a hard floor. Precedence does not authorize override. Source EngineeringRules and formal-calculus `LearnedConstraint(HARD|SOFT)` objects remain distinct; there is no implicit rule-to-constraint lowering.

## 4.3 Semantic projection/equivalence

**Status: GATED. Qualified public adoption parent: 0.32.18; runtime admission remains `PRE_ADMISSION_ONLY`.**

Contracts:

- `aasm.semantic.projection.v1`
- `aasm.semantic.equivalence.v1`
- `aasm.invariant.v1`

The contract distinguishes exact identity, projection-relative equivalence, non-equivalence, indeterminate/unsupported comparison, and lossless versus explicitly lossy projection. Projection/equivalence never mints truth, FactAuthority, EffectAuthority, artifact acceptance, entity identity authority, proof, objective preference, or reuse admission.

Invariant classes:

`REPRESENTATIONAL | STATIC_PROTOCOL | DYNAMIC_KERNEL | EMPIRICAL`

Representational/static equivalence never pretends to prove a dynamic-kernel or empirical invariant.

## 4.4 Uncertainty/scenarios/trace properties

**Status: GATED. Qualified public adoption parent: 0.32.19; runtime admission remains `PRE_ADMISSION_ONLY`.**

Contracts:

- `aasm.uncertainty.v1`
- `aasm.scenario.v1`
- `aasm.trace-property.v1`
- `aasm.trace-property.assessment.v1`

Uncertainty forms:

`EXACT | INTERVAL | SCENARIOS | DISTRIBUTION_REFERENCE | EMPIRICAL_SAMPLES | UNKNOWN_BOUNDED | UNKNOWN_UNBOUNDED`

Uncertainty reuses Quantity/Scenario/external-reference semantics; it is not solver numeric tolerance and it does not infer probability from confidence. Scenario is an explicit hypothetical/parametric context, not a ProblemRevision, Evidence record, solver run, or hidden current scenario. TraceProperty reuses the authoritative existing `aasm.trace.v1` durable event projection and requires explicit trace completeness for decisive evaluation. Temporal requirements remain dynamic-kernel properties rather than being silently lowered into static constraints.

## 4.5 Degraded autonomy

**Status: FOUNDATION GATED under `aasm/engineering-degraded-operation`; 0.32.20 additive public promotion is being qualified. Runtime admission remains `PRE_ADMISSION_ONLY`.**

Target/implemented contract:

- `aasm.degraded.operation.v1`
- `aasm.degraded.operation.assessment.v1`

Modes:

`FULL_OPERATION | DEGRADED_OPERATION | LOCAL_ONLY | SAFE_HOLD | RETURN_TO_SAFE_STATE | EMERGENCY`

The foundation is a revision-bound policy and pure assessment over an exact existing `EffectCapability`. It does not introduce a second operational state machine, authority evaluator, Effect lifecycle, dispatcher, resource plane, or current-mode store.

Mandatory semantics:

- mode selection may only preserve or reduce an exact existing EffectCapability operation set;
- `FULL_OPERATION` requires every declared dependency to be explicitly `AVAILABLE`;
- `LOCAL_ONLY` forbids remote dependencies but creates no local authority;
- unknown dependencies, overlapping selection rules, and unmatched dependency states fail closed to `SAFE_HOLD` with no new effects;
- `SAFE_HOLD` is a policy label for no new effects, not empirical proof of physical safety;
- `RETURN_TO_SAFE_STATE` and `EMERGENCY` are recovery intents only;
- emergency status never creates or expands authority;
- existing AuthorityDomain/AuthorityLease/epoch/revocation, point-of-use Effect authorization/dispatch, TaskLease/resource governance, UNKNOWN/reconciliation, and postcondition verification remain authoritative;
- a degraded-operation assessment is neither authorization nor a reusable authorization token and does not activate a mode or prove capability liveness.

## 4.6 Risk and irreversibility

**Status: FOUNDATION IMPLEMENTED; dedicated qualification active. Public/runtime admission remains `PRE_ADMISSION_ONLY` until independently qualified.**

Targets/implemented contracts:

- `aasm.risk.envelope.v1`
- `aasm.effect.irreversibility.v1`
- `aasm.risk.assessment.v1`

The foundation deliberately reuses `aasm.rule.v1` for hard-hazard legality instead of creating a second hard-floor vocabulary. A `PROHIBITED` hazard must bind an exact existing `EngineeringRule` whose strength is `HARD_FLOOR`.

Risk is not resource or monetary cost and is not collapsed into a scalar objective. Objective improvement and provider/resource scarcity cannot override a present or unknown hard hazard. Hazard observations are explicit Evidence-referenced policy inputs; they do not mint FactAuthority.

Irreversibility classes:

`REVERSIBLE | CONDITIONALLY_REVERSIBLE | COSTLY_TO_REVERSE | IRREVERSIBLE | UNKNOWN`

An explicit monotonic assurance policy maps irreversibility to:

`BASELINE | ELEVATED | STRONG | MAXIMUM`

`UNKNOWN` irreversibility requires `MAXIMUM` assurance. Stronger assurance never waives a present hard hazard. Explicit risk acceptance is a requirement signal only; this foundation performs no waiver, authority grant, objective/resource override, artifact acceptance, or empirical safety proof.

The dedicated foundation must fail closed on forged Rule fingerprints, unknown hard hazards, incomplete hazard observations, revision/subject mismatch, non-monotonic assurance policies, binary-float identity metadata, and false recovery claims for irreversible effects.

## 4.7 Obligation phases

**Status: FOUNDATION GATED under `aasm/engineering-obligation-phase`; public/runtime admission remains `PRE_ADMISSION_ONLY`.**

Extend the existing obligation graph with explicit phases:

`PRE_AUTHORIZE | PRE_DISPATCH | POST_DISPATCH | POST_OBSERVE | POST_VERIFY | RECOVERY`

This must extend the existing obligation graph rather than create a second lifecycle/verification queue.

## 4.8 Safety envelope/hybrid state

**Status: FOUNDATION GATED under `aasm/engineering-safety-envelope-hybrid-state`; public/runtime admission remains `PRE_ADMISSION_ONLY`.**

Targets:

- `aasm.safety.envelope.v1`
- `aasm.hybrid.state.v1`

Bind discrete modes to observed continuous quantities and external solver/evidence references. AASM does not become an ODE/physics solver.

## 4.9 Epistemic debt and manual override

**Status: FOUNDATION IMPLEMENTED; dedicated qualification active. Public/runtime admission remains `PRE_ADMISSION_ONLY`.**

Targets:

- `aasm.epistemic.debt.v1`
- `aasm.manual.override.v1`

Debt is a deterministic, revision-bound projection of the exact existing calculus obligations and `REQUIRES` edges; there is no second debt graph, store, lifecycle, scalar score, or forgiveness switch. Verified/committed obligations leave the projection, while terminal unresolved obligations remain visible.

Override records principal, exact Rule revision/fingerprint and scope, explicit logical-clock duration, exact accepted RiskAssessment, exact scoped-authority reference and evidence, and exact resulting existing obligations. `HARD_FLOOR` remains unconditionally non-overridable. An assessment is review eligibility only: it performs no waiver, authorization, Rule/obligation mutation, current-override activation, Effect dispatch, or history deletion.

## 4.10 TextPCB S4 fixtures

**Status: PERMANENT CORPUS IMPLEMENTED; aggregate qualification active under `aasm/safety-governance`.**

Permanent fixture requirements include:

- dimensional mismatch;
- trace/width/clearance/manufacturing rules;
- DRC/ERC hard rules vs preferences;
- controlled waiver provenance;
- thermal/power/signal scenario differences;
- tolerance/quantization handling;
- production alternative equivalence/diversity;
- degraded-operation dependency loss without authority amplification;
- UNKNOWN degraded state failing closed;
- present/unknown hard hazard dominating optimization and resource scarcity;
- irreversible-operation assurance escalation;
- hard hazard/evidence floor not relaxed by solver/resource scarcity.

**Current S4 gates:** `aasm/engineering-quantity`, `aasm/engineering-rule`, `aasm/engineering-semantic-projection`, `aasm/engineering-semantic-projection-public`, `aasm/engineering-uncertainty-scenario-trace`, `aasm/engineering-uncertainty-scenario-trace-public`, `aasm/engineering-degraded-operation`, `aasm/engineering-degraded-operation-public` (public promotion qualification), `aasm/engineering-s4`.
**Next seam:** S5.7 portable boundary after implemented and qualified S5.1-S5.6 foundations.
**Aggregate safety gate:** `aasm/safety-governance` (permanent TextPCB corpus implemented; qualification active).

---

# 5. S5 — Governed Refinement, Experiments, Verification Planning and Knowledge Application

## 5.1 Refinement proposal/loop

Targets:

- `aasm.refinement.proposal.v1`
- `aasm.refinement.loop.v1`

Generic loop:

`solve -> verify -> diagnose -> propose -> validate applicability -> authorize -> ProblemDelta -> ProblemRevision -> invalidate affected work -> replan/re-solve/re-verify`.

The evaluator that discovers an issue cannot directly apply its own delta.

Termination includes:

`GOAL_SATISFIED | NO_PROGRESS | OSCILLATION | RESOURCE_EXHAUSTED | INCONCLUSIVE | CONFLICT | MANUAL_HOLD`.

## 5.2 Experiment contract

Target: `aasm.experiment.v1`.

Bind hypothesis, controlled variables, measured variables, procedure, environment, fixture/calibration identity, expected discriminating result, evidence floor, resources, safety/risk constraints and problem revision.

Experiment selection may optimize expected information gain/uncertainty reduction under hard safety/evidence/resource constraints. Selection is proposal-only.

## 5.3 Verification plan/debt

Targets:

- `aasm.verification.plan.v1`
- `aasm.verification.debt.v1`

Verifier capability declares fidelity, evidence grade, cost/resources, environment, numerical policy, soundness/completeness claims and cache/reuse eligibility.

Verification debt is a projection from required obligations vs applicable evidence, not a second truth plane.

## 5.4 Knowledge applicability/application

**Status: FOUNDATION IMPLEMENTED AND QUALIFIED; durable pre-admission runtime active under `aasm/knowledge-applicability`. Public admission remains `PRE_ADMISSION_ONLY`.**

Generalize the semantic/performance firewall:

- semantic knowledge stays inert until target-local validation;
- performance knowledge can affect search/routing but not legality;
- application requires explicit authority;
- applicability cannot broaden itself;
- superseded revision invalidates applicability unless independently preserved.

## 5.5 Integrated core/conflict pipeline

**Status: FOUNDATION IMPLEMENTED AND QUALIFIED under `aasm/core-conflict`; backend-independent pre-admission pipeline active. Public admission remains `PRE_ADMISSION_ONLY`.**

Preserve external references through raw -> normalized -> reduced -> independently rechecked cores/conflicts. The qualified contract distinguishes backend-reported, conflict-preserving, irreducible, minimum-cardinality, minimum-weight, and budget-limited partial claims without inferring one proof class from another. Irreducibility requires independent removal rechecks; minimum-cardinality and minimum-weight require their own explicit certificates.

## 5.6 TextPCB refinement qualification

**Status: QUALIFICATION IMPLEMENTED AND PASSED under `aasm/textpcb-refinement`; `QUALIFICATION_ONLY_NO_RUNTIME_SURFACE`.**

TextPCB consumes the generic S5.1 `RefinementLoop` for DRC/ERC, SPICE, EM, thermal/PDN, mechanical/manufacturing checks, external measurements, and artifact/tool feedback. Evaluators return typed Evidence/counterexamples/diagnoses and optional ordinary `RefinementProposal` objects; none directly mutates canonical truth, accepts artifacts, dispatches effects, or bypasses existing scoped refinement authority.

S5.6 is pinned to the permanent S4 TextPCB safety corpus and requires both `aasm/refinement` and `aasm/safety-governance` semantics to remain intact.

Generic architecture:

`DESIGN -> VERIFY -> BUILD/GENERATE -> OPERATE/OBSERVE -> LEARN -> REDESIGN`

## 5.7 Portable boundary

The future portable kernel carries refinement IDs/revisions/Evidence refs/obligations/state transitions. It does not embed LLMs, solvers, CAD, SPICE, EM or physics engines.

**Gate:** `aasm/refinement`.

---

# 6. S6 — Portable Machine IR and Kernel Boundary

This stage freezes semantics another runtime may implement. It does **not** translate the whole Python codebase.

## 6.1 Invariant taxonomy

Finalize `aasm.invariant.v1` with:

- `REPRESENTATIONAL`
- `STATIC_PROTOCOL`
- `DYNAMIC_KERNEL`
- `EMPIRICAL`

## 6.2 Machine IR

Target: `aasm.machine.ir.v1`.

Portable machine definition includes machine/profile identity, states, events, transitions, structural legality, static capability requirements, dynamic guards, required Evidence refs, authority references, obligations/conflicts, revision bindings, and deterministic error semantics.

## 6.3 Timing semantics

Target: `aasm.transition.timing.v1`.

Timing must use explicit clocks/epochs/sequences/bounds. Host wall clock is never hidden universal truth.

## 6.4 Portable kernel contract

Target: `aasm.kernel.portable.v1`.

Freeze canonical language-independent serialization/hashing, deterministic reducer behavior, stable errors, proof-carrying configuration, replay fingerprints, and Python-oracle differential vectors.

---

# 7. S7 — Rust `std` Reference Kernel

Implement the portable data model, canonical serialization/fingerprints equal to Python, deterministic reducer, guard/reference checks, authority/capability refs, obligations/conflicts, replay, and stable errors.

Rust typestate may be generated from Machine IR only where it preserves exactly the legal machine. Python/Rust differential conformance is mandatory.

---

# 8. S8 — Rust `no_std` + Real-Time Execution

Add bounded queues/counts/journals/storage, explicit overflow/fail-closed semantics, protocol/vendor-independent observer/executor/artifact-producer traits, device/node identity + boot epoch + sequence interrupt/event bridge, explicit event loss, and a governed rollout machine.

CAN/EtherCAT/GPIO/PWM/serial/REST/sim/HIL remain adapters behind traits. RTIC integration follows stabilized timing semantics. Unsafe code is avoided by default and independently justified where unavoidable.

---

# 9. S9 — Qualification Continuum

Qualify the same semantic contracts across:

`MODEL -> SIMULATION -> SIL -> HIL -> BENCH -> CONTROLLED_PHYSICAL -> OPERATIONAL`

No level automatically implies truth or authority. Evidence applicability is explicit.

---

# 10. S10 — Permanent Stress Corpus and Production Search Expansion

Maintain adversarial/domain fixtures covering revision races, stale/ambiguous Evidence, authority expiry/preemption, resource exhaustion, effect UNKNOWN/reconciliation, artifact/entity ambiguity, semantic projection loss, uncertainty/scenario misuse, degraded-mode authority laundering, hard-hazard/objective conflict, irreversibility assurance, and Python/Rust differential traces.

---

# 11. S11 — Hosted-Foundation Review

Hosted/multi-tenant fabric may remain private, but public code must preserve stable tenant/principal scoping, authority/capability/resource seams, portable IDs, and export/replay contracts so future hosting does not require rewriting the kernel.

---

# 12. Immediate execution order

1. Finish exact `0.32.20` degraded-operation public qualification and parent/cumulative release-chain repair without runtime admission.
2. Qualify the landed S4.6 Risk/Irreversibility foundation under an independent gate.
3. If S4.6 foundation is green, design its additive public semantic-IR promotion while preserving `aasm.rule.v1` HARD_FLOOR and existing authority/resource/objective planes.
4. Proceed to S4.7 Obligation Phases by extending the existing obligation graph rather than creating a second lifecycle.
5. Continue through S4.8–S4.9 safety semantics before freezing S6 portable machine/kernel contracts.
6. Only then begin the Rust `std` reference kernel; follow with `no_std`/real-time after differential identity/timing semantics are frozen.

No known desired outcome is architecturally deferred. Implementation depth may be staged; compatibility with the intended end state may not be.
