# AASM Roadmap

AASM is currently **v0.51.0 / Governed Solution Pools & Complete Enumeration** with **v0.52 under active implementation and freeze review**.

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
- **v0.51.0 Governed Solution Pools & Complete Enumeration — Current Release**

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

These are not fixed global weights. AASM supports hard thresholds, governed lexicographic priorities, Pareto comparison, and explicit policy.

A weekly model/subscription allowance is a valid governed resource. AASM may reason over provider-controlled external capacity while preserving whether the measurement is authoritative, observed, derived, estimated, declared, or unknown.

## Cross-cutting public invariants

The following are architectural requirements now, not a post-solver afterthought:

1. **Scoped identity:** Principal / Workspace / Scope / Machine remain distinguishable.
2. **Scoped authority:** cross-scope access fails closed; authority and resource rights are separate.
3. **Proposal/commit boundary:** models, adapters, humans, and solvers propose; legal runtime transitions commit.
4. **Resource capacity:** owned, purchased, subscription, rolling, weekly, credit, compute, storage, worker, solver, and custom capacity share one governed abstraction.
5. **Resource provenance:** uncertain provider quota observations remain Evidence rather than silently becoming truth.
6. **Protected reserve:** remaining capacity may be intentionally unavailable to ordinary work.
7. **Proposal demand:** candidate work can declare expected resource demand, upper bounds, uncertainty, and explicit quota/cost/time/scarcity estimates.
8. **Lease/reservation before consumption:** resource availability never grants authority; authority never grants unlimited resources.
9. **Reconciliation:** estimated and actual consumption remain distinct and durable.
10. **Dynamic replanning:** material estimate/capacity changes can invalidate an execution plan before silent overspend.
11. **Effect ownership:** external effects require authorization, idempotency/ownership, and explicit UNKNOWN reconciliation.
12. **Portable history:** exported public history must be sufficient for deterministic reconstruction without hidden hosted tables.
13. **Profile identity:** profile/package binding is versioned and migrated explicitly.
14. **Scope-safe inspection:** observability cannot depend on single-tenant global views.
15. **No privileged hosted bypass:** hosted operator machines must consume public runtime semantics rather than mutate around them.

# v0.52.0 — Lexicographic Multi-Objective & Pareto Solving — Resource-Governed Decision Foundation

**Status: active implementation; semantic core delivered; freeze/conformance work remains.**

v0.52 establishes the multi-objective decision machinery required by real AASM resource allocation rather than treating optimization as solver-only functionality.

Primary public contracts now implemented on the experimental path:

```text
aasm.optimization.multi-objective.v1
aasm.optimization.frontier.v1
aasm.resource.capacity.v1
aasm.resource.observation.v1
aasm.resource.demand.v1
aasm.resource.routing.v1
aasm.resource.runtime.v1
aasm.sii.resource-aware-proposal.v1
```

## Delivered v0.52 semantic core

### Exact finite multi-objective solving

Implemented:

1. ordered objectives with explicit identity, priority, sense, coefficients, offset, and tolerance;
2. exact finite lexicographic solving over the v0.51 complete-enumeration substrate;
3. independent replay/reconstruction of lexicographic stage optima and survivor sets;
4. exact finite Pareto-frontier construction over an independently certified complete feasible set;
5. independent frontier verification requiring exact equality of solution IDs, assignments, and objective vectors;
6. fail-closed rejection of dominated, missing, or forged frontier content;
7. durable `EVIDENCE_ONLY` persistence of problems, complete feasible pools, enumeration certificates, lexicographic results, Pareto certificates, and complete frontiers;
8. no partial accepted multi-objective history when enumeration/certification fails.

### Resource capacity and external quota evidence

Implemented:

1. finite / rolling / refilling / credit / unbounded / unknown capacity windows;
2. resource-observation authority classes `AUTHORITATIVE | OBSERVED | DERIVED | ESTIMATED | DECLARED | UNKNOWN`;
3. protected reserves and declared allocatable capacity;
4. policy-controlled observation-backed planning capacity that may reduce but never create capacity;
5. confidence/freshness/measurement-authority gates;
6. workspace/scope-safe resource visibility and mutation through the existing AASM scope-flow model;
7. fail-closed unknown finite capacity.

### Resource-aware governed proposals

Implemented:

1. additive v0.52 SII successor over the frozen parent proposal contract;
2. exact binding to an already-durable governed parent proposal;
3. identity/fingerprint coverage for resource demands and expected correctness/evidence/progress;
4. explicit expected wall time, monetary cost, **provider quota burn**, and scarce-expert usage;
5. durable successor → routing/frontier Evidence lineage;
6. proposer confidence never substituted for correctness/evidence quality.

### Governed objective policy

Resource routing no longer owns one permanent ranking tuple.

The default objective policy is:

```text
0 correctness            MAXIMIZE
1 evidence_quality       MAXIMIZE
2 expected_progress      MAXIMIZE
3 provider_quota_burn    MINIMIZE
4 scarce_expert_usage    MINIMIZE
5 monetary_cost          MINIMIZE
6 wall_time_seconds      MINIMIZE
```

