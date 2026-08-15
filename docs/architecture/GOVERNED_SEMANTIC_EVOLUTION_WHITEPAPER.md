# AASM Governed Semantic Evolution

## Reconciled Architecture Whitepaper for TextPCB, CAD/PCB State Machines, External-Machine Supervision, and Demanding Engineering Workflows

**Date:** 2026-08-15  
**Baseline repository:** `halthinks/AASM`  
**Baseline release:** `v0.54.0`  
**Baseline commit evaluated:** `e7322e0827009e094c849ca8a3b218534f41b924`  
**Status:** Canonical implementation doctrine for the post-v0.54 roadmap  
**Primary qualification consumer:** TextPCB  
**Architecture scope:** General AASM public engine; no TextPCB logic in the kernel

---

## 1. Executive conclusion

AASM has crossed an important architectural threshold. It is no longer merely a durable state-machine runtime with solver integrations. By v0.54 it already has the foundations necessary for a substantially more powerful role:

- explicit semantic problems and reasoning artifacts;
- dependency-driven truth maintenance;
- typed capabilities and formal verification workers;
- governed memory and cross-run knowledge;
- proof-carrying solver claims;
- complete finite solution pools and certified multi-objective reasoning;
- resource governance, reservations, settlement, and scarcity-aware routing;
- scoped identity and authority;
- durable solver learning with local revalidation;
- effect intent, dispatch, ownership, UNKNOWN recovery, and external resource reconciliation;
- certified solver translation, deterministic solver portfolios, and cross-solver learned-state exchange.

The strongest next direction is therefore **not** to add a separate CAD subsystem, a separate self-improvement system, a second knowledge plane, or a second external-machine runtime.

The strongest direction is to make **governed semantic evolution** a native composition of the machinery AASM already owns.

Governed semantic evolution means:

> AASM can observe that an explicit problem, model, plan, external machine, artifact, or assumption is no longer adequate; produce a typed and attributable refinement proposal; validate its applicability and evidence; authorize or reject the proposal through existing policy/authority boundaries; commit a new canonical problem revision; invalidate only the affected dependent work; preserve valid unaffected work; and continue under the new revision without silently rewriting history or importing authority from the producer of the evidence.

This is the architecture required by TextPCB, but it is not TextPCB-specific. It generalizes to CAD, EDA, CAE, robotics, manufacturing, verification, software architecture, long-running scientific workflows, infrastructure, and any system where a durable controller must coordinate changing external state and progressively stronger evidence.

---

## 2. Source precedence and reconciliation rule

This paper reconciles four source classes:

1. **Live AASM `main` at the baseline commit.** Live code is authoritative for what already exists.
2. **AASM semantic-problem / semantic-solver source material.** These define the architectural invariants: one authority path, one canonical durable history, explicit proposal/commit boundaries, no alternate truth store, deterministic admission, dependency-aware invalidation, and fail-closed semantics.
3. **TextPCB AASM requirements and builder gap-closure sources.** These define the integration pressure from a real substantial engineering system and enumerate solver, provenance, identity, verification, enumeration, and external feedback requirements.
4. **The prior AASM × TextPCB CAD/PCB research paper and handoff.** These expand the integration problem into state-machine composition, artifact lineage, topology identity, quantities, rule semantics, hybrid reasoning, refinement, verifier planning, incremental revisions, uncertainty, scenarios, equivalence, resources, concurrency, and readiness.

Where earlier planning assumed a capability was absent but v0.52-v0.54 has since implemented it, this paper treats the live implementation as the stronger base and replaces the proposed duplicate mechanism with a generalization of the existing one.

---

## 3. The non-negotiable architectural doctrine

The following rules govern every implementation tranche in this roadmap.

### 3.1 One truth path

AASM must continue to have one canonical admission/mutation path. Reasoners, solvers, external tools, LLMs, verifiers, imported knowledge, and hosted services may propose or observe. They do not directly become machine truth.

