# Mission Controls, Controlled Forks, and High-Volume Observability

AASM v0.19 adds the operator layer needed to run long-lived missions without conflating execution control, effect approval, or history branching.

## Mission pause modes

A mission-level pause is independent of the AASM machine state, Planner/Builder/Verifier directives, selective information-change checkpoints, and worker lifecycle state.

- `QUIESCE` blocks all new task claims but lets already-active leases finish.
- `SUSPEND` commits the pause first, then releases active leases so their work can be reclaimed after the mission resumes.

Both modes are durable. Task claiming reads canonical store state before and after ownership creation, so a stale worker process cannot race past a newly committed mission pause.

```python
from aasm import MissionControlAction, MissionControlRecord, MissionPauseMode

engine.pause_mission(MissionControlRecord(
    MissionControlAction.PAUSE,
    actor="operator",
    reason="review unexpected provider behavior",
    mode=MissionPauseMode.QUIESCE,
))

engine.resume_mission(MissionControlRecord(
    MissionControlAction.RESUME,
    actor="operator",
    reason="review complete",
))
```

Mission resume reopens admission only. It does not silently resume tasks paused by an information-change checkpoint, reactivate an OFFLINE worker, authorize an effect, or recreate a released lease.

## Pending-effect approval

The Control Center and API expose the durable effect queue. Approval remains explicit:

```text
PROPOSED effect
      ↓
operator inspects intent / payload / risk
      ↓
authorize_pending_effect(actor, reason)
      ↓
AUTHORIZED effect
      ↓
type-specific executor
```

Approval does not execute an effect. Provisioning, fork creation, and other external-effect types retain separate execution endpoints and adapters.

## Controlled forks

A controlled fork is represented as a `machine.fork` effect with a deterministic target machine ID and source event sequence.

```python
from aasm import ForkRequest

proposal = engine.propose_fork(ForkRequest(
    source_sequence=engine.current_sequence(),
    actor="operator",
    reason="evaluate an alternate implementation strategy",
))

engine.authorize_pending_effect(
    proposal.spec.effect_id,
    actor="operator",
    reason="approved isolated experiment",
)

result = engine.execute_fork(proposal.spec.effect_id)
```

The target machine ID is part of the idempotency boundary. Re-executing an already-successful fork effect does not create another branch. A pre-existing target with different lineage is rejected.

The legacy low-level `engine.fork()` and `aasm fork` APIs remain available for embedded/local code that already owns authority. Network and Control Center workflows use the controlled proposal/approval/execution path.

## Cursor-paged telemetry and artifacts

Telemetry and artifact-reference endpoints now use opaque cursors rather than returning an ever-growing array.

```python
page = engine.telemetry_page(limit=100)
while page["has_more"]:
    page = engine.telemetry_page(cursor=page["next_cursor"], limit=100)
```

New telemetry records have stable `record_id` values. New external artifact references have stable `artifact_id` values. Legacy rows are paged with compatibility identities; if bounded retention removes the cursor anchor, AASM returns an explicit cursor-expired error instead of silently skipping or duplicating records.

The cursor is an iteration token, not an authorization token. Every page request still requires normal API authentication and policy.

## Artifact previews

The Control Center can request text previews from a configured artifact backend. Preview size is bounded. The authoritative log or artifact remains in its external backend; AASM stores only the reference and provenance.

## Local process supervisor

`LocalProcessSupervisorAdapter` lets one AASM control plane operate a local worker fleet without Kubernetes.

- commands are explicit argv lists; no shell strings are evaluated;
- optional `workspace_root` confines worker `cwd` values;
- worker IDs are generated deterministically from a prefix and persisted counter;
- the PID ledger is written atomically;
- the provisioning effect idempotency key prevents duplicate starts;
- drain requests terminate only selected or oldest matching local workers.

The worker command may use:

```text
{worker_id}
{resource_id}
{request_id}
```

The supervisor also supplies `AASM_WORKER_ID`, `AASM_RESOURCE_ID`, and `AASM_PROVISION_REQUEST_ID` environment variables.

## Docker Compose supervisor

`DockerComposeScaleAdapter` reads the current replica count with `docker compose ps -q` and changes the selected service with explicit argv:

```text
docker compose up -d --scale SERVICE=N SERVICE
```

It supports compose-file, project-directory, and project-name configuration. As with every provisioning adapter, it is invoked only after the enclosing durable effect is authorized.

## Runtime provider configuration

Start a turnkey local control plane with a JSON configuration:

```bash
aasm serve \
  --store runs.db \
  --token "$AASM_SERVER_TOKEN" \
  --runtime-config examples/runtime-config.local.json
```

The configuration can register Kubernetes, local-process, and Docker Compose provisioners plus memory or local-directory artifact backends. Credentials and provider IAM remain outside the config contract and must be supplied through the normal operating environment.

## Control boundaries

The following remain deliberately distinct:

```text
mission PAUSED
    ≠ machine terminal state
    ≠ Planner PAUSE directive
    ≠ change-impact checkpoint
    ≠ worker OFFLINE

approved effect
    ≠ executed effect

fork proposed
    ≠ fork authorized
    ≠ fork created

cursor returned
    ≠ permission to read the next page
```

## Lease loss after suspension

A generic worker process cannot always be force-cancelled at the exact instant a `SUSPEND`, worker `OFFLINE`, expiry, or other revocation releases its lease. The worker may finish local computation after durable ownership is gone.

AASM v0.19 therefore distinguishes executor completion from durable task completion. `RemoteWorkerLoop` checks the returned lease status and emits `LEASE_LOST` rather than `COMPLETED` when the result no longer owns the lease. That result is not accepted as successful task completion. Externally visible actions must still use the effect/idempotency boundary, because cancelling a task lease cannot undo an external side effect that already occurred.

## Targeted drain versus replica-count scale-down

A local supervisor can confirm the exact logical worker process it stopped and returns `drained_worker_ids`. Kubernetes and Docker Compose replica scaling generally cannot prove which AASM worker identity the platform selected for termination.

AASM marks a registered worker `DRAINING` only when an adapter explicitly confirms that logical worker ID. Replica-count adapters report `drain_scope=replica-count`; requested logical targets remain recorded as unconfirmed until worker heartbeat/lifecycle reconciliation establishes what actually disappeared. This prevents a provider-side scale operation from falsely changing the state of the wrong AASM worker.

## In-memory contract parity

The default `MemoryStore` now accepts the same resource-capacity, quota, task-claim, event-sequence, and effect-attempt ownership contracts used by the durable stores. It remains single-process/in-memory, but default tests and embedded runs no longer bypass those runtime checks accidentally.
