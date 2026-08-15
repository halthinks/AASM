# Changelog

## [0.54.0] - 2026-08-15

### Certified Cross-Solver Exchange & Deterministic Portfolio Racing + Effect Ownership/UNKNOWN Recovery

- advanced package/public surface to `0.54.0` and `aasm.adoption.v1 / 0.30.0`;
- added public `aasm.effect.intent.v1`, dispatch-request, ownership, reconciliation, and resource-settlement contracts;
- made durable atomic `EffectOwnership` mandatory before the external executor boundary and bound it to the existing scoped authority, TaskLease, workspace/scope, and declared resource reservations;
- added crash/restart UNKNOWN recovery that preserves ownership and blocks redispatch until explicit scoped Evidence-backed reconciliation;
- kept dispatch, ownership, and reconciliation history append-only and refused silent adoption of legacy pre-v0.54 effects;
- added `aasm.effect.resource-settlement.v1 / 0.1.0`, reconciling observed actual external consumption only after `CONFIRMED | FAILED` outcomes through the existing scoped `resource.settle` authority and resource ledger;
- made multi-reservation effect settlement recoverable/idempotent per reservation and rejected retries that attempt to rewrite already-durable actual consumption;
- added `aasm.solver.translation.v1 / 0.1.0` with deterministic source/target identity and independent exact semantic-equivalence checking across compatible solver-family representations;
- added `aasm.solver.portfolio.v1 / 0.1.0` and `aasm.solver.portfolio.runtime.v1 / 0.1.0` while preserving ordinary optimization requests, `TaskDemand`, `TaskLease`, existing provider execution, result validation, Evidence, and proof-certificate pathways;
- introduced no parallel race scheduler and explicitly forbade fastest-result, arrival-order, and majority-vote correctness shortcuts;
- made uncertified negative claims unable to outvote validated feasible assignments and made incompatible certified/validated facts fail closed as `CONFLICT`;
- added proof-aware portfolio decisions using the existing v0.50 proof-certificate plane rather than creating a second certification authority;
- added a real OR-Tools CP-SAT + HiGHS governed portfolio race through the existing TaskLease/provider path and required the deterministic certified-optimal result;
- added `aasm.solver.exchange.v1 / 0.1.0`, reusing v0.53 `SolverLearningArtifact`, validation, and application semantics for cross-solver learned-artifact exchange;
- required source local PASS validation, independently reproducible source/target translation certificates, and target-local revalidation before exchanged learning can be applied;
- kept no-goods/cores/bounds correctness-sensitive, incumbents/warm starts performance-only, and native accelerator state non-portable across different solvers;
- preserved `cross_solver_agreement_grants_truth = false`, `truth_authority = NONE`, and `policy_authority = NONE`;
- promoted `runtime_v54_full.AASMEngine`, `public_v54`, and `cli_v54` to the active package surface while retaining v0.53 as a versioned frozen parent;
- added permanent exact-SHA `aasm/v54` conformance and hardened release publication to require it alongside CI, formal assurance, RC, proof claims, solution pools, optimization, scoped authority, and solver learning;
- preserved all v0.53 scoped-identity/authority and solver-learning semantics, v0.52 resource/multi-objective semantics, v0.51 complete enumeration, v0.50 proof certification, v0.49 RC, v0.48 cross-run admission, and v0.47 governed SII as versioned parents.

## [0.53.0] - 2026-08-14

### Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening

