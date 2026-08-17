# AASM Governed Semantic Evolution — Unified Engineering and Portable Kernel Roadmap

**Date:** 2026-08-17  
**Repository:** `halthinks/AASM`  
**Latest immutable release:** `v0.56.0`  
**Current development package:** `0.56.1`  
**Current adoption contract:** `aasm.adoption.v1 / 0.32.16`  
**Current exact qualified code boundary before documentation-only synchronization:** `263640a634da0e92bb1ae0b42cb55063e0b64552` — all 28 current custom qualification contexts green  
**Status:** single canonical execution roadmap for governed semantic evolution, TextPCB compatibility, physical/distributed control, portable machine semantics, Rust `std`, and Rust `no_std`

Companion architecture:

- `docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`
- `docs/architecture/GOVERNED_PHYSICAL_DISTRIBUTED_REALITY_RECONCILIATION.md`
- `docs/implementation/GOVERNED_PHYSICAL_REALITY_INTEGRATION_PLAN.md`
- `docs/implementation/GOVERNED_SEMANTIC_EVOLUTION_EXECUTION_LEDGER.md`
- `docs/VERSIONING.md`

---

# 1. Mission

Build AASM into a public deterministic governance and supervisory-control substrate that can coordinate:

- nondeterministic intelligence and human proposals;
- semantic problems and problem revisions;
- heterogeneous mathematical solvers;
- formal and empirical verifiers;
- external authoritative state machines;
- engineering artifacts and entity evolution;
- governed resources and scarce intelligence;
- physical effect authority and recovery;
- experiments and refinement loops;
- applicability-scoped reusable knowledge;
- a portable deterministic machine/kernel subset;
- Python, Rust `std`, and constrained Rust `no_std` implementations of the same portable semantics.

TextPCB is the primary demanding engineering conformance consumer. It is not a kernel subsystem.

The target can be summarized as:

> **AASM is a governed reasoning and supervisory-control kernel over authoritative external state machines, typed engineering artifacts, heterogeneous solvers, and verification/refinement loops, with a portable deterministic subset suitable for independent runtime implementations and embedded execution.**

The roadmap is deliberately product-backward. Known requirements from TextPCB and embedded/Rust research constrain current contracts now. Implementation depth may be staged; architectural compatibility with the destination may not be deferred.

---

# 2. Reconciliation verdict

The two major directions are not competing:

## 2.1 TextPCB/general engineering direction

TextPCB requires AASM to supervise a large authoritative engineering application without becoming a second project truth. It pressures AASM to support:

- stable external requirement/design identity;
- problem revisions and deltas;
- external machine transitions;
- artifact revision lineage;
- entity evolution and ambiguity;
- quantities, units, tolerances and design/manufacturing rules;
- heterogeneous solver/verifier evidence;
- DRC/ERC/SPICE/EM/thermal/mechanical feedback;
- governed refinement;
- uncertainty/scenarios/temporal properties;
- alternative search and equivalence;
- deterministic readiness/completion explanations.

## 2.2 Rust/embedded direction

The Rust/embedded research requires AASM semantics to be sufficiently explicit and portable that a constrained implementation can exist without Python, SQL, an LLM, an OS process model, or hidden host state. It pressures AASM to support:

- explicit static vs dynamic vs empirical invariant classes;
- language-neutral IDs and canonical serialization;
- portable machine IR;
- deterministic transition/reducer semantics;
- explicit authority/capability/effect/resource references;
- causal event identity and timing requirements;
- bounded queues/journals/storage;
- semantic executor traits independent of transport/vendor;
- differential replay across runtimes;
- `no_std` and real-time profiles;
- SIM/SIL/HIL/physical qualification.

## 2.3 Unified architectural consequence

TextPCB drives the richness of the semantic contracts. Rust drives their portability and precision.

Therefore:

- TextPCB fixtures are used continuously to ensure the generic contracts are useful for serious engineering;
- portable representation constraints are applied continuously so those same contracts do not later require a rewrite for Rust;
- broad Rust implementation begins only after the portable kernel subset is frozen enough to be a differential-conformance target;
- neither TextPCB nor Rust gets a parallel truth/authority/effect/revision system.

---

# 3. Permanent execution rules

1. **One canonical truth/admission path.**
2. **One scoped authority system.** New semantic capabilities may reference or refine authority; they do not create a second ACL or permission database.
3. **One resource-governance plane.** Energy, wear, occupancy, quotas, money, compute, storage, workers, solver calls, model quotas and human review use the same generalized resource algebra with type-specific dynamics where needed.
4. **One Effect lifecycle.** External and physical transitions reuse `EffectIntent`, authorization, TaskLease/resource governance, durable ownership, dispatch, `UNKNOWN`, and reconciliation.
5. **One problem-revision system.** Refinement uses `ProblemDelta` / `ProblemRevision`; evaluators cannot self-mutate canonical models.
6. **One knowledge/admission plane.** Cross-run memory, solver learning, reasoning artifacts and learned engineering knowledge remain applicability-scoped and locally validated.
7. **One semantic dependency graph.** Staleness, debt and change impact extend the existing dependency plane rather than creating parallel graphs.
8. **Information cannot hitchhike authority.** Transport, repetition, memory, aggregation, simulation, sensor fusion, solver agreement, replay, translation, or execution does not elevate authority.
9. **Command is not achievement.** Dispatch/ACK/SUCCEEDED does not prove the external physical postcondition.
10. **Resources cannot weaken hard semantics.** Cost/quota/time/provider scarcity changes strategy only.
11. **No silent lowering.** Unsupported semantics fail closed or are explicitly translated/approximated under a declared contract.
12. **Revision-bound applicability.** Old results remain historical Evidence unless explicitly revalidated.
13. **Canonical portable identity.** No durable/public portable identity may depend on Python or Rust runtime accidents.
14. **Rust typestate strengthens, never redefines, machine legality.**
15. **TextPCB remains authoritative for TextPCB project truth.** AASM supervises and reasons about it; it does not mirror/replace it.
16. **No invisible mutable configuration.** Behavior-changing config is identified, revisioned, attributable, authorized and applicable.
17. **Every public capability has a claim ceiling and gate.**
18. **Package SemVer is independent from architecture progress.** Milestones do not reserve package numbers.

