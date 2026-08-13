# Changelog

Detailed history through v0.27.0 is preserved in [`CHANGELOG_0.27_AND_EARLIER.md`](CHANGELOG_0.27_AND_EARLIER.md). Git history and immutable release tags preserve the complete source history for later releases.

## [0.39.0] - 2026-08-13

### Typed Protocol, Capability ABI, and Formal Verification Workers

- added `aasm.typed.protocol.v1 / 0.1.0`, `aasm.capability.abi.v1 / 0.1.0`, `aasm.formal.statement.v1 / 0.1.0`, and `aasm.formal.verification.v1 / 0.1.0`;
- added immutable, policy-admitted typed event schemas, scoped legal transitions, and pattern machines without introducing a second transition engine;
- compiled legal transition proposals into existing causal `DecisionRecord`s plus ordinary guard/evidence `ObligationRecord`s, with policy/controller authorization required before activation;
- added versioned Operator, Observer, Verifier, and Handler capability contracts plus provider bindings enforced through existing resource capability tokens;
- added provenance-bearing `FormalStatement` objects binding exact source reasoning-artifact fingerprints to canonical TPTP, SMT-LIB2, Lean 4, or HOL representations;
- added `FormalVerificationRequest`, `FormalVerificationResult`, solver identity, verification-strength, and deterministic aggregation contracts;
- added reference Vampire, Z3, cvc5, and Lean 4 verifier providers and injectable process workers while keeping execution outside the AASM reducer/kernel;
- made SMT validity semantics explicit through `ASSUMPTIONS_AND_NEGATED_CONJECTURE`, and made Lean rejection explicitly not a theorem refutation;
- required conclusive default solver evidence to identify the solver version and an executable SHA-256 or immutable container digest;
- prohibited theorem-by-vote: independent solver disagreement produces `INCONCLUSIVE`, while proof/certificate/kernel strength remains explicit;
- routed formal requests through ordinary `TaskDemand` / `TaskLease` execution and committed solver outputs only as ordinary AASM Evidence;
- integrated conclusive formal evidence with v0.37 verification without automatic epistemic authorization, allowing v0.38 dependency/truth maintenance to handle downstream consequences;
- added provider-specific lease binding, exact formalization/result fingerprints, crash/restart preservation, idempotent request/result handling, CLI/inspection surfaces, JSON schemas, executable conformance, and bounded TLC/SPIN invariants;
- advanced `aasm.adoption.v1` to `0.15.0`.

## [0.38.0] - 2026-08-13

### Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance

- added `aasm.semantic.dependencies.v1 / 0.1.0`, `aasm.truth.maintenance.v1 / 0.1.0`, `aasm.reactive.obligation.v1 / 0.1.0`, and `aasm.causal.decision.v1 / 0.1.0`;
- added typed semantic node references and dependency edges spanning admitted reasoning, Evidence, events, constraints, decisions, obligations, operators, effects, objectives, verifiers, observers, and certificates;
- added deterministic forward impact and backward lineage projections;
- required a DAG for stale-propagating edges while permitting cycles only for explicitly non-propagating descriptive edges;
- added `CausalDecisionRecord` on the existing calculus with rejected alternatives, confidence, reasoning, causal event IDs, and causal reasoning-artifact IDs;
- added policy/controller admission for explicit semantic dependencies and reactive-obligation rules;
- added deterministic event-to-obligation derivation while explicitly forbidding handler execution inside the derivation/reducer path;
- added durable plan-before-apply truth maintenance with affected-descendant-only invalidation and unrelated-sibling preservation;
- added causal-decision invalidation, active-model cleanup, legal obligation reopening as `NEEDS_REVALIDATION`, and existing lock reevaluation;
- made truth-maintenance application idempotent and resumable after restart through pending plan Evidence;
- exposed deterministic semantic validity/relevance signals for the v0.40 Hierarchical Memory and Reasoning Frontier layer without introducing a second truth system;
- added CLI/inspection surfaces, JSON schemas, executable conformance, and bounded TLC/SPIN invariants;
- refined the roadmap: v0.39 Typed Event/Transition Protocol and Capability ABI, v0.40 Hierarchical Memory/Reasoning Frontier/Context Projection, and v0.41 Domain-Neutral Autonomous Solver Loop;
- advanced `aasm.adoption.v1` to `0.14.0`.

## [0.37.0] - 2026-08-13

### Reasoning Artifacts and Epistemic Admission

- added `aasm.reasoning.artifact.v1 / 0.1.0`, `aasm.reasoning.admission.v1 / 0.1.0`, and `aasm.reasoning.commit.v1 / 0.1.0`;
- added typed `Claim`, `Hypothesis`, `Lemma`, `Invariant`, `Counterexample`, `Definition`, `Assumption`, `Observation`, `Derivation`, `Refutation`, and `ObjectiveResult` artifacts;
- added deterministic artifact IDs/fingerprints, producer authority classes, verifier requirements, and append-only lifecycle transitions;
- added `propose_artifact`, `support_artifact`, `contest_artifact`, `request_verification`, `record_verification`, `authorize_artifact`, `refute_artifact`, `mark_stale`, `reject_artifact`, and `reasoning_commit`;
- rejected self-verification, nonexistent evidence references, low-authority authorization, invalid lifecycle transitions, and forged/direct reasoning records;
- kept all reasoning durability on ordinary AASM Evidence events and the existing event/reducer/store path;
- added deterministic reasoning projection, replay/restart preservation, provenance inspection, JSON schemas, CLI surfaces, and executable conformance;
- reserved semantic dependency propagation and truth maintenance for v0.38;
- advanced `aasm.adoption.v1` to `0.13.0`.

