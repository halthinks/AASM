# Changelog

All notable user-visible changes to AASM are documented here. Detailed history through v0.18 is preserved in [`CHANGELOG_0.18_AND_EARLIER.md`](CHANGELOG_0.18_AND_EARLIER.md).

## [0.27.0] - 2026-08-11

AASM v0.27.0 makes the v0.26 reference application operable as a one-command PostgreSQL, runtime, worker, and Control Center stack while preserving the existing event/reducer authority path.

### One-command local stack

- added `compose.yaml` with PostgreSQL 17, canonical bootstrap, runtime, default worker, optional second worker, and explicit `stackctl` service;
- added a reproducible Python 3.13 image with the PostgreSQL extra installed;
- added live setup and completed reference machines seeded through `run_research_synthesis_demo()`;
- added stack discovery metadata without moving authoritative machine state out of PostgreSQL;
- added authenticated `GET /demo-stack` and a root redirect into the existing Control Center;
- added automatic Control Center loading of the selected stack machine;
- added local stack status, fresh, complete, select, verify, check, and worker commands;
- added a deterministic worker that uses the existing remote registration, heartbeat, claim-next, lease, telemetry, and completion APIs;
- added an optional second worker through the `two-workers` Compose profile;
- made normal reset non-destructive by creating a fresh canonical machine while retaining prior histories;
- documented explicit destructive volume reset separately.

### Public adoption surface

- advanced `aasm.adoption.v1` to contract version `0.3.0`;
- added the local stack, worker lease path, `/demo-stack`, root/UI routes, and stack CLI to the supported surface;
- routed the public CLI, server, and Control Center through their v0.27 entry modules;
- retained `runtime_v25.AASMEngine` as the machine authority instead of creating a parallel stack runtime;
- retained `aasm.remote.v1 / 0.19.0` as the separate remote compatibility protocol.

### Verification and documentation

- added SQLite stack bootstrap, worker, non-destructive reset, HTTP discovery, and replay tests;
- added Docker Compose configuration validation and an end-to-end Compose smoke gate;
- expanded Control Center JavaScript validation to all embedded script blocks;
- added `docs/LOCAL_FULL_STACK.md` and `docs/RELEASE_0.27.md`;
- rewrote the README around `docker compose up --build` while preserving the human-readable Decision, Obligation, and Evidence explanation;
- updated the formal source-contract gate to enforce stack topology, working-path reuse, version visibility, and release documentation.

## [0.26.0] - 2026-08-11

AASM v0.26.0 delivers the first complete adoption-grade reference application without adding a parallel runtime or bypassing the existing authority boundary.

### Research Synthesis Hero Stack

- added the built-in `aasm.research-synthesis@1.0.0` profile and package manifest;
- added explicit research decision namespaces, persistent obligations, evidence contracts, fairness defaults, model-routing defaults, governance defaults, and controlled profile evolution;
- added a fixed synthetic CC0 offline corpus with a recorded SHA-256 manifest;
- added deterministic setup and complete reference-run modes;
- added a known contradiction that produces a validated explanation, soft no-good, independently verified certificate, hard learned constraint, and non-chronological backjump;
- demonstrated preservation of an unrelated structured-report decision after the causal backjump;
- demonstrated that the failed `retrieval_only` model is blocked from recurring;
- injected a mid-run prior-knowledge requirement through the existing change-impact pathway;
- restored subgroup work through an existing conditional lock break;
- produced a known-good structured synthesis with claim-level evidence IDs and machine provenance;
- added exact event replay and reconstructed-versus-persisted history verification;
- added generated run summary, final artifact, machine export, history result, machine identity, and replay-command files.

### Product surface

- extended the existing `aasm demo` command with `--scenario research-synthesis` and `--mode setup|complete`;
- added programmatic `run_research_synthesis_demo()`, corpus verification, and research profile/package helpers;
- added the research profile to the canonical built-in registry;
- extended the existing Control Center with Decision, Obligation, Evidence, conflict/backjump, fairness, profile-history, and final-artifact panels;
- added the reference application to `aasm.adoption.v1`;
- packaged the fixed research corpus in the Python distribution.

