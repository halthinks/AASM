# Resource-Governed Decision Foundation

**Status:** implementation foundation for the v0.52 program; not a v0.52 completion claim.

## Product-backward requirement

AASM must be able to choose among legal ways of accomplishing work by jointly considering outcome quality, evidence strength, expected progress, resource scarcity, monetary cost, wall time, and scarce expert-intelligence usage.

This is a known target capability, so current public contracts must remain structurally compatible with it. Implementation may be staged; architectural accommodation may not.

## Governing loop

```text
CAPACITY
   ↓
PROPOSALS — expected outcome + evidence + resource demand + uncertainty
   ↓
MULTI-OBJECTIVE DECISION
   ↓
AUTHORITY + CAPACITY CHECK
   ↓
LEASE / RESERVATION
   ↓
EXECUTION
   ↓
ACTUAL CONSUMPTION + RESULT + EVIDENCE
   ↓
RECONCILE / VERIFY / LEARN
   ↓
future estimates and routing
```

AASM must not create a second hosted-only scheduler or accounting truth system. This work extends the existing resource, scheduler, economics, SII, scope, authority, and optimization surfaces.

## Capacity is broader than money or tokens

A governed capacity may represent:

- CPU/GPU time;
- solver time or calls;
- workers/concurrency;
- storage;
- API dollars or credits;
- provider/model credits;
- subscription allowances;
- rolling or weekly usage envelopes;
- human review capacity;
- custom scarce resources.

A provider-controlled weekly model allowance is therefore a valid AASM resource even when AASM does not control the provider meter.

## Capacity truth and provenance

AASM must never convert an observation into provider truth merely because it is useful for planning. Resource observations carry one of:

```text
AUTHORITATIVE
OBSERVED
DERIVED
ESTIMATED
DECLARED
UNKNOWN
```

Examples:

- provider API meter → `AUTHORITATIVE` when the provider contract makes it authoritative;
- provider UI/usage surface → `OBSERVED`;
- AASM sum of authoritative effect records → `DERIVED`;
- forecast from historical burn → `ESTIMATED`;
- user-entered remaining weekly allowance → `DECLARED`;
- no reliable signal → `UNKNOWN`.

Uncertain resource state is Evidence. It is not silently promoted to truth.

## Capacity windows

The public resource model must support:

```text
FIXED
ROLLING
REFILLING
CREDIT_BALANCE
UNBOUNDED
UNKNOWN
```

A weekly subscription allowance is a capacity window with an explicit reset/refill horizon. The implementation must not hard-code OpenAI, Codex, ChatGPT, Anthropic, or any other provider into the kernel.

## Protected reserve

`remaining` and `allocatable` are not synonymous.

A capacity may reserve part of its remaining supply for higher-value or critical future work:

```text
total
- consumed
- committed
- protected_reserve
= allocatable
```

This prevents routine work from consuming scarce expert-model capacity that policy intends to preserve for difficult or critical work.

## Proposal-side resource demand

Proposals must be able to state expected resource demand with uncertainty:

```text
resource class / optional concrete resource
expected amount
upper bound
unit
confidence
```

Future SII evolution must add these demands to the structured proposal contract rather than creating a separate intelligence-only accounting path.

## Authority and resource rights are distinct

```text
Authority: may this principal perform this action in this scope?
Capacity/lease: may this work consume these resources?
```

Both may be required. Resource availability never grants authority; authority never implies unlimited resource rights.

## Reconciliation and replanning

Reservations are estimates, not final consumption. Execution must reconcile reserved capacity with actual metered use. When expected consumption materially changes, the runtime must be able to pause and re-evaluate the plan before silently exceeding a lease or protected reserve.

Required future transition family:

```text
RESERVE
SETTLE
RELEASE
REESTIMATE
REPLAN
REQUEST_CAPACITY
THROTTLE
FALLBACK
FREEZE
```

## Multi-objective target

The v0.52 decision layer must support policy-selected objective vectors such as:

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

These are dimensions, not fixed kernel weights. Policies may impose hard thresholds, lexicographic priority, Pareto comparison, or other explicitly governed rules.

Example:

```text
hard:
  correctness >= required threshold
  evidence >= required grade
  protected expert reserve must remain intact

lexicographic:
  1. maximize correctness
  2. maximize evidence quality
  3. maximize expected progress
  4. minimize scarce expert capacity
  5. minimize money
  6. minimize wall time
```

## Scope compatibility

All new resource objects include principal/workspace/scope seams now so hosted multi-tenancy does not require replacing resource identity later. Scope enforcement remains a public-runtime concern; hosted routing/isolation topology may remain private.

## Initial implementation slice

The first code slice introduces:

- `CapacityWindowKind`;
- `MeasurementAuthority`;
- `ResourceObservation`;
- `ResourceCapacity`;
- `ResourceDemandEstimate`;
- protected-reserve accounting;
- explicit reset horizon;
- reservation/release/settlement primitives;
- fail-closed behavior when finite capacity is unknown;
- JSON schemas and focused tests.

It intentionally does **not** yet claim:

- integration with every provider meter;
- complete SII proposal wiring;
- full durable lease persistence;
- automatic scarcity pricing;
- full v0.52 multi-objective solving;
- hosted billing or portal behavior.

Those must build on these public primitives rather than bypass them.

## Permanent architectural rule

> No known target capability may be deferred in a way that makes current public contracts structurally incompatible with it. Implementation may be staged; architectural accommodation may not.