- advanced package/public surface to `0.53.0` and `aasm.adoption.v1 / 0.29.0`;
- added `aasm.identity.scoped.v1`, `aasm.authority.scoped.v1`, and durable `aasm.authority.scoped.runtime.v1` with explicit Principal / Workspace / Scope separation;
- made scoped authority fail closed by default, with DENY precedence, grant expiry, nondelegability, delegation depth/capability/scope ceilings, and delegated-wildcard rejection;
- preserved `cross_run_authority_transfer = NEVER` and the rule that resource state never grants authority;
- added durable workspace bootstrap, principal registration, grant admission, allow/deny decisions, and authorization lineage through ordinary AASM Evidence/event replay;
- required scoped capabilities for resource capacity registration, observation, reservation, re-estimation, release, and settlement;
- added principal-aware resource-history projection derived from the exact scoped-authority Evidence that authorized the resource mutation;
- added v0.53 optimistic machine-version guarding for resource Evidence commits so stale concurrent hosts cannot both commit conflicting reservations;
- verified stale-writer rejection and canonical reload across MemoryStore, SQLite, and PostgreSQL;
- added `aasm.store.scoped.v1` as a fail-closed read-only persistence facade: cross-workspace, child-scope raw, multi-workspace ambiguous, unfinished-machine leakage, and legacy-unscoped-effect reads fail closed; direct store mutation remains forbidden outside governed runtime transitions;
- separated scoped effect proposal, `effect.authorize`, `effect.execute`, and `effect.reconcile`; every external execution attempt receives a fresh authority decision so expired/revoked authority cannot be bypassed by retry behavior;
- added `aasm.solver.learning.v1 / 0.1.0` for correctness-sensitive `NO_GOOD | UNSAT_CORE | BOUND` and performance-only `INCUMBENT | WARM_START | NATIVE_ACCELERATOR` artifacts;
- reused the existing v0.48 `CrossRunKnowledgeEnvelope(kind="REUSE_RESULT")` and admission path for cross-run solver learning instead of introducing a second transport/admission plane;
- kept imported correctness-sensitive learning inert until receiving-run exact local revalidation and rejected forged no-goods/bounds that would eliminate feasible solutions;
- kept incumbents, warm starts, and compatible native accelerator state performance-only with `truth_authority = NONE`;
- added `aasm.solver.learning.application.v1 / 0.1.0`, requiring exact PASS validation, exact artifact/model binding, and scoped `solver.learning.apply` authority before application;
- lowered certified pruning into a new canonical optimization model through the existing provider path rather than creating a new solver executor;
- made the existing OR-Tools CP-SAT adapter explicitly consume validated assignment hints through `CpModel.add_hint(...)` and report consumed solver-learning application IDs;
- added dedicated exact-SHA `aasm/scoped-authority` and `aasm/solver-learning` status gates;
- hardened release publication so v0.53 requires `aasm/ci-summary`, `aasm/formal-assurance`, `aasm/semantic-solver-rc`, `aasm/proof-claims`, `aasm/solution-pools`, `aasm/optimization`, `aasm/scoped-authority`, and `aasm/solver-learning` on the same current `main` SHA;
- preserved v0.52 multi-objective/resource contracts, v0.51 complete enumeration, v0.50 proof certification, v0.49 Semantic Solver RC, v0.48 cross-run admission, and v0.47 governed SII as frozen versioned parents.

## [0.52.0] - 2026-08-14

### Resource-Governed Multi-Objective Decisions & Pareto Solving

- advanced package/public surface to `0.52.0` and `aasm.adoption.v1 / 0.28.0`;
- added `aasm.optimization.multi-objective.v1 / 0.1.0` with exact finite lexicographic solving over the v0.51 certified complete-enumeration substrate;
- added `aasm.optimization.frontier.v1 / 0.1.0` with independently reconstructed exact finite Pareto frontiers;
- hardened exact Pareto certification to require equality of solution IDs, assignments, and objective vectors rather than ID equality alone;
- froze tolerance-aware lexicographic survivor and Pareto-dominance semantics;
- added `aasm.resource.capacity.v1`, `aasm.resource.observation.v1`, `aasm.resource.demand.v1`, `aasm.resource.routing.v1`, and `aasm.resource.runtime.v1`;
- added fixed, rolling, refilling, credit-balance, unbounded, and unknown resource windows plus protected reserves;
- preserved external quota/usage provenance as `AUTHORITATIVE | OBSERVED | DERIVED | ESTIMATED | DECLARED | UNKNOWN` Evidence;
- added an additive `aasm.sii.resource-aware-proposal.v1 / 0.1.0` successor bound to an already-durable governed parent SII proposal;
- made correctness, evidence quality, expected progress, provider quota burn, scarce-expert usage, monetary cost, and wall time explicit governed decision dimensions;
- replaced the permanent routing tuple with an explicit policy-controlled ordered objective contract;
- added exact Pareto analysis over the supplied eligible resource-candidate set without reserving resources or claiming global route-discovery completeness;
- added atomic conservative resource reservation, durable re-estimation with `CONTINUE | REPLAN_REQUIRED`, release, settlement, and predicted-versus-actual calibration Evidence;
- added replayable routing explanations containing objective policy, candidate vectors, capacity state, reserve, reset horizon, and observation provenance;
- added workspace/scope-safe resource inspection and fail-closed unknown/cross-workspace resource behavior;
- added JSON schemas and adversarial tests for false completeness, forged frontier contents, policy inversion, quota-vs-money tradeoffs, reserve violations, unknown capacity, partial reservation, duplicate settlement, and replay;
- added a dedicated v0.52 contract/adversarial job plus exact-SHA `aasm/optimization` status requiring the real native optimization/modeling suite to pass as well;
- hardened release publication so v0.52 requires `aasm/ci-summary`, `aasm/formal-assurance`, `aasm/semantic-solver-rc`, `aasm/proof-claims`, `aasm/solution-pools`, and `aasm/optimization` on the exact current `main` SHA;
- preserved v0.51 solution-pool/enumeration semantics and all earlier proof, semantic-solver RC, cross-run, SII, authority, memory, and formal boundaries.

