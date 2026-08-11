# AASM Roadmap

AASM is currently **v0.27.0 / experimental**.

The current program is **Adoption and Operability**: make the deterministic kernel, formal calculus, assurance system, and observability understandable, runnable, distributable, and operable by people who did not build them.

This roadmap is an execution contract. Every release has an observable user outcome and an exit gate.

## Program rule: extend the working path

Adoption work must use the implementation proven through v0.27.0:

```text
public AASM API
    → existing event/reducer runtime
    → existing Memory / SQLite / PostgreSQL stores
    → existing calculus and assurance boundary
    → existing worker, lease, effect, and mission-control paths
    → existing observability projections
    → existing CLI / HTTP / Control Center surfaces
```

The program must not create a parallel runtime, alternate authority path, duplicate event model, private database mutation path, replacement Control Center, or reference-only orchestration loop.

## Release sequence

| Release | Primary outcome | Status |
|---|---|---|
| **v0.25.2** | Canonical adoption API and implementation contract | Completed |
| **v0.26.0** | Research Synthesis Hero Stack | Completed |
| **v0.27.0** | One-command PostgreSQL, worker, runtime, and Control Center stack | **Current — implemented** |
| **v0.28.0** | Clean distribution and tested operator runbooks | Next |
| **v0.29.0** | Thin LangGraph adapter and incremental-adoption example | Planned |

---

# v0.27.0 — One-Command Local Full Stack

## Objective

Make first contact operational rather than instructional.

## Delivered topology

```text
Docker Compose
├── PostgreSQL 17
├── canonical bootstrap service
├── AASM HTTP runtime
├── existing Control Center
├── one default deterministic worker
├── optional second worker
├── live setup reference machine
└── completed reference machine
```

## Delivered commands

```bash
# Start everything
docker compose up --build

# Inspect stack state
docker compose run --rm stackctl status

# Non-destructive reset to a fresh canonical machine
docker compose run --rm stackctl fresh

# Create a completed trajectory
docker compose run --rm stackctl complete

# Exact durable-history and replay verification
docker compose run --rm stackctl verify --selection completed

# Full readiness check
docker compose run --rm stackctl check
```

## Delivered behavior

- ✅ PostgreSQL-backed multi-process persistence;
- ✅ one-shot bootstrap through `run_research_synthesis_demo()`;
- ✅ live setup machine stopped before the known contradiction;
- ✅ completed machine containing conflict learning, certificate verification, causal backjump, steering, provenance, and replay;
- ✅ existing HTTP runtime and Control Center;
- ✅ transparent local demo authentication while preserving the non-loopback token rule;
- ✅ stack discovery through authenticated `GET /demo-stack`;
- ✅ automatic Control Center selection of the current machine;
- ✅ deterministic worker using the existing registration, heartbeat, claim, lease, telemetry, and completion APIs;
- ✅ optional second worker through a Compose profile;
- ✅ non-destructive `fresh` semantics that retain prior machine histories;
- ✅ explicit destructive volume reset through Docker Compose;
- ✅ Python/SQLite stack tests and Docker Compose smoke tests;
- ✅ README, release, architecture, changelog, and version visibility.

## Exit gate

v0.27.0 is complete when:

1. `docker compose up --build` starts PostgreSQL, bootstrap, runtime, and the default worker;
2. `http://localhost:8787/` loads the existing Control Center and selects the live setup machine;
3. the completed reference machine is immediately inspectable;
4. the worker completes a task through the existing remote lease path;
5. `stackctl fresh` creates a new setup machine without deleting prior history;
6. `stackctl verify` reports a valid durable history and equal replay/persistence hashes;
7. the optional second worker can join without changing the machine model;
8. no service directly mutates AASM database tables or snapshots;
9. Python 3.11–3.13, PostgreSQL, Control Center JavaScript, Compose smoke, TLA+, and SPIN gates are green.

---

# v0.28.0 — Distribution and Operator Readiness

## Objective

Make AASM dependably installable and operable under common failure conditions.

## Distribution work

- annotated release tags for the maintained release line;
- GitHub releases with immutable source and wheel artifacts;
- PyPI publication as `aasm-runtime`;
- primary user path: `pip install aasm-runtime`;
- editable contributor path clearly separated;
- CI build, install, and smoke test against the wheel rather than only the checkout;
- compatibility and deprecation policy linked from the README;
- release checksums and reproducible artifact inventory.

## Operator runbooks

Short imperative runbooks, each backed by an executable scenario test:

- recover after lease loss;
- inject a requirement without destroying the plan;
- inspect and act on a learned no-good;
- operate a human approval gate with policy as data;
- safely replay and fork a machine;
- reconcile an `UNKNOWN` external effect without guessing;
- diagnose a failed durable-history verification.

## Exit gate

A clean environment can install AASM without vendoring the repository, and every documented recovery procedure is exercised in CI.

---

# v0.29.0 — Incremental Framework Adoption

## Objective

Let an existing team keep its current orchestration framework while placing AASM underneath it as durable authority and recovery infrastructure.

## First adapter: LangGraph

The adapter must remain thin:

1. map one LangGraph thread/run to one AASM machine;
2. record selected decisions and results as AASM state and evidence;
3. require AASM authorization before declared external effects;
4. return AASM recovery outcomes to the existing graph.

