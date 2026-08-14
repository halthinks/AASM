# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, formal systems, and high-performance native solvers.**

## Current release — v0.47.0

**Governed Symbiotic Intelligence & Intelligence Economics**

**Next release:** v0.48.0 — Cross-Run Certified Knowledge & Governed Long-Term Memory

AASM is a deterministic, event-sourced control plane that separates proposal, execution, verification, authority, memory, solver output, search state, resource allocation, and durable truth.

v0.47 closes the loop between AASM's semantic/authority machinery and the real native solver substrate introduced in v0.44–v0.46. SII can now measure which reasoners are producing durable value and allocate **more or less compute, search, context, and portfolio width** accordingly—without ever granting truth authority or weakening verification required by policy.

### Current release contracts

```text
aasm.adoption.v1 / 0.23.0
aasm.remote.v1 / 0.19.0
aasm.certification.v1 / 0.2.0
aasm.sii.v1 / 0.3.0
aasm.optimization.advanced.v1 / 0.1.0
aasm.optimization.v1 / 0.1.0
aasm.optimization.convex.v1 / 0.1.0
aasm.adapter.pulp.v1 / 0.1.0
aasm.reference-domains.v1 / 0.1.0
aasm.reuse.v1 / 0.1.0
aasm.reuse.certificate.v1 / 0.1.0
aasm.solver.loop.v1 / 0.1.0
aasm.memory.hierarchical.v1 / 0.1.0
aasm.capability.abi.v1 / 0.1.0
aasm.formal.verification.v1 / 0.1.0
```

## The architecture

```text
                         human / model / solver
                                  |
                                  v
                        StructuredProposal
                                  |
                    +-------------+-------------+
                    |                           |
                    v                           v
            reasoning / Evidence         semantic problem state
                    |                           |
                    v                           v
            measured outcomes              solver portfolio
                    |                           |
                    v                           v
             PerformanceVector       Kissat / CaDiCaL / CP-SAT
                    |                HiGHS / CVXPY / Z3 / cvc5
                    v                Vampire / Lean 4
          versioned SIIScoringPolicy            |
                    |                           v
                    v                   normalized Evidence
          GovernedResourceLease                 |
                    |                           v
       +------------+-----------+       validation / admission
       |            |           |               |
       v            v           v               v
    context      scheduler   native budgets   durable truth
   projection     priority   / portfolio     only by AASM
```

The important boundary is simple:

> **AASM decides what is legal, verified, authoritative, stale, reusable, or true. SII decides which intelligence is worth spending more computation on next.**

## Governed SII — v0.47

The original SII preview established three laws:

1. **The reasoner proposes; AASM measures.**
2. **Utility may buy resources; utility never buys truth.**
3. **SII returns compressed, governed intelligence — not merely a score.**

v0.47 makes those laws executable.

### Durable principal binding

SII participants are now bound through `SIIPrincipalBinding` records admitted by existing `POLICY` or `CONTROLLER` authority.

Bindings state:

- stable `principal_id`;
- authority class;
- whether the principal may propose;
- whether the principal may measure outcomes;
- active/inactive state.

A stable principal cannot silently reset itself into a new verifier/controller identity. Measurement authority is resolved from durable AASM state; the measurement caller does **not** supply an authority class.

A principal also cannot measure its own proposal even if that principal legitimately has a verifier role.

### Versioned scoring policy

The active resource economics are now explicit policy data rather than hidden thresholds.

`SIIScoringPolicy` scores the existing measured performance dimensions:

- reliability;
- calibration;
- verified utility;
- reuse contribution;
- compute efficiency;
- conflict-learning value;
- artifact durability.

The default v0.47 policy is `1.0.0` and retains separate default/exploration/exploitation/formal weight profiles.

### Real ResourceLease enforcement

A `GovernedResourceLease` can allocate:

- context tokens;
- outstanding discretionary candidate count;
- scheduler priority;
- native solver timeout;
- SAT conflict budget;
- SAT decision budget;
- CP-SAT deterministic time;
- CP-SAT search workers;
- MILP node budget;
- convex solve time;
- discretionary formal verification time;
- solver portfolio width;
- model-call budget metadata for future first-class model workers.

Tier-1 requests are intentionally bounded; higher verified utility and sufficient sample history unlock larger budgets.

Crucially, the lease is fixed to:

```text
authority_class        = PROPOSER
direct_truth_promotion = false
direct_state_mutation  = false
self_verification      = false
authority_reward       = NEVER
```

### Required verification is never reduced

SII's formal-verification path is explicitly **discretionary**.

