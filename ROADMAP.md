# AASM Roadmap

AASM is currently **v0.44.0 / experimental**.

## Released

- v0.35.0 Semantic Problem Model Foundations
- v0.36.0 Semantic Compiler SDK
- v0.37.0 Reasoning Artifacts and Epistemic Admission
- v0.38.0 Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- v0.39.0 Typed Capability ABI and Formal Verification Workers
- v0.40.0 Hierarchical Memory, Reasoning Frontier, and Context Projection
- v0.41.0 Domain-Neutral Solver Loop and Deterministic Reuse Plane
- v0.42.0 Reference Domains & Reuse/Memory/Reasoning Stress Tests
- v0.43.0 Semantic Conformance, Adversarial Domains, and Certification
- **v0.44.0 Heterogeneous Optimization Solver Portfolio — Current — implemented**

## v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection

Delivered canonical governed memory, reasoning frontier/context projection, privacy, retention/tombstones, deterministic replay/restart, and preservation of legacy `DPMemory` as algorithmic memoization.

## v0.41.0 — Domain-Neutral Solver Loop and Deterministic Reuse Plane

Delivered canonical reuse requests/candidates, POLICY/CONTROLLER admission, durable reuse certificates, exact/idempotent/explicit-subsumption/certified-equivalence modes, scope/privacy/environment/dependency/freshness/effect validation, disposable non-authoritative hot index, reuse metrics, and certificate-gated solver execution skipping.

## v0.42.0 — Reference Domains and Stress Tests

Delivered `aasm.reference-domains.v1 / 0.1.0`, five deterministic offline reference domains, explicit verification-strength reuse enforcement, public/CLI/schema/docs/regression surfaces, and exact replay checks without introducing a parallel runtime.

## v0.43.0 — Semantic Conformance and Adversarial Certification

Delivered `aasm.certification.v1 / 0.1.0` with `PASS | FAIL | INCONCLUSIVE`, certification profiles for reference domains/reuse/truth-memory/formal verification, strict separation of architecture certification from arbitrary external semantic truth, and an experimental SII certification target with explicit unresolved graduation gates.

## v0.44.0 — Heterogeneous Optimization Solver Portfolio

Delivered:

1. `aasm.optimization.v1 / 0.1.0` canonical Constraint IR;
2. Boolean, integer, and continuous variables;
3. clause, linear, and all-different constraints;
4. linear minimize/maximize objectives;
5. deterministic SAT / CP-SAT / MILP family inference;
6. `solver.sat@0.1.0` backed by PySAT/CaDiCaL;
7. `solver.cp_sat@0.1.0` backed by OR-Tools CP-SAT;
8. `solver.milp@0.1.0` backed by HiGHS/highspy;
9. preservation of Z3, cvc5, Vampire, and Lean 4 on the existing formal-verification path;
10. provider admission through the existing v0.39 Capability ABI;
11. execution through existing `ResourceRecord`, `WorkerRecord`, `TaskDemand`, and `TaskLease` machinery;
12. exact request/model/provider/lease validation before result commit;
13. independent rechecking of successful assignments and objective values against canonical AASM IR;
14. optimization results committed as `EVIDENCE_ONLY`;
15. explicit v0.41 `ReuseRequest` generation and policy-gated reuse-candidate admission;
16. certificate-gated solver-loop `SKIP_EXECUTION` for validated repeated optimization work;
17. dependency-neutral regression coverage;
18. real native-backend GitHub Actions coverage for CaDiCaL, CP-SAT, and HiGHS;
19. bounded TLA+ and Promela/SPIN authority models;
20. schemas, CLI, public contract, release/source gates, release documentation, and tracked-inventory coverage.

The v0.44 release deliberately does not rewrite solver inner loops. AASM owns the canonical problem/decomposition/execution/reuse/certification boundary; native solver projects own their optimized search kernels.

### Next performance work after v0.44

The next solver-specific extensions should be explicit contracts rather than opaque backend metadata:

- incremental SAT assumptions and UNSAT cores;
- governed learned-clause provenance;
- pseudo-Boolean/cardinality constraints;
- CP-SAT interval/no-overlap/cumulative scheduling primitives;
- deterministic-time and conflict/search budgets;
- MILP incumbents, bounds, nodes, bases, warm starts, and cut telemetry;
- solver portfolio racing/selection;
- cross-solver translation certificates;
- proof logging/certificate checking for SAT or optimization infeasibility;
- certified cross-solver conflict/bound reuse.

## v0.45.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics

**Next.** Graduate SII from experimental certification target to enforceable participation plane on top of real solver and reasoning resources.

Required graduation work:

1. bind proposer and measurement identities to durable governed AASM principals;
2. resolve measurement authority from existing AASM authority/capability state rather than caller-supplied strings;
3. bind ResourceLease context budgets to v0.40 context projection;
4. bind parallel-candidate and scheduling budgets to the existing resource/scheduler path;
5. bind solver privileges to the v0.39/v0.44 capability and task-lease boundaries;
6. expose real resource budgets such as SAT search/conflict budget, CP-SAT deterministic time, MILP node/iteration budget, formal verification budget, model-call budget, and portfolio width;
7. move scoring thresholds/weight profiles into explicit versioned policy objects;
8. preserve bounded-window decay so prior success never grants permanent power;
9. add adversarial fixtures for farming, collusion, stale data, identity games, score oscillation, privilege escalation, and resource-policy bypass;
10. require `aasm certify --target sii-preview` to graduate from `INCONCLUSIVE` to `PASS` before activating SII authority-adjacent resource control;
11. retain the invariant that utility can buy compute/search/context, never truth or canonical-state authority.

## v0.46.0 — Cross-Run Certified Knowledge and Governed Long-Term Memory

Opt-in cross-run knowledge with immutable provenance, applicability scope, compatibility, epistemic status, retention/privacy, revocation/supersession, explicit receiving-run admission, and SII-aware resource accounting without authority inheritance.

## v0.47.0 — Semantic Solver Release Candidate

Freeze the coherent public solver contracts after replay, formal, distributed, adversarial, memory/privacy, reference-domain, certification, native optimization, SII, packaging, and upgrade gates pass.
