# Model economics and governance overhead

AASM v0.9 treats model calls as a scarce resource with different purposes rather than counting every call as equivalent.

## Why this exists

A coding system can spend substantial model capacity on governance rather than productive engineering. AASM distinguishes productive reasoning, verification, governance, permission review, synthesis, and retries so operators can see where tokens and money are actually going.

AASM does **not** disable sandboxing or security controls. The optimization target is narrower: express repeatable permission decisions deterministically and spend model reasoning at checkpoints where new information, changed assumptions, failed verification, or genuinely risky actions require judgment.

## Cache-adjusted accounting

`ModelUsageRecord` records:

- input tokens
- cached input tokens
- output tokens
- model
- task/checkpoint
- call purpose

`EconomicsLedger` then calculates cost from separately configured uncached-input, cached-input, and output prices. Pricing is configurable. The built-in GPT-5.6 table is a dated convenience snapshot, not a promise that provider prices never change.

## Codex Auto-review telemetry

`codex_telemetry.import_otel_events()` and `import_otel_jsonl()` can ingest Codex/OpenTelemetry-style token metrics. Events labelled with `codex-auto-review`, `subagent_guardian`, or equivalent guardian metadata are classified as `permission_review` rather than productive work. Cached input, fresh input, and output remain separate when the telemetry exposes those token types.

This gives AASM a concrete measurement loop:

```text
Codex execution / Auto-review
        |
        v
OpenTelemetry token metrics
        |
        v
AASM Codex telemetry importer
        |
        +-- productive
        +-- verification
        +-- permission_review
        |
        v
EconomicsLedger + Control Center
```

The importer is intentionally conservative: token classes it cannot classify are reported as ignored rather than silently priced as uncached input.

```python
from aasm import import_otel_jsonl

batch = import_otel_jsonl("codex-otel.jsonl")
for record in batch.records:
    engine.record_model_usage(record)
print(engine.economics_summary())
```

## Governance ratio

AASM exposes both:

- `governance_token_ratio`
- `governance_cost_ratio`

This makes pathological patterns visible. A run where permission reviewers consume more resources than the implementation itself should be obvious in the Control Center.

## Deterministic review gate

`ReviewGatePolicy` performs a cheap first pass.

Examples of default benign action classes:

- read
- search
- list
- test
- lint
- format
- build
- local status inspection

Examples that require model review by default:

- destructive operations
- credentials or secrets
- security-sensitive changes
- external writes
- unknown network destinations
- irreversible operations
- unclassified actions

Even a normally benign class escalates when governing assumptions change, tests fail, or a material change exceeds the configured threshold.

The intended structure is:

```text
sandbox / OS boundary
        |
        v
deterministic permission rules
        |
        +-- clearly allowed/blocked --> no reviewer model
        |
        +-- judgment required
                 |
                 v
          semantic review model
                 |
                 v
         checkpoint decision
```

This is deliberately different from asking an intelligent reviewer to re-decide every routine shell boundary.

## APIs

```python
from aasm import CallPurpose, ModelUsageRecord

engine.record_model_usage(ModelUsageRecord(
    model_id="gpt-5.6-terra",
    purpose=CallPurpose.PRODUCTIVE.value,
    input_tokens=12000,
    cached_input_tokens=9000,
    output_tokens=3500,
    task_id="backend-17",
))

print(engine.economics_summary())
print(engine.review_gate("test"))
```

CLI:

```bash
aasm economics MACHINE_ID --db runs.db
```

## Policy principle

**Do not pay an intelligent agent to repeatedly re-decide a permission decision that can be expressed deterministically. Spend intelligence on validating changed information and substantive work.**
