# Changelog

All notable user-visible changes to AASM are documented here. Detailed history through v0.18 is preserved in [`CHANGELOG_0.18_AND_EARLIER.md`](CHANGELOG_0.18_AND_EARLIER.md).

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
