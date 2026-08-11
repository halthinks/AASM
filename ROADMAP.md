# AASM Roadmap

AASM is currently **v0.26.0 / experimental**.

The immediate program is **Adoption and Operability**: make the existing deterministic kernel, formal calculus, assurance system, and observability understandable, runnable, distributable, and operable by people who did not build them.

This roadmap is an execution contract. Every release has an observable user outcome and an exit gate.

## Program rule: extend the working path

Adoption work must use the implementation proven through v0.25.2:

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
| **v0.25.2** | Canonical adoption API and implementation contract | Completed |
| **v0.26.0** | Research-synthesis hero application and finished research profile | **Current — implemented** |
| **v0.27.0** | One-command PostgreSQL/worker/Control Center demo stack | Next |
| **v0.28.0** | Clean distribution and tested operator runbooks | Planned |
| **v0.29.0** | Thin LangGraph adapter and incremental-adoption example | Planned |

## v0.25.2 — Canonical Adoption Contract

### Delivered

- ✅ package runtime version and separate remote-protocol identity;
- ✅ machine-readable `aasm.adoption.v1` public API contract;
- ✅ supported top-level imports and `AASMEngine` method inventory;
- ✅ supported CLI, inspection, and HTTP surface inventories;
- ✅ explicit `SUPPORTED`, `EXPERIMENTAL`, and `INTERNAL` meanings;
- ✅ Python, CLI, and HTTP contract access;
- ✅ architecture rule prohibiting parallel authority, reducer, and persistence paths;
- ✅ release-version visibility and CI consistency gates.

## v0.26.0 — Research Synthesis Hero Stack

### Objective

Deliver one understandable end-to-end application in which a new user can see AASM preserve truth, obligations, and unrelated work after a contradiction.

### 26.1 Finished research profile — delivered

- ✅ `aasm.research-synthesis@1.0.0`;
- ✅ research, synthesis, and report decision namespaces;
- ✅ persistent source-review, contradiction, steering, provenance, and artifact obligations;
- ✅ explicit evidence kinds and evidence contracts;
- ✅ fairness defaults;
- ✅ model-routing and governance-budget defaults;
- ✅ controlled profile evolution;
- ✅ profile/package conformance and fingerprint tests.

### 26.2 Fixed offline corpus — delivered

- ✅ small synthetic redistributable source set;
- ✅ CC0-1.0 source and license manifest;
- ✅ SHA-256 verification before execution;
- ✅ one fixed causal question;
- ✅ one reproducible matched-exposure contradiction;
- ✅ one known subgroup resolution;
- ✅ no network, paid API, or model key;
- ✅ corpus included in the Python package.

### 26.3 Canonical reference machine — delivered

The existing AASM runtime now executes:

```text
seed question
→ initial causal interpretation
→ conditional obligations
→ evidence extraction
→ validated contradiction
→ causal explanation
→ soft learned no-good
→ independent certificate verification
→ hard promotion
→ non-chronological backjump
→ preservation of unrelated report work
→ mid-run requirement injection
→ conditional lock restoration
→ corrected synthesis
→ provenance-bearing artifact
```

The reference application uses the ordinary public operations and event/reducer path. It has no private state authority.

### 26.4 Replay and comparison — delivered

- ✅ setup mode before contradiction;
- ✅ complete deterministic trajectory;
- ✅ full event replay;
- ✅ reconstructed-versus-persisted snapshot comparison;
- ✅ generated run summary, machine export, replay commands, and final artifact;
- ✅ reproducible `WHY_AASM.md` comparison;
- ✅ measurements for preserved work, invalidated decisions, repeated failure blocking, steering impact, obligations, and provenance.

### 26.5 Minimum browser visibility — delivered

The existing Control Center now renders:

- ✅ run reasoning summary;
- ✅ Decision Graph;
- ✅ Obligation Graph;
- ✅ Evidence Graph;
- ✅ conflict and learned no-good lifecycle;
- ✅ causal backjump target and invalidated decisions;
- ✅ fairness debt;
- ✅ profile and migration history;
- ✅ final semantic result and artifact provenance.

### Run

```bash
aasm demo \
  --scenario research-synthesis \
  --mode complete \
  --db research-demo.db \
  --output-dir research-output
```

### Exit gate

The release is complete when:

1. the corpus verifies from packaged data;
2. the profile/package conformance checks pass;
3. setup and complete modes run through the public API;
4. the failed model is learned, certified, blocked, and causally backjumped;
5. unrelated work is preserved;
6. selective steering restores only relevant work;
7. every mandatory obligation reaches a terminal disposition;
8. the final artifact carries claim-level provenance;
9. full replay matches persisted state;
10. Python 3.11–3.13, PostgreSQL, Control Center JavaScript, TLA+, and SPIN gates remain green.

