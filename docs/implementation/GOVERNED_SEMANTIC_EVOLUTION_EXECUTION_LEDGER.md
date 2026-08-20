# AASM Governed Semantic Evolution — Execution Ledger

**Status projection date:** 2026-08-17
**Latest immutable release:** `v0.56.0` at commit `551b2f4780acaeb93384b454f6f474f6ebd1b30e`
**Current development target:** `0.56.1` on `main`; exact unreleased identity is Git SHA
**Current adoption contract:** `aasm.adoption.v1 / 0.32.17`
**Current exact qualified code boundary before documentation-only synchronization:** `7c808fc504fa91edb8fe9af13f12568b745f9762` — all 29 current custom qualification contexts green
**Doctrine:** `docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`
**Physical/distributed reconciliation:** `docs/architecture/GOVERNED_PHYSICAL_DISTRIBUTED_REALITY_RECONCILIATION.md`
**Physical integration plan:** `docs/implementation/GOVERNED_PHYSICAL_REALITY_INTEGRATION_PLAN.md`
**Roadmap:** `ROADMAP.md` and `docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`
**Version/release policy:** `docs/VERSIONING.md`
**Historical v0.56 work-package release plan:** `docs/roadmaps/V056_CUMULATIVE_RELEASE_DISCIPLINE.md` — retained for provenance, superseded for future package allocation
**Source lock:** `docs/source_material/SOURCE_LOCK_MANIFEST.md`

This is the canonical mutable progress ledger. It may advance or refine work items, but locked requirements may not disappear. When an item is split, the parent row remains and points to its children.

Package SemVer is not an architecture-progress counter. Historical work-package IDs such as `56.2`, `57.1`, and `60.2` remain stable dependency/provenance identifiers; future work uses named milestone/program IDs and does **not** reserve future package versions.

Dormant or interrupted source code does not advance a row by itself. A row advances only when the relevant contract/runtime/test/gate evidence is deliberately admitted and qualified. A prerequisite must be semantically landed and sufficiently qualified before dependent work relies on it, but it does **not** need to be published as its own package release first.

## Status vocabulary

`SOURCE_LOCKED | DESIGNED | CONTRACT_LANDED | RUNTIME_LANDED | TESTED | GATED | RELEASED | BLOCKED`

- `GATED` means the declared qualification gate has actually executed the capability claims on an exact Git head.
- `RELEASED` means an immutable published package/tag exposes the capability.
- `GATED` does **not** imply `RELEASED`.

## Active execution ledger

