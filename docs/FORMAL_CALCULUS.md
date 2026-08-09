# AASM Formal Calculus

AASM v0.21 adds a durable conflict-learning calculus to the production event-sourced runtime. It does not introduce a second state engine. Every calculus mutation is committed through the existing `SNAPSHOT_PATCHED` event and pure reducer, so replay, historical forks, SQLite, PostgreSQL, and the existing authority/effect boundaries continue to apply.

## State

`MachineSnapshot.calculus` contains:

```text
schema_version
 epoch
 active_model
 decisions / decision_edges
 obligations / obligation_edges
 locks
 conflicts
 explanations
 constraints
 fairness
 search_local
```

The active model maps one decision subject to one active `decision_id`. A decision carries its value, kind, status, decision level, causal parents, evidence, plan-node provenance, and scope.

An obligation carries a condition over decision values, dependency obligations, causal decisions, attached plan nodes, an evidence contract, locks, artifacts, persistence/mandatory flags, and explicit terminal disposition.

## Conditions

The condition AST is intentionally small and deterministic:

```json
{"const": true}
{"decision": {"subject": "database", "op": "EQ", "value": "postgres"}}
{"all": [CONDITION, CONDITION]}
{"any": [CONDITION, CONDITION]}
{"not": CONDITION}
```

Missing decision subjects make decision literals false. `NEQ` is evaluated only when the subject is present.

## Conflict learning

A conflict snapshots the active model and decision levels at the point of contradiction. It references durable evidence and may identify an observed obligation and preliminary implicated decisions.

A validated explanation contains the decision literals materially responsible for the conflict. Every literal must point to a decision that was active in the conflict snapshot. Explanation evidence must be drawn from the conflict evidence set.

Projection creates a guarded no-good:

```text
guard => NOT (literal_1 AND ... AND literal_n)
```

Only validated or proven explanations of `ASSUMPTION_CONFLICT` may become hard constraints. Evidence conflicts and heuristic/provisional explanations remain soft.

Hard constraints are checked before a new decision model is activated. Same-guard constraints use body-subset subsumption: a smaller no-good body is stronger and supersedes a larger one.

## Backjumping

Backjumping is causal, not chronological.

1. Resolve explanation literals to active decisions.
2. Follow `DERIVED` decisions to explicit causal roots.
3. Compute each root's active dependent closure.
4. Sort roots by decision level descending, closure size ascending, then decision ID.
5. Select the first revisable root.
6. Invalidate only that root and its dependent decisions.
7. Mark obligations depending on that closure `NEEDS_REVALIDATION`.
8. Preserve unrelated decisions, including unrelated decisions created later.
9. Mark linked plan nodes `needs_revalidation` and send them to the existing information-change checkpoint machinery.

A backjump must remove every active violation of learned hard constraints. When no revisable causal pivot exists, the caller must investigate, restart search, or fail explicitly.

## Locks

A lock suppresses an obligation only while an explicit model condition holds. Locks are never deletions.

On every model change, backjump, or search restart, active locks are reevaluated. A false lock condition produces a broken lock and makes the obligation available when no other active lock remains.

## Fairness

Persistent unresolved obligations receive epoch-based accounting:

```text
hidden_epochs
continuous_lock_epochs
lock_count
last_considered_epoch
last_enabled_epoch
last_reviewed_epoch
explicit_deferral_until_epoch
```

The default policy marks work due at three hidden epochs, three continuous lock epochs, or three locks. With `BLOCK_PLANNING`, a new model must expose overdue work unless the authoritative Planner records bounded deferral or a terminal disposition (`REJECTED`, `SUPERSEDED`, or `IMPOSSIBLE`) with a reason and evidence where available.

Fairness blocks plan expansion/model selection. It does not block evidence recording, effect reconciliation, safety pauses, worker heartbeats, or inspection.

## Search restart

`restart_search()` is distinct from process resume, checkpoint restoration, and historical fork.

It clears speculative active decisions, temporary branch ordering, and `search_local`, while retaining:

- pinned/root decisions;
- requirements and machine state;
- plan, evidence, and artifact provenance;
- conflicts, explanations, and learned constraints;
- effects and their UNKNOWN/idempotency semantics;
- mission state, workers, leases, replay history, and fork lineage.

## Authority

When the executable Planner/Builder/Verifier profile is configured, only the authoritative Planner may request `BACKJUMP` or `RESTART_SEARCH` through `RecoveryDecision`. The Verifier may create evidence and recommend recovery, but does not mutate the authoritative plan or activate hard learned knowledge by itself.

## Completion

A transition to `COMPLETE` is rejected while any persistent mandatory obligation lacks a terminal disposition:

```text
COMMITTED | REJECTED | SUPERSEDED | IMPOSSIBLE
```

## Public API

```python
from aasm import (
    AASMEngine,
    DecisionRecord,
    ObligationRecord,
    LockRecord,
    ConflictRecord,
    ExplanationRecord,
    FairnessPolicy,
    RecoveryDecision,
)

engine.register_decision(...)
engine.activate_decision(...)
engine.register_obligation(...)
engine.enable_obligation(...)
engine.lock_obligation(...)
engine.raise_conflict(...)
engine.register_explanation(...)
engine.learn_constraint(...)
engine.backjump_conflict(...)
engine.restart_search(...)
engine.audit_calculus_fairness()
engine.review_calculus_fairness(...)
engine.calculus_report()
```

The CLI adds:

```bash
aasm calculus MACHINE_ID --store runs.db
aasm calculus-fairness MACHINE_ID --store runs.db
```
