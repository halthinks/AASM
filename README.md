<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, models, humans, and real work.**

AASM keeps machine truth outside the model. Models and compilers may propose structures; deterministic AASM validation decides what may become durable.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## Current release — v0.36.0

**Semantic Compiler SDK**

| Identity | Value |
|---|---|
| Package/runtime | `aasm-runtime 0.36.0` |
| Adoption contract | `aasm.adoption.v1 / 0.12.0` |
| Semantic problem | `aasm.semantic.problem.v1 / 0.1.0` |
| Semantic source | `aasm.semantic.source.v1 / 0.1.0` |
| Semantic compiler | `aasm.semantic.compiler.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |
| Next release | **v0.37.0 — Reasoning Artifacts and Semantic Dependency Graph** |

v0.36 turns the semantic problem model into a deterministic compiler pipeline:

```text
PARSE → RESOLVE → NORMALIZE → TYPE_CHECK → VALIDATE → FINGERPRINT → INSTANTIATE
```

A compiler is **proposal-only**. It cannot write AASM tables, snapshots, or durable truth. `compile-and-admit` first produces and validates a `ProblemInstance`, then calls the ordinary v0.35 semantic admission method, which records the accepted problem as Evidence through the existing event/reducer/store path.

### Compiler outputs

`CompileResult` exposes:

- `status`;
- `problem_instance | None`;
- `missing_inputs[]`;
- `missing_capabilities[]`;
- source-mapped warnings and hard errors;
- deterministic audit trail;
- content-addressed cache key;
- compiler-result fingerprint.

Diagnostics include JSON pointer, source name, line, column, UTF-8 byte offset, stage, severity, and issue code. Missing capabilities and missing inputs remain explicit; they are never guessed away.

### Determinism and cache

The cache key is derived from the compiler declaration, canonical normalized source, environment snapshot, and compilation policy. The reference compiler rejects a collision in which one key would map to a different result. When `instance_id` is omitted it is deterministically derived from normalized inputs, domain/model fingerprints, and compiler identity.

```bash
aasm semantic-compiler-contract

aasm semantic-compile problem.json --environment environment.json --output compile-result.json

aasm problem-check problem.json --environment environment.json

aasm semantic-compiler-conformance

aasm semantic-compile-admit MACHINE_ID --store runs.db \
  --source problem.json --environment environment.json
```

The compatibility aliases `aasm compile` and `aasm problem-check` exercise the same deterministic implementation.

## Why AASM exists

A conversational agent can forget decisions, retry disproven approaches, hide unfinished requirements, or modify the newest symptom instead of the causal assumption. AASM turns long-running work into a replayable state machine with durable Decisions, Obligations, Evidence, conflicts, learned constraints, causal backjumping, fairness, effects, leases, replay, provenance, and formal checks.

## Architecture

```text
problem source
     ↓
proposal-only compiler
     ↓
deterministic validation
     ↓
ProblemInstance candidate
     ↓
AASM admission
     ↓
durable event → production reducer → canonical snapshot → Memory / SQLite / PostgreSQL
```

No compiler-owned database, scheduler, event log, or authority path exists.

## Release progression

- **v0.29** Thin LangGraph Adapter
- **v0.30** Adapter Conformance Kit
- **v0.31** Hierarchical Decision Scopes
- **v0.32** Runtime/Formal Trace Conformance
- **v0.33** Signed Provenance and Verifiable Exports
- **v0.34** Distributed Recovery Certification
- **v0.35** Semantic Problem Model Foundations
- **v0.36** Semantic Compiler SDK
- **v0.37 next** Reasoning Artifacts and Semantic Dependency Graph

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

The compiler guarantees deterministic structure, diagnostics, fingerprints, cache behavior, and admission routing for the supported source contract. It does not make a scientific premise, external measurement, or model-generated candidate true.

## License

MIT — see [LICENSE](LICENSE).
