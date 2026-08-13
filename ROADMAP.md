# AASM Roadmap

AASM is currently **v0.36.0 / experimental**.

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
| **v0.36.0** | **Semantic Compiler SDK** | **Current — implemented** |

## v0.36.0 — Semantic Compiler SDK

The reference compiler implements deterministic `PARSE → RESOLVE → NORMALIZE → TYPE_CHECK → VALIDATE → FINGERPRINT → INSTANTIATE`, exact compiler/source identities, deterministic IDs, source-mapped diagnostics, missing-input and missing-capability reports, environment snapshots, compile audit trails, content-addressed caching, proposal-only compiler authority, compile-and-admit through the AASM event path, and an executable conformance report.

The exit gate is explicit: same normalized source + same domain package + same compiler version + same environment/policy produces the same problem fingerprint.

## v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph

**Next.** Add typed durable `Claim`, `Hypothesis`, `Lemma`, `Invariant`, `Counterexample`, `Definition`, `Assumption`, `Observation`, `Derivation`, `Refutation`, and `ObjectiveResult` artifacts plus the semantic dependency graph:

`Entity → Predicate → Claim → Evidence → Verifier → Certificate → Constraint → Decision → Operator → Effect → Observation`.

## v0.38.0 — Semantic Truth Maintenance
Dependency propagation marks only affected descendants stale and preserves unrelated siblings.

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
