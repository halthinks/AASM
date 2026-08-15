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
REESTIMATE if assumptions change
   ├─ CONTINUE
   └─ REPLAN_REQUIRED → RELEASE → reroute
   ↓
ACTUAL CONSUMPTION + RESULT + EVIDENCE
   ↓
RECONCILE / VERIFY / LEARN
   ↓
future estimates and routing
```

AASM must not create a second hosted-only scheduler or accounting truth system. This work extends the existing resource, scheduler, economics, SII, scope, authority, Evidence/event replay, and optimization surfaces.

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
= declared allocatable
```

This prevents routine work from consuming scarce expert-model capacity that policy intends to preserve for difficult or critical work.

## Observation-backed planning capacity

Provider observations now participate in routing as a **policy-controlled conservative constraint**.

`planning_allocatable(capacity, policy)` starts from the declared allocatable envelope. A qualifying latest observation may reduce that envelope, but it may never expand it.

Conceptually:

```text
planning allocatable = min(
    declared allocatable,
    accepted observed remaining - committed - protected reserve
)
```

The observation constrains planning only when policy accepts its measurement authority and any configured confidence/freshness requirements are satisfied.

Default accepted authorities are:

```text
AUTHORITATIVE
OBSERVED
DERIVED
```

`DECLARED` is not accepted by default. A user-declared weekly allowance can constrain routing only when policy explicitly opts into that authority class.

Critical invariant:

> An observation may reduce what AASM is willing to spend. It never creates capacity that the declared resource envelope did not already grant.

Therefore an observed remaining value cannot turn `UNKNOWN` declared capacity into spendable capacity.

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

### Durable governed proposal lineage

A resource-aware successor cannot bypass governed SII admission.

The experimental v0.52 runtime requires:

```text
governed durable parent SII proposal
        ↓ exact fingerprint/proposer/scope binding
resource-aware successor Evidence
        ↓ derived_from
routing + reservation Evidence
```

A successor is rejected unless its parent proposal already exists in the governed SII projection with the same fingerprint, proposer, and scope. The successor Evidence records the parent proposal Evidence ID, and routing-by-successor-ID derives the routing transaction from the successor Evidence.

Workspace/scope filtering applies to successor proposal inspection and routing.

## Deterministic resource-aware routing

`aasm.resource.routing.v1` provides the first governed candidate-selection slice.

Hard feasibility gates apply before ranking:

```text
correctness >= policy threshold
evidence quality >= policy threshold
expected progress >= policy threshold
all conservative resource demands are feasible
protected reserves remain intact
unknown finite capacity is not allocatable
accepted provider observations may further constrain capacity
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

The foundation implements atomic in-memory reservation planning:

1. use each demand's upper bound when present;
2. resolve explicit resource IDs directly;
3. resolve class-only demands deterministically by resource ID;
4. preflight the complete allocation plan without mutation;
5. if any demand is infeasible, reserve nothing;
6. only after the whole plan is feasible, commit every reservation.

The experimental v0.52 runtime then persists the **selection and reservation together as one AASM Evidence/event transaction document**. Replay therefore cannot reconstruct a durable state in which the route was committed but its corresponding reservation was absent merely because those two facts were written as separate resource records.

This is durable single-machine transaction semantics over the existing AASM event path. Distributed compare-and-swap/lease ownership across multiple concurrent worker processes remains a separate hardening requirement.

## Scope-safe resource access

Workspace and scope are now enforced on the experimental resource runtime rather than remaining descriptive fields.

For a scoped capacity:

```text
workspace_id must match exactly
AND
caller scope must be allowed by the existing AASM scope-flow relation
```

Behavior is fail-closed:

- scoped capacity is invisible without matching context;
- wrong workspace cannot consume it;
- an unknown scope ID is rejected;
- cross-workspace observation is rejected;
- cross-workspace settlement is rejected without mutation;
- routing transactions and reservations carry their access context;
- inspect/report surfaces return only records visible in that context.

The runtime consumes the existing AASM scope hierarchy rather than inventing a second resource namespace.

This is **scope enforcement**, not yet the final scoped principal-authority calculus. `owner_principal_id` is present in the resource contract, but central Principal/Workspace/Scope authority delegation and capability ceilings remain a v0.53 hardening requirement and must be implemented centrally rather than as a resource-only ACL.

## Durable resource runtime

`aasm.resource.runtime.v1` is composed in experimental `runtime_v52` over the released v0.51 runtime. It does not replace the v0.51 engine, reducer, Evidence ledger, store, scheduler, truth model, or authority layer.

The runtime currently persists:

```text
capacity registration
resource observations
resource-aware SII successor proposals
routing decision + reservation transaction
reservation re-estimation transaction
reservation release transaction
settlement transaction
```

All resource state transitions are ordinary AASM Evidence records committed through the existing `EVIDENCE_ADDED` event path. Resource state is reconstructed as a deterministic projection over replayed Evidence.

The runtime contract explicitly preserves:

```text
RESOURCE_STATE_NEVER_GRANTS_AUTHORITY
RESOURCE_OBSERVATIONS_REMAIN_EVIDENCE
```

A reported weekly allowance therefore remains an observation with its measurement authority. Recording it can conservatively constrain planning under policy without silently rewriting declared capacity, transferring truth authority, or granting permission to spend it.

### Durable selection/reservation

`select_and_reserve_resource_candidate()`:

1. reconstructs current capacity from durable Evidence;
2. applies workspace/scope visibility;
3. applies declared capacity plus policy-accepted observation constraints;
4. runs deterministic resource-aware selection;
5. reserves the selected candidate's conservative demand envelope using the same policy;
6. records the decision, reservation, and post-capacity state in one durable transaction document;
7. returns no reservation when no candidate is eligible.

### Durable settlement

`settle_resource_reservation()`:

1. requires an ACTIVE durable reservation;
2. requires matching workspace/scope context;
3. requires actual-consumption keys to match the reserved resource set exactly;
4. reconciles committed capacity against actual measured consumption;
5. records post-settlement capacity in one durable settlement transaction;
6. marks the reservation SETTLED in projection;
7. rejects a second settlement of the same reservation.

### Durable re-estimation and replanning gate

`reestimate_resource_reservation()` handles a material change in expected resource use before settlement.

It temporarily evaluates the revised demand against the same current declared/observed planning constraints without mutating durable state first.

If the revised reservation remains feasible:

```text
ACTIVE
  ↓ REESTIMATE
