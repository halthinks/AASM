# Remote execution and PostgreSQL coordination

AASM v0.8 adds a network control plane so workers can run on different hosts while sharing one authoritative machine history. The v0.9 audit hardens that boundary for concurrent state, capacity/quota policy, effects, and remote HTTP exposure.

## Topology

```text
                    ┌──────────────────────────┐
                    │       AASM control       │
User / planner ────▶│ HTTP API + Control Center│
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

Local development stays loopback-only by default:

```bash
aasm serve --store sqlite:///aasm.db --host 127.0.0.1 --port 8787
```

For multi-host coordination, install the PostgreSQL extra and provide authentication. Prefer the environment variable so the bearer token is not exposed in the process command line:

```bash
pip install -e '.[postgres]'
export AASM_SERVER_TOKEN='replace-with-a-strong-random-secret'
aasm serve \
  --store 'postgresql://aasm:password@db.example/aasm' \
  --host 0.0.0.0 \
  --port 8787
```

AASM refuses a non-loopback bind unless `--token` or `AASM_SERVER_TOKEN` is present. The built-in HTTP server does **not** terminate TLS. Put it behind HTTPS/TLS at a reverse proxy, private ingress, VPN, or equivalent trusted network boundary. The bearer token is deliberately simple transport authentication, not a complete identity platform.

The Control Center is available at `/ui`. The page can be loaded without the bearer token so the operator can enter it; all machine data and mutation endpoints remain authenticated when a token is configured.

## Remote protocol

Important endpoints include:

- `GET /health`
- `POST /v1/machines`
- `GET /v1/machines/{machine_id}/state`
- `GET /v1/machines/{machine_id}/dashboard`
- `POST /v1/machines/{machine_id}/workers/register`
- `POST /v1/machines/{machine_id}/workers/{worker_id}/heartbeat`
- `POST /v1/machines/{machine_id}/claim`
- `POST /v1/machines/{machine_id}/claim-next`
- `POST /v1/machines/{machine_id}/leases/{lease_id}/heartbeat`
- `POST /v1/machines/{machine_id}/leases/{lease_id}/complete`
- `POST /v1/machines/{machine_id}/leases/{lease_id}/fail`
- `POST /v1/machines/{machine_id}/model-route`

The Python `AASMRemoteClient` wraps the worker-facing endpoints without an extra HTTP dependency.

## PostgreSQL correctness boundary

`PostgresStore` is the shared coordination authority for real multi-host execution:

- event append is serialized by a transaction-scoped advisory lock per machine;
- every new event is reduced against database-canonical event history, then the canonical materialized snapshot is updated in the same transaction;
- stale hosts therefore cannot overwrite state committed by another host;
- task ownership is unique per `(machine_id, task_id)` and active claims are held in one shared claim table;
- claims take the machine event lock before the claim lock, read the current durable snapshot, and enforce the **current** worker mapping, resource enabled/capacity state, and quota policy inside the claim transaction;
- stale worker processes cannot use an old local capacity or quota configuration to overbook work;
- active claim demand is accounted by resource, worker, and machine scope;
- effect execution uses a row-locked atomic attempt claim, so two hosts cannot both move one authorized effect into `RUNNING` and invoke it;
- lease renewal/release and effect recovery remain explicit durable operations.

## Failure behavior

A remote worker that loses contact stops renewing its worker heartbeat and task lease. Another controller/maintenance process can mark the worker stale and expire/reclaim its leases.

A task lease and an external provider transaction are separate correctness boundaries. Externally visible operations still use the effect/idempotency system. Normal `AASMEngine.resume()` is passive and safe for dashboards/HTTP handlers; only a genuine crash-recovery path should use `recover_effects=True` (or `recover_unfinished()`) to convert unresolved `RUNNING` effects to `UNKNOWN` for reconciliation.