Policy-required verification continues on the ordinary formal path. A low SII score cannot:

- remove a required verifier;
- lower required proof strength;
- shrink a required independent-result quorum;
- bypass reasoning-artifact verification;
- promote solver output directly into truth.

The design is intentionally asymmetric:

> **SII may spend more compute on useful intelligence. It may not spend less correctness than AASM policy requires.**

## Native solver portfolio

v0.47 preserves every released direct and advanced solver path.

```text
                              AASM
                               |
                    canonical problem identities
                               |
       +---------+--------------+------------+--------------+---------+
       v         v              v            v              v         v
      SAT     CP-SAT           MILP        CONVEX         SMT/FOL    PROOF
       |         |              |            |              |         |
 Kissat /     OR-Tools       HiGHS         CVXPY       Z3 / cvc5   Lean 4
 CaDiCaL      scheduling    warm starts    QP / SOC       Vampire
       |         |              |            |              |         |
       +---------+--------------+------------+--------------+---------+
                               |
                      normalized Evidence
                               |
                 validation / certification / reuse
```

### Fast SAT — Kissat

`solver.sat.fast@0.1.0` uses PySAT's dedicated `Kissat404` binding for non-incremental high-performance Boolean solving. AASM owns clauses, provider admission, TaskLease, result identity, Evidence, and reuse boundaries.

### Incremental SAT — CaDiCaL

`solver.sat.incremental@0.1.0` supports assumptions, UNSAT cores, conflict/decision budgets, and bounded in-process solver-session reuse.

Learned state is explicitly:

```text
EPHEMERAL_PERFORMANCE_ONLY
```

Deleting it changes speed, not truth.

v0.47 can now clamp conflict and decision budgets directly from a governed SII ResourceLease before the advanced problem is durably admitted and fingerprinted.

### CP-SAT scheduling — OR-Tools

`solver.cp_sat.scheduling@0.1.0` supports fixed/optional intervals, `NO_OVERLAP`, `CUMULATIVE`, deterministic-time budgets, worker counts, conflicts/branches, and time telemetry.

v0.47 can cap deterministic time and worker count from SII resource policy.

### MILP — HiGHS

`solver.milp.advanced@0.1.0` supports warm starts, MIP gap targets, node limits, primal/dual bounds, gap, node count, and simplex-iteration telemetry.

v0.47 can enforce an SII MIP-node budget. Warm starts remain performance hints only.

### Convex optimization — CVXPY

`solver.convex.advanced@0.1.0` supports factorized PSD/NSD quadratic objectives, real cross terms through weighted squared linear forms, and affine SOC constraints:

```text
||A x + b||2 <= c^T x + d
```

AASM independently rechecks canonical feasibility and objective value before result Evidence is admitted.

### PuLP — compatibility, not authority

PuLP remains `TRANSLATION_ONLY` with `solver_execution = NEVER`. Supported PuLP models are translated into AASM IR and then executed by native providers such as HiGHS.

## Formal verification portfolio

The v0.39 formal pathway remains active:

- **Z3** — SMT-LIB2;
- **cvc5** — SMT-LIB2;
- **Vampire** — TPTP first-order theorem proving;
- **Lean 4** — trusted proof-kernel checking.

Formal output is Evidence. It does not skip epistemic admission merely because a backend says “proved.”

## One scheduler, one authority path

Neither optimization nor SII creates a parallel execution authority.

```text
canonical work
      |
CapabilityContract
      |
POLICY / CONTROLLER provider admission
      |
ResourceRecord
      |
WorkerRecord
      |
TaskDemand
      |
TaskLease
      |
execution
      |
AASM validation
      |
Evidence
      |
optional policy-gated reuse / epistemic admission
```

A governed SII request only modifies fields already consumed by that path—priority, timeout, native search limits, context projection limits, and task metadata.

## Reuse

AASM reuse is not an opaque truth cache.

```text
prior Evidence / reasoning / memory
       |
POLICY / CONTROLLER candidate admission
       |
ReuseRequest + applicability validation
       |
ReuseCertificate
       |
solver-loop SKIP_EXECUTION
```

Scope, privacy, environment, dependencies, freshness, effect safety, and verification strength remain explicit checks. Deleting a hot index or solver session changes performance only.

## Certification

v0.47 advances the certification contract to:

```text
aasm.certification.v1 / 0.2.0
```

The default certification set now includes governed SII. The historical target name remains valid:

```bash
aasm certify --target sii-preview
```

In v0.47 it aliases the governed graduation fixture and is expected to return `PASS`, not the v0.43 expected `INCONCLUSIVE`.