---

# 4. Current evidence-backed baseline

Historical/released capabilities remain recorded in the execution ledger and immutable release documents. The current roadmap starts from these real substrates rather than replaying old version-numbered plans.

## 4.1 Released through v0.56.0

The released base includes:

- semantic problem and reasoning artifacts;
- semantic dependency truth maintenance;
- typed capability ABI and provider contracts;
- formal verification workers;
- hierarchical memory/context projection;
- domain-neutral solver loops;
- heterogeneous SAT/CP-SAT/MILP/convex integration;
- proof-carrying solver claims;
- solution pools and finite exact multi-objective semantics;
- generalized resource governance, reservation and settlement;
- scoped identity/authority;
- cross-run knowledge and solver learning;
- certified solver exchange and deterministic portfolios;
- `EffectIntent`, durable ownership, `UNKNOWN` recovery/reconciliation;
- `ExternalReference`, `ProblemRevision`, `ProblemDelta`;
- generalized mathematical IR and portable semantic archive;
- normalized truthful solver outcome semantics.

## 4.2 Gated on active development line

### Execution profiles/runtime provenance

Evidence-grade provider/runtime execution provenance is active and qualified. Provenance alone does not prove reproducibility.

### PR-1 / authoritative state

Active contracts include:

- `aasm.fact.authority.v1`
- `aasm.state.claim.v1`
- `aasm.state.authority.runtime.v1`

State kinds:

`DESIRED | PREDICTED | OBSERVED | AUTHORITATIVE`

Authority is explicit; observation/consensus/transport cannot mint it.

### PR-2 / external-machine supervision

Active contracts include:

- `aasm.machine.binding.v1`
- `aasm.machine.state-observation.v1`
- `aasm.machine.transition.v1`
- `aasm.machine.postcondition-verification.v1`

Transition proposal reuses existing `EffectIntent`; postcondition verification requires execution-correlated observation plus independently authoritative state. `SUCCEEDED != achieved` is gated.

### PR-3 / physical authority and inherited Effect-boundary integration

Active contracts/runtime include:

- `aasm.authority.domain.v1`
- `aasm.authority.lease.v1`
- `aasm.effect.capability.v1`
- `aasm.effect.capability-use.v1`
- `aasm.authority.preemption.v1`
- stale-command fencing;
- non-amplifying delegation;
- monotonic epochs/revocation generations;
- semantic preemption;
- crash-safe recovery when semantic preemption is durable before canonical lease revocation;
- mandatory live authority/capability recheck at the existing `authorize_effect` and `execute_effect` boundaries.

The complete PR-3 / PHY-01 parent is GATED. Existing scoped effect authority, TaskLease/resource governance, durable EffectOwnership, dispatch, `UNKNOWN`, and reconciliation remain authoritative.

### S3 reality-evidence, observation epistemics, artifact lineage and entity evolution

Active and gated contracts/runtime include:

- `aasm.state.conflict.v1`;
- `aasm.event.causality.v1`;
- `aasm.observation.freshness.v1`;
- `aasm.physical.identity.v1`;
- `aasm.calibration.v1`;
- `aasm.source.trust.v1`;
- `aasm.execution.environment.v1`;
- `aasm.execution.environment-binding.v1`;
- `aasm.observation.lifecycle.v1`;
- `aasm.observation.disposition.v1`;
- `aasm.observation.fusion.v1`;
- `aasm.observation.processing.runtime.v1`;
- `aasm.artifact.revision.v1` + `aasm.artifact-lineage.runtime.v1`;
- `aasm.entity.evolution.v1` + `aasm.entity-evolution.runtime.v1`.

Claim ceilings remain strict: conflict/freshness/identity/calibration/trust/environment/processing are Evidence or policy-input layers only; source trust cannot replace `FactAuthority`; record/revoke authority is not trust-evaluation authority; environment level is not a truth/authority rank; neither proximity to hardware, a `TRUSTED` disposition, a `VALIDATED` processing label, fusion agreement, nor declared source independence mints truth or effect authority. Existing machine observations remain the empirical root, artifact/entity lineage remains Evidence-backed, and no parallel observation/artifact/entity/truth table is introduced.

### S4 engineering quantity/unit/tolerance semantic foundation

Qualified public semantic contract:

- `aasm.quantity.v1`

The foundation supports exact integer, rational, canonical decimal, interval, and measured/estimated values with uncertainty reference; canonical integer-exponent dimensions; exact affine source-unit to canonical-unit transforms; explicit absolute/relative/asymmetric tolerance; quantization/grid and rounding; source precision; provenance; canonical projection; deterministic fingerprints; and fail-closed dimensional compatibility.

The public/runtime boundary is explicit:

```text
public semantic admission = QUALIFIED
runtime engine-state admission = PRE_ADMISSION_ONLY
unit registry = NONE_HIDDEN_OR_MUTABLE
FactAuthority = NONE
EffectAuthority = NONE
legacy aasm.numeric.tolerance.v1 = UNCHANGED
legacy EffectCapability NumericInterval = UNCHANGED
```

Exact qualified code boundary before documentation-only synchronization: `263640a634da0e92bb1ae0b42cb55063e0b64552`, adoption `0.32.16`, all 28 current custom qualification contexts green.

---

# 5. Unified dependency graph

