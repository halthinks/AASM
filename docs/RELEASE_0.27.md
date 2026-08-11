# AASM v0.27.0 — One-Command Local Full Stack

AASM v0.27.0 turns the v0.26 Research Synthesis Hero Stack into a locally operable application.

## User outcome

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
docker compose up --build
```

Then open `http://localhost:8787/`.

The browser shows a PostgreSQL-backed, partially progressed research-synthesis machine and provides one-click switching to the completed canonical run.

## Included services

- PostgreSQL 17;
- canonical reference-machine bootstrap;
- the existing AASM HTTP runtime;
- the existing Control Center extended with stack discovery;
- one default deterministic worker;
- an optional second worker;
- an explicit `stackctl` maintenance service.

## Canonical machine paths

Bootstrap uses the existing `run_research_synthesis_demo()` reference application.

The default worker uses:

```text
AASMRemoteClient
→ worker registration
→ heartbeat
→ claim-next
→ durable lease
→ execution telemetry
→ complete lease
```

No service writes AASM database tables or snapshot JSON directly.

## Reset behavior

`stackctl fresh` creates a new setup machine and updates the selected stack metadata while retaining prior machines. This preserves the replay and audit history that AASM exists to protect.

A destructive volume reset remains available through ordinary Docker Compose volume removal.

## Control Center additions

The existing Control Center now discovers local-stack metadata from authenticated `GET /demo-stack` and automatically loads the selected machine. It retains all prior mission, effect, worker, lease, telemetry, artifact, and v0.26 reasoning views.

## Release gates

v0.27.0 requires:

- Python 3.11, 3.12, and 3.13 tests;
- SQLite stack bootstrap, worker, reset, and replay tests;
- PostgreSQL coordination tests;
- embedded Control Center JavaScript validation;
- Docker Compose configuration validation;
- Docker Compose end-to-end smoke test;
- runtime/release/adoption source-contract checks;
- bounded TLA+/TLC and Promela/SPIN assurance gates.

## Version boundary

The package and server runtime are `0.27.0`.

The remote compatibility protocol remains:

```text
aasm.remote.v1 / 0.19.0
```

The protocol number is intentionally independent of the package release.
