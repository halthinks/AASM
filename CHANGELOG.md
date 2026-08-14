# Changelog

## [0.47.0] - 2026-08-14

### Governed Symbiotic Intelligence & Intelligence Economics

- advanced `aasm.adoption.v1` to `0.23.0`, `aasm.certification.v1` to `0.2.0`, and the current SII contract to `aasm.sii.v1 / 0.3.0`;
- graduated SII stability from the v0.43 experimental certification target to `GOVERNED_ENFORCED`;
- added durable POLICY/CONTROLLER-admitted `SIIPrincipalBinding` records for stable proposer and measurement identities;
- removed caller-controlled measurement authority from the governed path: `measure_sii_outcome()` resolves authority from durable principal state;
- rejects stable-principal rebinding and principal-level self-measurement;
- added versioned durable `SIIScoringPolicy` objects with explicit default/exploration/exploitation/formal profiles and tier thresholds;
- added durable `GovernedResourceLease` records bound to proposer, principal, scoring-policy version, measured performance window, utility, and tier;
- fixed every governed ResourceLease to `PROPOSER` authority with direct truth promotion, direct state mutation, and self-verification false;
- enforced context budgets through the existing v0.40 context projection;
- enforced SII scheduler priority through ordinary `TaskDemand.priority` and copied SII provenance into ordinary task/TaskLease metadata;
- enforced maximum outstanding discretionary SII candidate count before queue growth;
- compiled tier budgets into real v0.46 advanced solver requests: incremental CaDiCaL conflict/decision limits, solver timeout, CP-SAT deterministic time/search workers, HiGHS MIP node limits, and convex timeout;
- added an explicitly discretionary governed formal-verification path with timeout/provider-width limits while preserving ordinary policy-required verification outside SII caps;
- added the invariant `REQUIRED_VERIFICATION_NEVER_REDUCED_BY_SII` so SII cannot remove required verifiers, shrink required independent-result quorums, weaken proof strength, or bypass epistemic admission;
- added durable `ENFORCEMENT` Evidence connecting governed ResourceLease records to actual solver/formal requests;
- added a v0.47 certification facade that keeps existing core fixtures and turns the historical `sii-preview` target into an alias for the governed graduation fixture;
- added governed SII adversarial certification for unbound measurement actors, authority escalation, native solver-budget bypass, scheduler-budget bypass, required-verification reduction, and replay;
- preserved the v0.43 preview implementation/import surface for compatibility while making the current package-level `sii_contract()` resolve to v0.47 governance;
- preserved all v0.44–v0.46 native solver, v0.45 CVXPY/PuLP, and v0.39 Z3/cvc5/Vampire/Lean execution paths;
- added public/CLI surfaces, JSON schemas, documentation, release notes, roadmap updates, release/formal source gates, and regression coverage;
- moved cross-run certified knowledge and governed long-term memory to v0.48.

## [0.46.0] - 2026-08-14

### Advanced Solver Control & Search Artifacts

- added `aasm.optimization.advanced.v1 / 0.1.0` and advanced `aasm.adoption.v1` to `0.22.0`;
- added `solver.sat.fast@0.1.0` backed by real Kissat through PySAT's dedicated `Kissat404` binding;
- added incremental CaDiCaL assumptions, UNSAT-core extraction, conflict/decision budgets, and bounded in-process solver-session reuse;
- classified retained incremental SAT learned state as `EPHEMERAL_PERFORMANCE_ONLY`, never durable truth or authority;
- added `solver.cp_sat.scheduling@0.1.0` with fixed/optional intervals, `NO_OVERLAP`, `CUMULATIVE`, search-worker count, deterministic-time budget, and search telemetry;
- added `solver.milp.advanced@0.1.0` with HiGHS warm starts, MIP relative-gap target, node limit, primal/dual bound, gap, node, and iteration telemetry;
- added `solver.convex.advanced@0.1.0` with factorized general PSD/NSD quadratic forms, cross terms, and affine SOC constraints;
- added canonical advanced request/result identities carrying UNSAT core, best bound, relative gap, telemetry, provider identity, and exact problem fingerprints;
- reused the existing v0.39 Capability ABI and resource/worker/TaskLease scheduler rather than creating a second execution plane;
- added lease-expiry, superseded-attempt, provider-implementation, result-collision, and exact-replay hardening to advanced solver commits;
- kept all advanced results `EVIDENCE_ONLY` under `SEARCH_STATE_NEVER_PROMOTES_TRUTH`;
- connected advanced results to the existing v0.41 `OPTIMIZATION_RESULT` reuse/certificate path while excluding ephemeral learned state from durable reuse;
- preserved v0.44 direct CaDiCaL/CP-SAT/HiGHS, v0.45 CVXPY/PuLP, and v0.39 Z3/cvc5/Vampire/Lean pathways;
- added real Python 3.13 backend coverage for Kissat, incremental CaDiCaL, CP-SAT scheduling, advanced HiGHS, and advanced CVXPY while retaining all prior real-backend tests;
- added public API, CLI, schemas, documentation, release/source gates, and compatibility tests;
- moved SII graduation to v0.47 so governed intelligence economics can meter concrete conflict, decision, deterministic-time, worker, node, gap, convex, formal, model-call, and context budgets.

