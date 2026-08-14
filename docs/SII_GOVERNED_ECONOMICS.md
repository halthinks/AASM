# Governed Symbiotic Intelligence Interface & Intelligence Economics

AASM v0.47 graduates the Symbiotic Intelligence Interface from the v0.43 experimental certification target into a governed participation and resource-allocation plane.

Current contract:

```text
aasm.sii.v1 / 0.3.0
stability: GOVERNED_ENFORCED
```

The governing laws remain:

1. **The reasoner proposes; AASM measures.**
2. **Utility may buy resources; utility never buys truth.**
3. **SII returns compressed, governed intelligence — not merely a score.**

v0.47 closes the two explicit graduation gaps from the v0.43 preview: measurement identity is no longer accepted from a caller-supplied authority string, and ResourceLease values are no longer just advisory projections.

## One authority plane

v0.47 is a thin `SIIGovernanceRuntimeMixin + runtime_v46.AASMEngine` composition. It does not add a second scheduler, reducer, truth store, resource registry, capability registry, or epistemic authority system.

```text
reasoner / solver / human
        |
        v
StructuredProposal
        |
        v
v0.37 reasoning / Evidence lifecycle
        |
        +------------------------------+
        |                              |
        v                              v
measured durable outcome        v0.41 reuse telemetry
        |                              |
        +---------------+--------------+
                        v
               PerformanceVector
                        |
                        v
          versioned SIIScoringPolicy
                        |
                        v
             GovernedResourceLease
                        |
        +---------------+-------------------------------+
        |               |              |                |
        v               v              v                v
 v0.40 context      TaskDemand       TaskLease      native budgets
   projection        priority         lineage      SAT/CP/MILP/time
        |               |              |                |
        +---------------+--------------+----------------+
                        v
                     Evidence
```

## Durable principal binding

`SIIPrincipalBinding` is admitted only by existing `POLICY` or `CONTROLLER` authority. A binding records:

- stable `principal_id`;
- durable authority class;
- whether the principal may propose;
- whether the principal may measure SII outcomes;
- active/inactive state;
- optional metadata.

A principal may not silently rebind the same stable identity to a different authority class or role set. Measurement principals must resolve to `VERIFIER`, `POLICY`, or `CONTROLLER` in durable AASM state.

Outcome measurement therefore takes `measured_by_principal_id`; it does **not** take a caller-controlled authority class. The governed SII layer resolves that authority from the durable binding before delegating to the existing measured-outcome machinery.

A principal cannot measure its own proposal even when that principal legitimately holds a verifier role.

## Versioned scoring policy

Hard-coded v0.43 resource thresholds are replaced by durable `SIIScoringPolicy` objects admitted and activated by `POLICY` or `CONTROLLER`.

The default v0.47 policy is version `1.0.0`. It retains the seven measured dimensions already established by the SII preview:

- reliability;
- calibration;
- verified utility;
- reuse contribution;
- compute efficiency;
- conflict-learning value;
- artifact durability.

It also retains contextual profiles for default, exploration, exploitation, and formal work. Profiles and tier thresholds are now policy data rather than hidden constants in the active runtime.

The default resource tiers are:

| Tier | Required terminal samples | Minimum utility | Context tokens | Parallel discretionary tasks | Scheduler priority | Solver timeout | SAT conflict budget | SAT decision budget | CP-SAT deterministic time | CP-SAT workers | MILP node limit | Formal timeout | Portfolio width |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0.00 | 8,192 | 2 | 40 | 15 s | 10,000 | 20,000 | 1.0 | 1 | 500 | 15 s | 1 |
| 2 | 12 | 0.68 | 16,384 | 4 | 75 | 45 s | 50,000 | 100,000 | 5.0 | 2 | 5,000 | 45 s | 2 |
| 3 | 25 | 0.82 | 32,768 | 8 | 100 | 120 s | 250,000 | 500,000 | 20.0 | 4 | 25,000 | 120 s | 4 |

Those numbers are not epistemic thresholds. They allocate compute/search/context only.

