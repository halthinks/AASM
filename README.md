# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, formal systems, native solvers, engineering workflows, governed memory, external authoritative state machines, and cross-run knowledge.**

## Current release — v0.56.0

**Truthful Solver Outcomes + Governed Semantic Evolution + Engineering Mathematical IR**

**Next release / cumulative release:** v0.56.1 — Execution Profiles + Runtime Provenance + Governed External Reality + Physical Authority + S3 Artifact/Entity Lineage + S4 Engineering Quantity + Rule

**Current development package on `main`:** `0.56.1`
**Current active adoption contract on `main`:** `aasm.adoption.v1 / 0.32.20`
**Qualified development boundary:** PR-1 + PR-2 + complete PR-3 / PHY-01 + complete S3 + active S4 public lineage through Degraded Operation 0.32.20, with Risk/Irreversibility, Obligation Phases, Safety Envelope/Hybrid State, and Epistemic Debt/Manual Override gated pre-admission foundations
**Next unfinished boundary:** S4.10 — permanent TextPCB safety/engineering fixtures and aggregate safety-governance qualification
**Latest fully qualified pre-documentation implementation head:** `7c808fc504fa91edb8fe9af13f12568b745f9762`

AASM is an event-sourced control plane for work that must survive retries, crashes, competing agents, changing evidence, external solvers, long-lived memory, external engineering tools, physical/external state machines, and prior-run knowledge **without allowing any of those inputs to silently become authority or truth**.

The latest immutable published release remains **v0.56.0**. Development on `main` has advanced materially beyond that published boundary without pretending the development target is already released. The active `0.56.1` candidate now combines execution provenance, explicit state/fact authority, external-machine supervision, postcondition verification, complete physical-effect authority integration, observation epistemics, backend-independent artifact revision lineage, governed entity evolution with ambiguity-safe reuse fencing, exact portable engineering Quantity semantics, and explicit portable engineering Rule applicability/precedence semantics.

The governing rule remains:

> **Information may move through AASM. Authority does not hitchhike with it.**

Reasoning, memory, solver output, sensor agreement, simulation, external-tool state, and prior-run knowledge can support governed decisions. None of them acquire authority merely because they were transported, repeated, cached, aggregated, translated, or executed.

AASM's declared project license is **Apache License, Version 2.0 (`Apache-2.0`) across the project**. Previously granted MIT permissions remain valid for their recipients. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), and [`LICENSE_POLICY.md`](LICENSE_POLICY.md).

## Current release and development contracts

