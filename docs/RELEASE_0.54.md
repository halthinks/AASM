# AASM v0.54.0 — Certified Cross-Solver Exchange & Deterministic Portfolio Racing + Effect Ownership/UNKNOWN Recovery

AASM v0.54.0 promotes the v0.54 experimental layer to the active public package surface.

This release does not replace AASM's existing authority, scheduler, resource, solver, Evidence, or replay planes. It composes the v0.53 foundation into stronger governed external-effect and heterogeneous-solver semantics.

## Release identity

```text
package: aasm-runtime 0.54.0
public surface: public_v54
runtime: runtime_v54_full.AASMEngine
adoption contract: aasm.adoption.v1 / 0.30.0
stability: ACTIVE_DEVELOPMENT
license: Apache-2.0
```

## Effect Ownership/UNKNOWN Recovery

v0.54 adds public durable contracts for effect intent, dispatch, ownership, and reconciliation:

```text
aasm.effect.intent.v1 / 0.1.0
aasm.effect.dispatch-request.v1 / 0.1.0
aasm.effect.ownership.v1 / 0.1.0
aasm.effect.reconciliation.v1 / 0.1.0
```

Before an executor crosses the external boundary, AASM requires the bound intent, current scoped execution authority, an active existing TaskLease, declared resource reservations, and a durable atomic ownership record.

Crash/recovery after ownership but before a trustworthy terminal observation produces `UNKNOWN`. A second execution attempt is blocked until explicit scoped reconciliation establishes `CONFIRMED` or `FAILED` with local Evidence.

Dispatch, ownership, and reconciliation history is append-only.

## Effect actual-resource settlement

```text
aasm.effect.resource-settlement.v1 / 0.1.0
```

Observed actual consumption is reconciled only after `CONFIRMED` or `FAILED` effect reconciliation and only through the existing `resource.settle` scoped authority and resource ledger.

`UNKNOWN` effects cannot settle consumption. Retry of partially completed multi-reservation settlement is idempotent and must match already-durable actual consumption exactly.

## Certified solver translation

```text
aasm.solver.translation.v1 / 0.1.0
```

Compatible solver-family representations are explicitly bound to one canonical model and independently checked for semantic equality. Cross-family execution is therefore not modeled as unrelated cloned problems.

## Deterministic Portfolio Racing

```text
aasm.solver.portfolio.v1 / 0.1.0
aasm.solver.portfolio.runtime.v1 / 0.1.0
```

Every portfolio leg remains an ordinary AASM optimization request, `TaskDemand`, `TaskLease`, provider execution, validation, and Evidence commit. v0.54 adds no parallel scheduler.

Correctness selection explicitly rejects:

- fastest-result wins;
- arrival-order wins;
- majority-vote truth;
- uncertified negative claims outvoting validated feasible assignments.

Proof-grade OPTIMAL/UNSAT/INFEASIBLE decisions reuse the existing v0.50 proof-certificate path. Certified contradictions fail closed as `CONFLICT`.

A native release-gate fixture runs OR-Tools CP-SAT and HiGHS through the real existing provider/TaskLease path and requires the deterministic certified portfolio result.

## Certified Cross-Solver Exchange

```text
aasm.solver.exchange.v1 / 0.1.0
```

v0.54 reuses v0.53 `SolverLearningArtifact`, validation, and application semantics for cross-solver exchange.

Source learning must already have exact local PASS validation. Source and target representations must have reproducible translation certificates. The exchanged target artifact is a new target-family solver-learning artifact and must independently pass target-local validation before existing solver-learning application can use it.

Correctness-sensitive no-goods, cores, and bounds remain pruning-capable only after local certification. Incumbents and warm starts remain performance-only. Native accelerator state cannot cross solvers.

```text
cross_solver_agreement_grants_truth = false
truth_authority  = NONE
policy_authority = NONE
```

## Release gates

The exact release SHA must pass:

```text
aasm/ci-summary
aasm/formal-assurance
aasm/semantic-solver-rc
aasm/proof-claims
aasm/solution-pools
aasm/optimization
aasm/scoped-authority
aasm/solver-learning
aasm/v54
```

`aasm/v54` directly exercises the new effect, settlement, portfolio, exchange, replay, and active-public-surface contracts. The broader permanent gates ensure v0.54 remains compatible with the released proof, solution-pool, optimization, scoped-authority, solver-learning, formal, and RC foundations.

## Hard completion criterion

v0.54 is complete only when crash/retry fixtures cannot silently duplicate or lose effect ownership, UNKNOWN effects remain unresolved until evidenced, actual external consumption reconciles through the governed resource ledger, and portfolio execution cannot bypass existing TaskLease/provider/resource/authority boundaries.

Those criteria are encoded as executable release gates rather than documentation-only claims.

## Next

**v0.55.0 — Extended Mathematical IR + Portable Machine Archive**
