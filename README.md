<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, humans, models, and real work.**

AASM keeps probabilistic reasoning inside explicit machine authority: state is durable, transitions are legal or illegal, plans are graphs, effects require authorization, evidence governs commitment, contradictions become learned constraints, and use-case behavior arrives through domain-neutral profile packages rather than being baked into the kernel.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.22.0%20experimental-orange)](ROADMAP.md)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[**Quick start**](#quick-start) · [**Profile packages**](#profile-packages) · [**Formal calculus**](#formal-conflict-learning-calculus) · [**Capabilities**](#capabilities) · [**Architecture**](#architecture) · [**Downloads**](#downloads)

</div>

---

## What is AASM?

Most agent frameworks concentrate on giving a model tools. AASM focuses on the systems question underneath them:

> **How do you govern what an intelligent system is allowed to do next, preserve what happened, recover selectively, coordinate real work, and improve future decisions when execution contradicts the plan?**

AASM is a Python runtime, CLI, durable event model, and control plane. It provides:

- explicit machine states and legal transitions;
- event-sourced replay, checkpoints, and historical forks;
- SQLite and PostgreSQL persistence;
- graph planning, dependency-aware scheduling, and DP memory;
- durable evidence, assumptions, observations, contradictions, and lineage;
- external-effect proposal, authorization, idempotency, and reconciliation;
- distributed workers, heartbeats, leases, quotas, and canonical task claims;
- model capability, strength, context, latency, cost, and outcome routing;
- optional Planner / Builder / Verifier orchestration;
- selective information-change checkpoints and additive steering;
- collaboration analysis, fleet admission, mission controls, telemetry, artifacts, CLI, API, and browser Control Center;
- a formal decision/obligation calculus with conflict learning;
- domain-neutral profile packages and independent adapter contracts.

The operating principle is:

> **Models propose. Algorithms organize. Policy authorizes. Evidence validates. Contradictions teach. Durable state governs what happens next.**

---

## Profile packages

AASM v0.22 separates the domain from the kernel.

```text
profile package
    vocabulary · adapters · validators · policies · migrations
                              ↓
                       stable contracts
                              ↓
AASM kernel
    state · authority · evidence · effects · constraints
    locks · fairness · backjumping · restart · replay
```

The domain says what a decision, obligation, result, or artifact **means**. AASM decides what that information is **allowed to change**.

### Package, profile, binding, run

These are different objects:

| Object | Meaning |
|---|---|
| **Package** | A distributable artifact containing one or more profiles, optional adapters, schemas, migrations, documentation, examples, and tests. |
| **Profile** | A versioned use-case contract inside a package: vocabulary, evidence kinds, policies, machine definition, and adapter bindings. |
| **Binding** | The exact immutable profile version, fingerprint, package identity, and user configuration attached to one AASM machine. |
| **Run** | The actual event-sourced execution history governed by that binding. |

Users, teams, AASM maintainers, or third parties can create packages for a use case. A package might represent a research protocol, design workflow, operations process, hardware-validation flow, document-production system, or any other domain that can express decisions, obligations, evidence, and results.

### Is package design an art form?

Yes—more precisely, it is an engineering and design craft.

A package author chooses:

- which decisions deserve explicit names;
- which obligations are persistent or conditional;
- what counts as adequate evidence;
- how conflicts should be explained;
- when a learned constraint may become hard;
- what belongs in a reusable profile versus one run's configuration;
- how older bindings migrate to a new contract.

Different packages can encode different philosophies for the same use case. AASM does not impose one ontology. It enforces identity, authority, persistence, provenance, conformance, and migration rules around whichever profile is selected.

### Do packages naturally evolve?

They can evolve, but **not by silently rewriting themselves**.

```text
repeated evidence or conflicts
          ↓
ProfileEvolutionProposal
          ↓
new package/profile version is authored
          ↓
conformance and domain validation
          ↓
explicit ProfileMigration
          ↓
authorized activation
          ↓
new immutable binding
```

A run naturally adapts inside a stable profile: decisions change, obligations enable or lock, conflicts create learned constraints, and search can backjump or restart.

Changing the profile contract is different. It requires a new semantic version, fingerprint, conformance result, migration, and explicit activation. This preserves replay: an old history always retains the exact rules under which it was created.

Run configuration can change without creating a new package version. A threshold, site list, budget, or reporting option is configuration. Changing the meaning of an obligation, evidence policy, decision namespace, or adapter contract is package evolution.

See [`docs/PROFILE_PACKAGES.md`](docs/PROFILE_PACKAGES.md) and [`docs/EXTENSION_CONTRACT.md`](docs/EXTENSION_CONTRACT.md).

### Built-in profiles

AASM ships two domain-neutral profiles:

- **`aasm.bare`** — minimal binding when the surrounding application already owns domain interpretation;
- **`aasm.evolve`** — iterative modeling, conditional work, verification, conflict learning, repair, investigation, backjumping, and restart without assuming a domain.

External Python distributions can advertise installed profiles through:

```toml
[project.entry-points."aasm.profiles"]
standard = "my_package:standard_profile"
high_assurance = "my_package:high_assurance_profile"
```

Discovery loads only already-installed entry points. AASM never downloads or installs code as a side effect of profile discovery.

---

## Formal conflict-learning calculus

AASM v0.21 introduced the production calculus that v0.22 packages extend.

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

The calculus maintains three linked views:

```text
Decision Graph
    what was selected, under which assumptions, and why

Obligation Graph
    what must eventually be enabled, satisfied, rejected,
    superseded, or proven impossible

Evidence Graph
    what observations support, contradict, verify, or invalidate
    decisions and completion claims
```

A validated incompatibility becomes a guarded no-good:

```text
guard ⇒ NOT (assumption₁ AND assumption₂ AND ... AND assumptionₙ)
```

Only validated or proven assumption conflicts may become hard constraints. Evidence disagreement and heuristic explanations remain soft.

Backjumping follows causal dependency rather than reverse creation order. Model-relative locks suppress work without deleting it. Cross-model fairness prevents persistent obligations from remaining hidden forever. `restart_search()` abandons speculative assignments while retaining verified work, evidence, conflicts, constraints, effects, mission state, leases, replay, and fork provenance.

See [`docs/FORMAL_CALCULUS.md`](docs/FORMAL_CALCULUS.md).

---

## Domain-neutral adapter contracts

A package can independently provide any of five optional adapters:

```text
DecisionBackend
    proposes a CandidateModel

ObligationAdapter
    proposes obligations enabled by a model

SemanticValidator
    evaluates concrete evidence

ConflictExplainer
    proposes a causal explanation

ConstraintCertifier
    assigns a justified trust level to a projected constraint
```

No adapter can directly mutate AASM state, activate a decision, commit an obligation, authorize an effect, or install a hard constraint.

Decision backends are solver-neutral. They may use deterministic rules, enumeration, SAT, SMT, CP-SAT, MILP, heuristic search, an LLM, a human, or a portfolio. Before activation, the kernel validates identity, parent decisions, pinned assignments, hard learned constraints, profile namespaces, and fairness.

The generic semantic-result envelope supports:

```text
PASS
LOCAL_DEFECT
INFORMATION_GAP
ASSUMPTION_CONFLICT
EVIDENCE_CONFLICT
POLICY_CONFLICT
FATAL
```

It can carry claims, observations, evidence, artifacts, scope, confidence, and proposed conflict information without forcing one domain ontology.

---

## Capabilities

| Capability | What AASM provides |
|---|---|
| **State machine** | Explicit legal transitions, terminal states, replay, declarative definitions, and structural model checking. |
| **Durable cognition** | Plan graph, frontier, visited/pruned state, DP memory, evidence, assumptions, contradictions, and provenance. |
| **Formal calculus** | Named decisions, conditional obligations, locks, conflicts, explanations, learned no-goods, backjumping, fairness, and restart. |
| **Profile packages** | Versioned domain contracts, package manifests, fingerprints, bindings, adapters, conformance, and migrations. |
| **Semantic results** | One durable, fingerprinted envelope for validators, tools, simulations, humans, and agents. |
| **External effects** | Proposal, authorization, attempt ownership, idempotency, `FAILED` versus `UNKNOWN`, and reconciliation. |
| **Resource scheduling** | Capability-aware allocation, priorities, quotas, max-flow/min-cut evidence, and unmet demand. |
| **Distributed execution** | PostgreSQL-backed workers, heartbeats, leases, expiry, reclaim, and canonical ownership. |
| **Model routing** | Capability, strength, context, latency, cost, concurrency, and evaluated task-class outcomes. |
| **Planner / Builder / Verifier** | Optional executable protocol with Planner-only plan authority. |
| **Selective steering** | Changed information pauses only the affected dependency closure. |
| **Collaboration and fleet** | Critical path, parallel width, coordination overhead, admission limits, and explicit provisioning effects. |
| **Mission control** | Durable `QUIESCE`, `SUSPEND`, and `RESUME` independent of plan, worker, and machine state. |
| **Observability** | Telemetry, `LEASE_LOST`, external artifact references, bounded previews, CLI/API, and Control Center. |

---

## Architecture

```mermaid
flowchart TD
    U[User / Event / Goal] --> B[Profile Binding]
    B --> S[AASM Durable State]
    S --> P[Decision Backend or Human]
    P --> K[Kernel Candidate Validation]
    K --> A[Authority and Governance]
    A --> R[Resource and Model Routing]
    R --> W[Workers / Agents / Tools / Humans]
    W --> E[Semantic Result / Evidence / Artifacts]
    E --> V[Verifier]
    V -->|accepted| C[Commit]
    V -->|local defect| X[Selective Repair]
    V -->|information gap| I[Investigate]
    V -->|contradiction| F[Conflict Explanation]
    F --> L[Learn Constraint]
    L --> J[Backjump / Restart]
    X --> P
    I --> P
    J --> P
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
 model    tool/sim   human
 worker    worker    reviewer
```

The LLM is **inside** the machine. It is not the machine.

---

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

### Inspect built-in profiles

```bash
aasm profiles
aasm profile-describe aasm.evolve
aasm profile-conformance profiles/evolve/profile.json \
  --package profiles/evolve/package.json
```

### Bind a profile

```python
from aasm import AASMEngine, ProblemSpec, evolve_profile

engine = AASMEngine(ProblemSpec("Carry out a verified multi-step objective"))
engine.bind_profile(
    evolve_profile(),
    configuration={"review_mode": "strict"},
    actor="owner",
)
print(engine.profile_report())
```

### Create a use-case profile

```python
from aasm import AASMProfile, ProfileEvolutionPolicy

profile = AASMProfile(
    profile_id="example.field-study",
    profile_version="1.0.0",
    description="Evidence contract for a repeatable field study.",
    decision_namespaces=["method"],
    obligation_kinds=["measurement", "review", "work"],
    evidence_kinds=["measurement", "observation", "human_attestation"],
    artifact_kinds=["physical", "record"],
    evolution_policy=ProfileEvolutionPolicy(mode="PROPOSAL_ONLY"),
)
```

### Solver-neutral candidate validation

```python
from aasm import CandidateModel

candidate = CandidateModel(
    candidate_id="candidate-7",
    assignments={"method.schedule": "decision-soil-triggered"},
    backend_id="human-review",
    backend_version="1",
)
report = engine.validate_candidate_model(candidate)
assert report.valid, report.errors
```

### Record a semantic result

```python
from aasm import ProducerRef, SemanticResultEnvelope

engine.record_semantic_result(SemanticResultEnvelope(
    result_id="measurement-week-1",
    producer=ProducerRef("human", "field-team", version="1"),
    subject_ids=["obligation-measure"],
    classification="PASS",
    summary="The scheduled measurements were recorded.",
    evidence=[{"kind": "measurement", "ref": "field-log-week-1"}],
))
```

A complete non-software example is in [`examples/domain_profile_field_study.py`](examples/domain_profile_field_study.py).

### CLI surfaces

```bash
aasm profile MACHINE_ID --store runs.db
aasm profile-bind MACHINE_ID --store runs.db --profile aasm.evolve
aasm decision-request MACHINE_ID --store runs.db
aasm candidate-validate MACHINE_ID --store runs.db --candidate candidate.json
aasm semantic-result-validate result.json
aasm semantic-result-record MACHINE_ID --store runs.db --result result.json
aasm semantic-results MACHINE_ID --store runs.db
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

Open `/ui` for the Control Center.

---

## Use cases

Because profiles are external to the kernel, AASM can support many use cases without redefining core semantics:

- autonomous and human-guided software engineering;
- research protocols and evidence synthesis;
- CAD, hardware, simulation, and manufacturing workflows;
- laboratory and field experiments;
- document, policy, and publication production;
- operations, approvals, and compliance processes;
- long-running multi-model or multi-worker missions;
- any workflow where decisions, obligations, evidence, effects, and recovery must remain explicit.

---

## Project structure

```text
src/aasm/       runtime, calculus, profile contracts, stores, workers, control plane
profiles/       built-in and example profile packages
schemas/        machine-readable contracts
docs/           architecture, subsystem, package, and release guides
examples/       runnable examples across multiple kinds of work
tests/          unit, durability, conformance, remote, and integration coverage
SKILL.md        operating contract for Codex and other agents
```

## Non-goals

The core does not require:

- Planner / Builder / Verifier;
- SAT or SMT;
- an LLM or a particular provider;
- GitHub or a source repository;
- one evidence ontology or artifact type;
- one user interface or worker topology;
- automatic package installation;
- silent package self-evolution.

AASM improves control, provenance, and recovery. It does not make an underlying model, validator, simulation, or human judgment correct.

---

## Downloads

- **[Download source ZIP](https://github.com/halthinks/AASM/archive/refs/heads/main.zip)**
- **[Download source TAR.GZ](https://github.com/halthinks/AASM/archive/refs/heads/main.tar.gz)**
- Clone: `git clone https://github.com/halthinks/AASM.git`

AASM is currently **v0.22.0 / experimental**. The `main` archives track current development.

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/FORMAL_CALCULUS.md`](docs/FORMAL_CALCULUS.md)
- [`docs/PROFILE_PACKAGES.md`](docs/PROFILE_PACKAGES.md)
- [`docs/EXTENSION_CONTRACT.md`](docs/EXTENSION_CONTRACT.md)
- [`docs/RELEASE_0.22.md`](docs/RELEASE_0.22.md)
- [`ROADMAP.md`](ROADMAP.md)

## Contributing

Contributions are welcome, including profile packages, adapters, conformance fixtures, validators, solver backends, formal properties, documentation, and core-runtime improvements.

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md), [`GOVERNANCE.md`](GOVERNANCE.md), [`SECURITY.md`](SECURITY.md), and [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Design principles

1. **Explicit over implicit.** Important state belongs in machine-readable structures.
2. **Authority is separate from capability.** Being able to act does not grant permission to redefine state.
3. **Evidence before commitment.** Important claims remain inspectable and challengeable.
4. **Domains extend; the kernel governs.** Use-case meaning belongs in packages, not hard-coded core branches.
5. **Profiles are immutable contracts.** Evolution creates a new version and migration, never an invisible rewrite.
6. **Contradictions should become knowledge.** Trustworthy failure restricts future search instead of creating blind retry loops.
7. **Reversible where possible.** Backjump and restart preserve unrelated work and durable knowledge.
8. **Algorithms before blind spawning.** Dependency, capacity, cost, and evidence determine whether more agents help.
9. **Provenance is a feature.** A run remains understandable after restart, repair, migration, or fork.
10. **No fake determinism.** AASM constrains authority and control flow; it does not pretend probabilistic outputs are infallible.

## Acknowledgements

AASM's algorithmic mapping was inspired by Jeff Erickson's open educational materials on algorithms and models of computation. The formal-calculus direction is informed by formal verification, saturation theorem proving, AVATAR-style splitting, labelled splitting, conflict-driven clause learning, non-chronological backjumping, restart policies, and fairness under changing abstract models.

AASM's implementation and agent-runtime interpretation are original.

## License

AASM is released under the [MIT License](LICENSE).

---

<div align="center">

**Define the contract. Preserve the evidence. Learn from contradiction. Keep authority explicit.**

</div>