### 3.2 No second scheduler

New solver portfolios, verifier planning, refinement work, machine transitions, and engineering analyses must use the existing work allocation, TaskDemand/TaskLease, effect, resource, provider, worker, and execution paths where applicable.

### 3.3 No second effect lifecycle

v0.54 has already established:

`EffectIntent -> EffectDispatchRequest -> durable EffectOwnership -> external boundary -> EffectReconciliation`

External-machine transitions must compile into or bind to this lifecycle rather than creating a competing ownership/retry system.

### 3.4 No second knowledge store

Reasoning artifacts, Evidence, cross-run knowledge envelopes, hierarchical memory, solver-learning artifacts, reuse certificates, and semantic dependencies already provide the storage/admission substrate. New reusable knowledge semantics must classify and govern those artifacts, not create an unrelated truth database.

### 3.5 No silent semantic lowering

If a provider cannot faithfully represent a model feature, the model must be rejected, decomposed explicitly, approximated only under an explicit approximation contract, or routed elsewhere. Silent feature loss is forbidden.

### 3.6 Resources cannot weaken hard semantics

Quota, cost, expert-model scarcity, wall time, solver calls, GPU availability, or human-review capacity may change strategy. They may not silently convert a hard requirement into a soft preference or lower a required evidence grade.

### 3.7 Historical evidence is immutable; current applicability is revision-bound

A result produced for an old problem revision or external-machine revision remains historical Evidence. It does not remain current authority unless its applicability to the new revision is independently established.

---

## 4. What v0.54 already solved and must be reused

The new direction starts from strengths, not from a rewrite.

### 4.1 Epistemic artifacts and admission

AASM already represents Claims, Hypotheses, Lemmas, Invariants, Counterexamples, Definitions, Assumptions, Observations, Derivations, Refutations, and ObjectiveResults with producer identity, evidence, verifier requirements, confidence, scope, and explicit lifecycle states. Refinement observations should reuse this plane.

### 4.2 Semantic dependencies and truth maintenance

AASM already represents typed semantic dependency edges and can invalidate affected descendants while preserving unrelated siblings. Problem-revision transitions must feed this existing graph rather than create a second change-impact engine.

### 4.3 Cross-run knowledge

AASM already transports prior knowledge through envelopes that preserve source run/machine/scope, evidence/artifact references, environment fingerprints, dependency fingerprints, verification strength, privacy, retention, freshness, and applicability scopes while transferring no source authority. The new architecture should add more precise **applicability** and **application** contracts around these existing envelopes.

### 4.4 Solver learning

v0.53 already distinguishes correctness-sensitive learned artifacts (`NO_GOOD`, `UNSAT_CORE`, `BOUND`) from performance-only hints (`INCUMBENT`, `WARM_START`, `NATIVE_ACCELERATOR`), requires local revalidation, and separates validation from application. This semantic/performance firewall should become the generic reusable-knowledge rule for the rest of AASM.

### 4.5 Resource governance

v0.52 already models fixed, rolling, refilling, credit, unbounded, and unknown resource capacities; authoritative/observed/derived/estimated/declared observations; protected reserve; proposal demand; reservation; re-estimation; settlement; calibration; and lexicographic/Pareto routing over correctness/evidence/progress/cost/time/quota/scarcity. Verification and refinement should consume this plane directly.

### 4.6 Effect ownership and UNKNOWN recovery

v0.54 already binds external execution to an intent, worker, task lease, scoped authority evidence, workspace/scope, resource reservations, and durable ownership before the executor crosses the external boundary. Unknown outcomes are retry-blocked until explicit evidence-backed reconciliation. This is the correct substrate for controlling TextPCB and other external state machines.

### 4.7 Certified solver translation and portfolios

v0.54 already rejects fastest-wins, arrival-order correctness, and majority-vote semantics; revalidates results against the canonical model; and requires proof for decisive negative/optimal claims under the configured policy. Future cross-backend work should enrich formulation mappings and proof/capability metadata rather than create another portfolio mechanism.

