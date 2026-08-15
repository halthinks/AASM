# AASM Governed Semantic Evolution — Canonical Roadmap and Builder Execution Plan

**Date:** 2026-08-15  
**Baseline:** AASM v0.54.0  
**Baseline commit:** `e7322e0827009e094c849ca8a3b218534f41b924`  
**Status:** Canonical post-v0.54 implementation roadmap  
**Companion architecture:** `docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`

---

## 1. Mission

Build AASM into a public, deterministic, evidence-governed semantic-evolution substrate capable of supervising authoritative external state machines such as TextPCB while improving AASM's general usefulness for CAD, PCB/EDA, CAE, robotics, manufacturing, complex software systems, and other long-lived engineering workflows.

The roadmap is product-backward. Known required outcomes constrain present public seams. Capabilities may be implemented in stages, but no stage may knowingly establish an architecture structurally incompatible with the destination.

---

## 2. Permanent execution rules

1. One canonical event/reducer/state authority path.
2. No second scheduler, resource ledger, effect lifecycle, knowledge truth store, or hosted-only truth system.
3. External tools/solvers/verifiers propose or observe; they never directly become truth.
4. Every correctness-sensitive reusable artifact is applicability-scoped and locally validated before application.
5. Performance-only knowledge cannot alter semantic legality.
6. All long-running results are bound to problem/artifact/external-machine revisions and are fenced when stale.
7. Resource scarcity can change strategy, never hard semantics or required evidence grade.
8. Every release claim maps to a reproducible gate.
9. Exact finite reference engines remain qualification oracles for scalable implementations where applicable.
10. TextPCB remains a qualification consumer and adapter; no TextPCB types enter the AASM kernel.

---

## 3. Baseline reconciliation at v0.54

### Already delivered and reused

- semantic problem/reasoning artifacts;
- dependency truth maintenance;
- typed capability ABI;
- formal verification workers;
- hierarchical memory/context;
- reuse plane;
- heterogeneous optimization providers;
- advanced optimization controls;
- governed SII/economics;
- cross-run knowledge;
- semantic solver RC/certification;
- proof-carrying solver claims;
- complete finite solution pools;
- exact finite lexicographic/Pareto semantics;
- governed capacity/quota/resource routing;
- scoped identity/authority/store;
- durable solver learning/application;
- effect intent/dispatch/ownership/UNKNOWN recovery;
- actual resource settlement;
- certified exact solver translation;
- deterministic proof-aware portfolios;
- certified cross-solver learned-state exchange.

### Still required

- stable external-reference lineage through generated solver artifacts;
- first-class problem revision and delta contracts;
- generalized formulation/capability negotiation;
- normalized solver outcome v2;
- evidence-grade runtime provenance/reproducibility;
- real solver-core minimization pipeline;
- generic knowledge applicability/application;
- machine binding and revision-safe external transition semantics;
- artifact revision and entity evolution;
- governed refinement loop;
- verifier capability/multi-fidelity planning/debt;
- production top-K/diverse/near-optimal pools;
- production lexicographic/Pareto truth levels;
- broader proof/checker support;
- quantities/rules/tolerances/units;
- uncertainty/scenario/temporal contracts;
- deterministic readiness gates;
- generic engineering conformance and TextPCB qualification.

---

# v0.55 — Extended IR + Portable Semantic Evolution Archive

## Goal

Ensure that the next generation of AASM identity and mathematical semantics is structurally representable before later refinement/external-machine features deepen the codebase.

## Work package 55.1 — External reference foundation

Add:

- `ExternalReference`;
- `ProblemRevision`;
- `ProblemDelta`;
- public schemas;
- deterministic fingerprints;
- revision/delta validation;
- source-lineage tests.

Acceptance:

- an external requirement ID can be carried without loss through a canonical object;
- revision and delta identity are deterministic;
- blank/ambiguous required identity fails closed;
- mismatched base revision fails;
- revision graph helper rejects self-parent and obvious duplicate/cycle conditions;
- schemas round-trip representative fixtures.

