# AASM Roadmap

AASM is currently **v0.48.1 / experimental**.

## Released

- v0.35.0 Semantic Problem Model Foundations
- v0.36.0 Semantic Compiler SDK
- v0.37.0 Reasoning Artifacts and Epistemic Admission
- v0.38.0 Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- v0.39.0 Typed Capability ABI and Formal Verification Workers
- v0.40.0 Hierarchical Memory, Reasoning Frontier, and Context Projection
- v0.41.0 Domain-Neutral Solver Loop and Deterministic Reuse Plane
- v0.42.0 Reference Domains & Reuse/Memory/Reasoning Stress Tests
- v0.43.0 Semantic Conformance, Adversarial Domains, and Certification
- v0.44.0 Heterogeneous Optimization Solver Portfolio
- v0.45.0 Convex Optimization & Modeling Adapters
- v0.46.0 Advanced Solver Control & Search Artifacts
- v0.47.0 Governed Symbiotic Intelligence & Intelligence Economics
- v0.47.1 Apache-2.0 License Transition
- v0.48.0 Cross-Run Certified Knowledge & Governed Long-Term Memory
- **v0.48.1 Project-Wide Apache-2.0 Policy Correction — Current — implemented**

## v0.44.0 — Heterogeneous Optimization Solver Portfolio

Delivered the AASM-owned SAT/CP-SAT/MILP canonical IR, direct native CaDiCaL, OR-Tools CP-SAT, and HiGHS providers, existing Capability ABI/resource/worker/TaskLease execution, independent checking, Evidence-only results, certified reuse, real-backend CI, and formal assurance.

## v0.45.0 — Convex Optimization & Modeling Adapters

Delivered governed CVXPY LP/QP/SOC execution and a translation-only PuLP import boundary while preserving the direct native solver paths.

## v0.46.0 — Advanced Solver Control & Search Artifacts

Delivered Kissat fast SAT, incremental CaDiCaL assumptions/UNSAT cores/session reuse, CP-SAT scheduling, HiGHS warm starts/bound-gap telemetry, richer CVXPY forms, and `SEARCH_STATE_NEVER_PROMOTES_TRUTH`.

## v0.47.0 — Governed Symbiotic Intelligence & Intelligence Economics

Graduated SII to `aasm.sii.v1 / 0.3.0` / `GOVERNED_ENFORCED`: durable principals, versioned scoring/resource policy, real context/scheduler/native-solver/formal budget enforcement, no self-measurement, `authority_reward = NEVER`, and `REQUIRED_VERIFICATION_NEVER_REDUCED_BY_SII`.

## v0.47.1 — Apache-2.0 License Transition

Preserved the v0.47 runtime while introducing Apache License 2.0 packaging with PEP 639/SPDX metadata, packaged `LICENSE`/`NOTICE`, contribution alignment, and release gates. The project-wide policy is now stated explicitly in `LICENSE_POLICY.md`: to the extent AASM has the necessary relicensing rights, prior AASM versions first distributed under MIT are also offered under Apache-2.0. Earlier MIT grants remain valid for their recipients, but prior AASM versions are not designated MIT-only.

## v0.48.0 — Cross-Run Certified Knowledge & Governed Long-Term Memory

Delivered:

1. `aasm.knowledge.cross-run.v1 / 0.1.0` immutable envelopes with source-run/machine/scope provenance;
2. `aasm.knowledge.cross-run.admission.v1 / 0.1.0` receiving-run validation certificates;
3. `aasm.principal.cross-run-map.v1 / 0.1.0` stable source→local principal mapping;
4. explicit applicability scope, privacy, environment, dependency, freshness, retention, and verification-strength checks;
5. invariant `source_authority = PROVENANCE_ONLY_NEVER_INHERITED`;
6. ordinary Decision → POLICY/CONTROLLER authorization → Obligation → Evidence receiving admission;
7. deterministic envelope/bundle/certificate/principal-map fingerprints;
8. foreign semantic content remaining Evidence until receiving-run AUTHORIZED reasoning exists;
9. ordinary v0.40 memory authorization/commit for materialization;
10. ordinary v0.41 `ReuseCandidate` / `ReuseCertificate` execution reuse rather than a second cache;
11. exact v0.41 verification-strength semantics preserved across runs;
12. receiving validator ID/version carried into the ordinary reuse certificate;
13. receiving POLICY/CONTROLLER admission for source revocation/supersession signals;
14. revocation blocking already-hot cross-run reuse candidates;
15. revocation tombstoning already-materialized local memory through the existing FORGET path;
16. deterministic source-side delta generation when exported source memory ceases to be ACTIVE;
17. stable cross-run principal rebinding rejection;
18. exact source-principal matching for SII reputation envelopes;
19. cross-run SII reputation stored as `CROSS_RUN_REFERENCE_ONLY` accounting;
20. `truth_authority = NONE` and `resource_entitlement = NONE` for imported reputation;
21. explicit `used_by_sii_resource_lease = false` so historical reputation cannot buy local compute;
22. transport boundary documented: untrusted transport still requires authentication/signed provenance outside the envelope format;
23. dependency-neutral conformance and adversarial regression fixtures;
24. JSON Schema 2020-12 contracts;
25. dedicated `Cross-Run Knowledge` GitHub Actions workflow;
26. bounded TLA+ and Promela/SPIN assurance for authority, admission, privacy, revocation, materialization, reuse, and reputation boundaries;
27. public API/CLI surfaces and adoption contract `aasm.adoption.v1 / 0.24.0`;
28. preservation of the entire v0.39 formal, v0.40 memory, v0.41 reuse, v0.44–v0.46 solver, and v0.47 SII pathways;
29. preservation of Apache-2.0 / PEP 639 / NOTICE packaging from v0.47.1.

## v0.48.1 — Project-Wide Apache-2.0 Policy Correction

Corrects the licensing-policy description without changing runtime semantics:

1. adds `LICENSE_POLICY.md` as the explicit project-wide Apache-2.0 declaration;
2. declares prior AASM versions also offered under Apache-2.0 to the extent AASM has the necessary relicensing rights;
3. states that previously granted MIT permissions remain valid for recipients;
4. removes the incorrect implication that those surviving MIT permissions make old AASM versions MIT-only;
5. removes the incorrect implication that v0.47.1 is the first/only Apache-2.0 point in AASM history;
6. adds release-gate checks requiring the project-wide declaration;
7. adds forbidden-text regression checks so the incorrect historical-policy framing cannot silently return;
8. preserves package/runtime contracts at the v0.48 semantic level and keeps adoption at `aasm.adoption.v1 / 0.24.0`.

### Explicit v0.48 limits

- the cross-run envelope is not itself a network authentication protocol;
- source-run authority never becomes receiving-run authority;
- cross-run reputation does not automatically change local SII scoring tiers;
- v0.48 reuse begins with exact semantic payload equality rather than generalized cross-run subsumption;
- source revocation must be admitted by receiving policy before changing receiving-run eligibility;
- the receiving run may retain history/provenance even after active memory/reuse eligibility is revoked.

### Solver work still worth doing

- durable learned-clause provenance with proof/certificate boundaries;
- pseudo-Boolean/cardinality native representations;
- MILP LP-basis and cut-pool exchange with provenance/numerical compatibility;
- SAT proof logging and optimization infeasibility certificates;
- deterministic solver portfolio racing under governed budgets;
- cross-solver translation certificates and certified bound/conflict exchange;
- raw matrix-form PSD/NSD quadratic input with deterministic canonicalization;
- additional conic problem families where independent validation is available.

## v0.49.0 — Semantic Solver Release Candidate

**Next.** Freeze the coherent public solver/control contracts after replay, formal, distributed, adversarial, memory/privacy, reference-domain, certification, native optimization, convex/modeling adapters, advanced solver control, governed SII, project-wide Apache packaging/policy, and cross-run knowledge gates all pass.

Release-candidate work should focus on compatibility freeze, benchmark evidence, upgrade/migration guarantees, final cross-backend certification, documentation consolidation, and removal of claims that are not backed by a reproducible gate.
