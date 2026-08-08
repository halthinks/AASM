<div align="center">

# AASM
## Algorithmic Agent State Machine

**A deterministic orchestration runtime for AI agents, tools, humans, and multi-agent systems.**

AASM turns open-ended agent behavior into an explicit computational process: state is durable, transitions are legal or illegal, plans are graphs, branches can be rolled back, repeated subproblems can be memoized, scarce resources can be allocated algorithmically, and important claims can be challenged before they are committed.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.9.0%20early--stage-orange)](ROADMAP.md)
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
- No mandatory runtime dependencies beyond the Python standard library in v0.9.0; PostgreSQL support is an optional extra

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

> AASM is currently **v0.9.0 / early-stage**. The `main` archive tracks current development. Versioned releases and package-registry distribution are planned; see the [roadmap](ROADMAP.md).

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

store = SQLiteStore("runs.db")
engine = AASMEngine.resume(machine_id, store)
```

See [`docs/DURABLE_RUNTIME.md`](docs/DURABLE_RUNTIME.md) and [`examples/durable_run.py`](examples/durable_run.py).

### Durable planning, memory, and evidence

AASM persists the plan graph, frontier/visited/pruned state, memoized subproblems, and structured evidence lineage in the same replayable history as the state machine. Historical forks receive exactly the cognitive state that existed at their fork boundary and then diverge independently.

See [`docs/DURABLE_COGNITION.md`](docs/DURABLE_COGNITION.md).

### Durable external effects

AASM can persist externally observable actions separately from model reasoning. Each effect has an authorization state, retry policy, idempotency key, durable result/error record, and crash-recovery semantics. If a process dies while an effect is running, AASM marks the outcome `UNKNOWN` and refuses a blind retry by default.

See [`docs/EFFECT_SYSTEM.md`](docs/EFFECT_SYSTEM.md) and [`examples/effect_demo.py`](examples/effect_demo.py).

### Declarative machines and model checking

AASM machines can be defined as data rather than hard-coded control flow. `MachineDefinition` supports JSON and TOML with no additional dependency, plus optional YAML when PyYAML is installed. Before execution, `check_machine()` can detect undefined targets, unreachable states, non-terminal dead ends, terminal states with outgoing edges, and reachable regions that cannot reach any terminal state.

```bash
aasm verify-machine examples/machine.json
```

See [`docs/DECLARATIVE_MACHINES.md`](docs/DECLARATIVE_MACHINES.md) and [`examples/machine.json`](examples/machine.json).

### Historical replay and forks

Replay can stop at an exact event sequence, and a durable run can fork from that boundary into an independent machine with explicit lineage. Forks do not copy or re-run prior external effects.

```bash
aasm replay MACHINE_ID --db runs.db --at 17
aasm fork MACHINE_ID --db runs.db --at 17
```

See [`docs/REPLAY_FORK.md`](docs/REPLAY_FORK.md) and [`examples/fork_demo.py`](examples/fork_demo.py).

### Durable capability scheduling

AASM can persist a capability registry for agents, tools, humans, services, and constrained compute resources, then allocate task demand through its max-flow/min-cut engine. Schedules expose assignments, utilization, unmet demand, and the current bottleneck instead of simply spawning more workers.

```python
from aasm import ResourceRecord, TaskDemand

