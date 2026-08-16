# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, formal systems, native solvers, engineering workflows, governed memory, and cross-run knowledge.**

## Current release — v0.56.0

**Truthful Solver Outcomes + Governed Semantic Evolution + Engineering Mathematical IR**

**Next release / cumulative release:** v0.56.1 — Execution Profiles + Runtime Provenance

AASM is an event-sourced control plane for work that must survive retries, crashes, competing agents, changing evidence, external solvers, long-lived memory, external engineering tools, and prior-run knowledge **without allowing any of those inputs to silently become authority or truth**.

v0.56.0 makes solver outcome semantics truthful enough for later refinement and knowledge application: detailed status, termination, incumbent validation, bounds/gaps, evidence grade, raw provider status/code, and explicit lossy compatibility projection are governed separately. It preserves and extends all released v0.55 semantic-evolution, formulation, engineering-IR, and archive capabilities.

AASM's declared project license is **Apache License, Version 2.0 (`Apache-2.0`) across the project**. Previously granted MIT permissions remain valid for their recipients. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), and [`LICENSE_POLICY.md`](LICENSE_POLICY.md).

## Current release contracts

```text
package / public surface: 0.56.0
aasm.adoption.v1 / 0.32.0

v0.56 truthful solver evidence:
  aasm.solver.outcome.v2
  aasm.solver.status.v2
  aasm.solver.termination.v2
  aasm.solver.evidence-grade.v1
  aasm.solver.status-v1-projection.v1
  aasm.solver.provider-status-map.v1
  aasm.solver.outcome-v2.runtime.v1

parent v0.55 semantic evolution:
  aasm.external.reference.v1
  aasm.problem.revision.v1
  aasm.problem.delta.v1
  aasm.semantic-evolution.runtime.v1

parent v0.55 formulation governance:
  aasm.model.feature-set.v1
  aasm.provider.capability-manifest.v1
  aasm.model.admission.v1
  aasm.solver.formulation.v1
  aasm.solver.formulation-certificate.v1
  aasm.solver.formulation-execution-binding.v1
  aasm.solver.formulation-runtime.v1

parent v0.55 engineering IR:
  exact pseudo-Boolean/cardinality IR
  portable scheduling IR
  deterministic quadratic/conic IR
  governed decision-vector IR
  portable semantic-evolution archive

parent v0.54 execution/solver contracts remain public:
  aasm.effect.intent.v1
  aasm.effect.dispatch-request.v1
  aasm.effect.ownership.v1
  aasm.effect.reconciliation.v1
  aasm.effect.resource-settlement.v1
  aasm.solver.translation.v1
  aasm.solver.portfolio.v1
  aasm.solver.exchange.v1

license: Apache-2.0
```

## Why AASM exists

The failure mode AASM targets is architectural: useful reasoning, solver output, memory, cached results, model confidence, external-tool state, or prior-run success gets mistaken for authority.

AASM separates those concerns:

```text
proposal / observation / solver output / external receipt
                         |
                         v
                      Evidence
                         |
                validation / policy
                         |
                authority boundary
                         |
              durable machine state
```

Performance state may improve performance. Evidence may support a decision. Neither silently becomes truth or authority.

## v0.56 — Truthful Solver Outcomes

### Detailed status is no longer one overloaded enum

The released v0.55 optimization result remains preserved for compatibility, but new v0.56 solver-facing features use `SolverOutcomeV2.normalized_status` as the authoritative detailed outcome.

A v0.56 outcome separates:

```text
termination cause
solution / feasibility state
incumbent presence
incumbent validation
optimality claim
bounds / relative gap
proof status
evidence grade
raw provider status + code
provider mapping rule/version
legacy projection
```

Representative statuses include:

```text
OPTIMAL
FEASIBLE_NOT_PROVEN_OPTIMAL
INFEASIBLE
UNBOUNDED
INFEASIBLE_OR_UNBOUNDED
TIME_LIMIT_WITH_INCUMBENT
TIME_LIMIT_NO_SOLUTION
NODE_LIMIT_WITH_INCUMBENT
NODE_LIMIT_NO_SOLUTION
ITERATION_LIMIT_WITH_INCUMBENT
ITERATION_LIMIT_NO_SOLUTION
SOLUTION_LIMIT_WITH_INCUMBENT
SOLUTION_LIMIT_NO_SOLUTION
MEMORY_LIMIT_WITH_INCUMBENT
MEMORY_LIMIT_NO_SOLUTION
USER_INTERRUPT_WITH_INCUMBENT
USER_INTERRUPT_NO_SOLUTION
NUMERICAL_FAILURE
MODEL_INVALID
PROVIDER_UNAVAILABLE
UNSUPPORTED_FEATURE
STALE_RESULT
UNKNOWN_WITH_INCUMBENT
UNKNOWN_NO_SOLUTION
```

