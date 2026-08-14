# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, native solvers, and long-horizon work.**

## Current release — v0.44.0

**Heterogeneous Optimization Solver Portfolio**

**Next release:** v0.45.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics

AASM v0.44 turns the existing v0.39 Capability ABI and v0.41 solver/reuse loop into a real heterogeneous optimization portfolio. The runtime now owns a canonical SAT/CP-SAT/MILP constraint IR and can route work through **CaDiCaL**, **OR-Tools CP-SAT**, and **HiGHS** using the same `ResourceRecord → WorkerRecord → TaskLease → Evidence` path already used throughout AASM.

The existing formal portfolio is preserved rather than replaced: **Z3**, **cvc5**, **Vampire**, and **Lean 4** remain callable through the v0.39 formal-verification pathway. The optimization workers are OPERATOR capabilities; the formal workers remain VERIFIER capabilities. Solver outputs remain Evidence, not authority.

### Release contracts

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
aasm.memory.index.v1 / 0.1.0
aasm.reasoning.frontier.v1 / 0.1.0
aasm.context.projection.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
aasm.semantic.dependencies.v1 / 0.1.0
aasm.reasoning.admission.v1 / 0.1.0
aasm.remote.v1 / 0.19.0
```

## Native optimization portfolio

```text
                           AASM
                            │
                 Canonical Constraint IR
                            │
        ┌──────────┬────────┼─────────┬────────────────────┐
        │          │        │         │                    │
       SAT       CP-SAT    MILP     SMT/FOL              PROOF
        │          │        │         │                    │
    CaDiCaL    OR-Tools   HiGHS   Z3 / cvc5 / Vampire    Lean 4
        │          │        │         │                    │
        └──────────┴────────┴─────────┴────────────────────┘
                            │
                   normalized Evidence
                            │
                  validated v0.41 reuse
```

### Canonical Constraint IR

AASM owns the semantic identity of optimization work. The v0.44 IR supports:

- variables: `BOOL`, `INTEGER`, `CONTINUOUS`;
- constraints: `CLAUSE`, `LINEAR`, `ALL_DIFFERENT`;
- linear objectives: `MINIMIZE`, `MAXIMIZE`;
- deterministic family selection: `SAT`, `CP_SAT`, or `MILP`.

`AUTO` never guesses an unsupported lowering. A pure Boolean clause model selects SAT; an integer/Boolean model representable by CP-SAT selects CP-SAT; a linear model representable by MILP selects MILP; anything outside the v0.44 canonical subset is rejected explicitly.

### SAT — CaDiCaL

`solver.sat@0.1.0` is backed by CaDiCaL through PySAT. AASM deterministically lowers Boolean clauses to integer CNF literals and recovers the Boolean assignment from the native solver.

### CP-SAT — OR-Tools CP-SAT

`solver.cp_sat@0.1.0` lowers Boolean/integer variables, clauses, integer linear constraints, all-different constraints, and integer linear objectives to OR-Tools CP-SAT. Reference execution fixes the random seed and uses one search worker.

### MILP — HiGHS

`solver.milp@0.1.0` lowers continuous/integer/Boolean variables and linear constraints/objectives through `highspy`.

### Existing formal providers remain active

The v0.39 formal pathway still calls:

- **Z3** — SMT-LIB2 through `formal.smt`;
- **cvc5** — SMT-LIB2 through `formal.smt`;
- **Vampire** — TPTP through `formal.first_order`;
- **Lean 4** — proof-kernel checking through `formal.proof_kernel`.

Z3/cvc5/Vampire/Lean outputs remain formal Evidence and cross the existing v0.37 epistemic-admission boundary before they can affect admitted knowledge.

## One scheduler and one authority path

v0.44 introduces a real runtime extension (`runtime_v44.AASMEngine`) because native optimization is executable kernel functionality, but it **does not** introduce another scheduler, reducer, event log, provider registry, or truth store.

The path is:

```text
OptimizationModel
      ↓
ordinary AASM Evidence
      ↓
OptimizationRequest
      ↓
ordinary AASM Obligation
      ↓
TaskDemand with capability + provider tokens
      ↓
existing ResourceRecord / WorkerRecord scheduler
      ↓
existing TaskLease
      ↓
native solver
      ↓
OptimizationResult
      ↓
AASM validates exact request/model/provider/lease/assignment
      ↓
ordinary Evidence
```

A provider must still be admitted by `POLICY` or `CONTROLLER` through the existing Capability ABI.

## Independent result checking

For `SAT`, `FEASIBLE`, and `OPTIMAL` results AASM independently rechecks the returned assignment against the canonical model before durable admission:

- exact request and model fingerprints;
- exact leased provider;
- admitted capability compatibility;
- bounds;
- Boolean/integer integrality;
- clauses;
- linear constraints;
- all-different constraints;
- objective value.

`UNSAT` and `INFEASIBLE` remain solver Evidence unless a separate proof/certificate path establishes stronger assurance. A solver result never directly authorizes reasoning or canonical truth.

## Reuse

Optimization uses the existing v0.41 reuse plane instead of adding a solver cache.

```text
native result Evidence
      ↓
POLICY/CONTROLLER reuse admission
      ↓
ordinary ReuseCandidate
      ↓
scope/privacy/environment/dependency/effect validation
      ↓
