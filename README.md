<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, models, humans, and real work.**

AASM keeps the official state of a long-running job outside the language model. Models propose; AASM decides what may become durable, records why, preserves evidence, and recovers from bad assumptions without throwing away unrelated work.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## Current release — v0.34.0

**Distributed Recovery Certification**

| Identity | Value |
|---|---|
| Package/runtime | `aasm-runtime 0.34.0` |
| Adoption contract | `aasm.adoption.v1 / 0.10.0` |
| Trace contract | `aasm.trace.v1 / 0.1.0` |
| Provenance contract | `aasm.provenance.v1 / 0.1.0` |
| Recovery contract | `aasm.recovery.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |
| Next release | **v0.35.0 — Semantic Problem Model Foundations** |

v0.34 turns distributed recovery from a collection of capabilities into an executable certification report. `aasm recovery-certify` deterministically injects worker loss, lease expiry and reclaim, stale completion, duplicate delivery, database restart, supervisor loss, and an external `UNKNOWN` effect followed by explicit reconciliation. A scenario passes only when there is one valid authority/effect outcome or an explicit reconciliation boundary.

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
docker compose up --build

aasm adoption-contract
aasm recovery-certify
```

### What AASM protects

- **Decisions** — named assumptions and choices with causal provenance.
- **Obligations** — work that cannot silently disappear.
- **Evidence** — durable support for decisions, conflicts, and completion.
- **Recovery** — causal backjumping and restart without amnesia.
- **Effects and leases** — explicit authority, idempotency, expiry, stale-result rejection, and reconciliation.
- **Replay and formal trace** — reconstruct and check what actually happened.
- **Portable provenance** — signed content-addressed exports verifiable away from the original database.

## Architecture

```text
public AASM API
      ↓
durable event
      ↓
production reducer
      ↓
canonical snapshot
      ↓
Memory / SQLite / PostgreSQL
      ↓
assurance · observability · replay · provenance · recovery certification
```

There is one authoritative event/reducer path. Framework adapters and the coming semantic solver extend it instead of creating competing machine truth.

## Release progression

- **v0.29** Thin LangGraph Adapter
- **v0.30** Adapter Conformance Kit
- **v0.31** Hierarchical Decision Scopes
- **v0.32** Runtime/Formal Trace Conformance
- **v0.33** Signed Provenance and Verifiable Exports
- **v0.34** Distributed Recovery Certification
- **v0.35 next** Semantic Problem Model Foundations
- **v0.36** Semantic Compiler SDK

## Install

```bash
pip install aasm-runtime
```

Contributor setup:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'
pytest -q
```

## Documentation

[Why AASM?](WHY_AASM.md) · [Roadmap](ROADMAP.md) · [Architecture](docs/ARCHITECTURE.md) · [Formal Assurance](docs/FORMAL_ASSURANCE.md) · [Operator Runbooks](docs/runbooks/README.md) · [Release Process](docs/RELEASE_PROCESS.md)

## Correctness boundary

AASM can establish machine authority, replayability, digest equality, bounded formal properties, and deterministic failure-recovery outcomes. It does not manufacture domain truth: external measurements, simulations, human reports, and scientific assumptions still require appropriate domain verification.

## License

MIT — see [LICENSE](LICENSE).
