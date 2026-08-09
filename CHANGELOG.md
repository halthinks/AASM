# Changelog

All notable user-visible changes to AASM are documented here. Detailed history through v0.18 is preserved in [`CHANGELOG_0.18_AND_EARLIER.md`](CHANGELOG_0.18_AND_EARLIER.md).

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
