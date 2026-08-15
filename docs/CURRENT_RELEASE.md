# AASM v0.56.0 — Truthful Solver Outcomes

AASM v0.56.0 is the active public package/runtime and advances the adoption contract to `aasm.adoption.v1 / 0.32.0`.

The stable remote wire-protocol compatibility surface remains **`aasm.remote.v1 / 0.19.0`**. That protocol version is intentionally independent of the package/runtime release version.

```text
active public surface: public_v56
active runtime: runtime_v56.AASMEngine
parent public surface: public_v55
parent runtime: runtime_v55.AASMEngine
remote wire protocol: aasm.remote.v1 / 0.19.0

truthful solver evidence:
  aasm.solver.outcome.v2
  aasm.solver.status.v2
  aasm.solver.termination.v2
  aasm.solver.evidence-grade.v1
  aasm.solver.status-v1-projection.v1
  aasm.solver.provider-status-map.v1
  aasm.solver.outcome-v2.runtime.v1
```

v0.56.0 is the first cumulative release in the v0.56 family. It completes work package **56.1 — Normalized Solver Outcome v2**. Later v0.56.x patch releases may add the remaining v0.56 work packages without reopening or weakening the v0.56.0 status contract.

## Authoritative detailed solver outcome

New v0.56 solver-facing features use `SolverOutcomeV2.normalized_status` as the authoritative detailed status. The older v1 optimization status is preserved and fingerprint-bound for compatibility, but projection from v2 to v1 is one-way and explicitly lossy where v1 cannot preserve the distinction.

The release distinguishes, among others:

- `OPTIMAL` from `FEASIBLE_NOT_PROVEN_OPTIMAL`;
- timeout/node/iteration/solution/memory/objective/user-interrupt termination with and without incumbents;
- `MODEL_INVALID` from `INFEASIBLE`;
- `NUMERICAL_FAILURE` from generic `UNKNOWN`;
- `PROVIDER_UNAVAILABLE` and `UNSUPPORTED_FEATURE` from internal errors;
- `STALE_RESULT` as a first-class fail-closed state;
- `UNBOUNDED` and `INFEASIBLE_OR_UNBOUNDED` from ordinary infeasibility.

## Independent incumbent admission

A nonempty assignment cannot become a v0.56 `*_WITH_INCUMBENT`, `SAT`, `OPTIMAL`, or `FEASIBLE_NOT_PROVEN_OPTIMAL` outcome merely because a provider returned values. AASM revalidates the assignment against the exact durable `OptimizationRequest` and model, including objective-value consistency where applicable, before the incumbent is accepted.

The resulting local validation is durable Evidence derived from the exact source result. Outcome normalization itself grants no truth authority.

## Provider status mapping

Provider status translation is versioned and exact. Substring/fuzzy inference is forbidden.

The v0.56.0 qualification corpus includes real provider identity/status checks for:

- CaDiCaL through PySAT;
- OR-Tools CP-SAT;
- HiGHS.

Raw native status names/codes are preserved. Unknown future provider statuses remain `UNKNOWN`; AASM does not guess their meaning from text fragments.

## Proof and optimality boundary

A provider `OPTIMAL` status plus an independently validated incumbent remains a provider optimality claim. It is **not** independently proved optimal merely by normalization. Proof certification remains the stronger v0.50 proof/checker boundary and requires its own checked certificate.

Likewise, negative provider status does not silently become proof-grade infeasibility.

## Durability and replay

Solver Outcome v2 records are stored through the existing AASM Evidence/event/reducer path. There is no parallel result table or alternate truth store. Outcome records bind the exact durable request/result/model/provider identities and survive SQLite restart/replay through the existing machine history.

## Exact release boundary

The dedicated `aasm/v56` gate checks:

- authoritative Solver Outcome v2 contracts and schemas;
- exhaustive roadmap-mandated terminal-class fixtures;
- independent incumbent-validation attacks;
- explicit lossy v2→v1 projection;
- exact provider-status mapping and ambiguity rejection;
- real CaDiCaL/PySAT, OR-Tools CP-SAT, and HiGHS qualification;
- active `public_v56` / released `public_v55` parent compatibility.

Repository-wide release publication remains gated by ordinary AASM CI, formal assurance, Semantic Solver RC, proof, solution-pool, optimization, scoped-authority, solver-learning, v0.54/v0.55 parent gates, and the active v0.56 gate on the same exact SHA.

Next cumulative release: **v0.56.1 — Execution Profiles + Runtime Provenance**.

AASM remains an `0.x` active-development project. License: Apache-2.0 project-wide under `LICENSE`, `NOTICE`, and `LICENSE_POLICY.md`.