### Documentation and verification

- added `WHY_AASM.md` as a reproducible baseline comparison;
- added `docs/RESEARCH_SYNTHESIS_DEMO.md` and `docs/RELEASE_0.26.md`;
- kept v0.26.0, the next v0.27.0 milestone, and the separate remote protocol visible at the top of the README;
- added profile fingerprint, corpus digest, setup, complete-run, replay, artifact, CLI, and Control Center regression coverage;
- retained the ordinary event/reducer runtime, stores, calculus, assurance boundary, CLI, HTTP, and Control Center implementation path.

## [0.25.2] - 2026-08-11

AASM v0.25.2 begins the Adoption and Operability program by defining one supported golden path over the existing v0.25.1 runtime.

### Added

- package-level `__version__` and explicit separation from the stable `aasm.remote.v1 / 0.19.0` compatibility protocol;
- machine-readable `aasm.adoption.v1` public API contract;
- inventories of supported top-level imports, `AASMEngine` methods, CLI commands, inspection surfaces, and HTTP endpoints;
- explicit `SUPPORTED`, `EXPERIMENTAL`, and `INTERNAL` compatibility meanings for the pre-1.0 project;
- `public_api_contract()` and `validate_public_api_contract()`;
- `aasm adoption-contract` CLI output;
- `GET /adoption-contract` HTTP output;
- regression coverage for Python, CLI, and remote contract inspection.

### Architecture and adoption

- declared that reference applications, Control Center additions, runbooks, and external adapters must use the existing event/reducer runtime and authority boundary;
- prohibited parallel runtimes, alternate reducers, private snapshot mutation, and direct database writes as adoption shortcuts;
- replaced the architecture-first near-term roadmap with a release-gated adoption sequence: research-synthesis hero stack, one-command local stack, distribution/runbooks, and a thin LangGraph adapter;
- added measurable adoption scorecard gates for startup time, replay equality, contradiction visibility, learned no-good reuse, causal backjumping, work preservation, and operator drills.

### Documentation

- kept the current package/runtime version, next planned release, and separate remote-protocol version visible near the top of the README;
- documented the canonical adoption surface in the README and architecture guide;
- made the formal release-by-release implementation plan the primary roadmap.

## [0.25.1] - 2026-08-10

AASM v0.25.1 stabilizes the v0.23–v0.25 architecture and closes the assurance, atomicity, replay, formal-model, and readability defects found during source-level review.

### Fixed

- moved certificate enforcement to the calculus commit boundary so inherited and indirect paths cannot create active uncertified hard constraints;
- changed strict hard learning to create a soft constraint first, followed by certificate registration, independent verification, and explicit hard promotion;
- made complete candidate activation all-or-nothing through one staged calculus update and one durable snapshot commit;
- replaced the shallow history linter with reducer-based replay verification and exact reconstructed-versus-persisted snapshot comparison;
- added contiguous event, state continuity, legal transition, terminal absorption, lock, profile fingerprint, completion, and hard-certificate checks;
- corrected conflict-core minimization for non-conflicting inputs, duplicate literals, empty root conflicts, and exact budget boundaries;
- made adopted minimized explanations immutable successor objects with durable lineage;
- enforced finite-domain, callback, and portfolio candidate, combination, cost, and latency budgets;
- retained every contributing backend when portfolio candidates deduplicate to the same assignment;
- refreshed every observability surface from canonical storage and closed all graph edges over represented nodes;
- added a heterogeneous causal graph joining decisions, obligations, evidence, locks, conflicts, explanations, constraints, certificates, verifications, and candidates;
- made fairness debt actionable with thresholds, overage, lock reasons, and required next action;
- aligned assurance defaults across new snapshots, deserialization, runtime policy, CLI, schemas, and HTTP health reporting.

### Formal assurance

