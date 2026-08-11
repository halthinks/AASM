# AASM Roadmap

AASM is currently **v0.28.2 / experimental**.

The current program is **Adoption, Interoperability, and Verifiable Operation**: make the deterministic kernel, formal calculus, assurance system, observability, distributed runtime, and framework adapters understandable, runnable, distributable, and independently checkable by people who did not build them.

This roadmap is an execution contract. Every release has an observable user outcome, an implementation boundary, and an exit gate.

## Program rule: extend the working path

All new work must use the implementation proven through v0.28.2:

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

The architectural rule inherited from the AVATAR/labelled-splitting work remains:

```text
exploration may be conditional and reversible
history and provenance are append-only
contradictions become durable blocking knowledge
backjumping follows causes rather than recency
restart discards speculation, not verified knowledge
fairness prevents mandatory work from remaining hidden forever
```

## Release sequence

| Release | Primary outcome | Status |
|---|---|---|
| **v0.25.2** | Canonical adoption API and implementation contract | Completed |
| **v0.26.0** | Research Synthesis Hero Stack | Completed |
| **v0.27.0 — One-Command Local Full Stack** | PostgreSQL, runtime, Control Center, worker, and reference machines | Completed |
| **v0.28.0 — Distribution and Operator Readiness** | Immutable releases, compatibility policy, and executable runbooks | Completed |
| **v0.28.1 — Distribution Release Hardening** | Reproducible builds, no-overwrite publication, and exact remote verification | Completed |
| **v0.28.2 — Self-Contained Source Distribution** | Standalone source package with repository contracts and executable smoke validation | **Current — implemented** |
| **v0.29.0 — Thin LangGraph Adapter** | Incremental AASM adoption beneath an existing graph | Next |
| **v0.30.0 — Adapter Conformance Kit** | Framework-neutral proof that an adapter preserves the AASM boundary | Planned |
| **v0.31.0 — Hierarchical Decision Scopes** | Strategy, architecture, and implementation reasoning without duplicated authority | Planned |
| **v0.32.0 — Runtime/Formal Trace Conformance** | Machine-checkable correspondence between production events and the formal abstraction | Planned |
| **v0.33.0 — Signed Provenance and Verifiable Exports** | Portable, independently verifiable run evidence | Planned |
| **v0.34.0 — Distributed Recovery Certification** | Failure-injection evidence for leases, effects, ownership, and recovery | Planned |

---

# v0.28.2 — Self-Contained Source Distribution

## User outcome

A user can download the source distribution, extract it outside a Git checkout, and validate the packaged source plus its repository-level contracts.

## Delivered implementation

- ✅ `MANIFEST.in` includes profiles, schemas, formal models, examples, runbooks, workflows, release scripts, and tests;
- ✅ the packaged adoption contract declares `source_distribution_self_test = true`;
- ✅ the packaged contract declares scope `FULL_REPOSITORY_CONTRACT`;
- ✅ a standalone smoke test validates representative contract-bearing members;
- ✅ the smoke test validates `aasm.adoption.v1` and executes an operator runbook;
- ✅ CI builds, safely extracts, and tests the sdist outside the repository checkout;
- ✅ the existing reproducible double-build, clean-wheel, PostgreSQL, Compose, TLC, SPIN, and immutable-release gates remain active;
- ✅ v0.28.1 assets are not overwritten; publication uses a new immutable version.

## Exit gate

v0.28.2 is complete when:

1. Python 3.11->3.13 pass;
2. PostgreSQL and Docker Compose pass;
3. TLA+/TLC and Promela/SPIN pass;
4. two clean builds produce byte-identical wheel and source distribution files;
5. the extracted sdist passes its standalone smoke test with no Git checkout;
6. the current release is published once and every remote asset byte is verified;
7. README and version surfaces show v0.28.2 and v0.29.0 next;
8. no packaging operation changes AASM machine authority or runtime semantics.

---

# v0.29.0 — Thin LangGraph Adapter

## User outcome

