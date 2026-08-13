# AASM Roadmap

AASM is currently **v0.38.0 / experimental**.

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
| v0.37.0 | Reasoning Artifacts and Epistemic Admission | Released |
| **v0.38.0** | **Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance** | **Current — implemented** |

## How the expanded modules fit

The three expanded designs are now sequenced by the invariant each one depends on rather than shipped as parallel sidecars:

| Original module | Roadmap placement | Why |
|---|---|---|
| Rich Causal Decisions & Reactive Obligations | **v0.38** | Requires admitted reasoning plus dependency-local invalidation |
| Refined Typed Legal Transitions | **v0.39** | Becomes the typed event/transition and capability ABI rather than a second transition engine |
| Hierarchical Memory Layer | **v0.40** | Must retrieve only against validity/staleness already established by v0.37–v0.38 |

## v0.38.0 — Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance

V0.38 connects semantic truth to its downstream consequences.

Delivered:

- typed semantic nodes and dependencies;
- deterministic forward impact and backward lineage indexes;
- propagating-edge DAG enforcement with non-propagating descriptive cycles allowed;
- `CausalDecisionRecord` over the existing decision calculus;
- explicit rejected alternatives, confidence, reasoning, causal event IDs, and causal artifact IDs;
- policy-admitted reactive rules that derive ordinary obligations from durable events;
- no handler execution inside derivation or reduction;
- durable plan-before-apply truth maintenance;
- descendant-only stale propagation;
- unrelated sibling preservation;
- causal-decision invalidation;
- consumed obligation reopening through the existing `NEEDS_REVALIDATION` transition;
- lock reevaluation through existing calculus machinery;
- idempotent/resumable crash recovery for truth-maintenance plans;
- deterministic memory/context signals for v0.40;
- TLC/SPIN invariants for locality, ordering, sibling preservation, decision invalidation, obligation reopening, and no hidden reactive execution.

## v0.39.0 — Typed Event/Transition Protocol and Capability ABI

**Next.** Generalize the Typed Legal Transitions design into the ABI shared by domain packages and runtime capabilities.

Planned contracts include:

- versioned `TypedEventSchema`;
- scope-aware legal transition rules;
- payload validation;
- guard-to-obligation compilation;
- evidence requirements;
- admitted pattern/version lifecycle rather than direct `register_pattern()` authority;
- versioned Operator, Observer, Verifier, and handler capability contracts;
- effect/capability compatibility checks;
- transition/capability conformance fixtures.

Pattern registration itself must be proposed, validated, authorized, and admitted. A pattern cannot silently redefine machine legality.

## v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection

Turn the Hierarchical Memory Layer into a first-class scope-aware memory system built on the validity signals exposed by v0.38.

Canonical memory will contain durable references/content, semantic fingerprints, scopes, causal lineage, epistemic state, retention/privacy policy, and source provenance. Embeddings and other retrieval indexes are **derived indexes**, not memory identity.

Planned memory kinds include sensory, working, episodic, semantic, and procedural memory. Semantic memory references admitted reasoning rather than creating a second truth system.

Context projection will combine:

- scope visibility;
- validity/staleness;
- dependency depth;
- causal and objective relevance;
- verification strength/recency;
- retention and privacy policy;
- bounded frontier budgets.

Forgetting must preserve append-only provenance semantics through tombstoning, visibility revocation, or cryptographic-erasure policy rather than silently deleting history.

## v0.41.0 — Domain-Neutral Autonomous Solver Loop

Close the loop:

`Compile → frontier/context → candidate → epistemic admission → causal decision → obligation → capability execution/observation → verify → truth maintenance → learn → backjump/restart`.

Reactive obligations become executable here only through the typed v0.39 capability path.

## v0.42.0 — Reference Domains and Memory/Reasoning Stress Tests

Finite constraints, software delivery/repair, research evidence synthesis, and mathematical reasoning, with long-horizon memory and truth-maintenance stress fixtures.

## v0.43.0 — Semantic Conformance and Adversarial Certification

`PASS | FAIL | INCONCLUSIVE` across packages, compilers, reasoning admission, dependency traces, memory projections, capabilities, truth-maintenance traces, and authority boundaries.

## v0.44.0 — Cross-Run Certified Knowledge and Governed Long-Term Memory

Opt-in, provenance-bearing, applicability-scoped, revocable, version-aware reusable knowledge and cross-run memory.

## v0.45.0 — Semantic Solver Release Candidate

Freeze the first coherent solver contracts after replay, formal, distributed, adversarial, memory, reference-domain, and packaging gates pass.
