# AASM Roadmap

AASM is currently **v0.25.2 / experimental**.

The immediate program is **Adoption and Operability**: make the existing deterministic kernel, formal calculus, assurance system, and observability understandable, runnable, distributable, and operable by people who did not build them.

This roadmap is an execution contract, not a list of aspirational features. Every release below has an observable user outcome and an exit gate.

## Program rule: extend the working path

Adoption work must use the implementation already proven in v0.25.1:

```text
public AASM API
    → existing event/reducer runtime
    → existing stores
    → existing calculus and assurance boundary
    → existing observability projections
    → existing CLI / HTTP / Control Center surfaces
```

The program must not create a parallel runtime, alternate authority path, duplicate event model, private database mutation path, replacement Control Center, or reference-only orchestration loop.

## Release sequence

| Release | Primary outcome | Status |
|---|---|---|
| **v0.25.2** | Canonical adoption API and implementation contract | **Current — Step 1 executed** |
| **v0.26.0** | Research-synthesis hero application and finished research profile | Next |
| **v0.27.0** | One-command PostgreSQL/worker/Control Center demo stack | Planned |
| **v0.28.0** | Clean distribution and tested operator runbooks | Planned |
| **v0.29.0** | Thin LangGraph adapter and incremental-adoption example | Planned |

## v0.25.2 — Canonical Adoption Contract

### Objective

Give reference applications, adapters, documentation, and operator tooling one supported path through AASM instead of forcing each adopter to infer which of the many exported capabilities is canonical.

### Implemented

- ✅ package-level runtime version and separate remote-protocol identity;
- ✅ machine-readable `aasm.adoption.v1` public API contract;
- ✅ supported top-level imports and `AASMEngine` method inventory;
- ✅ supported CLI command, inspection-surface, and HTTP endpoint inventory;
- ✅ explicit `SUPPORTED`, `EXPERIMENTAL`, and `INTERNAL` compatibility meanings;
- ✅ `public_api_contract()` and `validate_public_api_contract()`;
- ✅ `aasm adoption-contract`;
- ✅ `GET /adoption-contract`;
- ✅ regression checks that every supported import and engine method still exists;
- ✅ architecture rule prohibiting parallel authority, reducer, and persistence paths;
- ✅ README and release-version visibility.

### Exit gate

The release is complete when:

1. the contract validates in Python, CLI, and HTTP tests;
2. package, server, README, changelog, and roadmap versions agree;
3. CI passes on Python 3.11–3.13 and PostgreSQL;
4. formal TLA+/SPIN gates remain green;
5. `main` remains the only branch and no pull request is required.

## v0.26.0 — Research Synthesis Hero Stack

### Objective

Deliver one understandable end-to-end application in which a new user can see AASM preserve truth, obligations, and unrelated work after a contradiction.

### Work packages

#### 26.1 Finished research profile

- versioned research decision vocabulary;
- persistent synthesis obligations;
- evidence kinds and evidence contracts;
- conflict-explanation policy;
- fairness defaults;
- model-routing and governance-budget defaults;
- profile conformance tests and migration fixture.

#### 26.2 Fixed offline corpus

- small redistributable literature set;
- source and license manifest;
- cryptographic hashes;
- one known causal question;
- one deliberate, reproducible contradiction;
- no required network, paid API, or model key.

#### 26.3 Canonical reference machine

The run must demonstrate:

```text
seed question
→ candidate interpretation
→ conditional obligations
→ evidence extraction
→ validated contradiction
→ causal explanation
→ learned no-good
→ non-chronological backjump
→ preservation of unrelated work
→ corrected synthesis
→ final provenance-bearing artifact
```

#### 26.4 Replay and comparison

- one-command replay with exact final snapshot/hash comparison;
- fresh-run and completed-run modes;
- empirical `WHY_AASM.md` baseline comparison;
- measurements for work retained, work invalidated, repeated failures, unresolved obligations, and claim-level provenance.

#### 26.5 Minimum browser visibility

The existing Control Center must expose enough of the current observability API to show:

- run summary;
- Decision Graph;
- Obligation Graph;
- Evidence Graph;
- conflict, learned no-good, and backjump target;
- final artifact provenance.

