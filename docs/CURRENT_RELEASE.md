# AASM v0.46.0 — Advanced Solver Control & Search Artifacts

AASM v0.46 deepens the working heterogeneous solver portfolio with explicit search controls and solver-native artifacts while preserving the existing AASM authority architecture. The runtime is `AdvancedOptimizationRuntimeMixin + runtime_v45.AASMEngine`; there is still one scheduler, one event/reducer path, one provider registry, one reuse plane, and one truth boundary.

## Contracts

```text
aasm.adoption.v1 / 0.22.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.certification.v1 / 0.1.0
aasm.sii.v1 / 0.2.0              # experimental v0.47 target
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
```

## Executable portfolio

- fast SAT → Kissat through PySAT `Kissat404`;
- incremental SAT → CaDiCaL assumptions / UNSAT core / bounded in-process session reuse;
- CP-SAT → OR-Tools CP-SAT, now including interval scheduling, `NO_OVERLAP`, and `CUMULATIVE`;
- MILP → HiGHS/highspy, now including warm start, node/gap controls, and primal/dual bound telemetry;
- convex optimization → CVXPY, now including factorized general PSD/NSD quadratics and affine SOC;
- LP/MILP model import → PuLP translation-only adapter;
- SMT → Z3 / cvc5;
- first-order theorem proving → Vampire;
- proof-kernel checking → Lean 4.

The v0.44 direct native paths remain available; v0.46 adds richer contracts rather than forcing every problem through the advanced layer.

## Search-state boundary

The v0.46 law is **SEARCH_STATE_NEVER_PROMOTES_TRUTH**.

Solver output, UNSAT cores, bounds, incumbents, warm starts, learned search state, and telemetry remain `EVIDENCE_ONLY` or performance state. Incremental CaDiCaL learned state is explicitly `EPHEMERAL_PERFORMANCE_ONLY`: it can make a later solve cheaper, but deleting it cannot change AASM truth or durable meaning.

## Incremental SAT

`solver.sat.incremental@0.1.0` binds each request to an admitted canonical SAT model plus exact assumptions. The worker can apply conflict/decision budgets, retain a bounded in-process CaDiCaL session, return an UNSAT core over request assumptions, and expose whether the session was reused. The durable result is still validated and admitted through the ordinary lease/Evidence path.

## CP-SAT scheduling

`solver.cp_sat.scheduling@0.1.0` adds fixed/optional intervals, `NO_OVERLAP`, `CUMULATIVE`, search-worker count, and deterministic-time budget. AASM independently rechecks interval equations, overlap, cumulative resource load, base constraints, and objective values.

## Advanced MILP

`solver.milp.advanced@0.1.0` adds a warm start, MIP relative-gap target, node limit, MIP node count, simplex iteration count, primal/dual bound, and gap telemetry. Warm starts and incumbents are performance hints, never canonical-model mutations.

## Advanced convex optimization

`solver.convex.advanced@0.1.0` represents richer convex quadratics structurally as weighted squares of linear forms, allowing cross terms while keeping positive-semidefiniteness explicit. Affine SOC constraints use `||A x + b||₂ <= cᵀx + d`. AASM independently evaluates the canonical objective and feasibility before result Evidence is accepted.

## Reuse

Advanced results enter the existing v0.41 `OPTIMIZATION_RESULT` reuse plane. A prior result can skip execution only after normal candidate admission, applicability validation, and a committed `ReuseCertificate`. Ephemeral learned SAT state is not a durable reusable truth object.

## Verification

The dedicated Optimization Backends workflow executes the real v0.44, v0.45, and v0.46 solver stacks on Python 3.13. v0.46 specifically verifies Kissat, incremental CaDiCaL assumptions/UNSAT core/session reuse, CP-SAT scheduling, HiGHS warm-start/bound-gap behavior, and advanced CVXPY. Ordinary CI separately checks Python 3.11/3.12/3.13, packaging, PostgreSQL, Compose/replay, scopes, adapters, and LangGraph. Formal Assurance model-checks the shared lease/Evidence authority boundary and source-gates v0.46's non-authoritative search-state invariants.

Release identity:

```text
package/public surface: 0.46.0
runtime: runtime_v46.AASMEngine
base convex runtime: runtime_v45.AASMEngine
base optimization runtime: runtime_v44.AASMEngine
base solver/reuse kernel: runtime_v41.AASMEngine
adoption: aasm.adoption.v1 / 0.22.0
next: v0.47.0 Symbiotic Intelligence Interface & Governed Intelligence Economics
```