## Concrete ResourceLease enforcement

`GovernedResourceLease` is durably linked to the proposer principal, active scoring policy, measured performance window, and resource tier. Its authority fields are fixed:

```text
authority_class       = PROPOSER
direct_truth_promotion = false
direct_state_mutation  = false
self_verification      = false
authority_reward       = NEVER
```

### Context

`sii_context()` converts `context_budget_tokens` into the existing v0.40 `ContextProjectionRequest.max_chars` boundary. Returned memory and reasoning items retain their original privacy, freshness, epistemic state, and authority.

### Scheduler priority

SII discretionary solver/formal requests are queued as the existing `TaskDemand` type. `scheduler_priority` is copied into the ordinary deterministic capability scheduler, not into a new SII queue.

### Parallel candidates

Before queueing a discretionary advanced-solver request, AASM counts outstanding SII-tagged tasks for that proposer. New work is rejected when `max_parallel_candidates` is exhausted.

### Native SAT budget

Incremental CaDiCaL requests are rewritten before admission so conflict and decision budgets cannot exceed the active SII lease. The resulting canonical advanced problem is what AASM fingerprints, records, leases, executes, and validates.

### CP-SAT budget

OR-Tools scheduling requests cap `max_deterministic_time` and `num_search_workers` at the active lease.

### MILP budget

HiGHS requests cap the MIP node limit at the active lease. Warm starts remain performance hints only.

### Convex budget

Advanced CVXPY requests are bounded by the governed solve timeout. The canonical convex model is not changed to make a problem easier or different.

### Formal verification

`request_sii_formal_verification()` is explicitly a **discretionary** resource-funded path and enforces timeout/portfolio-width limits.

Policy-required verification remains on the ordinary formal-verification path and is never reduced by SII. A low SII score cannot remove a required verifier, shrink a required independent-result quorum, or weaken a required proof strength. This is a deliberate asymmetry:

> SII may spend more compute on useful intelligence. It may not spend less correctness than policy requires.

## Durable enforcement provenance

Every enforced SII request records an `ENFORCEMENT` Evidence object derived from the governed ResourceLease and the solver/formal request Evidence. The queued `TaskDemand` is tagged with:

- proposer ID;
- principal ID;
- resource-lease ID;
- policy ID;
- resource tier;
- enforcement Evidence ID;
- `authority_reward = NEVER`.

A subsequent `TaskLease` copies ordinary task metadata, so the resource decision remains attributable through worker execution and replay.

## Certification

The v0.47 certification facade advances `aasm.certification.v1` to `0.2.0` and adds `sii-governance` to the default certification set.

For compatibility, the historical target name remains valid:

```bash
aasm certify --target sii-preview
```

In v0.47 that target is an alias for the governed graduation fixture and must return `PASS`, not the v0.43 expected `INCONCLUSIVE`.

The fixture adversarially checks:

- durable measurement-principal authority binding;
- versioned active scoring policy;
- rejection of unbound measurement actors;
- no authority reward through ResourceLease;
- native SAT conflict/decision/time budget enforcement;
- scheduler priority/provenance enforcement;
- mandatory verification non-reduction;
- exact event-sourced replay.

Certification remains a claim about observed deterministic AASM contract behavior. It is not a claim that arbitrary model or solver conclusions are semantically true.

## Compatibility

The v0.43 `create_sii(engine)` preview implementation and its durable proposal/outcome record format remain importable so existing integrations are not silently broken. The current public SII contract and recommended entry point are:

```python
from aasm import create_governed_sii, governed_sii_contract
```

The current package-level `sii_contract()` resolves to the governed v0.47 contract.

## Deliberate remaining limits

v0.47 does not yet make model-call execution itself a first-class metered TaskLease provider, does not allow SII to change canonical truth policy, and does not let learned SAT clauses or MILP cuts become durable knowledge merely because they improved performance.

The next release should build cross-run certified knowledge and governed long-term memory on this now-enforced resource/accountability plane.