```text
RELEASED/GATED BASE
  |
  +-- S0  state/fact authority ----------------------------- DONE
  |
  +-- S1  external-machine supervision/postconditions ------ DONE
  |
  +-- S2  physical authority/capabilities
  |      +-- A-G -------------------------------------------- DONE
  |      +-- H effect-boundary integration ----------------- DONE
  |
  +-- S3  state conflict ------------------------------------ DONE
  |      +-- causality/freshness ---------------------------- DONE
  |      +-- physical identity/calibration/source trust ----- DONE
  |      +-- execution/qualification environment ------------ DONE
  |      +-- observation lifecycle/fusion ------------------- DONE
  |      +-- artifact revision/entity evolution ------------- DONE
  |
  v
S4 ENGINEERING + SAFETY SEMANTICS -------------------------- ACTIVE
  quantity/unit/tolerance semantic foundation -------------- DONE
  rule applicability/precedence ----------------------------- NEXT
  projection/equivalence + uncertainty/scenarios/trace
  degraded operation + risk + irreversibility + obligation phases
  safety/hybrid state + epistemic debt + manual override
  |\
  | +-- TextPCB design/manufacturing/electrical fixtures
  | +-- invariant taxonomy pressure
  v
S5 GOVERNED REFINEMENT
  RefinementProposal + RefinementLoop + Experiment
  VerificationPlan + VerificationDebt
  knowledge applicability/application + conflict/core pipeline
  |\
  | +-- TextPCB DRC/ERC/SPICE/EM/thermal/mechanical feedback
  | +-- refinement references remain portable kernel data
  v
S6 PORTABLE MACHINE/KERNEL CONTRACT
  invariant classes + machine IR + canonical serialization
  timing + portable kernel boundary + generated configuration package
  Python reference interpreter/compiler + differential trace corpus
  |\
  | +-- representative TextPCB supervisory machine compiles to generic IR
  v
S7 RUST STD REFERENCE KERNEL
  deterministic reducer/guards/refs/replay/fingerprints
  Python <-> Rust differential conformance
  v
S8 RUST NO_STD + REAL-TIME PROFILE
  bounded journal/queues/storage
  semantic observer/executor traits
  interrupt/boot-epoch bridge
  transition timing + optional RT backend
  v
S9 QUALIFICATION
  MODEL -> SIMULATION -> SIL -> HIL -> BENCH -> CONTROLLED_PHYSICAL -> OPERATIONAL
  TextPCB conformance + embedded reference machine + readiness
  v
S10 PERMANENT STRESS CORPUS + HOSTED-FOUNDATION REVIEW
```

---

# 6. S2H — Physical Effect Integration

**Status:** GATED.

## 6.1 Purpose

Make the already-qualified authority-domain/lease/effect-capability semantics mandatory at the actual existing effect authorization/execution boundaries for effects that explicitly bind physical/external authority.

This is implemented and qualified. The requirements below remain permanent compatibility requirements, not future work.

## 6.2 Required binding

A physically governed Effect attempt must bind enough identity to re-evaluate at point of use:

- `effect_id` / intent fingerprint;
- authority domain ID;
- authority lease ID + fingerprint;
- holder principal;
- authority epoch;
- effect capability ID + fingerprint;
- effective capability revocation generation;
- exact operation;
- named numeric parameters/bounds;
- workspace/scope/subject;
- problem revision;
- external revision;
- current time/validity context.

## 6.3 Mandatory checks

At **effect authorization**:

1. existing scoped `effect.authorize` path passes;
2. physical authority binding exists where required;
3. current lease matches holder/scope/domain/epoch/revisions and is active;
4. capability matches lease/domain/holder/scope/revisions/epoch;
5. capability is not expired/revoked/stale;
6. operation and numeric parameters are inside bounds.

At **effect execution**:

All physical capability/lease checks are repeated against current state immediately before ownership/dispatch. A previously valid validation record is not authorization.

## 6.4 Forbidden implementation

Do not add:

- second effect dispatcher;
- physical-only EffectRecord;
- physical authorization database;
- reusable bearer token from `EffectCapabilityUse`;
- automatic effect permission from `MachineBinding`, operator capability reference, resource reservation, `FactAuthority`, or successful prior use.

## 6.5 Adversarial tests

- capability valid at proposal but revoked before authorize;
- capability valid at authorize but revoked/preempted before execute;
- stale authority epoch;
- stale lease/capability fingerprint;
- wrong holder;
- operation escape;
- numeric bound escape/missing parameter;
- scope/subject/revision mismatch;
- capability-use Evidence replayed as if reusable authorization;
- ordinary non-physical Effects retain existing compatibility behavior;
- physical Effect uses existing TaskLease/ownership/UNKNOWN/reconciliation unchanged;
- restart/replay does not resurrect old authority.

**Gate:** `aasm/physical-effect-integration` — GATED.

**Exit:** PR-3 / PHY-01 is GATED and remains subject to this inherited gate on every qualifying head.

---

# 7. S3 — Reality Semantics: Time, Identity, Artifact Lineage and Observation Epistemics

S3 combines the missing pieces from the original TextPCB roadmap and the physical/Rust reconciliation because they operate on the same external-reality identity boundary.

## 7.1 State conflict / expectation violation

**Status: GATED.**

A generic conflict object records an authoritative/observed external state that contradicts desired/predicted/expected state without overwriting either history.

Contract: `aasm.state.conflict.v1`.

## 7.2 Causal/temporal identity

**Status: GATED.**

Contract: `aasm.event.causality.v1`.

Represents:

- node/device identity;
- boot epoch;
- monotonic local sequence;
- `CAUSED_BY`;
- `HAPPENS_BEFORE`;
- `CONCURRENT_WITH`;
- `ORDER_UNKNOWN`;
- receipt time vs source time;
- clock quality/uncertainty.

Host wall clock is Evidence/context, not universal truth. Portable integer/time identity is bounded so Python and future Rust implementations cannot diverge through integer-width accidents.

## 7.3 Observation freshness

**Status: GATED.**

Contract: `aasm.observation.freshness.v1`.