```text
latest published package / public surface: 0.56.0
released adoption contract:                 aasm.adoption.v1 / 0.32.0

current development package on main:        0.56.1
active development adoption contract:       aasm.adoption.v1 / 0.32.20

v0.56 truthful solver evidence:
  aasm.solver.outcome.v2
  aasm.solver.status.v2
  aasm.solver.termination.v2
  aasm.solver.evidence-grade.v1
  aasm.solver.status-v1-projection.v1
  aasm.solver.provider-status-map.v1
  aasm.solver.outcome-v2.runtime.v1

v0.56.1 execution provenance:
  aasm.solver.execution-profile.v1
  aasm.solver.runtime-provenance.v1
  aasm.solver.profile-evaluation.v1
  aasm.solver.runtime-provenance.runtime.v1

PR-1 governed state authority:
  aasm.fact.authority.v1
  aasm.state.claim.v1
  aasm.state.authority.runtime.v1

PR-2 governed external reality:
  aasm.machine.binding.v1
  aasm.machine.state-observation.v1
  aasm.machine.external.runtime.v1
  aasm.machine.transition.v1
  aasm.machine.transition.runtime.v1
  aasm.machine.postcondition-verification.v1
  aasm.machine.postcondition-verification.runtime.v1

PR-3A/3B physical authority:
  aasm.authority.domain.v1
  aasm.authority.lease.v1
  aasm.physical.authority.runtime.v1

PR-3C/3D bounded effect capability:
  aasm.effect.capability.v1
  aasm.effect.capability.runtime.v1

PR-3E/3F stale-command fencing:
  aasm.effect.capability-use.v1

PR-3G semantic preemption:
  aasm.authority.preemption.v1
  aasm.physical.control-fencing.runtime.v1
  crash-safe preemption recovery over canonical AuthorityLease revocation

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

parent v0.54 execution/solver contracts remain authoritative:
  aasm.effect.intent.v1
  aasm.effect.dispatch-request.v1
  aasm.effect.ownership.v1
  aasm.effect.reconciliation.v1
  aasm.effect.resource-settlement.v1
  aasm.solver.translation.v1
  aasm.solver.portfolio.v1
  aasm.solver.exchange.v1

PR-3H physical-effect integration:
  GATED
  reuses existing authorize_effect / execute_effect
  rechecks capability/lease/epoch/revocation/bounds at effect boundaries
  creates no second authority evaluator, dispatcher, ownership model, or effect lifecycle

S3 artifact + entity lineage:
  aasm.artifact.revision.v1
  aasm.artifact-lineage.runtime.v1
  aasm.entity.evolution.v1
  aasm.entity-evolution.runtime.v1
  artifact existence/generation != authoritative acceptance
  AMBIGUOUS entity mapping blocks hard automatic reuse

S4 engineering quantity semantics:
  aasm.quantity.v1
  exact integer / rational / canonical decimal / interval / measured values
  explicit dimensions and exact affine source->canonical unit transforms
  explicit tolerance / quantization / rounding / source precision / uncertainty / provenance
  public semantic admission = QUALIFIED
  runtime engine-state admission = PRE_ADMISSION_ONLY
  hidden unit registry = NONE
  legacy aasm.numeric.tolerance.v1 = UNCHANGED
  legacy EffectCapability NumericInterval = UNCHANGED

S4 engineering Rule semantics:
  aasm.rule.v1
  stable rule/clause/source-authority/external-reference identity
  explicit scope / subject / problem-revision / external-revision applicability
  portable APPLICABLE / NOT_APPLICABLE / INDETERMINATE evaluation
  HARD_FLOOR / HARD / POLICY / PREFERENCE / ADVISORY strength
  explicit precedence / specificity / priority / waiver / override structural policy
  public semantic admission = QUALIFIED
  runtime engine-state admission = PRE_ADMISSION_ONLY
  parallel rule registry / constraint engine / authority evaluator = NONE
  implicit Rule -> LearnedConstraint lowering = NONE

license: Apache-2.0
```

## Why AASM exists

The failure mode AASM targets is architectural: useful reasoning, solver output, memory, cached results, model confidence, external-tool state, sensor output, or prior-run success gets mistaken for authority.

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

AASM's deeper direction is a governed reasoning and supervisory-control kernel over external authoritative state machines, typed engineering artifacts, heterogeneous solvers, verification/refinement loops, and reusable cross-run knowledge. This extends the original deterministic agent-state-machine purpose; it does not replace it.

## v0.56.1 development — Governed external reality, physical control, and engineering semantics

### PR-1 — desired, predicted, observed, and authoritative state are different

The active development runtime distinguishes:

```text
DESIRED       requested/target state
PREDICTED     model/simulation expectation
OBSERVED      empirical/source observation
AUTHORITATIVE explicitly admitted fact under matching FactAuthority
```

Observation existence is not authority. Observation agreement is not authority. `FactAuthority` does not create effect authority. State claims do not directly mutate core machine state.

### PR-2 — supervise external machines without copying their truth

AASM now has a governed external-machine path that preserves the existing Effect plane:

```text
AUTHORITATIVE pre-state + DESIRED target
        |
        v
MachineTransitionIntent
        |
        v
existing propose_effect() / EffectIntent
        |
        v
existing authorize_effect()
        |
        v
existing TaskLease + execute_effect()
        |
        +-- durable dispatch request
        +-- durable ownership Evidence
        +-- SUCCEEDED / FAILED / UNKNOWN / CANCELLED
        |
        v
if UNKNOWN -> existing Effect reconciliation
        |
        v
correlated post-effect OBSERVED state
        |
        v
independent AUTHORITATIVE admission
        |
        v
VERIFIED | MISMATCH
```

