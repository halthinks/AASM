# AASM v0.45.0 — Convex Optimization & Modeling Adapters

Released 2026-08-14.

v0.45 adds `aasm.optimization.convex.v1 / 0.1.0` and `aasm.adapter.pulp.v1 / 0.1.0`, and advances the public adoption contract to `aasm.adoption.v1 / 0.21.0`.

CVXPY is a governed `solver.convex@0.1.0` OPERATOR capability using the existing AASM resource/worker/TaskLease boundary. The reference canonical subset covers linear constraints, diagonal convex/concave quadratic objectives, and constant-radius SOC constraints. Results remain `EVIDENCE_ONLY` and successful assignments are independently checked by AASM.

PuLP is a translation-only compatibility adapter. It never executes a solver inside AASM. Supported PuLP LP/MILP models compile into the existing v0.44 `OptimizationModel` and then use ordinary native provider routing such as HiGHS.

The original v0.44 CaDiCaL, OR-Tools CP-SAT, and HiGHS paths remain direct. Z3, cvc5, Vampire, and Lean 4 remain on the formal-verification path.

The real-backend workflow validates CVXPY QP/SOC solves and PuLP→HiGHS execution in addition to the complete v0.44 native portfolio.
