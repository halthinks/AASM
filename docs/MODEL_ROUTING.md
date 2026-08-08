# Model strength and cost routing

AASM v0.8 treats model choice as a resource-allocation decision rather than a prompt convention.

Different model classes can have materially different reasoning strength, latency, context size, capabilities, and cost. `ModelProfile` records those facts; `ModelRouteRequest` states the minimum contract for a task; `ModelStrengthRouter` selects only from eligible profiles.

A deployment may name profiles however it wants. For example, a team can use `luna`, `terra`, and `sol` as local routing classes without AASM assuming those names correspond to any specific provider model.

```python
from aasm import ModelProfile, ModelRouteRequest

engine.register_model_profile(ModelProfile(
    model_id="luna",
    provider="provider-adapter",
    capabilities=["scan", "simple_code"],
    strength=0.45,
    cost_per_1k_output=0.2,
    latency_score=0.95,
    context_window=100_000,
))

engine.register_model_profile(ModelProfile(
    model_id="sol",
    provider="provider-adapter",
    capabilities=["architecture", "review", "hard_reasoning"],
    strength=0.96,
    cost_per_1k_output=4.0,
    latency_score=0.45,
    context_window=300_000,
))

route = engine.route_model(ModelRouteRequest(
    task_id="architecture-review",
    required_capabilities=["architecture", "review"],
    min_strength=0.9,
    optimize="strength",
))
```

## Hard constraints first

Profiles are rejected before scoring when they fail any hard requirement:

- disabled
- missing required capability
- below minimum strength
- insufficient context window
- above an explicit cost ceiling
- outside an explicit candidate allow-list

Only eligible models are scored.

## Objectives

`optimize` can be `strength`, `cost`, `latency`, or `balanced`.

The result includes the chosen model, ranked eligible set, rejected models with reasons, and routing explanation. The route is persisted in the machine event stream through the authoritative snapshot patch path so later inspection can answer not only *which model ran* but *why that class was selected*.

## Adapters, not hard-coded providers

AASM does not itself create an OpenAI, Anthropic, local, or other provider session. The model profile is the control-plane decision. A runtime adapter translates the selected `model_id/provider` pair into a concrete API request, Codex agent type, local worker command, or other execution mechanism.
