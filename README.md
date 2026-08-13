<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, models, humans, and real work.**

AASM keeps machine truth outside the model. Models and compilers propose; evidence, verifiers, policy, and deterministic state transitions decide what becomes durable and what must be reconsidered when upstream truth changes.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## Current release — v0.38.0

**Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance**

| Identity | Value |
|---|---|
| Package/runtime | `aasm-runtime 0.38.0` |
| Adoption contract | `aasm.adoption.v1 / 0.14.0` |
| Reasoning artifacts | `aasm.reasoning.artifact.v1 / 0.1.0` |
| Semantic dependencies | `aasm.semantic.dependencies.v1 / 0.1.0` |
| Truth maintenance | `aasm.truth.maintenance.v1 / 0.1.0` |
| Reactive obligations | `aasm.reactive.obligation.v1 / 0.1.0` |
| Causal decisions | `aasm.causal.decision.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |
| Next release | **v0.39.0 — Typed Event/Transition Protocol and Capability ABI** |

v0.38 connects the knowledge admitted by v0.37 to the decisions and work that depend on it.

```text
Evidence / Observation
        ↓
Reasoning Artifact
        ↓
Verifier / Certificate
        ↓
Constraint
        ↓
Causal Decision
        ↓
Obligation / Operator / Effect
        ↓
Observation
```

The graph is a deterministic projection over the same authoritative AASM history. It does **not** introduce a second database, event log, reducer, scheduler, or truth authority.

## Semantic dependency graph

AASM now exposes typed semantic nodes for entities, predicates, objectives, reasoning artifacts, evidence, events, verifiers, observers, certificates, constraints, decisions, obligations, operators, effects, and reactive rules.

Dependencies have an explicit direction: **upstream premise/cause → dependent object**. That makes two core queries deterministic:

```text
What breaks if X is false?     → forward impact closure
Why does Y currently exist?    → backward dependency lineage
```

Dependencies that can propagate staleness must form a DAG. Descriptive edges may cycle only when `propagates_stale=false`.

## Causal decisions

`CausalDecisionRecord` extends the existing AASM `DecisionRecord`; it does not replace the decision calculus. It adds:

- rejected alternatives;
- confidence;
- explicit reasoning;
- causal event IDs;
- causal reasoning-artifact IDs.

This makes a durable decision explainable as a consequence of admitted knowledge rather than merely a value that happened to become active.

## Reactive obligations without hidden execution

A reactive rule watches durable event types and deterministically **derives an ordinary AASM Obligation**. The rule carries a `handler_name`, but v0.38 never calls that handler from the reducer or derivation path.

```text
Durable Event
    ↓
Reactive rule match
    ↓
ordinary ObligationRecord
    ↓
existing scheduler / authority path
```

Handler/capability typing belongs to v0.39. Autonomous execution belongs to the v0.41 solver loop.

## Truth maintenance

Truth maintenance is local, append-only, resumable, and idempotent.

When an upstream node changes:

1. AASM computes the affected descendant closure.
2. It records a durable `TruthMaintenancePlan` **before** mutation.
3. Reasoning artifacts in the closure become `STALE` where legal.
4. Dependent causal decisions become `INVALIDATED`.
5. Work that already consumed stale truth reopens as `NEEDS_REVALIDATION` through the existing obligation transition table.
6. Existing locks are reevaluated through the existing lock machinery.
7. A completion Evidence record closes the plan.

If the process stops between steps 2 and 7, `resume_truth_maintenance(plan_id)` resumes the recorded plan. Reapplying an already completed plan is a no-op with the same identity.

**Unrelated siblings are preserved.** V0.38 does not restart the world because one premise changed.

## Future memory boundary already exposed

V0.38 intentionally does **not** implement the Hierarchical Memory Layer early. Instead it exposes deterministic inputs for v0.40 context selection:

```text
VALID
STALE
REFUTED
AUTHORIZED
scope_visibility
dependency_depth
causal_relevance
objective_relevance
last_verified_at
verification_strength
superseded_by
```

That lets v0.40 remember and retrieve only against the semantic validity system already established by v0.37–v0.38.

## CLI

```bash
aasm semantic-dependency-contract
aasm semantic-dependency-conformance

aasm dependency-graph MACHINE_ID --store runs.db
aasm dependency-impact MACHINE_ID --store runs.db --node-type ARTIFACT --node-id ARTIFACT_ID
aasm dependency-lineage MACHINE_ID --store runs.db --node-type OBLIGATION --node-id OBLIGATION_ID

aasm dependency-add MACHINE_ID --store runs.db --input dependency.json \
  --authority-id policy-1 --authority-class POLICY

aasm causal-decision-add MACHINE_ID --store runs.db --input decision.json --activate

aasm reactive-rule-add MACHINE_ID --store runs.db --input rule.json \
  --authority-id policy-1 --authority-class POLICY
aasm reactive-derive MACHINE_ID --store runs.db

aasm truth-maintain MACHINE_ID --store runs.db \
  --node-type ARTIFACT --node-id ARTIFACT_ID \
  --reason "upstream evidence invalidated" \
  --authority-id verifier-1 --authority-class VERIFIER

aasm truth-resume MACHINE_ID PLAN_ID --store runs.db
aasm semantic-memory-signals MACHINE_ID --store runs.db
```

## Architecture progression

- **v0.35** Semantic Problem Model Foundations
- **v0.36** Semantic Compiler SDK
- **v0.37** Reasoning Artifacts and Epistemic Admission
- **v0.38** Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- **v0.39 next** Typed Event/Transition Protocol and Capability ABI
- **v0.40** Hierarchical Memory, Reasoning Frontier, and Context Projection
- **v0.41** Domain-Neutral Autonomous Solver Loop
- **v0.42** Reference Domains and Memory/Reasoning Stress Tests
- **v0.43** Semantic Conformance and Adversarial Certification
- **v0.44** Cross-Run Certified Knowledge and Governed Long-Term Memory
- **v0.45** Semantic Solver Release Candidate

## Why AASM exists

Long-running agents fail when conversation history becomes machine state: claims turn into facts without admission, causal dependencies disappear, disproven assumptions return, and context grows without a principled way to decide what is still valid. AASM separates proposal from authority and makes decisions, obligations, evidence, reasoning, dependencies, effects, recovery, and provenance replayable.

## Install

```bash
pip install aasm-runtime
```

Contributor setup:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'
pytest -q
```

## Documentation

[Why AASM?](WHY_AASM.md) · [Roadmap](ROADMAP.md) · [Architecture](docs/ARCHITECTURE.md) · [Semantic Truth Maintenance](docs/SEMANTIC_TRUTH_MAINTENANCE.md) · [Formal Assurance](docs/FORMAL_ASSURANCE.md) · [Release Process](docs/RELEASE_PROCESS.md)

## Correctness boundary

V0.38 proves and tests deterministic dependency topology, descendant-only impact, causal provenance, resumable truth maintenance, obligation revalidation, and reactive derivation. It does not claim that a model-generated statement is true, and it does not let a reactive rule secretly execute a capability.

## License

MIT — see [LICENSE](LICENSE).
