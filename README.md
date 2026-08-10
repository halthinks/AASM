<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, humans, models, and real work.**

AASM keeps probabilistic reasoning inside explicit machine authority: state is durable, transitions are legal or illegal, plans are graphs, effects require authorization, evidence governs commitment, contradictions become learned constraints, candidate generation is replaceable, and use-case meaning arrives through domain-neutral profile packages rather than being baked into the kernel.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-v0.25.0%20experimental-orange)](ROADMAP.md)

[**Quick start**](#quick-start) · [**Architecture**](#architecture) · [**Packages**](#profile-packages) · [**Decision backends**](#decision-backends) · [**Assurance**](#formal-assurance) · [**Observability**](#observability)

</div>

---

## What AASM is

Most agent frameworks concentrate on giving a model tools. AASM concentrates on the systems problem underneath them:

> **How do you govern what an intelligent system is allowed to do next, preserve what happened, recover selectively, coordinate real work, and learn from contradictions without giving probabilistic components authority over durable state?**

AASM is a Python runtime, CLI, event model, and control plane with:

- explicit machine states and legal transitions;
- event-sourced replay, checkpoints, and historical forks;
- SQLite and PostgreSQL persistence;
- plan graphs, scheduling, memory, evidence, and provenance;
- external-effect proposal, authorization, idempotency, and reconciliation;
- distributed workers, heartbeats, leases, quotas, mission controls, and telemetry;
- optional Planner / Builder / Verifier orchestration;
- a formal decision/obligation calculus with conflict learning;
- versioned domain-neutral profile packages;
- replaceable decision-generation backends;
- independently checkable assurance records;
- generic Decision, Obligation, Evidence, conflict, fairness, package, candidate, and assurance observability.

The operating principle is:

> **Models propose. Algorithms organize. Policy authorizes. Evidence validates. Contradictions teach. Durable state governs what happens next.**

---

## Release architecture

```text
v0.21  Formal conflict-learning calculus
       decisions · obligations · locks · conflicts · explanations
       learned no-goods · backjumping · fairness · restart

v0.22  Domain-neutral package/profile contract
       profiles · packages · bindings · adapters · migrations
       semantic-result envelope · governed profile evolution

v0.23  Replaceable decision backends
       finite-domain · human · callback/model · portfolio
       candidate batches · lifecycle · selection · activation

v0.24  Formal assurance
       certificates · independent verification · history checks
       conflict-core minimization · certificate-gated hard knowledge

v0.25  Generic observability
       Decision/Obligation/Evidence graphs · conflicts · fairness debt
       package history · candidate history · assurance history
```

These layers are additive. The core stays domain-neutral and role-agnostic.

---

## Quick start

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .
```

Create a machine:

```python
from aasm import AASMEngine, ProblemSpec

engine = AASMEngine(ProblemSpec("Investigate a problem"))
print(engine.snapshot.machine_id)
print(engine.inspect_machine("summary"))
```

Run the CLI:

```bash
aasm --help
```

For durable storage, use the existing SQLite or PostgreSQL stores. Existing v0.21/v0.22 snapshots remain readable; missing v0.23/v0.24 state is initialized to the canonical empty state during deserialization.

---

## Architecture

```text
                  Domain package / profile
               meaning · policies · adapters
                          |
                          v
                 DecisionRequest
                          |
          +---------------+---------------+
          |               |               |
   finite-domain         human        model/solver/
      backend            input         portfolio
          |               |               |
          +---------- CandidateBatch -----+
                          |
                          v
                 deterministic AASM
          identity · parents · pinned state
        hard constraints · fairness · authority
                          |
                          v
                    active model
                          |
                          v
                conditional obligations
                          |
                          v
              execution / observation
                          |
                          v
                     evidence
                          |
                          v
          verify -> conflict -> explanation
                          |
                          v
                   learned constraint
                          |
             +------------+------------+
             |            |            |
           repair      backjump      restart
```

A backend can propose a candidate. It cannot activate a decision, commit an obligation, authorize an external effect, replace a package binding, or install hard machine knowledge.

---

## Formal conflict-learning calculus

The v0.21 calculus maintains durable:

- **Decisions** — named choices and assumptions;
- **Obligations** — work that must eventually be satisfied, rejected, superseded, or proven impossible;
- **Evidence** — observations and claims with lineage;
- **Locks** — model-relative temporary suppression, never silent deletion;
- **Conflicts** — contradictions tied to evidence and an active-model snapshot;
- **Explanations** — the assumptions materially responsible for a conflict;
- **Learned constraints** — guarded no-goods restricting future search;
- **Fairness records** — deterministic accounting preventing persistent obligations from remaining hidden forever.

A validated incompatibility can be represented as:

```text
guard => NOT (assumption_1 AND assumption_2 AND ... AND assumption_n)
```

Backjumping follows causal dependency instead of chronological creation order. `restart_search()` discards speculative assignments while preserving validated knowledge and durable execution state.

See [`docs/FORMAL_CALCULUS.md`](docs/FORMAL_CALCULUS.md).

---

## Profile packages

AASM does not require one domain ontology.

| Object | Meaning |
|---|---|
| **Package** | Distributable profiles, optional adapters, schemas, migrations, docs, examples, and tests. |
| **Profile** | One immutable, versioned use-case contract. |
| **Binding** | The exact profile/package identity and run configuration attached to a machine. |
| **Run** | The actual event-sourced execution history under that binding. |

Package design is an engineering craft. Authors decide which decisions deserve names, which obligations persist, what evidence is sufficient, how conflicts are explained, and what belongs in reusable contract versus run configuration.

Runs adapt naturally under a stable profile. **Profiles do not silently self-modify.** Repeated evidence can create a `ProfileEvolutionProposal`, but changing the contract requires a new version, new fingerprint, conformance, an explicit migration, and authorized activation.

See [`docs/PROFILE_PACKAGES.md`](docs/PROFILE_PACKAGES.md) and [`docs/EXTENSION_CONTRACT.md`](docs/EXTENSION_CONTRACT.md).

---

## Decision backends

v0.23 makes search replaceable.

Built-in backend primitives include:

- `FiniteDomainDecisionBackend` — deterministic finite-domain enumeration with stable pagination;
- `HumanDecisionBackend` — structured human proposal packets;
- `CallbackDecisionBackend` — provider-neutral callback for heuristics, models, or external systems;
- `PortfolioDecisionBackend` — combines and deduplicates several proposal sources;
- `DecisionBackendRegistry` — explicit backend registry and capability routing.

Candidate lifecycle is durable:

```text
PROPOSED -> ADMISSIBLE | REJECTED -> SELECTED -> ACTIVATED -> SUPERSEDED
```

Before selection or activation, AASM revalidates the candidate against current canonical state. Scores never override feasibility.

See [`docs/DECISION_BACKENDS.md`](docs/DECISION_BACKENDS.md).

---

## Formal assurance

v0.24 adds a separate assurance layer around learned machine knowledge.

- `CertificateRecord` fingerprints exactly what is being certified;
- `ProjectionCertificateVerifier` independently checks that a certificate covers the current learned-constraint projection;
- `DetachedDigestVerifier` verifies external artifacts by SHA-256;
- verified certificates can gate explicit promotion of a soft constraint to hard;
- `check_history()` verifies durable event-history properties;
- `minimize_conflict_core()` supports greedy irreducible and exact-bounded causal-core reduction through an explicit `ConflictOracle`.

AASM can verify machine-level coverage and provenance. It does not manufacture domain truth: a valid digest does not prove a simulation is physically accurate, and a formally covered constraint does not make bad evidence good.

See [`docs/FORMAL_ASSURANCE.md`](docs/FORMAL_ASSURANCE.md).

---

## Observability

v0.25 exposes generic machine projections through:

```python
engine.inspect_machine("summary")
engine.inspect_machine("decisions")
engine.inspect_machine("obligations")
engine.inspect_machine("evidence")
engine.inspect_machine("conflicts")
engine.inspect_machine("fairness")
engine.inspect_machine("packages")
engine.inspect_machine("candidates")
engine.inspect_machine("assurance")
```

The built-in views include:

- Decision Graph;
- Obligation Graph;
- Evidence Graph;
- conflict/backjump timeline;
- search-restart and profile/candidate/assurance event timeline;
- fairness debt;
- profile binding/migration history;
- candidate backend history;
- certificate/history-check/minimization summary.

These views describe AASM objects rather than a specific industry or workflow.

See [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md).

---

## Optional agent topology

Planner / Builder / Verifier remains optional.

AASM does **not** require:

- one LLM provider;
- OpenAI or Codex;
- Planner / Builder / Verifier;
- SAT or SMT;
- source-code repositories;
- one evidence ontology;
- one user interface;
- one execution topology.

Packages and decision backends are extension contracts, not kernel assumptions.

---

## Safety and correctness boundary

AASM is experimental software. It strengthens execution governance, provenance, replay, and machine-level assurance; it does not automatically certify domain correctness or safety.

External effects remain behind explicit effect authorization and reconciliation. Model output is proposal data. Human or model confidence does not bypass evidence contracts, learned hard constraints, profile boundaries, or authority policy.

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/FORMAL_CALCULUS.md`](docs/FORMAL_CALCULUS.md)
- [`docs/PROFILE_PACKAGES.md`](docs/PROFILE_PACKAGES.md)
- [`docs/EXTENSION_CONTRACT.md`](docs/EXTENSION_CONTRACT.md)
- [`docs/DECISION_BACKENDS.md`](docs/DECISION_BACKENDS.md)
- [`docs/FORMAL_ASSURANCE.md`](docs/FORMAL_ASSURANCE.md)
- [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md)
- [`ROADMAP.md`](ROADMAP.md)
- [`CHANGELOG.md`](CHANGELOG.md)

Release notes: [`v0.21`](docs/RELEASE_0.21.md) · [`v0.22`](docs/RELEASE_0.22.md) · [`v0.23`](docs/RELEASE_0.23.md) · [`v0.24`](docs/RELEASE_0.24.md) · [`v0.25`](docs/RELEASE_0.25.md)

---

## Contributing

AASM is an early open-source project. Issues, tests, package designs, backend implementations, formal models, documentation, examples, and careful API review are welcome. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

## License

MIT — see [`LICENSE`](LICENSE).
