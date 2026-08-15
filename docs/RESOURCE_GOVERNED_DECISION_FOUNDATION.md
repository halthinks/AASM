# Resource-Governed Decision Foundation

**Status:** active implementation foundation for the v0.52 program; not yet a v0.52 release-completion claim.

## Product-backward requirement

AASM must be able to choose among legal ways of accomplishing work by jointly considering outcome quality, evidence strength, expected progress, provider quota burn, monetary cost, wall time, scarce expert-intelligence usage, and actual resource availability.

This is a known destination capability. It is therefore part of the architecture now, not an “eventual” enhancement.

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

These dimensions are not fixed global weights. AASM now supports explicit ordered routing objectives, hard quality thresholds, and Pareto comparison while keeping commitment/resource consumption separate from proposal analysis.

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

AASM does not create a second hosted-only scheduler, optimizer, accounting truth system, or authority plane for this work.

## Capacity and observation semantics

A governed capacity can represent CPU/GPU time, solver calls, workers/concurrency, storage, API dollars/credits, provider/model credits, subscription allowances, rolling/weekly envelopes, human review, or custom scarce resources.

The public capacity model supports:

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

An observation is Evidence. It is never silently promoted to provider truth.

### Protected reserve

```text
total
- consumed
- committed
- protected_reserve
= declared allocatable
```

`planning_allocatable()` may further reduce that amount from an accepted latest observation, but may never expand it:

```text
planning allocatable = min(
  declared allocatable,
  accepted observed remaining - committed - protected reserve
)
```

Default accepted observation authorities are `AUTHORITATIVE`, `OBSERVED`, and `DERIVED`. `DECLARED` requires explicit policy opt-in. Confidence and freshness can also gate whether an observation constrains planning.

Critical invariant:

> An observation may reduce what AASM is willing to spend. It never creates capacity that the declared resource envelope did not already grant.

## Resource-aware SII proposal contract

`aasm.sii.resource-aware-proposal.v1` is an additive successor over the frozen governed SII proposal contract.

Its identity now binds:

```text
parent proposal ID + fingerprint
resource demands
expected correctness
expected evidence quality
expected progress
expected wall time
expected monetary cost
expected provider quota burn
expected scarce expert usage
metadata
```

`provider quota burn` is explicit. It is not guessed from provider names or inferred from another resource field.

Missing correctness/evidence/progress estimates fail closed to zero during routing compilation. Proposer confidence is not reinterpreted as correctness or evidence quality.

A successor cannot bypass governed SII admission:

```text
governed durable parent SII proposal
        ↓ exact parent/proposer/scope binding
resource-aware successor Evidence
        ↓ derived_from
routing / Pareto Evidence
```

## Governed resource-routing objectives

`aasm.resource.routing.v1` now carries a typed ordered objective policy rather than a hard-coded ranking tuple.

The default backward-compatible policy is:

```text
0  correctness            MAXIMIZE
1  evidence_quality       MAXIMIZE
2  expected_progress      MAXIMIZE
3  provider_quota_burn    MINIMIZE
4  scarce_expert_usage    MINIMIZE
5  monetary_cost          MINIMIZE
6  wall_time_seconds      MINIMIZE
```

A policy may reorder or omit economic objectives. For example, a money-first policy can choose a cheaper route over a quota-preserving route when both satisfy the same hard quality gates.

Quality/capacity feasibility remains separate from preference ordering. A cheap route cannot pass a hard correctness threshold merely because it is cheap.

The durable routing explanation records:

- exact ordered objective policy;
- complete candidate objective vectors;
- declared and planning allocatable capacity;
- protected reserve;
- reset horizon;
- latest observation and provenance;
- selection decision;
- resulting reservation.

Thus a later operator can answer **why this route was chosen and what scarce capacity was protected** from replayable state rather than reconstructing intent heuristically.

## Two Pareto semantics — deliberately distinct

AASM v0.52 now contains two different Pareto mechanisms with different completeness claims.

### 1. Exact finite optimization Pareto frontier

`aasm.optimization.frontier.v1` operates over an independently certified complete finite feasible model space built from the v0.51 enumeration machinery.

For supported finite models:

1. v0.51 deterministically enumerates the entire feasible space;
2. the existing independent exhaustion checker certifies completeness;
3. v0.52 reconstructs the nondominated set;
4. an independent frontier verifier reconstructs the feasible space again;
5. a passing frontier certificate requires exact equality of **solution IDs, assignments, and objective vectors**.

Reusing a legitimate solution ID with forged assignment/value content fails certification.

A `COMPLETE` exact Pareto frontier therefore means complete relative to the supported finite optimization problem and certified enumeration boundary.

### 2. Resource-candidate Pareto frontier

`resource_candidate_pareto_frontier()` operates over the finite candidate set actually supplied to routing after hard quality/capacity gates.

It is exact over that **eligible candidate set**, but it does not claim that no undiscovered route exists elsewhere.

The runtime can persist this frontier as `EVIDENCE_ONLY` without reserving any capacity:

```text
candidate proposals
      ↓
capacity/quality feasibility
      ↓
Pareto analysis
      ↓
durable candidate-frontier Evidence
      ↓
NO resource mutation
```

A separate lexicographic selection/reservation operation is required to commit a route.

This preserves the distinction:

> “These alternatives are nondominated among the supplied eligible candidates” is not the same claim as “this route is authorized to consume resources.”

## Exact finite lexicographic multi-objective solving

`aasm.optimization.multi-objective.v1` is implemented over the v0.51 complete finite enumeration substrate rather than a second optimizer kernel.

For each ordered objective, the exact finite solver:

1. computes the stage optimum over the surviving certified feasible points;
2. retains only candidates within that objective’s declared tolerance;
3. proceeds to the next objective;
4. deterministically selects from the final survivor set;
5. independently reconstructs and verifies every stage optimum and survivor set.

