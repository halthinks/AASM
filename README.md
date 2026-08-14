# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, formal systems, and high-performance native solvers.**

## Current release — v0.46.0

**Advanced Solver Control & Search Artifacts**

**Next release:** v0.47.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics

AASM is a deterministic, event-sourced agent state machine that separates proposal, execution, verification, authority, memory, solver output, search state, and durable truth. v0.46 deepens the executable heterogeneous solver portfolio with **Kissat fast SAT**, **incremental CaDiCaL assumptions/UNSAT cores**, **OR-Tools CP-SAT scheduling**, **HiGHS warm-start/bound-gap controls**, and richer **CVXPY factorized quadratic + affine-SOC** optimization, while preserving every released direct and formal solver path.

### Release contracts

```text
aasm.adoption.v1 / 0.22.0
aasm.remote.v1 / 0.19.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.certification.v1 / 0.1.0
aasm.sii.v1 / 0.2.0              # experimental v0.47 target
aasm.reference-domains.v1 / 0.1.0
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.solver.loop.v1 / 0.1.0
aasm.memory.hierarchical.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
```

## Solver portfolio

```text
                              AASM
                               │
                    canonical problem identities
                               │
       ┌─────────┬─────────────┼────────────┬──────────────┬─────────┐
       ▼         ▼             ▼            ▼              ▼         ▼
      SAT     CP-SAT          MILP        CONVEX         SMT/FOL    PROOF
       │         │             │            │              │         │
 Kissat /     OR-Tools      HiGHS         CVXPY       Z3 / cvc5   Lean 4
 CaDiCaL      scheduling   warm starts   QP / SOC       Vampire
       │         │             │            │              │         │
       └─────────┴─────────────┴────────────┴──────────────┴─────────┘
                               │
                      normalized Evidence
                               │
                 validation / certification / reuse
```

The original direct v0.44 routes remain first-class:

- `solver.sat@0.1.0` → CaDiCaL;
- `solver.cp_sat@0.1.0` → OR-Tools CP-SAT;
- `solver.milp@0.1.0` → HiGHS;
- `solver.convex@0.1.0` → CVXPY;
- PuLP → translation-only import into AASM IR.

v0.46 adds richer search/control capabilities where the problem benefits from them.

## Fast SAT — Kissat

`solver.sat.fast@0.1.0` uses PySAT's dedicated Kissat binding for non-incremental high-performance Boolean solving. AASM owns the clauses, provider admission, TaskLease, result identity, Evidence, and reuse boundary. The current Kissat binding does not expose aggregate statistics; AASM records that as a telemetry limitation rather than misclassifying a successful solve.

## Incremental SAT — CaDiCaL

`solver.sat.incremental@0.1.0` supports:

- exact Boolean assumptions;
- UNSAT core extraction over assumptions;
- conflict budget;
- decision budget;
- bounded in-process session reuse.

CaDiCaL can retain learned search state while an in-process session lives, but AASM labels that state **EPHEMERAL_PERFORMANCE_ONLY**. It is not a durable claim, not a reusable truth object, and deleting it cannot change canonical meaning.

## CP-SAT scheduling — OR-Tools

`solver.cp_sat.scheduling@0.1.0` extends the existing CP-SAT lowering with:

- fixed interval variables;
- optional intervals;
- `NO_OVERLAP`;
- `CUMULATIVE` resource constraints;
- configurable search-worker count;
- deterministic-time budget;
- conflict, branch, deterministic-time, and wall-time telemetry.

AASM independently rechecks interval equations, overlap, cumulative resource load, base constraints, and objective values before successful solver output becomes durable Evidence.

## Advanced MILP — HiGHS

`solver.milp.advanced@0.1.0` adds:

- warm start submission;
- MIP relative-gap target;
- node limit;
- primal/dual bound telemetry;
- MIP gap;
- node and simplex-iteration telemetry.

Warm starts and incumbents are search hints only. They do not modify the canonical AASM model or weaken feasibility validation.

## Advanced convex optimization — CVXPY

`solver.convex.advanced@0.1.0` adds a richer AASM-owned convex representation without making arbitrary CVXPY expressions canonical. It supports:

- scalar continuous variables;
- linear equality/inequality constraints;
- factorized positive-semidefinite quadratic minimization;
- factorized negative-semidefinite quadratic maximization;
- cross terms through weighted squares of linear forms;
- affine second-order-cone constraints `||A x + b||₂ <= cᵀx + d`.

The factor representation makes convexity structural rather than an unchecked backend assertion. AASM independently re-evaluates bounds, linear constraints, SOC feasibility, request/problem/provider identity, and canonical objective value before result Evidence is accepted.

## PuLP — compatibility, not authority

PuLP remains intentionally **not** an AASM solver provider. `aasm.adapter.pulp.v1` is `TRANSLATION_ONLY` with `solver_execution = NEVER`: supported `LpProblem` models are converted into AASM's canonical optimization IR and then routed to native providers such as HiGHS.

The adapter supports finite-bounded continuous, integer, and binary variables, linear constraints, and linear objectives. It rejects an unbounded side instead of inventing a large finite bound and silently changing problem semantics.

## Formal providers remain active

The v0.39 formal-verification path is unchanged:

- **Z3** — SMT-LIB2;
- **cvc5** — SMT-LIB2;
- **Vampire** — TPTP first-order theorem proving;
- **Lean 4** — trusted proof-kernel checking.

Formal solver output is Evidence and crosses the existing epistemic-admission boundary before it can affect admitted knowledge.

## One scheduler, one authority path

v0.46 does **not** create another execution authority.

```text
canonical problem
      ↓
CapabilityContract
      ↓
POLICY / CONTROLLER provider admission
      ↓
ResourceRecord
      ↓
WorkerRecord
      ↓
TaskDemand
      ↓
TaskLease
      ↓
solver execution
      ↓
AASM validation
      ↓
Evidence
      ↓
optional policy-gated reuse
```

