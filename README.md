<div align="center">

# AASM
## Algorithmic Agent State Machine

**Durable, replayable control for agents, tools, models, humans, and long-running work.**

AASM keeps the official state of a job outside the language model. Models can propose; AASM decides what is legal, records what happened, preserves evidence, learns from contradictions, and recovers without throwing away unrelated work.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## Current release

### **v0.32.0 — Runtime/Formal Trace Conformance**

| | Current |
|---|---|
| Package/runtime | **0.32.0** |
| Adoption contract | `aasm.adoption.v1 / 0.8.0` |
| Scope contract | `aasm.scopes.v1 / 0.1.0` |
| Trace contract | `aasm.trace.v1 / 0.1.0` |
| Semantic trace contract | `aasm.trace.semantic.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |
| Next release | **v0.33.0 — Signed Provenance and Verifiable Exports** |

v0.32 closes an important assurance gap: a bounded formal model passing is not the same thing as proving that a particular production history followed the modeled rules. AASM can now project the **actual durable event history** into a versioned formal trace, preserve every source event and its digest, explicitly mark unsupported transitions, and attach semantic counterexamples to exact event IDs.

> **No event is silently dropped. No snapshot is treated as invented history. Unsupported semantics remain explicit.**

---

## Try AASM in one command

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
docker compose up --build
```

Open:

```text
http://localhost:8787/
```

The local stack includes PostgreSQL, the AASM runtime, Control Center, a deterministic worker, and bundled reference machines. No model API key is required for the deterministic demonstrations.

Useful commands:

```bash
docker compose run --rm stackctl status
docker compose run --rm stackctl check
docker compose run --rm stackctl verify --selection completed
docker compose down
```

See [`docs/LOCAL_FULL_STACK.md`](docs/LOCAL_FULL_STACK.md).

---

## Install

From the immutable GitHub release:

```bash
pip install \
  https://github.com/halthinks/AASM/releases/download/v0.32.0/aasm_runtime-0.32.0-py3-none-any.whl
```

The PyPI package name is:

```bash
pip install aasm-runtime
```

PyPI publication is gated by the repository's Trusted Publisher configuration. The GitHub release remains the authoritative immutable distribution source when that external binding is not enabled.

Verify an install:

```bash
aasm adoption-contract
aasm runbook history-diagnosis
```

---

# Why AASM exists

A capable agent can still:

- forget an earlier decision;
- repeat a failed approach;
- hide unfinished mandatory work;
- repair the most recent symptom instead of the causal decision;
- report success without required evidence;
- lose useful knowledge during restart;
- duplicate an external effect whose prior outcome is unknown.

A conversation is not a reliable control plane. AASM gives the work an official machine state.

The core rule is simple:

```text
reasoner / model / human / tool
            ↓ proposes
        AASM authority
            ↓ admits
       durable event
            ↓
       pure reducer
            ↓
    canonical snapshot
```

A framework checkpoint, prompt transcript, adapter cache, or UI state does not become competing machine truth.

---

# The three durable structures

## Decisions

Named choices and assumptions:

```text
database = postgres
schema = v2
architecture = event_sourced
```

AASM records what is active, what it depends on, what evidence supports it, and why it changed.

## Obligations

Work that must eventually receive a legal terminal disposition:

```text
run compatibility tests
verify the external effect
resolve contradictory evidence
publish the required artifact
```

Mandatory work cannot quietly disappear because a new plan makes it inconvenient.

## Evidence

Durable provenance for observations, tests, human judgments, simulations, and verification results. AASM records evidence and its authority boundary; it does not manufacture truth.

---

# Conflict learning and causal recovery

When evidence contradicts an active assumption, AASM does not blindly retry the latest step.

```text
D1 choose database
D2 choose schema
D3 implement API
D4 implement cache
D5 build UI
D6 integration test fails
```

If the durable explanation shows that `D2` caused the conflict, AASM can backjump to `D2`, preserve unrelated work, and turn the failed combination into reusable blocking knowledge.

Restart means:

```text
discard speculative assignment
retain verified evidence
retain learned constraints
retain provenance
retain mandatory obligations
```

That is restart without amnesia.

---

# Hierarchical Decision Scopes

v0.31 introduced hierarchical reasoning inside **one** authoritative machine:

```text
root
└── strategy
    ├── architecture-a
    │   └── implementation-a
    └── architecture-b
        └── implementation-b
```

