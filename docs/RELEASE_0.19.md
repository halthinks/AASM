# AASM v0.19.0 — Mission Controls and High-Volume Observability

AASM v0.19 adds the operator-control layer for long-running, multi-host missions.

## Added

- durable mission-level `QUIESCE`, `SUSPEND`, and `RESUME` controls;
- canonical pre/post claim checks that prevent stale workers from crossing a newly committed mission pause;
- explicit lease-loss telemetry when a worker finishes after ownership was released or revoked;
- status-separated effect queues for approval, execution, reconciliation, and failure handling;
- authority-gated controlled forks represented as durable `machine.fork` effects;
- opaque cursor paging for execution telemetry and external artifact references;
- stable telemetry-record and artifact-reference identities;
- authenticated, bounded artifact previews that require the reference to belong to the selected machine;
- a local process supervisor with explicit argv, persistent PID/idempotency state, and workspace confinement;
- a Docker Compose scaling adapter with explicit argv;
- runtime JSON configuration for provisioners and artifact backends;
- Control Center actions for mission pause/resume, effect approval, controlled forks, worker lifecycle, telemetry pages, and artifact previews;
- CLI and remote-client surfaces for the same controls;
- MemoryStore parity with durable resource, quota, task-claim, event-sequence, and effect-attempt contracts.

## Control invariants

- Pausing a mission does not mutate the machine state or Planner-owned plan.
- Approving an effect does not execute it.
- Proposing a fork does not create it.
- A cursor does not grant access to the next page.
- Provider replica scale-down does not prove which logical AASM worker was terminated.
- `LEASE_LOST` is not successful completion.
- External effects remain behind authorization, idempotency, and reconciliation boundaries.

## Compatibility

The low-level `engine.fork()` and `aasm fork` surfaces remain available for embedded callers that already own authority. Network and Control Center use the controlled proposal/approval/execution path.

The former detailed changelog through v0.18 is preserved in `CHANGELOG_0.18_AND_EARLIER.md`.
