# Remote execution and PostgreSQL coordination

AASM v0.8 adds a network control plane so workers can run on different hosts while sharing one authoritative machine history.

## Topology

```text
                    ┌──────────────────────────┐
                    │       AASM control       │
User / planner ────▶│ HTTP API + web inspector│
                    │                          │
                    │ PostgreSQL Store         │
                    └───────────┬──────────────┘
                                │
                ┌───────────────┼────────────────┐
                │               │                │
          worker host A    worker host B    worker host C
          code / CPU       GPU / sim        review / model
```

Workers do not need filesystem access to the controller. They register, heartbeat, claim work, renew leases, and report completion through `aasm.remote.v1` JSON/HTTP.

## Start the control plane

For development with SQLite:

```bash
aasm serve --store sqlite:///aasm.db --host 0.0.0.0 --port 8787 --token CHANGE_ME
```

For multi-host coordination:

```bash
pip install -e '.[postgres]'
aasm serve --store 'postgresql://aasm:password@db.example/aasm' --host 0.0.0.0 --port 8787 --token CHANGE_ME
```

Put TLS in front of the server. The built-in bearer token is intentionally simple transport authentication, not a complete identity platform.

The web inspector is available at `/ui`. Enter a machine ID to see current state, workers, leases, and registered model profiles.

## Remote protocol

Important endpoints:

- `GET /health`
- `POST /v1/machines`
- `GET /v1/machines/{machine_id}/state`
- `POST /v1/machines/{machine_id}/workers/register`
- `POST /v1/machines/{machine_id}/workers/{worker_id}/heartbeat`
- `POST /v1/machines/{machine_id}/claim`
- `POST /v1/machines/{machine_id}/leases/{lease_id}/heartbeat`
- `POST /v1/machines/{machine_id}/leases/{lease_id}/complete`
- `POST /v1/machines/{machine_id}/leases/{lease_id}/fail`
- `POST /v1/machines/{machine_id}/model-route`

The Python `AASMRemoteClient` wraps these endpoints without an extra HTTP dependency.

## PostgreSQL correctness boundary

`PostgresStore` mirrors the durable SQLite contracts but adds multi-host coordination semantics:

- event sequence allocation is serialized with a transaction-scoped PostgreSQL advisory lock per machine;
- machine event append and materialized snapshot update happen in the same transaction;
- task claims use a unique `(machine_id, task_id)` key;
- expired claims are atomically replaceable with `INSERT ... ON CONFLICT ... WHERE expires_at <= now`;
- lease renewal and release mutate the same shared claim table.

This prevents two hosts from both believing they own the same still-valid task.

## Failure behavior

A remote worker that loses contact stops renewing its worker heartbeat and task lease. Another controller/maintenance process can mark the worker stale and expire/reclaim its leases. A completed external side effect should still use AASM's effect/idempotency system because a task lease and an external provider transaction are separate correctness boundaries.
