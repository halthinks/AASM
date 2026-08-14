# Changelog

## [0.48.0] - 2026-08-14

### Cross-Run Certified Knowledge & Governed Long-Term Memory

- advanced the package/public surface to `0.48.0` and `aasm.adoption.v1` to `0.24.0`;
- added `aasm.knowledge.cross-run.v1 / 0.1.0`, `aasm.knowledge.cross-run.admission.v1 / 0.1.0`, and `aasm.principal.cross-run-map.v1 / 0.1.0`;
- added immutable cross-run envelopes with source-run/machine/scope identity, exact memory/evidence/artifact provenance, fingerprints, environment/dependency declarations, privacy, retention/freshness, verification strength, and `authority_transfer = NEVER`;
- added deterministic receiving-run applicability validation and `CrossRunAdmissionCertificate` with validator ID/version;
- requires ordinary AASM Decision → POLICY/CONTROLLER authorization → Obligation → Evidence before foreign knowledge is admitted;
- prevents foreign semantic content from becoming local semantic memory unless receiving-run reasoning artifacts are already `AUTHORIZED`;
- materializes admitted knowledge only through the existing v0.40 memory operation/authorization/commit path;
- registers cross-run execution reuse only through the existing v0.41 `ReuseCandidate` / `ReuseCertificate` path;
- preserves v0.41 exact verification-strength matching rather than silently downcasting stronger foreign proof state;
- carries source/receiving run, envelope, and admission-validator provenance into the ordinary reuse certificate;
- adds source revocation/supersession signals requiring receiving POLICY/CONTROLLER admission;
- makes admitted revocation operational by blocking already-hot cross-run reuse and tombstoning already-materialized local memories through v0.40 FORGET;
- adds source-side delta generation for exported source memories that cease to be ACTIVE;
- adds stable cross-run principal mapping with `authority_transfer = NEVER` and `resource_entitlement_transfer = NEVER`;
- requires SII reputation envelopes to name the exact source principal and match the admitted stable mapping;
- stores cross-run SII reputation as `CROSS_RUN_REFERENCE_ONLY` with `truth_authority = NONE`, `resource_entitlement = NONE`, and `used_by_sii_resource_lease = false`;
- documents that the envelope format is not itself a network authentication protocol;
- added JSON schemas, public/CLI contracts, dependency-neutral conformance, adversarial tests, and a dedicated Cross-Run Knowledge CI workflow;
- added bounded TLA+ and Promela/SPIN invariants for authority inheritance, admission, privacy, revocation, materialization, reuse, and SII reputation separation;
- preserved all v0.39 formal, v0.40 memory, v0.41 reuse, v0.44–v0.46 native solver, and v0.47 SII pathways;
- preserved Apache-2.0 / PEP 639 / packaged `LICENSE` + `NOTICE` behavior from v0.47.1;
- moved the Semantic Solver Release Candidate to v0.49.

## [0.47.1] - 2026-08-14

### Apache-2.0 License Transition

- changed the active AASM project/distribution license from MIT to Apache License 2.0 (`Apache-2.0`);
- replaced the root `LICENSE` with the standard Apache License 2.0 text and added packaged `NOTICE` attribution;
- uses PEP 639/SPDX `license = "Apache-2.0"` with no legacy `License :: ...` classifier;
- preserved every v0.47.0 runtime/authority/solver/SII behavior unchanged;
- preserved the already-published v0.47.0 release as the historical MIT-licensed artifact.

## [0.47.0] - 2026-08-14

### Governed Symbiotic Intelligence & Intelligence Economics

- advanced `aasm.adoption.v1` to `0.23.0`, `aasm.certification.v1` to `0.2.0`, and SII to `aasm.sii.v1 / 0.3.0` / `GOVERNED_ENFORCED`;
- added durable principal binding, resolved measurement authority, self-measurement rejection, versioned scoring/resource policy, real solver/context/formal budget enforcement, enforcement Evidence, and `REQUIRED_VERIFICATION_NEVER_REDUCED_BY_SII`;
- preserved all native/formal solver paths outside SII truth authority.

## [0.46.0] - 2026-08-14

### Advanced Solver Control & Search Artifacts

- added Kissat fast SAT, incremental CaDiCaL assumptions/UNSAT cores/session reuse, CP-SAT scheduling, HiGHS warm starts and bound/gap/node telemetry, and advanced CVXPY forms;
- kept search state `EPHEMERAL_PERFORMANCE_ONLY` under `SEARCH_STATE_NEVER_PROMOTES_TRUTH`.

## [0.45.0] - 2026-08-14

### Convex Optimization & Modeling Adapters

- added governed CVXPY LP/QP/SOC execution and a `TRANSLATION_ONLY` PuLP import boundary.

## [0.44.0] - 2026-08-14

### Heterogeneous Optimization Solver Portfolio

- added canonical Boolean/integer/continuous optimization IR plus real CaDiCaL, OR-Tools CP-SAT, and HiGHS providers through the existing Capability ABI/resource/worker/TaskLease path;
- made optimization results `EVIDENCE_ONLY` and connected them to certificate-gated reuse.

## [0.43.0] - 2026-08-14

Semantic Conformance, Adversarial Domains, and Certification. Added explicit `PASS | FAIL | INCONCLUSIVE`, reference-domain/reuse/truth/formal certification, and the original experimental SII certification target.

## [0.42.0] - 2026-08-13

Reference Domains & Reuse/Memory/Reasoning Stress Tests. Added five deterministic offline stress domains and verification-strength reuse enforcement.

## [0.41.0] - 2026-08-13

Domain-Neutral Solver Loop and Deterministic Reuse Plane. Added canonical requests/candidates/certificates and deterministic applicability validation.

## [0.40.0] - 2026-08-13

Hierarchical Memory, Reasoning Frontier, and Context Projection. Added governed memory kinds, privacy/retention/tombstones, deterministic indexes, context projection, replay, schemas, conformance, and formal assurance.

## [0.39.0] - 2026-08-13

Typed Protocol, Capability ABI, and Formal Verification Workers. Added typed capability contracts and leased Z3/cvc5/Vampire/Lean execution with Evidence-only solver authority.

## [0.38.0] - 2026-08-13

Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance. Added descendant-only invalidation, obligation reopening, reactive derivation, and semantic memory signals.

## [0.37.0] - 2026-08-13

Reasoning Artifacts and Epistemic Admission. Added typed reasoning artifacts, independent verification, policy authorization, ReasoningCommit, replay/provenance, and self-verification rejection.

## [0.36.0] - 2026-08-12

Semantic Compiler SDK. Added deterministic source compilation and proposal-only admission boundary.

## [0.35.0] - 2026-08-12

Semantic Problem Model Foundations. Added domain/problem models, deterministic fingerprints, capability gaps, contradictions, and event-sourced admission.

Earlier history is preserved in repository history and archived changelog files.
