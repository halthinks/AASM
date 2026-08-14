# AASM v0.44.0 — Heterogeneous Optimization Solver Portfolio

AASM v0.44 adds executable SAT, CP-SAT, and MILP capabilities through a real `runtime_v44.AASMEngine` composition while preserving the existing AASM authority stack. The new runtime is `runtime_v41.AASMEngine` plus `OptimizationRuntimeMixin`; it does not introduce a second scheduler, reducer, event log, provider registry, or truth store.

Contracts:

```text
aasm.adoption.v1 / 0.20.0
aasm.optimization.v1 / 0.1.0
aasm.certification.v1 / 0.1.0
aasm.sii.v1 / 0.2.0              # experimental v0.45 target
aasm.reference-domains.v1 / 0.1.0
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.solver.loop.v1 / 0.1.0
aasm.memory.hierarchical.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
```

## Native optimization backends

- `cadical` — SAT through PySAT/CaDiCaL;
- `ortools-cp-sat` — integer/Boolean constraint programming through OR-Tools CP-SAT;
- `highs` — LP/MILP through HiGHS/highspy.

The existing formal providers remain active on the v0.39 pathway:

- Z3;
- cvc5;
- Vampire;
- Lean 4.

## Canonical IR and lowering

AASM now owns a canonical optimization identity for Boolean/integer/continuous variables, clause/linear/all-different constraints, and linear objectives. Deterministic family selection chooses SAT, CP-SAT, or MILP only when the current canonical subset can represent the model. Unsupported models are rejected rather than guessed.

## Existing scheduler and authority boundaries

Optimization provider admission reuses the v0.39 Capability ABI. Execution reuses ordinary `ResourceRecord`, `WorkerRecord`, `TaskDemand`, and `TaskLease` objects. Results are committed as ordinary Evidence and are explicitly `EVIDENCE_ONLY`.

Successful assignments are independently checked against the canonical model before durable admission. Solver claims of UNSAT/INFEASIBLE remain solver Evidence unless a separate proof/certificate path establishes stronger assurance.

## Reuse

Optimization results enter the v0.41 reuse plane only through explicit POLICY/CONTROLLER candidate admission. A future identical request may skip native execution only after ordinary reuse validation and durable `ReuseCertificate` commit.

## Verification

The standard CI suite checks the dependency-neutral optimization lifecycle along with Python 3.11/3.12/3.13, packaging, PostgreSQL, Compose/replay, scopes, adapters, and LangGraph.

A dedicated `Optimization Backends` workflow installs `python-sat`, `ortools`, and `highspy`, then executes real CaDiCaL, CP-SAT, and HiGHS solves through AASM's provider/resource/worker/lease/result path and requires `aasm optimization-conformance --real` to pass.

Formal Assurance includes `AASMOptimizationPortfolio.tla` and `aasm_optimization_portfolio.pml` to check that result commit requires a lease, solver output becomes Evidence, and solver execution cannot directly authorize knowledge.

## SII ordering

SII remains experimental and moves to v0.45. This is intentional: SII resource economics can now be bound to actual solver budgets and portfolio width rather than abstract compute alone.

Release identity:

```text
package/public surface: 0.44.0
runtime: runtime_v44.AASMEngine
base solver kernel: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.20.0
optimization: aasm.optimization.v1 / 0.1.0
certification: aasm.certification.v1 / 0.1.0
SII preview: aasm.sii.v1 / 0.2.0
remote: aasm.remote.v1 / 0.19.0
next: v0.45.0 Symbiotic Intelligence Interface & Governed Intelligence Economics
```
