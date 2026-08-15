# Resource-Governed Decision Foundation

**Status:** active implementation foundation for the v0.52 program; not a v0.52 completion claim.

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

The public resource model supports:

```text
FIXED
ROLLING
REFILLING
CREDIT_BALANCE
UNBOUNDED
UNKNOWN
```

A weekly subscription allowance is a capacity window with an explicit reset/refill horizon. The implementation does not hard-code OpenAI, Codex, ChatGPT, Anthropic, or any other provider into the kernel.

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

The v0.52 proposal successor binds expected resource demand directly into proposal identity:

```text
resource class / optional concrete resource
expected amount
upper bound
unit
confidence
```

`aasm.sii.resource-aware-proposal.v1` wraps the frozen parent SII proposal without rewriting v0.47-v0.51 semantics. Its fingerprint binds the parent proposal fingerprint, the resource demand vector, expected correctness, expected evidence quality, expected progress, expected wall time, expected monetary cost, and expected scarce-expert usage.

Missing decision-quality estimates fail closed to zero during routing compilation. Proposer confidence is not silently reinterpreted as correctness, evidence quality, or expected progress.

## Deterministic resource-aware routing

`aasm.resource.routing.v1` now provides the first governed candidate-selection slice.

Hard feasibility gates apply before ranking:

```text
correctness >= policy threshold
evidence quality >= policy threshold
expected progress >= policy threshold
all conservative resource demands are feasible
protected reserves remain intact
unknown finite capacity is not allocatable
```

Eligible candidates are then ordered lexicographically:

```text
1. maximize correctness
2. maximize evidence quality
3. maximize expected progress
4. minimize scarce expert usage
5. minimize monetary cost
6. minimize wall time
7. deterministic candidate ID tie-break
```

This means cheaper work never defeats a required quality threshold, while equivalent-quality work can preserve scarce expert-model allowance.

## Selection-to-reservation boundary

Selection does not itself consume capacity. The selected candidate's conservative demand envelope must be reserved before execution.

The foundation implements atomic reservation planning:

1. use each demand's upper bound when present;
2. resolve explicit resource IDs directly;
3. resolve class-only demands deterministically by resource ID;
4. preflight the complete allocation plan without mutation;
5. if any demand is infeasible, reserve nothing;
6. only after the whole plan is feasible, commit every reservation.

This prevents partial reservation and immediate oversubscription races in the in-process foundation model. Durable distributed reservation/lease ownership remains a later runtime integration step.

## Authority and resource rights are distinct

```text
Authority: may this principal perform this action in this scope?
Capacity/lease: may this work consume these resources?
```

Both may be required. Resource availability never grants authority; authority never implies unlimited resource rights.

## Reconciliation and replanning

Reservations are estimates, not final consumption. `ResourceCapacity.settle()` separates committed capacity from actual consumption and releases reservation slack during reconciliation.

The broader runtime still needs the durable transition family:

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

When expected consumption materially changes, the runtime must be able to pause and re-evaluate the plan before silently exceeding a lease or protected reserve.

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

The deterministic routing implementation is the first concrete lexicographic policy slice. It does not yet claim to be the full generic v0.52 Pareto/multi-objective engine.

## Scope compatibility

All new resource objects include principal/workspace/scope seams now so hosted multi-tenancy does not require replacing resource identity later. Resource-aware SII routing also preserves proposer and scope identifiers in its routing IR.

Scope enforcement remains a public-runtime concern; hosted routing/isolation topology may remain private.

## Delivered foundation slices

The implementation now includes:

- `CapacityWindowKind`;
- `MeasurementAuthority`;
- `ResourceObservation`;
- `ResourceCapacity`;
- `ResourceDemandEstimate`;
- `ResourceAwareStructuredProposal`;
- `ResourceAwareCandidate`;
- `ResourceRoutingPolicy`;
- `ResourceRoutingDecision`;
- `ResourceReservation`;
- protected-reserve accounting;
- explicit reset horizon;
- reservation/release/settlement primitives;
- fail-closed unknown finite capacity;
- conservative upper-bound feasibility;
- deterministic resource-aware selection;
- atomic multi-resource reservation;
- SII proposal → routing-candidate compilation;
- JSON schemas and focused/adversarial tests.

## Still required for v0.52 completion

This foundation intentionally does **not** yet claim:

- integration with every provider meter;
- durable resource capacity/observation persistence through the main event reducer;
- distributed reservation/lease ownership and race safety across workers/processes;
- full runtime submission/commit APIs for resource-aware SII proposals;
- automatic re-estimation/replan transitions;
- predicted-versus-actual calibration history;
- generic Pareto-frontier solving over resource-aware decision vectors;
- automatic scarcity pricing;
- hosted billing or portal behavior.

Those must build on these public primitives rather than bypass them.

## Permanent architectural rule

> No known target capability may be deferred in a way that makes current public contracts structurally incompatible with it. Implementation may be staged; architectural accommodation may not.