Binds observation age, source time quality, maximum acceptable age, exact observation/causal identity, relevant revisions and stale/unknown reason. `FRESH | STALE | UNKNOWN` remain distinct. Receipt-time fallback is explicit and weaker. Freshness neither mints authority nor universally admits Evidence.

PR-2 exact execution correlation remains valid but is no longer the whole temporal story.

## 7.4 Physical identity and calibration

**Status: GATED for the physical identity + calibration + source trust foundation.**

Contracts:

- `aasm.physical.identity.v1`
- `aasm.calibration.v1`
- `aasm.source.trust.v1`

The active foundation binds exact device/component/sensor/actuator/fixture/firmware/assembly/project-instance identity, exact calibration ID/fingerprint/validity/revocation, and exact source-trust policy inputs. Same-context identity divergence fails closed until an explicit problem/external revision changes. Calibration does not rewrite observations. Source trust has no score/voting/latest pointer and cannot replace `FactAuthority` or grant effect authority.

Future lifecycle state richness such as `VALID | DUE | EXPIRED | INVALID | OUT_OF_RANGE | SUPERSEDED` may be added where explicitly evidenced; the current foundation truthfully claims explicit validity interval/revocation semantics and does not overclaim unimplemented calibration-state inference.

Hardware attestation hooks remain reserved without binding the kernel to a TPM/TEE/vendor.

## 7.5 Execution/qualification environment

**Status: GATED.**

Contracts:

- `aasm.execution.environment.v1`
- `aasm.execution.environment-binding.v1`
- `aasm.execution.environment.runtime.v1`

Levels:

`MODEL | SIMULATION | SIL | HIL | BENCH | CONTROLLED_PHYSICAL | OPERATIONAL`

The levels are exact qualification-context labels, not an ordinal truth or authority ranking. Accepted levels use exact set membership. Simulation evidence cannot silently become bench/physical evidence. Environment identity/configuration/revision is explicit and portable, optional identity/calibration/source-trust references are exact, and environment proximity to hardware does not mint FactAuthority, source trust, effect authority, or universal admission.

## 7.6 Observation lifecycle/fusion

**Status: GATED.**

Contracts:

- `aasm.observation.lifecycle.v1`
- `aasm.observation.disposition.v1`
- `aasm.observation.fusion.v1`
- `aasm.observation.processing.runtime.v1`

Lifecycle:

`RAW -> NORMALIZED -> CALIBRATED -> DERIVED -> VALIDATED`, with multi-source fusion represented explicitly and rejected/superseded/stale/disputed outcomes recorded separately.

The existing `MachineStateObservation` remains the empirical root. RAW reproduces its exact portable value. Every later record references exact source IDs/fingerprints. Lifecycle stage progression is checked at runtime; CALIBRATED requires exact active calibration under an explicit time context; fusion requires at least two processed sources and cannot bypass lifecycle with direct raw machine observations. Fusion never votes authority, source independence never grants authority, and `VALIDATED` is only a local processing label—not FactAuthority or universal admission. Dispositions never erase source history, and disposed-source reuse fails closed.

## 7.7 Artifact revision lineage

**Status: GATED under `aasm/artifact-lineage` and inherited by cumulative `aasm/v56`.**

Target: `aasm.artifact.revision.v1`.

Bind:

- stable logical artifact ID;
- immutable revision ID;
- content hash and semantic projection hash;
- parent revisions;
- producer/effect/machine binding;
- source problem revision;
- source external revision where applicable;
- format/schema/tool identity;
- external references;
- Evidence IDs.

The landed runtime records immutable revision documents through existing Evidence/event replay, verifies payload and semantic-projection hashes, exact parent IDs and parent fingerprints, ProblemRevision/external-source bindings, producer/machine/effect provenance, and active Evidence dependencies. Revision identity is backend-independent; `artifact_ref` is a non-semantic storage locator with a separate storage-binding fingerprint. Failed/generated artifacts may remain Evidence without becoming current authoritative artifacts. Artifact existence or successful generation is not authoritative acceptance. No hidden current-artifact/project-truth table, parallel artifact registry, truth table, or authority evaluator is introduced.

## 7.8 Entity evolution

**Status: GATED under the independent `aasm/entity-evolution` gate and inherited by cumulative `aasm/v56`.**

Target: `aasm.entity.evolution.v1`.

Relations:

`UNCHANGED | MODIFIED | GENERATED | SPLIT | MERGED | REPLACED | DELETED | AMBIGUOUS`

The landed runtime binds every predecessor/successor representation to an exact qualified artifact revision ID+fingerprint, validates workspace/scope and artifact-lineage ancestry, requires active supporting Evidence, reconstructs history by deterministic replay, and rejects forged fingerprints, unrelated lineages, and non-descendant successors. Hard reusable knowledge fails closed across `AMBIGUOUS` mapping. Evolution records preserve exact predecessor/successor identities and provenance; they do not silently rewrite historical entity identity or create a current-entity truth pointer.

## 7.9 TextPCB S3 conformance fixtures

Permanent fixture requirements include:

- project revision changes while solver/verifier is in flight;
- board/CAD artifact revision lineage;
- requirement/net/component/rule external-reference lineage;
- entity split/merge/replacement ambiguity;
- stale DRC/ERC observation;
- out-of-band TextPCB project-state transition;
- simulation result presented as if bench/physical;
- artifact hash mismatch;
- project/tool identity/configuration revision changes;
- DRC/tool calibration or trust invalidation without authority laundering;
- lifecycle stage skip or forged calibration/source lineage;
- multi-source agreement attempting to vote truth;
- disposed/stale/disputed source reuse.

TextPCB-specific kernel types remain forbidden.

## 7.10 Portability requirements active in S3

Every S3 object must define canonical field types, ordering, identity payload, enum values, optionality and fingerprint rules without Python object identity. These become future machine/kernel IR references rather than being redesigned for Rust.

