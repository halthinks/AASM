# AASM Roadmap

AASM is currently **v0.53.0 / Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening**.

The roadmap is explicitly **product-backward**: known destination properties must shape public contracts before implementation depth makes them expensive to add. A capability may be staged, but it may not be deferred in a way that makes the current architecture structurally incompatible with it.

## Released

- v0.35.0 Semantic Problem Model Foundations
- v0.36.0 Semantic Compiler SDK
- v0.37.0 Reasoning Artifacts and Epistemic Admission
- v0.38.0 Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- v0.39.0 Typed Capability ABI and Formal Verification Workers
- v0.40.0 Hierarchical Memory, Reasoning Frontier, and Context Projection
- v0.41.0 Domain-Neutral Solver Loop and Deterministic Reuse Plane
- v0.42.0 Reference Domains & Reuse/Memory/Reasoning Stress Tests
- v0.43.0 Semantic Conformance, Adversarial Domains, and Certification
- v0.44.0 Heterogeneous Optimization Solver Portfolio
- v0.45.0 Convex Optimization & Modeling Adapters
- v0.46.0 Advanced Solver Control & Search Artifacts
- v0.47.0 Governed Symbiotic Intelligence & Intelligence Economics
- v0.47.1 Apache-2.0 License Transition
- v0.48.0 Cross-Run Certified Knowledge & Governed Long-Term Memory
- v0.48.1 Project-Wide Apache-2.0 Policy Correction
- v0.49.0 Semantic Solver Release Candidate
- v0.50.0 Proof-Carrying Solver Claims
- v0.51.0 Governed Solution Pools & Complete Enumeration
- v0.52.0 Resource-Governed Multi-Objective Decisions & Pareto Solving
- **v0.53.0 Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening — Current Release**

## Product destination that constrains the next releases

AASM is being engineered toward a public deterministic governance/runtime substrate that can support both self-hosted use and a private hosted operating fabric without private semantic shortcuts.

A governed machine must ultimately be able to decide:

```text
what work should happen
who/what should do it
what evidence/correctness threshold is required
what resources may be consumed
whether scarce capacity should be preserved
whether a cheaper or stronger alternative dominates
when to pause, replan, fall back, or request approval/capacity
what actually happened and what it consumed
how the run can be exported and replayed without hosted-only state
```

The decision vector established in v0.52 remains policy-selectable:

```text
maximize:
  correctness
  evidence quality
  expected progress

minimize:
  provider quota burn
  monetary cost
  wall time
  scarce expert-model usage
```

These are not fixed global weights. AASM supports hard thresholds, governed lexicographic priorities, Pareto comparison, and explicit policy.

A weekly model/subscription allowance is a valid governed resource. AASM may reason over provider-controlled external capacity while preserving whether the measurement is authoritative, observed, derived, estimated, declared, or unknown.

## Cross-cutting public invariants

1. **Scoped identity:** Principal / Workspace / Scope / Machine remain distinguishable.
2. **Scoped authority:** cross-scope access fails closed; authority and resource rights are separate.
3. **Proposal/commit boundary:** models, adapters, humans, and solvers propose; legal runtime transitions commit.
4. **Resource capacity:** owned, purchased, subscription, rolling, weekly, credit, compute, storage, worker, solver, and custom capacity share one governed abstraction.
5. **Resource provenance:** uncertain provider quota observations remain Evidence rather than silently becoming truth.
6. **Protected reserve:** remaining capacity may be intentionally unavailable to ordinary work.
7. **Proposal demand:** candidate work can declare expected resource demand, upper bounds, uncertainty, quota/cost/time/scarcity estimates.
8. **Lease/reservation before consumption:** resource availability never grants authority; authority never grants unlimited resources.
9. **Reconciliation:** estimated and actual consumption remain distinct and durable.
10. **Dynamic replanning:** material estimate/capacity changes can invalidate an execution plan before silent overspend.
11. **Effect ownership:** external effects require authorization, idempotency/ownership, and explicit UNKNOWN reconciliation.
12. **Portable history:** exported public history must be sufficient for deterministic reconstruction without hidden hosted tables.
13. **Profile identity:** profile/package binding is versioned and migrated explicitly.
14. **Scope-safe inspection:** observability cannot depend on single-tenant global views.
15. **No privileged hosted bypass:** hosted operator machines must consume public runtime semantics rather than mutate around them.

# v0.52.0 — Resource-Governed Multi-Objective Decisions & Pareto Solving

**Status: released / frozen parent of v0.53.**

Public contracts:

