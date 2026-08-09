<div align="center">

# AASM
## Algorithmic Agent State Machine

**A deterministic orchestration runtime for AI agents, tools, humans, and multi-agent systems.**

AASM turns open-ended agent behavior into an explicit computational process: state is durable, transitions are legal or illegal, plans are graphs, branches can be rolled back, repeated subproblems can be memoized, scarce resources can be allocated algorithmically, and important claims can be challenged before they are committed.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.18.0%20early--stage-orange)](ROADMAP.md)
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
| **Executor orchestration** | Turns a claimed lease into a model route, physical executor invocation, usage/evidence capture, and durable completion. |
| **Adaptive model routing** | Learns task-class-specific model quality/cost/latency from explicit evaluated outcomes while preserving hard static eligibility floors. |
| **Governance economics** | Separates semantic review from authority, budgets governance overhead, reuses unchanged low-risk completed reviews, and pauses rather than waiving required review. |
| **Executable PBV profile** | Runs Builder → Verifier → Planner handoffs with Planner-only plan authority and explicit `CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT` control messages. |
| **Massive collaboration** | Computes useful worker fan-out from critical path, DAG width, eligible max-flow capacity, coordination overhead, cost, and min-cut bottlenecks instead of blindly spawning agents. |
| **Selective change checkpoints** | Maps changed information onto the affected dependency subgraph, pauses only invalidated work, preserves unaffected leases, and lets the Planner resume repaired nodes incrementally. |
| **Automatic checkpoint + fleet loop** | Turns material Verifier findings into selective checkpoints and optionally converts collaboration recommendations into an atomically enforced worker-admission quota. |
| **Physical fleet + telemetry** | Converts a fleet target into authority-gated provider effects and feeds observed execution durations/artifact references back into scheduling evidence. |
| **Provider/artifact/control layer** | Adds explicit provider adapters, external artifact references, and durable worker lifecycle controls without collapsing them into scheduling authority. |
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
- No mandatory runtime dependencies beyond the Python standard library in v0.18.0; PostgreSQL support is an optional extra

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

> AASM is currently **v0.18.0 / early-stage**. The `main` archive tracks current development. Versioned releases and package-registry distribution are planned; see the [roadmap](ROADMAP.md).

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

AASM can persist externally observable actions separately from model reasoning. Each effect has an authorization state, retry policy, idempotency key, durable result/error record, and crash-recovery semantics. If a process dies while an effect is running, explicit crash recovery marks the outcome `UNKNOWN` and refuses a blind retry by default.

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

AASM can run as a network control plane backed by PostgreSQL so workers on different machines share one authoritative event history and task-claim boundary.

```bash
pip install -e '.[postgres]'
aasm serve --store 'postgresql://aasm:password@db.example/aasm' --host 0.0.0.0 --port 8787 --token CHANGE_ME
```

Remote workers use `AASMRemoteClient` to register, heartbeat, claim leases, renew them, and report results. The browser Control Center at `/ui` shows live run state, workers, leases, plan graph, model routing, evidence, and cache-adjusted model economics. See [`docs/REMOTE_EXECUTION.md`](docs/REMOTE_EXECUTION.md) and [`docs/CONTROL_CENTER.md`](docs/CONTROL_CENTER.md).

### Model strength / cost routing

Model choice is a first-class resource decision. Register model profiles with capability, strength, cost, latency, and context metadata, then route each task against hard quality/cost constraints and an optimization objective.

The static router remains the eligibility boundary even when adaptive routing is enabled.

See [`docs/MODEL_ROUTING.md`](docs/MODEL_ROUTING.md) and [`examples/model_profiles.json`](examples/model_profiles.json).

### End-to-end executor orchestration

v0.10 closed the physical execution loop. A scheduled task can carry an `execution` contract; an `OrchestratedRemoteWorker` claims its lease, routes the model, selects a compatible worker-local executor, invokes the real Codex CLI / Responses API / custom adapter, reports model usage, and durably completes or fails the lease.

```bash
aasm worker \
  --url https://aasm.example \
  --machine-id MACHINE_ID \
  --worker-id coding-01 \
  --resource-id coding-pool \
  --executor codex \
  --executor-id codex-cli \
  --provider openai \
  --capability code \
  --cwd /workspace/repository \
  --token "$AASM_SERVER_TOKEN"
```

See [`docs/EXECUTOR_ORCHESTRATION.md`](docs/EXECUTOR_ORCHESTRATION.md) and [`examples/orchestrated_worker.py`](examples/orchestrated_worker.py).

### Adaptive model routing

v0.11 adds an explicit evaluated-outcome feedback loop. AASM can learn that one eligible model is sufficient for `routine_backend` work while a stronger static floor is still required for `architecture`, without hard-coding either conclusion globally.

