<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable algorithmic control plane and deterministic execution architecture for AI agents, tools, humans, models, and distributed worker fleets.**

AASM turns open-ended agent work into an explicit computational process: state is durable, transitions are legal or illegal, plans are graphs, authority is separate from capability, changed information pauses only affected work, evidence governs commitment, contradictions become learned constraints, and material decisions retain provenance.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.21.0%20experimental-orange)](ROADMAP.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[**Quick start**](#quick-start) · [**What it can do**](#what-it-can-do) · [**v0.21 formal calculus**](#v021-formal-calculus-and-conflict-learning) · [**Architecture**](#architecture) · [**Downloads**](#downloads) · [**Contributing**](#contributing)

</div>

---

## What is AASM?

Most agent frameworks focus on giving a model tools. AASM focuses on the harder systems question:

> **How do you govern what an intelligent system is allowed to do next, remember what happened, recover from failure, coordinate real work, and improve future decisions when execution contradicts the plan?**

AASM is not a prompt file pretending to be a runtime. It includes:

- a Python runtime and CLI;
- event-sourced machine state;
- SQLite and PostgreSQL coordination;
- declarative machine definitions and structural model checking;
- crash-safe worker leases, capacity limits, and quotas;
- remote worker and HTTP control-plane protocols;
- graph planning, checkpoint backtracking, replay, forks, and DP memory;
- evidence, assumptions, observations, contradictions, and lineage;
- capability-aware max-flow/min-cut scheduling;
- model-strength, cost, context, latency, and outcome-aware routing;
- OpenAI Responses and Codex CLI executor adapters;
- governance economics and redundant-review suppression;
- executable Planner / Builder / Verifier orchestration;
- selective information-change checkpoints and additive steering;
- useful-concurrency and physical-fleet planning;
- mission controls, live telemetry, external artifact references, and operator controls;
- a durable formal decision/obligation calculus with conflict learning;
- a browser Control Center.

The operating principle is:

> **Models propose. Algorithms organize. Policy authorizes. Evidence validates. Contradictions teach. Durable state governs what happens next.**

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
- provenance that survives restarts and forks;
- selective repair instead of destructive whole-plan replacement;
- machine-readable conflicts instead of unstructured failure logs;
- learned constraints instead of repeated rediscovery of the same invalid plan.

AASM makes those properties first-class around flexible agents rather than pretending the underlying model itself is deterministic.

## What it can do

| Capability | What AASM provides |
|---|---|
| **State machine** | Explicit legal transitions, terminal states, replay, and declarative machine definitions. |
| **Durable cognition** | Plan graph, frontier, visited/pruned state, DP memory, assumptions, claims, observations, contradictions, and provenance. |
| **Formal calculus** | Named decisions, conditional obligations, model-relative locks, conflict explanations, learned no-goods, backjumping, fairness, and search restart. |
| **External effects** | Proposal, authorization, attempt ownership, idempotency, failure, `UNKNOWN` outcome, and reconciliation. |
| **Resource scheduling** | Capability-aware allocation, priorities, quotas, utilization, unmet demand, max-flow, and min-cut evidence. |
| **Distributed execution** | PostgreSQL-backed multi-host workers, heartbeats, leases, expiry, reclaim, and canonical ownership. |
| **Model routing** | Strength, capability, context, latency, cost, concurrency, and task-class outcome evidence. |
| **Governance economics** | Productive/review token accounting, cache-aware cost, review budgets, and safe reuse of unchanged low-risk reviews. |
| **Planner / Builder / Verifier** | Executable `CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT` protocol with Planner-only plan authority. |
| **Selective steering** | Changed evidence, assumptions, verification, risk, or user requirements pause only the impacted dependency region. |
| **Massive collaboration** | Critical path, parallel width, capability cuts, coordination overhead, and the smallest near-optimal worker count. |
| **Fleet control** | Recommendation → admission quota → explicit provisioning plan → authorized provider effect. |
| **Mission control** | Durable `QUIESCE`, `SUSPEND`, and `RESUME` without conflating mission status with plan or machine state. |
| **Observability** | Cursor-paged telemetry, `LEASE_LOST`, external artifact references, bounded previews, and execution history. |
| **Operator interface** | Browser Control Center plus local and remote CLI/API surfaces. |

## v0.21: formal calculus and conflict learning

AASM v0.21 implements cumulative, conflict-learning agent execution inside the existing event-sourced runtime.

It adds:

- named planning decisions and one active decision per subject;
- conditional persistent obligations with explicit evidence contracts;
- model-relative locks that suppress work without deleting it;
- first-class conflict and explanation objects;
- projection of validated contradictions into guarded hard or soft learned constraints;
- deterministic, graph-directed non-chronological backjumping;
- restart-without-amnesia semantics;
- cross-model fairness for persistent unresolved obligations;
- Planner-authorized recovery under the executable PBV profile;
- backward-compatible replay, SQLite, PostgreSQL, and historical-fork semantics.

The executable loop is:

```text
Abstract decisions
       ↓
Enable conditional obligations
       ↓
Execute authorized work
       ↓
Verify concrete evidence
       ↓
Conflict and causal explanation
       ↓
Learn a durable blocking constraint
       ↓
Backjump, repair, investigate, or restart
```

The architectural connection is inspired by AVATAR-style heterogeneous reasoning: a cheaper abstraction layer controls candidate combinations, a richer semantic layer evaluates them, and contradictions discovered in the richer layer are returned as reusable blocking information.

### Formal object model

The v0.21 calculus distinguishes:

```text
Decision Graph
    what was selected, under which assumptions, and why

Obligation Graph
    what must eventually be enabled, satisfied, rejected,
    superseded, or proven impossible

Evidence Graph
    what observations support, contradict, or invalidate
    decisions and completion claims
```

A learned incompatibility is represented as a guarded no-good:

```text
guard ⇒ NOT (assumption₁ AND assumption₂ AND ... AND assumptionₙ)
```

Only validated or proven assumption conflicts may become hard constraints. Evidence disagreements and heuristic explanations remain soft.

### Backjumping

Backjumping follows causal dependencies rather than reverse creation order:

1. trace explanation literals to active decisions;
2. follow derived decisions to explicit causal roots;
3. compute dependent decision, obligation, and plan-node closures;
4. choose the deepest revisable root with the smallest dependent closure;
5. invalidate only that causal region;
6. preserve unrelated decisions and work, including unrelated work created later;
7. mark affected obligations and plan nodes for revalidation;
8. reuse the existing information-change checkpoint machinery for selective recovery.

### Locking, fairness, and restart

A lock is conditional suppression, never deletion. Model changes, backjumps, and search restarts reevaluate locks and restore obligations whose lock conditions no longer hold.

Persistent obligations age by deterministic model epochs. Overdue work must be exposed, explicitly deferred within policy, or terminally dispositioned; it cannot silently disappear under a sequence of plans.

`restart_search()` is distinct from process resume, checkpoint restoration, and historical fork. It clears speculative assignments and search-local state while retaining evidence, learned constraints, effects, mission state, workers, leases, replay history, and fork lineage.

### Integration boundary

The calculus is part of the production AASM state:

```text
existing MachineSnapshot
existing immutable event stream
existing pure reducer
existing SQLite/PostgreSQL stores
existing PlanGraph and EvidenceLedger
existing Planner authority boundary
existing information-change checkpoints
        +
formal decisions, obligations, locks, conflicts,
explanations, learned constraints, backjumping,
search restart, and fairness state
```

Calculus changes commit through the existing `SNAPSHOT_PATCHED` event path. Older snapshots without the field are migrated to the canonical empty calculus state when deserialized.

See [`docs/FORMAL_CALCULUS.md`](docs/FORMAL_CALCULUS.md) and [`docs/RELEASE_0.21.md`](docs/RELEASE_0.21.md).

## Architecture

```mermaid
flowchart TD
    U[User / Event / Goal] --> S[AASM Durable State]
    S --> P[Planner / Decision Abstraction]
    P --> A[Authority and Governance]
    A --> R[Resource and Model Routing]
    R --> W[Workers / Agents / Tools / Humans]
    W --> T[Telemetry / Artifacts / Evidence]
    T --> V[Verifier]
    V -->|accepted| C[Commit]
    V -->|local defect| X[Selective Repair]
    V -->|information gap| I[Investigate]
    V -->|contradiction| F[Conflict Explanation]
    F --> L[Learn Constraint]
    L --> B[Backjump / Restart]
    X --> P
    I --> P
    B --> P
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

### Formal-calculus example

```python
from aasm import AASMEngine, DecisionRecord, ObligationRecord, ProblemSpec

engine = AASMEngine(ProblemSpec("Build under explicit assumptions"))
engine.register_decision(DecisionRecord("D-db", "database", "postgres"))
engine.activate_decision("D-db")
engine.register_obligation(ObligationRecord(
    "O-db",
    "Implement PostgreSQL storage",
    activation_condition={
        "decision": {"subject": "database", "op": "EQ", "value": "postgres"}
    },
))
engine.enable_obligation("O-db")
print(engine.calculus_report()["active_model"])
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

### CLI inspection

```bash
aasm calculus MACHINE_ID --store runs.db
aasm calculus-fairness MACHINE_ID --store runs.db
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

AASM is currently **v0.21.0 / experimental**. The `main` archives track current development.

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

Insert explicit approvals where authority policy requires them without repeatedly asking an intelligent reviewer to re-decide deterministic low-risk permissions.

## Project structure

```text
src/aasm/       runtime, stores, routing, workers, calculus, control plane
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

A good contribution explains the problem, why the change belongs in AASM, how it was validated, and whether it changes a state, transition, authority, schema, persistence, or compatibility contract.

## Design principles

1. **Explicit over implicit.** Important state belongs in machine-readable structures.
2. **Reversible where possible.** Risky work should have a recovery path.
3. **Evidence before commitment.** Important claims should be inspectable and challengeable.
4. **Role-agnostic core.** Agent topology is configuration, not architecture.
5. **Authority is separate from capability.** Being able to act does not grant permission to redefine state.
6. **Algorithms before blind spawning.** Use dependency, flow, and cost structure to decide whether more agents help.
7. **Provenance is a feature.** A run should remain understandable after restart, repair, or fork.
8. **Contradictions should become knowledge.** A trustworthy failure should restrict future search rather than merely produce another retry.
9. **No fake determinism.** AASM constrains control flow; it does not pretend probabilistic outputs are infallible.

## Acknowledgements

AASM's algorithmic mapping was inspired by Jeff Erickson's open educational materials on algorithms and models of computation. AASM's implementation and agent-runtime interpretation are original; see [`docs/ERICKSON_MAPPING.md`](docs/ERICKSON_MAPPING.md).

The v0.21 formal-calculus direction is additionally informed by research in formal verification, saturation theorem proving, AVATAR-style splitting, labelled splitting, conflict-driven clause learning, non-chronological backjumping, restart policies, and fairness under changing abstract models.

This repository began as a first open-source contribution with the goal of turning a useful systems idea into something other people can inspect, test, challenge, and extend.

## License

AASM is released under the [MIT License](LICENSE).

---

<div align="center">

**Try it. Break it. Measure it. Improve it.**

</div>