| ID | Milestone / historical release | Capability | Status | Primary source requirement | Current code/contracts | Dependencies | Acceptance / adversarial evidence | Claim ceiling | Gate / next action |
|---|---|---|---|---|---|---|---|---|---|
| SRC-001 | cross | Source lock and doctrine | SOURCE_LOCKED | Preserve supplied TextPCB/AASM sources; prevent implementation drift | Whitepaper, canonical roadmap, source-lock manifest; exact source bundle retained separately | released semantic baseline | immutable hashes + precedence/no-overwrite rules | architecture doctrine only | add source revisions explicitly; never silently rewrite locked sources |
| VER-001 | development-identity-policy | Release/development identity separation | GATED | Git SHA, milestone, contract version, and package release must be distinct identity planes | `docs/VERSIONING.md`; `scripts/check_version_policy.py`; `.github/workflows/version-policy.yml`; manual-only release workflow | existing release gates | version-policy workflow passes without package bump; new chronology modules/version bumps rejected | development/release governance only | preserve; consolidate historical chronology gradually |
| 55.1-A | released v0.55.0 | ExternalReference | RELEASED | stable external requirement/decision identity through generated objects | `aasm.external.reference.v1`; schema; semantic evolution runtime | semantic fingerprinting | deterministic round trip + missing identity rejection | identity/provenance only; no truth authority | preserve |
| 55.1-B | released v0.55.0 | ProblemRevision | RELEASED | revision-bound solver/verifier/external semantics | `aasm.problem.revision.v1`; Evidence projection/runtime | 55.1-A | SQLite replay/restart; stale revision rejection | canonical revision identity; no external-state authority claim | preserve/extend |
| 55.1-C | released v0.55.0 | ProblemDelta | RELEASED | deterministic semantic change description | `aasm.problem.delta.v1`; typed truth-change roots | 55.1-B; semantic dependencies | stale-base fencing; semantic-fingerprint checks | declared delta only; no universal domain inference | preserve/extend |
| 55.1-D | released v0.55.0 | Revision transition + durable runtime | RELEASED | crash-safe application and precise invalidation | semantic-evolution runtime over existing Evidence/reducer | 55.1; truth maintenance; effects | restart/idempotent resume/replay/two-host stale writer | no parallel truth table | preserve |
| 55.2-A | released v0.55.0 | Model feature set | RELEASED | fail-closed semantic feature declaration | `aasm.model.feature-set.v1` | 55.1 | exact/approximate admission fixtures | declaration/admission only | preserve |
| 55.2-B | released v0.55.0 | Provider capability manifest | RELEASED | provider feature/status/proof/provenance negotiation | `aasm.provider.capability-manifest.v1` | 55.2-A | missing/approximate capability fail-closed | capability evidence only | preserve; later generalize executor/machine capability semantics |
| 55.2-C | released v0.55.0 | Model admission report | RELEASED | prevent unsupported lowering | `aasm.model.admission.v1` | 55.2-A/B | verifier-only and approximation fixtures | pre-execution semantic admission | preserve |
| 55.3 | released v0.55.0 | Generalized formulation artifact | RELEASED | preserve variable/constraint/objective/source mappings | `aasm.solver.formulation.v1` + certificate/runtime | 55.1/55.2 | mapping completeness/revision fencing/checker | exact identity checker only unless stronger checker exists | preserve |
| 55.3-A | released v0.55.0 | Exact pseudo-Boolean/cardinality IR | RELEASED | richer exact discrete constraints | `src/aasm/discrete_ir.py` | 55.2/55.3 | equivalence/tamper/contradiction fixtures | exact lowering only | preserve |
| 55.3-B | released v0.55.0 | Portable scheduling IR | RELEASED | portable scheduling semantics | `src/aasm/scheduling_ir.py` | 55.2/55.3 | precedence/no-overlap/cumulative validation | representation/validation; complete execution adapter not claimed | preserve |
| 55.3-C | released v0.55.0 | Deterministic quadratic/conic IR | RELEASED | continuous engineering representation | `src/aasm/continuous_ir.py` | 55.2/55.3 | deterministic serialization/feasibility/tolerance binding | structural + assignment validation; no global optimality proof | preserve; later compose with hybrid-state envelopes |
| 55.4 | released v0.55.0 | Shared objective-vector IR | RELEASED | semantic objectives and hard floors | `src/aasm/decision_vector_ir.py` | 55.1–55.3 | hard-floor exclusion/priority fixtures | scalarization none; exact representability required | preserve |
| 55.5 | released v0.55.0 | Portable semantic-evolution archive | RELEASED | portable replay/export without hosted truth | `aasm.semantic-evolution.archive.v1` | 55.1–55.4 | byte-stable round trip/tamper/reducer replay | event history is replay input; snapshot comparison evidence | preserve; foundational for portable-kernel differential replay |
| 56.1 | released v0.56.0 | Solver Outcome v2 | RELEASED | truthful solver termination/incumbent/bound/proof semantics | `solver_outcome_v2.py`; `provider_status_v2.py`; runtime + schemas | 55.2/55.3 | terminal-class corpus; independent incumbent validation; native provider mapping | normalization grants no truth; provider optimal is not independent proof | preserve |
| 56.2 | `execution-profiles-runtime-provenance`; existing 0.56.1 target | Execution profile + runtime provenance | GATED | evidence-grade observed execution configuration | `solver_provenance.py`; `_runtime_v56_provenance.py`; `solver_execution_observation.py`; schemas; active `public_v56` | 55.3; 56.1 | exact-head `aasm/v56-provenance` and cumulative `aasm/v56`; real CaDiCaL/OR-Tools/HiGHS/CVXPY fixtures | provenance alone does not prove reproducibility; unknown thread/config remains unknown | preserve in current coherent release train; no new package version allocated by subsequent work |
| 56.3 | `reproducibility-certification` | Reproducibility certification | SOURCE_LOCKED | truthful semantic/assignment/objective/proof reproduction claims | dormant `reproducibility.py`, `_runtime_v56_reproducibility.py`, and `solver_provenance_v2.py` work exists but is not active/admitted | qualified 56.2 | no active public/gate evidence yet; dormant source is insufficient | none beyond existing provenance ceiling | reconcile dormant v2 provenance with active provenance contract before admission |
| 56.4 | `knowledge-applicability-application` | Generic knowledge applicability/application | SOURCE_LOCKED | applicability-scoped learned constraints beyond solver learning | generalize v0.48/v0.53 mechanisms; no second knowledge store | 55.1; 56.1; solver learning | poisoned/cross-revision/cross-scope reuse corpus required | solver-learning subset already real | design explicit applicability/application contracts |
| 56.5 | `integrated-core-conflict-pipeline` | Integrated core/conflict pipeline | SOURCE_LOCKED | raw → normalized → minimized → independently rechecked requirement core | `conflict_minimization.py` exists as reusable primitive | 55.1; 55.3; 56.1 | irrelevant assumption/core-oracle fixtures | generic minimizer exists; integrated solver/domain pipeline not claimed | integrate after lineage + truthful outcomes |
| 57.1 | `external-machine-supervision` / PR-2A | External machine binding | GATED | supervise an external authoritative state machine without mirroring truth | `aasm.machine.binding.v1`; `aasm.machine.state-observation.v1`; `aasm.machine.external.runtime.v1`; `external_machine.py`; `external_machine_runtime.py`; schemas; active `public_v56` | v0.54 effects; 55.1 revisions; PR-1 | exact-head `aasm/external-machine`; subject/namespace/revision/capability laundering rejection; SQLite replay; binding references cannot mint fact/effect authority | reference/correlation only; no external truth copy, executor invocation, effect authority, or core machine-state mutation | preserve as PR-2A boundary; PR-2B/2C qualified on top |
| 57.2 | `external-machine-supervision` / PR-2B–2C | Revision-safe transition, state observation, postcondition verification | GATED | expected authoritative pre-state/revision, desired target state, post-effect observation, execution correlation, independently authoritative achieved state | `aasm.machine.transition.v1`; `aasm.machine.transition.runtime.v1`; `aasm.machine.postcondition-verification.v1`; `aasm.machine.postcondition-verification.runtime.v1`; existing v0.54 `EffectIntent`/ownership/reconciliation; active public surface | 57.1; effects; PR-1; PR-3; S3 reality evidence | exact-head transition/postcondition gates plus cumulative `aasm/v56`; real resource→worker→TaskDemand→TaskLease→ownership→dispatch path; stale prestate/correlation, ACK-without-achievement, non-authoritative observation, mismatch, idempotency, SQLite replay | `SUCCEEDED` is not achieved state; S3 context and S4 Quantity IR are separately qualified; Quantity has not yet been admitted into postcondition/capability runtime semantics; no second dispatcher/effect lifecycle or authority minting | preserve; explicit later quantity-aware postcondition translation requires its own contract/gate |
| 57.3 | `external-machine-supervision` | Artifact revision lineage | GATED | immutable CAD/PCB/CAE/physical outputs | `aasm.artifact.revision.v1`; `artifact_lineage.py`; `artifact_lineage_runtime.py`; schema; active public surface | 55.1; 57.1; S3-01–04 | first active/public exact head `6b107268cd4190357bf45b3bfd1385410a0d82cf`; inherited and requalified on `7c808fc504fa91edb8fe9af13f12568b745f9762`; `aasm/artifact-lineage` + cumulative `aasm/v56`; hash/parent/revision/provenance/storage/Evidence/replay attacks | artifact existence/generation/success is Evidence only; no authoritative acceptance, current artifact pointer, parallel registry/truth/authority evaluator | preserve |
| 57.4 | `external-machine-supervision` | Entity evolution | GATED | persistent semantic identity across topology/tool/world-model changes | `aasm.entity.evolution.v1`; `entity_evolution.py`; `entity_evolution_runtime.py`; schema; immutable additive public layer `0.32.15`, inherited by Quantity `0.32.16` and active Rule root `0.32.17` | 57.3 | first active/public exact head `6b107268cd4190357bf45b3bfd1385410a0d82cf`; inherited and requalified on `7c808fc504fa91edb8fe9af13f12568b745f9762`; `aasm/entity-evolution` + cumulative `aasm/v56`; evolution/fingerprint/lineage/Evidence/replay attacks | exact predecessor/successor provenance only; `AMBIGUOUS` blocks hard automatic reuse; no entity authority/current-state table | preserve as additive parent; S3 complete |
| S3-01 | `reality-evidence` | State conflict + causal event identity + observation freshness | GATED | expectation violation, distributed causal coordinates, clock quality and explicit freshness without host-time laundering | `aasm.state.conflict.v1`; `aasm.event.causality.v1`; `aasm.observation.freshness.v1`; runtimes/schemas/public surface | PR-1; PR-2 | original exact head `6dbd62dc704b15fccb86a61053ce7bfdcdea477a`; inherited through current `7c808fc504fa91edb8fe9af13f12568b745f9762`; TextPCB and embedded fixtures | conflict/freshness are Evidence only; no global total order; host wall clock not truth; `FRESH` grants no FactAuthority/effect authority/universal admission | preserve |
| S3-02 | `physical-identity-trust` | Physical identity + calibration + source trust | GATED | exact source/device/project identity, validity/revocation and trust-policy inputs without replacing authority | `aasm.physical.identity.v1`; `aasm.calibration.v1`; `aasm.source.trust.v1`; runtimes/schemas/public surface | S3-01; scoped authority; PR-1 | original exact head `6dbd62dc704b15fccb86a61053ce7bfdcdea477a`; inherited through current `7c808fc504fa91edb8fe9af13f12568b745f9762`; identity/calibration/trust/TextPCB/replay attacks | identity/calibration/trust are Evidence/policy-input layers only; record/revoke authority is not trust-evaluation authority; no reputation/voting/latest pointer; trust does not admit claims or grant effects | preserve |
| S3-03 | `execution-qualification-environment` | Explicit environment identity and qualification level | GATED | distinguish model/simulation/SIL/HIL/bench/controlled-physical/operational evidence without proximity laundering | `aasm.execution.environment.v1`; `aasm.execution.environment-binding.v1`; `aasm.execution.environment.runtime.v1`; schemas; active public surface | S3-01; S3-02 | first exact head `55a8da1f6937d97439a6e2103a55d1b6f6d0f4fd`; inherited through current `7c808fc504fa91edb8fe9af13f12568b745f9762` | environment level is exact context, not authority/truth rank; no automatic upgrade or cross-environment equivalence; record/bind authority is not environment-truth authority | preserve |
| S3-04 | `observation-epistemics` | Observation lifecycle + fusion | GATED | raw→normalized→calibrated→derived→validated lineage, explicit fusion, and rejected/superseded/stale/disputed outcomes without authority laundering | `aasm.observation.lifecycle.v1`; `aasm.observation.disposition.v1`; `aasm.observation.fusion.v1`; `aasm.observation.processing.runtime.v1`; schemas; active public surface | S3-01–03 | first exact head `55a8da1f6937d97439a6e2103a55d1b6f6d0f4fd`; inherited through current `7c808fc504fa91edb8fe9af13f12568b745f9762` | every derivation names exact source IDs/fingerprints; fusion never votes authority; `VALIDATED` is local label only; no parallel truth/observation/authority plane | preserve |
| 58.1 | `governed-refinement-verification-planning` | Governed refinement proposal/loop | DESIGNED | solve→verify→diagnose→refine→re-solve without evaluator self-mutation | designed `aasm.refinement.proposal.v1` / `aasm.refinement.loop.v1`; ProblemDelta and Evidence substrates released | 55.1; 56.4; 57.x | stale/self-authorized/no-progress/oscillation attacks | evaluator proposes only; existing authority commits | implement as composition, not new truth/scheduler |
| 58.2 | `governed-refinement-verification-planning` | Verification planning/debt | DESIGNED | multi-fidelity evidence acquisition and unresolved verification obligations | designed `aasm.verification.plan.v1` / `aasm.verification.debt.v1`; resources and verifier ABI exist | resources; verifier ABI; revisions | cheap pass cannot clear stronger obligation | debt is projection, not truth mutation | implement on existing obligations/Evidence/resources |
| 59.1 | `engineering-semantics-production-search` / S4-01 | Quantity/unit/tolerance semantics | GATED | exact dimensional correctness and portable engineering value identity | `aasm.quantity.v1`; `src/aasm/quantity.py`; strict `quantity.schema.json`; immutable additive public layer `0.32.16`, inherited by active Rule root `0.32.17`; `check_quantity_contracts.py`; `check_quantity_public.py` | 55.1; S3 complete | first qualified Quantity head `263640a634da0e92bb1ae0b42cb55063e0b64552`; inherited and requalified on `7c808fc504fa91edb8fe9af13f12568b745f9762`; `aasm/engineering-quantity` + cumulative `aasm/v56` + formal + full CI; exact-number/float rejection, affine conversion, dimension, interval, uncertainty, tolerance, quantization, precision, tamper, equivalence, legacy-substrate non-regression | public semantic IR only; runtime admission `PRE_ADMISSION_ONLY`; no unit registry, FactAuthority/effect authority, postcondition/capability/solver reinterpretation; `aasm.numeric.tolerance.v1` and `EffectCapability.NumericInterval` unchanged | preserve as additive parent |
| 59.2 | `engineering-semantics-production-search` / S4-02 | Rule applicability/precedence | GATED | hard-floor/hard/policy/preference/advisory semantics with applicability, waiver and revision/source authority | `aasm.rule.v1`; `src/aasm/rule.py`; strict `rule.schema.json`; additive active public root `0.32.17`; `public_active_engineering_rule.py`; `check_rule_contracts.py`; `check_rule_public.py`; dedicated tests/workflow | 55.1; 59.1 | exact head `7c808fc504fa91edb8fe9af13f12568b745f9762`; `aasm/engineering-rule` + cumulative `aasm/v56` + formal + full CI; 23 foundation/adversarial tests + 5 public tests; scope/revision/applicability/precedence/HARD_FLOOR/waiver/override/source-authority/float/portable-integer/tamper/learned-constraint-separation attacks | public semantic IR only; runtime admission `PRE_ADMISSION_ONLY`; no rule registry/current pointer/parallel constraint engine/authority evaluator; Rule existence and precedence grant no authority; no implicit mapping to `LearnedConstraint(HARD|SOFT)` | preserve; **NEXT 59.3 semantic projection/equivalence** |
| 59.3 | `engineering-semantics-production-search` / S4-03 | Semantic projection/equivalence | DESIGNED | meaningful top-K/diversity/cross-backend/artifact/reuse equivalence without implicit “same enough” | design exists; semantic fingerprints/projections already used narrowly across multiple substrates and must be reconciled before a generic contract lands | 55.1/55.3; 59.1; 59.2 | require exact identity vs projection-equivalence vs non-equivalence vs indeterminate/unsupported; projection-loss/revision/type/fingerprint attacks; TextPCB alternative/artifact fixtures | no generic claim yet; equivalence must be relative to explicit projection and cannot mint truth/authority/acceptance/proof/preference | **NEXT:** reconcile existing projections, define one portable explicit contract/schema/tests/firewall/gate; pull `aasm.invariant.v1` classification pressure into this design |
| 59.4 | `engineering-semantics-production-search` | Production lexicographic/Pareto | DESIGNED | scalable objective ordering/frontier truth | extend v0.52 finite reference engine | 55.4; 56.1; 59.3 | exact finite oracle qualifies scalable path | finite exact semantics already released | preserve partial/exact claim levels |
| 59.5 | `engineering-semantics-production-search` | Scalable pools/top-K/diversity | DESIGNED | production alternatives | extend v0.51 pools | 59.3/59.4 | top-K/near-optimal/diverse/restart fixtures | finite completeness currently released | truthful partiality required |
| 59.6 | `engineering-semantics-production-search` | Proof/checker expansion | DESIGNED | SAT proof transport; LP/MILP claims where genuine | extend v0.50 proof plane | 55.3; 56.x | forged/mismatched proof artifacts | provider-specific ceilings | implement only where checker/toolchain supports claim |
| 60.1 | `uncertainty-readiness-conformance` | Uncertainty/scenario/trace semantics | DESIGNED | operating modes, manufacturing variation, transient requirements | designed `aasm.uncertainty.v1`, `aasm.scenario.v1`, `aasm.trace-property.v1` | 55.1; 59.1 | nominal-vs-robust separation | none generic yet | implement explicit uncertainty/trace semantics |
| 60.2 | `uncertainty-readiness-conformance` | Readiness gate | DESIGNED | deterministic explainable completion/release predicate | designed `aasm.readiness.gate.v1` | 57–60 | UNKNOWN/stale/debt/conflict blocks readiness | none generic yet | implement explanation-required predicate |
| 60.3 | `uncertainty-readiness-conformance` | Engineering conformance + TextPCB qualification | DESIGNED | generic external-domain kit; TextPCB as demanding consumer | extend adapter-conformance substrate | all prior | realistic TextPCB mock/qualified fixtures | no TextPCB kernel types | qualify only after generic contracts land |
| 61.1 | `cross-capability-stress-corpus` | Permanent adversarial corpus | DESIGNED | proof of public claims under cross-capability attacks | existing specialized adversarial suites provide seed corpus | all | stale/forged/poisoned/UNKNOWN/unsupported/refinement/resource/projection attacks | tests establish only covered properties | make permanent and cumulative |
| 62.1 | `hosted-foundation-review` | Semantic Solver contract + hosted-foundation review | DESIGNED | hosted fabric must consume public semantics without private bypass | architecture review milestone | all | claim-to-gate audit + boundary review | no hosted-semantic bypass claim until review passes | execute after governed semantic evolution is substantially real |