## [0.51.0] - 2026-08-14

### Governed Solution Pools & Complete Enumeration

- advanced package/public surface to `0.51.0` and `aasm.adoption.v1 / 0.27.0`;
- added governed solution pools, exact solution identity/deduplication, durable exclusions, and restart-safe cursors;
- added complete finite Boolean/integer enumeration with independent exhaustion certification;
- partial, bounded, native, top-k, diverse, and incumbent-history pools never imply completeness;
- added adversarial false-completeness, duplicate, stale/corrupt cursor, and unsupported continuous-domain protections;
- added real CP-SAT and HiGHS iterative no-good enumeration requiring exact set equality to an independent oracle and never voting;
- persisted pool state through the existing Evidence/event history only;
- added JSON schemas, public API/CLI, dedicated `aasm/solution-pools` CI, and TLA+/SPIN assurance;
- preserved v0.50 proof certification and all prior authority, memory, reuse, solver, SII, and cross-run boundaries.

## [0.50.0] - 2026-08-14

### Proof-Carrying Solver Claims

- advanced the package/public surface to `0.50.0` and `aasm.adoption.v1` to `0.26.0`;
- added `aasm.solver.proof-certificate.v1 / 0.1.0` with `EXPERIMENTAL_ENFORCED` stability;
- added `SolverClaim`, `SolverProofArtifact`, and `SolverClaimCertificate` with exact problem/formulation/model/result bindings;
- separates `SOLVER_VALIDATED` from `PROOF_CERTIFIED`; solver status alone is never proof grade;
- requires an independent passing checker before any claim can become `PROOF_CERTIFIED`;
- added AASM-owned exhaustive finite-domain certification for bounded Boolean/integer `UNSAT`, `INFEASIBLE`, and `OPTIMAL` claims;
- added deterministic proof trace digests and independent proof reconstruction/recheck;
- distinguishes unsupported proof scope/budget from a contradicted claim (`UNSUPPORTED != FAIL`);
- rejects forged/tampered proof artifacts, false optimality, self-checking, unsupported continuous models, and over-budget exhaustive spaces;
- persists proof claims/artifacts/certificates through the existing Evidence/event history with exact replay;
- keeps proof certificates `EVIDENCE_ONLY`; AASM policy remains the only truth/state authority;
- added JSON schemas, public API/CLI, proof conformance, dedicated `aasm/proof-claims` CI, and bounded TLA+/SPIN assurance;
- hardened release publication to require CI + Formal Assurance + Semantic Solver RC + Proof Claims on the exact current `main` SHA;
- preserved project-wide Apache-2.0 policy and all v0.49/v0.48/v0.47 authority, solver, memory, reuse, SII, and cross-run boundaries.

## [0.49.0] - 2026-08-14

### Semantic Solver Release Candidate