```python
from aasm import ModelOutcomeRecord, ModelRouteRequest

engine.record_model_outcome(ModelOutcomeRecord(
    task_id="backend-42",
    task_class="routine_backend",
    model_id="luna",
    accepted=True,
    repair_required=False,
    verification_score=.95,
    latency_seconds=32.0,
    estimated_cost=.15,
))

route = engine.route_model(ModelRouteRequest(
    "next-backend-task",
    ["code"],
    min_strength=.5,
    metadata={
        "task_class":"routine_backend",
        "min_empirical_samples":5,
        "empirical_optimize":"cost_per_quality",
    },
))
```

AASM uses Wilson acceptance bounds rather than raw success rates; `confidence` is interval concentration rather than a probability-of-correctness claim. Execution success alone is not training evidence—the work must be explicitly evaluated first.

See [`docs/ADAPTIVE_MODEL_ROUTING.md`](docs/ADAPTIVE_MODEL_ROUTING.md) and [`examples/adaptive_routing.py`](examples/adaptive_routing.py).

### Real model executors and model economics

AASM is not only a skill file. It includes a real `OpenAIResponsesExecutor`, a headless `CodexCLIExecutor`, durable call-purpose accounting, cache-adjusted cost estimation, and a deterministic review gate.

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

See [`docs/EXECUTOR_ADAPTERS.md`](docs/EXECUTOR_ADAPTERS.md) and [`docs/MODEL_ECONOMICS.md`](docs/MODEL_ECONOMICS.md).

### Governance economics and reviewer-call efficiency

v0.12 makes semantic-review overhead a first-class control signal. AASM fingerprints the material governance context and can reuse a **completed low-risk semantic review** only when action, scope, policy, assumptions, and evidence remain unchanged.

```python
from aasm import GovernanceBudgetPolicy, GovernanceContext

engine.configure_governance_budget(GovernanceBudgetPolicy(
    soft_governance_token_ratio=.35,
    hard_governance_token_ratio=.75,
    min_total_tokens_for_ratio_enforcement=50_000,
))

decision = engine.governance_decide(GovernanceContext(
    action_class="architecture_choice",
    scope="backend",
    action_signature="sha256:...",
    assumption_revision="A17",
    evidence_revision="E42",
))
```

The result controls **whether another model review is required**, not whether execution is authorized. Sandbox policy, authority policy, credentials, network rules, effect authorization/idempotency, and destructive-operation guards remain independent boundaries.

Hard governance-budget exhaustion returns `BUDGET_PAUSE`; AASM never turns an exhausted review budget into silent approval. Soft pressure can suggest a lower-cost eligible reviewer. Ratio thresholds wait for a minimum usage sample so early 100%-governance ratios do not prematurely stop productive work.

`governance_report()` exposes deterministic bypasses, reused reviews, budget state, and conservative avoided-token/cost estimates derived from the run's observed average permission-review call when one exists.

See [`docs/GOVERNANCE_ECONOMICS.md`](docs/GOVERNANCE_ECONOMICS.md) and [`examples/governance_economics.py`](examples/governance_economics.py).

### Executable Planner / Builder / Verifier

v0.13 makes the Planner/Builder pattern executable and adds an explicit Verifier role. Builders produce work, Verifiers inspect it and recommend a response, and only the registered Planner can commit the authoritative control directive or change the plan.

The runtime control vocabulary is exactly:

```text
CONTINUE | REPAIR | INVESTIGATE | PAUSE | PLAN_INTERRUPT
```

`PLAN_INTERRUPT` is the only directive allowed to mutate the plan and requires an explicit plan patch. AASM validates the patch against a copy of the graph before incrementing the durable plan revision, so an invalid or cyclic update cannot half-apply.

`PBVCoordinator` automates the physical handoff:

```text
BuilderOutput → Verifier → VerifierReport → Planner → PlannerDecision
```

The Verifier and Planner may be Codex/Responses agents, other providers, remote services, deterministic code, or humans. Planner overrides remain linked to the source Verifier report.

See [`docs/EXECUTABLE_PBV.md`](docs/EXECUTABLE_PBV.md) and [`examples/pbv_cycle.py`](examples/pbv_cycle.py).

### Massive collaboration scheduler

v0.14 makes worker fan-out an explicit scheduling decision rather than a synonym for "spawn more agents." `CollaborationPlanner` combines the durable plan graph with the capability scheduler to determine how many concurrent workers can actually reduce completion time.

```python
from aasm import CollaborationPolicy

analysis = engine.analyze_collaboration(policy=CollaborationPolicy(
    max_workers=128,
    coordination_overhead_per_extra_worker=.05,
    min_relative_improvement=.02,
    near_optimal_tolerance=.02,
))

print(analysis["recommended_workers"])
print(analysis["bottlenecks"])
```