**Gates:** `aasm/physical-evidence`, `aasm/identity-calibration-trust`, `aasm/execution-environment`, `aasm/observation-epistemics`, `aasm/artifact-lineage`, `aasm/entity-evolution`; all inherited by cumulative `aasm/v56`.

---

# 8. S4 — Engineering Semantics, Safety, Risk and Uncertainty

**Status: ACTIVE.** The first semantic seam, Quantity, is qualified; Rule is next.

## 8.1 Quantity/unit/tolerance semantics

**Status: GATED under `aasm/engineering-quantity`; public semantic IR, runtime engine-state admission remains `PRE_ADMISSION_ONLY`.**

Contract: `aasm.quantity.v1`.

Qualified representations:

- exact integer;
- exact rational;
- canonical decimal;
- interval;
- measured/estimated value with explicit uncertainty reference.

Qualified metadata/semantics:

- canonical integer-exponent dimension vector;
- explicit source unit and canonical unit;
- exact affine source-to-canonical transformation;
- absolute / relative / asymmetric tolerance;
- quantization/grid origin and explicit rounding rule;
- source precision;
- provenance/external references;
- deterministic canonical projection and fingerprints.

Dimensional inconsistency fails closed before solving or verification. Binary floating-point values cannot enter durable Quantity identity. There is no hidden mutable unit registry.

The foundation deliberately does **not** reinterpret existing numeric subsystems:

- solver `aasm.numeric.tolerance.v1` remains unchanged;
- `EffectCapability.NumericInterval` remains unchanged;
- postcondition, capability, solver, and physical-effect integration require explicit later translation/admission contracts rather than implicit Quantity coercion.

Quantity grants no FactAuthority, physical/external state authority, EffectAuthority, artifact acceptance, or entity identity authority.

## 8.2 Rule applicability and precedence

**Status: NEXT.**

Target: `aasm.rule.v1`.

Strength classes:

`HARD_FLOOR | HARD | POLICY | PREFERENCE | ADVISORY`

Bind:

- stable rule identity and source/external references;
- explicit applicability context/predicate;
- scope selector;
- priority;
- specificity;
- waiver/override policy;
- severity;
- source authority;
- exact problem/external revision applicability.

Rule precedence is not objective priority. A lower objective score cannot override a hard floor.

**Critical substrate rule:** AASM already has conflict-learning `LearnedConstraint` objects with `HARD | SOFT` strength in the formal execution calculus. `aasm.rule.v1` must not redefine or alias that vocabulary. Source engineering rules and learned constraints are different semantic objects. Any rule-to-constraint lowering/admission must be explicit, versioned, provenance-preserving, independently checkable, and fail closed when semantics cannot be preserved.

The first Rule implementation remains pre-admission until a dedicated `aasm/engineering-rule` gate proves scope/revision/applicability, precedence, waiver/override, source-authority, portability, and no-parallel-rule-engine invariants.

## 8.3 Semantic projection/equivalence

One explicit equivalence/projection contract is used for:

- solution pools/top-K/diversity;
- cache/reuse;
- cross-provider comparison;
- artifact comparison;
- TextPCB alternative design identity.

No implicit “same enough.”

## 8.4 Uncertainty/scenarios/trace properties

Target contracts:

- `aasm.uncertainty.v1`
- `aasm.scenario.v1`
- `aasm.trace-property.v1`

Uncertainty forms include exact, interval, scenarios, distribution reference, empirical samples, unknown bounded and unknown unbounded.

Temporal startup/shutdown/transient/sequence requirements remain trace properties, not forced into static constraints.

## 8.5 Degraded autonomy

Target: `aasm.degraded.operation.v1`.

Candidate modes:

`FULL_OPERATION | DEGRADED_OPERATION | LOCAL_ONLY | SAFE_HOLD | RETURN_TO_SAFE_STATE | EMERGENCY`

Loss of upstream intelligence reduces/reshapes authority according to policy; it never creates authority.

## 8.6 Risk and irreversibility

Targets:

- `aasm.risk.envelope.v1`
- `aasm.effect.irreversibility.v1`

Risk remains separate from resource cost. Hard hazards dominate optimization. More irreversible effects may require stronger evidence/authority under explicit profile policy.

## 8.7 Obligation phases

Extend the existing obligation graph with explicit phases:

`PRE_AUTHORIZE | PRE_DISPATCH | POST_DISPATCH | POST_OBSERVE | POST_VERIFY | RECOVERY`.

## 8.8 Safety envelope/hybrid state

Targets:

- `aasm.safety.envelope.v1`
- `aasm.hybrid.state.v1`

Bind discrete modes to observed continuous quantities and external solver/evidence references. AASM does not become an ODE/physics solver.

## 8.9 Epistemic debt and manual override

Targets:

- `aasm.epistemic.debt.v1`
- `aasm.manual.override.v1`

Debt uses existing semantic dependencies/obligations; no second debt graph.

Override records principal, exact waived rule, reason, scope, duration, accepted risk, authority evidence and resulting obligations. It never deletes history.

## 8.10 TextPCB S4 fixtures

- dimensional mismatch;
- trace/width/clearance/manufacturing rules;
- DRC/ERC hard rules vs preferences;
- controlled waiver provenance;
- thermal/power/signal scenario differences;
- tolerance/quantization handling;
- production alternative equivalence/diversity;
- hard hazard/evidence floor not relaxed by solver/resource scarcity.

## 8.11 Portability requirement active in S4

Introduce `aasm.invariant.v1` classification early enough that each new engineering/safety invariant declares whether it is:

`REPRESENTATIONAL | STATIC_PROTOCOL | DYNAMIC_KERNEL | EMPIRICAL`.

This prevents later Rust typestate from pretending to prove empirical facts and prevents statically knowable illegal configurations from remaining unstructured runtime conditionals.

