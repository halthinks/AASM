<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, models, humans, and real work.**

AASM keeps the official state of a long-running job outside the language model. Models propose; AASM decides what may become durable, records why, preserves evidence, and recovers from bad assumptions without throwing away unrelated work.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## Current release — v0.33.0

**Signed Provenance and Verifiable Exports**

| Identity | Value |
|---|---|
| Package/runtime | `aasm-runtime 0.33.0` |
| Adoption contract | `aasm.adoption.v1 / 0.9.0` |
| Trace contract | `aasm.trace.v1 / 0.1.0` |
| Provenance contract | `aasm.provenance.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |
| Next release | **v0.34.0 — Distributed Recovery Certification** |

v0.33 lets a completed AASM run leave the server as a portable package that can be checked offline. The package contains canonical event, snapshot, trace, and semantic-trace files; a content-addressed manifest; and a detached HMAC-SHA256 signature envelope. A verifier checks the signer identity, manifest signature, byte sizes, and SHA-256 of every covered file. Selective-disclosure exports carry the parent-manifest digest so lineage remains explicit.

```bash
# Start the complete local stack
git clone https://github.com/halthinks/AASM.git
cd AASM
docker compose up --build

# Inspect the supported API
aasm adoption-contract

# Export one persisted machine
aasm provenance-export MACHINE_ID --store runs.db \
  --output verified-run --key-file signer.key --signer-id operator-1

# Verify without the original AASM database
aasm provenance-verify verified-run --key-file signer.key --signer-id operator-1

# Produce a signed disclosure containing only selected covered files
aasm provenance-select verified-run --output disclosure \
  --include trace.json --include semantic-trace.json --key-file signer.key
```

## Why AASM exists

A conversational agent can forget decisions, retry disproven approaches, hide unfinished requirements, or modify the newest symptom instead of the causal assumption. AASM turns that work into an explicit state machine with durable Decisions, Obligations, Evidence, conflicts, learned no-goods, causal backjumping, fairness, effects, leases, replay, and formal checks.

A failed branch is not merely `FAILED`. AASM can retain exactly which assumptions authorized it, what evidence contradicted it, what unrelated work remains valid, and where execution should reconsider.

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
assurance · observability · replay · exports
```

There is one authoritative event/reducer path. Framework adapters, reference applications, formal projection, provenance exports, and future semantic solving extend that path rather than creating competing machine truth.

## Major milestones

- **v0.29** — thin LangGraph adoption without replacing LangGraph.
- **v0.30** — framework-neutral adapter conformance.
- **v0.31** — hierarchical decision scopes with causal cross-scope recovery.
- **v0.32** — lossless runtime/formal trace conformance.
- **v0.33** — signed, content-addressed, offline-verifiable run exports.
- **v0.34 next** — distributed recovery certification.
- **v0.35+** — domain-neutral semantic solver program.

## Documentation

- [Why AASM?](WHY_AASM.md)
- [Roadmap](ROADMAP.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Formal Assurance](docs/FORMAL_ASSURANCE.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [Release Process](docs/RELEASE_PROCESS.md)
- [Operator Runbooks](docs/runbooks/README.md)

## Install

```bash
pip install aasm-runtime
```

For contributors:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'
pytest -q
```

## Correctness boundary

AASM can prove that a covered artifact matches a digest, that an event history replays under the production reducer, or that a declared bounded formal property holds. It does not manufacture domain truth: external measurements, simulations, human reports, and scientific assumptions still require appropriate domain verification.

## License

MIT — see [LICENSE](LICENSE).