- separated `LearnSoft`, `RegisterCertificate`, `VerifyCertificate`, and `PromoteHard` in the TLA+ model;
- modeled candidate staging and atomic activation explicitly;
- added bounded fairness as a checked temporal property;
- aligned Promela terminal guards with staged-candidate invariants;
- expanded formal-workflow path triggers to every transition-critical runtime source;
- tied static model contracts to concrete Python safeguards;
- retained pinned, hash-verified TLA+ and SPIN toolchains.

### Documentation

- rewrote the README for human readers around a concrete failure-and-recovery example;
- moved theorem-prover terminology behind plain-English explanations;
- added a five-minute start, capability map, correctness boundary, documentation guide, and explicit runtime/protocol version explanation;
- updated Decision Backend, Formal Assurance, Observability, and Roadmap documentation.

## [0.25.0] - 2026-08-10

AASM v0.25 adds domain-neutral observability over the formal calculus, decision backend ecosystem, assurance state, and profile package lifecycle.

### Added

- Decision Graph, Obligation Graph, and Evidence Graph projections;
- conflict/backjump timeline and event-derived restart, profile, candidate, and assurance timeline;
- fairness-debt projection for persistent obligations;
- package binding, evolution proposal, migration, and configuration history views;
- candidate-backend and assurance summaries;
- generic `AASMEngine.inspect_machine()` inspection surfaces;
- `aasm inspect` CLI surface;
- v0.25 HTTP runtime wiring;
- `schemas/observability-report.schema.json`;
- `docs/OBSERVABILITY.md` and `docs/RELEASE_0.25.md`.

The observability layer uses generic AASM objects rather than source-code, CAD, scientific, business, or other domain-specific concepts.

## [0.24.0] - 2026-08-10

AASM v0.24 adds independently checkable assurance around learned machine knowledge and durable execution history.

### Added

- durable assurance policy, certificate, verification, history-check, minimization, and generalization state;
- `CertificateRecord` and `CertificateVerification` contracts;
- exact learned-constraint projection certification;
- detached SHA-256 artifact verification;
- certificate-gated hard-constraint promotion;
- durable event-history checking for sequence, identity, machine, terminal-state, and completion properties;
- `GREEDY_IRREDUCIBLE` and `EXACT_BOUNDED` conflict-core minimization through a `ConflictOracle`;
- assurance state migration for older snapshots;
- assurance and history schemas;
- `docs/FORMAL_ASSURANCE.md` and `docs/RELEASE_0.24.md`.

The assurance layer verifies coverage, provenance, and declared machine properties. It does not substitute for domain-specific truth or model validation.

## [0.23.0] - 2026-08-10

AASM v0.23 makes candidate decision generation replaceable without moving state authority out of the deterministic runtime.

### Added

- durable candidate request, batch, lifecycle, selection, and activation state;
- backend capability, budget, usage, diagnostic, explanation, batch, and lifecycle contracts;
- deterministic finite-domain reference backend with stable continuation tokens;
- human proposal backend;
- provider-neutral callback backend for heuristic/model integrations;
- portfolio backend with candidate deduplication and backend provenance;
- backend registry and capability routing;
- runtime candidate generation, revalidation, selection, and activation;
- CLI surfaces for backend and candidate inspection/control;
- candidate state and batch schemas;
- `docs/DECISION_BACKENDS.md` and `docs/RELEASE_0.23.md`.

Backends propose candidate models. AASM independently checks profile namespaces, decision identity, parents, pinned assignments, learned hard constraints, and fairness before activation.

## [0.22.0] - 2026-08-09

AASM v0.22 introduces domain-neutral profile packages so use-case meaning can evolve outside the deterministic kernel.

### Added