**Current gate:** `aasm/engineering-quantity` — GATED.  
**Next dedicated gate:** `aasm/engineering-rule`.  
**Future aggregate gates:** `aasm/engineering-semantics`, `aasm/safety-governance`.

---

# 9. S5 — Governed Refinement, Experiments, Verification Planning and Knowledge Application

## 9.1 Refinement proposal/loop

Targets:

- `aasm.refinement.proposal.v1`
- `aasm.refinement.loop.v1`

Generic loop:

`solve -> verify -> diagnose -> propose -> validate applicability -> authorize -> ProblemDelta -> ProblemRevision -> invalidate affected work -> replan/re-solve/re-verify`.

The evaluator that discovers the issue cannot directly apply its own delta.

Termination includes:

`GOAL_SATISFIED | NO_PROGRESS | OSCILLATION | RESOURCE_EXHAUSTED | INCONCLUSIVE | CONFLICT | MANUAL_HOLD`.

## 9.2 Experiment contract

Target: `aasm.experiment.v1`.

Bind hypothesis, controlled variables, measured variables, procedure, environment, fixture/calibration identity, expected discriminating result, evidence floor, resources, safety/risk constraints and problem revision.

Experiment selection may optimize expected information gain/uncertainty reduction under hard safety/evidence/resource constraints. Selection is proposal-only.

## 9.3 Verification plan/debt

Targets:

- `aasm.verification.plan.v1`
- `aasm.verification.debt.v1`

Verifier capability declares fidelity, evidence grade, cost/resources, environment, numerical policy, soundness/completeness claims and cache/reuse eligibility.

Verification debt is a projection from required obligations vs applicable evidence, not a second truth plane.

## 9.4 Knowledge applicability/application

Generalize the v0.53 semantic/performance firewall:

- semantic knowledge stays inert until target-local validation;
- performance knowledge can affect search/routing but not legality;
- application requires explicit authority;
- applicability cannot broaden itself;
- superseded revision invalidates applicability unless independently preserved.

## 9.5 Integrated core/conflict pipeline

Preserve external references through raw -> normalized -> minimized -> independently rechecked cores/conflicts. Clearly distinguish irreducible, minimum/minimum-weight and budget-limited partial claims.

## 9.6 TextPCB refinement qualification

Treat TextPCB's engineering loop as a **consumer of the generic RefinementLoop**:

- DRC/ERC findings;
- SPICE simulation;
- EM analysis;
- thermal/PDN evidence;
- mechanical/manufacturing checks;
- external measurements;
- artifact/tool feedback.

Each evaluator returns typed Evidence/counterexample/diagnosis/proposal. No evaluator directly mutates TextPCB or AASM canonical truth.

This is the generic architecture:

`DESIGN -> VERIFY -> BUILD/GENERATE -> OPERATE/OBSERVE -> LEARN -> REDESIGN`.

## 9.7 Portable boundary

The future portable kernel carries refinement-related IDs/revisions/Evidence refs/obligations/state transitions. It does not embed LLMs, solvers, CAD, SPICE, EM or physics engines.

**Gate:** `aasm/refinement`.

---

# 10. S6 — Portable Machine IR and Kernel Boundary

This stage freezes the semantics another runtime may implement. It does **not** translate the entire Python codebase.

## 10.1 Invariant taxonomy

Finalize `aasm.invariant.v1`:

- `REPRESENTATIONAL`
- `STATIC_PROTOCOL`
- `DYNAMIC_KERNEL`
- `EMPIRICAL`

## 10.2 Machine IR

Target: `aasm.machine.ir.v1`.

Portable machine definition includes:

- machine/profile identity;
- states;
- events;
- transitions;
- structural legality;
- static capability requirements;
- dynamic guards;
- required Evidence refs;
- postcondition obligations;
- failure/recovery transitions;
- authority/capability refs;
- resource/effect refs;
- revision IDs;
- conflict transitions;
- timing requirements;
- canonical identity/fingerprint.

## 10.3 Transition timing

Target: `aasm.transition.timing.v1`.

Represent deadlines/timeouts/minimum intervals/ordering requirements in a clock-quality-aware portable way. Host wall-clock timestamps are not machine truth.

## 10.4 Portable kernel state boundary

Target: `aasm.kernel.portable.v1`.

Kernel includes only deterministic semantic state necessary to validate/process portable events/transitions/references.

It must not require:

- Python runtime/object identity;
- filesystem;
- SQL;
- network;
- LLM;
- solver;
- OS process model;
- arbitrary dynamic allocation;
- host wall clock as truth.

## 10.5 Canonical serialization

Freeze language-independent representation and hashing rules for portable objects. Unsupported/unknown fields and version migration behavior must be explicit.

## 10.6 Machine compiler/reference interpreter

Build a Python compiler/reference interpreter that consumes the canonical machine IR and produces deterministic transitions/traces. This is a semantic oracle, not a new AASM architecture.

## 10.7 Differential trace/fingerprint corpus

Each vector includes:

- input machine IR hash;
- initial portable state hash;
- ordered events;
- expected legal/illegal transition outcomes;
- Evidence/authority/capability references;
- expected state/event hashes;
- expected conflict/obligation outputs.

## 10.8 Proof-carrying configuration package

Generated deployable config binds:

- machine/config fingerprint;
- compiler identity/version;
- kernel compatibility profile;
- source problem/artifact revisions;
- verification/conformance evidence;
- authorization/admission evidence.

## 10.9 TextPCB portable fixture

Compile a representative TextPCB supervisory workflow to the **same generic machine IR** used by generic fixtures. This proves the IR is expressive enough for demanding external-engineering supervision without introducing TextPCB kernel types.

**Gate:** `aasm/portable-kernel`.

---

# 11. S7 — Rust `std` Reference Kernel

Implement only the S6 portable kernel contract.

## 11.1 Required implementation

