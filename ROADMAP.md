# AASM Roadmap

AASM is currently **v0.43.0 / experimental**.

## Released

- v0.35.0 Semantic Problem Model Foundations
- v0.36.0 Semantic Compiler SDK
- v0.37.0 Reasoning Artifacts and Epistemic Admission
- v0.38.0 Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- v0.39.0 Typed Capability ABI and Formal Verification Workers
- v0.40.0 Hierarchical Memory, Reasoning Frontier, and Context Projection
- v0.41.0 Domain-Neutral Solver Loop and Deterministic Reuse Plane
- v0.42.0 Reference Domains & Reuse/Memory/Reasoning Stress Tests
- **v0.43.0 Semantic Conformance, Adversarial Domains, and Certification — Current — implemented**

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

Delivered:

- `aasm.certification.v1 / 0.1.0` with explicit `PASS | FAIL | INCONCLUSIVE` semantics;
- certification profiles for reference domains, solver/reuse, truth/memory, and formal-verification boundaries;
- negative/adversarial fixtures where missing evidence is never converted to success;
- a strict distinction between deterministic architectural certification and arbitrary external semantic truth;
- public API, CLI, JSON schema, release/source gates, documentation, and regression coverage;
- an experimental `aasm.sii.v1 / 0.2.0` participation-plane preview included as a certification target before activation;
- explicit SII adversarial checks for producer-controlled fingerprints, identity-reset attempts, self-measurement, forged reuse telemetry, resource-to-authority escalation, and outcome farming;
- expected SII `INCONCLUSIVE` status while actor-authority binding and ResourceLease enforcement remain unimplemented;
- no new kernel runtime: `runtime_v41.AASMEngine` remains the active engine.

The v0.43 layer distinguishes architectural stress success from semantic certification. It does not reinterpret the synthetic v0.42 reference domains as proof that arbitrary real-world domain data or conclusions are correct.

## v0.44.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics

**Next.** Graduate SII from experimental certification target to enforceable participation plane without creating a second authority system.

Required graduation work:

1. bind proposer and measurement identities to durable governed AASM principals;
2. resolve measurement authority from existing AASM authority/capability state rather than caller-supplied strings;
3. bind ResourceLease context budgets to v0.40 context projection;
4. bind parallel-candidate and scheduling budgets to the existing resource/scheduler path;
5. bind solver-class/resource privileges to the existing v0.39 capability/lease boundary;
6. move scoring thresholds/weight profiles into explicit versioned policy objects rather than hidden kernel constants;
7. preserve bounded-window decay so prior success never grants permanent power;
8. add adversarial fixtures for easy-task farming, colluding verifier/proposer pairs, stale-data farming, identity games, score oscillation, privilege escalation, and resource-policy bypass;
9. require `aasm certify --target sii-preview` to graduate from `INCONCLUSIVE` to `PASS` before making SII an active runtime integration surface;
10. retain the invariant that utility can buy compute/search/context, never truth or canonical-state authority.

## v0.45.0 — Cross-Run Certified Knowledge and Governed Long-Term Memory

Opt-in cross-run knowledge with immutable provenance, applicability scope, compatibility, epistemic status, retention/privacy, revocation/supersession, explicit receiving-run admission, and SII-aware resource accounting without authority inheritance.

## v0.46.0 — Semantic Solver Release Candidate

Freeze the coherent public solver contracts after replay, formal, distributed, adversarial, memory/privacy, reference-domain, certification, SII, packaging, and upgrade gates pass.
