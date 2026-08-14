# AASM Roadmap

AASM is currently **v0.42.0 / experimental**.

## Released

- v0.35.0 Semantic Problem Model Foundations
- v0.36.0 Semantic Compiler SDK
- v0.37.0 Reasoning Artifacts and Epistemic Admission
- v0.38.0 Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- v0.39.0 Typed Capability ABI and Formal Verification Workers
- v0.40.0 Hierarchical Memory, Reasoning Frontier, and Context Projection
- v0.41.0 Domain-Neutral Solver Loop and Deterministic Reuse Plane
- **v0.42.0 Reference Domains & Reuse/Memory/Reasoning Stress Tests — Current — implemented**

## v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection

Delivered:

- canonical sensory/working/episodic/semantic/procedural memory objects;
- Decision → Obligation → Evidence memory mutations;
- exact authorized-object commit;
- semantic memory restricted to V37 admitted knowledge;
- V38 stale/refuted propagation into memory visibility;
- scope and principal privacy;
- deterministic retention and tombstone forgetting;
- derived retrieval indexes that never change canonical memory identity;
- bounded Reasoning Frontier;
- bounded deterministic Context Projection;
- replay/restart, schema, CLI, server rebinding, conformance, and formal assurance;
- legacy `DPMemory` preserved as the algorithmic memo cache.

## v0.41.0 — Domain-Neutral Solver Loop and Deterministic Reuse Plane

Delivered:

- canonical reuse requests/candidates referencing existing Evidence, Reasoning Artifacts, and Hierarchical Memory;
- policy/controller admission and durable reuse certificates;
- exact, idempotent, explicit-subsumption, and certified-equivalence modes;
- deterministic scope/privacy/environment/dependency/freshness/effect validation;
- a disposable process-local `HotReuseIndex` that cannot change machine truth;
- reuse metrics and durable reporting;
- a solver step that checks reusable prior work before routing capability execution;
- replay-safe integration without a second scheduler, reducer, event log, or truth store;
- formal reuse-plane checks in TLA+ and Promela/SPIN.

## v0.42.0 — Reference Domains and Stress Tests

Delivered:

- `aasm.reference-domains.v1 / 0.1.0`;
- deterministic offline stress execution across constraint solving, software repair, research synthesis, formal reasoning, and long-horizon memory;
- controlled tests for hot-index deletion, environment/dependency/freshness invalidation, non-idempotent effects, reasoning staleness, memory privacy/revocation, and replay identity;
- explicit `ReuseRequest.required_strength` enforcement against candidate verification strength;
- reference-domain public API, CLI commands, schema, example, documentation, and regression suite;
- no new kernel runtime: the harness exercises the existing v0.41 domain-neutral solver engine.

## v0.43.0 — Semantic Conformance and Adversarial Certification

**Next.** Certify domain packages, compilers, reasoning, truth maintenance, capabilities, formal verifiers, memory/context, solver traces, and recovery with explicit `PASS | FAIL | INCONCLUSIVE` adversarial fixtures.

The v0.43 layer should distinguish architectural stress success from semantic certification. It must not reinterpret the synthetic v0.42 reference domains as proof that arbitrary real-world domain data or conclusions are correct.

## v0.44.0 — Cross-Run Certified Knowledge and Governed Long-Term Memory

Opt-in cross-run knowledge with immutable provenance, applicability scope, compatibility, epistemic status, retention/privacy, revocation/supersession, and explicit receiving-run admission.

## v0.45.0 — Semantic Solver Release Candidate

Freeze the coherent public solver contracts after replay, formal, distributed, adversarial, memory/privacy, reference-domain, packaging, and upgrade gates pass.
