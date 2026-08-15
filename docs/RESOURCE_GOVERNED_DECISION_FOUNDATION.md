# Resource-Governed Decision Foundation

**Status:** released as the v0.52 public foundation; v0.53+ hardening builds on these contracts rather than replacing them.

## Product-backward requirement

AASM must be able to choose among legal ways of accomplishing work by jointly considering outcome quality, evidence strength, expected progress, provider quota burn, monetary cost, wall time, scarce expert-intelligence usage, and actual resource availability.

The governing product vector is:

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

These are governed dimensions, not one fixed kernel score. v0.52 exposes explicit ordered objectives, hard quality/capacity thresholds, and Pareto comparison while keeping proposal analysis separate from commitment and resource consumption.

## Governing loop

```text
CAPACITY / OBSERVATIONS
        ↓
GOVERNED SII PROPOSALS
  outcome claims + resource demand + quota/cost/time/scarcity
        ↓
FEASIBILITY GATES
  quality thresholds + scope + capacity + reserve + observation policy
        ↓
MULTI-OBJECTIVE ANALYSIS
  ├─ lexicographic policy
  └─ Pareto alternatives
        ↓
SELECTION + ATOMIC RESERVATION
        ↓
EXECUTION under ordinary AASM authority/effect rules
        ↓
REESTIMATE if assumptions change
  ├─ CONTINUE
  └─ REPLAN_REQUIRED → RELEASE → reroute
        ↓
SETTLE ACTUAL CONSUMPTION
        ↓
CALIBRATION EVIDENCE
        ↓
REPLAY / INSPECT / LEARN
```

There is no second hosted-only scheduler, optimizer, accounting truth system, or authority plane.

## Public v0.52 contracts

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

The v0.51 solution-pool/enumeration contracts remain the certified finite-space substrate used by exact v0.52 multi-objective claims.

## Capacity and observation semantics

A governed capacity can represent CPU/GPU time, solver calls, workers/concurrency, storage, API dollars/credits, provider/model credits, subscription allowances, rolling/weekly envelopes, human review, or a custom scarce resource.

Capacity windows:

```text
FIXED
ROLLING
REFILLING
CREDIT_BALANCE
UNBOUNDED
UNKNOWN
```

Resource observations preserve epistemic provenance:

```text
AUTHORITATIVE
OBSERVED
DERIVED
ESTIMATED
DECLARED
UNKNOWN
```

An observation is Evidence. It never silently becomes provider truth.

### Protected reserve and planning capacity

```text
total
- consumed
- committed
- protected_reserve
= declared allocatable
```

A qualifying observation may reduce the amount AASM is willing to allocate:

```text
planning allocatable = min(
  declared allocatable,
  accepted observed remaining - committed - protected reserve
)
```

It may never increase the declared envelope or turn `UNKNOWN` declared capacity into spendable capacity.

Default accepted observation authority is conservative; `DECLARED` requires policy opt-in. Confidence and freshness can also gate whether an observation participates in planning.

## Resource-aware SII proposals

`aasm.sii.resource-aware-proposal.v1` is additive over the governed SII parent proposal.

Its identity binds:

```text
parent proposal ID + fingerprint
resource demands + upper bounds
expected correctness
expected evidence quality
expected progress
expected wall time
expected monetary cost
expected provider quota burn
expected scarce expert usage
metadata
```

Provider quota burn is explicit. It is not inferred from provider names or another resource dimension.

A v0.52 successor cannot bypass governed SII admission. The durable lineage is:

```text
governed parent SII proposal
        ↓ exact parent/proposer/scope binding
resource-aware successor Evidence
        ↓ derived_from
routing / frontier / reservation Evidence
```

Missing correctness/evidence/progress estimates fail closed during routing compilation. Proposer confidence is not reinterpreted as correctness or evidence quality.

## Governed resource-routing objectives

`ResourceRoutingPolicy` owns an ordered objective vector. The default is:

```text
0  correctness            MAXIMIZE
1  evidence_quality       MAXIMIZE
2  expected_progress      MAXIMIZE
3  provider_quota_burn    MINIMIZE
4  scarce_expert_usage    MINIMIZE
5  monetary_cost          MINIMIZE
6  wall_time_seconds      MINIMIZE
```

Policy may reorder or omit economic objectives. Hard quality/capacity gates remain separate from preference ordering, so a cheap candidate cannot bypass required correctness or evidence.

A durable routing explanation records:

- exact ordered objective policy;
- candidate objective vectors;
- declared and planning allocatable capacity;
- protected reserve;
- reset horizon;
- latest observation/provenance;
- selection decision;
- resulting reservation.

That is the public support/operator explanation seam. Hosted AASM does not need a private decision-explanation truth table.

## Exact finite lexicographic solving

`aasm.optimization.multi-objective.v1` uses the v0.51 certified finite enumeration path.

For each objective it:

1. computes the exact stage optimum over current survivors;
2. admits only points within the declared tolerance;
3. advances to the next objective;
4. deterministically selects from the final survivor set;
5. independently reconstructs the stage optima and survivor trace.