## Reconciliation-discovered physical/distributed seams

These are the durable seams exposed by the Embedded/Physical review. They extend the existing authority, Evidence, resource, effect, revision, knowledge, verification, and refinement planes; they are **not** a separate Embedded AASM product.

| ID | Milestone | Capability | Status | Existing substrate / landed work | Missing semantic elevation / next boundary |
|---|---|---|---|---|---|
| PHY-01 | `physical-authority-capabilities` / PR-3 | Authority domains, leases/epochs, bounded revocable effect capabilities, semantic preemption, inherited Effect-boundary enforcement | GATED | PR-3A–G contracts plus PR-3H `aasm.effect.physical-authority-binding.v1` / `aasm.effect.physical-authority-integration.runtime.v1`; active engine rechecks live authority/capability at inherited effect authorization/execution; existing Effect lifecycle remains authoritative | parent complete; preserve live recheck, no reusable capability-use bearer token, no second dispatcher/authority/resource/effect system |
| PHY-02 | `authoritative-state-claims` / PR-1 | Desired / predicted / observed / authoritative state separation + fact authority | GATED | `aasm.fact.authority.v1`; `aasm.state.claim.v1`; `aasm.state.authority.runtime.v1`; Evidence + scoped authority only | boundary complete; preserve no authority laundering |
| PHY-03 | `postcondition-verification` / PR-2 | Command ≠ achievement; machine binding, transition attempt, correlated observation and postcondition verifier | GATED | machine binding/observation/transition/postcondition contracts over existing Effect lifecycle and PR-1 state authority | boundary complete; S4 Quantity IR is public/qualified but remains runtime-pre-admission, so quantity-aware postcondition/capability integration still requires an explicit later contract |
| PHY-04 | `temporal-causal-semantics` / PR-4 | state conflict, causal relation, boot epochs/local sequence, observation age, clock quality/freshness | GATED | `aasm.state.conflict.v1`; `aasm.event.causality.v1`; `aasm.observation.freshness.v1`; active runtimes/schemas/public surface | preserve no host-time truth/global ordering/authority from freshness; S3 complete |
| PHY-05 | `physical-identity-trust` / PR-4 | device/component/project identity, calibration validity/revocation, source-trust policy boundary | GATED | `aasm.physical.identity.v1`; `aasm.calibration.v1`; `aasm.source.trust.v1`; active runtimes/schemas/public surface | hardware attestation remains reserved; identity/calibration/trust remain Evidence only and `FactAuthority` remains separate |
| PHY-06 | `degraded-autonomy-safety` / PR-5 | degraded modes, safety envelopes, semantic preemption, hybrid discrete/continuous guards | DESIGNED | machine states/obligations, continuous IR, effects, scoped authority, qualified Quantity IR | degradation policy, continuous safety envelope, hybrid state contract, emergency/local authority rules |
| PHY-07 | `observation-epistemics` / PR-4 | execution environment, observation lifecycle, fusion, source independence, epistemic containment | GATED | `aasm.execution.environment.v1`; `aasm.observation.lifecycle.v1`; `aasm.observation.disposition.v1`; `aasm.observation.fusion.v1`; processing runtime; existing Evidence/PR-1/freshness/identity/calibration/trust | preserve exact environment/source lineage; no level ranking, stage-label authority, fusion voting, or parallel observation/truth store; S3 complete |
| PHY-08 | `epistemic-risk-obligations` / PR-5 | assumptions, epistemic debt, risk/hazards, irreversibility, pre/post obligations | DESIGNED | assumptions/reasoning artifacts, semantic dependencies, verification debt design, `EffectSpec.reversible`/compensation | generalized debt propagation, hazard/risk envelope, irreversible-action evidence escalation, obligation phase taxonomy |
| PHY-09 | `governed-experiments` / PR-6 | experiment contract and information-value evidence acquisition | DESIGNED | refinement design, resources, Evidence, verifier planning | hypothesis/control/measurement/procedure contract; experiment selection under safety/evidence/resource constraints |
| PHY-10 | `portable-kernel-machine-compiler` / PR-7 | language-neutral kernel semantics, stable machine IR, differential replay, Rust std/no_std | DESIGNED | portable semantic archive, typed IRs, deterministic fingerprints, formal models | kernel boundary independent of Python/DB/OS; canonical machine IR; Python/Rust conformance oracle; bounded no_std profile |
| PHY-11 | `embedded-realtime-qualification` / PR-8 | embedded-hal-style executor traits, RTIC mapping, SIM→SIL→HIL→physical qualification, safety profile | DESIGNED | provider/capability manifests, effects, resources, adapter conformance, S3 causal/identity/trust/environment foundations | embedded executor profile, timing contracts, interrupt bridge, safety-development restrictions; qualification-level binding is generic S3 substrate |

