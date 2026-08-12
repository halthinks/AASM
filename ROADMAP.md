# AASM Roadmap

AASM is currently **v0.31.0 / experimental**.

The current program is **Adoption, Interoperability, Verifiable Operation, and Semantic Problem Solving**: make the deterministic kernel, formal calculus, assurance system, observability, distributed runtime, framework adapters, and future semantic solver understandable, runnable, distributable, and independently checkable by people who did not build them.

This roadmap is an execution contract. Every release has a visible user outcome, an implementation boundary, explicit non-goals, and an exit gate.

## Program rule: extend the working path

All new work must use the implementation proven by the existing releases:

```text
public AASM API
    -> existing event creation
    -> existing pure reducer
    -> existing canonical snapshot
    -> Memory / SQLite / PostgreSQL stores
    -> existing calculus and assurance boundary
    -> existing workers, leases, effects, replay, and scopes
    -> existing CLI / HTTP / Control Center surfaces
```

The roadmap must not create a parallel runtime, alternate reducer, duplicate event model, private database mutation path, replacement Control Center, framework-owned AASM truth, domain-specific authority bypass, or reference-only orchestration loop.

The architectural rules inherited from the AVATAR and labelled-splitting work remain mandatory:

```text
exploration may be conditional and reversible
history and provenance are append-only
contradictions become durable blocking knowledge
backjumping follows causes rather than recency
restart discards speculation, not verified knowledge
fairness prevents mandatory work from remaining hidden forever
models propose; the AASM kernel authorizes durable state
```

---

# Release sequence

| Release | Primary outcome | Status |
|---|---|---|
| **v0.25.2** | Canonical adoption API and implementation contract | Completed |
| **v0.26.0** | Research Synthesis Hero Stack | Completed |
| **v0.27.0** | One-Command Local Full Stack | Completed |
| **v0.28.0** | Distribution and Operator Readiness | Completed |
| **v0.28.1** | Distribution Release Hardening | Completed |
| **v0.28.2** | Self-Contained Source Distribution | Completed |
| **v0.29.0** | Thin LangGraph Adapter | Completed |
| **v0.30.0** | Adapter Conformance Kit | Completed |
| **v0.31.0 — Hierarchical Decision Scopes** | One authority across strategy, architecture, implementation, and workstreams | **Current — implemented** |
| **v0.32.0 — Runtime/Formal Trace Conformance** | Production histories checked against a versioned formal transition vocabulary | Next |
| **v0.33.0 — Signed Provenance and Verifiable Exports** | Portable run evidence independently verifiable offline | Planned |
| **v0.34.0 — Distributed Recovery Certification** | Repeatable failure-injection evidence for leases, effects, ownership, and recovery | Planned |
| **v0.35.0 — Semantic Problem Model** | Domain-neutral semantic definitions, models, and instances | Planned |
| **v0.36.0 — Semantic Compiler SDK** | Deterministic compilation from problem definitions to executable semantic instances | Planned |
| **v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph** | Typed claims, hypotheses, lemmas, invariants, counterexamples, and causal dependencies | Planned |
| **v0.38.0 — Semantic Truth Maintenance** | Dependency-aware support, challenge, invalidation, reopening, learning, and recovery | Planned |
| **v0.39.0 — Capability ABI** | Interchangeable operators, observers, verifiers, tools, humans, and model-backed reasoners | Planned |
| **v0.40.0 — Reasoning Frontier** | Fair, budgeted, inspectable selection of the next unresolved semantic work | Planned |
| **v0.41.0 — Domain-Neutral Solver Loop** | Compilation, reasoning, verification, learning, and recovery in one loop | Planned |
| **v0.42.0 — Reference Domains** | Finished cross-domain demonstrations on one solver kernel | Planned |
| **v0.43.0 — Semantic Conformance Kit** | Black-box proof that semantic extensions preserve AASM boundaries | Planned |
| **v0.44.0 — Cross-Run Knowledge** | Governed reuse of verified artifacts and learned constraints | Planned |
| **v0.45.0 — Semantic Solver Release Candidate** | Consolidated, documented, replayable semantic solver surface | Planned |

---

# Completed adoption foundation

## v0.25.2 — Canonical Adoption Contract

Established `aasm.adoption.v1`, one supported public integration path, explicit stable/experimental/internal support classes, runtime/protocol separation, and machine-readable validation.

## v0.26.0 — Research Synthesis Hero Stack

Delivered a fixed offline corpus and a complete trajectory showing contradiction, certified learned no-good, causal backjump, selective steering, preservation of unrelated work, provenance-bearing output, and exact replay.