A contradiction in `implementation-a` can invalidate its causal architecture branch while preserving the `architecture-b` subtree. Parent knowledge can be inherited; overrides are explicit; sibling information flow requires a recorded dependency.

```bash
aasm scope-report MACHINE_ID --store runs.db
aasm scope-context MACHINE_ID --store runs.db architecture-a
```

Read [`docs/HIERARCHICAL_DECISION_SCOPES.md`](docs/HIERARCHICAL_DECISION_SCOPES.md).

---

# Runtime/Formal Trace Conformance

v0.32 makes production histories independently inspectable as formal trace evidence.

```python
from aasm import project_trace, semantic_trace_check

projection = project_trace(engine.events)
report = semantic_trace_check(engine.events)
```

Or through the engine:

```python
projection = engine.trace_projection()
semantic = engine.semantic_trace_report()
```

CLI:

```bash
aasm trace-project MACHINE_ID --store runs.db
aasm trace-check MACHINE_ID --store runs.db
```

The trace projection retains for every event:

```text
event ID
source sequence
event type
transition class
support status
SHA-256 of the exact source event
complete source event mapping
```

Unknown future transitions are represented as `UNSUPPORTED`; they are not discarded or guessed into conformance.

Semantic checks use explicit pre/post-state witnesses when available. Missing witnesses produce `INCONCLUSIVE`, not fabricated proof. Violations identify the exact source event and pre/post-state fingerprints.

Read [`docs/TRACE_CONFORMANCE.md`](docs/TRACE_CONFORMANCE.md).

---

# Existing framework adoption

AASM can sit underneath an existing LangGraph application without replacing its graph topology or checkpoint mechanism:

```python
from aasm import LangGraphAdapter

adapter = LangGraphAdapter(namespace="my-app")
graph.add_node("retrieve", adapter.wrap_node("retrieve", retrieve))
```

LangGraph still owns graph execution. AASM owns durable decisions, obligations, evidence, conflicts, external-effect authority, replay, and recovery.

Adapter authors can run:

```bash
aasm adapter-conformance --adapter langgraph
```

The framework-neutral conformance kit returns `PASS`, `FAIL`, or `INCONCLUSIVE` and checks replay, provenance, authority ownership, failure recovery, and direct-storage bypasses.

---

# Operator runbooks

Executable drills convert architectural claims into things an operator can actually do:

```bash
aasm runbook list
aasm runbook lease-loss
aasm runbook requirement-change
aasm runbook learned-no-good
aasm runbook human-approval
aasm runbook replay-fork
aasm runbook unknown-effect
aasm runbook history-diagnosis
```

See [`docs/runbooks/README.md`](docs/runbooks/README.md).

---

# Correctness boundary

AASM strengthens:

- transition legality;
- durable authority;
- replayability;
- provenance;
- conflict learning;
- recovery;
- certificate-gated hard knowledge;
- formal and trace-level assurance.

It does **not** automatically prove that a scientific model is physically correct, a sensor was calibrated, a human report was honest, or an external service told the truth. Domain verification remains explicit.

---

# Release discipline

Every maintained release is built twice under a pinned build toolchain and must produce byte-identical wheel and source distributions. CI clean-installs the wheel, tests the extracted source distribution outside the Git checkout, and verifies the release assets after publication.

A release is not considered complete until the exact commit has:

```text
aasm/ci-summary          success
aasm/formal-assurance    success
aasm/release             success
```

Existing tags are never moved and release assets are never overwritten. Corrections require a new version.

---

# Roadmap

```text
v0.32  Runtime/Formal Trace Conformance        ← current
v0.33  Signed Provenance and Verifiable Exports
v0.34  Distributed Recovery Certification
v0.35  Semantic Problem Model
v0.36  Semantic Compiler SDK
v0.37+ Semantic reasoning, truth maintenance, capabilities, frontier, solver loop
```

See [`ROADMAP.md`](ROADMAP.md) for the full program through v0.45.

---

## Documentation

- [Why AASM?](WHY_AASM.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Compatibility](docs/COMPATIBILITY.md)
- [Formal Assurance](docs/FORMAL_ASSURANCE.md)
- [Trace Conformance](docs/TRACE_CONFORMANCE.md)
- [Release Process](docs/RELEASE_PROCESS.md)
- [Roadmap](ROADMAP.md)
- [Changelog](CHANGELOG.md)

## License

MIT — see [LICENSE](LICENSE).