Higher-priority degradation outside declared tolerance is not legal.

## Two Pareto semantics

### Exact finite optimization frontier

`aasm.optimization.frontier.v1` can claim `COMPLETE` only over a supported finite model whose feasible space was independently exhausted and certified.

The independent frontier checker reconstructs the finite feasible space again. `exact_solution_set_match` has a stronger normative meaning than its historical field name might imply: exact equality of **solution IDs, assignments, and objective vectors**.

A forged point that reuses a legitimate solution ID but changes the assignment or objective values fails certification.

Pareto dominance is tolerance-aware:

- no-worse comparison honors objective tolerance;
- strict improvement must exceed tolerance.

### Resource-candidate frontier

`resource_candidate_pareto_frontier()` is exact over the finite supplied eligible candidate set after hard quality/capacity gates.

It does **not** claim that no undiscovered route exists elsewhere.

Resource-candidate Pareto analysis is non-committing:

```text
candidate proposals
      ↓
capacity/quality feasibility
      ↓
Pareto analysis
      ↓
durable frontier Evidence
      ↓
NO resource mutation
```

A separate selection/reservation operation is required before consumption can occur.

## Selection and reservation

Selection does not itself consume capacity. The selected candidate's conservative demand envelope must be reserved before execution.

Atomic reservation semantics:

1. use demand upper bounds when present;
2. resolve explicit resource IDs directly;
3. resolve class-only demand deterministically;
4. preflight the complete allocation without mutation;
5. if any required resource is infeasible, reserve nothing;
6. commit every allocation only after the whole plan is feasible.

Selection + reservation is persisted as one durable transaction Evidence document.

## Re-estimation, release, settlement

A long-running task can change its expected demand.

```text
ACTIVE
  ↓ feasible reestimate
CONTINUE → ACTIVE with revised allocation

ACTIVE
  ↓ infeasible reestimate
REPLAN_REQUIRED
```

`REPLAN_REQUIRED` preserves the existing reservation and prevents silent overspend. `release_resource_reservation()` frees it so work can be rerouted.

Settlement requires exact reserved-resource keys and reconciles committed capacity against actual use.

Predicted-versus-actual history is exposed through `resource_consumption_calibration_report()` as `PERFORMANCE_EVIDENCE_ONLY`, including reserved total, actual total, signed error, absolute error, and actual/reserved ratio.

Calibration is evidence for future estimator learning; it is not itself truth authority.

## Durable Evidence and replay

`runtime_v52` persists through the ordinary AASM Evidence/event path:

- capacity registration;
- resource observations;
- resource-aware SII successors;
- selection + reservation;
- routing explanations;
- resource-candidate Pareto frontiers;
- re-estimation;
- release;
- settlement;
- calibration projection;
- complete feasible pools;
- independent enumeration certificates;
- verified lexicographic results;
- exact Pareto certificates/frontiers.

No partial accepted multi-objective history is recorded when finite-space solving/certification fails.

## Scope-safe resource access

Workspace and scope are enforced on v0.52 resource operations.

For scoped capacity:

```text
workspace_id must match
AND
caller scope must be allowed by the existing AASM scope-flow relation
```

Wrong workspace, missing context, unknown scope, cross-workspace observation/settlement, and cross-workspace inspection fail closed or expose no records as appropriate.

This is **scope enforcement**, not yet the final principal-authority calculus. Central Principal / Workspace / Scope delegation, capability ceilings, expiry, and nondelegable denies are v0.53 public hardening.

## Authority boundary

Resource rights and action authority remain distinct:

```text
Authority: may this principal perform this action in this scope?
Capacity:  may this work consume these resources?
```

Both can be required.

Permanent v0.52 invariants:

```text
RESOURCE STATE NEVER GRANTS AUTHORITY.
RESOURCE OBSERVATIONS REMAIN EVIDENCE.
OPTIMALITY / PARETO COMPLETENESS REMAIN EVIDENCE.
SII UTILITY NEVER BUYS TRUTH OR STATE AUTHORITY.
```

## Release conformance

v0.52 adds a dedicated source/schema/adversarial gate plus real native optimization/modeling execution. The exact-SHA status `aasm/optimization` is successful only when both jobs pass.

Release publication requires:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
aasm/solution-pools
aasm/optimization
```

## v0.53+ hardening

The next public layer builds on these contracts rather than replacing them:

- central principal-scoped authority/delegation and nondelegable denies;
- distributed reservation/lease ownership across worker processes;
- durable cross-run solver/resource learning without authority inheritance;
- provider meter adapters mapped into generic observations;
- learned resource estimation from calibration Evidence;
- richer scarcity forecasting from reset/refill horizon, reserve, burn velocity, and forecast demand;
- effect ownership/UNKNOWN recovery and later portable machine archives.

## Permanent architectural rule

> **No known target capability may be deferred in a way that makes current public contracts structurally incompatible with it. Implementation may be staged; architectural accommodation may not.**

> **Proposal is cheap. Commitment, authority, resource consumption, and external effects are not.**
