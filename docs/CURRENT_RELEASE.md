# AASM v0.54.0 — Certified Cross-Solver Exchange & Deterministic Portfolio Racing + Effect Ownership/UNKNOWN Recovery

AASM v0.54.0 advances the public package/runtime to `0.54.0` and `aasm.adoption.v1 / 0.30.0`.

```text
active public surface: public_v54
active runtime: runtime_v54_full.AASMEngine
parent public surface: public_v53
parent runtime: runtime_v53_learning.AASMEngine

aasm.effect.intent.v1 / 0.1.0
aasm.effect.dispatch-request.v1 / 0.1.0
aasm.effect.ownership.v1 / 0.1.0
aasm.effect.reconciliation.v1 / 0.1.0
aasm.effect.resource-settlement.v1 / 0.1.0
aasm.solver.translation.v1 / 0.1.0
aasm.solver.portfolio.v1 / 0.1.0
aasm.solver.portfolio.runtime.v1 / 0.1.0
aasm.solver.exchange.v1 / 0.1.0
```

v0.54 extends the v0.53 scoped-authority and solver-learning foundation without creating a second scheduler, resource ledger, effect ledger, truth system, or solver executor.

## Effect intent, dispatch, ownership, and reconciliation

External execution now has an explicit durable lifecycle:

```text
EffectIntent
    ↓
authorization
    ↓
EffectDispatchRequest
    ↓
atomic EffectOwnership
    ↓
external boundary
    ↓
CONFIRMED | FAILED | UNKNOWN
    ↓
EffectReconciliation
```

A TaskLease, declared resource reservations, scoped execution authority, durable intent, and durable dispatch request must all agree before ownership can cross the external boundary. Ownership Evidence is durable before the executor is called.

If a process dies after ownership is acquired but before a trustworthy terminal observation is committed, recovery marks the effect `UNKNOWN`. A new dispatch is blocked until explicit scoped reconciliation supplies local Evidence for the observed external outcome.

Ownership, dispatch, and reconciliation history is append-only. Legacy pre-v0.54 effects are not silently adopted into the new lifecycle.

## Actual effect-resource settlement

`aasm.effect.resource-settlement.v1` binds observed external consumption back to the existing v0.52/v0.53 resource settlement path.

```text
reserved capacity
      ↓
external execution
      ↓
CONFIRMED | FAILED reconciliation
      ↓
observed actual consumption
      ↓
existing resource.settle authority + ledger
      ↓
Effect resource-settlement Evidence
```

Settlement is blocked while an effect is `UNKNOWN`. Actual resource keys must exactly match each bound reservation. Multi-reservation settlement is recoverable and idempotent per reservation; a retry may continue already-partially-settled work only when the durable actual-consumption values match exactly.

No new resource authority is introduced. `resource.settle` remains the governing scoped capability and resource observations remain Evidence.

## Certified canonical solver translation

v0.54 can represent one canonical optimization model for compatible solver families without pretending separately cloned models are automatically equivalent.

A `SolverTranslation` binds:

- the source canonical model fingerprint;
- a semantic fingerprint independent of target-family metadata;
- the target solver-family model;
- the target provider;
- a deterministic translation identity.

The AASM translation checker independently reconstructs and verifies exact semantic equality before the representation may enter a portfolio or solver-learning exchange.

## Deterministic governed portfolio racing

Portfolio racing reuses the existing optimization lifecycle:

```text
certified translations
        ↓
ordinary optimization requests
        ↓
ordinary TaskDemand queue
        ↓
ordinary TaskLease claims
        ↓
existing execute_optimization_lease
        ↓
normalized + independently validated results
        ↓
proof-certificate discovery
        ↓
deterministic portfolio decision Evidence
```

There is no v0.54 parallel scheduler. Race legs are ordinary AASM optimization tasks.

Correctness selection explicitly excludes wall time, arrival order, fastest-response wins, and majority voting. Uncertified negative claims cannot outvote a validated feasible assignment. Certified contradictions fail closed as `CONFLICT`.

For claims that require proof-grade strength, the existing v0.50 `SolverClaimCertificate` path remains authoritative for certification status. Portfolio agreement itself grants no truth authority.

A real native OR-Tools CP-SAT + HiGHS fixture exercises this complete TaskLease/provider/proof-aware race path.

## Certified cross-solver learned-artifact exchange

v0.54 reuses the v0.53 `SolverLearningArtifact`, validation, and application contracts. It does not invent a second learning representation.

A cross-solver exchange requires:

1. a source artifact with an exact local PASS validation;
2. independently reproducible source and target solver-translation certificates;
3. a newly bound target-family `SolverLearningArtifact`;
4. receiving-target local revalidation against the target model;
5. existing scoped solver-learning application authority before use.

Correctness-sensitive no-goods, cores, and bounds must pass target-local validation before pruning. Incumbents and warm starts remain performance-only. Native accelerator state is not portable across different solvers.

```text
cross_solver_agreement_grants_truth = false
truth_authority  = NONE
policy_authority = NONE
```

## Exact-SHA release gates

v0.54 publication requires success on the exact current `main` commit from:

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

`aasm/v54` covers effect ownership/UNKNOWN recovery, effect actual-resource settlement, deterministic portfolio semantics and execution, certified cross-solver exchange, and the active public v0.54 surface. `aasm/optimization` additionally exercises the real OR-Tools + HiGHS governed portfolio race.

The release workflow builds two byte-identical distributions, clean-installs the wheel, validates the active public contract, publishes the GitHub release once, and verifies every remote release asset byte.

Next: **v0.55.0 — Extended Mathematical IR + Portable Machine Archive**.

AASM remains an `0.x` active-development project. License: Apache-2.0 project-wide under `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