It must not translate every private framework object into a new ontology, create a second scheduler, or bypass the canonical adoption contract.

## Required comparison

The same task runs:

- once as an ordinary LangGraph workflow;
- once with AASM underneath it.

The comparison shows what was retained, invalidated, learned, replayed, and made inspectable after the same injected contradiction.

---

# Completed adoption foundation

## v0.25.2 — Canonical Adoption Contract

- ✅ machine-readable `aasm.adoption.v1` contract;
- ✅ supported imports, engine methods, CLI commands, inspection surfaces, and HTTP endpoints;
- ✅ separate package/runtime and remote-protocol identities;
- ✅ explicit `SUPPORTED`, `EXPERIMENTAL`, and `INTERNAL` meanings;
- ✅ rule prohibiting parallel authority, reducer, and persistence paths.

## v0.26.0 — Research Synthesis Hero Stack

- ✅ `aasm.research-synthesis@1.0.0` finished profile;
- ✅ fixed offline synthetic corpus with SHA-256 manifest;
- ✅ known contradiction and known corrected model;
- ✅ Decision, Obligation, and Evidence trajectory;
- ✅ soft learning, independent certification, and hard promotion;
- ✅ non-chronological backjump and repeated-failure blocking;
- ✅ unrelated work preservation;
- ✅ mid-run requirement injection and conditional lock restoration;
- ✅ claim-level provenance artifact;
- ✅ exact full-history replay;
- ✅ human-readable Control Center reasoning views;
- ✅ empirical `WHY_AASM.md` baseline comparison.

---

# Adoption scorecard

The program is substantially complete when:

| Measure | Gate |
|---|---:|
| Clone to healthy dashboard | under 5 minutes |
| Clone to understandable completed demonstration | under 10 minutes |
| Required external API keys | 0 |
| Commands before first useful result | no more than 3 |
| Reference replay | exact final snapshot/hash match |
| Injected contradiction | visible in UI and history |
| Learned no-good | visible and reused |
| Backjump | causal target shown |
| Unrelated work | demonstrably preserved |
| Mandatory unresolved obligations at completion | 0 |
| Fresh reset | one command and non-destructive by default |
| Published-wheel smoke test | required in v0.28 CI |
| Runbook scenario tests | required in v0.28 CI |
| Incremental framework path | required in v0.29 |

---

# Delivered technical foundation

## Deterministic control plane

- explicit machine state and legal transitions;
- declarative machine definitions and structural model checking;
- event-sourced durability, checkpoints, replay, and historical forks;
- SQLite and PostgreSQL coordination;
- external-effect authorization, idempotency, ownership, `UNKNOWN` outcomes, and reconciliation;
- mission `QUIESCE`, `SUSPEND`, and `RESUME`.

## Planning, evidence, and distributed execution

- plan graphs, checkpoint backtracking, and DP memory;
- claims, observations, assumptions, contradictions, invalidation, and lineage;
- capability scheduling and resource-flow evidence;
- workers, heartbeats, leases, expiry, reclaim, and stale-result rejection;
- model routing, adaptive outcomes, economics, and governance budgets;
- optional Planner / Builder / Verifier protocol;
- selective information-change checkpoints and additive steering;
- fleet admission, provisioning adapters, telemetry, artifacts, CLI/API, and Control Center.

## Formal calculus and assurance

- durable Decision, Obligation, and Evidence calculus;
- conditional obligations and model-relative locks;
- first-class conflicts and causal explanations;
- guarded hard/soft learned no-goods;
- graph-directed non-chronological backjumping;
- knowledge-preserving restart;
- bounded cross-model fairness;
- profile packages, fingerprints, conformance, and migrations;
- replaceable decision backends with budgets and atomic activation;
- exact projection certificates and independent verification;
- reducer-based durable-history verification;
- conflict-core minimization;
- bounded TLA+ and Promela/SPIN assurance models;
- closed generic observability and causal graphs.

---

# Post-adoption architecture backlog

The following work remains valuable, but it follows the adoption program rather than displacing it.

## Trust distribution

- signed package and backend manifests;
- package-registry protocol separating discovery from installation and activation;
- trust policies for profile, backend, validator, and certifier identities;
- reproducible package build provenance;
- migration dry-run reports.

## Hierarchical reasoning

- explicit strategy, architecture, implementation, and execution layers;
- cross-layer conflict projection and backjump targets;
- scoped learned-knowledge promotion;
- hierarchical fairness and obligation inheritance;
- portfolio search across abstraction layers.

## Deeper production conformance

- trace-conformance harness between the Python reducer and formal abstraction;
- expanded formal coverage for effects, profile migration, leases, and distributed ownership;
- signed history-check reports and externally verifiable snapshots;
- generated/property-based command sequences across live execution and replay.

---

# Non-goals for the core

AASM should not become:

- a bundled LLM provider;
- a domain-specific application;
- a package installer that downloads executable code during discovery;
- a mandatory Planner/Builder system;
- a mandatory SAT/SMT system;
- a monolith that forces one evidence ontology, UI, or agent topology;
- a self-modifying package system without explicit versioning and migration.

The core remains a role-agnostic, domain-neutral deterministic control plane with explicit extension contracts.
