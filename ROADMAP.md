# AASM Roadmap

AASM's latest immutable public release is **v0.56.0 — Truthful Solver Outcomes + Governed Semantic Evolution + Engineering Mathematical IR**.

`main` currently carries the already-established **0.56.1 next-release target** for Execution Profiles + Runtime Provenance. That target is development state, not a released claim, until the applicable exact-head qualification gates pass. Exact unreleased source identity is the Git commit SHA.

AASM no longer allocates a new package SemVer to every architecture milestone. See [`docs/VERSIONING.md`](docs/VERSIONING.md). Future architecture is tracked by named capability milestones; package versions are assigned only at a deliberate release boundary.

The roadmap is explicitly **product-backward**: known destination properties shape public contracts before implementation depth makes them expensive to add. A capability may be staged, but it may not be deferred in a way that makes the current architecture structurally incompatible with it.

## Canonical direction

AASM is being built toward **governed semantic evolution**: a public deterministic governance/runtime substrate that can supervise authoritative external state machines, evolve explicit problem revisions from evidence, preserve stable requirement/artifact lineage, reuse applicability-scoped knowledge, choose evidence acquisition under governed resources, and remain replayable without hosted-only truth.

Canonical implementation sources:

- [`docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`](docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md) — architecture, contracts, invariants, and TextPCB/general engineering boundary;
- [`docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`](docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md) — complete work packages, dependencies, release sequence, and acceptance gates;
- [`docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md`](docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md) — live implementation status;
- [`docs/source_material/SOURCE_LOCK_MANIFEST.md`](docs/source_material/SOURCE_LOCK_MANIFEST.md) — locked source hashes, baseline commit, source precedence, and no-drift rules.

## Permanent public invariants

1. **Scoped identity:** Principal / Workspace / Scope / Machine remain distinguishable.
2. **Scoped authority:** cross-scope access fails closed; authority and resource rights are separate.
3. **Proposal/commit boundary:** models, adapters, humans, solvers, verifiers, imported knowledge, and external machines may propose/observe; legal runtime transitions commit.
4. **One truth path:** no parallel truth store, hidden hosted state, or direct domain/tool mutation path may bypass AASM admission semantics.
5. **Resource capacity:** owned, purchased, subscription, rolling, weekly, credit, compute, storage, worker, solver, expert-model, human-review, and custom capacity share governed resource semantics.
6. **Protected reserve:** remaining capacity may be intentionally unavailable to ordinary work.
7. **Resource policy cannot weaken hard semantics:** scarcity changes strategy, never hard requirements or required evidence grade.
8. **Lease/reservation before consumption:** resource availability never grants authority; authority never grants unlimited resources.
9. **Reconciliation:** estimated and actual consumption remain distinct and durable.
10. **Effect ownership:** external effects require authorization, idempotency/ownership, and explicit UNKNOWN reconciliation.
11. **Revision-bound applicability:** solver, verifier, artifact, and external-machine results apply to an exact problem/external revision; superseded results remain historical Evidence only unless independently revalidated.
12. **Stable external lineage:** external requirements and decisions must remain traceable through generated variables, constraints, objectives, cores, no-goods, bounds, results, certificates, artifacts, and explanations.
13. **No silent unsupported lowering:** exact, translated, approximate, verifier-only, and unsupported model features must remain distinguishable and fail closed when a required feature cannot be preserved.
14. **Semantic/performance knowledge firewall:** performance hints cannot change semantic legality; correctness-sensitive knowledge requires applicability-scoped validation and explicit application authority.
15. **Portable history:** exported public history must be sufficient for deterministic reconstruction without hidden hosted tables.
16. **Profile identity:** profile/package binding is versioned and migrated explicitly.
17. **Scope-safe inspection:** observability cannot depend on single-tenant global views.
18. **No privileged hosted bypass:** hosted operator machines consume public runtime semantics rather than mutate around them.
19. **Cross-backend agreement never votes truth:** agreement is corroboration; contradiction is a first-class conflict; decisive claims require their documented evidence/proof level.
20. **Readiness is explainable and deterministic:** unresolved blocking obligations, stale evidence, UNKNOWN effects, conflicts, proof debt, or missing required verification block readiness.

## Released

- v0.35.0 Semantic Problem Model Foundations
- v0.36.0 Semantic Compiler SDK
- v0.37.0 Reasoning Artifacts and Epistemic Admission
- v0.38.0 Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- v0.39.0 Typed Capability ABI and Formal Verification Workers
- v0.40.0 Hierarchical Memory, Reasoning Frontier, and Context Projection
- v0.41.0 Domain-Neutral Solver Loop and Deterministic Reuse Plane
- v0.42.0 Reference Domains & Reuse/Memory/Reasoning Stress Tests
- v0.43.0 Semantic Conformance, Adversarial Domains, and Certification
- v0.44.0 Heterogeneous Optimization Solver Portfolio
- v0.45.0 Convex Optimization & Modeling Adapters
- v0.46.0 Advanced Solver Control & Search Artifacts
- v0.47.0 Governed Symbiotic Intelligence & Intelligence Economics
- v0.47.1 Apache-2.0 License Transition
- v0.48.0 Cross-Run Certified Knowledge & Governed Long-Term Memory
- v0.48.1 Project-Wide Apache-2.0 Policy Correction
- v0.49.0 Semantic Solver Release Candidate
- v0.50.0 Proof-Carrying Solver Claims
- v0.51.0 Governed Solution Pools & Complete Enumeration
- v0.52.0 Resource-Governed Multi-Objective Decisions & Pareto Solving
- v0.53.0 Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening
- v0.54.0 Certified Cross-Solver Exchange & Deterministic Portfolio Racing + Effect Ownership/UNKNOWN Recovery
- v0.55.0 Extended Mathematical IR + Portable Semantic Evolution Archive
- **v0.56.0 Truthful Solver Outcomes + Governed Semantic Evolution + Engineering Mathematical IR — latest immutable release**