---

## 5. The new architectural center: revision-bound semantic evolution

The central loop is:

```text
Canonical Problem Revision
        |
        +--> reasoning/search/optimization
        |
        +--> governed external effect or machine transition
        |
        v
Observation / Counterexample / Result / Artifact
        |
        v
Conflict explanation / causal dependency / verifier result
        |
        v
RefinementProposal
        |
   applicability + independent validation
        |
   scoped policy authorization
        |
        v
ProblemDelta
        |
        v
New ProblemRevision
        |
        v
semantic truth-maintenance invalidation
        |
        +--> preserve unaffected authority/evidence
        +--> mark affected work stale
        +--> fence superseded external results
        +--> replan / re-solve / re-verify
```

The critical design principle is that **the producer of the evidence cannot directly mutate the problem it is evaluating**. A verifier may produce a counterexample. A simulator may produce a violation. A solver may produce a core. An LLM may propose a model correction. An external machine may report a state change. None of those objects may directly edit canonical truth.

They enter the same governed proposal/admission path.

---

## 6. Foundational contract family

### 6.1 `aasm.external.reference.v1`

A stable lineage object that can bind external engineering/business requirement identity through every generated representation.

Minimum fields:

- `namespace`
- `external_id`
- `external_revision`
- `role`
- `semantic_entity_id`
- `source_fingerprint`
- `source_location`
- `metadata`

Required properties:

- immutable canonical fingerprint;
- namespace and ID cannot be blank;
- role is explicit rather than inferred from unstructured metadata;
- external revision may be absent only when the source is intrinsically immutable or explicitly revisionless;
- the object is transportable into constraints, variables, assumptions, objectives, cores, no-goods, bounds, certificates, results, effects, artifacts, and explanations.

This closes the current gap where internal IDs exist but stable source lineage is generally relegated to unconstrained metadata.

### 6.2 `aasm.problem.revision.v1`

A canonical identity for one explicit semantic world.

Minimum fields:

- `problem_id`
- `revision_id`
- `parent_revision_ids`
- `problem_fingerprint`
- `semantic_projection_fingerprint`
- `external_references`
- `environment_fingerprint`
- `dependency_fingerprints`
- `created_by`
- `created_from_delta_id`
- `metadata`

Required properties:

- revision graph is acyclic;
- content fingerprint is immutable;
- parent lineage is explicit;
- the revision is not itself authority; it is the identity of the materialized canonical problem state that was legally admitted.

### 6.3 `aasm.problem.delta.v1`

A deterministic description of revision change.

Minimum fields:

- `base_revision_id`
- `target_revision_id`
- added/removed/modified semantic refs;
- changed quantities/rules/objectives/scenarios/artifacts;
- invalidated/preserved evidence candidates;
- impacted obligations/solver objects;
- incremental/warm-start eligibility declaration;
- causal/refinement/evidence lineage;
- delta fingerprint.

A delta must never claim to preserve an artifact merely because the producer says so. Preservation is an applicability decision derived from dependency and identity checks.

---

## 7. Governed reusable knowledge: applicability and application, not a new knowledge store

### 7.1 `aasm.knowledge.applicability.v1`

This contract classifies whether an already-existing artifact may be considered for reuse under a particular target revision/environment.

Minimum semantics:

- referenced artifact/envelope/learning ID;
- knowledge class: `SEMANTIC` or `PERFORMANCE`;
- reuse scope: run-local, profile-local, domain-reusable, global-candidate;
- required subject/revision/environment/dependency fingerprints;
- external references;
- applicability predicate;
- required evidence/checker/certificate threshold;
- expiry, revocation, supersession;
- permitted application classes.

### 7.2 `aasm.knowledge.application.v1`

Application remains separate from validation.

For semantic knowledge, application may only occur through a legal semantic change path such as a certified new constraint, no-good, bound, rule, or problem delta.