An existing LangGraph application retains its graph, nodes, routing, checkpoint data, and domain state while AASM supplies durable authority, obligations, evidence, effect authorization, conflict learning, replay, and recovery underneath it.

## Required adapter boundary

1. map one LangGraph thread/run to one AASM machine;
2. create or resolve that binding idempotently;
3. map selected graph decisions to named AASM decisions rather than serializing every framework object;
4. map required work to obligations with explicit terminal disposition;
5. attach node and tool outputs as evidence with producer and causal provenance;
6. require AASM authorization before declared external effects;
7. return `CONTINUE`, `REPAIR`, `BACKJUMP`, `PAUSE`, `RESTART`, or `FORK` to the graph;
8. preserve LangGraph checkpoints only as framework state, never as competing AASM authority;
9. use `aasm.adoption.v1`, not versioned runtime internals;
10. add no second scheduler, lease system, effect ledger, or event store.

## Planned implementation

- optional `langgraph` dependency extra;
- `aasm.integrations.langgraph` adapter module;
- typed thread/run binding and node context;
- node-entry and node-exit hooks;
- decision, obligation, evidence, and effect mapping helpers;
- recovery directive mapping;
- contradiction-injection reference graph;
- ordinary-versus-AASM comparison harness;
- adapted-run replay and observability views;
- runnable migration guide and optional-dependency tests.

## Required comparison

The same controlled task runs as an ordinary LangGraph workflow and as the same workflow with AASM underneath it. Both receive the same contradiction. The comparison must show what is invalidated, what unrelated work remains, what learned constraint blocks recurrence, where the causal backjump lands, and how exact replay reconstructs the result.

## Exit gate

An existing LangGraph application adopts AASM without rewriting its graph, bypassing the canonical authority boundary, directly mutating AASM storage, or storing machine truth in framework-private checkpoint state.

## Non-goals

- no replacement LangGraph runtime;
- no translation of every LangGraph class into an AASM ontology;
- no mandatory Planner/Builder topology;
- no provider-specific model bundle;
- no direct snapshot or table mutation.

---

# v0.30.0 — Adapter Conformance Kit

## User outcome

A framework or application adapter can demonstrate—not merely claim—that it preserves AASM authority, replay, effect, and recovery contracts.

## Planned implementation

- framework-neutral adapter protocol and capability declaration;
- black-box fixture machines for success, contradiction, requirement change, lease loss, `UNKNOWN` effect, restart, replay, and fork;
- semantic-result and evidence-provenance checks;
- duplicate-authority and direct-storage-write detection hooks;
- deterministic replay comparison;
- machine-readable `PASS`, `FAIL`, and `INCONCLUSIVE` report;
- CLI and remote HTTP runner;
- one additional thin adapter only after the kit proves the boundary is reusable.

## Exit gate

A third party runs one command against an adapter and receives a reviewable report proving whether it preserves the supported AASM adoption contract.

---

# v0.31.0 — Hierarchical Decision Scopes

## User outcome

Long-running work separates strategy, architecture, and implementation decisions while retaining one authoritative machine and one causal conflict graph.

## Planned implementation

- parent/child decision-scope identities;
- scope-local decisions, obligations, evidence, locks, constraints, and fairness debt;
- validated cross-scope dependency directions;
- causal backjump across scopes only through recorded dependencies;
- scope-aware restart preserving verified parent knowledge;
- explicit inheritance and override rules;
- backward-compatible migration from flat histories;
- scope lineage in observability and Control Center;
- bounded formal properties for isolation and cross-scope recovery.

## Exit gate

An implementation contradiction can invalidate the responsible architecture or strategy decision while preserving unrelated sibling scopes and one authority path.

---

# v0.32.0 — Runtime/Formal Trace Conformance

## User outcome

A production event history can be projected into the formal vocabulary and checked step by step, closing the gap between “the model passed” and “the runtime followed the modeled rule.”

## Planned implementation

