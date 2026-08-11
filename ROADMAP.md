# AASM Roadmap

AASM is currently **v0.28.1 / experimental**.

The current program is **Adoption, Interoperability, and Verifiable Operation**: make the deterministic kernel, formal calculus, assurance system, observability, distributed runtime, and framework adapters understandable, runnable, distributable, and independently checkable by people who did not build them.

This roadmap is an execution contract. Every release has an observable user outcome, an implementation boundary, and an exit gate.

## Program rule: extend the working path

All new work must use the implementation proven through v0.28.1:

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
| **v0.28.0 — Distribution and Operator Readiness** | Immutable releases, clean-wheel verification, compatibility policy, and executable runbooks | Completed |
| **v0.28.1 — Distribution Release Hardening** | Reproducible builds, no-overwrite publication, exact remote verification, and non-blocking historical release evidence | **Current — implemented** |
| **v0.29.0 — Thin LangGraph Adapter** | Incremental AASM adoption beneath an existing graph | Next |
| **v0.30.0 — Adapter Conformance Kit** | Framework-neutral proof that an adapter preserves the AASM boundary | Planned |
| **v0.31.0 — Hierarchical Decision Scopes** | Strategy, architecture, and implementation reasoning without duplicated authority | Planned |
| **v0.32.0 — Runtime/Formal Trace Conformance** | Machine-checkable correspondence between production events and the formal abstraction | Planned |
| **v0.33.0 — Signed Provenance and Verifiable Exports** | Portable, independently verifiable run evidence | Planned |
| **v0.34.0 — Distributed Recovery Certification** | Failure-injection evidence for leases, effects, ownership, and recovery | Planned |

---

# v0.28.1 — Distribution Release Hardening

## Objective

Remove release fragility discovered by exercising the real v0.28.0 publication path, without changing the deterministic runtime or operator semantics.

## Delivered release path

- ✅ exact `setuptools` and `wheel` build-backend versions;
- ✅ exact `build` and `twine` versions in CI and release automation;
- ✅ modern SPDX package-license metadata;
- ✅ two independent distribution builds under the same recorded source epoch;
- ✅ byte-identical wheel and source-distribution comparison;
- ✅ clean virtual-environment installation of the selected build;
- ✅ release intent limited to an explicit dispatch or package-version change;
- ✅ ordinary non-release commits receive a successful `aasm/release` status without republishing;
- ✅ both `aasm/ci-summary` and `aasm/formal-assurance` required on the exact commit;
- ✅ no release-asset overwrite or `--clobber` path;
- ✅ exact remote tag target, asset-name set, byte-size, and SHA-256 verification;
- ✅ `historical-release-report.json` with `VERIFIED`, `PENDING_OWNER_PUBLICATION`, and `MISMATCH` states;
- ✅ missing old tags no longer fail a valid current release;
- ✅ a real historical tag/commit mismatch still fails;
- ✅ current release evidence remains generated from ordinary source and the existing workflow.

## Exit gate

v0.28.1 is complete when:

1. Python 3.11–3.13 tests pass;
2. PostgreSQL and Docker Compose integration pass;
3. TLA+/TLC and Promela/SPIN pass on the exact commit;
4. two clean builds produce byte-identical wheel and source-distribution files;
5. the built wheel installs and runs the adoption-contract and runbook smoke tests;
6. the release is created once, never overwritten, and resolves to the exact tested commit;
7. all five remote assets match local names, sizes, and SHA-256 values;
8. historical release state is reported without privileged mutation of old workflow-bearing commits;
9. the public version, compatibility boundary, release process, and next phases are aligned;
10. no release operation mutates AASM machine state.

PyPI publication remains an external account-level gate. The repository-side Trusted Publisher job stays credential-free and opt-in.

---

# v0.29.0 — Thin LangGraph Adapter

## User outcome

An existing LangGraph application retains its graph, nodes, routing, and application-specific state while AASM supplies durable authority, evidence, conflict, effect, replay, and recovery underneath it.

## Required adapter boundary

The adapter must remain thin:

1. map one LangGraph thread/run to one AASM machine;
2. map selected graph decisions to named AASM decisions rather than serializing every framework object;
3. map required work to obligations with explicit terminal disposition;
4. attach node/tool outputs as evidence with producer and causal provenance;
5. require AASM authorization before declared external effects;
6. surface AASM recovery results—continue, repair, backjump, pause, restart, or fork—to the graph;
7. preserve LangGraph checkpointing only as framework state, not a competing authority record;
8. use `aasm.adoption.v1` rather than importing versioned runtime internals;
9. avoid a second scheduler, lease system, or event store;
10. keep AASM optional at the application boundary so adoption can be incremental.