For performance knowledge, application may change search order, warm starts, provider/routing preferences, resource estimates, context projection, or scheduling hints, but cannot change feasibility or truth.

### 7.3 Cross-run rule

Cross-run admission proves that an envelope is eligible to be considered locally. It does not prove the embedded knowledge is currently semantically applicable. The new applicability contract sits after transport/admission and before semantic application.

---

## 8. External-machine supervision built over v0.54 effects

### 8.1 `aasm.machine.binding.v1`

A machine binding describes an external authoritative state machine without copying its truth into AASM.

Minimum fields:

- binding ID;
- machine kind;
- external machine identity;
- contract/protocol version;
- current observed external revision;
- current observed state fingerprint;
- supported transition catalog/capability manifest;
- observer/read interface identity;
- executor/effect interface identity;
- authority requirements;
- environment identity;
- metadata.

### 8.2 `aasm.machine.transition.v1`

A machine transition is a semantic specification that compiles to an ordinary v0.54 `EffectIntent`.

Minimum fields:

- binding ID;
- transition ID;
- expected external revision;
- expected pre-state fingerprint;
- parameters;
- preconditions;
- expected postconditions;
- idempotency key;
- resource reservations;
- relevant problem revision;
- external references;
- metadata.

### 8.3 `aasm.machine.state-observation.v1`

A state observation binds:

- binding ID;
- observed revision;
- observed state fingerprint;
- observation source;
- environment/tool identity;
- evidence/artifact IDs;
- correlation to effect/ownership/reconciliation where applicable;
- observation time;
- metadata.

### 8.4 Acceptance rule

AASM may treat a requested transition as confirmed only when the expected pre-state was current, effect ownership was valid, the external receipt correlates to the exact effect, and post-state observation reconciles to the resulting revision/fingerprint.

Out-of-band external changes are not overwritten. They become observations that may trigger stale marking, dependency invalidation, and a new problem revision.

---

## 9. Artifact revision and entity evolution

### 9.1 `aasm.artifact.revision.v1`

Required fields:

- stable logical artifact ID;
- immutable artifact revision ID;
- content hash;
- semantic projection hash;
- parent revision IDs;
- producer/effect/machine binding IDs;
- source problem revision;
- format/schema/tool identity;
- external references;
- evidence IDs;
- metadata.

Failed artifacts may remain evidence. They do not become current authoritative artifacts merely because an external effect ran.

### 9.2 `aasm.entity.evolution.v1`

Required evolution relations:

- `UNCHANGED`
- `MODIFIED`
- `GENERATED`
- `SPLIT`
- `MERGED`
- `REPLACED`
- `DELETED`
- `AMBIGUOUS`

The contract must distinguish semantic identity from tool representation identity. Hard reusable knowledge that depends on an entity must fail closed across `AMBIGUOUS` evolution unless an independent mapping is later established.

This is essential for CAD topology but is equally useful for code symbols, netlist objects, dataset entities, manufacturing objects, and robotics world models.

---

## 10. Engineering quantities and rule semantics

### 10.1 `aasm.quantity.v1`

Required representations:

- exact integer;
- rational;
- canonical decimal;
- interval;
- measured/estimated value with uncertainty reference.

Required metadata:

- physical dimension;
- source unit and canonical unit;
- absolute/relative/asymmetric tolerance;
- quantization/grid;
- rounding rule;
- source precision;
- uncertainty;
- provenance/external reference.

Dimensional inconsistency must fail closed before solving or verification.

### 10.2 `aasm.rule.v1`

Required semantics:

- rule ID/external reference;
- applicability predicate;
- scope selector;
- priority;
- specificity;
- strength: `HARD_FLOOR | HARD | POLICY | PREFERENCE | ADVISORY`;
- override/waiver policy;
- severity;
- source authority;
- revision applicability.

Rule precedence is distinct from objective priority. A lower objective score cannot override a hard floor.

---