## Verified immutable release evidence

### v0.55.0

Release commit: `dd9360858be8755a5639162a7d388d867c1b01e6`
Tag: `v0.55.0`
GitHub release workflow: `31912974049` — **SUCCESS**

The release passed the exact-head CI/formal/semantic-solver/proof/solution-pool/optimization/scoped-authority/solver-learning/v0.54-parent/v0.55 gates, reproducible wheel/sdist build, clean install, immutable tag targeting, and remote asset SHA-256 verification.

### v0.56.0 — work package 56.1

Release commit: `551b2f4780acaeb93384b454f6f474f6ebd1b30e`
Tag: `v0.56.0`
GitHub release workflow: `31916382216` — **SUCCESS**

The release passed the exact-head inherited gates plus `aasm/v56`, reproducible package build, PostgreSQL/Compose/scopes/adapter/LangGraph integration, clean-install public contract exercise, immutable tag/release creation, and remote asset byte/SHA-256 verification.

This immutable release completes **56.1 Solver Outcome v2**. It does not imply release of 56.2, PR-1, or later work.

## Current development qualification evidence

Earlier exact-head qualifications remain valid historical provenance. The current cumulative boundary below supersedes them as the live development qualification snapshot without rewriting their history.

### S3 artifact/entity + S4 Quantity + Rule cumulative qualification