The central invariant is explicit:

> **Command success is not achieved state.**

`EffectStatus.SUCCEEDED` proves the existing Effect lifecycle reached its success state. It does not prove that physical or external reality now matches the desired state. Postcondition verification requires separately governed correlated observation and independently admitted authoritative state.

### PR-3A/3B — authority domains and exclusive authority leases

`AuthorityDomain` names a bounded physical/effect authority namespace without granting authority by existence.

`AuthorityLease` adds:

- explicit holder and issuer;
- workspace/scope/domain identity;
- explicit permitted effect classes;
- validity interval;
- strict monotonic authority epoch;
- revision binding;
- append-only revocation generation;
- at-most-one-active-lease semantics for a domain.

A lease still does **not** grant existing `effect.authorize` by existence.

### PR-3C/3D — bounded effect capabilities

`EffectCapability` is derived from an active authority lease and can only preserve or narrow authority.

It binds:

- holder and issuer;
- exact domain and lease identity;
- exact authority epoch;
- workspace/scope/subject;
- problem/external revision;
- allowed operation set;
- named closed numeric bounds;
- validity interval;
- delegation depth;
- parent capability fingerprint/generation where delegated.

Delegation must fail closed on amplification:

```text
child operations        ⊆ parent operations
child bounds            ⊆ parent bounds
child validity          ⊆ parent validity
child scope/revision    = parent scope/revision
child authority epoch   = parent authority epoch
child delegation depth  < parent delegation depth
```

Capability existence still does not automatically grant Effect authorization.

### PR-3E/3F — stale-command fencing

Capability use is revalidated against current durable authority state. A previously valid use cannot be replayed as a reusable authorization token after revocation, preemption, epoch advancement, holder change, capability mismatch, scope/revision mismatch, or bound violation.

The current capability-use object is intentionally a **point-in-time stale-command fence**, not a second Effect authorization system.

### PR-3G — semantic preemption with crash recovery

A listed preemptor identity alone is not enough. Preemption requires both:

```text
authority-domain preemptor identity
        +
existing scoped physical.authority.preempt permission
```

Successful preemption:

1. durably records preemption Evidence;
2. uses the canonical existing `AuthorityLease` revocation representation;
3. invalidates capabilities tied to the preempted lease/epoch;
4. requires the next lease epoch to advance monotonically;
5. never rewrites prior Effect history;
6. never grants the preemptor new Effect authority merely because preemption occurred.

A crash between durable preemption Evidence and canonical lease-revocation Evidence is repaired deterministically on retry.

### PR-3H — implemented and gated

PR-3H now connects the qualified authority-domain/lease/capability/fencing semantics to the **existing** Effect authorization and execution boundaries. Both boundaries recheck live lease identity/fingerprint/epoch, capability identity/fingerprint, effective revocation generation, holder, operation/bounds, workspace/scope/subject, and applicable problem/external revision. Earlier capability-use Evidence is never a reusable bearer token.

The inherited `effect.authorize`, resources/Worker/TaskLease, Effect ownership, dispatch, `UNKNOWN`, and reconciliation paths remain authoritative; no parallel authority evaluator, scheduler, dispatcher, Effect store, ownership primitive, or reconciliation path was introduced.

### S3 — artifact revision lineage + entity evolution

Artifact revisions now have backend-independent immutable identity over content/semantic hashes and exact provenance, exact parent ID+fingerprint lineage, and a separate storage-binding fingerprint for non-semantic `artifact_ref` locators. Registration/replay uses existing Evidence and does not imply artifact acceptance or create a current-artifact truth pointer.

Entity evolution now records `UNCHANGED | MODIFIED | GENERATED | SPLIT | MERGED | REPLACED | DELETED | AMBIGUOUS` relationships over exact artifact-revision-bound representations. `AMBIGUOUS` mappings remain durable and block hard automatic reuse. There is no hidden current-entity state table and no authority minting.

### S4 — exact engineering quantity/unit/tolerance semantic IR

