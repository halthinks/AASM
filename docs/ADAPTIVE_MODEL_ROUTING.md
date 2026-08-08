# Adaptive model routing

AASM v0.11 learns which eligible model class is actually cost-effective for a task class from explicit evaluated outcomes.

The static router remains the hard gate. A model must still satisfy configured capability, minimum-strength, context-window, candidate-set, enabled-state, and cost-ceiling requirements before empirical data is allowed to influence selection.

## Evidence contract

AASM does **not** learn from “the API returned successfully.” A `ModelOutcomeRecord` is recorded only after some verifier/controller evaluates the work.

```json
{
  "task_id": "backend-42",
  "task_class": "routine_backend",
  "model_id": "luna",
  "accepted": true,
  "executor_id": "codex-cli",
  "repair_required": false,
  "verification_score": 0.94,
  "latency_seconds": 38.2,
  "estimated_cost": 0.17
}
```

This separates execution telemetry from quality evidence.

## Performance statistics

For each `(task_class, model_id)` AASM exposes:

- sample count;
- accepted count and acceptance rate;
- Wilson lower and upper bounds for the acceptance rate;
- repair rate;
- average verification score when supplied;
- average latency when supplied;
- average estimated cost when supplied;
- `confidence`, defined as `1 - (Wilson upper - Wilson lower)`.

`confidence` is therefore interval concentration, not a claim that the model has some probability of being correct.

## Routing behavior

1. Run the normal `ModelStrengthRouter` hard filters.
2. If no `task_class` is supplied, use the normal static result.
3. If there are fewer than `min_empirical_samples`, fall back to the static result unless deterministic calibration is explicitly enabled.
4. Apply `min_empirical_acceptance` to the **Wilson lower bound**, not the raw acceptance rate.
5. Rank empirically qualified models by one of:
   - `cost_per_quality` — Wilson lower-bound acceptance divided by observed cost penalty;
   - `quality` — highest conservative acceptance, then repair/cost tie-breaks;
   - `latency` — lowest measured latency while preserving the static quality contract.

A strong model can never make a weaker model eligible when the weaker model fails the static minimum-strength contract. Conversely, measured evidence can show that a cheaper eligible model is sufficient for a specific task class.

## Calibration

Set `explore_under_sampled=true` to deterministically collect evidence for eligible models with insufficient samples. Calibration is not random: AASM prioritizes the least-sampled eligible model, then lower configured cost and deterministic tie-breaks.

## Execution contract

```json
{
  "prompt": "Implement the isolated endpoint and run its tests.",
  "task_class": "routine_backend",
  "model_required_capabilities": ["code"],
  "executor_required_capabilities": ["code"],
  "min_strength": 0.5,
  "min_empirical_samples": 5,
  "min_empirical_acceptance": 0.75,
  "empirical_optimize": "cost_per_quality"
}
```

## CLI

Record a verifier-evaluated result:

```bash
aasm model-outcome MACHINE_ID --store runs.db --record outcome.json
```

Inspect learned performance:

```bash
aasm model-performance MACHINE_ID --store runs.db --task-class routine_backend
```

The HTTP control plane also accepts `POST /v1/machines/{id}/model-outcome`; `AASMRemoteClient.model_outcome()` wraps it.

## Luna / Terra / Sol-style use

The intended pattern is not a permanent rule such as “Luna does easy work and Sol does hard work.” The static strength floor expresses what a task is allowed to use; evaluated outcome data then answers a narrower empirical question:

> For this task class, among models already strong enough to be eligible, which one has demonstrated the best quality/cost/latency behavior with enough evidence?

That lets the same model be economical for one repository/task class and inadequate for another without hard-coding either conclusion globally.