Policy can reorder or omit economic dimensions while hard quality/capacity gates remain separate.

Adversarial fixtures now demonstrate that:

- a quota-preserving route can beat a cheaper-money route under default policy;
- a money-first policy deterministically reverses that result;
- lower price never bypasses a hard correctness/evidence threshold.

### Resource Pareto semantics

Implemented two deliberately different frontier claims:

1. **Certified exact finite optimization frontier** — complete relative to the supported independently exhausted finite model space.
2. **Resource-candidate frontier** — exact only over the supplied eligible candidate set after hard quality/capacity gates; it does not claim that no undiscovered route exists.

Resource-candidate Pareto analysis is durable but non-committing: it records objective vectors, policy, capacity-visible context, and nondominated candidate IDs without reserving capacity.

### Resource commitment lifecycle

Implemented:

```text
proposal
  ↓
select + reserve atomically
  ↓
execute under ordinary authority/effect rules
  ↓
reestimate
  ├─ CONTINUE
  └─ REPLAN_REQUIRED
        ↓
      RELEASE → reroute
  ↓
settle actual use
  ↓
calibration Evidence
```

Selection + reservation is persisted as one durable transaction. Re-estimation preserves existing capacity when a larger request becomes infeasible instead of silently overspending. Settlement reconciles committed versus actual use. Predicted-versus-actual calibration is exposed as performance Evidence only.

### Replayable decision explanation

Routing explanations now persist:

- exact ordered objective policy;
- candidate objective vectors;
- declared/planning allocatable capacity;
- protected reserve;
- reset horizon;
- latest capacity observation/provenance;
- selected candidate and reservation.

This is the support/operator inspection seam needed later by Hosted AASM without adding a private explanation truth table.

## v0.52 freeze blockers

v0.52 is **not released yet**. Remaining work before promotion:

1. complete exact-head CI after the final contract/schema/document changes;
2. add a dedicated v0.52 conformance/release-contract gate that checks the new contracts together rather than relying only on broad pytest;
3. freeze tolerance-aware Pareto dominance semantics explicitly;
4. decide before freeze whether `exact_solution_set_match` should be renamed to `exact_point_set_match` because the implemented check is stronger than ID-set equality;
5. validate public packaging/exports for the intended v0.52 surface;
6. update README, CURRENT_RELEASE, CHANGELOG, package metadata, release history, and release notes only after the above gates pass.

Hard completion criterion:

> On oracle-known finite multi-objective problems AASM reproduces and independently certifies the exact nondominated point set and preserves lexicographic priorities; on resource-governance fixtures it does not allocate protected or unknown finite capacity as freely available, preserves observation provenance, can compare alternative routes using policy-selected quality/quota/cost/time/scarcity dimensions, keeps Pareto analysis non-committing, atomically reserves the selected route, and reconciles reservation with actual use without granting authority or truth.

# v0.53.0 — Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening

Primary goals:

- freeze Principal / Workspace / Scope / Machine semantics across durable records;
- make store/query APIs scope-safe by construction;
- formalize capability delegation, ceilings, expiry, and nondelegable denies;
- preserve current cross-run knowledge rule that source authority never becomes receiving-run authority;
- implement compatible durable cross-run solver learning (canonical no-goods/bounds/cores plus performance-only native accelerator state);
- make resource capacities, leases, observations, consumption, and learned resource-estimation evidence principal-aware without a retrofit.

Hard completion criterion:

> Cross-scope reads/writes and privilege amplification fail closed in adversarial tests, while compatible learned solver/resource state remains reusable without inheriting foreign authority or truth.

# v0.54.0 — Certified Cross-Solver Exchange & Deterministic Portfolio Racing + Effect Ownership/UNKNOWN Recovery

Primary goals:

- public `EffectIntent` lifecycle;
- authorization before effect ownership;
- idempotency/ownership records;
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
- protected-reserve exhaustion and replenishment cases;
- resource-aware SII routing across alternative model/solver/tool paths;
- estimated-versus-actual consumption drift and replanning;
- cross-scope leakage and privilege-escalation attacks;
- effect UNKNOWN/reconciliation and duplicate-effect attacks;
- cold-vs-learned solver/resource reuse;
- forged proof, stale bound, poisoned incumbent, false completeness, tolerance abuse, false frontier content, and false quota-authority cases.

Hard completion criterion:

> Every public capability claim in the tranche maps to reproducible positive, negative, and adversarial evidence; performance measurements remain environment-bound evidence rather than correctness claims.

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

Resource-aware SII and the full product objective vector are **not** deferred to this phase; their first governed implementation is a v0.52 requirement and is hardened through v0.57.

Public hardening may continue with:

- learned resource-estimate calibration from predicted-versus-actual history;
- richer scarcity policies using remaining capacity, reset/refill horizon, protected reserve, consumption velocity, and forecast demand;
- central principal-authority delegation and capability ceilings;
- profile binding/migration maturity for generated operator stacks;
- additional provider adapters that map external usage telemetry into the generic observation contract without becoming kernel dependencies.

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

And:

> **Proposal is cheap. Commitment, authority, resource consumption, and external effects are not.**
