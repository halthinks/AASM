<div align="center">

# AASM

## Algorithmic Agent State Machine

**A durable control system for agents, tools, models, humans, and real work.**

AASM keeps the official state of a job outside the language model. Models may suggest what to do, but the runtime decides what is legal, records what happened, preserves evidence, and recovers from bad assumptions without throwing away unrelated work.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.26.0%20experimental-orange)](ROADMAP.md)

[Run the hero demo](#run-the-research-synthesis-hero-demo) · [Get started](#five-minute-start) · [Why AASM?](WHY_AASM.md) · [Roadmap](ROADMAP.md) · [Download ZIP](https://github.com/halthinks/AASM/archive/refs/heads/main.zip)

</div>

---

## Current release

| Item | Current state |
|---|---|
| **Package/runtime** | **v0.26.0** |
| **Project status** | Experimental |
| **Current adoption milestone** | Research Synthesis Hero Stack |
| **Next release** | **v0.27.0 — One-Command Local Full Stack** |
| **Remote compatibility protocol** | `aasm.remote.v1 / 0.19.0` |

The package/runtime version and remote protocol version are intentionally separate. The current Python package and server runtime are **0.26.0**; existing remote clients continue to negotiate `aasm.remote.v1 / 0.19.0`.

AASM’s immediate program is adoption and operability: reference application → one-command local stack → clean distribution and runbooks → thin framework adapter. See the [formal implementation roadmap](ROADMAP.md).

---

## What problem does AASM solve?

A capable agent can still lose track of what it decided, repeat failed work, hide unfinished requirements, or modify the wrong part of a project after a test fails. A long conversation is not a reliable control system.

AASM gives the work an official machine state.

Imagine an agent is building a service:

1. It chooses PostgreSQL.
2. Tasks that only matter for SQLite are temporarily hidden, but not deleted.
3. An integration test proves that the selected schema is incompatible.
4. AASM records the evidence and the exact decisions responsible for the conflict.
5. It returns to the schema decision instead of randomly editing the latest files.
6. Unrelated work, such as a valid cache implementation, stays intact.
7. The failed combination becomes reusable knowledge, so the same plan is not selected again.

> **Models propose. AASM decides what may become durable state.**

AASM is not a language model. It is the deterministic runtime around models, tools, workers, and people.

---

## Run the Research Synthesis Hero Demo

v0.26.0 includes a complete, offline reference application that demonstrates the core difference directly.

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
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

The fixed synthetic corpus requires **no network access, paid API, or model key**. The run shows:

```text
fixed causal question
→ initial interpretation
→ explicit obligations and evidence
→ validated contradiction
→ certified learned no-good
→ non-chronological backjump
→ preservation of unrelated work
→ mid-run requirement injection
→ conditional lock restoration
→ corrected synthesis
→ claim-level provenance
→ exact full-history replay
```

The output directory contains:

- `final_synthesis.json`
- `run_summary.json`
- `history_check.json`
- `machine_export.json`
- `machine_id.txt`
- `replay_commands.txt`

Use setup mode to inspect the machine before the known contradiction:

```bash
aasm demo \
  --scenario research-synthesis \
  --mode setup \
  --db research-setup.db \
  --output-dir research-setup
```

Read [Why AASM?](WHY_AASM.md) for the reproducible comparison and [Research Synthesis Hero Stack](docs/RESEARCH_SYNTHESIS_DEMO.md) for the exact trajectory and acceptance properties.

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

An obligation is work that must eventually be handled. It cannot silently disappear because the current plan makes it inconvenient.

Examples:

```text
run the compatibility test
collect the missing measurement
resolve contradictory evidence
publish the required artifact
```

A mandatory obligation must be completed, rejected with a reason, superseded, or proven impossible before the machine can complete.

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

A model, heuristic, human, or solver may propose a candidate. Only the AASM kernel can activate it or change durable state.

---

## Five-minute start

AASM requires Python 3.11 or newer.

> **Distribution status:** PyPI publication is scheduled for the operator/distribution milestone. The current supported install path is the repository checkout below; editable installation remains the contributor path.

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m venv .venv
```

Activate the environment and install:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS or Linux
source .venv/bin/activate

pip install -e .
```

Create a small machine:

```python
from aasm import AASMEngine, DecisionRecord, ObligationRecord, ProblemSpec

engine = AASMEngine(ProblemSpec("Prepare a field test"))
engine.register_decision(DecisionRecord("D-site-a", "test_site", "site-a"))
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

The CLI is available after installation:

```bash
aasm --help
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
| Unproductive search | Restart speculative search while retaining knowledge |
| Combination must not recur | Learn a blocking constraint |

### Conditional locks: hidden is not deleted

Work may be irrelevant under the current decision model. AASM can lock it temporarily while retaining the condition that justified the lock. When that condition changes, the lock breaks and the work becomes available again.

### Backjumping: repair the cause, not the latest symptom

When a failure is caused by an earlier choice, AASM can invalidate that choice and its dependent region while preserving later work that does not depend on it.

### Restart: start a new search without forgetting

A restart discards speculative assignments and temporary ordering. It retains evidence, verified artifacts, failed assumptions, learned constraints, and provenance.

### Fairness debt: unfinished work cannot stay hidden forever

AASM tracks how long persistent obligations remain unavailable or locked. Policy can force review, exposure, deferral, or terminal disposition.

### Certificate-gated hard knowledge

Under strict assurance, a learned constraint begins soft. It becomes hard only after an independent verifier confirms that a durable certificate covers the exact current constraint projection.

---

## Canonical adoption surface

AASM has many capabilities, but adopters should not have to guess which path is supported. The machine-readable `aasm.adoption.v1` contract identifies the golden path used by the hero application, Control Center, future runbooks, and framework adapters.

Python:

```python
from aasm import public_api_contract, validate_public_api_contract

contract = public_api_contract()
report = validate_public_api_contract()
assert report["valid"]
```

CLI:

```bash
aasm adoption-contract
```

HTTP:

```text
GET /adoption-contract
```

The contract identifies supported imports, engine methods, CLI commands, inspection surfaces, HTTP endpoints, version identities, and compatibility meanings.

Reference applications must use the existing event/reducer runtime and public authority boundary. A feature that works only by privately mutating snapshots or writing the database directly is not an accepted AASM path.

---

## Major capabilities

| Capability | What it gives you |
|---|---|
| Durable state and replay | Reconstruct a run from events instead of trusting a transcript |
| Legal transitions | Explicit rules for what the machine may do next |
| Plans and checkpoints | Graph-based work, selective revalidation, replay, and forks |
| Authority and effects | Proposal, approval, idempotency, ownership, and reconciliation |
| Conflict learning | Evidence-backed explanations, no-goods, backjumping, and restart |
| Decision backends | Finite-domain, human, callback/model, and portfolio proposal sources |
| Profile packages | Versioned domain meaning outside the kernel |
| Formal assurance | Certificate policy, replay verification, TLA+, and SPIN checks |
| Observability | Decision, Obligation, Evidence, causal graphs, timelines, and fairness debt |
| Distributed work | Workers, leases, heartbeats, quotas, telemetry, and mission controls |

---

## Profiles and packages

Profiles define domain vocabulary, obligations, evidence requirements, fairness, adapters, and migration policy without moving authority out of the kernel.

Built-in profiles now include:

- `aasm.bare`
- `aasm.evolve`
- `aasm.research-synthesis`

The finished research profile lives in [`profiles/research/`](profiles/research/) and is also available programmatically through `research_profile()` and `research_package()`.

Profiles do not silently rewrite themselves. Contract changes require a new version, fingerprint, conformance check, migration, and authorized activation.

See [Profile Packages](docs/PROFILE_PACKAGES.md) and [Extension Contract](docs/EXTENSION_CONTRACT.md).

---

## Assurance and replay verification

`engine.check_durable_history()` replays the authoritative event stream and compares the reconstructed snapshot with persisted state.

The verifier checks, among other things:

- contiguous sequence and unique event identities;
- machine and state continuity;
- legal transitions and terminal behavior;
- exact replay-versus-persistence equality;
- calculus invariants and active locks;
- profile fingerprints;
- unresolved mandatory obligations at completion;
- certificate coverage for active hard constraints.

The repository also runs bounded TLA+ and Promela/SPIN models. These models verify selected control properties; they do not prove every adapter, external service, measurement, or domain claim correct.

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

The causal graph connects decisions, obligations, evidence, locks, conflicts, explanations, constraints, certificates, verifications, and candidate models. The Control Center now renders these structures in human-readable panels.

See [Observability](docs/OBSERVABILITY.md) and [Control Center](docs/CONTROL_CENTER.md).

---

## What AASM does not guarantee

AASM strengthens control, replay, provenance, and machine-level assurance. It does not manufacture truth.

A verified certificate may prove that an artifact or constraint matches what was checked. It does not automatically prove that:

- a scientific model is physically accurate;
- a sensor was calibrated;
- a human report was honest;
- a legal interpretation is correct;
- an external service returned the truth;
- an adapter is safe to execute.

The v0.26 research corpus is explicitly synthetic. Use independent domain validation and appropriate safety controls for consequential systems.

---

## Documentation by audience

| Start here when you are… | Read |
|---|---|
| New to AASM | This README and [Why AASM?](WHY_AASM.md) |
| Running the hero application | [Research Synthesis Demo](docs/RESEARCH_SYNTHESIS_DEMO.md) |
| Evaluating adoption | [Roadmap](ROADMAP.md) and [Architecture](docs/ARCHITECTURE.md) |
| Designing an agent system | [Formal Calculus](docs/FORMAL_CALCULUS.md), [Decision Backends](docs/DECISION_BACKENDS.md), [Durable Runtime](docs/DURABLE_RUNTIME.md) |
| Building a domain package | [Profile Packages](docs/PROFILE_PACKAGES.md), [Extension Contract](docs/EXTENSION_CONTRACT.md) |
| Reviewing correctness | [Formal Assurance](docs/FORMAL_ASSURANCE.md), [`formal/`](formal/), [Replay and Forks](docs/REPLAY_FORK.md) |
| Operating workers or services | [Distributed Workers](docs/DISTRIBUTED_WORKERS.md), [Mission Controls](docs/MISSION_CONTROLS_OBSERVABILITY.md), [Remote Execution](docs/REMOTE_EXECUTION.md) |

Additional documents:

[Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [v0.26 Release](docs/RELEASE_0.26.md) · [Contributing](CONTRIBUTING.md) · [Security](SECURITY.md) · [Support](SUPPORT.md)

---

## Contributing

AASM is an early open-source project. Clear bug reports, adversarial tests, backend implementations, profile packages, formal-model improvements, examples, and documentation corrections are welcome.

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