## v0.27.0 — One-Command Local Full Stack

Delivered PostgreSQL, the existing HTTP runtime, the existing Control Center, deterministic workers, a live setup machine, a completed reference machine, status/fresh/complete/verify/check commands, and non-destructive reset semantics through Docker Compose.

## v0.28.0–v0.28.2 — Distribution and Operator Readiness

Delivered reproducible builds, immutable release assets, exact hash read-back, a clean-wheel gate, a self-contained source distribution, compatibility policy, release history reporting, and executable operator runbooks.

## v0.29.0 — Thin LangGraph Adapter

Allowed an existing LangGraph application to retain its graph, routing, interrupts, checkpoint data, and domain state while AASM supplied durable authority, obligations, evidence, effects, conflict learning, replay, and recovery underneath it.

## v0.30.0 — Adapter Conformance Kit

Delivered a framework-neutral adapter protocol, black-box fixtures, negative integrations, mutation auditing, replay checks, and machine-readable `PASS | FAIL | INCONCLUSIVE` reports.

---

# v0.31.0 — Hierarchical Decision Scopes

## User outcome

Long-running work can separate strategy, architecture, implementation, and workstream reasoning while retaining one authoritative machine and one causal conflict graph.

## Delivered contract

```text
aasm.scopes.v1 / 0.1.0
```

The release delivers:

- a permanent canonical root scope;
- generic scope kinds and lifecycle states;
- explicit inheritance and override policy;
- scope-local Decisions, Obligations, evidence, locks, conflicts, explanations, constraints, and fairness debt;
- validated cross-scope dependencies and invalidation policies;
- acyclic hierarchy and dependency-flow validation;
- effective inherited decision context;
- evidence-flow checks;
- causal cross-scope backjumping;
- scoped restart preserving parents, siblings, evidence, pinned decisions, and certified hard knowledge;
- atomic multi-scope candidate activation;
- explicit migration of historical flat state into root scope metadata;
- Python, CLI, authenticated HTTP, inspection, Control Center, schemas, and bounded formal models.

## Exit gate

A contradiction in one implementation branch can invalidate the responsible architecture or strategy decision through recorded dependencies while preserving unrelated sibling scopes, one authority path, exact replay, and append-only provenance.

---

# Execution-correctness program

The semantic solver program begins only after production execution, provenance, and distributed failure behavior are themselves checkable.

## v0.32.0 — Runtime/Formal Trace Conformance

### User outcome

A production event history can be projected into a versioned formal vocabulary and checked step by step. A failure identifies the exact durable event rather than only an abstract model state.

### Work packages

1. **Lossless trace contract**
   - one projection step per durable event;
   - exact event IDs and sequence numbers;
   - per-event digests and ordered trace digest;
   - explicit `UNSUPPORTED` classifications rather than guessed semantics.

2. **Production projector**
   - authoritative history input only;
   - snapshot-only input rejected;
   - historical field normalization;
   - retained original event mapping;
   - deterministic trace-corpus construction.

3. **Semantic step checker**
   - reconstruct formal pre-state and post-state witnesses;
   - check certificate-gated hard knowledge;
   - check atomic candidate activation;
   - check restart retention;
   - check mandatory-obligation completion safety;
   - check causal backjump outcomes;
   - link every violation to exact event IDs and state fingerprints.

4. **Generated corpus**
   - Research Synthesis;
   - operator runbooks;
   - scoped recovery;
   - candidates;
   - effects and leases;
   - deliberate counterexamples;
   - bounded property-generated histories.

5. **Conformance release gate**
   - versioned runtime-to-formal abstraction map;
   - covered-transition refinement report;
   - unsupported-transition accounting;
   - replay correspondence;
   - TLC/SPIN corpus gate;
   - clean wheel and extracted-sdist verification.

### Exit gate

Every covered production transition either refines a legal formal step or produces a concrete event-linked counterexample. Unsupported transitions remain explicit and cannot be reported as proven.

## v0.33.0 — Signed Provenance and Verifiable Exports

### User outcome

A completed run can be exported and independently verified offline without trusting the producing AASM server or database.

### Planned implementation

- canonical export manifest for events, snapshots, definitions, profiles, scopes, certificates, artifacts, and projections;
- content-addressed inventory with algorithm and version identity;
- detached signer and verifier interfaces;
- key identity, rotation, revocation, and verification policy records;
- selective disclosure that preserves hash linkage;
- replay evidence and trace-conformance evidence;
- offline verification CLI;
- tamper, truncation, substitution, wrong-key, expired-key, and revoked-key tests;
- export provenance visible in the Control Center.

### Exit gate