The old status vocabulary is available only through an explicit v2→v1 projection. That projection is marked lossy whenever v1 cannot preserve the detailed distinction.

### Incumbents are independently checked

A provider-returned assignment does not automatically become an accepted incumbent.

```text
provider assignment
      |
      v
exact OptimizationRequest + model
      |
      v
AASM independent assignment/objective validation
      |
      +--> FAIL: no accepted incumbent
      |
      v
validated incumbent Evidence
      |
      v
v0.56 *_WITH_INCUMBENT / SAT / OPTIMAL / FEASIBLE status
```

AASM records this validation through the existing Evidence/event path. No parallel solver-result truth table is introduced.

### Provider statuses are exact, not guessed

The provider-status-map contract forbids substring and fuzzy status inference.

Current qualified native status identities include:

- CaDiCaL through PySAT Boolean solve results;
- OR-Tools `CpSolverStatus` names/codes;
- HiGHS `HighsModelStatus` names/codes.

Unknown provider statuses remain unknown. A future string that happens to contain `time`, `optimal`, or `feasible` cannot silently acquire those semantics.

### Provider optimality is not proof certification

`OPTIMAL` means the provider made an optimal-completion claim and the returned incumbent passed independent source-model validation. It does **not** mean AASM independently proved global optimality.

```text
provider OPTIMAL + validated incumbent
              !=
independently checked proof certificate
```

The stronger proof boundary remains the released proof/checker subsystem.

### Full terminal-class coverage

The v0.56 release gate exercises the roadmap-mandated termination/failure classes, including time, node, iteration, solution, memory, user interrupt, numerical failure, invalid model, unavailable provider, unsupported feature, stale result, and unknown future provider states.

## v0.55 — Governed Semantic Evolution

### Stable external engineering identity

Engineering requirements and external domain objects can retain durable identity through solver compilation and revision changes.

```text
ExternalReference
      |
      v
ProblemRevision ---- ProblemDelta ----> ProblemRevision
      |
      v
ModelFeatureSet
      |
      v
SolverFormulation
      |
      v
provider execution binding
```

`ProblemRevision` and `ProblemDelta` are reconstructed through the existing Evidence/event path. v0.55 does **not** create a parallel revision truth table or a second change-impact graph.

Revision-dependent execution fails closed if:

- truth-maintenance work is still pending;
- the declared revision is not durable;
- the current usable head has changed;
- a formulation fingerprint no longer matches the revision it was certified against.

This matters for PCB/CAD/CAE and other engineering workflows because a solver result produced from revision `R1` cannot silently authorize work against `R2`.

## Governed solver formulations

A `SolverFormulation` binds:

- exact source model;
- exact target model;
- target provider identity;
- provider capability manifest;
- model feature set;
- model admission report;
- variable / constraint / objective mappings;
- external engineering-reference mappings;
- optional problem-revision ID and fingerprint.

The formulation must be durably registered before AASM will bind an execution request to it.

The built-in checker is intentionally narrow:

```text
built-in checker scope = EXACT_IDENTITY_ONLY
```

Non-trivial translations do not receive a PASS merely because an adapter produced them. They require an independent checker for the requested semantic fidelity.

## Exact pseudo-Boolean and cardinality IR

v0.55 adds typed Boolean-weighted constraints and cardinality constraints with deterministic exact linearization and independent reconstruction/checking.

Example semantic forms:

```text
2*a + 3*¬b + c <= 4

at_most(2, [a,b,c,d])
exactly(1, [route_A, route_B, route_C])
```

The lowering records source-to-target constraint mappings and preserves external-reference lineage.

```text
approximation = NOT_SUPPORTED_BY_THIS_CONTRACT
```

If exact semantics cannot be represented under the declared provider capability, admission fails closed.

## Portable global scheduling semantics

The scheduling IR represents:

- integer-duration tasks;
- earliest-start/latest-end windows;
- precedence with lag;
- no-overlap groups;
- cumulative resources;
- problem-revision binding;
- stable engineering-reference fingerprints;
- exact assignment validation;
- provider capability admission.

Resource capacity and demand are positive integers. Fractional resource demand is rejected rather than rounded or truncated.

AASM deliberately does **not** overclaim this layer:

