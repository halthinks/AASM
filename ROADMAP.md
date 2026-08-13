# AASM Roadmap

AASM is currently **v0.31.0 / experimental**.

The roadmap is an implementation contract. Every release must extend the working path:

```text
public AASM API
    → existing event creation
    → existing pure reducer
    → existing canonical snapshot
    → Memory / SQLite / PostgreSQL
    → existing assurance, observability, workers, leases, effects, and replay
```

No release may introduce a parallel runtime, alternate authority store, framework-private AASM truth, or direct database mutation path.

## Completed adoption and authority program

| Release | Outcome | State |
|---|---|---|
| v0.25.2 | Canonical adoption API | Completed |
| v0.26.0 | Research Synthesis Hero Stack | Completed |
| v0.27.0 | One-command PostgreSQL/worker/Control Center stack | Completed |
| v0.28.x | Distribution, immutable releases, runbooks, self-testing sdist | Completed |
| v0.29.0 | Thin LangGraph adapter | Completed |
| v0.30.0 | Adapter Conformance Kit | Completed |
| **v0.31.0** | **Hierarchical Decision Scopes** | **Current — implemented** |

## v0.31.0 — Hierarchical Decision Scopes

**Outcome:** strategy, architecture, implementation, and workstream reasoning are separated inside one authoritative machine.

Delivered:

- permanent `root` scope;
- `aasm.scopes.v1 / 0.1.0`;
- scope-local Decisions, Obligations, evidence, locks, conflicts, explanations, constraints, and fairness debt;
- inheritance, isolation, explicit override, and override denial;
- validated cross-scope dependencies;
- causal branch backjump preserving unrelated siblings;
- scoped restart retaining parents, pinned decisions, evidence, and hard knowledge;
- atomic multi-scope candidates;
- legacy-flat migration;
- Python, CLI, HTTP, Control Center, schemas, TLC, and SPIN.

## Execution-correctness program

### v0.32.0 — Runtime/Formal Trace Conformance

**Outcome:** demonstrate that a production event history refines the formal abstraction step by step.

Work packages:

1. lossless event-to-trace contract;
2. production durable-history projector;
3. semantic pre/post-state checker;
4. generated trace corpus covering scopes, candidates, recovery, effects, and leases;
5. completion gate with unsupported-transition accounting and exact event-linked counterexamples.

### v0.33.0 — Signed Provenance and Verifiable Exports

**Outcome:** export a completed run and verify it offline without trusting the original server or database.

Deliverables: canonical manifest, content-addressed inventory, detached signatures, verifier policy, selective disclosure, replay evidence, key rotation/revocation, and offline CLI.

### v0.34.0 — Distributed Recovery Certification

**Outcome:** produce repeatable failure-injection evidence for ownership, leases, effects, and recovery.

Scenarios include worker crash, lease expiry, stale completion, duplicate delivery, network partition, database restart, supervisor loss, and ambiguous `UNKNOWN` effects. Each scenario must recover without duplicate authority/effects or stop in explicit reconciliation.

## Semantic Solver Program

The semantic program follows the whitepaper and implementation handoff. It begins only after the execution-correctness substrate is complete.

```text
ProblemDefinition
        ↓ semantic compilation
ProblemModel
        ↓ instantiation
ProblemInstance
        ↓
AASM authority runtime
        ↓
verified completion or explicit unresolved state
```

### v0.35.0 — Semantic Problem Model Foundations
Persist/replay versioned `DomainPackage`, `ProblemModel`, and `ProblemInstance` contracts. First fixture: a finite parser/storage constraint problem.

### v0.36.0 — Domain and Instance Compiler SDK
Deterministic compiler protocols, missing-input/capability reports, canonical fingerprints, and `aasm compile` / `aasm problem-check`.

### v0.37.0 — Reasoning Artifacts and Epistemic Admission
Typed Claims, Hypotheses, Lemmas, Invariants, Counterexamples, Proof Obligations, and Reasoning Commits. Models propose; policy admits.

### v0.38.0 — Semantic Dependency Graph and Truth Maintenance
Typed dependency relations, deterministic stale propagation, obligation reopening, conditional-lock release, and unrelated-sibling preservation.

### v0.39.0 — Operator / Observer / Verifier ABI
Generic capabilities that use existing effect authorization and cannot self-promote beyond declared authority.

### v0.40.0 — Reasoning Frontier and Context Projection
Bounded semantic work packets derived from canonical state so a fresh worker can resume without transcript replay.

### v0.41.0 — Domain-Neutral Solver Loop
Compile/select/activate/execute/verify/learn/backjump/restart loop with replaceable candidate, objective, activity, restart, and budget policies.

### v0.42.0 — Domain Package SDK and Reference Domains
Finite CSP, software repair, research synthesis, and mathematical reasoning on the same kernel.

### v0.43.0 — Semantic Conformance and Formal Refinement
One-command `PASS | FAIL | INCONCLUSIVE` conformance with exact counterexample event IDs.

### v0.44.0 — Cross-Run Certified Knowledge
Run-local by default; reuse only with applicability predicates, package compatibility, provenance, expiry/revocation, and certification.

### v0.45.0 — Semantic Solver Release Candidate
Freeze the first coherent semantic contracts after exact replay, formal invariants, four reference domains, failure injection, fresh-worker resume, and complete handoff/runbooks.

## Planned semantic dependency graph

```text
Entity
  → Predicate
  → Claim
  → Evidence
  → Verifier
  → Certificate
  → Constraint
  → Decision
  → Operator
  → Effect
  → Observation
```

## Planned semantic calculus

```text
DEFINE  COMPILE  INSTANTIATE  PROPOSE  SUPPORT  CHALLENGE
VERIFY  AUTHORIZE  INVALIDATE  REOPEN  LEARN  GENERALIZE
PROJECT  BACKJUMP  RESTART  COMPLETE
```

Every operation must define preconditions, postconditions, preserved invariants, provenance, and replay semantics.

## Cross-release gates

Every release retains:

1. Python 3.11–3.13;
2. reproducible wheel and self-testing sdist;
3. Memory/SQLite/PostgreSQL replay equivalence;
4. Docker Compose full-stack verification;
5. LangGraph and adapter conformance;
6. TLC/SPIN when modeled semantics change;
7. visible README version and next milestone;
8. ordinary source committed directly to `main`;
9. no branch/PR staging for canonical implementation work;
10. immutable release assets with exact hash read-back.

## Adoption scorecard

| Measure | Gate |
|---|---:|
| Clone to healthy dashboard | under 5 minutes |
| Understandable completed demonstration | under 10 minutes |
| External model/API keys required | 0 |
| Exact replay | persisted and reconstructed hashes match |
| Unresolved mandatory obligations at completion | 0 |
| Published wheel smoke | required |
| Extracted-sdist smoke | required |
| Operator drills | required |
