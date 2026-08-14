# AASM Roadmap

AASM is currently **v0.46.0 / experimental**.

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
- **v0.46.0 Advanced Solver Control & Search Artifacts — Current — implemented**

## v0.44.0 — Heterogeneous Optimization Solver Portfolio

Delivered the AASM-owned SAT/CP-SAT/MILP canonical IR, direct native CaDiCaL, OR-Tools CP-SAT, and HiGHS providers, Capability ABI admission, existing resource/worker/TaskLease execution, independent assignment checking, Evidence-only solver results, optimization reuse, exact replay, real-backend CI, and bounded formal assurance. Existing Z3, cvc5, Vampire, and Lean 4 formal workers remained active.

## v0.45.0 — Convex Optimization & Modeling Adapters

Delivered governed CVXPY LP/QP/SOC execution, a translation-only PuLP import boundary, independent result checking, real Python 3.13 backend coverage, and preservation of the direct v0.44 solver paths.

## v0.46.0 — Advanced Solver Control & Search Artifacts

Delivered:

1. `aasm.optimization.advanced.v1 / 0.1.0`;
2. `solver.sat.fast@0.1.0` backed by real Kissat through PySAT's dedicated `Kissat404` binding;
3. `solver.sat.incremental@0.1.0` backed by incremental CaDiCaL;
4. exact SAT assumptions and UNSAT core extraction;
5. conflict and decision budgets for incremental SAT;
6. bounded in-process CaDiCaL session reuse;
7. learned SAT state explicitly classified as `EPHEMERAL_PERFORMANCE_ONLY`;
8. `solver.cp_sat.scheduling@0.1.0` with fixed/optional intervals;
9. CP-SAT `NO_OVERLAP` and `CUMULATIVE` constraints;
10. search-worker and deterministic-time controls plus conflict/branch/time telemetry;
11. `solver.milp.advanced@0.1.0` with warm start submission;
12. HiGHS MIP relative-gap target and node limit;
13. primal/dual bound, MIP gap, node, and simplex-iteration telemetry;
14. `solver.convex.advanced@0.1.0` with factorized general PSD quadratic minimization and NSD maximization;
15. cross terms through weighted squares of linear forms;
16. affine second-order-cone constraints `||A x + b||₂ <= cᵀx + d`;
17. canonical `AdvancedSolverRequest` / `AdvancedSolverResult` identities carrying UNSAT core, best bound, relative gap, and telemetry;
18. provider/resource/worker/TaskLease execution through the existing AASM scheduler;
19. exact lease-expiry, supersession, implementation-binding, collision, and replay hardening;
20. independent AASM validation before successful advanced results become Evidence;
21. advanced results remain `EVIDENCE_ONLY` under `SEARCH_STATE_NEVER_PROMOTES_TRUTH`;
22. reuse through the existing v0.41 `OPTIMIZATION_RESULT` candidate/certificate path;
23. real backend CI for Kissat, incremental CaDiCaL, CP-SAT scheduling, advanced HiGHS, and advanced CVXPY;
24. preservation of v0.44 direct solver, v0.45 CVXPY/PuLP, and v0.39 Z3/cvc5/Vampire/Lean pathways;
25. public/CLI/schema/docs/release and formal source-gate coverage.

### Solver work still worth doing

The remaining solver-depth work is now narrower and can be introduced as explicit governed contracts:

- durable learned-clause provenance without pretending ephemeral clauses are truth;
- pseudo-Boolean/cardinality native representations;
- richer CP-SAT scheduling constructs and hints/solution callbacks where determinism is defined;
- MILP LP-basis and cut-pool exchange with provenance and numerical-compatibility checks;
- proof logging / certificate checking for SAT UNSAT and optimization infeasibility;
- solver portfolio racing and selection under deterministic budget policy;
- cross-solver translation certificates and certified bound/conflict exchange;
- raw matrix-form PSD/NSD quadratic input with deterministic canonicalization;
- additional conic problem families where independent validation is available.

## v0.47.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics

**Next.** Graduate SII from the experimental certification target to an enforceable participation plane over the now-concrete solver and reasoning resource surfaces.

Required graduation work:

1. bind proposer and measurement identities to durable governed AASM principals;
2. resolve measurement authority from AASM authority/capability state rather than caller-supplied strings;
3. bind ResourceLease context budgets to v0.40 context projection;
4. bind parallel-candidate and scheduling budgets to the existing resource/scheduler path;
5. bind solver privileges to the v0.39–v0.46 capability and TaskLease boundaries;
6. meter real resources: SAT conflict/decision budgets, incremental-session eligibility, CP-SAT deterministic time/search workers, MILP node/gap budgets, convex solver time, formal verification, model calls, context, and portfolio width;
7. externalize scoring thresholds and weight profiles into versioned policy;
8. preserve bounded-window decay so old success never grants permanent compute privilege;
9. adversarially test farming, collusion, identity reset, stale data, score oscillation, privilege escalation, resource-policy bypass, solver-budget laundering, and easy-problem farming;
10. require `aasm certify --target sii-preview` to graduate from `INCONCLUSIVE` to `PASS` before authority-adjacent resource control is activated;
11. preserve the invariant that utility can buy compute/search/context, never truth or canonical-state authority.

## v0.48.0 — Cross-Run Certified Knowledge & Governed Long-Term Memory

Opt-in cross-run knowledge with immutable provenance, applicability scope, compatibility, epistemic status, privacy/retention, revocation/supersession, explicit receiving-run admission, and SII-aware resource accounting without authority inheritance.

## v0.49.0 — Semantic Solver Release Candidate

Freeze the coherent public solver contracts after replay, formal, distributed, adversarial, memory/privacy, reference-domain, certification, native optimization, convex/modeling adapters, advanced solver control, SII, packaging, and upgrade gates pass.