Expired leases, superseded attempts, mismatched provider implementations, result-ID collisions, and non-idempotent completed-lease replays are rejected.

The v0.46 law is:

> **SEARCH_STATE_NEVER_PROMOTES_TRUTH.**

UNSAT cores, bounds, gaps, incumbents, warm starts, learned search state, and solver telemetry can improve computation or provide Evidence; none can directly authorize AASM knowledge.

## Reuse

Optimization still does not create an opaque truth cache. Advanced solver results use the existing v0.41 `OPTIMIZATION_RESULT` plane only after explicit candidate admission and ordinary scope/privacy/environment/dependency/effect validation.

```text
prior solver Evidence
       ↓
POLICY / CONTROLLER candidate admission
       ↓
ReuseRequest + ReuseCandidate validation
       ↓
ReuseCertificate
       ↓
solver-loop SKIP_EXECUTION
```

Ephemeral learned SAT state is not part of durable reuse. Deleting a hot index or incremental solver session changes performance only, never truth.

## Real-backend verification

The dedicated **Optimization Backends** workflow on Python 3.13 installs and executes the real solver stack:

- Kissat through PySAT;
- CaDiCaL through PySAT;
- OR-Tools CP-SAT;
- HiGHS/highspy;
- CVXPY;
- PuLP.

It preserves the released v0.44/v0.45 real lifecycle tests and adds v0.46 real tests for:

- Kissat execution;
- incremental CaDiCaL assumptions + UNSAT core + session reuse;
- CP-SAT interval/no-overlap/cumulative scheduling;
- HiGHS warm start + bound/gap telemetry;
- advanced CVXPY factorized quadratic + affine SOC.

The conformance surfaces are:

```bash
aasm optimization-conformance --real
aasm modeling-conformance --real
aasm advanced-optimization-conformance --real
```

The ordinary CI matrix separately validates Python 3.11/3.12/3.13, packaging, PostgreSQL, Compose/replay, scopes, adapters, LangGraph, release contracts, and dependency-neutral tests. Formal Assurance continues the bounded TLA+ and Promela/SPIN models over the shared lease/Evidence authority boundary and source-gates v0.46's non-authoritative search-state rules.

## Installation

Base runtime:

```bash
pip install aasm-runtime
```

Full native optimization + modeling portfolio:

```bash
pip install 'aasm-runtime[optimization]'
```

CVXPY + PuLP modeling surfaces only:

```bash
pip install 'aasm-runtime[modeling]'
```

## Advanced solver example

```python
from aasm import AASMEngine, ProblemSpec
from aasm.advanced_optimization import (
    ADVANCED_PROVIDERS,
    default_advanced_providers,
    reference_advanced_problems,
)

engine = AASMEngine(ProblemSpec("advanced SAT"))
engine.install_default_advanced_optimization_capabilities(
    authority_id="policy",
    authority_class="POLICY",
)

provider = next(
    row for row in default_advanced_providers()
    if row.provider_id == ADVANCED_PROVIDERS["INCREMENTAL_SAT"]
)
engine.register_advanced_optimization_provider_runtime(
    provider,
    authority_id="policy",
    authority_class="POLICY",
)

problem = reference_advanced_problems()["INCREMENTAL_SAT"]
engine.admit_optimization_model(problem.model)
request = engine.request_advanced_optimization(problem, requester_id="agent")
lease = engine.claim_next_task("worker-cadical-incremental", lease_seconds=60)
result = engine.execute_advanced_optimization_lease(lease["lease_id"])
assert result["result"]["status"] == "UNSAT"
assert result["result"]["unsat_core"]
```

## CLI

```bash
# v0.46 advanced solver control
aasm advanced-optimization-contract
aasm advanced-optimization-blueprint
aasm advanced-optimization-conformance
aasm advanced-optimization-conformance --real

# v0.45 modeling surfaces
aasm convex-optimization-contract
aasm pulp-adapter-contract
aasm modeling-conformance --real

# v0.44 native portfolio
aasm optimization-contract
aasm optimization-blueprint
aasm optimization-conformance --real

# v0.43 certification
aasm certification-contract
aasm certify
aasm certify --target solver-reuse
aasm certify --target sii-preview
```

## Roadmap

- v0.35 Semantic Problem Model ✅
- v0.36 Semantic Compiler SDK ✅
- v0.37 Reasoning Artifacts & Epistemic Admission ✅
- v0.38 Dependency Graph & Truth Maintenance ✅
- v0.39 Typed Capability ABI + Z3/cvc5/Vampire/Lean ✅
- v0.40 Hierarchical Memory & Context Projection ✅
- v0.41 Domain-Neutral Solver Loop & Deterministic Reuse ✅
- v0.42 Reference-Domain Stress Tests ✅
- v0.43 Semantic/Adversarial Certification ✅
- v0.44 Heterogeneous Optimization — CaDiCaL / CP-SAT / HiGHS ✅
- v0.45 Convex Optimization & Modeling Adapters — CVXPY / PuLP ✅
- **v0.46 Advanced Solver Control & Search Artifacts — current ✅**
- **v0.47 next — Symbiotic Intelligence Interface & Governed Intelligence Economics**
- v0.48 Cross-Run Certified Knowledge & Governed Long-Term Memory
- v0.49 Semantic Solver Release Candidate

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/ADVANCED_SOLVER_CONTROL.md](docs/ADVANCED_SOLVER_CONTROL.md), [docs/CONVEX_AND_MODELING_ADAPTERS.md](docs/CONVEX_AND_MODELING_ADAPTERS.md), [docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md](docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md), and [docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md](docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md).