## Work package 55.2 — Model feature set and provider capability manifests

Add:

- `aasm.model.feature-set.v1`;
- `aasm.provider.capability-manifest.v1`;
- exact/translated/approximate/unsupported support levels;
- fail-closed model admission;
- explicit decomposition/approximation requirement.

Acceptance:

- unsupported feature admission fails before provider execution;
- approximate translations cannot masquerade as exact;
- provider capability fingerprint is attached to formulation/provenance.

## Work package 55.3 — Generalized solver formulation artifact

Generalize v0.54 translation into a formulation artifact preserving variable, constraint, objective, and external-reference mappings; transformation rules; scaling/tolerances; source/target fingerprints; provider capability manifest; and independent checker result.

Acceptance:

- dropped variable/constraint/objective/reference is detected;
- unsupported transformation fails closed;
- v0.54 identity translation remains valid as the simplest exact case.

## Work package 55.4 — Shared objective-vector IR

Unify semantic optimization objectives and solver objectives without collapsing them into fixed weights.

Required fields include objective ID/external reference, priority, sense, tolerance, hard floor/threshold where applicable, provenance, semantic meaning, and solver expression mapping.

Acceptance:

- true sequential lexicographic semantics remain possible;
- resource policy objectives remain separate from domain engineering objectives;
- no objective can override a hard floor.

## Work package 55.5 — Portable semantic-evolution archive v1

Extend the planned portable archive to include structural slots for external references, problem revisions/deltas, feature/capability/formulation artifacts, solver runtime provenance references, artifact revisions, machine bindings/observations, knowledge applicability/application, refinement history, verification plans/debt, and readiness explanations.

Some referenced object types may be empty/not yet active in v0.55, but the archive manifest must not require a breaking redesign when they arrive.

Acceptance:

- export/import reconstructs the same canonical observable state for implemented fields;
- integrity manifest detects tampering;
- no private hosted state is needed for replay.

## v0.55 release gate

`aasm/v55` must check contracts, schemas, archive round-trip, source lineage, feature admission, formulation identity, and existing regression suites.

---

# v0.56 — Truthful Solver Evidence + Governed Knowledge Application

## Goal

Make solver and reusable-knowledge inputs strong enough to support later refinement without overstating what any provider or artifact proves.

## Work package 56.1 — Normalized solver outcome v2

Add orthogonal fields for termination, incumbent, bound, proof, evidence grade, raw provider status/code, mapping rule/version, diagnostics, and provenance. Maintain a compatibility projection to the old status vocabulary, but make v2 the authoritative detailed result for new features.

Acceptance includes time/node/memory/user-cancel/numerical/model-invalid/provider-unavailable/unsupported/stale outcomes.

## Work package 56.2 — Execution profiles and runtime provenance

Add `aasm.solver.execution-profile.v1`, `aasm.solver.runtime-provenance.v1`, effective options capture, library/adapter/platform identity, worker/thread count, tolerance policy, deterministic controls, and environment/formulation/problem fingerprints.

Provider-specific fixtures: CaDiCaL/PySAT where available, OR-Tools CP-SAT, HiGHS, CVXPY-supported backends.

## Work package 56.3 — Reproducibility certification

Define semantic/assignment/objective/proof/byte equivalence levels and certify only tested levels.

## Work package 56.4 — Governed knowledge applicability/application

Generalize v0.53 solver-learning discipline to arbitrary existing reasoning/cross-run/reuse artifacts.

Acceptance:

- semantic and performance classes are enforced;
- imported semantic knowledge remains inert until target-local validation;
- application requires explicit authority;
- narrow applicability cannot broaden itself;
- superseded revision invalidates applicability unless independently preserved.

## Work package 56.5 — Core/conflict pipeline

Integrate conflict minimization into real solver explanation paths and return raw, irreducible, minimum/minimum-weight when completed, and explicitly partial cores when budget-limited. Preserve external references through formulation mappings.

## v0.56 release gate

Provider-specific status fixtures, deterministic-profile fixtures, reproducibility fixtures, knowledge-poisoning tests, core-minimization oracles, and backward-compatibility tests.