A clean offline environment verifies package identity, completeness, hashes, signatures, certificate coverage, scope lineage, trace correspondence, and replay evidence.

## v0.34.0 — Distributed Recovery Certification

### User outcome

AASM produces repeatable evidence that ownership, leases, effects, and recovery remain safe under declared failures.

### Planned implementation

- deterministic fault injection for worker crash, lease expiry, delayed completion, duplicate delivery, partitions, database restart, and supervisor loss;
- external-effect emulator for `NOT_STARTED`, `STARTED`, `SUCCEEDED`, `FAILED`, and `UNKNOWN`;
- invariants for single valid ownership, stale-result rejection, idempotency, reconciliation, and mandatory-obligation preservation;
- multi-process PostgreSQL scenarios;
- bounded schedule exploration;
- recovery certificate tied to exact scenario, configuration, trace, and software version;
- expanded operator drills and Control Center recovery timeline;
- selected lease/effect formal-model extensions;
- adapter-conformance integration.

### Exit gate

Every declared failure either recovers without duplicated authority or duplicated effect, or stops in an explicit state requiring human or external reconciliation.

---

# Semantic Solver Program

## Purpose

The Semantic Solver Program extends AASM from a deterministic execution and recovery substrate into a domain-neutral semantic problem-solving substrate. It does not replace the AASM runtime. It compiles domain meaning into typed objects that are admitted, revised, verified, replayed, and recovered through the same authoritative event/reducer path.

```text
ProblemDefinition
    -> semantic compilation
ProblemModel
    -> instantiation
ProblemInstance
    -> AASM authority runtime
Decision / Obligation / Evidence / Conflict / Constraint / Effect
    -> verified completion or explicit unresolved state
```

## Required semantic layers

### ProblemDefinition

A human- or machine-authored description of the problem. It may be incomplete and is not executable.

### ProblemModel

A reusable compiled semantic model defining entities, predicates, operators, observers, verifiers, objectives, admissibility rules, and domain constraints.

### ProblemInstance

One concrete instantiation containing facts, assumptions, claims, obligations, evidence, decisions, constraints, and objective state.

### Execution state

The authoritative AASM state produced by admitted semantic operations. Only this layer controls durable machine truth and external effects.

## Semantic Dependency Graph

The program adds a typed dependency graph connecting:

```text
Entity
  -> Predicate
  -> Claim
  -> Evidence
  -> Verifier
  -> Certificate
  -> Constraint
  -> Decision
  -> Operator
  -> Effect
  -> Observation
```

The existing Decision, Obligation, Evidence, causal, conflict, and scope graphs remain supported projections of this graph.

## Reasoning artifacts

Initial artifact kinds include:

```text
Claim
Hypothesis
Lemma
Invariant
Counterexample
Definition
Assumption
Observation
Derivation
Refutation
ObjectiveResult
```

Every artifact must carry:

- stable identity;
- semantic type and meaning;
- dependency set;
- authority class;
- verification state;
- conflict state;
- applicability predicate;
- expiration or invalidation policy;
- projection rule into AASM decisions, obligations, evidence, conflicts, or constraints;
- exact provenance and source event references.

Artifacts are versioned and append-only. Revision creates a successor artifact rather than silently changing the meaning of an existing certified subject.

## Semantic calculus

The planned semantic transition vocabulary is:

```text
DEFINE
COMPILE
INSTANTIATE
PROPOSE
SUPPORT
CHALLENGE
VERIFY
AUTHORIZE
INVALIDATE
REOPEN
LEARN
GENERALIZE
PROJECT
BACKJUMP
RESTART
COMPLETE
```

Each operation must define preconditions, postconditions, preserved invariants, conflict behavior, replay semantics, and its mapping to the existing AASM transition system.

## v0.35.0 — Semantic Problem Model

### Outcome

Versioned domain-neutral contracts for ProblemDefinition, ProblemModel, ProblemInstance, Entity, Predicate, Objective, Operator, Observer, Verifier, and DomainPackage.

### Implementation

- deterministic identity and canonical serialization;
- JSON schemas and Python types;
- semantic fingerprints;
- import and package identity;
- validation and migration rules;
- mappings into hierarchical AASM scopes;
- explicit completeness and ambiguity diagnostics;
- no semantic object may enter durable state outside normal AASM admission.

### Exit gate

Two independently authored domains compile into valid models without kernel changes, and every instantiated object has deterministic identity and provenance.

## v0.36.0 — Semantic Compiler SDK

### Outcome

A deterministic compiler pipeline transforms incomplete problem definitions into validated reusable models and concrete instances.

### Implementation