The useful ceiling is constrained by runnable task count, DAG parallel width, physical enabled capacity, and capability-eligible max-flow capacity. Candidate worker counts are evaluated against the critical path, total work, and coordination overhead. AASM chooses the smallest team in the near-optimal projected-makespan band.

This means 100 available workers can legitimately produce a recommendation of 1 when the plan is serial, 0 when capabilities cannot satisfy the task set, or a smaller intermediate number when coordination overhead erases the marginal speedup.

The result is scheduling evidence only. v0.14 does not silently provision workers or infrastructure.

```bash
aasm collaboration MACHINE_ID --store runs.db --policy collaboration-policy.json
```

See [`docs/MASSIVE_COLLABORATION.md`](docs/MASSIVE_COLLABORATION.md) and [`examples/massive_collaboration.py`](examples/massive_collaboration.py).

### Information-change checkpoints and additive steering

v0.15 maps changed information onto the plan instead of restarting everything. `ChangeSignal` can represent user steering, assumption/evidence changes, failed verification, contradictions, risk escalation, or external dependency changes.

When a signal names `seed_nodes`, AASM computes the downstream dependency closure, durably pauses only that affected region, releases affected active leases, and leaves unrelated active work untouched. Paused tasks cannot be claimed until the Planner resolves them.

```python
from aasm import ChangeKind, ChangeSignal

impact = engine.analyze_change(ChangeSignal(
    ChangeKind.USER_STEERING,
    "also support FreeCAD",
    seed_nodes=["cad-adapter"],
))

print(impact["affected_nodes"])
print(engine.paused_tasks())
```

Unanchored changes still require Planner attention but do not falsely invalidate the whole graph. Resolution is incremental: the authoritative Planner may resume repaired nodes while unresolved descendants remain paused. v0.15 checks the canonical stored pause set before and after task claim, and the pause path releases newly visible affected leases, preventing stale worker processes from successfully taking newly paused work.

The existing `user_interrupt()` API remains compatible; supplying `metadata={"seed_nodes": [...]}` automatically records the steering event and creates a selective impact checkpoint.

```bash
aasm change-analyze MACHINE_ID --store runs.db --signal change.json
aasm change-control MACHINE_ID --store runs.db
```

See [`docs/INFORMATION_CHANGE_CHECKPOINTS.md`](docs/INFORMATION_CHANGE_CHECKPOINTS.md) and [`examples/change_impact.py`](examples/change_impact.py).

### Automatic checkpoint triggers and fleet admission

v0.16 connects verification, selective impact handling, Planner authority, collaboration analysis, and worker admission into one loop. Material Verifier signals—failed tests, changed assumptions, unexpected output, or blocking findings—can automatically create a `ChangeSignal` and selective checkpoint.

The PBV Planner receives that trigger and affected region in the same handoff. A Planner decision may explicitly resolve part of the checkpoint through `metadata.resolve_impact`; unresolved descendants remain paused.

Fleet control is opt-in. When enabled, AASM re-runs collaboration analysis over runnable scheduled tasks and converts the recommended worker count into the existing durable **machine quota**. That means SQLite/PostgreSQL enforce the admission cap at the same atomic task-claim boundary used for other quotas.

```python
from aasm import FleetControlPolicy

engine.configure_fleet_control(FleetControlPolicy(enabled=True))
print(engine.fleet_control_report())
```

Automatic fleet refresh can run after a triggered checkpoint, Planner `PLAN_INTERRUPT`, or change resolution. Paused, completed, and pruned work is excluded from the runnable set before recalculation.

Fleet control does not provision machines, model sessions, or cloud resources and does not grant deployment authority. It only limits how much already-registered execution capacity may hold active leases concurrently.

See [`docs/AUTOMATIC_CHECKPOINTS_FLEET_CONTROL.md`](docs/AUTOMATIC_CHECKPOINTS_FLEET_CONTROL.md) and [`examples/automatic_checkpoint_fleet.py`](examples/automatic_checkpoint_fleet.py).

### Physical fleet provisioning and live execution telemetry

v0.17 adds the physical-lifecycle layer without collapsing scheduling into deployment authority. `plan_fleet_provisioning()` compares a desired fleet target with registered ACTIVE workers and emits provider-neutral `PROVISION` or idle-worker `DRAIN` requests.

Provisioning remains an external side effect:

```text
collaboration recommendation
        ↓
optional fleet admission quota
        ↓
provisioning plan
        ↓
proposed EffectSpec
        ↓
explicit authorization
        ↓
ProvisioningAdapter
        ↓
provider result
        ↓
worker must still register + heartbeat
```