## 11. Model-feature and provider-capability negotiation

### 11.1 `aasm.model.feature-set.v1`

The model should declare the semantic features it requires, including at least:

- Boolean;
- bounded integer;
- linear real;
- cardinality;
- pseudo-Boolean;
- global scheduling;
- SMT theory;
- nonlinear continuous;
- conic;
- quadratic;
- geometric predicate;
- black-box verifier constraint;
- temporal trace property;
- robust/scenario constraint.

### 11.2 `aasm.provider.capability-manifest.v1`

A provider manifest must state support level per feature:

- exact native;
- exact translated;
- approximate translated;
- unsupported;
- verifier-only.

It also declares status/proof/provenance capabilities, deterministic-execution modes, solution-pool capabilities, incremental solving, warm starts, core/proof support, and versioned limits.

### 11.3 `aasm.solver.formulation.v1`

A formulation artifact binds one canonical problem/model to a provider representation and records:

- source revision/model fingerprint;
- target provider/family/version;
- variable map;
- constraint map;
- objective map;
- external-reference preservation;
- lowering/transformation rule IDs;
- scaling/tolerance/sense transformations;
- lowered model fingerprint;
- presolved model fingerprint where available;
- exact/approximate/unsupported feature declarations;
- capability-manifest fingerprint;
- independent checker/certificate.

v0.54 solver translation becomes the first narrow exact formulation implementation and is generalized through this contract rather than replaced.

---

## 12. Solver outcome truthfulness and runtime provenance

### 12.1 `aasm.solver.outcome.v2`

The current flat vocabulary is insufficient for evidence-grade engineering. Outcome must separate orthogonal facts:

- `termination_reason`;
- `incumbent_state`;
- `bound_state`;
- `proof_state`;
- `evidence_grade`;
- normalized status;
- raw provider status/code;
- status mapping rule/version;
- diagnostics;
- objective/bound/gap;
- check results;
- runtime provenance ID.

Termination reasons must distinguish at least:

- normal complete;
- feasible/optimal termination;
- infeasible/unbounded where supported;
- time limit;
- node/conflict/iteration limit;
- memory limit;
- user cancellation;
- stale/superseded revision;
- numerical failure;
- model invalid;
- unsupported feature;
- provider unavailable;
- execution failure;
- unknown/inconclusive.

### 12.2 Evidence grades

At minimum:

- `SOLVER_REPORTED`
- `INDEPENDENTLY_FEASIBILITY_CHECKED`
- `CORROBORATED`
- `PROOF_CERTIFIED`
- `UNSUPPORTED`
- `INCONCLUSIVE`

Agreement is corroboration, not voting.

### 12.3 `aasm.solver.execution-profile.v1`

Named execution modes include at least:

- `EVIDENCE_GRADE_DETERMINISTIC`
- `PERFORMANCE_PARALLEL`
- `PROVIDER_DEFAULT`

The deterministic profile must specify the controls it requires rather than treating a random seed as sufficient.

### 12.4 `aasm.solver.runtime-provenance.v1`

Capture:

- solver implementation/version/digest;
- adapter version/digest;
- full effective options;
- seeds;
- threads/workers;
- deterministic-time settings;
- numerical tolerances;
- model/formulation fingerprints;
- runtime/platform/container identity;
- native library identity;
- environment fingerprint;
- wall and deterministic-time measurements;
- provider capability manifest fingerprint.

### 12.5 `aasm.solver.reproducibility-certificate.v1`

A certificate states what was actually reproduced and under what equivalence class:

- semantic result only;
- objective/bound equivalence;
- solution assignment equivalence;
- proof artifact equivalence;
- byte-for-byte provider output equivalence.

It must never claim stronger reproducibility than was tested.

---

## 13. Core/conflict diagnosis

The existing conflict minimization module must become part of the real solver/explanation path.

The result contract must distinguish:

- raw provider core;
- irreducible core;
- cardinality-minimum core;
- minimum-weight core;
- partial/minimization-budget-exhausted core.

Each core element must preserve external references and formulation mappings so explanations return to domain requirements rather than opaque generated clauses.

Scalable approaches should include deletion shrink, QuickXplain-style divide-and-conquer, MUS/MCS enumeration where appropriate, and hitting-set optimization for minimum/weighted cores.

A minimized core is an explanation artifact. It does not automatically become a learned hard constraint.

---

## 14. Governed refinement loop

### 14.1 `aasm.refinement.proposal.v1`

A refinement proposal binds:

- base problem revision and fingerprint;
- trigger reasoning/evidence/conflict/core IDs;
- refinement kind;
- target semantic/external references;
- proposed semantic payload;
- applicability declaration;
- dependency fingerprints;
- independent validation requirement;
- expected semantic effect;
- estimated resource demand;
- producer identity;
- status/fingerprint.

Refinement kinds include at least:

- no-good;
- bound tightening;
- new constraint;
- domain restriction;
- objective correction;
- required observation;
- verification escalation;
- model correction;
- scenario addition;
- rule applicability correction.

### 14.2 `aasm.refinement.loop.v1`

The loop orchestrates existing mechanisms:

`candidate -> verify/observe -> reasoning artifact -> diagnose -> refinement proposal -> validate applicability -> scoped authorization -> problem delta -> new problem revision -> truth maintenance -> replan`

It introduces no new truth store and no direct solver mutation API.

### 14.3 Anti-loop rules

- refinement proposals are base-revision bound;
- revision graph is acyclic;
- identical semantic refinement cannot be applied repeatedly to the same revision;
- stale verification cannot authorize a new refinement;
- refinement resource/budget exhaustion yields `INCONCLUSIVE`, not success;
- repeated no-progress cycles must become a deterministic blocking condition/obligation;
- refinements learned under narrow applicability scopes cannot silently broaden themselves.

---

## 15. Multi-fidelity verification and verification debt

### 15.1 Verifier capability declaration

Extend verifier capabilities with:

- supported target problem/artifact kinds;
- fidelity class;
- environment requirements;
- numerical/tolerance policy;
- soundness/completeness declaration where meaningful;
- expected resource demand;
- expected wall time;
- evidence grade produced;
- cache/reuse eligibility;
- revision/staleness semantics.

### 15.2 `aasm.verification.plan.v1`

A verification plan is a governed plan over existing workers/effects/resources. It is not another scheduler.

### 15.3 `aasm.verification.debt.v1`

Verification debt should normally be a deterministic projection over obligations and current evidence:

- obligation ID;
- target revision/artifact;
- required evidence grade;
- best current evidence grade;
- missing/stale checks;
- blocking/nonblocking status;
- estimated resources to close;
- waiver state;
- explanation.

Cheap verification passing does not erase a higher-fidelity obligation.

### 15.4 Resource-aware evidence acquisition

AASM may select the most valuable next evidence acquisition action using existing resource routing, but it may not lower the required evidence grade because a stronger verifier is expensive or scarce.

---

## 16. Solution pools, production multi-objective reasoning, and semantic diversity

The certified finite engines remain the oracle and reference semantics.

Production paths should add:

- exact Boolean/integer no-goods;
- solver-driven enumeration;
- top-K ranked alternatives;
- near-optimal pools;
- semantic projection/equivalence;
- diversity metrics over semantic projections rather than raw auxiliary assignments;
- restartable cursors;
- truthful bounded/partial completeness states.

Lexicographic production solving should use true sequential optimization with explicit tolerance-preserving constraints between stages. Pareto production solving must distinguish exact finite frontiers from bounded/partial/approximate frontiers and must never imply undiscovered points do not exist.

---

## 17. Proof/checker expansion

Proof architecture should expand incrementally and conservatively.

### 17.1 SAT

Support proof transport where the provider genuinely exposes it. Maintain canonical formulation identity, proof artifact identity, and independent checker identity. DRAT/LRAT levels must not be conflated.

