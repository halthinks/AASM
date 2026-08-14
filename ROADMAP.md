# AASM Roadmap

AASM is currently **v0.49.0 / Semantic Solver Release Candidate**.

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
- **v0.49.0 Semantic Solver Release Candidate — Current**

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

### Solver work still worth doing after the RC

- proof-producing SAT/infeasibility certificate integration where native backends expose it;
- pseudo-Boolean/cardinality native representations;
- MILP basis/cut-pool exchange with numerical/provenance compatibility;
- deterministic multi-backend racing under governed budgets;
- certified cross-solver translation/bound/conflict exchange;
- broader benchmark corpora with explicit hardware/runtime metadata;
- additional conic families with independent validation.

## v0.50.0 — Post-RC Stabilization

**Next only after RC evidence is satisfactory.** Use the v0.49 freeze manifest and field/benchmark evidence to decide which contracts can be declared stable, which remain experimental, and which require another compatibility cycle. No stability claim should be made merely because the version number reaches 0.50.
