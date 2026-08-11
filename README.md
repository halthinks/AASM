<div align="center">

# AASM

## Algorithmic Agent State Machine

**A durable control system for agents, tools, models, humans, and real work.**

AASM keeps the official state of a job outside the language model. Models can propose what to do; the runtime decides what is legal, records what happened, preserves evidence, and recovers from bad assumptions without discarding unrelated work.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.27.0%20experimental-orange)](ROADMAP.md)

[Run the full stack](#one-command-start) · [Why AASM?](WHY_AASM.md) · [Roadmap](ROADMAP.md) · [Local stack guide](docs/LOCAL_FULL_STACK.md) · [Download ZIP](https://github.com/halthinks/AASM/archive/refs/heads/main.zip)

</div>

---

## Current release

| Item | Current state |
|---|---|
| **Package/runtime** | **v0.27.0** |
| **Project status** | Experimental |
| **Current milestone** | **One-Command Local Full Stack** |
| **Included hero application** | Research Synthesis Hero Stack |
| **Next release** | **v0.28.0 — Distribution and Operator Readiness** |
| **Remote compatibility protocol** | `aasm.remote.v1 / 0.19.0` |

The package/runtime version and remote protocol version are intentionally separate. The current Python package and server runtime are **0.27.0**; existing remote clients continue to use `aasm.remote.v1 / 0.19.0`.

---

# One-command start

The fastest way to understand AASM is to run the complete local stack:

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
docker compose up --build
```

Open:

```text
http://localhost:8787/
```

The Control Center automatically loads a live, partially progressed research-synthesis machine. You can switch to the completed reference trajectory with one button.

The stack starts:

```text
PostgreSQL 17
AASM HTTP runtime
existing Control Center
one deterministic remote worker
one optional second worker
live setup reference machine
completed reference machine
```

It requires **no model key, paid API, external literature service, or host PostgreSQL installation**.

### Useful stack commands

```bash
# Show machines, workers, and leases
docker compose run --rm stackctl status

# Create a new live setup machine without deleting old history
docker compose run --rm stackctl fresh

# Create and select a new completed reference run
docker compose run --rm stackctl complete

# Verify durable history and exact replay
docker compose run --rm stackctl verify --selection completed

# Run the complete readiness check
docker compose run --rm stackctl check

# Add the optional second worker
docker compose --profile two-workers up -d worker-2

# Stop while preserving PostgreSQL data
docker compose down
```

See [One-Command Local Full Stack](docs/LOCAL_FULL_STACK.md) for reset behavior, port changes, logs, security, and troubleshooting.

---

## What problem does AASM solve?

A capable agent can still:

- forget an earlier decision;
- repeat a failed approach;
- hide an unfinished requirement;
- modify the latest file instead of the actual cause of a failure;
- report success without the required evidence;
- lose its useful knowledge when restarted.

A long conversation is not a reliable control system. AASM gives the work an official machine state.

Imagine an agent building a service:

1. It chooses PostgreSQL.
2. Work that matters only for SQLite becomes conditionally hidden, not deleted.
3. An integration test proves that the selected schema is incompatible.
4. AASM records the test evidence and the decisions responsible for the conflict.
5. It returns to the schema decision rather than randomly editing the latest files.
6. Unrelated valid work remains intact.
7. The failed combination becomes reusable knowledge and cannot silently recur.

> **Models propose. AASM decides what may become durable state.**

AASM is not a language model. It is the deterministic runtime around models, tools, workers, and people.

---

## The three things to remember

### Decisions

A decision is a named choice or assumption:

```text
database = postgres
schema = v2
synthesis.causal_model = retrieval_only
```

AASM records which decisions are active, what they depend on, why they changed, and which work they authorize.

### Obligations

An obligation is work that must eventually be handled:

```text
run the compatibility test
collect the missing measurement
resolve contradictory evidence
publish the required artifact
```

An obligation cannot disappear because the current plan makes it inconvenient. It must be completed, rejected with a reason, superseded, or proven impossible.

### Evidence

Evidence is the durable reason AASM accepts or rejects something. It can come from tests, tools, humans, simulations, sensors, or external systems.

AASM records provenance and relationships. It does not pretend that every evidence source is automatically true.

---

## How a run works

```text
Goal
  ↓
Complete candidate decisions are proposed
  ↓
AASM checks authority, dependencies, constraints, and fairness
  ↓
One candidate model is activated atomically
  ↓
Authorized work runs through workers, tools, or humans
  ↓
Evidence is recorded
  ↓
Success is committed, or a conflict is explained
  ↓
Repair, causal backjump, investigation, or restart
```

Proposal and authority are separate. A model, solver, heuristic, or human may propose a plan. Only the AASM kernel can change durable machine state.

---

# Run the Research Synthesis Hero Demo

The v0.26 hero application remains available independently of Docker:

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS or Linux
source .venv/bin/activate

pip install -e .

aasm demo \
  --scenario research-synthesis \
  --mode complete \
  --db research-demo.db \
  --output-dir research-output
```

The fixed synthetic corpus demonstrates:

```text
fixed causal question
→ initial interpretation
→ explicit obligations and evidence
→ validated contradiction
→ certified learned no-good
→ non-chronological backjump
→ unrelated work preserved
→ mid-run requirement injection
→ conditional lock restoration
→ corrected synthesis
→ claim-level provenance
→ exact full-history replay
```

Generated files include:

- `final_synthesis.json`;
- `run_summary.json`;
- `history_check.json`;
- `machine_export.json`;
- `machine_id.txt`;
- `replay_commands.txt`.

Read [Why AASM?](WHY_AASM.md) for the reproducible baseline comparison and [Research Synthesis Hero Stack](docs/RESEARCH_SYNTHESIS_DEMO.md) for the exact trajectory.

---

## Python start

AASM requires Python 3.11 or newer.

> PyPI publication is scheduled for v0.28.0. The current supported user path is the repository checkout; editable installation is also the contributor path.

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m venv .venv
pip install -e .
```

Create a small machine:

```python
from aasm import AASMEngine, DecisionRecord, ObligationRecord, ProblemSpec

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
engine = AASMEngine(ProblemSpec("Run a durable investigation"), store=store)
print(engine.snapshot.machine_id)
```

---

## What happens when a plan is wrong?

AASM does not reduce every failure to `FAILED`.

| Situation | AASM response |
|---|---|
| Temporary tool error | Retry or repair under policy |
| Missing information | Create or expose an obligation |
| Contradicted assumption | Record a conflict and explanation |
| Bad earlier decision | Backjump to the causal decision |
| Unproductive search | Restart speculation while retaining knowledge |
| Failed combination must not recur | Learn a blocking constraint |

### Conditional locks: hidden is not deleted

Work can be irrelevant under the current decision model. AASM may lock it temporarily, but the lock records the assumption that made it irrelevant. When that assumption changes, the lock breaks and the work becomes visible again.

### Backjumping: repair the cause, not the latest symptom

A failure observed after six later tasks may have been caused by the second design decision. AASM can return to that decision and preserve later work that does not depend on it.

### Restart: search again without forgetting

A restart discards speculative assignments and temporary ordering while retaining evidence, verified artifacts, failed assumptions, learned constraints, and provenance.

### Fairness debt: unfinished work cannot stay hidden forever

AASM tracks how long persistent obligations remain unavailable or locked. Policy can force review, exposure, bounded deferral, or terminal disposition.

### Certificate-gated hard knowledge

Under strict assurance, a learned constraint starts soft. It becomes hard only after a durable certificate independently verifies the exact current projection.

---

## Major capabilities

| Capability | What it provides |
|---|---|
| Durable state and replay | Reconstruct a run from events instead of trusting a transcript |
| Legal transitions | Explicit rules for what the machine may do next |
| Plans and checkpoints | Graph-based work, selective revalidation, and historical forks |
| Authority and effects | Approval, idempotency, execution ownership, and unknown-outcome reconciliation |
| Conflict learning | Explanations, learned constraints, causal backjumping, and restart |
| Decision backends | Finite-domain, human, callback/model, and portfolio proposal sources |
| Profile packages | Versioned domain meaning outside the kernel |
| Formal assurance | Certificates, replay verification, bounded TLA+, and SPIN |
| Observability | Decision, Obligation, Evidence, and causal graphs plus timelines and fairness debt |
| Distributed work | Workers, leases, heartbeats, quotas, telemetry, and mission controls |
| One-command operation | PostgreSQL, runtime, worker, reference machines, and browser UI through Compose |

---

## Canonical adoption surface

AASM has many capabilities, but adopters should not have to guess which path is supported.

Inspect the machine-readable contract from Python:

```python
from aasm import public_api_contract, validate_public_api_contract

contract = public_api_contract()
report = validate_public_api_contract()
assert report["valid"]
```

From the CLI:

```bash
aasm adoption-contract
```

From HTTP:

```text
GET /adoption-contract
```

The contract identifies:

- supported top-level imports;
- supported `AASMEngine` methods;
- supported CLI commands and inspection surfaces;
- supported HTTP endpoints;
- the research reference application;
- the one-command local stack;
- package/runtime and remote-protocol identity;
- what `SUPPORTED`, `EXPERIMENTAL`, and `INTERNAL` mean before 1.0.

Reference applications, Control Center additions, worker services, runbooks, and external adapters must use this path. A feature that works only by mutating snapshots privately or writing AASM tables directly is not an accepted adoption path.

---

## Architecture

```text
Applications, models, solvers, humans, and framework adapters
                         ↓
                 Public AASM operations
                         ↓
              Deterministic authority boundary
                         ↓
             Existing event / pure reducer path
                         ↓
        Memory, SQLite, or PostgreSQL persistence
                         ↓
 calculus · assurance · replay · effects · workers · observability
```

The Docker stack changes process topology, not machine authority.

The default Compose worker uses the existing path:

```text
register worker
→ heartbeat
→ claim-next
→ durable lease
→ execute deterministic task
→ telemetry
→ complete lease
```

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

The Control Center renders these structures alongside mission controls, effects, workers, leases, telemetry, artifacts, and forks.

---

## What AASM does not guarantee

AASM strengthens control, replay, provenance, and machine-level assurance. It does not manufacture truth.

A verified certificate can prove that a particular artifact or constraint matches what was checked. It does not automatically prove that:

- a scientific model is physically accurate;
- a sensor was calibrated;
- a human report was honest;
- a legal interpretation is correct;
- an external service returned the truth;
- an adapter is safe to execute.

AASM is experimental software. Consequential systems still require independent domain validation, deployment hardening, and appropriate safety controls.

---

## Documentation by audience

| Start here when you are… | Read |
|---|---|
| Trying AASM locally | [One-Command Local Full Stack](docs/LOCAL_FULL_STACK.md) |
| New to the ideas | This README and [Why AASM?](WHY_AASM.md) |
| Evaluating the hero application | [Research Synthesis Demo](docs/RESEARCH_SYNTHESIS_DEMO.md) |
| Evaluating adoption | [Roadmap](ROADMAP.md) and [Architecture](docs/ARCHITECTURE.md) |
| Designing an agent system | [Formal Calculus](docs/FORMAL_CALCULUS.md), [Decision Backends](docs/DECISION_BACKENDS.md), [Durable Runtime](docs/DURABLE_RUNTIME.md) |
| Building a domain package | [Profile Packages](docs/PROFILE_PACKAGES.md), [Extension Contract](docs/EXTENSION_CONTRACT.md) |
| Reviewing correctness | [Formal Assurance](docs/FORMAL_ASSURANCE.md), [`formal/`](formal/), [Replay and Forks](docs/REPLAY_FORK.md) |
| Operating distributed work | [Distributed Workers](docs/DISTRIBUTED_WORKERS.md), [Mission Controls](docs/MISSION_CONTROLS_OBSERVABILITY.md), [Remote Execution](docs/REMOTE_EXECUTION.md) |

Additional project documents:

[Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Support](SUPPORT.md)

---

## Contributing

AASM is an early open-source project. Clear bug reports, adversarial tests, backend implementations, profile packages, formal-model improvements, examples, and documentation corrections are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