`aasm.quantity.v1` is a qualified public semantic contract. It represents exact integer, rational, canonical-decimal, interval, and measured/estimated engineering values; canonical dimensions; exact affine source-unit→canonical-unit transforms; absolute/relative/asymmetric tolerance; quantization/grid and rounding; source precision; uncertainty reference; provenance; canonical projection; and deterministic fingerprints.

Binary floating point cannot enter durable Quantity identity. Dimensional inconsistency fails closed before solving or verification. There is no hidden mutable unit registry.

Public admission is deliberately narrower than runtime integration:

```text
Quantity public semantic IR       = QUALIFIED
Quantity runtime engine state     = NOT ADMITTED / PRE_ADMISSION_ONLY
Quantity grants FactAuthority     = NO
Quantity grants EffectAuthority   = NO
solver numeric tolerance rewrite  = NO
EffectCapability bound rewrite    = NO
```

The existing solver `aasm.numeric.tolerance.v1` contract and `EffectCapability.NumericInterval` remain unchanged. Later use of Quantity in postconditions, physical capability bounds, solver/provider tolerance, or other runtime semantics requires explicit translation/admission contracts and qualification.

### S4 — engineering Rule applicability/precedence semantic IR

`aasm.rule.v1` is a qualified public semantic contract. It represents stable rule revision identity, exact clause and source-authority references, external references, explicit workspace/scope/subject applicability, exact problem/external revision applicability, portable tri-state context evaluation, `HARD_FLOOR | HARD | POLICY | PREFERENCE | ADVISORY` strength, precedence group, specificity, priority, severity, and explicit waiver/override structural policy.

The Rule claim ceiling is deliberately narrow:

```text
Rule public semantic IR          = QUALIFIED
Rule runtime engine state        = NOT ADMITTED / PRE_ADMISSION_ONLY
current Rule registry            = NONE
parallel constraint engine       = NONE
parallel authority evaluator     = NONE
Rule existence grants authority  = NO
precedence authorizes override   = NO
implicit Rule -> LearnedConstraint lowering = NONE
```

`HARD_FLOOR` cannot be waived or overridden by the Rule model. Waiver/override helpers establish structural eligibility only; any future runtime action still requires explicit authorization through the existing scoped-authority system.

Rule strength does **not** redefine the formal-calculus `LearnedConstraint(HARD|SOFT)` vocabulary or the decision-vector hard-floor substrate. Source engineering rules and learned constraints are distinct semantic objects unless an explicit versioned checked lowering is later admitted.

### S4.3 — semantic projection/equivalence is next

The next seam is one explicit generic projection/equivalence contract used across solution pools/top-K/diversity, cache/reuse, cross-provider comparison, artifact comparison, and TextPCB alternative design identity.

The key rule is:

> **No implicit “same enough.” Equivalence is always relative to an explicit declared projection.**

The contract must keep exact identity, equivalence-under-projection, non-equivalence, indeterminate/unsupported comparison, and declared lossy projection distinct. A projection must declare what it preserves and what it drops; semantic loss cannot silently become exact equivalence. Projection/equivalence itself grants no truth, authority, acceptance, proof, identity transfer, or objective preference.

This seam will also pull `aasm.invariant.v1` classification pressure into active S4 design so representational/static equivalence cannot pretend to prove dynamic or empirical facts before the later portable Rust kernel exists.

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

## Current claim ceilings

AASM is explicit about what the published release and current development surface do not prove:

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

observation agreement
  != fact authority

AuthorityDomain existence
  != effect authority

AuthorityLease existence
  != effect authority

EffectCapability existence
  != effect authority

point-in-time capability-use validation
  != reusable effect authorization

semantic preemption
  != new effect authority

EffectStatus.SUCCEEDED
  != achieved physical/external state

PR-3H effect-boundary integration
  = GATED THROUGH EXISTING EFFECT LIFECYCLE

Quantity public semantic admission
  = QUALIFIED

Quantity runtime engine-state admission
  = PRE_ADMISSION_ONLY

Quantity
  != fact authority / effect authority / hidden unit registry