- Rust canonical data model for the portable subset;
- canonical serialization/fingerprints equal to Python vectors;
- deterministic reducer/state transition engine;
- guard and reference checks;
- authority/capability ref validation required by machine IR;
- obligation/conflict generation;
- trace replay;
- stable error/outcome vocabulary.

## 11.2 Typestate

A generated Rust typestate layer may make statically provable illegal transitions unrepresentable. It is derived from the machine IR and may not add/remove legal transitions.

Dynamic authority, Evidence sufficiency, resource state and external facts stay runtime checks.

## 11.3 Differential conformance

For every portable corpus vector:

`Python reference outcome/hash == Rust std outcome/hash`.

Divergence is a failure; neither implementation votes the other correct. The canonical machine/kernel specification and independent vectors arbitrate.

## 11.4 Scope exclusion

Do not port:

- LLM integration;
- all solvers;
- all storage backends;
- full hosted orchestration;
- TextPCB domain logic;
- every Python convenience API.

**Gate:** `aasm/rust-kernel`.

---

# 12. S8 — Rust `no_std`, Real-Time and Embedded Executor Profile

## 12.1 `no_std` kernel

Provide a bounded profile for the already-conforming Rust kernel.

Explicitly define:

- maximum state/event/obligation/reference counts per profile;
- bounded journal behavior;
- bounded queues;
- deterministic overflow/fail-closed behavior;
- storage/checkpoint strategy;
- allocation strategy;
- recovery/replay boundaries.

## 12.2 Semantic executor/observer traits

Define semantic interfaces independent of hardware/transport brand. Examples may include observer/executor/artifact-producer roles, but the kernel contract is capability-based rather than vendor/protocol-based.

CAN, EtherCAT, GPIO/PWM, serial, REST gateways, simulators and HIL tools bind to these interfaces.

Interface compatibility does not imply evidence equivalence.

## 12.3 Interrupt/event bridge

Bind interrupt/device ingress to explicit device/node identity, boot epoch and monotonic sequence. Queue overflow/loss becomes explicit Evidence/conflict/degraded state, not silent disappearance.

## 12.4 Real-time backend

After generic timing semantics are stable, provide RTIC or another suitable backend mapping. The backend implements timing requirements; it does not define them.

## 12.5 Unsafe-code policy

Default portable kernel should avoid unsafe code where feasible. Hardware boundary unsafe code, if required, is isolated, reviewed, documented and covered by conformance/safety tests.

## 12.6 Firmware/config rollout pattern

Provide a generic AASM rollout machine such as:

`CANDIDATE -> VERIFIED -> STAGED -> DEPLOYING -> BOOT_VERIFIED -> ACCEPTED`, with rollback/recovery outcomes.

No firmware-specific kernel states are required globally.

**Gate:** `aasm/embedded-conformance`.

---

# 13. S9 — Qualification Continuum, TextPCB Conformance and Readiness

## 13.1 Environment ladder

Qualify the same semantic machine across:

`MODEL -> SIMULATION -> SIL -> HIL -> BENCH -> CONTROLLED_PHYSICAL -> OPERATIONAL`.

Evidence level changes only through explicit qualification policy, identity, calibration and verifier claims. The S3 environment contract provides the exact context identity; it does not itself define an ordinal truth ladder.

## 13.2 Embedded reference consumer

A canonical reference machine exercises:

- authority lease/epoch transfer;
- bounded effects;
- stale commands;
- postconditions;
- reboot epochs;
- interrupt/event loss;
- partitions and reconnect;
- degraded operation;
- safety envelopes;
- risk/irreversibility;
- manual override;
- resource exhaustion;
- replay/recovery.

## 13.3 Generic engineering adapter conformance

Conformance covers:

- external references/revisions;
- quantities/rules;
- artifacts/entities;
- external machines/effects;
- solver/verifier capabilities;
- refinement;
- alternative search/equivalence;
- uncertainty/scenarios/trace properties;
- readiness explanations.

## 13.4 TextPCB conformance

TextPCB remains authoritative for project truth/domain semantics/artifacts.

The adapter must provide:

- machine binding and transition mapping;
- stable requirement/constraint/net/component/artifact references;
- artifact observations/revisions;
- quantity/rule translations;
- verifier capability declarations;
- semantic projections/equivalence;
- refinement evaluator bindings;
- readiness/conformance Evidence.

Acceptance scenarios include:

- realistic project-state transitions;
- requirement -> constraint -> solver/artifact lineage;
- DRC/ERC feedback;
- SPICE/EM/thermal/mechanical verification;
- alternative search;
- artifact generation/revision;
- out-of-band change;
- stale result rejection;
- failed/inconclusive refinement;
- exact readiness explanation.

No TextPCB adapter operation may grant itself AASM truth or authority.

## 13.5 Readiness gate

Target: `aasm.readiness.gate.v1`.

Deterministic predicate over blocking obligations, Evidence/certificates, revision consistency, stale state, waivers, verification/epistemic debt, UNKNOWN effects, conflicts, required external state, resource settlement, proof state and conformance profile.

Every failed predicate returns exact blockers.

**Gates:** `aasm/textpcb-conformance`, `aasm/embedded-conformance`, `aasm/readiness`.

---

# 14. S10 — Production Search, Proof Expansion and Permanent Stress Corpus

The old production-search requirements remain active and are incorporated here rather than discarded.

## 14.1 Production lexicographic/Pareto

Extend exact finite reference semantics into scalable provider-backed modes while preserving truthful labels:

- exact finite;
- exact under certified provider contract;
- bounded partial;
- approximate;
- inconclusive.

## 14.2 Scalable solution pools/top-K/diversity

Support general integer no-goods, ranked top-K, near-optimal and semantically diverse alternatives, restartable cursors and provider-native paths. Exact finite engines remain oracles on tractable fixtures.

## 14.3 Proof/checker expansion