- versioned `AASMProfile` and `AASMPackageManifest` contracts;
- immutable profile and package fingerprints;
- explicit per-machine `ProfileBinding` state with backward-compatible snapshot migration;
- independent Decision Backend, Obligation Adapter, Semantic Validator, Conflict Explainer, and Constraint Certifier protocols;
- opt-in discovery of already-installed profiles through the `aasm.profiles` Python entry-point group;
- solver-neutral `DecisionRequest` and `CandidateModel` records;
- kernel-side candidate validation against decision identity, namespaces, parent decisions, pinned assignments, hard constraints, and fairness;
- generic, fingerprinted `SemanticResultEnvelope` records for tools, humans, agents, validators, and simulations;
- durable semantic-result storage and dashboard summary;
- `ProfileConformanceKit` with profile/package structure checks, fingerprint collision detection, serialization checks, adapter protocol checks, and optional determinism probes;
- built-in `aasm.bare` and domain-neutral `aasm.evolve` profiles;
- an Evolve machine, evidence policy, fairness policy, package manifests, and a non-software field-study example;
- evidence-backed `ProfileEvolutionProposal` records;
- explicit `ProfileMigration` and authorized profile-version activation;
- separate run-configuration history so instance tuning is not confused with package evolution;
- CLI commands for profile discovery, description, validation, conformance, binding, evolution, candidate validation, decision requests, and semantic results;
- `docs/PROFILE_PACKAGES.md`, `docs/EXTENSION_CONTRACT.md`, and `docs/RELEASE_0.22.md`;
- public v0.22 runtime, CLI, and server wiring.

### Package evolution semantics

- packages and profiles are authored contracts, not self-modifying agents;
- a run may adapt under a stable profile through decisions, locks, learned constraints, backjumping, and restart;
- changing a contract requires a new semantic version and fingerprint;
- runtime evidence may create an evolution proposal, but cannot silently activate a new contract;
- activation requires conformance, an explicit migration, and an authorized actor;
- profile discovery never downloads packages or executes adapter code automatically.

### Compatibility

- existing v0.21 machines load with an empty profile binding and semantic-result ledger;
- no SQL migration is required because both fields live in the existing snapshot JSON/JSONB;
- the formal calculus, machine definitions, effects, persistence stores, workers, leases, mission controls, PBV profile, replay, and historical forks remain available;
- package metadata is `0.22.0`.

See [`docs/PROFILE_PACKAGES.md`](docs/PROFILE_PACKAGES.md), [`docs/EXTENSION_CONTRACT.md`](docs/EXTENSION_CONTRACT.md), and [`docs/RELEASE_0.22.md`](docs/RELEASE_0.22.md).

## [0.21.0] - 2026-08-09

AASM v0.21 integrates the formal conflict-learning calculus into the production event-sourced runtime.

### Added

- backward-compatible `MachineSnapshot.calculus` state with automatic migration of older snapshots;
- typed decision literals, decisions, obligations, locks, conflicts, explanations, learned constraints, fairness policies, and Planner recovery decisions;
- a durable active decision model and conditional obligation activation;
- model-relative locks that break automatically when their decision condition stops holding;
- guarded no-good projection from validated conflict explanations;
- hard/soft learning policy that prevents evidence disagreements and heuristic explanations from becoming hard exclusions;
- same-guard no-good subsumption;
- deterministic graph-directed non-chronological backjumping using causal roots, decision depth, dependent-closure size, and stable ID tie-breaking;
- preservation of unrelated later decisions and plan regions during backjump;
- automatic `needs_revalidation` marking plus reuse of information-change checkpoints for the affected plan region;
- `restart_search()` semantics that discard speculative assignments while retaining evidence, conflicts, learned constraints, effects, mission state, leases, replay, and fork provenance;
- bounded cross-model fairness accounting and Planner-authorized deferral/disposition;
- completion gating for unresolved mandatory persistent obligations;
- PBV-authorized `RecoveryDecision(BACKJUMP | RESTART_SEARCH)`;
- calculus summary in the runtime dashboard;
- `aasm calculus` and `aasm calculus-fairness` CLI inspection commands;
- `schemas/calculus-state.schema.json` and the optional calculus field in the machine snapshot schema;
- `docs/FORMAL_CALCULUS.md` and `docs/RELEASE_0.21.md`.

### Architecture

The v0.21 control loop is now executable:

