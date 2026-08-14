# AASM v0.46.0 — Advanced Solver Control & Search Artifacts

AASM v0.46 deepens the heterogeneous solver portfolio without replacing any released solver or authority path.

Release identity:

```text
package/public surface: 0.46.0
runtime: runtime_v46.AASMEngine
adoption: aasm.adoption.v1 / 0.22.0
advanced optimization: aasm.optimization.advanced.v1 / 0.1.0
base optimization: aasm.optimization.v1 / 0.1.0
convex optimization: aasm.optimization.convex.v1 / 0.1.0
PuLP adapter: aasm.adapter.pulp.v1 / 0.1.0
next: v0.47.0 Symbiotic Intelligence Interface & Governed Intelligence Economics
```

## Delivered

- real Kissat fast SAT through the dedicated PySAT `Kissat404` binding;
- incremental CaDiCaL assumptions and UNSAT core extraction;
- bounded in-process incremental SAT session reuse with learned state explicitly `EPHEMERAL_PERFORMANCE_ONLY`;
- conflict and decision budgets for incremental SAT;
- OR-Tools CP-SAT interval, optional-interval, `NO_OVERLAP`, and `CUMULATIVE` scheduling;
- deterministic-time/search telemetry for CP-SAT;
- HiGHS warm start submission, node limit, MIP relative-gap target, primal/dual bound, gap, node, and iteration telemetry;
- richer CVXPY lowering with factorized PSD/NSD quadratic forms and affine SOC constraints;
- `AdvancedSolverRequest` / `AdvancedSolverResult` contracts with UNSAT-core, bound, gap, and telemetry fields;
- exact provider/implementation/lease hardening and idempotent replay;
- v0.41 reuse-request integration under `OPTIMIZATION_RESULT`;
- public API, CLI, schemas, docs, dependency-neutral tests, and real-backend conformance.

## Preserved

The v0.44 direct CaDiCaL / OR-Tools CP-SAT / HiGHS paths remain active. The v0.45 CVXPY and PuLP surfaces remain active. Z3, cvc5, Vampire, and Lean 4 remain callable on the v0.39 formal-verification path.

All solver output remains Evidence. Search state and solver utility never acquire truth authority.

## Verification target

The release is accepted only when ordinary CI, Formal Assurance, and the dedicated Optimization Backends workflow are green on the same exact `main` SHA.