The governed fixture checks:

- durable principal/measurement authority binding;
- versioned active scoring policy;
- rejection of unbound measurement actors;
- no authority reward;
- native SAT budget enforcement;
- scheduler priority/provenance enforcement;
- required-verification non-reduction;
- exact event-sourced replay.

## Installation

Base runtime:

```bash
pip install aasm-runtime
```

Full native optimization/modeling portfolio:

```bash
pip install 'aasm-runtime[optimization]'
```

CVXPY + PuLP modeling surfaces only:

```bash
pip install 'aasm-runtime[modeling]'
```

## Governed SII example

```python
from aasm import AASMEngine, ProblemSpec, SIIPrincipalBinding
from aasm.sii import StructuredProposal

engine = AASMEngine(ProblemSpec("governed intelligence"))

engine.install_default_sii_scoring_policy(
    authority_id="policy",
    authority_class="POLICY",
)
engine.bind_sii_principal(
    SIIPrincipalBinding("reasoner", "PROPOSER", can_propose=True),
    authority_id="policy",
    authority_class="POLICY",
)
engine.bind_sii_principal(
    SIIPrincipalBinding("meter", "VERIFIER", can_measure=True),
    authority_id="policy",
    authority_class="POLICY",
)

identity = engine.register_sii_proposer(
    principal_id="reasoner",
    name="reasoner",
    kind="llm",
)
proposer_id = identity["identity"]["proposer_id"]

proposal = StructuredProposal(
    proposer_id=proposer_id,
    decision_name="candidate",
    scope_id="root",
    chosen={"strategy": "reuse-first"},
    confidence=0.72,
)
engine.submit_sii_proposal(proposal)
feedback = engine.measure_sii_outcome(
    proposal.proposal_id,
    measured_by_principal_id="meter",
    disposition="INCONCLUSIVE",
    verification_verdict="INCONCLUSIVE",
)

assert feedback["resource_lease"]["authority_class"] == "PROPOSER"
assert feedback["resource_lease"]["direct_truth_promotion"] is False
```

## SII-governed solver request

```python
from aasm.advanced_optimization import default_advanced_providers, reference_advanced_problems

engine.install_default_advanced_optimization_capabilities(
    authority_id="policy",
    authority_class="POLICY",
)
for provider in default_advanced_providers():
    engine.register_advanced_optimization_provider_runtime(
        provider,
        authority_id="policy",
        authority_class="POLICY",
    )

problem = reference_advanced_problems()["INCREMENTAL_SAT"]
request = engine.request_sii_advanced_optimization(proposer_id, problem)

# The effective canonical problem/request now contains the SII-enforced native
# conflict/decision/time limits, and the ordinary TaskDemand carries the SII
# lease/policy/enforcement provenance.
print(request["resource_lease"])
```

## CLI

```bash
# v0.47 governed SII
aasm sii-contract
aasm sii-governance-contract
aasm sii-default-scoring-policy
aasm certification-contract
aasm certify
aasm certify --target sii-preview

# v0.46 advanced solver control
aasm advanced-optimization-contract
aasm advanced-optimization-blueprint
aasm advanced-optimization-conformance --real

# v0.45 modeling surfaces
aasm convex-optimization-contract
aasm pulp-adapter-contract
aasm modeling-conformance --real

# v0.44 native portfolio
aasm optimization-contract
aasm optimization-blueprint
aasm optimization-conformance --real
```

## Verification

The repository validates the runtime in several independent ways:

- Python 3.11 / 3.12 / 3.13 test matrices;
- deterministic replay;
- SQLite and PostgreSQL persistence;
- Compose full-stack smoke testing;
- wheel/sdist reproducibility and clean-install smoke tests;
- LangGraph and framework-neutral adapter conformance;
- native Optimization Backends workflow;
- bounded TLA+ and Promela/SPIN formal models;
- release/source contract gates;
- semantic/adversarial certification.

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
- v0.46 Advanced Solver Control & Search Artifacts ✅
- **v0.47 Governed Symbiotic Intelligence & Intelligence Economics — current ✅**
- **v0.48 next — Cross-Run Certified Knowledge & Governed Long-Term Memory**
- v0.49 Semantic Solver Release Candidate

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/SII_GOVERNED_ECONOMICS.md](docs/SII_GOVERNED_ECONOMICS.md), [docs/ADVANCED_SOLVER_CONTROL.md](docs/ADVANCED_SOLVER_CONTROL.md), and [docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md](docs/HETEROGENEOUS_SOLVER_PORTFOLIO.md).