### Exit gate

A new technical user can run the offline example, understand the contradiction and recovery without reading the architecture documents, replay the exact trajectory, and inspect a known-good final artifact.

## v0.27.0 — One-Command Local Full Stack

### Objective

Make first contact operational rather than instructional.

### Required stack

```text
Docker Compose
├── PostgreSQL
├── AASM HTTP runtime
├── Control Center
├── one default worker
├── optional second worker
└── pre-seeded research-synthesis machine
```

### Required commands

```bash
docker compose up --build
```

must print the browser URL, reference machine identity, and health state.

The stack must also provide one-command:

- fresh deterministic run;
- completed-run inspection;
- replay verification;
- reset;
- clean shutdown.

### Exit gate

A new user reaches a healthy dashboard in under five minutes on a normal developer machine, with no external credentials and no direct database setup.

## v0.28.0 — Distribution and Operator Readiness

### Objective

Make AASM dependably installable and operable under common failure conditions.

### Distribution

- annotated `v0.25.1`, `v0.25.2`, and subsequent release tags;
- GitHub releases with immutable source and wheel artifacts;
- PyPI publication as `aasm-runtime`;
- primary user install path: `pip install aasm-runtime`;
- contributor path: editable install from the repository;
- CI installation and smoke test against the built/published wheel;
- compatibility and deprecation policy linked from the README.

### Operator runbooks

Short imperative runbooks, each backed by an executable scenario test:

- recover after lease loss;
- inject a requirement without destroying the plan;
- inspect and act on a learned no-good;
- operate a human approval gate with policy as data;
- safely replay and fork a machine;
- reconcile an `UNKNOWN` external effect without guessing;
- diagnose a failed durable-history verification.

### Exit gate

A clean environment can install the package without vendoring the repository, and every documented recovery procedure is exercised in CI.

## v0.29.0 — Incremental Framework Adoption

### Objective

Let an existing team retain its current orchestration framework while placing AASM underneath it as durable authority and recovery infrastructure.

### First adapter: LangGraph

The adapter must remain thin:

1. map one LangGraph thread/run to one AASM machine;
2. record selected decisions and results as AASM state/evidence;
3. require AASM authorization before declared external effects;
4. return AASM recovery outcomes to the existing graph.

It must not translate every private framework object into a new AASM ontology or create a second scheduler.

### Required comparison

The same task must run:

- once as an ordinary LangGraph workflow;
- once with AASM underneath it.

The comparison must show what was retained, invalidated, learned, replayed, and made inspectable after the same injected contradiction.

### Exit gate

An existing LangGraph application can adopt AASM incrementally without rewriting its agent graph or bypassing the canonical adoption contract.

## Adoption scorecard

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
| Fresh reset | one command |
| Published-wheel smoke test | required in CI |
| Runbook scenario tests | required in CI |

## Delivered foundation

### Deterministic control plane

- ✅ explicit machine state and legal transitions
- ✅ declarative machine definitions and structural model checking
- ✅ event-sourced durability, checkpoints, replay, and historical forks
- ✅ SQLite and PostgreSQL coordination
- ✅ external-effect authorization, idempotency, ownership, `UNKNOWN` outcomes, and reconciliation
- ✅ mission `QUIESCE`, `SUSPEND`, and `RESUME`

### Planning, evidence, and execution

- ✅ plan graphs, shortest paths, checkpoint backtracking, and DP memory
- ✅ claims, observations, assumptions, contradictions, invalidation, and lineage
- ✅ capability scheduling, max-flow/min-cut evidence, priorities, and quotas
- ✅ distributed workers, heartbeats, leases, expiry, reclaim, and stale-result rejection
- ✅ model routing, adaptive outcomes, economics, and governance budgets
- ✅ optional Planner / Builder / Verifier protocol and automatic handoff
- ✅ selective information-change checkpoints and additive steering
- ✅ collaboration analysis, fleet admission, provisioning adapters, telemetry, artifacts, CLI/API, and Control Center

### v0.21 — Formal calculus