The current exact development head is:

```text
7c808fc504fa91edb8fe9af13f12568b745f9762
```

All **29 current custom commit-status contexts** were `success` on that exact head, including:

- `aasm/ci-summary`
- `aasm/formal-assurance`
- `aasm/semantic-solver-rc`
- `aasm/proof-claims`
- `aasm/solution-pools`
- `aasm/optimization`
- `aasm/scoped-authority`
- `aasm/solver-learning`
- `aasm/v54`
- `aasm/v55`
- `aasm/v56`
- `aasm/v56-provenance`
- `aasm/state-authority`
- `aasm/external-machine`
- `aasm/machine-transition`
- `aasm/machine-postcondition`
- `aasm/physical-authority`
- `aasm/effect-capability`
- `aasm/physical-control-fencing`
- `aasm/physical-preemption-recovery`
- `aasm/physical-effect-integration`
- `aasm/identity-calibration-trust`
- `aasm/execution-environment`
- `aasm/observation-epistemics`
- `aasm/artifact-lineage`
- `aasm/entity-evolution`
- `aasm/engineering-quantity`
- `aasm/engineering-rule`
- `aasm/physical-evidence`

The cumulative `aasm/v56` run passed the full inherited solver/provenance/PR-1/PR-2/PR-3/S3 chain, then the S4 Quantity and Rule source/public firewalls and adversarial/public corpora, cumulative release-contract validation, and the active `0.32.17` authority-boundary guard.

