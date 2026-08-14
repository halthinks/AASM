# AASM Roadmap

AASM is currently **v0.51.0 / Governed Solution Pools & Complete Enumeration**.

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
- v0.48.1 Project-Wide Apache-2.0 Policy Correction
- v0.49.0 Semantic Solver Release Candidate
- v0.50.0 Proof-Carrying Solver Claims
- **v0.51.0 Governed Solution Pools & Complete Enumeration — Current**

## v0.44.0 — Heterogeneous Optimization Solver Portfolio

Delivered AASM-owned SAT/CP-SAT/MILP canonical IR; direct CaDiCaL, OR-Tools CP-SAT, and HiGHS providers; existing Capability ABI/resource/worker/TaskLease execution; independent checking; Evidence-only results; certified reuse; real-backend CI; and formal assurance.

## v0.45.0 — Convex Optimization & Modeling Adapters

Delivered governed CVXPY LP/QP/SOC execution and a translation-only PuLP import boundary while preserving direct native solver paths.

## v0.46.0 — Advanced Solver Control & Search Artifacts

Delivered Kissat fast SAT, incremental CaDiCaL assumptions/UNSAT cores/session reuse, CP-SAT scheduling, HiGHS warm starts/bound-gap telemetry, richer CVXPY forms, and `SEARCH_STATE_NEVER_PROMOTES_TRUTH`.

## v0.47.0 — Governed Symbiotic Intelligence & Intelligence Economics

Graduated SII to `aasm.sii.v1 / 0.3.0` / `GOVERNED_ENFORCED`: durable principals, versioned scoring/resource policy, real context/scheduler/native-solver/formal budget enforcement, self-measurement rejection, `authority_reward = NEVER`, and `REQUIRED_VERIFICATION_NEVER_REDUCED_BY_SII`.

## v0.47.1 / v0.48.1 — Project-Wide Apache-2.0 Licensing

AASM's project-wide declared license is Apache-2.0 through `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`. To the extent AASM has the necessary relicensing rights, prior AASM versions first distributed under MIT are also offered under Apache-2.0. Previously granted MIT permissions remain valid for their recipients; prior AASM versions are not designated MIT-only.

## v0.48.0 — Cross-Run Certified Knowledge & Governed Long-Term Memory

Delivered immutable cross-run knowledge envelopes; receiving-run applicability/admission certificates; privacy/environment/dependency/freshness/verification checks; local authority admission; v0.40 governed memory materialization; v0.41 certified reuse; operational revocation/supersession; stable cross-run principal mapping; accounting-only SII reputation; dedicated Cross-Run Knowledge CI; and bounded TLA+/SPIN assurance.

## v0.49.0 — Semantic Solver Release Candidate

Delivered:

1. `aasm.semantic.solver.rc.v1 / 0.1.0` with stability `RELEASE_CANDIDATE`;
2. public adoption contract `aasm.adoption.v1 / 0.25.0`;
3. thin `SemanticSolverRCRuntimeMixin + runtime_v48.AASMEngine` composition with no new scheduler/reducer/truth/authority/solver kernel;
4. deterministic public freeze manifest over contract IDs/versions, engine methods, CLI commands, public imports, inspection surfaces, schemas, provider identities, replay expectations, and project-wide Apache licensing;
5. freeze-manifest semantic fingerprint for explicit 0.49.x compatibility review;
6. v0.41 → v0.49 replay/upgrade fixture covering event history, memoized state, and governed memory;
7. v0.47 → v0.49 replay/upgrade fixture covering SII scoring policy and principal binding;
8. v0.48 → v0.49 replay/upgrade fixture covering admitted cross-run knowledge and foreign-authority non-inheritance;
9. exact canonical replay/hash equality required for each upgrade fixture;
10. exact overlapping Boolean/integer optimization model independently solved by OR-Tools CP-SAT and HiGHS;
11. CP-SAT and MILP optimum agreement required at objective `1`;
12. CaDiCaL Boolean feasibility projection for the same core condition;
13. cross-backend law `AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE`;
14. canonical-result validation before cross-backend agreement is accepted as corroborating Evidence;
15. semantic-fingerprint workload measurement;
16. event append/replay workload measurement;
17. direct native CP-SAT execution measurement when the native stack is installed;
18. full AASM provider → request → TaskLease → native solve → validation → Evidence lifecycle measurement;
19. observed orchestration-overhead ratio recorded as environment-specific evidence;
20. invariant `AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS`;
21. benchmark policy `MEASURE_OVERHEAD_AND_SAVINGS_NO_UNGATED_SPEEDUP_CLAIM`;
22. claim policy `NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE`;
23. claim-to-gate audit for Python support, formal assurance, native solver coverage, cross-run governance, project-wide Apache policy, and RC readiness;
24. complete RC certification aggregating cross-run, semantic/adversarial, optimization, modeling, advanced-solver, overlap, upgrade, benchmark, and claim-audit results;
25. JSON Schema 2020-12 contracts for freeze manifest, benchmark report, and RC certification report;
26. public CLI surfaces for RC contract, freeze, upgrade, cross-backend, benchmark, claim audit, and complete certification;
27. dedicated `.github/workflows/rc.yml` installing real native optimization/modeling backends;
28. exact-head `aasm/semantic-solver-rc` commit status;
29. release workflow hardened to require CI + Formal Assurance + Semantic Solver RC success on the exact `main` SHA;
30. preservation of all v0.39 formal, v0.40 memory, v0.41 reuse, v0.44–v0.46 solver, v0.47 SII, and v0.48 cross-run authority semantics.

