# AASM One-Command Local Full Stack

The v0.27 stack remains the canonical local application in AASM v0.28.0. It packages the existing runtime, PostgreSQL store, worker/lease path, Research Synthesis Hero Stack, and Control Center into one Compose application.

## Start

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
docker compose up --build
```

Open:

```text
http://localhost:8787/
```

The root route enters the existing Control Center, supplies the local demo token, loads stack metadata, and selects the live setup machine automatically.

No model key, paid API, literature service, or host PostgreSQL installation is required.

## What starts

```text
Docker Compose
├── postgres     PostgreSQL 17 durable coordination store
├── bootstrap    seeds canonical setup and completed reference machines
├── runtime      existing AASM HTTP server and Control Center
├── worker-1     deterministic worker using existing remote lease APIs
├── worker-2     optional second worker under the two-workers profile
└── stackctl     explicit maintenance commands; not started by default
```

The bootstrap service creates two machines through `run_research_synthesis_demo()` and ordinary `AASMEngine` operations:

- **Live setup machine:** stopped before the known contradiction, with a worker resource and one deterministic lease task.
- **Completed reference machine:** the full learned-no-good, certificate, causal-backjump, steering, provenance, and replay trajectory.

The stack state file contains only demo discovery metadata and machine IDs. It does not replace PostgreSQL as authoritative machine state.

## Useful commands

### Inspect stack status

```bash
docker compose run --rm stackctl status
```

### Create a fresh live setup machine

```bash
docker compose run --rm stackctl fresh
```

This creates a new canonical machine and preserves previous histories.

### Create and select a new completed trajectory

```bash
docker compose run --rm stackctl complete
```

### Select the live or completed machine

```bash
docker compose run --rm stackctl select --selection active
docker compose run --rm stackctl select --selection completed
```

### Verify exact replay

```bash
docker compose run --rm stackctl verify --selection completed
```

The command runs the durable-history verifier, replays the event stream, and compares reconstructed and persisted snapshot hashes.

### Run the complete readiness check

```bash
docker compose run --rm stackctl check
```

The check requires:

- runtime `0.28.0` health;
- live machine state `SELECT`;
- completed machine state `COMPLETE`;
- default worker registration;
- a valid durable-history report for the completed run.

### Start the optional second worker

```bash
docker compose --profile two-workers up -d worker-2
```

### Stop while preserving data

```bash
docker compose down
```

### Destructive storage reset

```bash
docker compose down --volumes --remove-orphans
docker compose up --build
```

Use `stackctl fresh` for the normal non-destructive reset.

## Local security boundary

The runtime refuses non-loopback binding without a token. Compose supplies a local token named `aasm-local-demo` by default. The root redirect passes it once to the Control Center, which moves it into session storage and removes it from the visible URL.

Override the token and host port:

```bash
AASM_DEMO_TOKEN='replace-this' AASM_PORT=8788 docker compose up --build
```

The Compose stack is for local evaluation. Do not expose it publicly without a reverse proxy, TLS, secret management, network restrictions, and normal authentication controls.

## Working-path guarantee

```text
Compose process topology
    ↓
public AASM CLI / HTTP client
    ↓
existing AASMEngine operations
    ↓
existing event/reducer runtime
    ↓
PostgreSQL store
    ↓
existing calculus, assurance, replay, workers, leases, and observability
```

The default worker registers, heartbeats, claims a scheduled task, reports telemetry, and completes its lease through `AASMRemoteClient` and `RemoteWorkerLoop`.

**No container mutates machine snapshots or AASM tables directly.**

## Troubleshooting

### Port 8787 is already used

```bash
AASM_PORT=8788 docker compose up --build
```

### See all service logs

```bash
docker compose logs --tail=200
```

### Check individual services

```bash
docker compose ps
docker compose logs postgres
docker compose logs bootstrap
docker compose logs runtime
docker compose logs worker-1
```

### Rebuild after source changes

```bash
docker compose up --build --force-recreate
```

### Verify without the browser

```bash
docker compose run --rm stackctl check
```