A control plane can receive a `ProvisioningRegistry` containing real provider adapters. Without a matching registry/adapter, provider execution fails closed. AASM does not bundle or infer cloud credentials/provider behavior from a provider name.

Remote workers now emit `STARTED`, `COMPLETED`, and `FAILED` telemetry around every lease. Custom workers can also send `LOG`, `PROGRESS`, `ARTIFACT`, and `HEARTBEAT` records. The durable telemetry ledger is bounded; large logs and binaries should be stored externally and referenced by stable artifact IDs or URIs.

Completed telemetry provides observed task/task-class durations. When enabled, those measurements feed the next critical-path and fleet calculation unless a task locks its declared estimate with `metadata.lock_estimated_duration=true`.

```bash
aasm telemetry MACHINE_ID --store runs.db
aasm provision-plan MACHINE_ID --store runs.db --provider my-provider --resource-id coding-pool
aasm provision-propose MACHINE_ID --store runs.db --request provision.json
```

See [`docs/FLEET_PROVISIONING_TELEMETRY.md`](docs/FLEET_PROVISIONING_TELEMETRY.md) and [`examples/provisioning_telemetry.py`](examples/provisioning_telemetry.py).

### Provider adapters, external artifacts, and worker controls

v0.18 makes the physical-fleet layer more operational while keeping its boundaries explicit.

`CommandProvisioningAdapter` accepts caller-supplied argv construction and never executes a shell string. `KubernetesScaleAdapter` is the first concrete provider-specific adapter: it reads the current replica count for a named Kubernetes workload and issues explicit `kubectl scale` argv. It is still reachable only through an already-authorized provisioning effect.

Large text logs and artifacts can move out of the bounded machine snapshot through `ArtifactBackend`. The built-in `MemoryArtifactBackend` is useful for tests; `LocalDirectoryArtifactBackend` persists text beneath one configured root and returns stable content-addressed refs while sanitizing path components.

```python
from aasm import LocalDirectoryArtifactBackend

backend = LocalDirectoryArtifactBackend("./.aasm-artifacts", "local")
item = engine.store_text_artifact(
    backend,
    backend_name="local",
    namespace=engine.snapshot.machine_id,
    name="worker-log",
    text="...",
)
print(item["ref"])
```

Worker lifecycle is now an explicit durable control surface:

```text
DRAIN   → stop new claims; allow active lease to finish
RESUME  → return worker to ACTIVE admission
OFFLINE → stop new claims and release active leases
```

Each action records actor, reason, previous/new status, and released lease IDs. Taking an AASM worker offline does **not** delete its VM/pod/process; physical teardown remains a separate provisioning effect with its own authorization.

```bash
aasm execution-controls MACHINE_ID --store runs.db
aasm worker-control MACHINE_ID --store runs.db --worker worker-7 --action DRAIN --actor operator --reason maintenance
aasm artifacts MACHINE_ID --store runs.db
```

The Control Center exposes authenticated Drain/Resume/Offline actions through the same bearer-protected runtime endpoints.

See [`docs/PROVIDER_ADAPTERS_ARTIFACTS_CONTROLS.md`](docs/PROVIDER_ADAPTERS_ARTIFACTS_CONTROLS.md) and [`examples/provider_artifacts_controls.py`](examples/provider_artifacts_controls.py).

## Orchestration profiles

AASM ships with multiple profiles to demonstrate that governance and role structure are independent of the core runtime:

- [`single_agent.yaml`](profiles/single_agent.yaml) — one agent with bounded autonomy
- [`planner_builder.yaml`](profiles/planner_builder.yaml) — executable Planner / Builder / Verifier with Planner-owned plan authority
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

**Current version: `0.18.0` — early-stage / experimental.**

The runtime now includes event-sourced state, SQLite and PostgreSQL durability, persisted checkpoints, crash/restart recovery, durable external effects, declarative machines, static model checking, historical replay/forking, durable planning and DP memory, evidence lineage, capability-aware scheduling, crash-safe worker leases/quotas, remote multi-host execution, static model-strength/cost routing, real OpenAI/Codex executor adapters, end-to-end executor orchestration, evaluated-outcome adaptive model routing, governance-review budgets/reuse, executable Planner/Builder/Verifier orchestration, evidence-based massive-collaboration planning, selective information-change checkpointing/additive steering, automatic Verifier checkpoint triggers, opt-in collaboration-driven fleet admission, authority-gated physical provisioning, live observed-duration telemetry, provider-specific Kubernetes/command adapters, external artifact references/backends, durable worker lifecycle controls, an authenticated browser Control Center, and cache-adjusted model economics.

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