- parse, resolve, normalize, type-check, validate, fingerprint, and instantiate phases;
- source maps and exact diagnostics;
- package and capability resolution;
- canonical intermediate representation;
- deterministic build cache;
- compiler plugin conformance;
- byte-identical repeated compilation;
- compiler results admitted through the public AASM API.

### Exit gate

Repeated compilation is byte-identical; diagnostics point to exact definition locations; no compiler output bypasses machine authority.

## v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph

### Outcome

Reasoning becomes a typed, inspectable system rather than unstructured text attached to tasks.

### Implementation

- artifact algebra and immutable successor semantics;
- typed dependency edges;
- support, challenge, derivation, refutation, applicability, and projection relations;
- graph closure and cycle policy;
- scope-aware artifact placement;
- Decision, Obligation, Evidence, and causal projections;
- schemas, CLI, HTTP, Control Center, and export surfaces.

### Exit gate

Every final claim can be traced through typed dependencies to evidence, verifiers, certificates, constraints, decisions, operators, effects, and observations.

## v0.38.0 — Semantic Truth Maintenance

### Outcome

Changed facts or invalid evidence retract only dependent conclusions, reopen affected work, and preserve unrelated verified knowledge.

### Implementation

- dependency-aware support and challenge sets;
- contradiction detection;
- justification tracking;
- artifact invalidation and successor creation;
- obligation reopening;
- learned semantic constraints;
- causal semantic backjumping;
- knowledge-preserving restart;
- scope-aware propagation;
- conflict minimization and certificate coverage.

### Exit gate

Invalidated premises retract only their dependency closure; unrelated verified artifacts remain; repeated failed semantic combinations are blocked by certified learned knowledge.

## v0.39.0 — Capability ABI

### Outcome

Operators, observers, verifiers, deterministic solvers, model-backed reasoners, tools, humans, and remote workers become interchangeable implementations of declared semantic capabilities.

### Implementation

- capability identity and versioning;
- typed input/output and semantic-result contracts;
- authority and evidence requirements;
- cost, latency, token, and resource budgets;
- effect declarations and idempotency requirements;
- isolation and trust-level declarations;
- deterministic and nondeterministic capability classes;
- local and remote execution bindings;
- capability conformance suite.

### Exit gate

Multiple implementations satisfy the same capability contract without changing the ProblemModel or bypassing AASM effects, workers, leases, evidence, or authority.

## v0.40.0 — Reasoning Frontier

### Outcome

AASM can explain exactly why a particular unresolved semantic item is the next work to perform.

### Implementation

- frontier items for open objectives, unresolved obligations, unsupported claims, missing observations, active conflicts, and candidate repairs;
- priority, dominance, pruning, and dependency readiness;
- fairness debt for mandatory semantic work;
- cost and uncertainty budgets;
- scope-aware scheduling;
- deterministic tie-breaking;
- frontier provenance and explanation;
- Control Center reasoning-frontier view.

### Exit gate

Mandatory semantic work cannot remain hidden indefinitely, and every frontier-selection decision is inspectable and replayable.

## v0.41.0 — Domain-Neutral Solver Loop

### Outcome

Compilation, frontier selection, candidate generation, operator execution, observation, verification, conflict learning, repair, backjump, restart, and completion operate as one replayable solver loop.

### Implementation

```text
compile
  -> instantiate
  -> select frontier item
  -> propose candidate
  -> check authority and constraints
  -> execute authorized capability
  -> record observation and evidence
  -> verify or challenge
  -> learn / repair / backjump / restart
  -> complete or continue
```

- bounded loop budgets and termination reasons;
- explicit `UNKNOWN`, `INCONCLUSIVE`, and reconciliation states;
- exact event-to-semantic-operation mapping;
- semantic completion contracts;
- solver-loop inspection and replay;
- no alternate reducer or semantic-private event store.

### Exit gate

A complete run reconstructs exactly from durable events and either reaches verified completion or stops in an explicit unresolved or reconciliation state.

## v0.42.0 — Reference Domains

### Outcome

The semantic solver demonstrates generality across materially different kinds of reasoning.

### Initial domains

1. research and evidence synthesis;
2. software delivery and repair;
3. a constrained engineering, CAD, theorem-solving, or planning domain.

Each domain must include:

- finished DomainPackage and defaults;
- fixed offline deterministic example;
- known contradiction;
- typed reasoning artifacts;
- learned constraint;
- causal recovery;
- final provenance artifact;
- exact replay;
- measured ordinary-loop comparison;
- Control Center views and operator procedure.

### Exit gate

The same solver kernel operates every reference domain without domain-specific kernel changes.

