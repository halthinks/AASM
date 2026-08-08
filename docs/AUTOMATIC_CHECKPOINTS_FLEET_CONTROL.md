# Automatic Checkpoints and Fleet Control

AASM v0.16 connects verification, selective change impact, Planner authority, collaboration analysis, and worker admission into one control loop.

## Automatic Verifier checkpoints

`CheckpointTriggerEngine` converts explicit Verifier signals into `ChangeSignal` records when configured conditions are crossed:

- failed tests → `verification_failed`
- changed assumptions → `assumption_changed`
- unexpected output → `evidence_changed`
- blocking findings → `risk_escalation`

The resulting signal is passed through the v0.15 change-impact analyzer. If the task maps to a plan node, that node and its downstream dependents are paused. Unrelated work remains active. If the PBV task is not represented in the graph, AASM still records the trigger and requests Planner attention without inventing a dependency anchor.

Automatic checkpointing does **not** authorize a plan mutation. The Planner remains the only role allowed to commit an authoritative `PLAN_INTERRUPT`.

## PBV closed loop

`PBVCoordinator` now includes the automatic checkpoint, current change-control state, and fleet state in the Planner payload:

`BuilderOutput → VerifierReport → automatic checkpoint → PlannerDecision`

A Planner may optionally resolve part of the checkpoint from the same decision by putting this in `PlannerDecision.metadata`:

```json
{
  "resolve_impact": {
    "impact_id": "impact_123",
    "resume_nodes": ["module-a"],
    "retire_nodes": []
  }
}
```

Only the listed nodes are resolved. Remaining impacted nodes stay paused.

## Fleet admission

`FleetControlPolicy` is opt-in. When enabled, AASM re-runs v0.14 collaboration analysis over runnable scheduled tasks and converts the recommended worker count into a durable machine quota.

This intentionally reuses the existing `QuotaPolicy` path. SQLite and PostgreSQL therefore enforce the admission cap at the same atomic claim boundary already used for machine/worker/resource quotas.

Fleet control does **not** provision machines, cloud instances, model sessions, or external infrastructure. It controls how much already-registered execution capacity AASM admits concurrently.

## Automatic refresh

When enabled, fleet control can refresh after:

- an automatic Verifier checkpoint;
- a Planner `PLAN_INTERRUPT`;
- change-impact resolution.

Paused, completed, and structurally pruned tasks are removed from the runnable set before re-analysis.

## Safety properties

- Verifiers trigger checkpoints but cannot rewrite plans.
- Builders cannot resolve checkpoints or change the authoritative plan.
- Fleet admission is opt-in and does not grant deployment authority.
- A collaboration recommendation and a fleet quota remain separate from effect authorization, credentials, sandbox policy, and external side-effect governance.
- Partial checkpoint resolution never resumes unrelated unresolved nodes.

## CLI

```bash
aasm checkpoint-triggers MACHINE_ID --store runs.db
aasm checkpoint-trigger-policy MACHINE_ID --store runs.db --policy checkpoint.json
aasm fleet-control MACHINE_ID --store runs.db --policy fleet.json
aasm fleet-refresh MACHINE_ID --store runs.db --policy collaboration.json
```

## Remote API

- `GET /v1/machines/{id}/checkpoint-triggers`
- `POST /v1/machines/{id}/checkpoint-triggers/configure`
- `GET /v1/machines/{id}/fleet-control`
- `POST /v1/machines/{id}/fleet-control/configure`
- `POST /v1/machines/{id}/fleet-control/refresh`
