# AASM Roadmap

AASM is currently **v0.51.0 / Governed Solution Pools & Complete Enumeration**.

The roadmap is now explicitly **product-backward**: known destination properties must shape public contracts before implementation depth makes them expensive to add. A capability may be staged, but it may not be deferred in a way that makes the current architecture structurally incompatible with it.

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
- **v0.51.0 Governed Solution Pools & Complete Enumeration — Current**

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

The target decision problem includes, as policy-selectable dimensions:

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

These are not fixed global weights. AASM must support hard thresholds, lexicographic priorities, Pareto comparison, and explicit policy.

A weekly model/subscription allowance is a valid governed resource. AASM may reason over provider-controlled external capacity while preserving whether the measurement is authoritative, observed, derived, estimated, declared, or unknown.

## Cross-cutting public invariants

The following are architectural requirements now, not a post-solver afterthought:

1. **Scoped identity:** Principal / Workspace / Scope / Machine remain distinguishable.
2. **Scoped authority:** cross-scope access fails closed; authority and resource rights are separate.
3. **Proposal/commit boundary:** models, adapters, humans, and solvers propose; legal runtime transitions commit.
4. **Resource capacity:** owned, purchased, subscription, rolling, weekly, credit, compute, storage, worker, solver, and custom capacity share one governed abstraction.
5. **Resource provenance:** uncertain provider quota observations remain Evidence rather than silently becoming truth.
6. **Protected reserve:** remaining capacity may be intentionally unavailable to ordinary work.
7. **Proposal demand:** candidate work can declare expected resource demand, upper bounds, and uncertainty.
8. **Lease/reservation before consumption:** resource availability never grants authority; authority never grants unlimited resources.
9. **Reconciliation:** estimated and actual consumption remain distinct and durable.
10. **Dynamic replanning:** material estimate/capacity changes can invalidate an execution plan before silent overspend.
11. **Effect ownership:** external effects require authorization, idempotency/ownership, and explicit UNKNOWN reconciliation.
12. **Portable history:** exported public history must be sufficient for deterministic reconstruction without hidden hosted tables.
13. **Profile identity:** profile/package binding is versioned and migrated explicitly.
14. **Scope-safe inspection:** observability cannot depend on single-tenant global views.
15. **No privileged hosted bypass:** hosted operator machines must consume public runtime semantics rather than mutate around them.

# v0.52 — Resource-Governed Multi-Objective Decisions & Pareto Solving

v0.52 remains the multi-objective/Pareto release, but its purpose is broadened to establish the decision machinery required by real AASM resource allocation rather than treating optimization as solver-only functionality.

Primary contract targets:

```text
aasm.optimization.multi-objective.v1
aasm.optimization.frontier.v1
aasm.resource.capacity.v1
aasm.resource.observation.v1
aasm.resource.demand.v1
```

Required scope:

1. ordered objective vectors with explicit priority, sense, expression, tolerance, and hard thresholds;
2. full lexicographic solving where higher-priority optima cannot be degraded outside declared tolerances;
3. exact finite Pareto-frontier enumeration built on v0.51 solution enumeration;
4. nondominance and exact-frontier exhaustion evidence for supported finite models;
5. governed `ResourceCapacity` with finite/rolling/refilling/credit/unbounded/unknown windows;
6. explicit resource-observation authority: `AUTHORITATIVE | OBSERVED | DERIVED | ESTIMATED | DECLARED | UNKNOWN`;
7. principal/workspace/scope seams on resource capacity so later hosted isolation does not require replacement identity;
8. protected reserves and allocatable-capacity semantics;
9. proposal-side resource-demand estimates with expected amount, upper bound, unit, and confidence;
10. reservation/release/settlement semantics separating estimated commitment from actual consumption;
11. at least one conformance fixture representing a weekly external model/subscription allowance without hard-coding a provider into the kernel;
12. policy examples that jointly reason over correctness/evidence/progress and quota/cost/time/expert scarcity;
13. explicit re-estimation/replan trigger contract when expected consumption or available capacity materially changes;
14. compatibility with existing `ResourceRecord`, scheduler, economics, SII, scope, authority, and solver surfaces—no second scheduler or private accounting truth plane.

Hard completion criterion:

> On oracle-known finite multi-objective problems AASM reproduces the exact nondominated set and preserves lexicographic priorities; on resource-governance fixtures it must not allocate protected or unknown finite capacity as if freely available, must distinguish observed quota evidence from authoritative capacity, and must reconcile reservation with actual use without granting authority or truth.

# v0.53 — Scoped Identity/Authority Hardening + Durable Cross-Run Solver Learning

Primary goals:

- freeze Principal / Workspace / Scope / Machine semantics across durable records;
- make store/query APIs scope-safe by construction;
- formalize capability delegation, ceilings, expiry, and nondelegable denies;
- preserve current cross-run knowledge rule that source authority never becomes receiving-run authority;
- implement compatible cross-run solver learning (canonical no-goods/bounds/cores plus performance-only native accelerator state);
- make resource capacities, leases, observations, and consumption scope-aware without a retrofit.

Hard completion criterion:

> Cross-scope reads/writes and privilege amplification fail closed in adversarial tests, while compatible learned solver state remains reusable without inheriting foreign authority or truth.

# v0.54 — Effect Ownership & UNKNOWN Recovery + Certified Portfolio Exchange

Primary goals:

- public `EffectIntent` lifecycle;
- authorization before effect ownership;
- idempotency/ownership records;
- `CONFIRMED | FAILED | UNKNOWN` outcomes with explicit reconciliation;
- resource reservation before governed external execution and settlement after observation;
- deterministic multi-backend racing under leases/budgets;
- certified translation of exchanged incumbents, bounds, conflicts/no-goods, cores, and compatible solver state;
- no winner-by-speed or majority-vote truth shortcut.

Hard completion criterion:

> Crash/retry fixtures cannot silently duplicate or lose effect ownership, UNKNOWN effects remain unresolved until evidenced, and portfolio execution cannot consume resources outside its governed allocation.

# v0.55 — Portable Machine Archive + Extended Mathematical IR

Primary goals:

- versioned portable machine/workspace archive;
- events, profiles, decisions, obligations, evidence, certificates, constraints, solution pools, resource history, effect history, memory, fingerprints, and integrity manifest;
- deterministic replay from export without private hosted state;
- explicit profile/package binding and migration records;
- pseudo-Boolean/cardinality, richer scheduling/global constraints, additional conic/quadratic forms, and shared objective-vector IR;
- independent validation for every nontrivial translation.

Hard completion criterion:

> A portable archive reconstructs the same canonical observable state under the declared compatibility boundary, and no supported mathematical lowering can silently change semantic identity.

# v0.56 — Resource/Scope/Proof/Optimization Stress Corpus

Permanent corpora include:

- SAT/UNSAT and proof-grade negative claims;
- exact enumeration and solution pools;
- lexicographic and Pareto oracle-known problems;
- weekly/rolling/refilling external-capacity fixtures;
- protected-reserve exhaustion and replenishment cases;
- estimated-versus-actual consumption drift;
- cross-scope leakage and privilege-escalation attacks;
- effect UNKNOWN/reconciliation and duplicate-effect attacks;
- cold-vs-learned solver reuse;
- forged proof, stale bound, poisoned incumbent, false completeness, tolerance abuse, and false quota-authority cases.

Hard completion criterion:

> Every public capability claim in the tranche maps to reproducible positive, negative, and adversarial evidence; performance measurements remain environment-bound evidence rather than correctness claims.

# v0.57 — Semantic Solver RC2 + Public Hosted-Foundation Review

This is a subsystem and architectural-boundary reassessment, not a v1.0 declaration.

Required review:

- proof certificates;
- solution pools/enumeration;
- multi-objective/Pareto semantics;
- resource capacity/observation/demand contracts;
- scoped identity/authority;
- effect ownership/recovery;
- portable replay/export;
- cross-run solver learning and cross-solver exchange;
- profile migration and scope-safe inspection;
- claim-to-gate coverage for every public contract.

Hard completion criterion:

> Hosted AASM could be built as a consumer of public contracts without introducing a second authority, resource, effect, history, or truth system.

# After v0.57 — Resource-Aware SII and Hosted Product Fabric

The next public work should deepen, not reinvent, the above seams:

- SII proposals carry expected outcome, evidence quality, progress, resource demand, uncertainty, and alternatives;
- resource-aware routing selects among models, solvers, tools, humans, and local compute under policy;
- predicted versus actual consumption calibrates future estimates without becoming truth authority;
- scarcity uses remaining capacity, reset/refill horizon, protected reserve, consumption velocity, and forecast demand;
- scope-safe inspection explains why a resource/intelligence was selected and what was protected/consumed;
- profile binding/migration becomes stable enough for generated operator stacks.

The private Hosted AASM fabric then consumes those public contracts:

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

Private product policy may determine deployment topology and operator content, but it may not replace public scope, authority, resource, effect, replay, or commitment semantics.

# No Presumed v1.0

AASM does not infer v1.0 from version arithmetic. `0.x` remains architecture-expansion territory. A stable major requires a separate project-wide readiness review supported by migration guarantees, authority/safety evidence, replay guarantees, operational evidence, and field results.

# Permanent Engineering Doctrine

> **No known target capability may be deferred in a way that makes current public contracts structurally incompatible with it. Implementation may be staged; architectural accommodation may not.**

And:

> **Proposal is cheap. Commitment, authority, resource consumption, and external effects are not.**