---

# v0.57 — External Machine Supervision + Artifact/Entity Lineage

## Goal

Allow AASM to supervise TextPCB and other authoritative external state machines without duplicating their truth and without weakening v0.54 effect ownership.

## Work package 57.1 — Machine binding

Add `aasm.machine.binding.v1` with external identity, protocol/contract version, observed revision/fingerprint, transition capability catalog, observer/executor identity, authority requirements, and environment identity.

## Work package 57.2 — Transition specification over EffectIntent

Add `aasm.machine.transition.v1` that compiles/binds into existing v0.54 EffectIntent/Dispatch/Ownership/Reconciliation.

Acceptance:

- stale expected external revision rejects before dispatch;
- no external call before durable ownership;
- idempotency survives retry;
- UNKNOWN blocks dependent transition/readiness until reconciliation.

## Work package 57.3 — External state observation

Add revision/fingerprint-bound post-state observation and out-of-band-change handling. Out-of-band external changes produce Evidence and invalidate dependent current assumptions; they are not overwritten.

## Work package 57.4 — Artifact revision lineage

Add stable logical artifact/revision IDs, content/semantic hashes, parent lineage, producer/effect/machine/problem revision, external refs, and tool/schema identity.

## Work package 57.5 — Entity evolution

Add explicit semantic/tool identity mapping and `UNCHANGED | MODIFIED | GENERATED | SPLIT | MERGED | REPLACED | DELETED | AMBIGUOUS` relations. Hard reuse fails across ambiguous mapping.

## Work package 57.6 — Stale-result fencing and cancellation

Every long-running external/solver/verifier task carries revision/problem/artifact/environment fingerprints. Superseded results are retained as historical Evidence and prevented from current promotion.

## v0.57 release gate

Crash/retry/out-of-band-state fixtures, stale external revision attacks, artifact tamper tests, ambiguous entity evolution tests, and a TextPCB mock-machine conformance fixture.

---

# v0.58 — Governed Refinement + Problem Deltas + Verification Planning

## Goal

Implement the full governed solve/verify/learn/revise loop over the existing authority, evidence, dependency, resource, effect, and worker systems.

## Work package 58.1 — Refinement proposals

Add typed refinement proposal kinds for no-goods, bounds, constraints, domain restriction, objective/model correction, scenario addition, required observation, and verification escalation.

## Work package 58.2 — Refinement admission and problem revision materialization

Pipeline:

`Evidence/Counterexample -> diagnosis -> RefinementProposal -> applicability check -> independent validation -> scoped authorization -> ProblemDelta -> ProblemRevision`

No verifier or solver gets direct model mutation authority.

## Work package 58.3 — Dependency-driven continuation

Use existing truth maintenance to stale affected descendants, reopen affected obligations, preserve unrelated siblings, and invalidate stale machine/solver/verifier work.

## Work package 58.4 — Anti-loop/progress policy

Add deterministic limits for repeated refinements, identical refinements, no-progress cycles, and resource/budget exhaustion. Exhaustion produces `INCONCLUSIVE`/blocking obligation, never fabricated completion.

## Work package 58.5 — Verifier capability and verification plans

Extend verifier capability metadata with fidelity, evidence grade, cost/resource demand, environment, numerical policy, soundness/completeness declarations, and cache/reuse eligibility. VerificationPlan remains a governed plan executed through existing workers/effects/resources.

## Work package 58.6 — Verification debt projection

Compute blocking/nonblocking debt from obligations versus current applicable evidence. Readiness cannot ignore unresolved blocking debt.

## v0.58 release gate

Reference CEGAR-style finite fixture, external verifier counterexample fixture, stale-result attack, invalid refinement attack, no-progress loop fixture, resource-exhaustion/inconclusive fixture, and crash/replay tests.

---

# v0.59 — Engineering Semantics + Production Alternative Search

## Goal

Make AASM practical for substantial CAD/PCB/CAE optimization rather than relying only on exact finite reference algorithms.