## [0.36.0] - 2026-08-12

### Semantic Compiler SDK

- added `aasm.semantic.source.v1 / 0.1.0` and `aasm.semantic.compiler.v1 / 0.1.0`;
- added `DomainCompiler`, `InstanceCompiler`, `CompileResult`, environment snapshots, deterministic IDs, source-mapped diagnostics, audit trails, and a content-addressed compile cache;
- implemented `PARSE → RESOLVE → NORMALIZE → TYPE_CHECK → VALIDATE → FINGERPRINT → INSTANTIATE`;
- kept compiler authority `PROPOSAL_ONLY` and admission `AASM_EVENT_REDUCER_ONLY`;
- added deterministic compiler conformance and compile-and-admit through ordinary AASM Evidence;
- extended the bounded trace model with invalid-source and admission-evidence compiler invariants;
- advanced `aasm.adoption.v1` to `0.12.0`.

## [0.35.0] - 2026-08-12

### Semantic Problem Model Foundations

- added `aasm.semantic.problem.v1`, `aasm.domain.v1`, and `aasm.problem.v1`;
- added DomainPackage, ProblemDefinition, ProblemModel, ProblemInstance, Entity, Predicate, Objective, Operator, Observer, and Verifier value objects;
- added canonical serialization, deterministic fingerprints, referential integrity, capability gaps, decision-domain checks, and contradiction detection;
- admitted accepted problems through ordinary AASM Evidence events and replayed them without a private semantic store;
- advanced `aasm.adoption.v1` to `0.11.0`.

## [0.34.0] - 2026-08-12

### Distributed Recovery Certification

- added `aasm.recovery.v1 / 0.1.0`;
- added deterministic failure injection for worker loss, lease expiry/reclaim, stale completion, duplicate delivery, database restart, supervisor loss, and UNKNOWN-effect reconciliation;
- fixed stale lease completion so expired/superseded workers cannot mutate canonical task state;
- separated full evidence hashes from deterministic scenario-outcome signatures;
- advanced `aasm.adoption.v1` to `0.10.0`.

## [0.33.0] - 2026-08-12

### Signed Provenance and Verifiable Exports

- added `aasm.provenance.v1 / 0.1.0`;
- added canonical run exports, SHA-256 content inventories, detached HMAC-SHA256 signatures, offline verification, and selective-disclosure lineage;
- advanced `aasm.adoption.v1` to `0.9.0`.

## [0.32.0] - 2026-08-12

### Runtime/Formal Trace Conformance

- added `aasm.trace.v1 / 0.1.0` lossless production-event projection;
- added `aasm.trace.semantic.v1 / 0.1.0` semantic witness checking;
- preserved exact event IDs, source sequences, raw source mappings, and per-event SHA-256 digests;
- added deterministic source-trace, projection, semantic-report, and trace-corpus fingerprints;
- made unknown transitions explicitly `UNSUPPORTED` instead of silently dropping them;
- rejected snapshot-only input as insufficient evidence of transition history;
- linked semantic counterexamples to exact source event IDs and pre/post-state fingerprints;
- added CLI and inspection surfaces for trace projection and semantic checking;
- added JSON schemas and bounded TLA+/Promela trace models;
- advanced `aasm.adoption.v1` to `0.8.0`;
- retained `aasm.scopes.v1 / 0.1.0` and `aasm.remote.v1 / 0.19.0`.

## [0.31.0] - 2026-08-12

### Hierarchical Decision Scopes

- added `aasm.scopes.v1 / 0.1.0`;
- added permanent root plus strategy, architecture, implementation, workstream, and custom scopes;
- added scope-local models, inherited effective models, explicit override policy, and validated cross-scope dependencies;
- added causal cross-scope backjumping preserving unrelated sibling subtrees;
- added scoped restart retaining parents, evidence, pinned decisions, certified hard knowledge, and append-only history;
- added atomic multi-scope candidate activation and legacy-flat root migration;
- added Python, CLI, HTTP, Control Center, schema, TLC, and SPIN surfaces;
- retained one authoritative machine and one event/reducer/store path.

## [0.30.0] - 2026-08-11

Added the framework-neutral Adapter Conformance Kit with eight black-box scenarios, real LangGraph coverage, replay verification, provenance checks, direct-storage-write detection, duplicate-authority detection, and `PASS | FAIL | INCONCLUSIVE` reports.

## [0.29.0] - 2026-08-11

Added the thin LangGraph adapter while preserving LangGraph graph/checkpoint ownership and placing durable authority, obligations, evidence, effects, conflict learning, replay, and recovery under AASM.

## [0.28.x] - 2026-08-11

Added one-command local operation, executable runbooks, immutable release evidence, reproducible double builds, exact remote asset verification, and a self-contained source distribution.
