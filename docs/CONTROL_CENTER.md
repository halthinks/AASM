# AASM Control Center

AASM v0.9 adds a browser command surface on top of the same durable runtime used by the CLI and remote workers.

Start locally with the default loopback boundary:

```bash
aasm serve --store runs.db --host 127.0.0.1 --port 8787
```

For multi-host deployments, prefer an environment bearer token rather than placing the secret in the command line:

```bash
export AASM_SERVER_TOKEN='replace-with-a-strong-random-secret'
aasm serve \
  --store 'postgresql://user:pass@db-host/aasm' \
  --host 0.0.0.0 \
  --port 8787
```

AASM refuses non-loopback binding when no bearer token is configured. The built-in server does not provide TLS termination; remote deployments should put it behind HTTPS/TLS at a reverse proxy, private ingress, VPN, or equivalent trusted boundary.

Then open `/ui`. If authentication is configured, enter the bearer token in the Control Center. It is kept in browser `sessionStorage` for that tab/session, not written into the durable AASM run.

## What the interface shows

- authoritative machine state and version
- current goal and plan graph
- frontier size
- registered workers
- active leases / task ownership
- configured model profiles
- model-call token and estimated cost totals
- cached-input reads and cache-write accounting
- governance-overhead ratio
- spend grouped by productive work, verification, governance, permission review, synthesis, and retries
- evidence and control provenance
- legal transitions

The browser polls `/v1/machines/{machine_id}/dashboard`, so the same interface works whether workers are local processes or remote machines using PostgreSQL.

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

The Control Center is an operator surface, not a replacement for network security. The v0.9 audit adds several defensive defaults:

- non-loopback bind requires bearer authentication;
- bearer comparison uses a constant-time comparison;
- JSON request bodies are size-limited;
- UI/API responses use `Cache-Control: no-store`;
- the UI receives CSP, no-sniff, no-referrer, frame-deny, and restricted permissions headers;
- durable model/worker/task labels are escaped before HTML rendering to prevent stored-label injection;
- machine data/mutation APIs remain authenticated even though `/ui` and `/health` can be loaded without the bearer token.

For remote deployments still use TLS termination, private networking/VPN where appropriate, strong random bearer secrets, and database credentials with least privilege. AASM's built-in bearer token is intentionally lightweight; organizations needing user-level identity, SSO, audit roles, or fine-grained authorization should put an identity-aware gateway in front of the control plane.
