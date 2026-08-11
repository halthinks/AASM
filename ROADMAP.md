# AASM Roadmap

AASM is currently **v0.25.1 / experimental**. This roadmap describes architectural direction, not guaranteed delivery dates.

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

### v0.21 — Formal calculus

- ✅ durable Decision, Obligation, and Evidence graph calculus
- ✅ conditional obligations and evidence contracts
- ✅ model-relative locks with automatic restoration
- ✅ first-class conflicts and causal explanations
- ✅ guarded hard/soft learned no-goods
- ✅ graph-directed non-chronological backjumping
- ✅ knowledge-preserving search restart
- ✅ bounded cross-model fairness and Planner-authorized recovery

### v0.22 — Domain-neutral extension contract

- ✅ versioned `AASMProfile` and `AASMPackageManifest`
- ✅ immutable fingerprints and explicit per-machine profile bindings
- ✅ separate Decision, Obligation, Validation, Explanation, and Certification adapter protocols
- ✅ solver-neutral decision requests and candidate models
- ✅ generic fingerprinted semantic-result envelope
- ✅ static package/profile conformance and optional determinism probes
- ✅ built-in `aasm.bare` and domain-neutral `aasm.evolve`
- ✅ evidence-backed evolution proposals and explicit versioned migrations

### v0.23 — Decision backend ecosystem

- ✅ deterministic finite-domain backend with incremental continuation
- ✅ human proposal backend
- ✅ provider-neutral callback/model backend
- ✅ portfolio backend with candidate deduplication and multi-source provenance
- ✅ enforced candidate, combination, cost, and latency budgets
- ✅ durable candidate lifecycle, revalidation, selection, and atomic activation
- ✅ backend registry and capability routing

### v0.24 — Formal assurance

- ✅ durable certificates and independent verification results
- ✅ exact learned-constraint projection certification
- ✅ detached SHA-256 artifact verification
- ✅ globally enforced certificate-gated hard knowledge
- ✅ reducer-based durable-history replay verification
- ✅ greedy irreducible and exact-bounded conflict-core minimization
- ✅ immutable successor explanations for adopted minimized cores
- ✅ bounded TLA+ and Promela/SPIN assurance models
- ✅ backward-compatible assurance state persistence

### v0.25 — Generic observability

- ✅ Decision Graph projection
- ✅ Obligation Graph projection
- ✅ Evidence Graph projection
- ✅ closed heterogeneous causal graph
- ✅ typed conflict, backjump, restart, profile, candidate, and assurance timelines
- ✅ actionable fairness-debt view with thresholds and lock reasons
- ✅ profile/package binding and migration history
- ✅ candidate backend and assurance summaries
- ✅ canonical-store refresh for every inspection surface
- ✅ generic `inspect_machine()` CLI and authenticated HTTP surfaces

### v0.25.1 — Stabilization

- ✅ closed inherited hard-constraint certification bypasses
- ✅ all-or-nothing candidate activation
- ✅ exact replay-versus-persistence comparison
- ✅ conflict-minimization root and budget correctness
- ✅ backend timeout and provenance diagnostics
- ✅ runtime-to-formal contract checks and complete formal workflow triggers
- ✅ human-first README and clearer architecture documentation

## Next architecture layer

### v0.26 — Package and backend trust distribution

- signed package and backend manifests
- compatibility and conformance evidence attached to published packages
- package-registry protocol that separates discovery from installation and activation
- trust policies for profile, backend, validator, and certifier identities
- reproducible package build artifacts and provenance
- migration dry-run reports before an active binding changes

### v0.27 — Hierarchical reasoning and projection

- explicit strategy / architecture / implementation / execution abstraction layers
- cross-layer conflict projection and backjump targets
- scoped learned knowledge promotion between abstraction levels
- hierarchical fairness and obligation inheritance
- portfolio search across independently represented abstraction layers

### v0.28 — Deeper production conformance and visualization

- trace-conformance harness between the Python reducer and formal abstraction
- expanded formal coverage for effects, profile migration, leases, and distributed ownership
- richer Control Center graph/timeline views over the generic observability API
- signed history-check reports and externally verifiable state snapshots
- generated/property-based command-sequence testing across live execution and replay

## Continuing control-plane work

- run- and project-level productive-work budgets
- richer human approval queues and delegation scopes
- provider-neutral streamed executor events
- external log stores with retention, search, and signed references
- reconciliation assistance that never guesses external state
- rolling worker-fleet health and provider/AASM identity reconciliation
- multi-runtime SDKs and standardized interoperability contracts

## Longer-term possibilities

- governed package-evolution assistants that propose but never silently activate new contracts
- cross-project performance priors with strict profile/task-class isolation
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