### RC limits and non-claims

- RC benchmarks measure orchestration cost; they do not establish universal performance superiority.
- AASM does not claim its orchestration layer makes native inner solver kernels faster.
- The compatibility fixture exercises stable public/durable behaviors from selected released generations; it does not freeze arbitrary undocumented private implementation details.
- Cross-backend agreement is corroborating Evidence, never voting authority.
- The cross-run envelope is not a network authentication protocol.
- Source-run authority never becomes receiving-run authority.
- Complete Pareto-frontier enumeration is not yet established.
- General governed solution pools and complete finite enumeration are not yet established.
- Arbitrary lexicographic multi-objective optimization is not yet established.
- Durable cross-run solver-native learning is not yet established.
- Proof-carrying certification for every negative, bound, or optimality claim is not yet established.

# Current Semantic-Solver Closure Program

The v0.50–v0.57 sequence closes the **currently identified** semantic-solver gap cluster. It does **not** imply that AASM is nearly complete, and it does **not** imply readiness for v1.0.

The dependency order is deliberate: proof semantics land before completeness claims; enumeration lands before Pareto completeness; cross-run native learning lands before cross-solver exchange; stabilization happens only after those capabilities exist and have adversarial evidence.

## v0.50.0 — Proof-Carrying Solver Claims

**Status: Delivered/current.**

Delivered in v0.50:

