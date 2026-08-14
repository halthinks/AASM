# AASM v0.47.0 — Governed Symbiotic Intelligence & Intelligence Economics

AASM v0.47 graduates SII from the v0.43 experimental preview into an enforceable participation/resource plane over the real v0.46 solver substrate.

## Contracts

```text
aasm.adoption.v1 / 0.23.0
aasm.certification.v1 / 0.2.0
aasm.sii.v1 / 0.3.0
```

The existing solver contracts remain unchanged and active:

```text
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
```

## Delivered

- durable POLICY/CONTROLLER-admitted SII principal bindings;
- measurement authority resolved from durable principal state instead of caller-supplied authority strings;
- stable-principal rebinding rejection;
- versioned durable scoring policy with explicit profile/tier data;
- governed ResourceLease records with authority permanently limited to `PROPOSER`;
- context budgets enforced through v0.40 context projection;
- scheduler priority enforced through existing `TaskDemand` ordering;
- parallel discretionary-task budget enforcement;
- incremental CaDiCaL conflict/decision budget enforcement;
- CP-SAT deterministic-time and worker-count budget enforcement;
- HiGHS node-budget enforcement;
- convex/native solver timeout enforcement;
- discretionary formal-verification timeout/portfolio-width enforcement;
- explicit rule that mandatory verification is never reduced by SII;
- durable request/lease/enforcement provenance copied into the ordinary TaskLease path;
- `aasm.certification.v1 / 0.2.0` governed SII graduation fixture;
- `sii-preview` retained as a compatibility alias that now executes the governed graduation check;
- public API, CLI, schemas, docs, regression/adversarial tests, replay checks, and release gates.

## Runtime composition

```text
runtime_v47.AASMEngine
  = SIIGovernanceRuntimeMixin
  + runtime_v46.AASMEngine
```

There is no second scheduler, reducer, event log, truth store, capability registry, or solver kernel.

## Invariant

```text
UTILITY MAY BUY COMPUTE / SEARCH / CONTEXT.
UTILITY NEVER BUYS TRUTH / STATE AUTHORITY / SELF VERIFICATION.
REQUIRED VERIFICATION IS NEVER REDUCED BY SII.
```

## Next

v0.48 — Cross-Run Certified Knowledge & Governed Long-Term Memory.