## Planned implementation

- `aasm.integrations.langgraph` adapter package inside the existing distribution;
- typed thread/run binding and idempotent machine lookup;
- node-entry and node-exit hooks;
- decision, obligation, evidence, and effect mapping helpers;
- recovery directive mapping;
- contradiction-injection reference graph;
- ordinary-vs-AASM comparison harness;
- replay and observability views for the adapted run;
- compatibility documentation and runnable example;
- regression tests with LangGraph isolated as an optional dependency.

## Required comparison

The same controlled task runs:

```text
ordinary LangGraph workflow
versus
same LangGraph workflow with AASM underneath it
```

Both receive the same injected contradiction. The comparison must show:

- what the ordinary graph retries or loses;
- what the AASM-backed graph preserves;
- which assumption is invalidated;
- which unrelated work remains valid;
- what learned constraint blocks recurrence;
- where the causal backjump lands;
- how exact replay reconstructs the result.

## Exit gate

An existing LangGraph application adopts AASM without rewriting its graph, bypassing the canonical authority boundary, or storing AASM machine truth in framework-private state.

## Non-goals

- no replacement LangGraph runtime;
- no translation of every framework-internal class into an AASM ontology;
- no mandatory Planner/Builder topology;
- no provider-specific model bundle;
- no direct mutation of AASM snapshots or tables.

---

# v0.30.0 — Adapter Conformance Kit

## User outcome

A framework or application adapter can demonstrate—not merely claim—that it preserves AASM’s authority, replay, effect, and recovery contracts.

## Planned implementation

- framework-neutral adapter protocol and capability declaration;
- conformance fixture machines for success, contradiction, requirement change, lease loss, UNKNOWN effect, restart, and replay/fork;
- black-box test runner usable against Python adapters and remote HTTP adapters;
- semantic-result and evidence-provenance checks;
- duplicate-authority and direct-storage-write detection hooks;
- deterministic replay comparison;
- adapter scorecard with PASS, FAIL, and INCONCLUSIVE results;
- signed or hashed conformance report input for later provenance work;
- one additional thin adapter only after the kit proves the boundary is reusable.

## Exit gate

A third party can run one command against an adapter and receive a machine-readable report proving whether it preserves the supported AASM adoption contract.

## Non-goals

- no claim that the external framework itself is correct;
- no arbitrary code certification;
- no compatibility promise for framework-private internals;
- no adapter marketplace before conformance exists.

---

# v0.31.0 — Hierarchical Decision Scopes

## User outcome

Long-running work can separate strategy, architecture, and implementation decisions while retaining one authoritative machine and one causal conflict graph.

## Planned implementation

- explicit decision scopes and parent/child scope identities;
- scope-local obligations, evidence, locks, constraints, and fairness debt;
- cross-scope dependency edges with validated direction rules;
- causal backjump that may cross scopes only through recorded dependency paths;
- scope-aware restart that retains verified parent knowledge and disposes speculative descendants;
- scope inheritance and override rules;
- observability views for strategy → architecture → implementation lineage;
- policy preventing a child scope from silently replacing parent authority;
- migrations for existing flat decision records with backward-compatible defaults;
- bounded formal model additions for scope isolation and cross-scope recovery.

## Exit gate

A contradiction discovered in implementation can invalidate the responsible architecture or strategy decision without erasing unrelated sibling scopes or creating a second planner authority.

## Non-goals

- no mandatory organizational hierarchy;
- no role names baked into the kernel;
- no automatic promotion of local evidence into global truth;
- no unrestricted cross-scope mutation.

---

# v0.32.0 — Runtime/Formal Trace Conformance

## User outcome

A production event history can be projected into the bounded formal vocabulary and checked for step-by-step conformance, closing the gap between “the model passed” and “the runtime followed the modeled rule.”

## Planned implementation

- explicit abstraction map from production events/state to formal variables;
- typed trace-projection records with source event ranges and hashes;
- transition classifier for calculus, candidate activation, conflict learning, restart, completion, effects, and leases;
- conformance checker that distinguishes unsupported abstraction from actual violation;
- counterexample report linking a failed formal step to concrete event IDs;
- generated runtime traces from existing scenario and runbook tests;
- property-based bounded event-sequence generation;
- CI gate covering a representative production trace corpus;
- versioned abstraction contract so formal-model changes cannot silently reinterpret old histories.