- ✅ durable Decision, Obligation, and Evidence graph calculus
- ✅ conditional obligations and evidence contracts
- ✅ model-relative locks with automatic restoration
- ✅ first-class conflicts and causal explanations
- ✅ guarded hard/soft learned no-goods
- ✅ graph-directed non-chronological backjumping
- ✅ knowledge-preserving search restart
- ✅ bounded cross-model fairness and Planner-authorized recovery

### v0.22 — Domain-neutral extension contract

- ✅ versioned `AASMProfile` and `AASMPackageManifest`
- ✅ immutable fingerprints and explicit per-machine profile bindings
- ✅ separate Decision, Obligation, Validation, Explanation, and Certification adapter protocols
- ✅ solver-neutral decision requests and candidate models
- ✅ generic fingerprinted semantic-result envelope
- ✅ static package/profile conformance and optional determinism probes
- ✅ built-in `aasm.bare` and domain-neutral `aasm.evolve`
- ✅ evidence-backed evolution proposals and explicit versioned migrations

### v0.23 — Decision backend ecosystem

- ✅ deterministic finite-domain backend with incremental continuation
- ✅ human proposal backend
- ✅ provider-neutral callback/model backend
- ✅ portfolio backend with candidate deduplication and multi-source provenance
- ✅ enforced candidate, combination, cost, and latency budgets
- ✅ durable candidate lifecycle, revalidation, selection, and atomic activation
- ✅ backend registry and capability routing

### v0.24 — Formal assurance

- ✅ durable certificates and independent verification results
- ✅ exact learned-constraint projection certification
- ✅ detached SHA-256 artifact verification
- ✅ globally enforced certificate-gated hard knowledge
- ✅ reducer-based durable-history replay verification
- ✅ greedy irreducible and exact-bounded conflict-core minimization
- ✅ immutable successor explanations for adopted minimized cores
- ✅ bounded TLA+ and Promela/SPIN assurance models
- ✅ backward-compatible assurance state persistence

### v0.25 — Generic observability

- ✅ Decision Graph projection
- ✅ Obligation Graph projection
- ✅ Evidence Graph projection
- ✅ closed heterogeneous causal graph
- ✅ typed conflict, backjump, restart, profile, candidate, and assurance timelines
- ✅ actionable fairness-debt view with thresholds and lock reasons
- ✅ profile/package binding and migration history
- ✅ candidate backend and assurance summaries
- ✅ canonical-store refresh for every inspection surface
- ✅ generic `inspect_machine()` CLI and authenticated HTTP surfaces

### v0.25.1 — Stabilization

- ✅ closed inherited hard-constraint certification bypasses
- ✅ all-or-nothing candidate activation
- ✅ exact replay-versus-persistence comparison
- ✅ conflict-minimization root and budget correctness
- ✅ backend timeout and provenance diagnostics
- ✅ runtime-to-formal contract checks and complete formal workflow triggers
- ✅ human-first README and clearer architecture documentation

## Post-adoption architecture backlog

The following work remains valuable, but it follows the adoption program rather than displacing it.

### Trust distribution

- signed package and backend manifests;
- compatibility and conformance evidence attached to published packages;
- package-registry protocol separating discovery from installation and activation;
- trust policies for profile, backend, validator, and certifier identities;
- reproducible package build provenance;
- migration dry-run reports.

### Hierarchical reasoning

- explicit strategy, architecture, implementation, and execution layers;
- cross-layer conflict projection and backjump targets;
- scoped learned-knowledge promotion;
- hierarchical fairness and obligation inheritance;
- portfolio search across abstraction layers.

### Deeper production conformance

- trace-conformance harness between the Python reducer and formal abstraction;
- expanded formal coverage for effects, profile migration, leases, and distributed ownership;
- signed history-check reports and externally verifiable snapshots;
- generated/property-based command sequences across live execution and replay.

## Non-goals for the core

AASM should not become:

- a bundled LLM provider;
- a domain-specific application;
- a package installer that downloads executable code during discovery;
- a mandatory Planner/Builder system;
- a mandatory SAT/SMT system;
- a monolith that forces one evidence ontology, user interface, or agent topology;
- a self-modifying package system without explicit versioning and migration.

The core remains a role-agnostic, domain-neutral deterministic control plane with explicit extension contracts.