## [0.45.0] - 2026-08-14

### Convex Optimization & Modeling Adapters

- added `aasm.optimization.convex.v1 / 0.1.0` and advanced `aasm.adoption.v1` to `0.21.0`;
- added `solver.convex@0.1.0` as a governed OPERATOR capability executing CVXPY through the existing AASM resource/worker/TaskLease boundary;
- added an AASM-owned convex IR for scalar continuous variables, linear equality/inequality constraints, diagonal convex/concave quadratic objectives, and constant-radius SOC constraints;
- independently rechecked CVXPY results before durable Evidence admission;
- added `aasm.adapter.pulp.v1 / 0.1.0` as a `TRANSLATION_ONLY` compatibility boundary with solver execution `NEVER`;
- added supported finite-bounded PuLP LP/MILP conversion into the existing AASM `OptimizationModel` and real PuLP-to-HiGHS CI execution;
- preserved direct CaDiCaL, OR-Tools CP-SAT, HiGHS, Z3, cvc5, Vampire, and Lean 4 paths;
- added modeling extras, schemas, CLI/public surfaces, docs, release gates, and real Python 3.13 CVXPY/PuLP coverage.

## [0.44.0] - 2026-08-14

### Heterogeneous Optimization Solver Portfolio

- added `aasm.optimization.v1 / 0.1.0` and advanced `aasm.adoption.v1` to `0.20.0`;
- added canonical Boolean/integer/continuous optimization IR with clause, linear, all-different, and linear objective support;
- added real PySAT/CaDiCaL, OR-Tools CP-SAT, and HiGHS/highspy providers;
- reused the existing v0.39 Capability ABI and resource/worker/TaskLease scheduler;
- independently rechecked successful assignments/objectives before durable admission;
- made optimization results `EVIDENCE_ONLY` and connected them to v0.41 certificate-gated reuse;
- added bounded formal assurance, real-backend CI, public/CLI/schema/docs/release coverage.

## [0.43.0] - 2026-08-14

### Semantic Conformance, Adversarial Domains, and Certification

- added `aasm.certification.v1 / 0.1.0` and advanced `aasm.adoption.v1` to `0.19.0`;
- added explicit `PASS | FAIL | INCONCLUSIVE` certification semantics;
- added deterministic profiles for reference domains, reuse, truth/memory, and formal-verification boundaries;
- staged `aasm.sii.v1 / 0.2.0` as an experimental participation plane with no direct truth/state authority;
- added SII identity/proposal/outcome/performance/resource-lease preview contracts and adversarial checks;
- intentionally kept SII `INCONCLUSIVE` until authority binding and resource enforcement are real.

## [0.42.0] - 2026-08-13

### Reference Domains & Reuse/Memory/Reasoning Stress Tests

- added `aasm.reference-domains.v1 / 0.1.0` and advanced adoption to `0.18.0`;
- added five deterministic offline stress domains and explicit verification-strength reuse enforcement;
- added public/CLI/schema/docs/regression surfaces while retaining the v0.41 solver kernel.

## [0.41.0] - 2026-08-13

### Domain-Neutral Solver Loop and Deterministic Reuse Plane

- added canonical reuse requests/candidates/certificates and exact/idempotent/subsumption/certified-equivalence modes;
- added deterministic scope/privacy/environment/dependency/freshness/effect validation;
- added durable reuse metrics, hot index, solver-step reuse checks, formal assurance, and adoption `0.17.0`.

## [0.40.0] - 2026-08-13

### Hierarchical Memory, Reasoning Frontier, and Context Projection

- added governed sensory/working/episodic/semantic/procedural memory, privacy/retention/tombstones, deterministic indexes, reasoning frontier/context projection, replay, schemas, conformance, and formal assurance;
- preserved legacy `DPMemory` as algorithmic memoization and advanced adoption to `0.16.0`.

## [0.39.0] - 2026-08-13

Typed Protocol, Capability ABI, and Formal Verification Workers. Added typed pattern/capability/formal contracts, leased solver execution, solver identity, proof-strength semantics, and no solver auto-authorization. Adoption `0.15.0`.

## [0.38.0] - 2026-08-13

Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance. Added dependency/impact/lineage, descendant-only invalidation, obligation reopening, reactive derivation, and semantic memory signals. Adoption `0.14.0`.

## [0.37.0] - 2026-08-13

Reasoning Artifacts and Epistemic Admission. Added typed reasoning artifacts, independent verification, policy authorization, ReasoningCommit, replay/provenance, and self-verification rejection. Adoption `0.13.0`.

## [0.36.0] - 2026-08-12

Semantic Compiler SDK. Added deterministic source compilation and proposal-only admission boundary. Adoption `0.12.0`.

## [0.35.0] - 2026-08-12

Semantic Problem Model Foundations. Added domain/problem models, deterministic fingerprints, capability gaps, contradictions, and event-sourced admission. Adoption `0.11.0`.

Earlier history is preserved in repository history and archived changelog files.
