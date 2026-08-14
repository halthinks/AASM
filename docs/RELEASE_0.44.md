# AASM v0.44.0 — Heterogeneous Optimization Solver Portfolio

AASM v0.44 adds a canonical optimization layer and real native SAT, CP-SAT, and MILP execution while preserving the existing formal solver and governance pathways.

## Contracts

```text
aasm.adoption.v1 / 0.20.0
aasm.optimization.v1 / 0.1.0
```

## New native backends

- CaDiCaL through PySAT for SAT;
- OR-Tools CP-SAT for integer/Boolean constraint optimization;
- HiGHS/highspy for LP/MILP.

Existing Z3, cvc5, Vampire, and Lean 4 formal workers remain active through the v0.39 formal-verification ABI.

## Runtime

```text
runtime_v44.AASMEngine
  = OptimizationRuntimeMixin
  + runtime_v41.AASMEngine
```

No second scheduler, reducer, event log, provider registry, or truth store was added.

## Canonical IR

The v0.44 AASM-owned IR supports:

- `BOOL`, `INTEGER`, and `CONTINUOUS` variables;
- `CLAUSE`, `LINEAR`, and `ALL_DIFFERENT` constraints;
- linear `MINIMIZE` and `MAXIMIZE` objectives;
- deterministic SAT / CP-SAT / MILP family selection.

## Execution boundary

Provider registration uses the existing v0.39 Capability ABI. Execution uses existing `ResourceRecord`, `WorkerRecord`, `TaskDemand`, and `TaskLease` objects.

Successful assignments are independently rechecked against the canonical model before durable result admission. Solver results are `EVIDENCE_ONLY`.

## Reuse

Optimization produces an ordinary v0.41 `ReuseRequest`. Results are not automatically reusable; a POLICY/CONTROLLER must admit a reusable candidate. Execution skipping still requires ordinary validation and durable `ReuseCertificate` commit.

## Verification

- dependency-neutral v0.44 regression suite;
- real native-backend GitHub Actions workflow;
- real `aasm optimization-conformance --real` execution;
- TLA+ `AASMOptimizationPortfolio` model;
- Promela/SPIN `aasm_optimization_portfolio.pml` model;
- standard Python, wheel, PostgreSQL, Compose/replay, scope, LangGraph, and adapter gates.

## Roadmap effect

SII graduation moves to v0.45 so ResourceLease economics can target real solver budgets and heterogeneous portfolio width.