ReuseCertificate
      ↓
solver-loop SKIP_EXECUTION
```

A completed solver result is not automatically reusable. Cache/index deletion cannot change truth.

## Real-backend verification

The repository has a dedicated `Optimization Backends` GitHub Actions workflow. It installs the optional `optimization` extra and executes the real native backends:

- PySAT/CaDiCaL;
- OR-Tools CP-SAT;
- HiGHS/highspy.

It then runs each backend through AASM provider registration, task scheduling, lease claiming, native execution, result validation, Evidence commit, obligation completion, and replay. It also requires:

```bash
aasm optimization-conformance --real
```

to report `PASS` for all three native backends.

The regular CI suite separately checks Python 3.11/3.12/3.13, packaging, PostgreSQL, Compose/replay, scopes, adapters, LangGraph, and the dependency-neutral optimization lifecycle.

Formal Assurance includes bounded TLA+ and Promela models asserting that an optimization result requires a lease, produces Evidence, and cannot directly authorize knowledge.

## v0.43 certification remains active

The v0.43 certification layer still reports `PASS | FAIL | INCONCLUSIVE` and refuses to reinterpret missing evidence as success. Reference-domain, solver/reuse, truth/memory, and formal-verification certification remain available.

```python
from aasm import run_certification

report = run_certification()
assert report["core_status"] == "PASS"
```

## Symbiotic Intelligence Interface

SII remains staged above the solver plane and is now targeted for v0.45. Its three laws remain:

1. **The reasoner proposes; AASM measures.**
2. **Utility may buy resources; utility never buys truth.**
3. **AASM returns compressed governed intelligence, not merely a reputation score.**

This ordering is intentional: SII resource leases can now eventually allocate real computational budgets—SAT search/conflict budget, CP-SAT deterministic time, MILP nodes/iterations, formal-verification budget, model calls, context, and portfolio width—rather than only abstract reasoning resources.

SII still cannot grant direct truth promotion, direct canonical-state mutation, self-verification, `POLICY`, or `CONTROLLER` authority.

## Quick start

Base runtime:

```bash
pip install aasm-runtime
```

Native optimization portfolio:

```bash
pip install 'aasm-runtime[optimization]'
```

Example canonical model:

```python
from aasm import AASMEngine, ProblemSpec
from aasm.optimization import (
    BooleanLiteral,
    OptimizationConstraint,
    OptimizationModel,
    OptimizationVariable,
    default_optimization_providers,
)

engine = AASMEngine(ProblemSpec("native SAT"))
engine.install_default_optimization_capability_contracts(
    authority_id="policy",
    authority_class="POLICY",
)
provider = next(p for p in default_optimization_providers() if p.provider_id == "cadical")
engine.register_optimization_provider_runtime(
    provider,
    authority_id="policy",
    authority_class="POLICY",
)

model = OptimizationModel(
    "example",
    (OptimizationVariable("x", "BOOL"), OptimizationVariable("y", "BOOL")),
    (OptimizationConstraint("CLAUSE", literals=(BooleanLiteral("x"), BooleanLiteral("y"))),),
    family="SAT",
)
engine.admit_optimization_model(model)
request = engine.request_optimization(model.model_id, requester_id="agent", required_provider="cadical")
lease = engine.claim_next_task("worker-cadical", lease_seconds=60)
result = engine.execute_optimization_lease(lease["lease_id"])
assert result["result"]["status"] == "SAT"
```

## CLI

```bash
# v0.44 optimization surfaces
aasm optimization-contract
aasm optimization-blueprint
aasm optimization-conformance
aasm optimization-conformance --real

# v0.43 certification remains active
aasm certification-contract
aasm certify
aasm certify --target solver-reuse
aasm certify --target sii-preview
aasm sii-contract

# v0.42 reference stress remains active
aasm reference-domain-contract
aasm reference-domain-stress

# v0.41 reuse/solver loop remains active
aasm reuse-contract
aasm solver-loop-contract
```

## Roadmap

- v0.35 Semantic Problem Model ✅
- v0.36 Semantic Compiler SDK ✅
- v0.37 Reasoning Artifacts & Epistemic Admission ✅
- v0.38 Dependency Graph & Truth Maintenance ✅
- v0.39 Typed Capability ABI & Z3/cvc5/Vampire/Lean Formal Workers ✅
- v0.40 Hierarchical Memory, Reasoning Frontier & Context Projection ✅
- v0.41 Domain-Neutral Solver Loop & Deterministic Reuse Plane ✅
- v0.42 Reference Domains & Reuse/Memory/Reasoning Stress Tests ✅
- v0.43 Semantic Conformance, Adversarial Domains & Certification ✅
- **v0.44 Heterogeneous Optimization Solver Portfolio — CaDiCaL / CP-SAT / HiGHS ✅**
- **v0.45 next — Symbiotic Intelligence Interface & Governed Intelligence Economics**
- v0.46 Cross-Run Certified Knowledge & Governed Long-Term Memory
- v0.47 Semantic Solver Release Candidate

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md](docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md), [docs/SEMANTIC_CERTIFICATION.md](docs/SEMANTIC_CERTIFICATION.md), [docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md](docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md), and [docs/REUSE_AND_SOLVER_LOOP.md](docs/REUSE_AND_SOLVER_LOOP.md).