```text
execution_adapter = NOT_CLAIMED_BY_THIS_FOUNDATION
```

The v0.55 public contract is a portable scheduling semantic/model + validation foundation. A complete provider execution adapter requires its own conformance evidence.

## Deterministic quadratic and conic representation

Engineering calculations often mix discrete topology/selection decisions with continuous geometry, electrical, thermal, structural, or resource constraints.

v0.55 therefore adds deterministic continuous representation using canonical decimal strings and `Decimal`-based validation for:

- bounded continuous variables;
- linear expressions;
- quadratic expressions and constraints;
- quadratic objectives;
- standard second-order-cone constraints;
- named absolute/relative tolerance policies;
- provider bindings and environment fingerprints.

The claim boundary is explicit:

```text
structural representation != feasibility proof
numerical validation       != global optimality proof
optimality_proof           = NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION
```

## Governed decision vectors — no hidden scalarization

AASM already supports exact finite lexicographic and Pareto reasoning. v0.55 adds the shared decision-vector seam needed by engineering and resource-governed workflows.

Hard floors are constraints, never weighted objectives:

```text
candidate
   |
   +--> hard correctness floor
   +--> hard evidence floor
   +--> hard engineering requirement
   |
   v
eligible candidates only
   |
   v
lexicographic objectives
```

A policy can express priorities such as:

```text
maximize:
  correctness
  evidence quality
  expected progress

minimize:
  provider quota burn
  scarce expert-model usage
  monetary cost
  wall time
```

But v0.55 does not collapse these into an undocumented weighted score:

```text
scalarization = NONE
```

Linear criteria compile into the existing exact-finite multi-objective engine only when the semantics match exactly. Named/nonlinear criteria remain representable but cannot be silently compiled.

## Portable semantic archive

`SemanticEvolutionArchive` packages:

- canonical snapshot material;
- complete durable event history;
- derived v0.55 semantic-evolution/formulation projections;
- per-section fingerprints;
- root fingerprint;
- root-derived archive identity.

Verification uses the archived **event sequence** as the replay source and runs the existing AASM reducer. The persisted snapshot is comparison evidence, not a replay input.

```text
replay source                      = ARCHIVED_EVENT_SEQUENCE_ONLY
persisted snapshot as replay input = false
derived projections grant truth    = false
```

Durable event sequence numbers are ordering provenance. They are **not** machine-state version counters; replayed machine version is checked against the persisted canonical snapshot version.

## v0.56 claim ceilings

AASM is explicit about what this release does not prove:

```text
solver outcome normalization truth authority
  = NONE

provider OPTIMAL
  != independent optimality proof

provider negative status
  != independent infeasibility proof

provider status text inference
  = FORBIDDEN

semantic-evolution truth authority
  = EXISTING_AASM_ADMISSION_PATH_ONLY

solver-formulation truth authority
  = NONE

pseudo-Boolean/cardinality approximation
  = NOT_SUPPORTED_BY_THIS_CONTRACT

scheduling execution adapter
  = NOT_CLAIMED_BY_THIS_FOUNDATION

continuous optimality proof
  = NOT_CLAIMED_BY_ASSIGNMENT_VALIDATION

decision-vector scalarization
  = NONE
```

## Core architecture

```text
                              AASM
                               |
                    canonical durable state
                               |
      +-----------+------------+------------+-----------+
      |           |            |            |           |
      v           v            v            v           v
  reasoning     memory       solvers      effects     external
      |           |            |            |         machines
      |           |            |            |           |
      +-----------+------------+------------+-----------+
                               |
                         Evidence/events
                               |
                  deterministic reducer + policy
```

Three persistent graphs remain central:

- **Decision graph** — what was chosen, rejected, superseded, or backjumped and why;
- **Obligation graph** — what remains mandatory, enabled, locked, satisfied, or invalidated;
- **Evidence graph** — what observations, certificates, solver results, and receipts support each conclusion.

AASM's AVATAR/CDCL-inspired architecture uses conditional activation, durable conflict learning, non-chronological recovery, restart without forgetting learned knowledge, and fairness controls without turning the runtime into a theorem prover.

## Engineering / TextPCB direction

v0.56 continues to shape AASM for demanding external engineering state machines without baking PCB or CAD types into the kernel.

The public seams now support:

```text
external requirement identity
        ↓
problem revision / delta
        ↓
feature + provider admission
        ↓
governed formulation
        ↓
discrete / scheduling / continuous IR
        ↓
truthful solver outcome
        ↓
external verification / execution evidence
        ↓
revision-safe re-evaluation
```