- advanced the package/public surface to `0.49.0` and `aasm.adoption.v1` to `0.25.0`;
- added `aasm.semantic.solver.rc.v1 / 0.1.0` with stability `RELEASE_CANDIDATE`;
- added a thin `SemanticSolverRCRuntimeMixin + runtime_v48.AASMEngine` assurance layer with no new scheduler, reducer, truth store, authority plane, memory store, or inner solver kernel;
- added deterministic public freeze manifests over contract identities, engine methods, CLI commands, imports, inspection surfaces, schemas, provider identities, replay expectations, and project-wide Apache licensing;
- added a freeze-manifest semantic fingerprint for 0.49.x compatibility review;
- added v0.41 → v0.49 replay/upgrade coverage for event history, memoized state, and governed memory;
- added v0.47 → v0.49 replay/upgrade coverage for governed SII policy and principal binding;
- added v0.48 → v0.49 replay/upgrade coverage for admitted cross-run knowledge and foreign-authority non-inheritance;
- requires exact canonical replay/hash equality for each upgrade fixture;
- added exact overlapping OR-Tools CP-SAT and HiGHS MILP certification for the same Boolean/integer optimum, plus a CaDiCaL Boolean feasibility projection;
- added `AGREEMENT_OR_INCONCLUSIVE_NEVER_VOTE` as the cross-backend certification rule;
- added semantic fingerprint and event append/replay benchmark workloads;
- added direct native CP-SAT versus full AASM provider/request/TaskLease/solve/validate/Evidence lifecycle measurement;
- records observed orchestration-overhead ratio as environment-specific evidence only;
- added `AASM_DOES_NOT_CLAIM_FASTER_INNER_SOLVER_KERNELS` and `MEASURE_OVERHEAD_AND_SAVINGS_NO_UNGATED_SPEEDUP_CLAIM`;
- added `NO_PUBLIC_CAPABILITY_CLAIM_WITHOUT_REPRODUCIBLE_GATE` and a claim-to-gate audit;
- added complete RC certification aggregating cross-run, semantic/adversarial, optimization, modeling, advanced solver, overlap, upgrade, benchmark, and claim-audit gates;
- added RC freeze/benchmark/certification JSON schemas;
- added public RC CLI surfaces;
- added a dedicated `Semantic Solver RC` GitHub Actions workflow with real native backends;
- publishes exact-head `aasm/semantic-solver-rc` commit status;
- hardened the release workflow to require `aasm/ci-summary`, `aasm/formal-assurance`, and `aasm/semantic-solver-rc` on the exact current `main` commit;
- preserved project-wide Apache-2.0 policy and all prior formal, memory, reuse, solver, SII, and cross-run authority boundaries.

## [0.48.1] - 2026-08-14

### Project-Wide Apache-2.0 Policy Correction

- added `LICENSE_POLICY.md` as AASM's explicit project-wide Apache-2.0 licensing declaration;
- declares prior AASM versions also offered under Apache-2.0 to the extent AASM has the necessary relicensing rights, including versions first distributed under MIT;
- states that previously granted MIT permissions remain valid for recipients while removing the incorrect implication that prior AASM versions are MIT-only;
- removed the incorrect implication that v0.47.1 is the first or only Apache-2.0 point in AASM history;
- corrected README, roadmap, current-release, and v0.47.1 release documentation accordingly;
- added release-gate requirements for the project-wide Apache policy and regression checks that reject the stale MIT-only/first-Apache framing;
- advanced the package/public distribution version to `0.48.1` while keeping `aasm.adoption.v1 / 0.24.0` and all runtime, cross-run, SII, solver, formal, memory, reuse, persistence, scheduler, and replay semantics unchanged.

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
- preserved Apache-2.0 / PEP 639 / packaged `LICENSE` + `NOTICE` + `LICENSE_POLICY.md` behavior.

## [0.47.1] - 2026-08-14

### Apache-2.0 License Transition

- changed AASM package/project metadata to Apache License 2.0 (`Apache-2.0`);
- replaced the root `LICENSE` with the standard Apache License 2.0 text and added packaged `NOTICE` attribution;
- uses PEP 639/SPDX `license = "Apache-2.0"` with no legacy `License :: ...` classifier;
- preserved every v0.47.0 runtime/authority/solver/SII behavior unchanged;
- under the project-wide declaration now recorded in `LICENSE_POLICY.md`, prior AASM versions are also offered under Apache-2.0 where AASM has the necessary relicensing rights; previously granted MIT permissions remain valid for their recipients without making those prior versions MIT-only.

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