## Work package 59.1 — Quantity/unit/tolerance semantics

Add `aasm.quantity.v1` and dimensional validation, canonical units, tolerance, quantization/grid, rounding, source precision, uncertainty, and provenance.

## Work package 59.2 — Rule applicability/precedence

Add `aasm.rule.v1` with scope, applicability, priority, specificity, strength, waiver/override, severity, authority, and revision applicability.

## Work package 59.3 — Semantic projection/equivalence

Add semantic projection and equivalence contracts used by pools, cache/reuse, cross-provider comparison, artifact comparison, and engineering alternative diversity.

## Work package 59.4 — Production lexicographic solving

Sequentially solve objective stages through provider capabilities while preserving prior-stage optima within declared tolerance. Verify results against canonical semantics.

## Work package 59.5 — Production Pareto solving

Support exact finite, bounded partial, and approximate frontier modes with truthful completeness labels and progress/cursor state.

## Work package 59.6 — Scalable pools/top-K/diversity

Add general integer no-goods, ranked top-K, near-optimal pools, semantic diversity, restartable cursors, and provider-native generation paths.

## Work package 59.7 — Proof/checker expansion

SAT proof transport/checking where genuine; LP feasible/infeasible/unbounded/optimality certificates where genuine; MIP claim levels separated by evidence support.

## v0.59 release gate

Exact finite oracles must qualify scalable implementations on tractable fixtures; larger provider-specific fixtures validate partial/top-K/diversity/provenance semantics.

---

# v0.60 — Uncertainty, Scenarios, Temporal Properties, Readiness, and Engineering Conformance

## Goal

Complete the generic engineering-control semantic layer required for TextPCB qualification.

## Work package 60.1 — Uncertainty

Implement exact/interval/scenario/distribution-reference/empirical/unknown-bounded/unknown-unbounded uncertainty semantics.

## Work package 60.2 — Scenarios and operating modes

Bind constraints/obligations/verifiers to operating scenarios and environment assumptions.

## Work package 60.3 — Temporal trace properties

Represent startup, shutdown, transient, sequence, and state-history requirements.

## Work package 60.4 — Readiness gates

Add deterministic `aasm.readiness.gate.v1` over obligations, evidence grades, stale state, waivers, proof state, unresolved UNKNOWN effects, verification debt, conflicts, external machine state, and profile/domain conformance.

## Work package 60.5 — Generic engineering adapter conformance

Create an engineering conformance profile over existing adapter conformance covering references, quantities, rules, revisions, artifacts, external machines, verifier semantics, refinement, and readiness.

## Work package 60.6 — TextPCB qualification

Implement/qualify a TextPCB adapter against the generic profile without adding TextPCB kernel semantics. Acceptance includes realistic project-state transitions, requirement lineage, design-rule feedback, artifacts, optimization alternatives, external verification/refinement, and readiness explanation.

---

# v0.61 — Permanent Cross-Capability Stress Corpus

## Goal

Move the existing planned stress-corpus milestone until after the architecture it must certify exists.

Permanent adversarial coverage includes false external lineage; forged source revisions; revision-cycle attempts; stale solver/verifier/external-machine results; poisoned reusable semantic knowledge; performance hints attempting semantic mutation; invalid/dropped formulation mappings; unsupported feature lowering; false solver statuses; deterministic-profile drift; false proof/certificate claims; false solution-pool completeness; Pareto tolerance abuse; bad core-minimization claims; duplicate/out-of-order external effects; UNKNOWN outcome attacks; out-of-band external changes; ambiguous entity evolution; artifact hash mismatch; invalid quantity dimensions/tolerances; rule precedence/waiver attacks; refinement self-authorization; refinement loop/no-progress cases; resource scarcity attempting to weaken hard evidence; and false readiness.

Performance measurements remain environment-bound Evidence, never correctness claims.

---

# v0.62 — Semantic Solver RC2 + Hosted-Foundation Review

## Goal

Perform the subsystem/architecture reassessment only after the new semantic-evolution destination is substantially real.