The kernel remains domain neutral. PCB/CAD/CAE-specific semantics belong in adapters and conformance packages.

## Quick start

```bash
git clone https://github.com/halthinks/AASM.git
cd AASM
python -m pip install -e '.[dev]'
pytest -q
```

Optional solver/modeling stack:

```bash
python -m pip install -e '.[dev,optimization,modeling]'
```

Optional PostgreSQL support:

```bash
python -m pip install -e '.[dev,postgres]'
```

Basic use:

```python
from aasm import AASMEngine
from aasm.model import ProblemSpec

engine = AASMEngine(ProblemSpec("governed engineering task"))
print(engine.snapshot.machine_id)
```

Inspect the active adoption contract:

```python
import aasm

report = aasm.validate_public_api_contract()
assert report["valid"]
assert aasm.__version__ == "0.56.0"
print(aasm.public_api_contract()["contract_version"])
```

## Verification

AASM uses independent, exact-head gates rather than treating documentation as evidence of implementation.

The v0.56-specific gate verifies:

```text
tracked file inventory
Solver Outcome v2 contracts and schemas
all roadmap-mandated terminal classes
independent incumbent validation
lossy v2→v1 compatibility projection
exact provider status mapping
real CaDiCaL / OR-Tools / HiGHS status identity
active public v0.56 surface
released v0.55 parent compatibility
```

### Reproducible release evidence

The permanent repository gates retain the evidence labels used by the Semantic Solver RC claim audit:

- **Python 3.11 / 3.12 / 3.13** — the main CI matrix;
- **Promela/SPIN** — bounded operational formal assurance alongside TLA+;
- **Optimization Backends** — native CaDiCaL, OR-Tools CP-SAT, HiGHS, CVXPY, and PuLP conformance where applicable;
- **Cross-Run Knowledge** — cross-run admission, replay, privacy, and non-inheritance-of-authority checks;
- **LICENSE_POLICY.md** — project-wide Apache-2.0 policy with earlier MIT grants preserved.

Repository-wide gates additionally cover build reproducibility, proof claims, solution pools, scoped authority, solver learning, semantic-solver RC certification, and exact immutable release-asset verification.

## Release progression

AASM has advanced by adding governed layers rather than replacing the deterministic core:

```text
v0.21  formal conflict-learning execution calculus
v0.22  profile/package contracts
v0.23  decision backend ecosystem
v0.24  formal assurance
v0.25  observability and inspection
v0.26–v0.32  adoption, local stack, adapters, scope and trace foundations
v0.37–v0.41  reasoning, dependencies, typed capabilities, memory, certified reuse
v0.42–v0.46  reference domains and optimization/modeling stack
v0.47  governed SII
v0.48  cross-run knowledge
v0.49  semantic solver release candidate
v0.50  proof-carrying solver claims
v0.51  solution pools and complete finite enumeration
v0.52  resource-governed multi-objective / Pareto decisions
v0.53  scoped authority and durable solver learning
v0.54  effect ownership + deterministic solver portfolio/exchange
v0.55  governed semantic evolution + engineering IR + portable archive
v0.56  truthful solver outcomes + exact provider status mapping
```

Historical release documentation remains under `docs/RELEASE_*.md` and the architecture/roadmap documents.

## Documentation

Start with:

- [`docs/CURRENT_RELEASE.md`](docs/CURRENT_RELEASE.md) — active v0.56 contract and boundaries;
- [`docs/RELEASE_0.56.md`](docs/RELEASE_0.56.md) — v0.56 release summary;
- [`docs/RELEASE_0.55.md`](docs/RELEASE_0.55.md) — parent v0.55 release summary;
- [`docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`](docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md) — semantic-evolution architecture;
- [`docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`](docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md) — implementation sequence;
- [`docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md`](docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md) — canonical execution ledger;
- [`WHY_AASM.md`](WHY_AASM.md) — project motivation;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — broader architecture;
- [`docs/FORMAL_CALCULUS.md`](docs/FORMAL_CALCULUS.md) — calculus background;
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow;
- [`SECURITY.md`](SECURITY.md) — security policy.

## Project status

AASM is an experimental `0.x` project. Public contracts are versioned and aggressively tested, but interfaces may still evolve between minor releases. Claims in the README are intended to stay below the evidence available from code, tests, and release gates.

**Current release:** `0.56.0`  
**Adoption contract:** `aasm.adoption.v1 / 0.32.0`  
**License:** Apache-2.0  
**Repository:** https://github.com/halthinks/AASM
