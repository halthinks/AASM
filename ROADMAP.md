# AASM Roadmap

AASM is currently **v0.37.0 / experimental**.

A release is complete only when ordinary source is reachable from `main`, package/runtime/README agree, CI and formal assurance pass, the immutable tag points to the exact commit, and remote release assets verify.

## Completed foundation

| Release | Capability | State |
|---|---|---|
| v0.29.0 | Thin LangGraph Adapter | Released |
| v0.30.0 | Adapter Conformance Kit | Released |
| v0.31.0 | Hierarchical Decision Scopes | Released |
| v0.32.0 | Runtime/Formal Trace Conformance | Released |
| v0.33.0 | Signed Provenance and Verifiable Exports | Released |
| v0.34.0 | Distributed Recovery Certification | Released |
| v0.35.0 | Semantic Problem Model Foundations | Released |
| v0.36.0 | Semantic Compiler SDK | Released |
| **v0.37.0** | **Reasoning Artifacts and Epistemic Admission** | **Current — implemented** |

## v0.37.0 — Reasoning Artifacts and Epistemic Admission

The epistemic layer adds typed durable `Claim`, `Hypothesis`, `Lemma`, `Invariant`, `Counterexample`, `Definition`, `Assumption`, `Observation`, `Derivation`, `Refutation`, and `ObjectiveResult` artifacts.

Artifacts move through an explicit lifecycle under append-only evidence:

`PROPOSED → SUPPORTED / CONTESTED → VERIFICATION_REQUESTED → VERIFIED → AUTHORIZED`

with explicit `REFUTED`, `STALE`, and `REJECTED` outcomes.

The release enforces independent verification, rejects self-verification, requires evidence-bearing verifier results, requires `POLICY` or `CONTROLLER` authority for authorization, and permits `ReasoningCommit` only over `AUTHORIZED` artifacts.

There is still one authoritative event/reducer/store path. Reasoning proposals, transitions, and commits are ordinary Evidence records, so exact replay, restart, Memory/SQLite/PostgreSQL durability, and provenance use the same runtime.

## v0.38.0 — Semantic Dependency Graph and Truth Maintenance

**Next.** Add the typed semantic dependency graph and deterministic invalidation engine:

`Entity → Predicate → Claim → Evidence → Verifier → Certificate → Constraint → Decision → Operator → Effect → Observation`

with indexed forward/backward adjacency, impact traversal, stale propagation, obligation reopening, lock reactivation, cycle handling, dependency provenance, and explicit queries such as “what breaks if X is false?” and backward proof lineage.

Dependency propagation belongs here, not in v0.37.

## v0.39.0 — Capability ABI

Versioned domain-neutral Operator, Observer, and Verifier contracts.

## v0.40.0 — Reasoning Frontier and Context Projection

Fresh workers receive bounded canonical semantic projections rather than growing transcripts.

## v0.41.0 — Domain-Neutral Solver Loop

Compile → frontier → candidate → admit → execute/observe → verify → learn → backjump/restart.

## v0.42.0 — Reference Domains

Finite constraints, software delivery/repair, research evidence synthesis, and mathematical reasoning.

## v0.43.0 — Semantic Conformance

`PASS | FAIL | INCONCLUSIVE` across packages, compilers, capabilities, truth-maintenance traces, and authority boundaries.

## v0.44.0 — Cross-Run Certified Knowledge

Opt-in, provenance-bearing, applicability-scoped, revocable, version-aware reusable knowledge.

## v0.45.0 — Semantic Solver Release Candidate

Freeze the first coherent solver contracts after replay, formal, distributed, adversarial, reference-domain, and packaging gates pass.