### 17.2 LP/MILP

Separate claims:

- feasible incumbent;
- infeasibility;
- unboundedness;
- optimality.

Use independently checked certificates only where the backend/toolchain genuinely supports them. General MIP proof support remains provider/toolchain constrained and must not be simulated by stronger wording than the evidence warrants.

### 17.3 Cross-backend rule

`agreement OR inconclusive, never vote` remains permanent. Cross-backend disagreement is a first-class conflict that can trigger diagnosis/refinement; it is not resolved by majority.

---

## 18. Uncertainty, scenarios, and temporal semantics

### 18.1 `aasm.uncertainty.v1`

Supported forms should include:

- exact;
- interval;
- discrete scenarios;
- distribution reference;
- empirical samples;
- unknown bounded;
- unknown unbounded.

### 18.2 `aasm.scenario.v1`

A scenario binds operating conditions, environment assumptions, required evidence, and applicability.

### 18.3 `aasm.trace-property.v1`

Trace properties represent startup/shutdown/transient/sequential requirements over state histories rather than forcing all requirements into static feasibility constraints.

Robustness/scenario semantics must remain explicit so a design proven under one nominal point is not accidentally claimed for an uncertainty set.

---

## 19. Readiness and release gates

### 19.1 `aasm.readiness.gate.v1`

Readiness is a deterministic predicate over:

- required obligations;
- evidence/certificate grades;
- problem/artifact/external-machine revision consistency;
- stale evidence;
- waivers;
- verification debt;
- unresolved UNKNOWN effects;
- unresolved conflicts;
- required external state;
- resource settlement state;
- proof state;
- profile/domain conformance.

Readiness must be explainable: every failed predicate returns the blocking obligation/evidence/revision/reference.

### 19.2 Claim ceiling

AASM must continue to distinguish:

- solver-reported;
- independently checked;
- certified;
- complete over a declared finite space;
- bounded/partial;
- inconclusive.

No release note may claim more than the strongest reproducible gate proves.

---

## 20. TextPCB integration architecture

TextPCB remains authoritative for its project truth, domain rules, board/CAD semantics, generated artifacts, and internal lifecycle.

AASM governs:

- requirements/semantic lineage;
- authority to request TextPCB transitions;
- resource allocation;
- solver/verifier selection;
- evidence and artifact provenance;
- revision-aware optimization;
- cross-tool/cross-solver corroboration;
- conflict explanation;
- refinement admission;
- reconsideration after changed evidence;
- readiness/completion claims.

The TextPCB adapter provides:

- external machine binding;
- mapping between TextPCB states/transitions and AASM machine transition specifications;
- external references for requirements/constraints/artifacts;
- TextPCB artifact observations/revisions;
- domain quantity/rule translation;
- verifier capability declarations;
- semantic projections/equivalence for board/design alternatives;
- TextPCB-specific conformance fixtures.

The adapter must not grant itself AASM truth or authority.

---

## 21. General engineering value

### Mechanical CAD

Revision-safe constraints, topology evolution, artifact lineage, simulation refinement, dimensional quantities, design-rule precedence, multi-fidelity CAE, and readiness gates.

### PCB/EDA

Stable requirement/net/component/rule identity, DRC/ERC feedback, layout-state supervision, manufacturing constraints, top-K/diverse designs, signal/power/thermal verification, and evidence-grade release readiness.

### Robotics

External robot/controller state-machine supervision, world-model revisions, simulation/real-world feedback, stale-result fencing, resource-bounded planning, and safety obligations.

### Manufacturing

Part/process revisions, machine transitions, quality observations, tolerance/uncertainty semantics, production evidence, and change-impact qualification.

### Software and infrastructure

Source/deployment artifact evolution, CI/CD external-machine control, environment provenance, solver/planner feedback, reproducible evidence, and scope-safe multi-tenant authority.