Quantity integration into EffectCapability/postconditions/solver tolerance
  = NOT YET ADMITTED; EXPLICIT TRANSLATION CONTRACT REQUIRED

Rule public semantic admission
  = QUALIFIED

Rule runtime engine-state admission
  = PRE_ADMISSION_ONLY

Rule existence / precedence / waiver eligibility
  != fact authority / effect authority / source authority / override authorization

Rule -> LearnedConstraint lowering
  = NONE

Generic semantic projection/equivalence
  = NOT YET ADMITTED; NO IMPLICIT SAME-ENOUGH SEMANTICS
```

## Core architecture

```text
                                     AASM
                                      |
                           canonical durable state
                                      |
      +-----------+-----------+-------+--------+--------------+
      |           |           |       |        |              |
      v           v           v       v        v              v
  reasoning     memory      solvers  effects  authority   external machines
      |           |           |       |        |              |
      +-----------+-----------+-------+--------+--------------+
                                      |
                                Evidence/events
                                      |
                         deterministic reducer + policy
                                      |
                      verification / reconciliation / refinement
```

Three persistent graphs remain central:

- **Decision graph** — what was chosen, rejected, superseded, or backjumped and why;
- **Obligation graph** — what remains mandatory, enabled, locked, satisfied, or invalidated;
- **Evidence graph** — what observations, certificates, solver results, and receipts support each conclusion.

AASM's AVATAR/CDCL-inspired architecture uses conditional activation, durable conflict learning, non-chronological recovery, restart without forgetting learned knowledge, and fairness controls without turning the runtime into a theorem prover.

## Engineering / TextPCB direction

AASM continues to shape a domain-neutral supervisory kernel for demanding external engineering state machines without baking PCB or CAD types into the kernel.

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
exact engineering Quantity semantic IR
        ↓
explicit engineering Rule semantic IR
        ↓
truthful solver outcome
        ↓
external machine binding + authoritative-state claims
        ↓
governed Effect proposal / ownership / dispatch
        ↓
correlated observation + postcondition verification
        ↓
revision-safe re-evaluation / refinement
```

The kernel remains domain neutral. PCB/CAD/CAE-specific semantics belong in adapters and conformance packages. TextPCB is a demanding consumer and qualification target, not kernel logic.

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

Inspect the active development adoption contract on `main`:

```python
import aasm

report = aasm.validate_public_api_contract()
assert report["valid"]
assert aasm.__version__ == "0.56.1"
assert aasm.public_api_contract()["contract_version"] == "0.32.17"
```

If you need the immutable published package contract rather than the development branch, use the `v0.56.0` release/tag.

## Verification

AASM uses independent, exact-head gates rather than treating documentation as evidence of implementation.

The implementation head `7c808fc504fa91edb8fe9af13f12568b745f9762` qualified the active `0.56.1 / 0.32.17` candidate across **29 current custom commit-status contexts**:

```text
aasm/ci-summary                         PASS
aasm/formal-assurance                   PASS
aasm/semantic-solver-rc                 PASS
aasm/proof-claims                       PASS
aasm/solution-pools                     PASS
aasm/optimization                       PASS
aasm/scoped-authority                   PASS
aasm/solver-learning                    PASS
aasm/v54                                PASS
aasm/v55                                PASS
aasm/v56                                PASS
aasm/v56-provenance                     PASS
aasm/state-authority                    PASS
aasm/external-machine                   PASS
aasm/machine-transition                 PASS
aasm/machine-postcondition              PASS
aasm/physical-authority                 PASS
aasm/effect-capability                  PASS
aasm/physical-control-fencing           PASS
aasm/physical-preemption-recovery       PASS
aasm/physical-effect-integration        PASS
aasm/identity-calibration-trust         PASS
aasm/execution-environment              PASS
aasm/observation-epistemics             PASS
aasm/artifact-lineage                   PASS
aasm/entity-evolution                   PASS
aasm/engineering-quantity               PASS
aasm/engineering-rule                   PASS
aasm/physical-evidence                  PASS
```

The cumulative v0.56 gate on that head passed:

- Solver Outcome v2 contracts and terminal-class fixtures;
- real CaDiCaL / OR-Tools / HiGHS status identity;
- execution-profile/runtime-provenance fixtures;
- PR-1 state authority;
- PR-2 external-machine binding, transition, observation correlation, and postcondition verification;
- PR-3A/3B authority domains and exclusive/revocable leases;
- PR-3C/3D bounded effect capabilities and non-amplifying delegation;
- PR-3E/3F stale-command fencing;
- PR-3G semantic preemption and canonical lease revocation;
- crash recovery between durable preemption Evidence and lease-revocation Evidence;
- PR-3H physical-effect authority rechecks at existing Effect authorization/execution boundaries;
- S3 identity/calibration/trust, execution-environment, observation-epistemics, artifact lineage, and entity evolution;
- S4 `aasm.quantity.v1` source/public firewalls and adversarial/public corpora;
- S4 `aasm.rule.v1` source/public firewalls and adversarial/public corpora, including learned-constraint separation and no Rule runtime/authority plane;
- cumulative source/release contracts;
- active adoption contract `0.32.17` and no-authority/no-runtime-Quantity-or-Rule-state guard.

The main CI matrix on the same head passed Python **3.11, 3.12, and 3.13**, reproducible development-wheel smoke, PostgreSQL integration, Compose full-stack smoke, hierarchical scopes, LangGraph integration, and adapter conformance. The formal gate passed the architecture/release-contract validator plus every bounded TLA+ and Promela/SPIN model.

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
v0.56.1 development  execution provenance + governed external reality + complete PR-3 + complete S3 + S4 Quantity + Rule semantic foundations
```

Historical release documentation remains under `docs/RELEASE_*.md` and the architecture/roadmap documents.

## Documentation

Start with:

- [`docs/CURRENT_RELEASE.md`](docs/CURRENT_RELEASE.md) — immutable published v0.56.0 boundary plus current `main` development state;
- [`docs/RELEASE_0.56.1.md`](docs/RELEASE_0.56.1.md) — active 0.56.1 development candidate and claim ceilings;
- [`docs/RELEASE_0.56.md`](docs/RELEASE_0.56.md) — v0.56 release summary;
- [`docs/RELEASE_0.55.md`](docs/RELEASE_0.55.md) — parent v0.55 release summary;
- [`docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`](docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md) — semantic-evolution architecture;
- [`docs/architecture/GOVERNED_PHYSICAL_DISTRIBUTED_REALITY_RECONCILIATION.md`](docs/architecture/GOVERNED_PHYSICAL_DISTRIBUTED_REALITY_RECONCILIATION.md) — physical/distributed architecture reconciliation;
- [`docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md`](docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md) — canonical execution ledger;
- [`docs/implementation/GOVERNED_PHYSICAL_REALITY_INTEGRATION_PLAN.md`](docs/implementation/GOVERNED_PHYSICAL_REALITY_INTEGRATION_PLAN.md) — physical-reality integration plan;
- [`docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`](docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md) — implementation sequence;
- [`WHY_AASM.md`](WHY_AASM.md) — project motivation;
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — broader architecture;
- [`docs/FORMAL_CALCULUS.md`](docs/FORMAL_CALCULUS.md) — calculus background;
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution workflow;
- [`SECURITY.md`](SECURITY.md) — security policy.

## Project status

AASM is an experimental `0.x` project. Public contracts are versioned and aggressively tested, but interfaces may still evolve between minor releases. Claims in the README are intended to stay below the evidence available from code, tests, and exact-head qualification gates.

**Current immutable release:** `0.56.0`
**Current development target on `main`:** `0.56.1`
**Released adoption contract:** `aasm.adoption.v1 / 0.32.0`
**Active development adoption contract:** `aasm.adoption.v1 / 0.32.17`
**PR-3 / S3 / S4 status:** `complete PR-3 / PHY-01 GATED; complete S3 GATED; S4 Quantity + Rule GATED/public semantic IR; next S4.3 semantic projection/equivalence`
**License:** Apache-2.0
**Repository:** https://github.com/halthinks/AASM