1. `aasm.solver.proof-certificate.v1 / 0.1.0` with `EXPERIMENTAL_ENFORCED` stability;
2. public adoption contract `aasm.adoption.v1 / 0.26.0`;
3. thin `ProofClaimRuntimeMixin + runtime_v49.AASMEngine` composition with no new scheduler, reducer, solver kernel, memory store, or truth authority;
4. `SolverClaim`, `SolverProofArtifact`, and `SolverClaimCertificate` exact-bound objects;
5. explicit `SOLVER_VALIDATED` versus `PROOF_CERTIFIED` levels;
6. mandatory independent-checker requirement for `PROOF_CERTIFIED`;
7. exact problem/formulation/model/result fingerprint binding;
8. AASM-owned `aasm.checker.finite-domain-exhaustive.v1 / 0.1.0` checker for bounded Boolean/integer claims;
9. exhaustive certification of supported `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims;
10. deterministic proof trace digest and independent reconstruction/recheck;
11. `UNSUPPORTED != FAIL`: continuous, uncovered, or over-budget proof modes never masquerade as failed claims;
12. false optimality and false negative claims fail closed without a proof certificate;
13. proof artifacts/certificates persisted through the existing Evidence/event history and exact replay;
14. certificate authority fixed at `EVIDENCE_ONLY`, with truth authority remaining `EXISTING_AASM_POLICY_ONLY`;
15. JSON Schema 2020-12 contracts for claims, proof artifacts, and certificates;
16. bounded TLA+ and Promela/SPIN proof-certification invariants;
17. public CLI contract/conformance commands;
18. dedicated exact-head `aasm/proof-claims` gate with applicability and adversarial tests;
19. release workflow hardened to require the proof-claims gate before publishing v0.50.

**Next planned implementation release: v0.51.0 — Governed Solution Pools & Complete Enumeration.**

Primary contract target:

```text
aasm.solver.proof-certificate.v1
```

Required scope:

1. classify solver claims explicitly: `FEASIBLE`, `INFEASIBLE`, `SAT`, `UNSAT`, `BOUNDED`, `UNBOUNDED`, `OPTIMAL`, `SUBOPTIMAL`, `UNKNOWN`;
2. separate ordinary validated solver evidence from proof-grade certification;
3. introduce durable `SolverClaimCertificate` objects bound to exact problem, formulation, solver, assumptions, tolerances, proof/bound artifact, verifier, and checker versions;
4. support proof-producing SAT/UNSAT and infeasibility/optimality paths where native backends expose suitable artifacts;
5. add independent certificate checkers rather than accepting solver self-attestation;
6. make unsupported proof modes explicit rather than silently treating solver status as proof;
7. carry exact provenance through replay, persistence, CLI, schemas, and release reports;
8. add adversarial fixtures for forged proofs, wrong formulation fingerprints, stale assumptions, mismatched tolerances, truncated artifacts, and solver/checker version incompatibility.

Hard completion criterion:

> No `UNSAT`, `INFEASIBLE`, `UNBOUNDED`, or `OPTIMAL` result may receive a proof-grade status unless an independent checker verifies a certificate covering the exact canonical problem/formulation and declared assumptions/tolerances.

## v0.51.0 — Governed Solution Pools & Complete Enumeration

**Status: Delivered/current.**

Delivered in v0.51:

1. `aasm.optimization.solution-pool.v1 / 0.1.0` and `aasm.optimization.enumeration.v1 / 0.1.0`;
2. public adoption contract `aasm.adoption.v1 / 0.27.0`;
3. thin `SolutionPoolRuntimeMixin + runtime_v50.AASMEngine` composition with no new scheduler, reducer, memory store, solver kernel, or truth authority;
4. durable `SolutionRecord`, `SolutionExclusion`, `EnumerationCursor`, `SolutionPool`, and `EnumerationCompletenessCertificate`;
5. explicit pool modes `COMPLETE_FINITE_ENUMERATION`, `BOUNDED_PARTIAL_POOL`, `TOP_K`, `DIVERSE_POOL`, and `INCUMBENT_HISTORY`;
6. deterministic assignment identity and exact deduplication;
7. durable exact-assignment no-goods for every accepted finite solution;
8. crash/restart-safe continuation from durable next-state cursors;
9. exact Evidence/event replay for pool, cursor, solutions, exclusions, and completeness certificate;
10. finite Boolean/integer exhaustion checker `aasm.checker.finite-enumeration-exhaustion.v1 / 0.1.0`;
11. `COMPLETE` forbidden until full finite-state exhaustion and independent checker PASS;
12. bounded/native/partial pools never imply completeness;
13. false completeness fails closed with explicit unseen-solution diagnostics;
14. continuous-variable complete enumeration explicitly unsupported;
15. exact oracle-known restart fixture enumerating every feasible assignment exactly once;
16. real OR-Tools CP-SAT and HiGHS iterative no-good enumeration;
17. cross-backend requirement `EXACT_SOLUTION_SET_EQUALITY_NEVER_VOTING`;
18. JSON Schema 2020-12 contracts for solution records, pools, cursors, and completeness certificates;
19. bounded TLA+ and Promela/SPIN completeness invariants;
20. dedicated exact-head `aasm/solution-pools` release gate and public contract/conformance CLI.

**Next planned implementation release: v0.52.0 — Lexicographic Multi-Objective & Pareto Solving.**

Hard completion criterion achieved:

> For finite oracle-known reference problems, AASM enumerates every satisfying solution exactly once, survives restart mid-enumeration, resumes correctly, and independently certifies that no additional finite solutions remain before reporting completeness.

## v0.52.0 — Lexicographic Multi-Objective & Pareto Solving

Primary contract targets:

```text
aasm.optimization.multi-objective.v1
aasm.optimization.frontier.v1
```

Required scope:

1. ordered objective vectors with explicit priority, sense, expression, and tolerance;
2. full lexicographic solving where each higher-priority optimum is independently fixed/certified before optimizing the next objective;
3. proof that lower-priority optimization cannot degrade higher-priority objectives outside declared tolerances;
4. exact finite Pareto-frontier enumeration built on v0.51 solution enumeration;
5. explicit frontier modes: `EXACT_FINITE_PARETO_FRONTIER`, `BOUNDED_PARTIAL_FRONTIER`, `EPSILON_APPROXIMATE_FRONTIER`;
6. nondominance checking for every admitted frontier point;
7. exhaustion/completeness evidence for exact finite frontiers;
8. deterministic frontier fingerprints and restart-safe frontier enumeration;
9. independent cross-backend frontier checks on oracle-known reference problems;
10. adversarial fixtures for dominated points, missing frontier members, tolerance abuse, priority inversion, duplicate points, and false exactness claims.

Hard completion criterion:

> On oracle-known finite multi-objective problems, AASM must return exactly the nondominated set, prove pairwise nondominance, prove exhaustion, preserve lexicographic priority semantics, survive restart, and reproduce the same frontier fingerprint across supported exact backends.

## v0.53.0 — Durable Cross-Run Solver Learning

Primary contract target:

```text
aasm.solver.learning.cross-run.v1
```

Required scope:

1. explicitly separate canonical reusable learning from solver-native accelerator state;
2. canonical transferable learning may include validated no-goods, bound tightenings, conflicts, assumption cores, incumbents, dominance exclusions, enumeration exclusions, and objective bounds;
3. native accelerator state may include learned clauses, cut pools, LP/MILP bases, branching hints, presolve hints, and native incumbents where supported;
4. every native artifact carries a compatibility envelope including problem fingerprint, formulation fingerprint, variable mapping, provider, solver version, presolve/configuration, numerical tolerances, environment, and dependency fingerprints;
5. imported native state is performance state only and never truth/authority;
6. receiving runs must independently validate final solver results using ordinary AASM admission rules;
7. stale/incompatible learning must be rejected before activation;
8. cross-run revocation/supersession must invalidate reusable native learning when its source basis is no longer admissible;
9. cold-vs-learned benchmark evidence must measure search work without turning performance into correctness.

Permanent invariant:

```text
SEARCH_STATE_NEVER_PROMOTES_TRUTH
```

Hard completion criterion:

> A receiving run must safely reuse compatible learned solver state, reject deliberately incompatible state, preserve the same canonical answer with or without imported learning, and demonstrate any search reduction only as measured performance evidence.

## v0.54.0 — Certified Cross-Solver Exchange & Deterministic Portfolio Racing

Primary contract targets:

```text
aasm.solver.exchange.v1
aasm.solver.portfolio.v1
```

Required scope:

1. deterministic multi-backend racing under governed resource budgets;
2. typed exchange of incumbents, lower/upper bounds, conflicts/no-goods, UNSAT cores, dominance constraints, and cut candidates where semantics permit;
3. certified translation before one solver consumes another solver's semantic artifact;
4. explicit source and target formulation fingerprints for every exchanged object;
5. compatibility checks for MILP basis/cut-pool exchange and numerical state;
6. deterministic scheduling/portfolio decisions under identical inputs, budgets, and seeds;
7. no winner-by-speed truth shortcut;
8. backend disagreement remains `INCONCLUSIVE`/investigate, never majority authority;
9. adversarial fixtures for malformed translations, stale bounds, incompatible bases, poisoned incumbents, unsound cuts, and forged cross-solver provenance.

Hard completion criterion:

> Multiple eligible backends must race reproducibly under fixed budgets; every exchanged semantic object must be traceably translated and independently admissible; disagreement must never become voting authority.

## v0.55.0 — Extended Mathematical IR

Required scope:

1. pseudo-Boolean constraints;
2. native cardinality constraints;
3. richer scheduling/global constraints;
4. additional conic families;
5. stronger quadratic representations;
6. explicit objective-vector IR shared with v0.52;
7. native backend representations where they preserve semantics better than generic compilation;
8. source semantic fingerprint, target formulation fingerprint, translation certificate, and validation strategy for every nontrivial lowering;
9. at least two independent validation paths for every new representation.

Hard completion criterion:

> Every newly supported mathematical representation must have reproducible semantic identity, a documented lowering/native path, and independent validation sufficient to prevent a translation error from silently becoming authoritative solver evidence.

## v0.56.0 — Proof/Enumeration/Optimization Stress Corpus

Required permanent corpora:

1. SAT/UNSAT positive models and certified negative claims;
2. CP-SAT scheduling, enumeration, and objective-bound cases;
3. MILP feasible/infeasible/optimal/bounded cases;
4. convex primal/dual validation and failure cases;
5. lexicographic and Pareto oracle-known multi-objective problems;
6. exact solution-pool problems with known solution counts;
7. cold-vs-learned cross-run solver-learning cases;
8. valid and malicious cross-solver exchange cases;
9. forged proof, stale cut, wrong mapping, poisoned incumbent, false completeness, and false optimality adversarial cases.

Every benchmark record must bind exact hardware/runtime metadata, OS, Python, dependency versions, solver version/configuration, seed, budgets, problem hash, formulation hash, and relevant certificate/checker versions.

Hard completion criterion:

> Every public capability claim added in v0.50–v0.55 must map to a reproducible corpus/gate, including negative and adversarial fixtures; no universal performance claim may be inferred without an explicit statistical threshold and methodology.

## v0.57.0 — Semantic Solver RC2 / Contract Review

This is a **subsystem reassessment release**, not a declaration that AASM is nearly complete.

Required scope:

1. freeze proof-certificate ABI;
2. freeze solution-pool and enumeration semantics;
3. freeze multi-objective and Pareto semantics;
4. freeze cross-run solver-learning compatibility rules;
5. freeze cross-solver exchange and portfolio scheduling ABI;
6. extend replay/migration fixtures across the new release generations;
7. repeat the public claim-to-gate audit across the complete semantic-solver surface;
8. classify each contract as stable, experimental, or requiring another compatibility cycle based on evidence rather than version number;
9. preserve every existing AASM truth, authority, memory, reuse, SII, and cross-run boundary;
10. explicitly publish all remaining non-claims and unresolved research questions.

Hard completion criterion:

> No semantic-solver capability advertised by AASM may lack a reproducible gate, schema, compatibility rule, negative/adversarial fixture, and documented authority boundary.

## Closure Matrix for the Current Gap Cluster

| Capability | Planned release | Hard completion criterion |
|---|---:|---|
| Proof-grade negative/optimality claims | v0.50 | independently checkable exact-claim certificate |
| General solution pools | v0.51 | resumable, deduplicated, completeness-aware pools |
| Complete finite enumeration | v0.51 | oracle solution set reproduced exactly and exhaustion certified |
| Full lexicographic objectives | v0.52 | higher-priority optima provably preserved |
| Pareto-frontier enumeration | v0.52 | exact finite nondominated set plus exhaustion certification |
| Durable cross-run solver-native learning | v0.53 | compatible learning reused; incompatible learning rejected |
| MILP basis/cut-pool reuse | v0.53–v0.54 | compatibility envelope plus performance-only semantics |
| Cross-solver bounds/conflicts | v0.54 | certified translation before reuse |
| Deterministic portfolio racing | v0.54 | reproducible budget/scheduling decisions |
| PB/cardinality support | v0.55 | native/certified formulations |
| Additional conic families | v0.55 | independent semantic validation |
| Broad benchmark/adversarial corpus | v0.56 | reproducible hardware/config-bound evidence and negative fixtures |
| Semantic-solver RC2 review | v0.57 | full closure audit for this capability tranche |

# No Presumed v1.0

AASM does **not** presently schedule, promise, or infer a v1.0 release from this roadmap.

Completion of v0.50–v0.57 means only that the **currently identified semantic-solver gap cluster** has been implemented and reassessed. It does not mean the broader AASM architecture, agent runtime, distributed execution model, proof system, semantic compiler, memory architecture, orchestration economics, real-world validation program, or future research program is finished.

Permanent versioning rule:

```text
0.x = architecture is still expanding
RC  = a subsystem or contract family is mature enough to freeze and test seriously
1.0 = considered only after a separate project-wide readiness review
```

There is no version arithmetic such as `v0.57 → v1.0`. Future work may continue through as many `0.x` releases as required.

A future v1.0 may be considered only after a dedicated project-wide readiness review establishes—with evidence—that the architecture, public contracts, migration guarantees, authority/safety boundaries, solver semantics, operational tooling, and real-world field results justify a stable-major declaration.

# Beyond v0.57 — Open Research & Capability Program

The roadmap beyond v0.57 is intentionally **not version-bounded**. New releases will be assigned as architectural work is identified, specified, implemented, tested, and validated.

Candidate research/capability areas include, but are not limited to:

- deeper proof-producing and proof-checking infrastructure;
- abstraction/refinement and counterexample-guided loops;
- compositional and hierarchical solving;
- temporal planning and temporal logics;
- stochastic, robust, and chance-constrained optimization;
- nonlinear and global optimization;
- richer SMT/theorem-prover integration;
- distributed search and distributed portfolio solving;
- durable cross-run search intelligence beyond the first solver-learning ABI;
- semantic compiler completeness and ambiguity management;
- explanation, minimal-cause, and minimal-unsatisfied-subset generation;
- solver/model/agent cooperative reasoning protocols;
- stronger uncertainty and epistemic-status handling;
- large-scale resource economics and scheduling;
- adversarial solver-state poisoning resistance;
- distributed and independently replicated certificate verification;
- hardware-aware solver orchestration and heterogeneous accelerators;
- real-world reference-domain campaigns;
- long-duration autonomous execution studies;
- privacy/security hardening for distributed and cross-run artifacts;
- provenance compression without loss of auditability;
- new formal models as the architecture expands;
- capabilities and failure modes discovered through field use that are not yet known.

This list is **append-only in spirit**: discovery of new requirements expands the program rather than forcing them into an artificial endpoint.

The governing principle remains:

> **v0.50–v0.57 closes the currently identified semantic-solver gap cluster. It does not close AASM.**
