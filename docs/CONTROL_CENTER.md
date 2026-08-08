# AASM Control Center

AASM v0.9 adds a browser command surface on top of the same durable runtime used by the CLI and remote workers.

Start it with:

```bash
aasm serve --store runs.db --host 127.0.0.1 --port 8787
```

For multi-host deployments:

```bash
aasm serve \
  --store 'postgresql://user:pass@db-host/aasm' \
  --host 0.0.0.0 \
  --port 8787 \
  --token "$AASM_TOKEN"
```

Then open `/ui`.

## What the interface shows

- authoritative machine state and version
- current goal and plan graph
- frontier size
- registered workers
- active leases / task ownership
- configured model profiles
- model-call token and estimated cost totals
- governance-overhead ratio
- spend grouped by productive work, verification, governance, permission review, synthesis, and retries
- evidence and control provenance
- legal transitions

The browser polls `/v1/machines/{machine_id}/dashboard`, so the same interface works whether the workers are local processes or remote machines using PostgreSQL.

## User steering

The Control Center can submit an additive steering instruction. AASM records it as a durable `user_interrupt` event plus machine control metadata. It does not silently rewrite prior history.

This is intentionally provenance-preserving: a user can change direction without erasing why the earlier plan existed.

## API endpoints added in v0.9

```text
GET  /v1/machines/{id}/dashboard
POST /v1/machines/{id}/interrupt
POST /v1/machines/{id}/model-usage
POST /v1/machines/{id}/review-gate
```

Existing worker, lease, model-routing, and state endpoints remain available.

## Security boundary

The browser UI is an operator surface, not a replacement for network security. For remote deployments use a bearer token, TLS termination, private networking/VPN where appropriate, and database credentials with least privilege.