CONTINUE
  ↓
ACTIVE with revised allocation
```

The revised committed allocation is persisted atomically with the re-estimation record.

If the revised reservation is not feasible:

```text
ACTIVE
  ↓ REESTIMATE
REPLAN_REQUIRED
```

The existing reservation remains committed; no extra capacity is consumed. Settlement is blocked because the reservation is no longer ACTIVE.

`release_resource_reservation()` can then move either `ACTIVE` or `REPLAN_REQUIRED` to `RELEASED`, freeing the existing committed allocation so the work can be rerouted.

This provides the replayable path:

```text
governed parent SII proposal
    ↓
resource-aware successor
    ↓
select + reserve
    ↓
execute externally under ordinary AASM authority/effect rules
    ↓
reestimate when assumptions change
    ├─ continue
    └─ replan required → release → reroute
    ↓
settle actual consumption
    ↓
Evidence/event history
    ↓
deterministic replay
```

## Authority and resource rights are distinct

```text
Authority: may this principal perform this action in this scope?
Capacity/lease: may this work consume these resources?
```

Both may be required. Resource availability never grants authority; authority never implies unlimited resource rights.

The experimental durable runtime deliberately does not invent an authority shortcut. Effect authorization remains on the existing AASM effect/authority path; the resource runtime governs capacity state, proposal lineage, selection, reservations, re-estimation, release, and settlement evidence.

Central principal-scoped authority hardening remains required before the public hosted-foundation boundary is frozen.

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
- `ResourceGovernanceRuntimeMixin`;
- experimental `runtime_v52` composition over `runtime_v51`;
- protected-reserve accounting;
- explicit reset horizon;
- fail-closed unknown finite capacity;
- conservative upper-bound feasibility;
- policy-controlled observation-backed planning capacity;
- confidence/freshness/measurement-authority gates for external capacity observations;
- deterministic resource-aware selection;
- atomic multi-resource reservation planning;
- scope-safe workspace/scope capacity access;
- durable governed-parent → resource-aware-successor proposal lineage;
- durable decision+reservation transaction records;
- durable re-estimation with `CONTINUE | REPLAN_REQUIRED`;
- durable release for rerouting;
- durable settlement transaction records;
- SII proposal → routing-candidate compilation;
- exact canonical replay coverage across the resource lifecycle;
- duplicate-settlement rejection;
- JSON schemas and focused/adversarial tests.

## Still required for v0.52 / hosted-foundation completion

This foundation intentionally does **not** yet claim:

- integration with every provider meter;
- distributed reservation/lease ownership and race safety across workers/processes;
- central principal-scoped authority delegation, capability ceilings, expiry, and nondelegable denies;
- automatic replacement-route execution after `REPLAN_REQUIRED`;
- `REQUEST_CAPACITY`, `THROTTLE`, `FALLBACK`, and `FREEZE` transition policies;
- predicted-versus-actual calibration history and learned resource estimation;
- generic Pareto-frontier solving over resource-aware decision vectors;
- dynamic scarcity forecasting from reset horizon, burn velocity, and forecast demand;
- automatic scarcity pricing;
- hosted billing or portal behavior.

Those must build on these public primitives rather than bypass them.

## Permanent architectural rule

> No known target capability may be deferred in a way that makes current public contracts structurally incompatible with it. Implementation may be staged; architectural accommodation may not.
