# AASM Roadmap

AASM is currently **v0.35.0 / experimental**.

Every release is complete only when its ordinary source is reachable from `main`, package/runtime/README agree, CI and formal assurance pass, and the immutable release assets verify against the exact commit.

## Completed foundation

| Release | Capability | State |
|---|---|---|
| v0.29.0 | Thin LangGraph Adapter | Released |
| v0.30.0 | Adapter Conformance Kit | Released |
| v0.31.0 | Hierarchical Decision Scopes | Released |
| v0.32.0 | Runtime/Formal Trace Conformance | Released |
| v0.33.0 | Signed Provenance and Verifiable Exports | Released |
| v0.34.0 | Distributed Recovery Certification | Released |
| **v0.35.0** | **Semantic Problem Model Foundations** | **Current — implemented** |

## v0.35.0 — Semantic Problem Model Foundations

`DomainPackage`, `ProblemDefinition`, `ProblemModel`, and `ProblemInstance` are canonical, versioned, fingerprinted value objects. Entities, predicates, objectives, operators, observers, and verifiers are domain-neutral. Referential integrity, duplicates, decision domains, missing model pieces, capability gaps, and direct fact contradictions are checked before admission. Accepted instances are recorded through ordinary AASM evidence events and reconstruct through replay.

## v0.36.0 — Semantic Compiler SDK

**Next.** Implement deterministic `PARSE → RESOLVE → NORMALIZE → TYPE_CHECK → VALIDATE → FINGERPRINT → INSTANTIATE`; source-mapped diagnostics; deterministic IDs; missing input/capability reports; content-addressed cache; proposal-only compiler authority; compile-and-admit through the event/reducer path; and conformance fixtures.

## v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph
Typed durable reasoning artifacts connected through Entity → Predicate → Claim → Evidence → Verifier → Certificate → Constraint → Decision → Operator → Effect → Observation.

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