### Scientific/optimization workflows

Problem revision lineage, evidence acquisition planning, multi-fidelity models, reusable learned constraints, exact/partial frontier truth levels, and proof-aware cross-backend reasoning.

---

## 22. Formal invariants to maintain or add

The implementation must enforce and eventually formally model the following invariants:

1. `ReplayEqualsPersistedCanonicalState`
2. `NoAlternateTruthMutationPath`
3. `NoExternalStateMutationWithoutDurableOwnership`
4. `NoAcceptedStaleExternalTransition`
5. `IdempotentTransitionIntent`
6. `ProblemRevisionGraphAcyclic`
7. `ProblemDeltaBaseRevisionMatches`
8. `ArtifactLineageAcyclic`
9. `ArtifactHashBinding`
10. `ResolvedSemanticReferenceOrExplicitAmbiguity`
11. `DimensionalConsistency`
12. `HardFloorNonOverride`
13. `NoSilentUnsupportedFeatureLowering`
14. `NoHardLearningOutsideApplicabilityScope`
15. `NoSemanticAuthorityFromPerformanceKnowledge`
16. `NoStaleVerificationPromotion`
17. `LocalDeltaPreservesUnrelatedAuthority`
18. `ResourcePolicyCannotWeakenHardSemantics`
19. `UnknownEffectBlocksDependentReadiness`
20. `ReadinessImpliesNoBlockingVerificationDebt`
21. `CrossBackendAgreementNeverVotesTruth`
22. `RefinementProducerCannotSelfAuthorizeSemanticMutation`
23. `SupersededRevisionResultsRemainHistoricalOnly`
24. `AmbiguousEntityEvolutionBlocksHardReuse`
25. `ClaimStrengthDoesNotExceedCertificateStrength`

---

## 23. Implementation doctrine for builders

Every new capability must land with:

- typed contract/model;
- stable ID and fingerprint rules;
- schema when it is public/persisted;
- explicit authority boundary;
- explicit Evidence/provenance boundary;
- persistence/replay story;
- stale/supersession behavior;
- positive tests;
- negative/adversarial tests;
- exact claim ceiling;
- documentation;
- release-gate mapping before the release is called complete.

Do not land “temporary” public shortcuts that the known product destination will make invalid.

Do not broaden the kernel with TextPCB types. Generalize the needed semantics, then qualify them with TextPCB.

Do not weaken existing v0.48-v0.54 contracts to make new work easier. Compose through them.

---

## 24. Canonical release direction

The reconciled roadmap is:

- **v0.55** — Extended IR + Portable Semantic Evolution Archive
- **v0.56** — Truthful Solver Evidence + Governed Knowledge Application
- **v0.57** — External Machine Supervision + Artifact/Entity Lineage
- **v0.58** — Governed Refinement + Problem Deltas + Verification Planning
- **v0.59** — Engineering Semantics + Production Alternative Search
- **v0.60** — Uncertainty/Scenarios/Temporal + Readiness + Engineering Conformance
- **v0.61** — Permanent Cross-Capability Stress Corpus
- **v0.62** — Semantic Solver RC2 + Hosted-Foundation Review

The detailed work packages, dependencies, and acceptance criteria are defined in the companion canonical roadmap.

---

## 25. Final architectural statement

The target system is not a self-modifying solver and not an AI agent framework with more state.

It is a **governed semantic-evolution runtime**:

- cognition can remain nondeterministic;
- solvers can remain heterogeneous;
- external machines can retain their own authoritative state;
- engineering artifacts can evolve;
- evidence can conflict;
- models can be refined;
- resources can be scarce;
- prior knowledge can be reused;

while promotion into current machine truth remains explicit, typed, attributable, revision-bound, replayable, independently checkable where possible, and subject to deterministic authority and admission rules.

That is the strongest architecture for TextPCB, and it materially expands AASM's usefulness far beyond TextPCB without compromising the principles that make AASM valuable in the first place.