Review one-truth-path compliance; archive/replay portability; external identity/revision lineage; solver outcome/provenance truthfulness; formulation/capability negotiation; knowledge applicability/application; external machine supervision; artifact/entity lineage; refinement/change impact; verifier planning/debt; engineering quantities/rules; solution pools/multi-objective production semantics; proof/checker strength; uncertainty/scenarios/temporal semantics; readiness; scope/authority/resource/effect integrity; and claim-to-gate coverage.

Hard completion criterion:

> A private hosted AASM fabric could be built as a consumer of the public contracts without introducing a second truth, authority, resource, effect, history, revision, refinement, decision-routing, or machine-control system.

---

## 4. Cross-release dependency graph

```text
ExternalReference ──────────────┐
ProblemRevision/Delta ──────────┼─> Refinement
ModelFeature/Capabilities ──────┼─> Formulation -> Truthful Solver Evidence
Runtime Provenance ─────────────┤
Knowledge Applicability ────────┤
Machine Binding ────────────────┼─> External Verification/State Feedback
Artifact/Entity Lineage ────────┤
Resources/Authority/Effects ────┤ (already exist)
Semantic Dependencies ──────────┤ (already exist)
                                v
                   Verification Planning/Debt
                                |
                                v
                  Engineering Semantics/Search
                                |
                                v
                     Readiness/Conformance
```

---

## 5. Canonical implementation ledger format

Every roadmap item must be tracked with these fields:

`ID | release | capability | current status | source requirement | code/contracts | dependencies | acceptance test | adversarial test | claim ceiling | gate | notes`

Allowed status values:

- `SOURCE_LOCKED`
- `DESIGNED`
- `CONTRACT_LANDED`
- `RUNTIME_LANDED`
- `TESTED`
- `GATED`
- `RELEASED`
- `BLOCKED`

No item is considered complete because code exists. It is complete only when the acceptance/adversarial tests and release gate support the documented claim.

---

## 6. Initial execution sequence beginning now

### Tranche A — source lock and doctrine

1. Commit this roadmap.
2. Commit the companion whitepaper.
3. Commit the supplied TextPCB requirement sources as immutable source snapshots.
4. Commit the previous AASM × TextPCB research paper/handoff as source snapshots.
5. Commit a source-lock manifest with SHA-256 values and live baseline commit.
6. Update root `ROADMAP.md` to point to and summarize this canonical direction.

### Tranche B — v0.55 semantic identity foundation

1. Add `ExternalReference`.
2. Add `ProblemRevision`.
3. Add `ProblemDelta`.
4. Add deterministic fingerprint helpers/reuse existing semantic fingerprinting.
5. Add JSON schemas.
6. Add unit/adversarial tests.
7. Keep active package export on v0.54 until v0.55 release contract/gates are ready.

### Tranche C — v0.55 provider/formulation foundation

1. Model feature set.
2. Provider capability manifest.
3. Generalized formulation artifact.
4. v0.54 translation adapter compatibility.
5. fail-closed admission tests.

### Tranche D — v0.55 archive

Build portable archive around the now-known future object families rather than a narrow v0.54-only snapshot.

---

## 7. Builder stop conditions

The builder pauses a tranche only for a safety/security issue requiring product decision; an unavoidable backward-compatibility conflict with a released contract; evidence that the proposed design would create a second truth/authority/scheduler/effect system; or a source requirement contradiction that cannot be reconciled without changing the documented product destination.

Ordinary test failures, integration friction, schema mismatches, or missing small helper code are repair work, not stop conditions.

---

## 8. Completion rule

The program is successful when TextPCB can use AASM as a supervisory control/state machine with stable requirement/decision lineage; revision-aware solving and verification; explicit external transition authority; durable effect ownership and UNKNOWN recovery; artifact/entity lineage; truthful solver/proof/provenance semantics; governed reuse and refinement; multi-fidelity evidence planning; scalable alternative search; and deterministic readiness claims—while the same public AASM contracts remain generally useful outside TextPCB and no TextPCB-specific domain logic has entered the AASM kernel.
