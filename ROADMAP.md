# AASM Roadmap

AASM is currently **v0.22.0 / experimental**. This roadmap describes architectural direction, not guaranteed delivery dates.

## Delivered foundation

### Deterministic control plane

- ✅ explicit machine state and legal transitions
- ✅ declarative machine definitions and structural model checking
- ✅ event-sourced durability, checkpoints, replay, and historical forks
- ✅ SQLite and PostgreSQL coordination
- ✅ external-effect authorization, idempotency, ownership, `UNKNOWN` outcomes, and reconciliation
- ✅ mission `QUIESCE`, `SUSPEND`, and `RESUME`

### Planning, evidence, and execution

- ✅ plan graphs, shortest paths, checkpoint backtracking, and DP memory
- ✅ claims, observations, assumptions, contradictions, invalidation, and lineage
- ✅ capability scheduling, max-flow/min-cut evidence, priorities, and quotas
- ✅ distributed workers, heartbeats, leases, expiry, reclaim, and stale-result rejection
- ✅ model routing, adaptive outcomes, economics, and governance budgets
- ✅ optional Planner / Builder / Verifier protocol and automatic handoff
- ✅ selective information-change checkpoints and additive steering
- ✅ collaboration analysis, fleet admission, provisioning adapters, telemetry, artifacts, CLI/API, and Control Center

### v0.21 formal calculus

- ✅ durable Decision, Obligation, and Evidence graph calculus
- ✅ conditional obligations and evidence contracts
- ✅ model-relative locks with automatic restoration
- ✅ first-class conflicts and causal explanations
- ✅ guarded hard/soft learned no-goods
- ✅ graph-directed non-chronological backjumping
- ✅ knowledge-preserving search restart
- ✅ bounded cross-model fairness and Planner-authorized recovery

### v0.22 domain-neutral extension contract

- ✅ versioned `AASMProfile` and `AASMPackageManifest`
- ✅ immutable fingerprints and explicit per-machine profile bindings
- ✅ separate Decision, Obligation, Validation, Explanation, and Certification adapter protocols
- ✅ opt-in discovery of already-installed `aasm.profiles` entry points
- ✅ solver-neutral decision requests and candidate models
- ✅ kernel-side candidate validation against identity, hard constraints, pinned decisions, namespaces, and fairness
- ✅ generic fingerprinted semantic-result envelope
- ✅ static package/profile conformance and optional determinism probes
- ✅ built-in `aasm.bare` and domain-neutral `aasm.evolve`
- ✅ evidence-backed evolution proposals and explicit versioned migrations
- ✅ non-software example package and run

## Next architecture layer

### v0.23 — Decision backend ecosystem

- finite-domain reference backend with reproducible enumeration
- optional SAT, SMT, CP-SAT, MILP, human, LLM, and portfolio backends
- backend capability declarations and budget-aware routing
- backend-independent candidate explanation and scoring records
- decision-model benchmark and conformance fixtures

### v0.24 — Certificates and temporal conformance

- independently checked proof/certificate adapters for hard constraints
- TLA+ and Promela/SPIN models for calculus, effects, locks, fairness, and migration
- history-property checker over durable event streams
- formal CI gates with pinned tool versions
- conflict-core minimization and semantic generalization policies

### v0.25 — Generic calculus observability

- Control Center Decision, Obligation, and Evidence graph views
- profile/package identity, fingerprint, configuration, and migration history
- conflict, explanation, constraint, lock, fairness-debt, backjump, and restart timelines
- profile-specific display hints that cannot alter authority semantics
- authenticated remote write APIs for typed profile/calculus records

### Continuing control-plane work

- run- and project-level productive-work budgets
- richer human approval queues and delegation scopes
- provider-neutral streamed executor events
- external log stores with retention, search, and signed references
- deeper critical-path and event-timeline visualization
- reconciliation assistance that never guesses external state
- rolling worker-fleet health and provider/AASM identity reconciliation
- signed release artifacts and package-registry publication

## Longer-term possibilities

- hierarchical conflict projection across strategy, implementation, and execution layers
- governed package-evolution assistants that propose but never silently activate new contracts
- package registries with trust, provenance, signatures, and compatibility evidence
- cross-project performance priors with strict profile/task-class isolation
- multi-runtime SDKs and standardized interoperability contracts
- simulation-driven plan validation and counterfactual forks
- domain packages for CAD, robotics, research, deployment, operations, and scientific simulation maintained outside the core

## Non-goals for the core

AASM should not become:

- a bundled LLM provider;
- a domain-specific application;
- a package installer that downloads executable code during discovery;
- a mandatory Planner/Builder system;
- a mandatory SAT/SMT system;
- a monolith that forces one evidence ontology, user interface, or agent topology;
- a self-modifying package system without explicit versioning and migration.

The core remains a role-agnostic, domain-neutral deterministic control plane with explicit extension contracts.