The Quantity qualification specifically proves:

- binary floating point is rejected from durable semantic numeric identity;
- integer/rational/canonical decimal normalization is deterministic;
- affine unit conversion (including scale/offset) is exact;
- dimensions and canonical-unit compatibility fail closed;
- intervals and measured/estimated uncertainty are explicit;
- tolerance modes, quantization/grid, rounding and source precision are explicit;
- canonical projection/identity/fingerprints survive round trip and reject tampering;
- different source units can share the same exact canonical mathematical projection;
- metadata/provenance cannot smuggle binary float identity;
- there is no hidden mutable unit registry;
- solver `aasm.numeric.tolerance.v1` remains untouched;
- `EffectCapability.NumericInterval` remains untouched;
- Quantity public admission adds no engine methods/state and grants no fact/effect/physical/external/artifact/entity authority.

The Rule qualification specifically proves:

- binary floating point and portable integer overflow are rejected from durable Rule identity/context where applicable;
- rule/clause/source-authority/external-reference identity and fingerprints are deterministic and tamper-evident;
- scope/subject and exact problem/external revision applicability are deterministic and fail closed;
- applicability is portable tri-state and executable callbacks are forbidden;
- precedence is strength, then specificity, then priority only inside an explicit precedence group;
- `HARD_FLOOR` cannot be waived or overridden;
- waiver/override helpers establish structural eligibility only and never grant authority;
- source authority is an exact existing scoped-authority grant reference, not a new authority evaluator;
- Rule strength does not redefine `LearnedConstraint(HARD|SOFT)` or decision-vector hard floors;
- no Rule registry/current pointer/parallel constraint engine/authority evaluator is introduced;
- Rule public admission adds no `AASMEngine` methods or state and runtime admission remains `PRE_ADMISSION_ONLY`.

