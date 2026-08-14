# Changelog

## [0.42.0] - 2026-08-13

### Reference Domains & Reuse/Memory/Reasoning Stress Tests

- added `aasm.reference-domains.v1 / 0.1.0` and advanced `aasm.adoption.v1` to `0.18.0`;
- added deterministic offline reference stress scenarios for constraint solving, software repair, research synthesis, formal reasoning, and long-horizon memory;
- exercised durable reuse after hot-index deletion, environment/dependency/freshness invalidation, non-idempotent effect rejection, reasoning staleness, memory privacy/revocation, certificate-gated solver skipping, and exact replay;
- added explicit verification-strength enforcement so `ReuseRequest.required_strength` cannot be bypassed by a matching request fingerprint;
- added the reference-domain public API, CLI, JSON schema, executable example, architecture documentation, and regression suite;
- kept the v0.41 solver runtime as the kernel rather than introducing a parallel v0.42 scheduler/reducer/truth path.

## [0.41.0] - 2026-08-13

### Domain-Neutral Solver Loop and Deterministic Reuse Plane

- added `aasm.reuse.v1 / 0.1.0`, `aasm.reuse.certificate.v1 / 0.1.0`, and `aasm.solver.loop.v1 / 0.1.0`;
- added canonical reuse candidates over existing Evidence, Reasoning Artifacts, and Hierarchical Memory with POLICY/CONTROLLER admission;
- added exact, idempotent, explicit-subsumption, and certified-equivalence reuse modes;
- added deterministic scope, privacy, environment, dependency, freshness, source-validity, and effect-safety validation;
- added durable reuse certificates, durable reuse reporting, reuse telemetry, and a disposable non-authoritative `HotReuseIndex`;
- added a solver step that checks reusable prior work before capability execution while preserving the existing scheduler, reducer, event log, and truth stores;
- added bounded TLA+ and Promela/SPIN reuse-plane assurance and v0.41 regression coverage;
- advanced `aasm.adoption.v1` to `0.17.0`.

## [0.40.0] - 2026-08-13

### Hierarchical Memory, Reasoning Frontier, and Context Projection

- added `aasm.memory.hierarchical.v1 / 0.1.0`, `aasm.memory.index.v1 / 0.1.0`, `aasm.reasoning.frontier.v1 / 0.1.0`, and `aasm.context.projection.v1 / 0.1.0`;
- added durable sensory, working, episodic, semantic, and procedural memory;
- required canonical mutations to follow existing Decision → Obligation → Evidence authority;
- restricted semantic memory to V37 `AUTHORIZED` reasoning artifacts and projected V38 staleness into memory visibility;
- added scope/principal privacy, deterministic retention, tombstone forgetting, derived retrieval indexes, bounded Reasoning Frontier, bounded Context Projection, replay/restart, CLI/server bindings, schemas, conformance, and formal assurance;
- preserved legacy `DPMemory`/`memo_*` APIs as the algorithmic cache;
- advanced `aasm.adoption.v1` to `0.16.0`.

## [0.39.0] - 2026-08-13

Typed Protocol, Capability ABI, and Formal Verification Workers. Added typed pattern/capability/formal verification contracts, leased solver execution, provenance-bearing formalization, solver identity, proof-strength semantics, and no solver auto-authorization. Adoption `0.15.0`.

## [0.38.0] - 2026-08-13

Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance. Added dependency/impact/lineage, plan-before-apply truth maintenance, descendant-only invalidation, obligation reopening, reactive derivation, and semantic memory signals. Adoption `0.14.0`.

## [0.37.0] - 2026-08-13

Reasoning Artifacts and Epistemic Admission. Added typed reasoning artifacts, independent verification, policy authorization, ReasoningCommit, replay/provenance, and self-verification rejection. Adoption `0.13.0`.

## [0.36.0] - 2026-08-12

Semantic Compiler SDK. Added deterministic source compilation and proposal-only admission boundary. Adoption `0.12.0`.

## [0.35.0] - 2026-08-12

Semantic Problem Model Foundations. Added domain/problem models, deterministic fingerprints, capability gaps, contradictions, and event-sourced admission. Adoption `0.11.0`.

Earlier history is preserved in repository history and the archived changelog files.
