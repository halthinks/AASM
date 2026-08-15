# AASM v0.53.0 — Durable Cross-Run Solver Learning + Scoped Identity/Authority Hardening

AASM v0.53.0 makes scoped identity, scoped authority, safe persistence access, distributed resource commit protection, external-effect authority, and durable solver learning part of the active public runtime.

## Highlights

- Added `aasm.authority.scoped.v1` with explicit Principal/Workspace/Scope grants, default deny, DENY precedence, expiry, nondelegability, delegation ceilings, and no cross-run authority inheritance.
- Added `aasm.store.scoped.v1`, a fail-closed read-only persistence facade. Ambiguous or cross-workspace raw reads fail closed; direct store writes remain governed runtime transitions.
- Resource mutations now require scoped authority and derive actor provenance from durable authorization Evidence.
- Added optimistic machine-version guards for resource-state Evidence commits. Stale conflicting reservations fail closed and canonical state is reloaded. Verified on MemoryStore, SQLite, and PostgreSQL.
- Effect authorization, execution, and reconciliation now have distinct scoped capabilities; every external execution attempt requires a fresh authority decision.
- Added `aasm.solver.learning.v1` for `NO_GOOD`, `UNSAT_CORE`, `BOUND`, `INCUMBENT`, `WARM_START`, and `NATIVE_ACCELERATOR` learning artifacts.
- Cross-run learning reuses the existing v0.48 `REUSE_RESULT` envelope/admission pathway. Foreign authority is never inherited and cross-run admission never implies truth.
- Correctness-sensitive learning remains inert until receiving-run local revalidation succeeds for the exact model.
- Added `aasm.solver.learning.application.v1`; exact PASS validation plus scoped `solver.learning.apply` is required before application.
- Solver-learning application has `truth_authority = NONE` and `policy_authority = NONE`.
- Certified pruning lowers into the existing optimization IR/provider path. The existing OR-Tools CP-SAT adapter consumes validated assignment hints with `CpModel.add_hint(...)` and reports consumed application IDs.
- Added dedicated exact-SHA `aasm/scoped-authority` and `aasm/solver-learning` gates and made both mandatory for release publication.

## Preserved boundaries

v0.53 does not replace v0.52 multi-objective/resource semantics, v0.51 enumeration, v0.50 proof certification, v0.49 Semantic Solver RC, v0.48 cross-run admission, or v0.47 governed SII. Those remain versioned parent contracts.

The following remain non-authoritative by construction:

```text
foreign knowledge
resource availability
solver-learning validation/application
optimization results
model confidence
performance hints
```

Only governed AASM policy and authorized transitions may change durable machine state.