Entity Evolution remains an immutable additive `0.32.15` parent layer; Quantity is the immutable additive `0.32.16` parent layer; the active Rule public root is `0.32.17`. Later additive public promotion does not rewrite either earlier contract layer.

This evidence qualifies **S3 complete + 59.1/S4-01 Quantity + 59.2/S4-02 Rule as GATED**, not RELEASED.

## Immediate builder queue

1. Keep `v0.56.0` / `551b2f47…` as the immutable published boundary. Do not publish 0.56.1 automatically.
2. Preserve all PR-1/2/3 and S3 claim ceilings; do not turn Evidence, capability existence, environment proximity, calibration, freshness, trust, processing stage, fusion agreement, artifact/entity existence, or source independence into authority.
3. **NEXT: reconcile existing semantic projections/equivalence mechanisms** across solution pools, cache/reuse, solver/formulation comparison, artifact semantic projections, decision vectors and semantic evolution before defining a generic S4.3 contract. Do not create a second identity/cache/truth plane.
4. Define exact identity versus equivalence-under-explicit-projection versus non-equivalence versus indeterminate/unsupported comparison. Any declared lossy projection must identify its semantic losses; loss cannot be silently treated as exact equivalence.
5. Pull `aasm.invariant.v1` classification pressure into S4.3 (`REPRESENTATIONAL | STATIC_PROTOCOL | DYNAMIC_KERNEL | EMPIRICAL`) so projection/equivalence cannot pretend that representational sameness proves empirical truth or discharges dynamic authority/evidence obligations.
6. Add a strict portable projection/equivalence schema/model, deterministic fingerprints, adversarial revision/type/projection-loss/forged-fingerprint fixtures, TextPCB alternative/artifact fixtures, source firewall, and dedicated pre-admission gate before public exposure.
7. Preserve Rule as public but runtime-pre-admission. Do not add a current Rule registry, automatic waiver/override authority, parallel constraint engine, or implicit Rule→`LearnedConstraint` lowering.
8. Preserve Quantity as public but runtime-pre-admission. Future Quantity integration with EffectCapability, postconditions, solver/provider tolerance, or physical-effect semantics must use explicit translation/admission contracts; do not silently reinterpret existing substrates.
9. Reconcile dormant reproducibility/provenance-v2 source separately before any 56.3 admission; dormant code remains non-authoritative.
10. Continue S4 uncertainty/scenario/trace, degraded-operation, risk/irreversibility, obligation phase, hybrid safety, epistemic debt and manual-override semantics after projection/equivalence qualifies.
11. Then implement S5 RefinementLoop/Experiment/VerificationPlan/KnowledgeApplication on existing Evidence/ProblemDelta/authority/resource/dependency planes.

