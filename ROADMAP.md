# AASM Roadmap

AASM is currently **v0.47.0 / experimental**.

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
- **v0.47.0 Governed Symbiotic Intelligence & Intelligence Economics — Current — implemented**

## v0.44.0 — Heterogeneous Optimization Solver Portfolio

Delivered the AASM-owned SAT/CP-SAT/MILP canonical IR, direct native CaDiCaL, OR-Tools CP-SAT, and HiGHS providers, Capability ABI admission, existing resource/worker/TaskLease execution, independent assignment checking, Evidence-only solver results, optimization reuse, exact replay, real-backend CI, and bounded formal assurance. Existing Z3, cvc5, Vampire, and Lean 4 formal workers remained active.

## v0.45.0 — Convex Optimization & Modeling Adapters

Delivered governed CVXPY LP/QP/SOC execution, a translation-only PuLP import boundary, independent result checking, real Python 3.13 backend coverage, and preservation of the direct v0.44 solver paths.

## v0.46.0 — Advanced Solver Control & Search Artifacts

Delivered Kissat fast SAT, incremental CaDiCaL assumptions/UNSAT cores/session reuse, CP-SAT scheduling primitives and deterministic-time/search-worker controls, HiGHS warm starts and bound/gap/node telemetry, richer factorized PSD/NSD + affine-SOC CVXPY models, and durable advanced result/reuse/lease hardening under `SEARCH_STATE_NEVER_PROMOTES_TRUTH`.

## v0.47.0 — Governed Symbiotic Intelligence & Intelligence Economics

Delivered:

1. `aasm.sii.v1 / 0.3.0` with stability `GOVERNED_ENFORCED`;
2. `aasm.certification.v1 / 0.2.0` with governed SII included in default certification;
3. durable `SIIPrincipalBinding` records admitted only by existing POLICY/CONTROLLER authority;
4. stable-principal rebinding rejection;
5. measurement authority resolution from durable principal state instead of a caller-supplied authority string;
6. explicit rejection of self-measurement at principal identity level;
7. versioned durable `SIIScoringPolicy` objects with active-policy selection;
8. default/exploration/exploitation/formal scoring profiles preserved as policy data;
9. bounded performance windows retained so old success cannot grant permanent compute privilege;
10. durable `GovernedResourceLease` records bound to proposer, principal, policy version, performance window, utility, and tier;
11. context budgets enforced through the existing v0.40 context projection;
12. scheduler priority enforced through ordinary `TaskDemand.priority`;
13. max outstanding discretionary candidate count enforced before queue growth;
14. incremental CaDiCaL conflict-budget enforcement;
15. incremental CaDiCaL decision-budget enforcement;
16. native solver timeout enforcement;
17. CP-SAT deterministic-time enforcement;
18. CP-SAT search-worker enforcement;
19. HiGHS MIP-node enforcement;
20. advanced convex solve-time enforcement;
21. discretionary formal-verification timeout enforcement;
22. discretionary formal provider-width enforcement;
23. explicit preservation of the ordinary policy-required formal-verification path outside SII caps;
24. invariant `REQUIRED_VERIFICATION_NEVER_REDUCED_BY_SII`;
25. durable `ENFORCEMENT` Evidence connecting SII ResourceLease records to solver/formal requests;
26. SII lease/policy/principal/enforcement provenance copied into the ordinary task and TaskLease metadata;
27. `authority_reward = NEVER` attached to governed execution provenance;
28. resource leases permanently fixed to `PROPOSER` authority with direct truth promotion/state mutation/self-verification false;
29. `request_sii_advanced_optimization()` compiling resource policy into the real v0.46 advanced solver IR/request path;
30. `request_sii_formal_verification()` as an explicitly discretionary governed formal path;
31. `sii_context()` compiling resource policy into the real v0.40 context path;
32. current `sii-contract` reporting the governed v0.47 contract while the v0.43 preview implementation remains importable;
33. `sii-preview` certification retained as a compatibility alias to the governed graduation fixture;
34. adversarial certification for unbound measurement actors, authority escalation, native-budget bypass, scheduler-budget bypass, and replay;
35. public API, CLI, schemas, docs, release/source gates, and regression coverage;
36. preservation of all v0.44–v0.46 native solver and v0.39 formal-verification pathways rather than routing them through a new SII executor.

### Deliberate SII limits after v0.47

The major graduation gaps are closed, but these remain explicit future work rather than hidden claims:

- model calls are represented in SII resource policy but model execution is not yet a universal first-class TaskLease provider across every adapter;
- learned SAT clauses, MILP cuts/bases, and solver-specific search state remain performance artifacts unless separately certified/admitted;
- collusion/easy-problem farming need larger empirical/reference-domain campaigns beyond deterministic contract fixtures;
- resource policy currently applies to SII-discretionary work and must never intercept correctness-required verification in a way that can weaken it;
- cross-run performance/resource reputation remains run-local until cross-run identity/knowledge admission is formalized.

### Solver work still worth doing

- durable learned-clause provenance with proof/certificate boundaries;
- pseudo-Boolean/cardinality native representations;
- MILP LP-basis and cut-pool exchange with provenance/numerical compatibility;
- SAT proof logging and optimization infeasibility certificates;
- deterministic solver portfolio racing under governed budgets;
- cross-solver translation certificates and certified bound/conflict exchange;
- raw matrix-form PSD/NSD quadratic input with deterministic canonicalization;
- additional conic problem families where independent validation is available.

## v0.48.0 — Cross-Run Certified Knowledge & Governed Long-Term Memory

**Next.** Extend durable knowledge across run boundaries without allowing prior-run authority or stale context to leak into a receiving run.

Planned work:

1. immutable cross-run knowledge envelopes with source-run identity and exact provenance;
2. explicit applicability scope, environment/dependency compatibility, freshness, privacy, and retention metadata;
3. receiving-run admission rather than automatic inheritance;
4. revocation and supersession propagation across retained knowledge;
5. cross-run reuse certificates with exact validator/version provenance;
6. stable governed principal identity mapping without making SII reputation an authority credential;
7. separate cross-run SII performance/resource accounting from truth admission;
8. provenance-preserving memory compaction and summarized knowledge objects;
9. certified long-term procedural/semantic memory with invalidation boundaries;
10. adversarial checks for stale-run poisoning, identity conflation, privacy leakage, revocation loss, and authority inheritance;
11. deterministic export/import and replay fixtures;
12. reference-domain tests that demonstrate genuine cross-run savings without truth drift.

## v0.49.0 — Semantic Solver Release Candidate

Freeze the coherent public solver/control contracts after replay, formal, distributed, adversarial, memory/privacy, reference-domain, certification, native optimization, convex/modeling adapters, advanced solver control, governed SII, packaging, upgrade, and cross-run knowledge gates pass.
