# AASM v0.45.0 — Convex Optimization & Modeling Adapters

AASM v0.45 extends the working v0.44 heterogeneous solver portfolio with a governed convex optimization capability and a PuLP compatibility boundary. The runtime is a thin `ConvexOptimizationRuntimeMixin + runtime_v44.AASMEngine` composition. It does not create a second scheduler, event log, reducer, provider registry, reuse plane, or truth store.

## Contracts

```text
aasm.adoption.v1 / 0.21.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.certification.v1 / 0.1.0
aasm.sii.v1 / 0.2.0              # experimental v0.46 target
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
```

## Executable portfolio

- SAT → PySAT/CaDiCaL
- CP-SAT → OR-Tools CP-SAT
- MILP → HiGHS/highspy
- convex LP/QP/SOC → CVXPY (`solver.convex@0.1.0`)
- SMT → Z3 / cvc5
- first-order theorem proving → Vampire
- proof-kernel checking → Lean 4

PuLP is deliberately not listed as a solver provider. `aasm.adapter.pulp.v1` translates supported `LpProblem` objects into the existing AASM optimization IR; native AASM routing then chooses the execution provider.

## Convex canonical subset

The v0.45 convex IR supports scalar continuous variables with optional finite bounds, linear equality/inequality constraints, diagonal positive-semidefinite quadratic minimization, diagonal negative-semidefinite quadratic maximization, and constant-radius second-order-cone constraints. Unsupported/non-convex forms are rejected rather than approximated.

CVXPY executes through the ordinary AASM `ResourceRecord → WorkerRecord → TaskDemand → TaskLease` path. Provider output is `EVIDENCE_ONLY`. AASM independently rechecks bounds, linear constraints, SOC feasibility, request/model identity, provider identity, and canonical objective evaluation before durable admission.

## PuLP compatibility

PuLP is `TRANSLATION_ONLY`; `solver_execution` is `NEVER`. The adapter supports finite-bounded continuous, integer, and binary variables, linear constraints, and linear objectives. A variable unbounded on either side is rejected because v0.45 will not invent a large finite bound and silently change semantics.

## Reuse

Convex results reuse the existing `OPTIMIZATION_RESULT` kind and v0.41 validation/certificate path. No solver output becomes automatically reusable merely because it was successful.

## Verification

The dedicated Optimization Backends workflow installs the complete optimization extra and runs real CaDiCaL, CP-SAT, HiGHS, CVXPY QP, CVXPY SOC, and PuLP→HiGHS lifecycle tests on Python 3.13. It requires both `aasm optimization-conformance --real` and `aasm modeling-conformance --real` to pass.

Release identity:

```text
package/public surface: 0.45.0
runtime: runtime_v45.AASMEngine
base optimization runtime: runtime_v44.AASMEngine
base solver/reuse kernel: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.21.0
next: v0.46.0 Symbiotic Intelligence Interface & Governed Intelligence Economics
```