## Completion discipline

A row advances to `TESTED` only with reproducible tests. It advances to `GATED` only when the declared gate executes those claims on an exact Git head. It advances to `RELEASED` only when an immutable published package/tag exposes the capability without exceeding the evidence.

Development may continue from a sufficiently qualified prerequisite without forcing an intermediate package publication. Package SemVer is assigned only at a deliberate coherent release boundary under `docs/VERSIONING.md`.

## S4.8 — Safety Envelope and Hybrid State

- Foundation implemented and gated under `aasm/engineering-safety-envelope-hybrid-state`.
- Reuses exact Quantity, HARD_FLOOR/SAFETY_INVARIANT Rule, ProblemRevision, Evidence/external references, and existing authority/effect boundaries.
- Performs conservative exact support containment only; no ODE/physics solving, controller synthesis, mode activation, authority grant, dispatch, or empirical safety proof.
- Runtime/public admission remains `PRE_ADMISSION_ONLY`.

## S4.9 — Epistemic Debt and Manual Override

- Foundation implemented; dedicated qualification active under `aasm/engineering-epistemic-debt-manual-override`.
- `aasm.epistemic.debt.v1` projects unresolved knowledge from the existing calculus obligation graph; no second graph/store/lifecycle or scalar debt score.
- `aasm.manual.override.v1` records exact Rule, scope, reason, explicit sequence window, accepted RiskAssessment, scoped-authority reference/evidence, and resulting existing obligations.
- HARD_FLOOR is never overridable. Review eligibility performs no waiver, authorization, mutation, dispatch, current-override activation, or history deletion.
- Runtime/public admission remains `PRE_ADMISSION_ONLY`.
- Next dependency seam: S4.10 permanent TextPCB fixtures and aggregate safety-governance qualification.

## S4.10 — Permanent TextPCB Corpus and Aggregate Safety Governance

- Closed, fingerprinted `aasm.textpcb.s4-safety-fixtures.v1` manifest implements all twelve normative S4.10 cases.
- Independent `aasm/safety-governance` gate reruns every S4 foundation/public/adversarial corpus plus integrated TextPCB fixtures and release firewalls.
- TextPCB remains a qualification consumer; no domain-specific runtime or engine surface was introduced.
- S4 dependency chain is now implemented through the permanent aggregate corpus.
- Next dependency seam: S5.1 governed Refinement Proposal/Loop foundation.
