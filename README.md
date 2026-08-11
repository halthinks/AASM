<div align="center">

# AASM

## Algorithmic Agent State Machine

**A durable control system for agents, tools, models, humans, and real work.**

AASM keeps the official state of a job outside the language model. Models may suggest what to do, but the runtime decides what is legal, records what happened, preserves evidence, and recovers from bad assumptions without throwing away unrelated work.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.25.2%20experimental-orange)](ROADMAP.md)

[Get started](#five-minute-start) · [Adoption contract](#canonical-adoption-surface) · [Roadmap](ROADMAP.md) · [Download ZIP](https://github.com/halthinks/AASM/archive/refs/heads/main.zip) · [Examples](examples/)

</div>

---

## Current release and adoption program

| Item | Current state |
|---|---|
| **Package/runtime** | **v0.25.2** |
| **Project status** | Experimental |
| **Completed adoption step** | Canonical supported API and implementation contract |
| **Next release** | **v0.26.0 — Research Synthesis Hero Stack** |
| **Remote compatibility protocol** | `aasm.remote.v1 / 0.19.0` |

The immediate roadmap is no longer “add another architecture layer.” It is to make the existing runtime visible, runnable, distributable, and operable: reference application → one-command local stack → clean distribution and runbooks → thin framework adapter.

See the [formal release-by-release implementation plan](ROADMAP.md).

---

## What problem does AASM solve?

A capable agent can still lose track of what it decided, repeat failed work, hide unfinished requirements, or modify the wrong part of a project after a test fails. A long conversation is not a reliable control system.

AASM gives the work an official machine state.

Imagine an agent is building a service:

1. It chooses PostgreSQL.
2. Tasks that only matter for SQLite are temporarily hidden, but not deleted.
3. An integration test proves that the selected schema is incompatible.
4. AASM records the evidence and the exact decisions responsible for the conflict.
5. It returns to the schema decision instead of randomly editing the most recent files.
6. Unrelated work, such as a valid cache implementation, stays intact.
7. The failed combination becomes reusable knowledge, so the same plan is not selected again.

That is the core idea:

> **Models propose. AASM decides what may become durable state.**

AASM is not a language model and it does not replace one. It is the deterministic runtime around models, tools, workers, and people.

---

## The three things to remember

### Decisions

A decision is a named choice or assumption, such as:

```text
database = postgres
schema = v2
inspection_method = thermal_camera
```

AASM records which decisions are active, what they depend on, why they changed, and which work they authorize.

### Obligations

An obligation is work that must eventually be handled. It cannot quietly disappear because the current plan makes it inconvenient.

Examples include:

```text
run the compatibility test
collect the missing measurement
review the safety evidence
publish the required artifact
```

An obligation must be completed, rejected with a reason, superseded, or proven impossible.

### Evidence

Evidence is the durable reason AASM accepts or rejects something. It can come from tests, tools, humans, simulations, sensors, or external systems.

AASM records provenance and relationships. It does not pretend that every piece of evidence is automatically true.

---

## How a run works

```text
Goal
  ↓
Candidate decisions are proposed
  ↓
AASM checks authority, dependencies, constraints, and fairness
  ↓
One complete candidate is activated atomically
  ↓
Authorized work runs
  ↓
Evidence is collected
  ↓
Success is committed, or a conflict is explained
  ↓
Repair, causal backjump, or restart
```

The important boundary is that proposal and authority are separate. A model, heuristic, human, or solver may propose a candidate. Only the AASM kernel can activate it or change durable state.

---

## Five-minute start

AASM requires Python 3.11 or newer.

> **Distribution status:** PyPI publication is an adoption-roadmap deliverable. The current supported install path is the repository checkout below; editable installation remains the contributor path.

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS or Linux
source .venv/bin/activate
```

Install the package:

```bash
pip install -e .
```

Create a small machine:

```python
from aasm import (
    AASMEngine,
    DecisionRecord,
    ObligationRecord,
    ProblemSpec,
)

engine = AASMEngine(ProblemSpec("Prepare a field test"))

engine.register_decision(
    DecisionRecord("D-site-a", "test_site", "site-a")
)
engine.activate_decision("D-site-a")

engine.register_obligation(
    ObligationRecord(
        "O-weather",
        "Confirm that weather conditions are safe",
        decision_dependencies=["D-site-a"],
    )
)

print(engine.inspect_machine("summary"))
```

For durable local storage:

```python
from aasm import AASMEngine, ProblemSpec, SQLiteStore

store = SQLiteStore("aasm-runs.db")
engine = AASMEngine(
    ProblemSpec("Run a durable investigation"),
    store=store,
)
print(engine.snapshot.machine_id)
```

The CLI is available after installation:

```bash
aasm --help
```

---

## Canonical adoption surface

AASM has many capabilities, but adopters should not have to guess which path is supported. v0.25.2 defines one machine-readable golden path over the existing runtime—without adding a wrapper runtime, second reducer, duplicate store, or alternate authority mechanism.

Inspect it from Python:

```python
from aasm import public_api_contract, validate_public_api_contract

contract = public_api_contract()
report = validate_public_api_contract()
assert report["valid"]
```

Inspect it from the CLI:

```bash
aasm adoption-contract
```

Or from the HTTP runtime:

```text
GET /adoption-contract
```

The contract identifies:

- supported top-level imports;
- supported `AASMEngine` methods;
- supported CLI commands;
- supported inspection surfaces;
- supported HTTP endpoints;
- package/runtime and remote-protocol identity;
- what `SUPPORTED`, `EXPERIMENTAL`, and `INTERNAL` mean before 1.0.

Reference applications, Control Center additions, runbooks, and framework adapters must use this path. A feature that works only by mutating snapshots privately, writing the database directly, or running a parallel orchestration loop is not an accepted AASM adoption path.

See [Architecture: Canonical adoption surface](docs/ARCHITECTURE.md#8-canonical-adoption-surface).

---

## What happens when a plan is wrong?

AASM does not reduce every failure to `FAILED`.

It can distinguish among:

| Situation | AASM response |
|---|---|
| A temporary tool error | Retry or repair under policy |
| Missing information | Create or expose an obligation |
| A contradicted assumption | Record a conflict and explanation |
| A bad earlier decision | Backjump to the causal decision |
| Search has become unproductive | Restart speculative search while keeping learned knowledge |
| A combination must never recur | Learn a blocking constraint |

A conflict is connected to evidence and to the decisions that caused it. AASM can therefore return to the relevant earlier choice instead of undoing everything that happened afterward.

---

## Advanced ideas, in plain English

### Conditional locks: hidden is not deleted

Work can be irrelevant under the current decision model. AASM may lock it temporarily, but the lock records the assumption that made it irrelevant.

When that assumption changes, the lock breaks and the work becomes visible again.

### Backjumping: repair the cause, not the latest symptom

Suppose a test fails after six later tasks have been completed, but the real cause is the second design decision. AASM can return directly to that decision and preserve later work that does not depend on it.

### Restart: start a new search without forgetting

A restart discards speculative assignments and temporary ordering. It retains evidence, verified artifacts, failed assumptions, learned constraints, and provenance.

### Fairness debt: unfinished work cannot stay hidden forever

AASM tracks how long persistent obligations remain unavailable or locked. Policy can force review, exposure, deferral, or a terminal disposition.

### Certificate-gated hard knowledge

A learned constraint starts soft when strict assurance is enabled. It becomes hard only after a durable certificate is independently verified against the exact current constraint projection.

Changing the constraint body, guard, provenance, scope, or intended strength breaks that coverage.

---

## Major capabilities

| Capability | What it gives you |
|---|---|
| Durable state and replay | Reconstruct a run from its event history instead of trusting a transcript |
| Legal transitions | Explicit rules for what the machine may do next |
| Plans and checkpoints | Graph-based work, selective revalidation, replay, and historical forks |
| Authority and effects | Proposal, approval, idempotency, execution ownership, and reconciliation for external actions |
| Conflict learning | Evidence-backed explanations, blocking constraints, backjumping, and restart |
| Decision backends | Finite-domain, human, callback/model, and portfolio proposal sources |
| Profile packages | Versioned domain meaning outside the kernel |
| Formal assurance | Certificate policy, replay verification, conflict-core minimization, bounded TLA+, and SPIN checks |
| Observability | Closed Decision, Obligation, Evidence, and causal graphs plus timelines and fairness debt |
| Distributed work | Workers, leases, heartbeats, quotas, telemetry, and mission controls |

---

## Decision backends

A decision backend proposes complete candidate assignments. Built-in reference backends include:

- `FiniteDomainDecisionBackend` for deterministic, paginated finite search;
- `HumanDecisionBackend` for structured human input;
- `CallbackDecisionBackend` for models, heuristics, or external systems;
- `PortfolioDecisionBackend` for combining several sources while preserving provenance.

Budgets can limit candidates, combinations, declared cost, and latency. Candidate activation is all-or-nothing: AASM stages the entire model, checks it, and commits it once.

A callback timeout limits how long the caller waits. It is **not** a security sandbox. Run untrusted callback code in a separate process or isolation boundary.

See [Decision Backends](docs/DECISION_BACKENDS.md).

---

## Profiles and packages

AASM keeps use-case meaning outside the core runtime.

A profile can define:

- the decisions meaningful to a domain;
- persistent obligations;
- evidence requirements;
- fairness policy;
- adapters and validation contracts;
- migration rules between profile versions.

This lets the same kernel govern software work, investigations, laboratory procedures, operations, field studies, robotics workflows, or other structured activity without hard-coding one ontology.

Profiles do not silently rewrite themselves. A contract change requires a new version, a new fingerprint, conformance checks, an explicit migration, and authorized activation.

See [Profile Packages](docs/PROFILE_PACKAGES.md) and the [Extension Contract](docs/EXTENSION_CONTRACT.md).

---

## Assurance and replay verification

`engine.check_durable_history()` replays the authoritative event stream and compares the reconstructed snapshot with persisted state.

The verifier checks, among other things:

- contiguous event sequence and unique event identities;
- machine and state continuity;
- legal transitions and terminal-state behavior;
- exact replay-versus-persistence equality;
- calculus invariants and active locks;
- profile fingerprints;
- unresolved mandatory obligations at completion;
- certificate coverage for active hard constraints.

The repository also runs bounded TLA+ and Promela/SPIN models. Those models check selected control properties such as staged certification, atomic candidate activation, restart preservation, safe completion, and bounded fairness. They are useful formal evidence, but they are not a proof that every adapter, external service, measurement, or domain model is correct.

See [Formal Assurance](docs/FORMAL_ASSURANCE.md) and [`formal/`](formal/).

---

## Inspecting a machine

```python
engine.inspect_machine("summary")
engine.inspect_machine("decisions")
engine.inspect_machine("obligations")
engine.inspect_machine("evidence")
engine.inspect_machine("causal")
engine.inspect_machine("conflicts")
engine.inspect_machine("fairness")
engine.inspect_machine("packages")
engine.inspect_machine("candidates")
engine.inspect_machine("assurance")
```

The causal graph connects decisions, obligations, evidence, locks, conflicts, explanations, constraints, certificates, verifications, and candidate models. Every edge endpoint is represented in the graph, so consumers do not receive dangling references.

See [Observability](docs/OBSERVABILITY.md).

---

## Where AASM fits

AASM is useful when the work matters enough that “the model probably remembers” is not an acceptable control strategy.

Common fits include:

- long-running coding or infrastructure agents;
- multi-agent planning and execution;
- experiments and research procedures;
- operations and incident response;
- controlled external effects;
- human-in-the-loop workflows;
- replayable investigations;
- domain systems that need explicit obligations, evidence, and recovery.

AASM does not require one model provider, one agent role layout, SAT/SMT, Planner/Builder/Verifier, source-code repositories, or a particular user interface.

---

## What AASM does not guarantee

AASM strengthens control, replay, provenance, and machine-level assurance. It does not manufacture truth.

A verified certificate may prove that a particular artifact or constraint matches what was checked. It does not automatically prove that:

- a scientific model is physically accurate;
- a sensor was calibrated;
- a human report was honest;
- a legal interpretation is correct;
- an external service returned the truth;
- an adapter is safe to execute.

AASM is experimental software. Use independent domain validation and appropriate safety controls for consequential systems.

---

## Runtime and protocol versions

The Python package and current runtime are **v0.25.2**.

The remote server still reports the stable compatibility protocol as:

```text
aasm.remote.v1 / 0.19.0
```

That protocol number is intentionally separate from the package/runtime release number.

The next planned runtime release is **v0.26.0 — Research Synthesis Hero Stack**. See the [Roadmap](ROADMAP.md) for its exact work packages and exit gate.

---

## Documentation by audience

| Start here when you are… | Read |
|---|---|
| New to AASM | This README, [Use Cases](docs/USE_CASES.md), and the examples |
| Evaluating adoption | [Roadmap](ROADMAP.md) and [Architecture](docs/ARCHITECTURE.md) |
| Designing an agent system | [Formal Calculus](docs/FORMAL_CALCULUS.md), [Decision Backends](docs/DECISION_BACKENDS.md), [Durable Runtime](docs/DURABLE_RUNTIME.md) |
| Building a domain package | [Profile Packages](docs/PROFILE_PACKAGES.md), [Extension Contract](docs/EXTENSION_CONTRACT.md) |
| Reviewing correctness | [Formal Assurance](docs/FORMAL_ASSURANCE.md), [`formal/`](formal/), [Replay and Forks](docs/REPLAY_FORK.md) |
| Operating workers or services | [Distributed Workers](docs/DISTRIBUTED_WORKERS.md), [Mission Controls](docs/MISSION_CONTROLS_OBSERVABILITY.md), [Remote Execution](docs/REMOTE_EXECUTION.md) |
| Integrating external actions | [Effect System](docs/EFFECT_SYSTEM.md), [Provider Adapters](docs/PROVIDER_ADAPTERS_ARTIFACTS_CONTROLS.md) |

Additional project documents:

[Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Support](SUPPORT.md)

---

## Contributing

AASM is an early open-source project. Clear bug reports, adversarial tests, backend implementations, profile packages, formal-model improvements, examples, and documentation corrections are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