SAT proof transport/checking and LP/MILP certificate claims only where the provider/toolchain genuinely supports the claim. Feasibility, infeasibility, unboundedness and optimality remain separate claims.

## 14.4 Permanent adversarial corpus

Include at minimum:

- forged lineage/revisions;
- stale solver/verifier/machine/artifact results;
- poisoned semantic knowledge;
- performance hints attempting semantic mutation;
- unsupported/dropped lowering;
- false solver status/proof/completeness;
- Pareto/tolerance abuse;
- false core-minimization claims;
- duplicate/UNKNOWN external effects;
- out-of-band changes;
- stale authority epochs;
- revoked/expired capabilities;
- stale capability bearer attempts;
- forged/uncalibrated observation;
- simulation-as-physical laundering;
- sensor/solver consensus laundering;
- lifecycle stage laundering and forged processing lineage;
- disposed/stale/disputed observation reuse;
- artifact tampering;
- quantity/rule attacks;
- refinement self-authorization/no-progress/oscillation;
- scarcity attempting to weaken hard evidence;
- manual override without authority;
- portable serialization drift;
- Python/Rust fingerprint divergence;
- `no_std` queue/journal overflow;
- reboot-epoch replay attacks;
- false readiness.

---

# 15. S11 — Hosted-Foundation Review

Only after the merged architecture is substantially real, review whether a private hosted AASM fabric can be built purely as a consumer of the public contracts.

Hard criterion:

> A hosted fabric must not require a second truth, authority, resource, effect, revision, refinement, history, decision-routing, or machine-control system.

---

# 16. Cross-cutting portability discipline — active immediately

The broad Rust implementation occurs in S7/S8, but the following constraints apply to **every new contract from now on**:

1. stable language-neutral contract ID/version;
2. canonical identity payload and ordering rules;
3. explicit enum values;
4. explicit optional/unknown handling;
5. deterministic canonical serialization/fingerprint;
6. no Python object identity/`repr`/pickle/address dependency;
7. no host wall-clock dependence for semantic identity;
8. public finite/bounded profile considerations documented where embedded implementation will need them;
9. static-vs-dynamic-vs-empirical enforcement location identified;
10. portable cross-runtime test-vector feasibility reviewed before public admission.

This is how the Rust destination is engineered backward into current work instead of being deferred to a memory hole.

---

# 17. Cross-cutting TextPCB discipline — active immediately

Every generic engineering capability that TextPCB needs should gain at least one TextPCB-derived conformance fixture as soon as the generic contract is stable enough to test.

TextPCB may pressure contract design through realistic cases, but:

- no TextPCB classes/types enter the kernel;
- no TextPCB state becomes AASM state by copying;
- no TextPCB adapter grants itself authority;
- no TextPCB solver/verifier result becomes truth by provider status;
- TextPCB artifact/project revisions remain externally authoritative;
- TextPCB feedback enters as Evidence/refinement proposals;
- TextPCB readiness is an AASM explanation over governed evidence/obligations, not a rewrite of TextPCB's lifecycle.

---

# 18. Immediate builder queue

1. **Implement a pre-admission `aasm.rule.v1` foundation** with stable rule identity, external/source references, explicit applicability context, scope selector, priority, specificity, `HARD_FLOOR | HARD | POLICY | PREFERENCE | ADVISORY`, waiver/override policy, severity, source authority, and exact problem/external revision applicability.
2. Preserve the existing calculus `LearnedConstraint(strength=HARD|SOFT)` unchanged. Rule strength is source engineering/policy semantics, not learned-constraint strength; any lowering between them must be explicit, versioned, provenance-preserving, independently checkable, and fail closed.
3. Add strict portable Rule schema, deterministic fingerprinting, adversarial scope/revision/applicability/precedence/waiver/source-authority fixtures, a source firewall, and an independent `aasm/engineering-rule` gate before public/runtime admission.
4. Keep `aasm.quantity.v1` public but runtime-pre-admission while future Quantity integration is designed explicitly. Do not replace/reinterpret `aasm.numeric.tolerance.v1`, `EffectCapability.NumericInterval`, postcondition semantics, or solver/provider tolerance behavior implicitly.
5. Continue S4 projection/equivalence, uncertainty/scenarios/trace properties, degraded operation, risk/irreversibility, obligation phases, safety/hybrid state, epistemic debt, and manual override after Rule qualifies.
6. Add TextPCB-derived rule/waiver/revision fixtures only as conformance pressure; TextPCB rule/domain classes remain outside the kernel.
7. Continue applying cross-cutting portable identity/serialization discipline to every S4 object so future Rust does not require contract redesign.
8. Build S5 RefinementLoop/Experiment/VerificationPlan/KnowledgeApplication on existing Evidence/ProblemDelta/authority/resource/dependency planes.
9. Freeze S6 machine IR/kernel/wire semantics and Python reference vectors.
10. Implement S7 Rust `std` only against the frozen portable target; then S8 `no_std`/real-time/executor traits.
11. Complete TextPCB + embedded qualification, readiness and permanent stress corpus.

---

# 19. Release discipline

Architecture milestone completion does not allocate package SemVer.

A package release occurs only when:

- a coherent selected scope is intentionally frozen;
- active public/adoption contracts are internally consistent;
- applicable dedicated gates pass on the exact release SHA;
- inherited CI/formal/replay/provider gates pass;
- release inventory and reproducibility gates pass;
- release notes state only evidence-supported claims.

Published tags/releases remain immutable.

---

# 20. Final execution statement

The program is not “TextPCB first, Rust someday” and not “Rust kernel first, engineering later.”

It is one vertical architecture:

> **TextPCB and serious engineering workflows continuously force AASM's semantics to become rich enough for real governed design/refinement, while portable/Rust requirements continuously force those semantics to become explicit, deterministic and implementation-independent. Once that contract is frozen, Rust `std` and `no_std` become conforming implementations of the same AASM kernel—not a rewrite.**