```text
abstract decisions
    → conditional activation
    → authorized execution
    → verification evidence
    → conflict explanation
    → learned blocking constraint
    → repair, investigation, backjump, or restart
```

Calculus state is committed through the existing `SNAPSHOT_PATCHED` event and pure reducer. No parallel runtime, persistence database, or alternate authority mechanism was added.

### Backjump semantics

- explanations identify the assumptions materially responsible for a contradiction;
- `DERIVED` decisions are traced to revisable explicit causal roots;
- the deepest root with the smallest dependent closure is selected deterministically;
- only the pivot, dependent decisions, linked obligations, and linked plan nodes are invalidated or marked for revalidation;
- unrelated active work remains preserved even when it was created later;
- the remaining model must satisfy all active hard constraints before recovery is committed.

### Locking and fairness

- work irrelevant only under the current model is locked rather than deleted;
- every lock carries a condition, reason, originating decision, epoch, evidence, and scope;
- model change, backjump, and search restart reevaluate every active lock;
- persistent obligations age by deterministic model epochs rather than wall-clock time;
- overdue obligations must be exposed by the next model, explicitly deferred within policy, or terminally dispositioned.

### Compatibility

- existing machine states, custom machine definitions, public runtime APIs, effects, stores, workers, leases, mission controls, PBV directives, and historical forks remain available;
- no SQL migration is required because calculus state is stored inside the existing snapshot JSON/JSONB;
- snapshots without the new field deserialize with the canonical empty calculus state;
- public package, CLI, and HTTP control-plane wrappers now use the v0.21 runtime;
- package metadata is `0.21.0`.

See [`docs/FORMAL_CALCULUS.md`](docs/FORMAL_CALCULUS.md) and [`docs/RELEASE_0.21.md`](docs/RELEASE_0.21.md).

## [0.19.0] - 2026-08-08

### Added

- durable mission-level `QUIESCE`, `SUSPEND`, and `RESUME` controls;
- canonical pre/post task-claim checks around mission pause;
- `LEASE_LOST` execution telemetry for workers that finish after durable ownership was released or revoked;
- status-separated effect queues for approval, execution, reconciliation, and failure handling;
- authority-gated controlled forks represented as durable `machine.fork` effects;
- opaque cursor paging for execution telemetry and external artifact references;
- stable telemetry-record and artifact-reference identities;
- bounded authenticated artifact previews scoped to the selected machine;
- `LocalProcessSupervisorAdapter` with explicit argv, persistent PID/idempotency state, and workspace-root confinement;
- `DockerComposeScaleAdapter` with explicit argv and replica-count semantics;
- runtime JSON configuration for provisioners and artifact backends;
- Control Center mission/effect/fork/worker/telemetry/artifact controls;
- CLI and remote-client surfaces for mission control, effect approval, controlled forks, cursor paging, and worker lifecycle;
- in-memory store parity with durable event sequencing, effect-attempt ownership, resource capacity, quotas, and task claims.

### Control semantics

- a mission pause is not a machine-state transition, Planner directive, selective change checkpoint, or worker lifecycle mutation;
- `QUIESCE` blocks new claims while active leases may finish;
- `SUSPEND` commits the pause and releases active leases;
- approving an effect never executes it;
- proposing a fork never creates it;
- a cursor is an iteration token, not an authorization token;
- provider replica scale-down does not prove which logical AASM worker terminated;
- a worker result reported after lease loss is never recorded as successful durable completion;
- external actions remain behind effect authorization, idempotency, attempt ownership, and UNKNOWN-outcome reconciliation.

### Compatibility

- low-level `engine.fork()` and `aasm fork` remain available for embedded callers that already own authority;
- the remote API and Control Center use proposal → approval → execution for controlled forks;
- prior APIs remain available through the v0.19 runtime and compatibility entry modules.

See [`docs/RELEASE_0.19.md`](docs/RELEASE_0.19.md) and [`docs/MISSION_CONTROLS_OBSERVABILITY.md`](docs/MISSION_CONTROLS_OBSERVABILITY.md).