```text
aasm.optimization.multi-objective.v1 / 0.1.0
aasm.optimization.frontier.v1 / 0.1.0
aasm.resource.capacity.v1 / 0.1.0
aasm.resource.observation.v1 / 0.1.0
aasm.resource.demand.v1 / 0.1.0
aasm.resource.routing.v1 / 0.1.0
aasm.resource.runtime.v1 / 0.1.0
aasm.sii.resource-aware-proposal.v1 / 0.1.0
```

Delivered:

- exact finite lexicographic optimization over v0.51 certified complete enumeration;
- exact finite Pareto frontier with independent full-point equality certification;
- tolerance-aware Pareto dominance and lexicographic survivor semantics;
- durable `EVIDENCE_ONLY` multi-objective problems/results/certificates;
- governed capacity windows and observation provenance;
- protected reserves and fail-closed unknown capacity;
- resource-aware governed SII successor proposals;
- explicit correctness/evidence/progress/quota/cost/time/expert-scarcity vector;
- policy-controlled resource objective ordering;
- exact Pareto analysis over supplied eligible resource candidates without commitment;
- atomic selection + reservation before consumption;
- durable re-estimation with `CONTINUE | REPLAN_REQUIRED`, release, settlement, and calibration evidence;
- workspace/scope-safe resource inspection;
- replayable routing explanations;
- exact-SHA `aasm/optimization` release gate.

Two Pareto claims remain deliberately distinct:

1. **Exact finite optimization frontier** — complete relative to the supported independently exhausted finite model space.
2. **Resource-candidate frontier** — exact only over the supplied eligible candidate set; it makes no route-discovery completeness claim.

Neither optimality, frontier completeness, resource availability, nor SII utility grants truth or authority.

# v0.53.0 — Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening

**Status: released / current.**

Public contracts and runtime surfaces:

```text
aasm.identity.scoped.v1 / 0.1.0
aasm.authority.scoped.v1 / 0.1.0
aasm.authority.scoped.runtime.v1 / 0.1.0
aasm.store.scoped.v1 / 0.1.0
aasm.solver.learning.v1 / 0.1.0
aasm.solver.learning.runtime.v1 / 0.1.0
aasm.solver.learning.application.v1 / 0.1.0
aasm.adoption.v1 / 0.29.0
```

Delivered:

- durable Principal / Workspace / Scope / Machine identity separation;
- explicit scoped ALLOW/DENY authority with default deny and DENY precedence;
- delegation ceilings for capability, scope, depth, expiry, and nondelegable grants;
- delegated wildcard prohibition and fail-closed malformed/unknown scopes;
- source/cross-run authority remains provenance only and never becomes receiving authority;
- `aasm.store.scoped.v1` read-only fail-closed persistence facade for raw machine/effect access;
- resource capacity/observation/reservation/re-estimate/release/settlement operations require scoped capabilities;
- principal-aware resource history derived from exact durable authorization Evidence rather than duplicated actor fields;
- optimistic machine-version guarded resource Evidence commits preventing two stale hosts from committing conflicting reservations;
- stale-writer canonical reload verified on MemoryStore, SQLite, and PostgreSQL;
- scope-bound external effect proposals with separate `effect.authorize`, `effect.execute`, and `effect.reconcile` authority;
- fresh authorization before each external execution attempt, preventing expired/revoked grants from being bypassed by retries;
- durable solver-learning artifacts for `NO_GOOD`, `UNSAT_CORE`, `BOUND`, `INCUMBENT`, `WARM_START`, and `NATIVE_ACCELERATOR`;
- cross-run solver learning carried through the existing v0.48 `REUSE_RESULT` envelope/admission pathway;
- correctness-sensitive imported learning remains inert until receiving-run exact local revalidation;
- foreign solver learning never imports truth, policy authority, resource entitlement, or source authority;
- explicit `aasm.solver.learning.application.v1` separating validation from application;
- scoped `solver.learning.apply` required for application;
- certified pruning lowered into a new canonical optimization model and routed through the existing provider path;
- validated incumbent/warm-start hints remain performance-only and are explicitly consumed by the existing OR-Tools CP-SAT adapter via `CpModel.add_hint(...)`;
- dedicated exact-SHA `aasm/scoped-authority` and `aasm/solver-learning` release gates;
- release publication hardened to require those gates in addition to CI, formal assurance, RC, proof, solution-pool, and optimization gates.

Hard completion criterion satisfied:

> Cross-scope reads/writes, privilege amplification, cross-principal resource misuse, stale distributed reservations, unscoped effect execution, and unvalidated foreign solver learning fail closed in adversarial tests, while compatible learned solver/resource state remains reusable without inheriting foreign authority or truth.

# v0.54.0 — Certified Cross-Solver Exchange & Deterministic Portfolio Racing + Effect Ownership/UNKNOWN Recovery

**Next active layer.**

Primary goals:

- public `EffectIntent` lifecycle;
- certified effect ownership handoff/recovery beyond the v0.53 scoped authorization foundation;
- stronger idempotency/ownership records across distributed executors;
- `CONFIRMED | FAILED | UNKNOWN` outcomes with explicit reconciliation;
- resource reservation before governed external execution and settlement after observation;
- deterministic multi-backend/model racing under leases/budgets;
- certified translation of exchanged incumbents, bounds, conflicts/no-goods, cores, and compatible solver state;
- no winner-by-speed or majority-vote truth shortcut.

Hard completion criterion:

> Crash/retry fixtures cannot silently duplicate or lose effect ownership, UNKNOWN effects remain unresolved until evidenced, and portfolio execution cannot consume resources outside its governed allocation.

# v0.55.0 — Extended Mathematical IR + Portable Machine Archive

Primary goals:

- versioned portable machine/workspace archive;
- events, profiles, decisions, obligations, evidence, certificates, constraints, solution pools, resource history, effect history, memory, fingerprints, and integrity manifest;
- deterministic replay from export without private hosted state;
- explicit profile/package binding and migration records;
- pseudo-Boolean/cardinality, richer scheduling/global constraints, additional conic/quadratic forms, and shared objective-vector IR;
- independent validation for every nontrivial translation.

Hard completion criterion:

> A portable archive reconstructs the same canonical observable state under the declared compatibility boundary, and no supported mathematical lowering can silently change semantic identity.

# v0.56.0 — Proof/Enumeration/Optimization/Resource/Scope Stress Corpus

Permanent Stress Corpus coverage includes:

- SAT/UNSAT and proof-grade negative claims;
- exact enumeration and solution pools;
- lexicographic and Pareto oracle-known problems;
- weekly/rolling/refilling external-capacity fixtures;
- protected-reserve exhaustion/replenishment;
- resource-aware SII routing across model/solver/tool paths;
- estimated-versus-actual consumption drift and replanning;
- cross-scope leakage and privilege-escalation attacks;
- effect UNKNOWN/reconciliation and duplicate-effect attacks;
- cold-vs-learned solver/resource reuse;
- forged proof, stale bound, poisoned incumbent, false completeness, tolerance abuse, false frontier content, and false quota-authority cases.

Hard completion criterion:

> Every public capability claim in the tranche maps to reproducible positive, negative, and adversarial evidence; performance measurements remain environment-bound Evidence rather than correctness claims.

# v0.57.0 — Semantic Solver RC2 / Contract Review + Public Hosted-Foundation Review

This is a subsystem and architectural-boundary reassessment, not a v1.0 declaration.

Required review:

- proof certificates;
- solution pools/enumeration;
- multi-objective/Pareto semantics;
- resource capacity/observation/demand/routing contracts;
- resource-aware SII routing and estimate/actual reconciliation;
- scoped identity/authority;
- effect ownership/recovery;
- portable replay/export;
- cross-run solver/resource learning and cross-solver exchange;
- profile migration and scope-safe inspection;
- claim-to-gate coverage for every public contract.

Hard completion criterion:

> Hosted AASM could be built as a consumer of public contracts without introducing a second authority, resource, effect, history, decision-routing, or truth system.

# After v0.57 — Private Hosted Product Fabric and Further Public Hardening

Resource-aware SII and the product objective vector are public v0.52 semantics; scoped authority/store boundaries and cross-run solver learning are public v0.53 semantics; all are hardened further through v0.57.

Public hardening may continue with:

- learned resource-estimate calibration from predicted-versus-actual history;
- richer scarcity policies using remaining capacity, reset/refill horizon, protected reserve, consumption velocity, and forecast demand;
- scoped principal-authority delegation and capability-ceiling maturity;
- profile binding/migration maturity for generated operator stacks;
- provider adapters mapping external usage telemetry into the generic observation contract without becoming kernel dependencies.

The private Hosted AASM fabric consumes the public contracts:

```text
Fabric Root Policy
Bootstrap
Tenancy
Provisioning
Usage
Resource Broker
Health
Upgrade
Support
Portal / API gateway / billing / isolation topology
```

Private product policy may determine deployment topology and operator content, but it may not replace public scope, authority, resource, effect, replay, decision-routing, or commitment semantics.

# No Presumed v1.0

AASM does not infer v1.0 from version arithmetic. `0.x` remains architecture-expansion territory. A stable major requires a separate project-wide readiness review supported by migration guarantees, authority/safety evidence, replay guarantees, operational evidence, and field results.

# Permanent Engineering Doctrine

> **No known target capability may be deferred in a way that makes current public contracts structurally incompatible with it. Implementation may be staged; architectural accommodation may not.**

> **Proposal is cheap. Commitment, authority, resource consumption, and external effects are not.**