- versioned production-event to formal-variable abstraction map;
- trace projection with source event ranges and hashes;
- transition classifiers for calculus, activation, learning, restart, effects, leases, and completion;
- conformance checker distinguishing unsupported abstraction from violation;
- counterexamples linked to exact durable event IDs;
- generated traces from runbooks and scenario tests;
- property-based bounded event-sequence generation;
- representative trace corpus as a CI gate.

## Exit gate

Every covered transition either refines a legal formal step or produces an exact counterexample tied to durable history.

---

# v0.33.0 — Signed Provenance and Verifiable Exports

## User outcome

A run can be exported as portable evidence and independently verified without trusting the producing server or database.

## Planned implementation

- canonical export manifest for events, snapshots, definitions, profiles, certificates, artifacts, and projections;
- content-addressed inventory with explicit algorithm/version identity;
- pluggable detached signer and verifier interfaces;
- key identity, rotation, revocation, and verification-policy records;
- selective disclosure retaining hash linkage;
- offline verification CLI;
- tamper, truncation, substitution, and wrong-key tests;
- export provenance visible in the Control Center;
- compatibility rules for historical verification after upgrades.

## Exit gate

A clean offline environment verifies package identity, completeness, hashes, signatures, certificate coverage, and replay evidence.

---

# v0.34.0 — Distributed Recovery Certification

## User outcome

AASM produces repeatable failure-injection evidence that ownership, leases, effects, and recovery remain safe under declared failures.

## Planned implementation

- deterministic fault injection for worker crash, lease expiry, delayed completion, duplicate delivery, partitions, database restart, and supervisor loss;
- external-effect emulator for `NOT_STARTED`, `STARTED`, `SUCCEEDED`, `FAILED`, and `UNKNOWN`;
- invariants for single valid ownership, stale-result rejection, idempotency, reconciliation, and mandatory-obligation preservation;
- multi-process PostgreSQL scenarios and bounded schedule exploration;
- recovery certificate tied to exact scenario, configuration, trace, and software version;
- expanded operator drills and Control Center recovery timeline;
- selected lease/effect formal-model extensions;
- conformance-kit integration for remote adapters.

## Exit gate

Every declared failure either recovers without duplicated authority or duplicated effects, or stops in an explicit state requiring human or external reconciliation.

---

# Adoption scorecard

| Measure | Gate | Current state |
|---|---:|---|
| Clone to healthy dashboard | under 5 minutes | Implemented and Compose-tested |
| Understandable completed demonstration | under 10 minutes | Implemented |
| Required external model/API keys | 0 | Achieved |
| Reference replay | exact snapshot/hash match | Enforced |
| Learned no-good | visible, certified, and reused | Implemented |
| Causal backjump | target shown | Implemented |
| Mandatory unresolved obligations at completion | 0 | Enforced |
| Built-wheel smoke | required in CI | Implemented |
| Reproducible distribution | two byte-identical builds | Implemented |
| Extracted-sdist smoke | no Git checkout | **v0.28.2** |
| GitHub release assets | exact remote read-back | Implemented |
| Operator runbook drills | required in CI | Implemented |
| PyPI installation | Trusted Publisher binding required | Repository side ready; external binding pending |
| Existing-framework adoption | thin LangGraph adapter | v0.29.0 |
| Adapter boundary proof | conformance report | v0.30.0 |
| Hierarchical reasoning | one authority across scopes | v0.31.0 |
| Runtime/formal correspondence | trace refinement | v0.32.0 |
| Portable verification | signed offline package | v0.33.0 |
| Distributed recovery evidence | failure-injection certificate | v0.34.0 |

---

# Cross-release delivery discipline

Every release must retain:

1. Python 3.11–3.13 tests;
2. reproducible wheel and source-distribution builds;
3. clean-wheel and extracted-sdist validation;
4. PostgreSQL integration;
5. Docker Compose end-to-end verification;
6. TLA+/TLC and Promela/SPIN when the modeled boundary changes;
7. exact replay and append-only history;
8. visible README version and next milestone;
9. ordinary source committed directly to `main`;
10. no branch or PR staging for canonical implementation work.