## v0.27.0 — One-Command Local Full Stack

### Objective

Make first contact operational rather than instructional.

### Required stack

```text
Docker Compose
├── PostgreSQL
├── AASM HTTP runtime
├── existing Control Center
├── one default worker
├── optional second worker
└── pre-seeded research-synthesis machine
```

### Required command

```bash
docker compose up --build
```

The command must print the browser URL, reference machine identity, and health state.

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

- annotated release tags;
- GitHub releases with immutable source and wheel artifacts;
- PyPI publication as `aasm-runtime`;
- primary user path: `pip install aasm-runtime`;
- editable contributor path;
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

The same task must run once as an ordinary LangGraph workflow and once with AASM underneath it. The comparison must show what was retained, invalidated, learned, replayed, and made inspectable after the same contradiction.

### Exit gate

An existing LangGraph application can adopt AASM incrementally without rewriting its agent graph or bypassing the canonical adoption contract.

## Adoption scorecard

| Measure | Gate | v0.26 state |
|---|---:|---|
| Required external API keys | 0 | Met |
| Commands before first useful result | no more than 3 | Met after checkout/install |
| Reference replay | exact snapshot/hash match | Implemented |
| Injected contradiction | visible in UI and history | Implemented |
| Learned no-good | visible and reused | Implemented |
| Backjump | causal target shown | Implemented |
| Unrelated work | demonstrably preserved | Implemented |
| Mandatory unresolved obligations at completion | 0 | Enforced |
| Claim-level provenance | required | Implemented |
| Clone to healthy dashboard | under 5 minutes | v0.27 target |
| Fresh reset | one command | v0.27 target |
| Published-wheel smoke test | required in CI | v0.28 target |
| Runbook scenario tests | required in CI | v0.28 target |

## Delivered foundation

### Deterministic control plane

- ✅ explicit state and legal transitions;
- ✅ declarative definitions and structural model checking;
- ✅ event-sourced durability, checkpoints, replay, and forks;
- ✅ SQLite and PostgreSQL coordination;
- ✅ effect authorization, idempotency, ownership, `UNKNOWN` outcomes, and reconciliation;
- ✅ mission `QUIESCE`, `SUSPEND`, and `RESUME`.

### Planning, evidence, and execution

- ✅ plan graphs, checkpoint backtracking, and DP memory;
- ✅ claims, observations, assumptions, contradictions, invalidation, and lineage;
- ✅ capability scheduling, priorities, and quotas;
- ✅ workers, heartbeats, leases, reclaim, and stale-result rejection;
- ✅ model routing, economics, and governance budgets;
- ✅ optional Planner / Builder / Verifier protocol;
- ✅ selective information-change checkpoints and additive steering;
- ✅ collaboration, fleet admission, provisioning, telemetry, artifacts, CLI/API, and Control Center.

### v0.21–v0.25.2

- ✅ formal Decision / Obligation / Evidence calculus;
- ✅ conditional locks and bounded fairness;
- ✅ causal explanations, learned no-goods, backjumping, and restart;
- ✅ domain-neutral profiles, packages, fingerprints, and migrations;
- ✅ replaceable decision backends with atomic activation and budgets;
- ✅ certificate-gated hard knowledge and replay verification;
- ✅ bounded TLA+ and Promela/SPIN models;
- ✅ closed causal observability and actionable timelines;
- ✅ human-first README and canonical adoption contract.

## Post-adoption architecture backlog

The following remains valuable, but follows the adoption program rather than displacing it.

### Trust distribution

- signed package and backend manifests;
- published conformance evidence;
- package-registry protocol separating discovery from activation;
- trust policies for profile, backend, validator, and certifier identities;
- reproducible build provenance;
- migration dry-run reports.

### Hierarchical reasoning

- strategy, architecture, implementation, and execution layers;
- cross-layer conflict projection and backjump targets;
- scoped learned-knowledge promotion;
- hierarchical fairness and obligation inheritance;
- portfolio search across abstraction layers.

### Deeper production conformance

- Python-reducer to formal-model trace conformance;
- expanded formal coverage for effects, migrations, leases, and ownership;
- signed history reports and externally verifiable snapshots;
- property-based command sequences across live execution and replay.

## Non-goals for the core

AASM should not become:

- a bundled LLM provider;
- a domain-specific application;
- a package installer that executes code during discovery;
- a mandatory Planner/Builder system;
- a mandatory SAT/SMT system;
- a monolith forcing one evidence ontology, UI, or topology;
- a self-modifying package system without versioning and migration.

The core remains a role-agnostic, domain-neutral deterministic control plane with explicit extension contracts.
