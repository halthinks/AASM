# Information-Change Checkpoints

AASM v0.15 turns changed information into a selective control event instead of a global restart.

## Goal

When a user adds a requirement, an assumption changes, evidence changes, verification fails, a contradiction appears, or risk escalates, AASM should determine **which plan nodes are actually affected** and preserve work outside that region.

The dependency convention is the existing AASM plan graph: an edge `A -> B` means B depends on A. A change anchored at A therefore affects A and downstream descendants of A.

## Change signals

Use `ChangeSignal` with a stable kind, note, and zero or more `seed_nodes`.

Supported kinds:

- `user_steering`
- `assumption_changed`
- `evidence_changed`
- `verification_failed`
- `contradiction`
- `risk_escalation`
- `external_dependency`

Assumption/evidence IDs and metadata may be attached for provenance.

## Selective pause semantics

`engine.analyze_change(signal)`:

1. validates the current plan DAG;
2. computes seed-node descendants;
3. separates affected and unaffected nodes;
4. identifies active affected and preserved active tasks;
5. durably records the impact checkpoint;
6. adds affected nodes to the durable paused-task set;
7. releases only active leases in the affected region.

A released worker may still finish local computation, but a later completion cannot turn that released lease into a successful durable result. Unaffected leases remain active.

`claim_task()` rejects paused tasks. `claim_next_task()` naturally skips them because it delegates to `claim_task()`.

## Unanchored changes

A change may be real before its graph location is known. A signal without `seed_nodes` therefore requires Planner attention but does **not** pretend the entire plan is invalid. No unrelated nodes are paused automatically.

## Planner resolution

Only the authoritative Planner may resolve a checkpoint when the executable PBV profile is configured.

Use:

```python
engine.resolve_change_impact(
    planner_id="planner",
    impact_id="impact_...",
    resume_nodes=["node-b"],
    retire_nodes=[],
    plan_decision_id="decision_...",
)
```

Resolution is incremental. The checkpoint tracks `remaining_nodes`. A partial repair may resume some nodes while others stay paused; later Planner decisions can resolve the remaining region without re-pausing nodes already cleared.

`resume_nodes` and `retire_nodes` must be inside the currently unresolved affected region.

## Additive user steering

The existing `user_interrupt()` API remains compatible. When its metadata contains `seed_nodes`, v0.15 also creates a change-impact checkpoint:

```python
engine.user_interrupt(
    "also support FreeCAD",
    metadata={"seed_nodes": ["cad-adapter"], "source": "user"},
)
```

This preserves the existing plan, pauses only the impacted dependent region, and leaves unaffected work running.

## Relationship to Planner / Builder / Verifier

The impact analyzer does not rewrite the plan. It produces control evidence.

A typical loop is:

```text
changed information
      ↓
ChangeSignal
      ↓
impact closure
      ↓
pause affected region only
      ↓
Planner investigates/replans
      ↓
PLAN_INTERRUPT if plan must change
      ↓
Planner resolves repaired nodes
      ↓
valid work resumes
```

The Planner remains the only authority that can change the plan in the executable PBV profile.

## Safety boundary

Change-impact analysis is not execution authorization. Sandbox rules, governance review, authority policy, effect authorization, credentials, and external-write controls remain independent.
