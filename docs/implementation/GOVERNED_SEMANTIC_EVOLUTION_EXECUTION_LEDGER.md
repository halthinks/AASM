# AASM Governed Semantic Evolution — Execution Ledger

**Status projection date:** 2026-08-15  
**Baseline:** v0.54.0  
**Doctrine:** `docs/architecture/GOVERNED_SEMANTIC_EVOLUTION_WHITEPAPER.md`  
**Roadmap:** `docs/roadmaps/GOVERNED_SEMANTIC_EVOLUTION_ROADMAP.md`  
**Source lock:** `docs/source_material/SOURCE_LOCK_MANIFEST.md`

This is the canonical mutable progress ledger. It may advance or refine work items, but locked requirements may not disappear. When an item is split, the parent row remains and points to its children.

## Status vocabulary

`SOURCE_LOCKED | DESIGNED | CONTRACT_LANDED | RUNTIME_LANDED | TESTED | GATED | RELEASED | BLOCKED`

## Active execution ledger

| ID | Release | Capability | Status | Primary source requirement | Current code/contracts | Dependencies | Acceptance / adversarial evidence | Claim ceiling | Gate / next action |
|---|---:|---|---|---|---|---|---|---|---|
| SRC-001 | cross | Source lock and doctrine | SOURCE_LOCKED | Preserve supplied TextPCB/AASM sources; prevent implementation drift | Whitepaper, canonical roadmap, source-lock manifest | v0.54 baseline | immutable hashes recorded; baseline commit recorded | architecture doctrine only | maintain manifest on source changes |
| 55.1-A | 0.55 | ExternalReference | TESTED | stable external requirement/decision identity through generated solver objects | `src/aasm/semantic_evolution.py`; `aasm.external.reference.v1`; schema | semantic fingerprinting | local focused tests: deterministic round-trip + missing-identity rejection | foundation experimental; not active package API | wire v0.55 public/gate after broader 55.1 completion |
| 55.1-B | 0.55 | ProblemRevision | TESTED | revision-bound evidence/solver/verifier/external-machine semantics | `aasm.problem.revision.v1`; schema | ExternalReference | local focused round-trip and identity tests | foundation experimental | add persisted/replay integration and revision graph checks |
| 55.1-C | 0.55 | ProblemDelta | TESTED | deterministic change impact and refinement materialization | `aasm.problem.delta.v1`; schema | ProblemRevision | local evidence-overlap rejection and stale-base fencing tests | foundation experimental | integrate with semantic dependency truth maintenance |
| 55.1-D | 0.55 | Revision transition checker | TESTED | stale-result rejection; exact base/target semantic binding | `validate_revision_transition` | ProblemRevision/Delta | local stale base + wrong target semantic-state tests | structural validator only | add adversarial persisted/replay fixtures |
| 55.2-A | 0.55 | Model feature set | SOURCE_LOCKED | fail-closed provider/model admission | planned `aasm.model.feature-set.v1` | 55.1 | unsupported/exact/approximate fixtures | none yet | implement next |
| 55.2-B | 0.55 | Provider capability manifest | SOURCE_LOCKED | provider feature/status/proof/provenance negotiation | planned `aasm.provider.capability-manifest.v1` | 55.2-A | provider manifest mismatch fixtures | none yet | implement with 55.2-A |
| 55.3 | 0.55 | Generalized formulation artifact | SOURCE_LOCKED | preserve variable/constraint/objective/external-reference mappings | planned `aasm.solver.formulation.v1`; reuse v0.54 translation | 55.1, 55.2 | dropped/mutated mapping must fail | none yet | generalize v0.54 exact identity translation |
| 55.4 | 0.55 | Shared objective-vector IR | SOURCE_LOCKED | semantic objectives ↔ optimization objectives; true lexicographic priorities | extend v0.52 multi-objective | 55.1, 55.2 | higher-priority compliance beats lower-priority gain | exact finite semantics already released; shared IR not yet | implement after formulation seam |
| 55.5 | 0.55 | Portable semantic-evolution archive | SOURCE_LOCKED | portable replay/export without hosted-only state | extend current persistence/export work | 55.1-55.4 | round-trip + tamper detection + replay equality | none yet | design manifest around known future object families |
| 56.1 | 0.56 | Solver outcome v2 | SOURCE_LOCKED | normalized fine-grained statuses | planned | 55.2/55.3 | provider-specific termination/incumbent/bound/proof fixtures | old coarse status remains current | implement after v0.55 IR identity |
| 56.2 | 0.56 | Execution profile + runtime provenance | SOURCE_LOCKED | evidence-grade deterministic execution | planned | 55.3, 56.1 | effective-option/env/provider identity fixtures | current fingerprints/solver identity only | implement provider-neutral contract then adapters |
| 56.3 | 0.56 | Reproducibility certification | SOURCE_LOCKED | truthful reproducibility claim levels | planned | 56.2 | semantic/assignment/objective/proof equivalence reruns | none yet | follow provenance |
| 56.4 | 0.56 | Generic knowledge applicability/application | SOURCE_LOCKED | durable applicability-scoped learned constraints beyond solver learning | generalize v0.48/v0.53 mechanisms | 55.1, 56.1 | poisoned/cross-revision/cross-scope reuse attacks | solver-learning subset already real | design without second knowledge store |
| 56.5 | 0.56 | Integrated core/conflict pipeline | SOURCE_LOCKED | raw → normalized → minimized → independently rechecked external requirement core | reuse `conflict_minimization.py` | 55.1, 55.3, 56.1 | irrelevant-assumption/core oracle fixtures | generic minimizer exists; real pipeline incomplete | integrate after formulation lineage |
| 57.1 | 0.57 | External machine binding | SOURCE_LOCKED | AASM supervises TextPCB state machine without mirroring truth | planned `aasm.machine.binding.v1` | 55.1, v0.54 effects | stale observed revision, out-of-band change | none yet | build over EffectIntent |
| 57.2 | 0.57 | Revision-safe machine transition | SOURCE_LOCKED | transition intent/receipt/expected state | planned `aasm.machine.transition.v1` -> v0.54 EffectIntent | 57.1, v0.54 ownership | no call before ownership; stale prestate rejects; UNKNOWN blocks retry | effect ownership already real | no second effect lifecycle |
| 57.3 | 0.57 | Artifact revision lineage | SOURCE_LOCKED | CAD/PCB/CAE artifacts are immutable revisioned outputs | planned | 55.1, 57.1 | tamper/parent lineage/stale artifact tests | existing artifact backend only | add canonical lineage |
| 57.4 | 0.57 | Entity evolution | SOURCE_LOCKED | persistent semantic identity across CAD topology/tool representation change | planned | 57.3 | ambiguous mapping blocks hard reuse | none yet | genericize beyond CAD |
| 58.1 | 0.58 | Governed refinement proposal/loop | SOURCE_LOCKED | solve→verify→learn→re-solve without direct verifier mutation | planned | 55.1, 56.4, 57.x | stale/self-authorized/no-progress refinement attacks | none yet | compose existing Evidence/reasoning/authority |
| 58.2 | 0.58 | Verification planning/debt | SOURCE_LOCKED | multi-fidelity evidence acquisition and release debt | planned | resources, verifier ABI, 55.1 | cheap-pass must not clear stronger obligation | none yet | projection over existing obligations/evidence/resources |
| 59.1 | 0.59 | Quantity/unit/tolerance semantics | SOURCE_LOCKED | engineering dimensional correctness | planned | 55.1 | dimensional mismatch/rounding/tolerance fixtures | none yet | generic quantity contract |
| 59.2 | 0.59 | Rule applicability/precedence | SOURCE_LOCKED | hard floor / hard / policy / preference / advisory semantics | planned | 55.1, 59.1 | override/waiver/priority attacks | none yet | keep distinct from objective priority |
| 59.3 | 0.59 | Semantic projection/equivalence | SOURCE_LOCKED | meaningful top-K/diversity/cross-backend equivalence | planned | 55.1, 55.3 | auxiliary-variable differences collapse under semantic projection | none yet | use across pools/reuse/artifacts |
| 59.4 | 0.59 | Production lexicographic/Pareto | SOURCE_LOCKED | scalable objective ordering/frontier truth levels | extend v0.52 exact finite reference | 55.4, 56.1, 59.3 | exact finite oracle qualifies production paths | exact finite already released | preserve claim levels |
| 59.5 | 0.59 | Scalable pools/top-K/diversity | SOURCE_LOCKED | real generated alternatives | extend v0.51 pools | 59.3, 59.4 | top-K/near-optimal/diverse/restart fixtures | complete finite currently released | truthful partiality |
| 59.6 | 0.59 | Proof/checker expansion | SOURCE_LOCKED | SAT proof transport; LP/MILP claims where genuine | extend v0.50 proof plane | 55.3, 56.1/56.2 | forged/mismatched proof artifacts | bounded proof plane already released | provider-specific claim ceilings |
| 60.1 | 0.60 | Uncertainty/scenario/temporal | SOURCE_LOCKED | operating modes, manufacturing variation, transient requirements | planned | 55.1, 59.1 | nominal-vs-robust claim separation | none yet | generic contracts |
| 60.2 | 0.60 | Readiness gate | SOURCE_LOCKED | deterministic completion/release predicate | planned | 57-60 | unresolved UNKNOWN/stale/debt/conflict blocks readiness | none yet | explanation-required |
| 60.3 | 0.60 | Engineering conformance + TextPCB qualification | SOURCE_LOCKED | generic external-domain kit; TextPCB as consumer | extend adapter conformance | all prior | realistic TextPCB mock/qualified fixtures | none yet | no TextPCB kernel types |
| 61.1 | 0.61 | Permanent stress corpus | SOURCE_LOCKED | adversarial proof of public claims | planned | all | cross-capability attack corpus | none yet | move old v0.56 stress milestone here |
| 62.1 | 0.62 | Semantic Solver RC2 + hosted-foundation review | SOURCE_LOCKED | public engine can support hosted fabric without private semantic bypass | planned | all | claim-to-gate audit + architecture boundary review | none yet | move old v0.57 review here |

## Immediate builder queue

1. Finish 55.1 by integrating revisions/deltas with persistence/replay and semantic dependency impact semantics.
2. Implement 55.2 ModelFeatureSet + ProviderCapabilityManifest.
3. Generalize v0.54 solver translation into 55.3 FormulationArtifact while preserving exact v0.54 behavior.
4. Only after these identity/capability seams are stable, deepen shared objective IR and archive semantics.

## Completion discipline

A row advances to `TESTED` only with reproducible tests. It advances to `GATED` only when the declared release gate executes those claims on exact head. It advances to `RELEASED` only when the active package/public surface and release documentation expose the capability without exceeding the evidence.
