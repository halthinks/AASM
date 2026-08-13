# AASM Roadmap

AASM is currently **v0.32.0 / experimental**.

The roadmap is an execution contract: each version must exist as ordinary source on `main`, pass CI and formal assurance, publish an immutable release, and keep README/package metadata aligned before the next version advances.

## Architectural rule

All work extends the same authority path:

```text
public AASM API
  → durable event
  → production reducer
  → canonical snapshot
  → Memory / SQLite / PostgreSQL
  → assurance / observability / replay
```

No roadmap phase may introduce a competing runtime, event store, effect ledger, scheduler, or framework-private source of machine truth.

## Completed foundation

| Release | Capability | State |
|---|---|---|
| v0.29.0 | Thin LangGraph Adapter | Implemented and released |
| v0.30.0 | Adapter Conformance Kit | Implemented and released |
| v0.31.0 | Hierarchical Decision Scopes | Implemented and released |
| **v0.32.0** | **Runtime/Formal Trace Conformance** | **Current — implemented** |

## v0.32.0 — Runtime/Formal Trace Conformance

**Outcome:** production durable event histories can be projected into a versioned formal trace instead of relying only on a bounded model.

Delivered boundary:

- lossless event projection;
- exact event IDs and source sequences;
- SHA-256 per source event;
- deterministic source-trace and projection fingerprints;
- explicit `UNSUPPORTED` representation for unknown transitions;
- snapshot-only input rejected;
- semantic pre/post-state witnesses when available;
- exact event-linked counterexamples;
- deterministic trace-corpus fingerprints;
- bounded TLC/SPIN trace model.

**Exit gate:** CI, formal assurance, and immutable release verification all succeed on the exact v0.32 commit.

---

## v0.33.0 — Signed Provenance and Verifiable Exports

**Outcome:** a completed run can be exported and checked offline without trusting the original server or database.

Planned deliverables:

- canonical export manifest;
- content-addressed event/artifact inventory;
- detached signature envelope;
- verification policy and signer identity;
- selective-disclosure sub-manifests retaining parent digest lineage;
- replay and certificate coverage evidence;
- offline verification CLI;
- tamper, truncation, substitution, and wrong-key tests.

**Exit gate:** an isolated verifier detects any changed covered byte and can validate an untouched package from the manifest alone.

---

## v0.34.0 — Distributed Recovery Certification

**Outcome:** AASM can produce repeatable evidence that distributed ownership, leases, effects, and recovery remain safe under declared failures.

Planned scenarios:

- worker crash;
- lease expiry and reclaim;
- stale completion rejection;
- duplicate delivery;
- database restart;
- supervisor loss;
- external effect `UNKNOWN` followed by reconciliation.

**Exit gate:** every declared scenario either recovers with one valid authority/effect outcome or stops in an explicit reconciliation state.

---

# Semantic Solver Program

The semantic program begins only after the deterministic execution substrate above. The long-term architecture is:

```text
ProblemDefinition
      ↓ semantic compilation
ProblemModel
      ↓ instantiation
ProblemInstance
      ↓
AASM authority runtime
      ↓
reasoners / tools / humans / simulators
      ↓
verified completion or explicit unresolved state
```

The semantic plane defines meaning. The cognition plane searches. The AASM authority plane decides what may become durable truth.

## v0.35.0 — Semantic Problem Model Foundations

**Outcome:** AASM can bind, validate, fingerprint, persist through ordinary events, replay, and inspect a domain-neutral semantic problem.

Core artifacts:

- `DomainPackage`;
- `ProblemDefinition`;
- `ProblemModel`;
- `ProblemInstance`;
- entities and predicates;
- decision variables;
- facts and assumptions;
- obligations and constraints;
- objectives;
- operator/observer/verifier definitions;
- deterministic completion rules.

No domain-specific type belongs in the kernel.

## v0.36.0 — Semantic Compiler SDK

**Outcome:** domain/problem authors can compile normalized source into the same deterministic semantic model.

Compiler stages:

```text
PARSE → RESOLVE → NORMALIZE → TYPE_CHECK → VALIDATE → FINGERPRINT → INSTANTIATE
```

Required features:

- deterministic canonical IR;
- source-mapped diagnostics;
- missing-input and missing-capability reporting;
- content-addressed build cache;
- compiler declarations with proposal-only authority;
- compile-and-admit through the existing AASM event path;
- compiler conformance fixtures.

## v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph

Typed artifacts include `Claim`, `Hypothesis`, `Lemma`, `Invariant`, `Counterexample`, `Definition`, `Assumption`, `Observation`, `Derivation`, and `Refutation`.

The **Semantic Dependency Graph** connects:

```text
Entity
  → Predicate
  → Claim
  → Evidence
  → Verifier
  → Certificate
  → Constraint
  → Decision
  → Operator
  → Effect
  → Observation
```

Artifacts are durable consequences of reasoning, not raw hidden chain-of-thought.

## v0.38.0 — Semantic Truth Maintenance

Deterministic dependency propagation marks only affected descendants stale, reopens obligations whose support became invalid, releases conditional locks, and preserves unrelated siblings.

## v0.39.0 — Capability ABI

Versioned, domain-neutral `Operator`, `Observer`, and `Verifier` contracts integrate with existing authority and external-effect semantics.

## v0.40.0 — Reasoning Frontier and Context Projection

A fresh worker receives a bounded canonical semantic projection rather than replaying an ever-growing transcript.

## v0.41.0 — Domain-Neutral Solver Loop

Connect compile → select frontier → generate candidates → admit → execute/observe → verify → learn → backjump/restart while keeping candidate/search policy replaceable.

## v0.42.0 — Reference Domains

Prove generality across at least:

1. finite deterministic constraint problem;
2. software delivery/repair;
3. research evidence synthesis;
4. mathematical reasoning.

## v0.43.0 — Semantic Conformance

One command returns `PASS | FAIL | INCONCLUSIVE` for domain packages, compilers, capability adapters, truth-maintenance traces, and authority boundaries.

## v0.44.0 — Cross-Run Certified Knowledge

Reusable knowledge is opt-in, provenance-bearing, applicability-scoped, revocable, version-aware, and certificate-gated where required. Default scope remains run-local.

## v0.45.0 — Semantic Solver Release Candidate

Freeze the first coherent semantic solver contracts after replay, formal, distributed, adversarial, reference-domain, and packaging gates are satisfied.

---

## Adoption scorecard

A release is not done because source exists locally. It is done only when:

```text
ordinary source reachable from main
package/runtime version aligned
README current version aligned
full tests green
formal assurance green
immutable tag targets exact commit
release assets published once
remote sizes and SHA-256 verified
```

This rule applies to every version in this roadmap.