engine.register_resource(ResourceRecord("verifier", "agent", ["verify"], capacity=1))
result = engine.schedule([
    TaskDemand("verify-a", ["verify"], priority=10),
    TaskDemand("verify-b", ["verify"], priority=5),
])
print(result.bottlenecks)
```

See [`docs/RESOURCE_SCHEDULER.md`](docs/RESOURCE_SCHEDULER.md) and [`examples/scheduler_demo.py`](examples/scheduler_demo.py).

### Remote multi-host execution

AASM v0.9 can run as a network control plane backed by PostgreSQL so workers on different machines share one authoritative event history and task-claim boundary.

```bash
pip install -e '.[postgres]'
aasm serve --store 'postgresql://aasm:password@db.example/aasm' --host 0.0.0.0 --port 8787 --token CHANGE_ME
```

Remote workers use `AASMRemoteClient` to register, heartbeat, claim leases, renew them, and report results. The browser Control Center at `/ui` shows live run state, workers, leases, plan graph, model routing, evidence, and cache-adjusted model economics. See [`docs/REMOTE_EXECUTION.md`](docs/REMOTE_EXECUTION.md) and [`docs/CONTROL_CENTER.md`](docs/CONTROL_CENTER.md).

### Model strength / cost routing

Model choice is a first-class resource decision. Register model profiles with capability, strength, cost, latency, and context metadata, then route each task against hard quality/cost constraints and an optimization objective. Luna/Terra/Sol-class routing can therefore spend stronger models where the quality floor requires them instead of treating all work as equivalent.

See [`docs/MODEL_ROUTING.md`](docs/MODEL_ROUTING.md) and [`examples/model_profiles.json`](examples/model_profiles.json).

### Real model executors and governance economics

AASM is not only a skill file. v0.9 includes a real `OpenAIResponsesExecutor`, a headless `CodexCLIExecutor`, durable call-purpose accounting, cache-adjusted cost estimation, and a deterministic review gate.

```python
from aasm import CallPurpose, ModelUsageRecord

engine.record_model_usage(ModelUsageRecord(
    model_id="gpt-5.6-terra",
    purpose=CallPurpose.PRODUCTIVE.value,
    input_tokens=12000,
    cached_input_tokens=9000,
    output_tokens=3500,
))

print(engine.economics_summary())
print(engine.review_gate("test"))
```

The rule is simple: **do not pay an intelligent reviewer to repeatedly re-decide a permission decision that can be expressed deterministically.** Keep sandboxing and technical boundaries; reserve semantic model review for changed assumptions, failed verification, materially large changes, and genuinely risky or irreversible operations.

See [`docs/EXECUTOR_ADAPTERS.md`](docs/EXECUTOR_ADAPTERS.md) and [`docs/MODEL_ECONOMICS.md`](docs/MODEL_ECONOMICS.md).

## Orchestration profiles

AASM ships with multiple profiles to demonstrate that governance and role structure are independent of the core runtime:

- [`single_agent.yaml`](profiles/single_agent.yaml) — one agent with bounded autonomy
- [`planner_builder.yaml`](profiles/planner_builder.yaml) — compatibility profile for Planner/Builder systems
- [`expert_swarm.yaml`](profiles/expert_swarm.yaml) — specialist swarm with quorum authority
- [`hierarchical_team.yaml`](profiles/hierarchical_team.yaml) — layered authority and delegation
- [`quorum_governance.yaml`](profiles/quorum_governance.yaml) — decisions authorized by multiple voters
- [`human_in_loop.yaml`](profiles/human_in_loop.yaml) — human authorization for configured external/irreversible actions

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
- a hosted SaaS or managed worker fleet by itself
- tied to any single agent role topology

It is a control/runtime layer intended to sit around or underneath agent behavior.

## Distributed workers and crash-safe leases

AASM can coordinate multiple worker processes or machines through durable task leases. Workers are linked to capability resources, heartbeat into the runtime, claim tasks through an atomic reservation boundary, and hold time-limited leases that can be renewed, completed, failed, released, or reclaimed after expiry. Quotas can constrain the whole machine, a worker, or a resource.

SQLite uses a dedicated task-claim table to prevent two processes from simultaneously acquiring the same task; PostgreSQL extends that ownership boundary across hosts.

See [`docs/DISTRIBUTED_WORKERS.md`](docs/DISTRIBUTED_WORKERS.md) and [`docs/REMOTE_EXECUTION.md`](docs/REMOTE_EXECUTION.md).

## Project status

**Current version: `0.9.0` — early-stage / experimental.**

The runtime now includes event-sourced state, SQLite and PostgreSQL durability, persisted checkpoints, crash/restart recovery, durable external effects, declarative machines, static model checking, historical replay/forking, durable planning and DP memory, evidence lineage, capability-aware scheduling, crash-safe worker leases/quotas, remote multi-host execution, model-strength/cost routing, real OpenAI/Codex executor adapters, a browser Control Center, and cache-adjusted governance economics.

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