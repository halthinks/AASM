# AASM Roadmap

AASM is currently **v0.28.0 / experimental**.

The current program is **Adoption and Operability**: make the deterministic kernel, formal calculus, assurance system, observability, and distributed runtime understandable, runnable, distributable, and operable by people who did not build them.

This roadmap is an execution contract. Every release has an observable user outcome and an exit gate.

## Program rule: extend the working path

Adoption work must use the implementation proven through v0.28.0:

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
| **v0.27.0 — One-Command Local Full Stack** | PostgreSQL, runtime, Control Center, worker, and reference machines | Completed |
| **v0.28.0 — Distribution and Operator Readiness** | Immutable releases, clean-wheel verification, compatibility policy, and executable runbooks | **Current — implemented** |
| **v0.29.0 — Thin LangGraph Adapter** | Incremental adoption under an existing graph | Next |

---

# v0.28.0 — Distribution and Operator Readiness

## Objective

Make AASM dependably installable from immutable artifacts and operable under common failure conditions.

## Delivered distribution path

- ✅ package metadata and public project URLs for `aasm-runtime`;
- ✅ wheel and source-distribution build through `python -m build`;
- ✅ `twine check` metadata validation;
- ✅ structural inspection of wheel and source-distribution contents;
- ✅ clean virtual-environment installation of the built wheel;
- ✅ installed-package smoke tests for `aasm adoption-contract` and operator runbooks;
- ✅ generated `SHA256SUMS.txt` and `release-manifest.json`;
- ✅ annotated release-tag map for v0.25.1 through v0.27.0;
- ✅ automatic current annotated tag and GitHub Release creation;
- ✅ immutable wheel, source distribution, checksum, and manifest assets;
- ✅ credential-free PyPI Trusted Publisher job, externally gated until the PyPI project binding is activated;
- ✅ release status visible as `aasm/release` on the exact commit.

## Delivered operator runbooks

Each procedure is both a one-page imperative document and an executable CI scenario:

- ✅ recover after lease loss;
- ✅ inject a requirement without destroying the plan;
- ✅ inspect and act on a learned no-good;
- ✅ operate a human approval gate with policy as data;
- ✅ safely replay and fork a machine;
- ✅ reconcile an `UNKNOWN` external effect without guessing;
- ✅ diagnose a failed durable-history verification.

## Exit gate

v0.28.0 is complete at the repository level when:

1. Python 3.11–3.13 tests pass;
2. PostgreSQL and Docker Compose integration pass;
3. the built wheel installs and runs in a clean environment;
4. wheel and source-distribution contents match the declared release;
5. every runbook passes as an executable drill;
6. the exact commit passes TLA+/TLC and Promela/SPIN;
7. the annotated tag and GitHub Release contain immutable distributions, checksums, and a manifest;
8. the README exposes the current version, install path, runbooks, compatibility boundary, and next release;
9. no release path mutates AASM machine state outside the existing runtime.

PyPI publication has one external prerequisite: the `aasm-runtime` PyPI project must trust `.github/workflows/release.yml` in the `pypi` environment. The repository-side publisher is complete and disabled unless `AASM_PUBLISH_PYPI=true` or a manual release explicitly requests publishing.

---

# v0.29.0 — Thin LangGraph Adapter

## Objective

Let an existing LangGraph application retain its graph while placing AASM underneath it as the durable state, authority, conflict, and recovery substrate.

## Required adapter boundary

The adapter must remain thin:

1. map one LangGraph thread/run to one AASM machine;
2. record selected decisions and results as AASM state and evidence;
3. require AASM authorization before declared external effects;
4. return AASM recovery outcomes to the existing graph;
5. use the `aasm.adoption.v1` public surface;
6. avoid translating every framework-internal object into a new ontology;
7. avoid creating a second scheduler or persistence layer.

## Required comparison

The same controlled task runs:

- once as an ordinary LangGraph workflow;
- once with AASM underneath it.

The comparison must show what was preserved, invalidated, learned, replayed, and made inspectable after the same injected contradiction.

## Exit gate

An existing LangGraph application can adopt AASM incrementally without rewriting its graph or bypassing the canonical authority boundary.

---

# Completed adoption foundation

## v0.25.2 — Canonical Adoption Contract

- ✅ machine-readable `aasm.adoption.v1` contract;
- ✅ supported imports, engine methods, CLI commands, inspection surfaces, and HTTP endpoints;
- ✅ implementation rule prohibiting parallel authority and persistence paths.

## v0.26.0 — Research Synthesis Hero Stack

- ✅ finished `aasm.research-synthesis` profile;
- ✅ verified offline corpus;
- ✅ contradiction, learned no-good, independent certificate, hard promotion, and causal backjump;
- ✅ unrelated-work preservation and selective steering;
- ✅ final claim-level provenance and exact replay;
- ✅ Decision, Obligation, Evidence, conflict, fairness, and artifact views.

## v0.27.0 — One-Command Local Full Stack

- ✅ `docker compose up --build`;
- ✅ PostgreSQL-backed multi-process runtime;
- ✅ existing Control Center and worker/lease path;
- ✅ live and completed reference machines;
- ✅ non-destructive fresh-machine operation;
- ✅ Docker Compose end-to-end smoke verification.

---

# Adoption scorecard

| Measure | Gate | Current state |
|---|---:|---|
| Clone to healthy dashboard | under 5 minutes | Implemented and Compose-tested |
| Understandable completed demonstration | under 10 minutes | Implemented |
| Required external model/API keys | 0 | Achieved |
| Commands before first useful result | no more than 3 | Achieved |
| Reference replay | exact snapshot/hash match | Enforced |
| Injected contradiction | visible in UI and history | Implemented |
| Learned no-good | visible, certified, and reused | Implemented |
| Causal backjump | target shown | Implemented |
| Unrelated work | demonstrably preserved | Implemented |
| Mandatory unresolved obligations at completion | 0 | Enforced |
| Fresh reset | one command | Implemented |
| Built-wheel smoke test | required in CI | Implemented |
| GitHub release assets and checksums | automatic | Implemented |
| Operator runbook scenario tests | required in CI | Implemented |
| PyPI installation | Trusted Publisher binding required | Repository side ready; external binding pending |
| Existing-framework adoption | one thin adapter | v0.29.0 |

---

# Post-adoption architecture backlog

These remain valuable but do not displace the adoption sequence:

- signed package/backend manifests and reproducible provenance;
- hierarchical strategy/architecture/implementation reasoning;
- trace conformance between Python execution and formal abstraction;
- expanded formal coverage for effects, leases, and distributed ownership;
- generated property-based execution/replay sequences;
- externally verifiable signed snapshot and history reports.

## Core non-goals

AASM should not become:

- a bundled model provider;
- a domain-specific application;
- a mandatory Planner/Builder system;
- a mandatory SAT/SMT system;
- a package installer that executes unknown code during discovery;
- a monolith that forces one evidence ontology, UI, or agent topology;
- a self-modifying package system without explicit versioning and migration.

The core remains a role-agnostic, domain-neutral deterministic control plane.