## Exit gate

For every covered transition class, AASM can show that the production event sequence refines a legal formal transition or produce an exact counterexample tied to durable history.

## Non-goals

- no claim that bounded formal models prove arbitrary external adapters or domain evidence;
- no silent dropping of events that do not fit the abstraction;
- no replacement of production replay with a model checker.

---

# v0.33.0 — Signed Provenance and Verifiable Exports

## User outcome

A run can be exported as a portable evidence package that another party can verify without trusting the original AASM server.

## Planned implementation

- canonical export manifest for events, snapshots, definitions, profiles, certificates, artifacts, and observability projections;
- Merkle or equivalent content-addressed inventory with explicit algorithm/version identity;
- detached signatures through pluggable signer/verifier interfaces;
- key identity, rotation, revocation, and verification-policy records;
- selective disclosure packages that preserve hash linkage without exposing unrelated content;
- offline verification CLI;
- tamper, truncation, substitution, and wrong-key tests;
- export provenance visible in the Control Center;
- compatibility rules for re-verifying historical packages after software upgrades.

## Exit gate

A fresh environment can verify an exported run’s identity, completeness, hashes, signatures, certificate coverage, and replay evidence without database access or network trust in the producing server.

## Non-goals

- no bundled certificate authority;
- no assertion that signed evidence is factually true merely because it is authentic;
- no mandatory single cryptographic provider;
- no private-key storage in the AASM event stream.

---

# v0.34.0 — Distributed Recovery Certification

## User outcome

AASM can produce repeatable failure-injection evidence that distributed ownership, leases, effects, and recovery remain safe under crashes, partitions, stale workers, and ambiguous external outcomes.

## Planned implementation

- deterministic fault-injection harness for worker crash, lease expiry, delayed completion, duplicate delivery, network partition, database restart, and supervisor loss;
- controlled external-effect emulator covering NOT_STARTED, STARTED, SUCCEEDED, FAILED, and UNKNOWN outcomes;
- recovery invariants for single valid ownership, stale-result rejection, idempotency, reconciliation, and mandatory-obligation preservation;
- multi-process PostgreSQL scenarios and bounded schedule exploration;
- recovery certificate schema tied to exact scenario, configuration, trace, and software version;
- operator drill expansion and Control Center recovery timeline;
- formal coverage extensions for selected lease/effect ownership properties;
- conformance-kit integration for remote adapters.

## Exit gate

The release produces machine-readable evidence that every declared failure scenario either recovers without duplicated authority/effects or stops in an explicit state requiring human or external reconciliation.

## Non-goals

- no claim of arbitrary distributed-systems correctness;
- no unsafe automatic retry of UNKNOWN effects;
- no hiding of partition-induced uncertainty;
- no replacement of infrastructure-specific resilience testing.

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

## v0.28.0 — Distribution and Operator Readiness

- ✅ inspected wheel and source distribution;
- ✅ clean-wheel installation;
- ✅ compatibility policy;
- ✅ immutable release assets and checksums;
- ✅ Seven executable runbooks through the production runtime path.

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
| Reproducible distribution | two byte-identical builds | v0.28.1 |
| GitHub release assets and checksums | exact remote read-back | v0.28.1 |
| Historical tags | report-only unless owner publishes | v0.28.1 |
| Operator runbook scenario tests | required in CI | Implemented |
| PyPI installation | Trusted Publisher binding required | Repository side ready; external binding pending |
| Existing-framework adoption | one thin adapter | v0.29.0 |
| Adapter boundary proof | conformance report | v0.30.0 |
| Hierarchical reasoning | one authority across scopes | v0.31.0 |
| Runtime/formal correspondence | trace refinement check | v0.32.0 |
| Portable verification | signed offline package | v0.33.0 |
| Distributed recovery evidence | failure-injection certificate | v0.34.0 |

---

# Post-v0.34 research backlog

These remain valuable but do not displace the planned sequence:

- learned-constraint quality and aging policies inspired by LBD without making SAT mandatory;
- conflict-driven task/assumption activity scheduling inspired by VSIDS;
- Luby and adaptive knowledge-preserving restart policies;
- compositional formal models for larger machine families;
- privacy-preserving evidence disclosure;
- policy-controlled cross-machine learning;
- independently hosted conformance and provenance verification services.

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
