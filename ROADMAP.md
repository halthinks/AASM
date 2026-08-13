# AASM Roadmap

AASM is currently **v0.33.0 / experimental**.

A release is complete only when ordinary source is reachable from `main`, package/runtime and README agree, tests and formal assurance pass, the immutable tag targets the exact commit, and every published asset is remotely verified.

## Architectural rule

```text
public AASM API → durable event → production reducer → canonical snapshot
                → Memory / SQLite / PostgreSQL → assurance / observability / replay
```

No phase may introduce a competing runtime, event store, effect ledger, scheduler, or framework-private source of machine truth.

## Completed foundation

| Release | Capability | State |
|---|---|---|
| v0.29.0 | Thin LangGraph Adapter | Released |
| v0.30.0 | Adapter Conformance Kit | Released |
| v0.31.0 | Hierarchical Decision Scopes | Released |
| v0.32.0 | Runtime/Formal Trace Conformance | Released |
| **v0.33.0** | **Signed Provenance and Verifiable Exports** | **Current — implemented** |

## v0.33.0 — Signed Provenance and Verifiable Exports

Completed runs can be exported without trusting the original database. The package contains canonical event/snapshot/trace evidence, a content-addressed manifest, detached signer envelope, exact byte sizes and SHA-256 digests, and selective-disclosure sub-manifests that retain parent-manifest lineage. Offline verification detects changed, missing, substituted, truncated, or wrong-key-covered content.

## v0.34.0 — Distributed Recovery Certification

**Outcome:** repeatable evidence that ownership, leases, effects, and recovery remain safe under worker crash, lease expiry/reclaim, stale completion, duplicate delivery, database restart, supervisor loss, and external-effect `UNKNOWN` followed by reconciliation.

**Exit gate:** every declared scenario either recovers with one valid authority/effect outcome or stops in an explicit reconciliation state.

# Semantic Solver Program

```text
ProblemDefinition → semantic compilation → ProblemModel → ProblemInstance
                  → AASM authority runtime → verified completion or explicit unresolved state
```

## v0.35.0 — Semantic Problem Model Foundations

Bind, validate, fingerprint, persist through ordinary events, replay, and inspect a domain-neutral semantic problem: `DomainPackage`, `ProblemDefinition`, `ProblemModel`, `ProblemInstance`, entities, predicates, variables, facts, assumptions, obligations, constraints, objectives, operator/observer/verifier definitions, and deterministic completion rules.

## v0.36.0 — Semantic Compiler SDK

`PARSE → RESOLVE → NORMALIZE → TYPE_CHECK → VALIDATE → FINGERPRINT → INSTANTIATE`, with deterministic IR, source-mapped diagnostics, missing-input/capability reporting, content-addressed cache, proposal-only compiler authority, compile-and-admit through the event path, and conformance fixtures.

## v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph

Typed durable `Claim`, `Hypothesis`, `Lemma`, `Invariant`, `Counterexample`, `Definition`, `Assumption`, `Observation`, `Derivation`, and `Refutation` artifacts connected through Entity → Predicate → Claim → Evidence → Verifier → Certificate → Constraint → Decision → Operator → Effect → Observation.

## v0.38.0 — Semantic Truth Maintenance
Dependency propagation marks only affected descendants stale and preserves unrelated siblings.

## v0.39.0 — Capability ABI
Versioned domain-neutral Operator, Observer, and Verifier contracts.

## v0.40.0 — Reasoning Frontier and Context Projection
Fresh workers receive bounded canonical semantic projections instead of growing transcripts.

## v0.41.0 — Domain-Neutral Solver Loop
Compile → frontier → candidate → admit → execute/observe → verify → learn → backjump/restart.

## v0.42.0 — Reference Domains
Finite constraints, software delivery/repair, research evidence synthesis, and mathematical reasoning.

## v0.43.0 — Semantic Conformance
One command returns `PASS | FAIL | INCONCLUSIVE` across packages, compilers, capabilities, truth-maintenance traces, and authority boundaries.

## v0.44.0 — Cross-Run Certified Knowledge
Opt-in, provenance-bearing, applicability-scoped, revocable, version-aware reusable knowledge.

## v0.45.0 — Semantic Solver Release Candidate
Freeze the first coherent solver contracts after replay, formal, distributed, adversarial, reference-domain, and packaging gates pass.