## v0.43.0 — Semantic Conformance Kit

### Outcome

Third parties can prove whether a DomainPackage, compiler, capability, operator, observer, verifier, or solver integration preserves AASM semantic boundaries.

### Implementation

- black-box fixture instances;
- identity and determinism checks;
- authority and direct-storage-write detection;
- artifact and provenance validation;
- truth-maintenance scenarios;
- effect and lease scenarios;
- replay and scope checks;
- deliberate negative fixtures;
- `PASS | FAIL | INCONCLUSIVE` report with exact artifact and event references.

### Exit gate

One command produces a reviewable report that clearly distinguishes verified behavior, violations, and unexercised behavior.

## v0.44.0 — Cross-Run Knowledge

### Outcome

Verified artifacts and learned constraints can be reused across runs without silently turning local conclusions into universal truth.

### Implementation

- governed knowledge packages;
- applicability predicates and scope;
- evidence and certificate retention;
- domain, compiler, model, and version compatibility;
- promotion, supersession, revocation, and expiration;
- conflict and contamination handling;
- selective import;
- provenance-preserving reuse;
- cross-run knowledge graph and Control Center view.

### Exit gate

Transferred knowledge is never active outside a validated applicability predicate and accepted provenance/certificate policy.

## v0.45.0 — Semantic Solver Release Candidate

### Outcome

A consolidated, documented, installable semantic solver surface is ready for a pre-1.0 readiness review.

### Consolidation gate

- stable documented public API and compatibility identities;
- clean wheel and self-testing extracted source distribution;
- deterministic compiler and reference runs;
- typed semantic artifacts and dependency graph;
- truth maintenance and causal recovery;
- capability ABI and frontier scheduling;
- exact replay and runtime/formal correspondence for covered transitions;
- signed portable provenance;
- distributed recovery evidence;
- semantic conformance reports;
- governed cross-run knowledge;
- no unresolved critical authority, truth-maintenance, or effect-safety defect.

---

# Adoption scorecard

| Measure | Gate | Current state |
|---|---:|---|
| Clone to healthy dashboard | under 5 minutes | Implemented and Compose-tested |
| Understandable completed demonstration | under 10 minutes | Implemented |
| Required external model/API keys | 0 | Achieved |
| Exact reference replay | snapshot/hash match | Enforced |
| Learned no-good | visible, certified, and reused | Implemented |
| Causal backjump | target and preserved work visible | Implemented |
| Unresolved mandatory obligations at completion | 0 | Enforced |
| Fresh non-destructive reset | one command | Implemented |
| Published-wheel smoke | required | Implemented |
| Self-testing extracted source distribution | required | Implemented |
| Operator runbook drills | required | Implemented |
| Existing-framework adoption | thin LangGraph adapter | Implemented |
| Adapter boundary proof | conformance report | Implemented |
| Hierarchical reasoning | one authority across scopes | **v0.31.0** |
| Runtime/formal correspondence | event-linked trace refinement | v0.32.0 |
| Portable verification | signed offline export | v0.33.0 |
| Distributed recovery evidence | failure-injection certificate | v0.34.0 |
| Semantic problem compilation | deterministic ProblemModel/Instance | v0.35–v0.36 |
| Typed reasoning and truth maintenance | dependency-aware semantic graph | v0.37–v0.38 |
| Domain-neutral solver | frontier plus solver loop | v0.39–v0.41 |
| Cross-domain proof | finished reference domains | v0.42.0 |
| Extension proof | semantic conformance | v0.43.0 |
| Safe knowledge reuse | governed cross-run packages | v0.44.0 |
| Semantic solver RC | consolidated readiness gate | v0.45.0 |

---

# Cross-release delivery discipline

Every release must retain:

1. Python 3.11–3.13 tests;
2. clean wheel and source-distribution inspection;
3. extracted-sdist validation without a Git checkout;
4. PostgreSQL integration;
5. Docker Compose end-to-end verification;
6. TLA+/TLC and Promela/SPIN when the modeled boundary changes;
7. exact replay and append-only history;
8. visible README version and next milestone;
9. ordinary source committed directly to `main`;
10. no feature branch or pull-request staging for canonical implementation work;
11. immutable release tags and no-overwrite assets;
12. exact remote asset name, byte-size, and SHA-256 read-back;
13. machine-readable compatibility, conformance, and correctness limits;
14. honest `UNSUPPORTED`, `INCONCLUSIVE`, `UNKNOWN`, or reconciliation states instead of invented assurance.

The project advances only when the complete release gate passes. A partially implemented internal subsystem is not presented as a completed release.