## Future capability milestones

Future milestones below are architecture/dependency identities, **not reserved package versions**. Several milestones may ship together. Completing one does not automatically increment package SemVer.

### Active next-release scope — Execution Profiles + Runtime Provenance

Milestone ID: `execution-profiles-runtime-provenance`

This work is already associated with the existing 0.56.1 development target on `main`. Do not create another package version merely because subsequent architecture work begins.

Primary goals:

- named solver/execution profiles;
- evidence-grade runtime provenance and reproducibility certification;
- provider-specific execution/provenance mappings;
- effective configuration recorded from adapter observation rather than caller assertion;
- exact distinction between provenance and reproducibility claims;
- cumulative compatibility with released v0.56 solver-outcome semantics.

Hard completion criterion:

> Runtime claims cannot exceed their observed execution configuration and provenance evidence, and the exact-head release/compatibility/formal gates pass for the selected release scope.

### External Machine Supervision + Artifact/Entity Lineage

Milestone ID: `external-machine-supervision`

Primary goals:

- `aasm.machine.binding.v1`;
- revision-safe external transition specifications compiled through existing EffectIntent/Ownership/Reconciliation;
- external post-state observation and out-of-band change handling;
- immutable artifact revisions;
- semantic/tool entity evolution including explicit ambiguity;
- stale-result fencing and cancellation for superseded revisions.

Hard completion criterion:

> AASM can supervise an authoritative external state machine without copying its truth, bypassing effect ownership, or accepting stale/out-of-band state as if it were the requested transition result.

### Governed Refinement + Problem Deltas + Verification Planning

Milestone ID: `governed-refinement-verification-planning`

Primary goals:

- typed refinement proposals;
- solve/verify/diagnose/refine/admit/revise/replan loop;
- no direct verifier/solver model mutation;
- existing semantic dependency truth maintenance used for impact/staleness;
- anti-loop/no-progress/inconclusive semantics;
- multi-fidelity verifier capability declarations;
- resource-aware verification planning through existing scheduler/effect/resource paths;
- deterministic verification-debt projection.

Hard completion criterion:

> Evidence can drive a new canonical problem revision only through explicit applicability validation and existing authority/admission boundaries, while unaffected verified work is preserved and stale work is fenced.

### Engineering Semantics + Production Alternative Search

Milestone ID: `engineering-semantics-production-search`

Primary goals:

- engineering quantity/unit/tolerance/quantization semantics;
- scoped rule applicability/precedence/waiver semantics;
- semantic projection/equivalence;
- production sequential lexicographic solving;
- truthful exact/partial/approximate Pareto solving;
- general integer no-goods, ranked top-K, near-optimal and diverse pools;
- expanded SAT/LP/MILP proof/checker support only where the provider/toolchain genuinely supports the claim.

Exact finite v0.51/v0.52 engines remain qualification oracles for scalable implementations on tractable fixtures.

### Uncertainty, Scenarios, Temporal Properties, Readiness, and Engineering Conformance

Milestone ID: `uncertainty-readiness-conformance`

Primary goals:

- exact/interval/scenario/distribution-reference/empirical/unknown uncertainty;
- operating scenarios and modes;
- temporal trace properties;
- deterministic `aasm.readiness.gate.v1`;
- generic engineering adapter conformance;
- TextPCB adapter qualification as a consumer of generic AASM semantics, never as kernel logic.

Hard completion criterion:

> TextPCB can use AASM as a supervisory control/reasoning layer with stable lineage, revision-aware verification, governed refinement, truthful solver claims, artifact/effect recovery, and explainable readiness without making AASM a second TextPCB Project Truth.

### Permanent Cross-Capability Stress Corpus

Milestone ID: `cross-capability-stress-corpus`

Coverage includes forged lineage/revisions, stale solver/verifier/machine results, poisoned reusable knowledge, performance hints attempting semantic mutation, unsupported/dropped solver lowering, false statuses/proofs/completeness, tolerance abuse, core-minimization overclaim, duplicate/UNKNOWN external effects, out-of-band changes, ambiguous entity evolution, artifact tampering, quantity/rule attacks, refinement self-authorization/no-progress, resource scarcity attempting to weaken hard evidence, and false readiness.

This corpus exists to qualify the architecture actually required rather than to force a package release merely because the corpus grows.

### Semantic Solver Contract Review + Hosted-Foundation Review

Milestone ID: `hosted-foundation-review`

This is the architectural reassessment previously assigned a future package number. It occurs only after governed semantic evolution is substantially real.

Hard completion criterion:

> A private hosted AASM fabric could be implemented entirely as a consumer of public contracts without introducing a second truth, authority, resource, effect, history, revision, refinement, decision-routing, or machine-control system.

## Beyond the current milestone set

Further public hardening may continue around provider telemetry, resource-estimate learning, richer scarcity forecasting, profile migration, formal models for semantic evolution, larger engineering conformance corpora, portable deterministic kernels, machine compilation, embedded execution profiles, and hosted-fabric operational concerns. Those additions must preserve the same public authority and replay boundaries.

A future package version is assigned only when a coherent release scope is deliberately frozen and qualified.
