<div align="center">

# AASM
## Algorithmic Agent State Machine

**A deterministic orchestration runtime for AI agents, tools, humans, and multi-agent systems.**

AASM turns open-ended agent behavior into an explicit computational process: state is durable, transitions are legal or illegal, plans are graphs, branches can be rolled back, repeated subproblems can be memoized, scarce resources can be allocated algorithmically, and important claims can be challenged before they are committed.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.2.0%20early--stage-orange)](ROADMAP.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[**Quick start**](#quick-start) · [**Downloads**](#downloads) · [**Use cases**](#use-cases) · [**Examples**](#examples) · [**Architecture**](#architecture) · [**Contributing**](CONTRIBUTING.md)

</div>

---

## What is AASM?

Most agent frameworks are very good at giving a model tools. AASM is focused on a different question:

> **How do you govern what an intelligent system is allowed to do next?**

AASM provides a role-agnostic control layer around agents. The model can propose. AASM keeps the authoritative state, selects algorithmic operators, enforces legal transitions, records provenance, manages checkpoints, and provides hooks for verification and governance.

The core idea is simple:

> **Models propose. Algorithms organize. Policy authorizes. Evidence validates. State governs what happens next.**

AASM is not tied to a Planner/Builder architecture. It can coordinate one agent, many specialists, a swarm, human approvals, tools, simulators, or external services through the same runtime contracts.

## Why this exists

LLMs are probabilistic. Real workflows often are not.

Long-running or high-complexity agent work benefits from properties that ordinary conversational loops do not naturally provide:

- explicit machine state instead of hidden conversational state
- legal state transitions instead of improvised control flow
- reversible checkpoints before risky branches
- dependency graphs instead of flat task lists
- memoized subproblems instead of repeated reasoning
- resource-aware routing instead of indiscriminate agent spawning
- adversarial checks before important conclusions are committed
- configurable authority instead of assuming every worker can rewrite the plan
- append-only event provenance for inspection and debugging

AASM is an attempt to make those properties first-class.

## Core capabilities

| Capability | What AASM does |
|---|---|
| **State machine** | Governs execution through explicit states and legal transitions. |
| **Algorithm router** | Classifies problem structure and selects applicable computational strategies. |
| **Graph planning** | Represents dependencies as a graph with topological ordering, shortest-path search, and edge relaxation. |
| **Backtracking** | Checkpoints state, prunes invalid branches, and restores known-good states. |
| **DP memory** | Canonicalizes and memoizes equivalent solved subproblems with validity scopes. |
| **Resource flow** | Uses max-flow/min-cut machinery to reason about constrained agents, tools, and capacity. |
| **Adversarial verification** | Challenges unsupported claims and searches for counterexamples or missing evidence. |
| **Authority policies** | Supports controller, autonomous, quorum, and hierarchical governance models. |
| **Agent protocols** | Provides generic agent contracts plus adapters for common orchestration patterns. |
| **Provenance** | Emits state-change and execution events so the run can be inspected after the fact. |

## Architecture

```mermaid
flowchart TD
    G[Goal / Event / Request] --> I[Ingest & Normalize]
    I --> F[Formalize Objective, Constraints, Invariants]
    F --> C[Classify Problem Structure]
    C --> R[Algorithm Router]
    R --> P[Plan Graph / Search Frontier]
    P --> A[Authority Policy]
    A --> X[Agent / Tool / Human Execution]
    X --> O[Observe Result]
    O --> V[Verify Evidence & Invariants]
    V -->|valid| K[Commit]
    V -->|repairable| E[Repair]
    V -->|bad branch| B[Backtrack]
    V -->|unknown| N[Investigate]
    K --> D{Goal complete?}
    D -->|no| P
    D -->|yes| Z[Complete]
    E --> X
    B --> P
    N --> F
```

The LLM is **inside** the machine. It is not the machine.

## Algorithmic foundation

AASM translates classic algorithms into agent-runtime operators:

| Classical idea | Agentic interpretation |
|---|---|
| Recursion / reduction | Decompose a goal into structurally related subproblems. |
| Backtracking | Explore a branch, detect contradiction, and restore a prior valid state. |
| Dynamic programming | Reuse solved equivalent subproblems rather than paying to solve them again. |
| Greedy methods | Select locally optimal actions when the governing invariant makes that safe. |
| Graph traversal | Discover dependencies, requirements, artifacts, hypotheses, and work units. |
| Topological ordering | Determine a legal execution order for dependent work. |
| Shortest paths | Choose a lower-cost route from the current state to the goal. |
| Edge relaxation | Update a plan locally when a better path is discovered. |
| Max-flow / min-cut | Allocate scarce execution capacity and identify bottlenecks. |
| Adversary arguments | Search for a consistent counterexample that could invalidate a conclusion. |
| Automata | Define the legal control behavior of the orchestration system itself. |

The design was inspired by the algorithmic techniques presented in Jeff Erickson's openly available *Algorithms* and *Models of Computation* materials. AASM's implementation and agent-runtime interpretation are original. See [`docs/ERICKSON_MAPPING.md`](docs/ERICKSON_MAPPING.md).

## Use cases

AASM is intentionally domain-neutral. Examples include:

### Agentic software engineering
Coordinate architecture, implementation, tests, review, CI recovery, and release work while preserving a durable plan and preventing a worker from silently redefining project state.

### Research and evidence synthesis
Represent claims, sources, dependencies, contradictions, and confidence as explicit state; require adversarial verification before important conclusions are accepted.

### CAD / engineering workflows
Model requirements, geometry, analysis, simulation, drawings, validation, and manufacturing handoffs as dependent graph nodes with rollback when an assumption or test fails.

### Multi-agent teams
Allocate specialists by capability, control which roles can authorize changes, and use capacity-aware scheduling rather than simply spawning more workers.

### Long-running autonomous workflows
Checkpoint progress, recover from failure, memoize solved subproblems, and resume from durable machine state.

### Human-in-the-loop systems
Insert approvals only where authority policy requires them while allowing reversible low-risk work to continue autonomously.

### Simulation and optimization
Treat candidate solutions as branches, prune invalid states, reuse equivalent subproblems, and route scarce simulation capacity toward the most useful frontier.

### Tool-heavy automation
Coordinate APIs, CLIs, browsers, databases, test harnesses, or external systems through one state-and-evidence contract.

## Quick start

### Requirements

- Python **3.11+**
- No runtime dependencies beyond the Python standard library in v0.2.0

### Install from a clone

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
pytest -q
```

Run the included demo:

```bash
aasm demo
python examples/multi_agent_demo.py
```

## Downloads

Choose whichever form is easiest:

- **[Download source ZIP](https://github.com/halthinks/AASM/archive/refs/heads/main.zip)**
- **[Download source TAR.GZ](https://github.com/halthinks/AASM/archive/refs/heads/main.tar.gz)**
- **Clone with Git:** `git clone https://github.com/halthinks/AASM.git`
- **Browse the repository:** [github.com/halthinks/AASM](https://github.com/halthinks/AASM)

> AASM is currently **v0.2.0 / early-stage**. The `main` archive tracks current development. Versioned releases and package-registry distribution are planned; see the [roadmap](ROADMAP.md).

## Minimal example

```python
from aasm import AASMEngine, ProblemSpec, MachineState

problem = ProblemSpec(
    goal="Produce and verify an artifact",
    constraints=[{"id": "C1", "text": "preserve provenance"}],
    acceptance_tests=[{"id": "T1", "text": "all tests pass"}],
    features={
        "dependency_graph": True,
        "branching_choices": True,
        "overlapping_subproblems": True,
        "capacity_constraints": True,
    },
)

engine = AASMEngine(problem)
engine.transition(MachineState.FORMALIZE, "goal normalized")
engine.transition(MachineState.CLASSIFY, "problem formalized")

print(engine.classify())
```

A larger multi-agent example is available at [`examples/multi_agent_demo.py`](examples/multi_agent_demo.py).

### Durable runs and crash recovery

```python
from aasm import AASMEngine, MachineState, ProblemSpec, SQLiteStore

store = SQLiteStore("runs.db")
engine = AASMEngine(ProblemSpec("Long-running verified work"), store=store)
engine.transition(MachineState.FORMALIZE, "normalized")
machine_id = engine.snapshot.machine_id
store.close()

# A later process can reconstruct the run from the durable event stream.
store = SQLiteStore("runs.db")
engine = AASMEngine.resume(machine_id, store)
```

See [`docs/DURABLE_RUNTIME.md`](docs/DURABLE_RUNTIME.md) and [`examples/durable_run.py`](examples/durable_run.py).

## Orchestration profiles

AASM ships with multiple profiles to demonstrate that governance and role structure are independent of the core runtime:

- [`single_agent.yaml`](profiles/single_agent.yaml) — one agent with bounded autonomy
- [`planner_builder.yaml`](profiles/planner_builder.yaml) — compatibility profile for Planner/Builder systems
- [`expert_swarm.yaml`](profiles/expert_swarm.yaml) — specialist swarm with quorum authority
- [`hierarchical_team.yaml`](profiles/hierarchical_team.yaml) — layered authority and delegation
- [`quorum_governance.yaml`](profiles/quorum_governance.yaml) — decisions authorized by multiple voters
- [`human_in_loop.yaml`](profiles/human_in_loop.yaml) — human approval at configured boundaries

## Machine lifecycle

A typical run moves through:

```text
INGEST → FORMALIZE → CLASSIFY → DECOMPOSE / PLAN → SELECT
       → EXECUTE → OBSERVE → VERIFY
```

Verification can transition to:

```text
COMMIT | REPAIR | BACKTRACK | INVESTIGATE | COMPLETE | FAIL
```

Illegal transitions raise an exception rather than silently changing machine state.

## What AASM is not

AASM is **not**:

- an LLM provider
- a prompt library
- a replacement for your agent framework
- a guarantee that an AI-generated proposal is correct
- a fully distributed durable workflow engine yet
- tied to any single agent role topology

It is a control/runtime layer intended to sit around or underneath agent behavior.

## Project status

**Current version: `0.2.0` — early-stage / experimental.**

The runtime now includes an event-sourced state path, SQLite durability, deterministic replay for event-sourced fields, persisted checkpoints, and crash/restart recovery. The next stages focus on durable external effects, richer recovery semantics, async/distributed execution, declarative machine definitions, model checking, observability, and integration adapters.

See [`ROADMAP.md`](ROADMAP.md) for the direction of travel.

## Contributing

Contributions are welcome—especially small, well-tested improvements that strengthen correctness, interoperability, documentation, or agent-runtime usefulness.

Please read:

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — development workflow and contribution standards
- [`GOVERNANCE.md`](GOVERNANCE.md) — how project decisions are made
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md) — community expectations
- [`SECURITY.md`](SECURITY.md) — responsible vulnerability reporting

New pull requests should explain **what problem they solve, why the change belongs in AASM, how it was validated, and whether it changes any state/transition or compatibility contract**.

## Design principles

1. **Explicit over implicit.** Important state belongs in machine-readable structures.
2. **Reversible where possible.** Risky work should have a recovery path.
3. **Evidence before commitment.** Important claims should be inspectable and challengeable.
4. **Role-agnostic core.** Agent topology is configuration, not architecture.
5. **Algorithm before improvisation.** Use known computational structure when the problem has it.
6. **Authority is separate from capability.** Being able to perform work does not automatically grant permission to redefine authoritative state.
7. **Provenance is a feature.** A run should be understandable after it happens.
8. **No fake determinism.** AASM constrains control flow; it does not pretend probabilistic model outputs are deterministic.

## Potential

The long-term opportunity is larger than a single orchestration pattern. AASM can become a reusable **algorithmic control plane for intelligent systems**: a layer where agents and tools remain flexible, but execution acquires the same kinds of structure that mature software systems expect from schedulers, workflow engines, state machines, transaction logs, graph planners, and verification pipelines.

That could make agent systems easier to inspect, resume, benchmark, govern, integrate, and trust—not because the model becomes infallible, but because the surrounding system becomes more explicit about uncertainty, authority, state, evidence, and recovery.

## Acknowledgements

AASM's algorithmic mapping was inspired by Jeff Erickson's excellent open educational materials on algorithms and models of computation. Those materials are not bundled with this project and remain under their respective terms.

This repository began as a first open-source release with the goal of turning a useful systems idea into something other people can inspect, challenge, extend, and improve.

## License

AASM is released under the [MIT License](LICENSE).

---

<div align="center">

**If the idea is useful to you, try it, break it, open an issue, or send a PR.**

</div>
