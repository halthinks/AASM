<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable algorithmic control plane for AI agents, tools, humans, models, and distributed worker fleets.**

AASM turns open-ended agent work into an explicit computational process: state is durable, transitions are legal or illegal, plans are graphs, authority is separate from capability, model strength and cost are routable resources, changed information pauses only affected work, and every material decision can retain evidence and provenance.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.19.0%20experimental-orange)](ROADMAP.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[**Quick start**](#quick-start) · [**Downloads**](#downloads) · [**What it can do**](#what-it-can-do) · [**Architecture**](#architecture) · [**Use cases**](#use-cases) · [**Contributing**](#contributing)

</div>

---

## What is AASM?

Most agent frameworks focus on giving a model tools. AASM focuses on the harder systems question:

> **How do you govern what an intelligent system is allowed to do next, remember what happened, recover from failure, and coordinate real work across models and machines?**

AASM is not a prompt file pretending to be a runtime. It includes:

- a Python runtime and CLI;
- event-sourced machine state;
- SQLite and PostgreSQL coordination;
- crash-safe worker leases and quotas;
- remote worker and HTTP control-plane protocols;
- graph planning, backtracking, and DP memory;
- evidence and contradiction lineage;
- capability-aware max-flow/min-cut scheduling;
- model-strength, cost, context, and latency routing;
- OpenAI Responses and Codex CLI executor adapters;
- adaptive task-class model routing from evaluated outcomes;
- governance economics and redundant-review suppression;
- executable Planner / Builder / Verifier orchestration;
- selective information-change checkpoints;
- useful-concurrency and physical-fleet planning;
- live telemetry, external artifact references, and operator controls;
- a browser Control Center.

The operating principle is:

> **Models propose. Algorithms organize. Policy authorizes. Evidence validates. Durable state governs what happens next.**

## Why this exists

LLMs are probabilistic. Serious workflows still need properties normally supplied by schedulers, workflow engines, databases, state machines, transaction logs, and verification systems:

- explicit state instead of hidden conversational state;
- legal transitions instead of improvised control flow;
- checkpoint and replay instead of starting over;
- dependency graphs instead of flat task lists;
- resource-aware routing instead of indiscriminate agent spawning;
- distinct capability and authority boundaries;
- explicit external-effect authorization and idempotency;
- crash-safe ownership and recovery;
- measurable productive versus governance cost;
- provenance that survives restarts and forks.

AASM makes those properties first-class around flexible agents rather than trying to make the underlying model deterministic.

## What it can do

| Capability | What AASM provides |
|---|---|
| **State machine** | Explicit legal transitions, terminal states, replay, and declarative machine definitions. |
| **Durable cognition** | Plan graph, frontier, visited/pruned state, DP memory, assumptions, claims, observations, and contradictions. |
| **External effects** | Proposal, authorization, attempt ownership, idempotency, failure, UNKNOWN outcome, and reconciliation. |
| **Resource scheduling** | Capability-aware allocation, priorities, quotas, utilization, unmet demand, max-flow, and min-cut evidence. |
| **Distributed execution** | PostgreSQL-backed multi-host workers, heartbeats, leases, expiry, reclaim, and canonical ownership. |
| **Model routing** | Strength, capability, context, latency, cost, concurrency, and task-class outcome evidence. |
| **Governance economics** | Productive/review token accounting, cache-aware cost, review budgets, and safe reuse of unchanged low-risk reviews. |
| **Planner / Builder / Verifier** | Executable `CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT` protocol with Planner-only plan authority. |
| **Massive collaboration** | Critical path, parallel width, capability cuts, coordination overhead, and smallest near-optimal worker count. |
| **Selective steering** | Changed evidence, assumptions, verification, risk, or user requirements pause only the impacted dependency region. |
| **Fleet control** | Recommendation → admission quota → explicit provisioning plan → authorized provider effect. |
| **Mission control** | Durable `QUIESCE`, `SUSPEND`, and `RESUME` without conflating mission status with plan or machine state. |
| **Observability** | Cursor-paged telemetry, `LEASE_LOST`, external artifact refs, bounded previews, and execution history. |
| **Operator interface** | Browser Control Center plus local and remote CLI/API surfaces. |

## v0.19: mission controls and high-volume observability

AASM v0.19 adds the operator layer needed for long-running missions.

### Mission pause modes

```text
QUIESCE
  block new claims
  preserve active leases

SUSPEND
  commit mission pause
  release active leases
  reject stale concurrent claims

RESUME
  reopen mission admission
  do not silently resume change-paused tasks,
  offline workers, effects, or old leases
```

A worker may finish local computation after its lease was released by suspension, expiry, or worker control. AASM now records `LEASE_LOST` instead of falsely accepting that result as durable completion.

### Controlled effects and forks

```text
PROPOSED
   ↓ inspect
AUTHORIZED
   ↓ type-specific execution
SUCCEEDED / FAILED / UNKNOWN
```

Approving an effect never executes it. Controlled forks are durable `machine.fork` effects with a fixed source event sequence and deterministic target machine ID. Re-execution is idempotent; a target with conflicting lineage is rejected.

### Local and container fleets

- `LocalProcessSupervisorAdapter` starts explicit argv without a shell, confines optional working directories, and persists PID/idempotency state.
- `DockerComposeScaleAdapter` scales a selected service using explicit Docker Compose argv.
- `KubernetesScaleAdapter` scales workloads without claiming that a replica-count change proves which logical AASM worker terminated.

### Cursor observability

Telemetry and artifact references are paged with opaque cursors and stable IDs. Bounded retention produces an explicit expired-cursor error rather than silently skipping data. Artifact previews are authenticated, size-bounded, and restricted to references registered to the selected machine.

See [`docs/MISSION_CONTROLS_OBSERVABILITY.md`](docs/MISSION_CONTROLS_OBSERVABILITY.md) and [`docs/RELEASE_0.19.md`](docs/RELEASE_0.19.md).

## Architecture

```mermaid
flowchart TD
    U[User / Event / Goal] --> S[AASM Durable State]
    S --> P[Graph Planner and Algorithm Router]
    P --> A[Authority and Governance]
    A --> R[Resource and Model Routing]
    R --> W[Workers / Agents / Tools / Humans]
    W --> T[Telemetry and Artifacts]
    T --> V[Verifier and Evidence]
    V -->|accepted| C[Commit]
    V -->|repair| X[Selective Checkpoint]
    X --> P
    C --> D{Complete?}
    D -->|no| P
    D -->|yes| Z[Complete]
```

For distributed operation:

```text
Control Center / CLI / API
            │
            ▼
      AASM control plane
            │
       PostgreSQL truth
            │
   ┌────────┼────────┐
   ▼        ▼        ▼
 Codex   Responses   Tool/sim
 worker    worker     worker
```

The LLM is **inside** the machine. It is not the machine.

## Quick start

### Requirements

- Python 3.11+
- standard-library-only core runtime
- optional PostgreSQL extra for real multi-host coordination

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
pytest -q
```

Run the demo:

```bash
aasm demo
python examples/multi_agent_demo.py
```

### Minimal state-machine example

```python
from aasm import AASMEngine, MachineState, ProblemSpec

engine = AASMEngine(ProblemSpec(
    goal="Produce and verify an artifact",
    constraints=[{"id": "C1", "text": "preserve provenance"}],
    acceptance_tests=[{"id": "T1", "text": "all tests pass"}],
    features={
        "dependency_graph": True,
        "branching_choices": True,
        "capacity_constraints": True,
    },
))

engine.transition(MachineState.FORMALIZE, "goal normalized")
engine.transition(MachineState.CLASSIFY, "problem formalized")
print(engine.classify())
```

### Durable local run

```python
from aasm import AASMEngine, ProblemSpec, SQLiteStore

store = SQLiteStore("runs.db")
engine = AASMEngine(ProblemSpec("Long-running verified work"), store=store)
machine_id = engine.snapshot.machine_id
store.close()

store = SQLiteStore("runs.db")
engine = AASMEngine.resume(machine_id, store)
```

### Remote multi-host control plane

```bash
pip install -e '.[postgres]'
aasm serve \
  --store 'postgresql://aasm:password@db.example/aasm' \
  --host 0.0.0.0 \
  --port 8787 \
  --token "$AASM_SERVER_TOKEN"
```

Open `/ui` on that server for the Control Center.

### Turnkey local supervisor configuration

```bash
aasm serve \
  --store runs.db \
  --token "$AASM_SERVER_TOKEN" \
  --runtime-config examples/runtime-config.local.json
```

### Mission controls

```bash
aasm mission-pause MACHINE_ID --store runs.db \
  --actor operator --reason "inspect anomaly" --mode QUIESCE

aasm mission-resume MACHINE_ID --store runs.db \
  --actor operator --reason "review complete"
```

### Controlled fork

```bash
aasm fork-propose MACHINE_ID --store runs.db \
  --actor operator --reason "evaluate alternate architecture"

aasm effect-authorize MACHINE_ID --store runs.db \
  --effect-id EFFECT_ID --actor operator --reason "approved isolation"

aasm fork-execute MACHINE_ID --store runs.db --effect-id EFFECT_ID
```

## Downloads

- **[Download source ZIP](https://github.com/halthinks/AASM/archive/refs/heads/main.zip)**
- **[Download source TAR.GZ](https://github.com/halthinks/AASM/archive/refs/heads/main.tar.gz)**
- Clone: `git clone https://github.com/halthinks/AASM.git`
- Browse: [github.com/halthinks/AASM](https://github.com/halthinks/AASM)

AASM is currently **v0.19.0 / experimental**. The `main` archives track current development.

## Use cases

### Agentic software engineering
Coordinate architecture, repository inspection, implementation, tests, adversarial review, repairs, CI recovery, and release work while keeping plan authority and provenance explicit.

### Research and evidence synthesis
Represent claims, sources, assumptions, contradictions, dependency structure, and confidence as durable evidence rather than hidden conversation context.

### CAD and engineering workflows
Model requirements, geometry, analysis, simulation, drawings, validation, and manufacturing handoffs as dependency nodes with selective rollback when an assumption changes.

### Model-efficient collaboration
Route inexpensive models to high-volume work, stronger models to architecture or contradiction resolution, and measure the least-cost model that reliably satisfies each task class.

### Long-running autonomous operations
Recover after crashes, reclaim stale work, pause a mission without destroying its plan, branch alternate histories, and inspect what happened afterward.

### Human-in-the-loop systems
Insert explicit approvals where authority policy requires them without paying an intelligent reviewer to repeatedly re-decide deterministic low-risk permissions.

## Project structure

```text
src/aasm/       runtime, stores, routing, workers, control plane
schemas/        machine-readable contracts
profiles/       orchestration and authority examples
examples/       runnable usage examples
docs/           architecture and subsystem guides
tests/          unit, durability, remote, and integration coverage
SKILL.md        operating contract for Codex and other agents
```

## What AASM is not

AASM is not an LLM provider, a prompt library, a guarantee that model output is correct, or a hosted worker fleet by itself. It is a control/runtime layer designed to sit around agents and tools.

## Contributing

Contributions are welcome, especially focused changes that improve correctness, interoperability, documentation, testing, provider adapters, formal properties, or real-world usefulness.

Please read:

- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`GOVERNANCE.md`](GOVERNANCE.md)
- [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md)
- [`SECURITY.md`](SECURITY.md)

A good pull request explains the problem, why the change belongs in AASM, how it was validated, and whether it changes a state, transition, authority, schema, persistence, or compatibility contract.

## Design principles

1. **Explicit over implicit.** Important state belongs in machine-readable structures.
2. **Reversible where possible.** Risky work should have a recovery path.
3. **Evidence before commitment.** Important claims should be inspectable and challengeable.
4. **Role-agnostic core.** Agent topology is configuration, not architecture.
5. **Authority is separate from capability.** Being able to act does not grant permission to redefine state.
6. **Algorithms before blind spawning.** Use dependency, flow, and cost structure to decide whether more agents help.
7. **Provenance is a feature.** A run should remain understandable after restart, repair, or fork.
8. **No fake determinism.** AASM constrains control flow; it does not pretend probabilistic outputs are infallible.

## Acknowledgements

AASM's algorithmic mapping was inspired by Jeff Erickson's open educational materials on algorithms and models of computation. AASM's implementation and agent-runtime interpretation are original; see [`docs/ERICKSON_MAPPING.md`](docs/ERICKSON_MAPPING.md).

This repository began as a first open-source contribution with the goal of turning a useful systems idea into something other people can inspect, test, challenge, and extend.

## License

AASM is released under the [MIT License](LICENSE).

---

<div align="center">

**Try it. Break it. Measure it. Improve it.**

</div>
