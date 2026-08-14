# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, formal systems, and high-performance native solvers.**

## Current release — v0.45.0

**Convex Optimization & Modeling Adapters**

**Next release:** v0.46.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics

AASM is a deterministic, event-sourced agent state machine that separates proposal, execution, verification, authority, memory, solver output, and durable truth. v0.45 extends the executable heterogeneous solver portfolio with governed convex optimization through **CVXPY** and a **PuLP** import boundary, while preserving the direct native paths introduced in v0.44.

### Release contracts

```text
aasm.adoption.v1 / 0.21.0
aasm.remote.v1 / 0.19.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.certification.v1 / 0.1.0
aasm.sii.v1 / 0.2.0              # experimental v0.46 target
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
                         AASM semantic problem
                                  │
                     canonical problem identities
                                  │
       ┌───────────┬──────────┬───┴────┬──────────────┬─────────┐
       ▼           ▼          ▼        ▼              ▼         ▼
      SAT        CP-SAT      MILP    CONVEX         SMT/FOL    PROOF
       │           │          │        │              │         │
   CaDiCaL      OR-Tools    HiGHS    CVXPY       Z3 / cvc5   Lean 4
                                                   Vampire
       │           │          │        │              │         │
       └───────────┴──────────┴────────┴──────────────┴─────────┘
                                  │
                         normalized Evidence
                                  │
                      validation / certification
                                  │
                         governed v0.41 reuse
```

### SAT — CaDiCaL

`solver.sat@0.1.0` uses PySAT/CaDiCaL for native Boolean solving. AASM owns the canonical clauses, provider admission, lease, result identity, Evidence, and reuse boundary.

### CP-SAT — OR-Tools CP-SAT

`solver.cp_sat@0.1.0` handles Boolean/integer constraints, all-different constraints, clauses, integer linear constraints, and integer linear objectives through OR-Tools CP-SAT.

### MILP — HiGHS

`solver.milp@0.1.0` handles continuous/integer/Boolean variables and linear constraints/objectives through HiGHS/highspy.

### Convex optimization — CVXPY

`solver.convex@0.1.0` is the new v0.45 capability. The AASM-owned convex IR currently supports:

- scalar continuous variables with optional bounds;
- linear `<=`, `>=`, and equality constraints;
- diagonal convex quadratic minimization;
- diagonal concave quadratic maximization;
- constant-radius second-order-cone constraints `||x||₂ <= r`.

The reference worker uses CVXPY and selects an installed numerical backend appropriate to the problem class. The backend name is included in solver identity. AASM independently checks bounds, linear constraints, SOC feasibility, request/model identity, provider identity, and objective evaluation before the result can become durable Evidence.

A CVXPY result is **EVIDENCE_ONLY**. It does not promote truth or mutate canonical state by itself.

### PuLP — compatibility, not authority

PuLP is intentionally **not** an AASM solver provider.

`aasm.adapter.pulp.v1` is a `TRANSLATION_ONLY` adapter with `solver_execution = NEVER`. It converts supported `LpProblem` models into the existing AASM `OptimizationModel`; AASM then routes the canonical model to its native solver portfolio, such as HiGHS for MILP.

The v0.45 adapter supports finite-bounded continuous, integer, and binary variables, linear constraints, and linear objectives. It rejects variables that are unbounded on either side instead of inventing a large finite bound and silently changing model semantics.

### Formal providers remain active

The v0.39 formal-verification pathway remains unchanged:

- **Z3** — SMT-LIB2;
- **cvc5** — SMT-LIB2;
- **Vampire** — TPTP first-order theorem proving;
- **Lean 4** — trusted proof-kernel checking.

Formal solver output is Evidence and crosses the existing epistemic-admission boundary before it can affect admitted knowledge.

## One scheduler, one authority path

Neither v0.44 nor v0.45 creates a parallel execution authority.

```text
canonical model
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
result validation
      ↓
Evidence
      ↓
optional policy-gated reuse
```

Expired leases, superseded attempts, mismatched provider implementations, result-ID collisions, and non-idempotent completed-lease replays are rejected.

## Reuse

Optimization does not create an opaque cache. SAT/CP-SAT/MILP and convex work enters the existing v0.41 reuse plane as `OPTIMIZATION_RESULT` only after explicit candidate admission and ordinary scope/privacy/environment/dependency/effect validation.

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

Deleting a hot index changes performance only, never truth.

## Real-backend verification

The repository has a dedicated **Optimization Backends** workflow on Python 3.13. It installs:

- PySAT/CaDiCaL;
- OR-Tools;
- HiGHS/highspy;
- CVXPY;
- PuLP.

It executes real solver lifecycle tests through AASM and requires both:

```bash
aasm optimization-conformance --real
aasm modeling-conformance --real
```

to pass.

The ordinary CI matrix separately validates Python 3.11/3.12/3.13, packaging, PostgreSQL, Compose/replay, scopes, adapters, LangGraph, release contracts, and the dependency-neutral tests. Formal Assurance continues to run the bounded TLA+ and Promela/SPIN models.

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

## CVXPY example

```python
from aasm import AASMEngine, ProblemSpec
from aasm.convex_optimization import reference_convex_models

engine = AASMEngine(ProblemSpec("convex solve"))
engine.install_default_convex_capability_contract(
    authority_id="policy",
    authority_class="POLICY",
)
engine.register_default_cvxpy_provider_runtime(
    authority_id="policy",
    authority_class="POLICY",
)

model = reference_convex_models()["QP"]
engine.admit_convex_model(model)
request = engine.request_convex_optimization(model.model_id, requester_id="agent")
lease = engine.claim_next_task("worker-cvxpy", lease_seconds=60)
result = engine.execute_convex_lease(lease["lease_id"])
assert result["result"]["status"] == "OPTIMAL"
```

## PuLP import example

```python
import pulp
from aasm import AASMEngine, ProblemSpec
from aasm.optimization import default_optimization_providers

problem = pulp.LpProblem("allocation", pulp.LpMinimize)
x = pulp.LpVariable("x", 0, 10, cat=pulp.LpInteger)
y = pulp.LpVariable("y", 0, 10)
problem += x + y
problem += x + y >= 3

engine = AASMEngine(ProblemSpec("PuLP import"))
engine.install_default_optimization_capability_contracts(
    authority_id="policy",
    authority_class="POLICY",
)
highs = next(p for p in default_optimization_providers() if p.provider_id == "highs")
engine.register_optimization_provider_runtime(
    highs,
    authority_id="policy",
    authority_class="POLICY",
)
imported = engine.import_pulp_problem(problem, admit=True)
model_id = imported["admitted"]["model"]["model_id"]
request = engine.request_optimization(model_id, requester_id="agent", required_provider="highs")
lease = engine.claim_next_task("worker-highs", lease_seconds=60)
result = engine.execute_optimization_lease(lease["lease_id"])
```

PuLP never performs the solve in that flow. Its model is translated into AASM, and HiGHS executes the resulting AASM model.

## CLI

```bash
# v0.45
 aasm convex-optimization-contract
 aasm pulp-adapter-contract
 aasm modeling-conformance
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
- **v0.45 Convex Optimization & Modeling Adapters — CVXPY / PuLP ✅**
- **v0.46 next — Symbiotic Intelligence Interface & Governed Intelligence Economics**
- v0.47 Cross-Run Certified Knowledge & Governed Long-Term Memory
- v0.48 Semantic Solver Release Candidate

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/CONVEX_AND_MODELING_ADAPTERS.md](docs/CONVEX_AND_MODELING_ADAPTERS.md), [docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md](docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md), and [docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md](docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md).
