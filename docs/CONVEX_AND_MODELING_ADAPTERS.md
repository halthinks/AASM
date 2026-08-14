# AASM v0.45 Convex Optimization and Modeling Adapters

v0.45 extends the v0.44 heterogeneous solver portfolio without replacing its native execution paths.

## CVXPY

CVXPY is admitted as the `solver.convex@0.1.0` capability and executes only through the existing AASM resource -> worker -> TaskLease boundary. The v0.45 canonical convex IR supports scalar continuous variables, linear constraints, diagonal convex quadratic minimization / concave quadratic maximization, and constant-radius second-order-cone constraints. AASM rechecks variable bounds, linear constraints, SOC feasibility, and objective evaluation before the result can become durable Evidence.

CVXPY and its selected underlying numerical solver have **EVIDENCE_ONLY** authority. A provider verdict does not mutate canonical truth by itself.

The reference CVXPY worker deterministically prefers CLARABEL/SCS for SOC problems and OSQP/CLARABEL/SCS for QP problems based on installed backends. The selected backend is part of solver identity.

## PuLP

PuLP is not an AASM solver provider. `aasm.adapter.pulp.v1` is a translation-only compatibility boundary. It converts supported `LpProblem` instances into the existing `OptimizationModel`, after which ordinary AASM provider routing selects the native solver (for example HiGHS for MILP).

v0.45 deliberately rejects PuLP variables that are unbounded on either side because the v0.44 canonical MILP variable contract uses finite bounds. The adapter does not invent a large finite bound and therefore does not silently change problem semantics.

## Native paths remain preferred

- SAT -> CaDiCaL/PySAT
- CP-SAT -> OR-Tools CP-SAT
- MILP -> HiGHS
- Convex QP/SOC -> CVXPY
- SMT -> Z3/cvc5
- First-order theorem proving -> Vampire
- Proof kernel -> Lean 4

PuLP is an import surface only.

## Verification

The optimization CI extra installs CVXPY and PuLP alongside the v0.44 native solvers. Real conformance builds and solves QP and SOC models through CVXPY, imports a live PuLP MILP into the AASM canonical model, routes the imported model through the existing HiGHS lease path, and verifies replay and Evidence authority.