Higher-priority objective degradation outside explicit tolerance is not legal.

## Durable multi-objective Evidence

Experimental `runtime_v52` admits only independently verified PASS objects into durable multi-objective history.

The durable chain is:

```text
MultiObjectiveProblem
    ↓
complete feasible SolutionPool
    ↓
independent EnumerationCompletenessCertificate
    ↓
verified LexicographicResult

or

MultiObjectiveProblem
    ↓
complete feasible SolutionPool
    ↓
independent EnumerationCompletenessCertificate
    ↓
ParetoFrontierCertificate
    ↓
COMPLETE ParetoFrontier
```

All of these records remain `EVIDENCE_ONLY`. Optimality or Pareto completeness does not grant policy/truth authority.

If finite-space enumeration fails or exceeds its declared bound, the runtime records **no partial accepted multi-objective history**.

## Selection, reservation, re-estimation, release, settlement

The selected candidate’s conservative resource-demand envelope is reserved before execution.

Atomic reservation planning:

1. uses demand upper bounds where present;
2. resolves explicit resource IDs directly;
3. resolves class-only demand deterministically;
4. preflights the complete allocation without mutation;
5. fails without partial reservation if any demand is infeasible;
6. commits all reservations only after the full plan is feasible.

The runtime persists selection + reservation as one transaction Evidence document.

### Re-estimation

`reestimate_resource_reservation()` evaluates revised demand against current declared/observed constraints.

```text
ACTIVE
  ↓ feasible reestimate
CONTINUE → ACTIVE with revised reservation

ACTIVE
  ↓ infeasible reestimate
REPLAN_REQUIRED
```

`REPLAN_REQUIRED` preserves the existing reservation and blocks settlement. `release_resource_reservation()` frees it for rerouting.

### Settlement and calibration

Settlement requires exact reserved-resource keys and reconciles committed capacity against actual consumption.

Predicted-versus-actual history is now projected through `resource_consumption_calibration_report()` as `PERFORMANCE_EVIDENCE_ONLY` with reserved total, actual total, signed error, absolute error, and actual/reserved ratio.

This is evidence suitable for later estimator learning. It is not yet an automatic learned estimator update.

## Scope-safe resource access

Workspace and scope fields are enforced on experimental resource runtime operations.

For a scoped capacity:

```text
workspace_id must match exactly
AND
caller scope must be allowed by the existing AASM scope-flow relation
```

Wrong workspace, missing context, unknown scopes, cross-workspace observation, cross-workspace settlement, and cross-workspace inspection fail closed or return no visible records as appropriate.

This is scope enforcement, **not yet the final principal-authority calculus**. `owner_principal_id` remains descriptive until the central Principal/Workspace/Scope authority/delegation layer is implemented in the public runtime.

## Delivered v0.52 foundation slices

Implemented on the v0.52 experimental path:

- capacity windows and observation authority;
- protected reserve and observation-constrained planning capacity;
- resource-aware governed SII successor proposal;
- explicit provider-quota-burn proposal/candidate dimension;
- ordered resource-routing objective policy;
- hard correctness/evidence/progress gates;
- exact Pareto analysis over supplied eligible resource candidates;
- durable non-mutating resource-candidate frontier Evidence;
- scope-safe resource access and inspection;
- atomic selection + reservation;
- durable re-estimation with `CONTINUE | REPLAN_REQUIRED`;
- release and settlement;
- predicted-versus-actual calibration projection;
- replayable routing explanations;
- exact finite lexicographic multi-objective solver;
- exact finite Pareto solver built on v0.51 certified complete enumeration;
- independent full-point Pareto certification;
- durable certified multi-objective Evidence/replay;
- JSON schemas for the problem, frontier, frontier certificate, lexicographic result, resource-aware proposal, resource capacity/observation/demand, and resource-routing policy;
- adversarial tests for false completeness, forged frontier point content, priority inversion, quota-vs-money policy changes, scope leakage, unknown capacity, reserve violations, partial reservations, duplicate settlement, and replay.

## Still required before a v0.52 release freeze

The implementation is not yet being declared released. Remaining freeze work includes:

- run and close the complete exact-head CI matrix after the final schema/docs changes;
- add/finish an explicit v0.52 public conformance/release-contract gate that asserts the new schemas/contracts and durable-runtime invariants together;
- review tolerance-aware Pareto dominance semantics and document/freeze them explicitly;
- decide whether the experimental certificate field name `exact_solution_set_match` should be renamed to `exact_point_set_match` before freeze, because the implemented check is stronger than ID-set equality;
- verify packaging/public exports expected for the v0.52 contract surface;
- update release-facing README/current-release/changelog only after those gates pass.

## Later hosted-foundation hardening — not v0.52 semantic gaps

The following remain planned public hardening beyond this release rather than reasons to weaken v0.52:

- central principal-scoped authority delegation, capability ceilings, expiry, and nondelegable denies;
- distributed compare-and-swap/lease ownership for reservation safety across worker processes;
- provider-specific meter adapters;
- automatic replacement-route execution after `REPLAN_REQUIRED`;
- governed `REQUEST_CAPACITY`, `THROTTLE`, `FALLBACK`, and `FREEZE` operational transitions;
- learned resource estimators derived from calibration Evidence;
- reset-horizon/burn-velocity/forecast-demand scarcity forecasting;
- scarcity pricing;
- portable machine archive and hosted billing/portal implementation.

## Permanent architectural rule

> **No known target capability may be deferred in a way that makes current public contracts structurally incompatible with it. Implementation may be staged; architectural accommodation may not.**

And:

> **Proposal is cheap. Commitment, authority, resource consumption, and external effects are not.**
