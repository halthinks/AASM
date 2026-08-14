# AASM Roadmap

AASM is currently **v0.45.0 / experimental**.

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
- **v0.45.0 Convex Optimization & Modeling Adapters — Current — implemented**

## v0.44.0 — Heterogeneous Optimization Solver Portfolio

Delivered the AASM-owned SAT/CP-SAT/MILP canonical IR, direct native CaDiCaL, OR-Tools CP-SAT, and HiGHS providers, Capability ABI admission, existing resource/worker/TaskLease execution, independent assignment checking, Evidence-only solver results, optimization reuse, exact replay, real-backend CI, and bounded formal assurance. Existing Z3, cvc5, Vampire, and Lean 4 formal workers remained active.

## v0.45.0 — Convex Optimization & Modeling Adapters

Delivered:

1. `aasm.optimization.convex.v1 / 0.1.0`;
2. `solver.convex@0.1.0` as an OPERATOR capability;
3. real CVXPY execution through the existing AASM resource/worker/TaskLease path;
4. scalar continuous convex variables with explicit bounds;
5. linear equality and inequality constraints;
6. diagonal positive-semidefinite quadratic minimization;
7. diagonal negative-semidefinite quadratic maximization;
8. constant-radius second-order-cone constraints;
9. independent AASM feasibility and objective rechecking before Evidence admission;
10. CVXPY backend identity recording (OSQP / CLARABEL / SCS as applicable);
11. `aasm.adapter.pulp.v1 / 0.1.0`;
12. PuLP `TRANSLATION_ONLY` authority with solver execution explicitly `NEVER`;
13. conversion of supported finite-bounded PuLP LP/MILP models into the existing v0.44 `OptimizationModel`;
14. rejection of unbounded PuLP variables rather than semantic large-bound approximation;
15. post-import native AASM routing, including real PuLP→HiGHS execution;
16. use of the existing `OPTIMIZATION_RESULT` reuse kind and certificate-gated skip path for convex work;
17. real Python 3.13 CI coverage for CVXPY QP, CVXPY SOC, PuLP import, and PuLP→HiGHS;
18. public API, CLI, schemas, release/source gates, docs, and regression coverage;
19. preservation of direct CaDiCaL, CP-SAT, and HiGHS paths instead of wrapping them through CVXPY/PuLP;
20. preservation of Z3/cvc5/Vampire/Lean formal verification.

### Solver work still worth doing

The next solver-specific extensions remain explicit performance/certification work rather than hidden backend metadata:

- incremental SAT assumptions, UNSAT cores, learned-clause provenance, pseudo-Boolean/cardinality constraints;
- CP-SAT interval/no-overlap/cumulative scheduling primitives and deterministic-time/search budgets;
- MILP incumbents, node/bound telemetry, warm starts, bases, cuts, and portfolio racing;
- broader convex canonical forms, affine SOC expressions, general PSD quadratic forms, and eventually additional conic forms;
- proof logging/certificate checking for SAT and optimization infeasibility;
- cross-solver translation certificates and certified conflict/bound reuse.

## v0.46.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics

**Next.** Graduate SII from the experimental certification target to an enforceable participation plane over real solver and reasoning resources.

Required graduation work:

1. bind proposer and measurement identities to durable governed AASM principals;
2. resolve measurement authority from AASM authority/capability state rather than caller-supplied strings;
3. bind ResourceLease context budgets to v0.40 context projection;
4. bind parallel-candidate and scheduling budgets to the existing resource/scheduler path;
5. bind solver privileges to v0.39/v0.44/v0.45 capability and TaskLease boundaries;
6. expose real budgets for SAT conflicts/search, CP-SAT deterministic time, MILP nodes/iterations, convex solver time, formal verification, model calls, context, and portfolio width;
7. externalize scoring thresholds and weight profiles into versioned policy;
8. preserve bounded-window decay;
9. adversarially test farming, collusion, identity reset, stale data, score oscillation, privilege escalation, and resource-policy bypass;
10. require `aasm certify --target sii-preview` to graduate from `INCONCLUSIVE` to `PASS` before authority-adjacent resource control is activated;
11. preserve the invariant that utility can buy compute/search/context, never truth or canonical-state authority.

## v0.47.0 — Cross-Run Certified Knowledge & Governed Long-Term Memory

Opt-in cross-run knowledge with immutable provenance, applicability scope, compatibility, epistemic status, privacy/retention, revocation/supersession, explicit receiving-run admission, and SII-aware resource accounting without authority inheritance.

## v0.48.0 — Semantic Solver Release Candidate

Freeze the coherent public solver contracts after replay, formal, distributed, adversarial, memory/privacy, reference-domain, certification, native optimization, convex/modeling adapters, SII, packaging, and upgrade gates pass.
