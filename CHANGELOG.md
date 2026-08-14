# Changelog

## [0.45.0] - 2026-08-14

### Convex Optimization & Modeling Adapters

- added `aasm.optimization.convex.v1 / 0.1.0` and advanced `aasm.adoption.v1` to `0.21.0`;
- added `solver.convex@0.1.0` as a governed OPERATOR capability that executes CVXPY only through the existing AASM resource/worker/TaskLease boundary;
- added an AASM-owned convex canonical IR for scalar continuous variables, linear equality/inequality constraints, diagonal convex quadratic minimization, diagonal concave quadratic maximization, and constant-radius second-order-cone constraints;
- added deterministic CVXPY backend selection across installed OSQP/CLARABEL/SCS-style backends by problem class and included the selected backend in solver identity;
- independently rechecks bounds, linear constraints, SOC feasibility, request/model/provider identity, and canonical objective evaluation before CVXPY output can become durable Evidence;
- kept convex solver results explicitly `EVIDENCE_ONLY` and added lease expiry, superseded-attempt, provider-implementation, result-collision, and exact completed-lease replay protections;
- added `aasm.adapter.pulp.v1 / 0.1.0` as a `TRANSLATION_ONLY` compatibility boundary with solver execution explicitly `NEVER`;
- added conversion of supported finite-bounded PuLP continuous/integer/binary variables, linear constraints, and linear objectives into the existing v0.44 `OptimizationModel`;
- rejects unbounded PuLP variables rather than inventing finite big bounds that change model semantics;
- routes imported PuLP models through ordinary AASM native providers, including real PuLP-to-HiGHS execution in CI;
- preserved direct PySAT/CaDiCaL, OR-Tools CP-SAT, and HiGHS execution instead of wrapping those native paths through CVXPY or PuLP;
- preserved Z3, cvc5, Vampire, and Lean 4 on the existing formal-verification pathway;
- added `modeling` and expanded `optimization` optional dependency extras for CVXPY/PuLP;
- added real Python 3.13 backend coverage for CVXPY QP, CVXPY SOC, PuLP import, PuLP-to-HiGHS, and the existing native optimization portfolio;
- added public/CLI surfaces, schemas, release/source gates, documentation, and compatibility regression coverage;
- moved SII graduation to v0.46 so governed intelligence economics can allocate real SAT/CP-SAT/MILP/convex/formal/reasoning resource budgets.

## [0.44.0] - 2026-08-14

### Heterogeneous Optimization Solver Portfolio

- added `aasm.optimization.v1 / 0.1.0` and advanced `aasm.adoption.v1` to `0.20.0`;
- added a canonical AASM optimization IR for Boolean/integer/continuous variables, clauses, linear constraints, all-different constraints, and linear objectives;
- added deterministic SAT / CP-SAT / MILP family selection with explicit rejection of unsupported lowerings;
- added real PySAT/CaDiCaL, OR-Tools CP-SAT, and HiGHS/highspy solver workers behind an optional `optimization` dependency extra;
- preserved Z3, cvc5, Vampire, and Lean 4 on the existing v0.39 formal-verification pathway;
- reused the existing v0.39 Capability ABI for optimization provider admission and the existing resource/worker/task-lease scheduler for execution;
- added `runtime_v44.AASMEngine` as a thin `OptimizationRuntimeMixin + runtime_v41.AASMEngine` composition rather than adding a second scheduler/reducer/truth store;
- added exact request/model/provider/lease validation and independent rechecking of successful assignments/objectives before durable result admission;
- made optimization results explicitly `EVIDENCE_ONLY` and added bounded TLA+/Promela checks that solver execution cannot directly authorize knowledge;
- connected optimization results to the existing v0.41 reuse plane through explicit `ReuseRequest` generation and policy-gated `ReuseCandidate` admission;
- added certificate-gated solver-loop execution skipping for validated repeated optimization work;
- added real-backend GitHub Actions coverage that installs and executes CaDiCaL, CP-SAT, and HiGHS through AASM's actual provider/resource/worker/lease/result path;
- added public/CLI surfaces, schemas, regression tests, release/source gates, formal assurance, and detailed solver-portfolio documentation;
- moved SII graduation to v0.45 so resource economics can target real SAT/CP-SAT/MILP/formal/reasoning budgets.

## [0.43.0] - 2026-08-14

### Semantic Conformance, Adversarial Domains, and Certification

- added `aasm.certification.v1 / 0.1.0` and advanced `aasm.adoption.v1` to `0.19.0`;
- added explicit `PASS | FAIL | INCONCLUSIVE` certification semantics so missing evidence or enforcement cannot silently become success;
- added deterministic certification profiles for reference domains, solver/reuse, truth/memory, and formal-verification boundaries;
- added adversarial checks for freshness/dependency/effect mismatches, stale reasoning, privacy/revocation, and insufficient formal verification strength;
- preserved the distinction between deterministic architecture/contract certification and the semantic truth of arbitrary external conclusions;
- staged `aasm.sii.v1 / 0.2.0` as an experimental Symbiotic Intelligence Interface participation plane rather than creating another runtime kernel;
- added SII structured proposals, stable principal identities, durable outcome attribution, bounded performance vectors, contextual ResourceLease projections, and governed context access;
- ensured SII savings credit comes only from durable AASM reuse telemetry and that resource utility never promotes truth/state authority;
- added SII adversarial checks for producer-controlled fingerprints, identity reset, self-measurement, forged reuse metrics, authority escalation, and repeated-outcome farming;
- intentionally reports the SII preview as `INCONCLUSIVE` until measurement authority is durably actor-bound and ResourceLease values are enforced by existing scheduler/capability paths;
- added certification/SII public API, CLI commands, JSON schemas, documentation, regression tests, and release/formal source gates;
- kept `runtime_v41.AASMEngine` as the active kernel; no `runtime_v43.py` or replacement v0.42 runtime path was introduced.

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
