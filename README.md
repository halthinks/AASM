<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, models, humans, and real work.**

Models can propose. AASM owns what becomes durable: decisions, obligations, evidence, conflicts, effects, leases, replay, recovery, and now a domain-neutral semantic problem definition.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## Current release — v0.35.0

**Semantic Problem Model Foundations**

| Identity | Value |
|---|---|
| Package/runtime | `aasm-runtime 0.35.0` |
| Adoption contract | `aasm.adoption.v1 / 0.11.0` |
| Semantic problem | `aasm.semantic.problem.v1 / 0.1.0` |
| Domain package | `aasm.domain.v1 / 0.1.0` |
| Problem instance | `aasm.problem.v1 / 0.1.0` |
| Recovery | `aasm.recovery.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |
| Next release | **v0.36.0 — Semantic Compiler SDK** |

### What changed

AASM can now carry an explicit semantic problem instead of asking an agent to infer the problem repeatedly from a transcript. The semantic layer is reusable across domains and remains subordinate to the existing AASM authority path.

```text
ProblemDefinition
      ↓
ProblemModel + DomainPackage
      ↓
ProblemInstance
      ↓
validation + deterministic fingerprints
      ↓
ordinary AASM Evidence event
      ↓
production reducer / canonical snapshot / replay
```

The core objects are `DomainPackage`, `ProblemDefinition`, `ProblemModel`, `ProblemInstance`, `Entity`, `Predicate`, `Objective`, `Operator`, `Observer`, and `Verifier`. They use canonical JSON and deterministic SHA-256 fingerprints. Validation catches duplicate IDs, missing predicate references, invalid decision domains, missing required model pieces, package/model fingerprint mismatches, and hard compile-time contradictions.

A malformed or contradictory problem is rejected before admission. A structurally valid problem whose capabilities are not yet bound remains visible as `BLOCKED_MISSING_CAPABILITIES` instead of being silently treated as executable.

```bash
aasm semantic-problem-contract

aasm problem-admit MACHINE_ID --store runs.db --input problem.json

aasm problem MACHINE_ID --store runs.db
aasm domain MACHINE_ID --store runs.db
```

Because admission is ordinary evidence, Memory, SQLite, PostgreSQL, replay, provenance export, and existing observability continue to use the same authoritative runtime.

## Why AASM exists

A conversational agent can forget decisions, retry disproven approaches, hide unfinished requirements, or modify the newest symptom instead of the causal assumption. AASM turns that work into an explicit state machine with durable Decisions, Obligations, Evidence, conflicts, learned no-goods, causal backjumping, fairness, effects, leases, replay, and formal checks.

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
assurance · replay · provenance · semantic projections
```

There is still one authoritative event/reducer path. The semantic layer does not own a private database or a second scheduler.

## Release progression

- **v0.29** Thin LangGraph Adapter
- **v0.30** Adapter Conformance Kit
- **v0.31** Hierarchical Decision Scopes
- **v0.32** Runtime/Formal Trace Conformance
- **v0.33** Signed Provenance and Verifiable Exports
- **v0.34** Distributed Recovery Certification
- **v0.35** Semantic Problem Model Foundations
- **v0.36 next** Semantic Compiler SDK

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

AASM can validate structural semantics, identities, referential integrity, fingerprints, event-sourced admission, replay, and machine authority. It does not make a domain premise true merely because the premise is well formed.

## License

MIT — see [LICENSE](LICENSE).
