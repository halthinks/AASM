# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, and long-horizon work.**

## Current release — v0.42.0

**Reference Domains & Reuse/Memory/Reasoning Stress Tests**

**Next release:** v0.43.0 — Semantic Conformance, Adversarial Domains, and Certification

AASM v0.42 stress-tests the existing domain-neutral solver stack through five deterministic offline reference domains: constraint solving, software repair, research synthesis, formal reasoning, and long-horizon memory. It deliberately does **not** introduce a second runtime or domain-specific kernel path. The active engine remains the v0.41 solver/reuse runtime; v0.42 adds a reference harness, public/CLI surfaces, schema, documentation, regression coverage, and a stricter verification-strength reuse boundary.

### Release contracts

```text
aasm.adoption.v1 / 0.18.0
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

### Five reference domains

The v0.42 harness exercises different correctness boundaries rather than repeating the same fixture five times:

- **Constraint solving:** exact subproblem-result reuse, durable recovery after deleting the process-local hot index, environment invalidation, and certificate-gated execution skipping.
- **Software repair:** freshness expiry, repository/dependency fingerprint changes, and the rule that non-idempotent effects are never discharged by reuse.
- **Research synthesis:** an authorized Reasoning Artifact is reusable until an ordinary truth-status change marks it stale; provenance remains durable while reuse is rejected.
- **Formal reasoning:** a requested verification strength is checked independently of the request fingerprint. A `SOLVER_VERDICT` cannot satisfy a request for `MULTI_SOLVER_AGREEMENT` merely by carrying the same request fingerprint.
- **Long-horizon memory:** governed user-private memory obeys principal visibility and becomes ineligible for reuse after an ordinary tombstone/revocation transition.

Every scenario also checks exact replay against the persisted machine state. The harness is synthetic and offline; it makes no benchmark claim about real-world domain quality and requires no model key, network access, or external solver.

```python
from aasm.reference_domains import run_reference_domain_stress

report = run_reference_domain_stress()
assert report["passed"]
```

### Reuse boundary

A reusable result must pass all applicable checks before execution can be skipped:

- exact canonical source fingerprint;
- durable policy/controller candidate admission;
- V31 hierarchical scope visibility;
- V40 principal privacy;
- environment compatibility;
- dependency-fingerprint compatibility;
- explicit freshness bounds when required;
- effect safety;
- requested verification-strength compatibility when specified;
- an explicit sound relation: `EXACT`, `IDEMPOTENT`, `SUBSUMES`, or `CERTIFIED_EQUIVALENT`.

Similarity and embeddings may discover candidates but never establish reuse. `SUBSUMES` requires an explicit semantic validator. Non-idempotent effects are never discharged by a cached result. v0.42 does not invent a hidden ordering among proof-strength strings: a required strength must be satisfied explicitly by the candidate contract.

### Cache deletion cannot change truth

The process-local `HotReuseIndex` is disposable. Clearing it can make a run slower, but cannot change the semantic result because a hit still requires durable candidate admission and the canonical source object. V36 `CompilationCache`, legacy `DPMemory`, V37 reasoning, V39 formal results, V40 Hierarchical Memory, and learned no-goods remain their existing systems; the reuse plane coordinates them instead of copying them into a new store.

### Solver-loop order

```text
reasoning frontier
      ↓
open obligation
      ↓
reuse validation ── hit → ReuseCertificate → verification/admission
      │
      miss
      ↓
capability route → worker/model/tool/solver → Evidence
      ↓
verification → epistemic admission → truth maintenance
      ↓
memory / learning → deterministic completion
```

The coordinator uses the existing AASM Decision / Obligation / Evidence calculus, V39 capability/lease boundary, V37 epistemic admission, V38 truth maintenance, and V40 context projection. It adds no second scheduler, reducer, event log, or truth store.

### Reuse telemetry

The reuse plane exposes counters for reuse attempts, exact/subsumption hits, negative prunes, stale/privacy/freshness/environment rejections, model/tool/solver executions avoided, and avoided input/output units. The v0.42 reference harness supplies controlled scenarios for exercising these boundaries without pretending synthetic fixtures are production benchmarks.

## V40 memory foundation

The existing `DPMemory`/`memo_*` API remains a deterministic algorithmic memoization cache. V0.40 Hierarchical Memory remains the durable governed semantic layer.

Memory kinds: `SENSORY`, `WORKING`, `EPISODIC`, `SEMANTIC`, `PROCEDURAL`.

Canonical substrates: `TEXT_RECORD`, `STRUCTURED`, `REFERENCE`, `EXECUTION_SNAPSHOT`.

**Embeddings are derived indexes**, not memory. Re-embedding a memory changes only a `MemoryIndexEntry`; it never changes the canonical `MemoryObject` fingerprint.

Canonical memory still follows:

```text
proposal
  ↓
MemoryOperationDecision
  ↓ POLICY / CONTROLLER
MemoryOperationObligation
  ↓
exact authorized MemoryObject or MemoryTombstone
  ↓
ordinary Evidence
```

`SEMANTIC` memory requires V37 reasoning artifacts already in `AUTHORIZED` state. V38 stale/refuted/rejected truth is excluded from ordinary context by default. `AGENT` and `USER` memories require the matching `privacy_principal_id`; `SHARED` and `PUBLIC` remain scope-governed. Forgetting appends a `MemoryTombstone`; historical Evidence is never silently deleted.

## Quick start

```bash
pip install aasm-runtime
```

```python
from aasm import AASMEngine, ProblemSpec, ReuseCandidate, ReuseRequest
from aasm.evidence import EvidenceRecord

engine = AASMEngine(ProblemSpec("repeatable analysis"))
prior = engine.add_evidence(EvidenceRecord("observation", "validated result", source="worker"))
source = engine.canonical_reuse_ref("EVIDENCE", prior.evidence_id)

request = ReuseRequest(
    "TOOL_OBSERVATION",
    {"query": "component status"},
    environment_fingerprint="environment-v1",
)
engine.register_reuse_candidate(
    ReuseCandidate(
        "TOOL_OBSERVATION",
        request.fingerprint,
        source,
        {"query": "component status"},
        environment_fingerprint="environment-v1",
    ),
    authority_id="policy",
    authority_class="POLICY",
)

hit = engine.lookup_reuse(request)
if hit["hit"]:
    engine.commit_reuse_certificate(hit, actor_id="controller")
```

## CLI

```bash
# v0.42 reference stress surfaces
aasm reference-domain-contract
aasm reference-domain-stress
aasm reference-domain-stress --domain software-repair

# v0.41 solver/reuse surfaces remain active
aasm reuse-contract
aasm reuse-report MACHINE_ID --store runs.db
aasm reuse-candidate-add MACHINE_ID --store runs.db --input candidate.json --authority-id policy --authority-class POLICY
aasm reuse-lookup MACHINE_ID --store runs.db --input request.json --commit --actor-id controller
aasm reuse-metrics-record MACHINE_ID --store runs.db --input metrics.json --actor-id controller
aasm solver-loop-contract
aasm solver-step MACHINE_ID --store runs.db --input step.json --reuse-input reuse-request.json

# V40 memory/context remains available
aasm hierarchical-memory-contract
aasm memory-report MACHINE_ID --store runs.db
aasm reasoning-frontier MACHINE_ID --store runs.db --input context-request.json
aasm context-project MACHINE_ID --store runs.db --input context-request.json
```

## Roadmap

- v0.35 Semantic Problem Model ✅
- v0.36 Semantic Compiler SDK ✅
- v0.37 Reasoning Artifacts & Epistemic Admission ✅
- v0.38 Dependency Graph & Truth Maintenance ✅
- v0.39 Typed Capability ABI & Formal Verification Workers ✅
- v0.40 Hierarchical Memory, Reasoning Frontier & Context Projection ✅
- v0.41 Domain-Neutral Solver Loop & Deterministic Reuse Plane ✅
- **v0.42 Reference Domains & Reuse/Memory/Reasoning Stress Tests ✅**
- **v0.43 next — Semantic Conformance, Adversarial Domains, and Certification**

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/REFERENCE_DOMAIN_STRESS.md](docs/REFERENCE_DOMAIN_STRESS.md), [docs/REUSE_AND_SOLVER_LOOP.md](docs/REUSE_AND_SOLVER_LOOP.md), and [docs/HIERARCHICAL_MEMORY_CONTEXT.md](docs/HIERARCHICAL_MEMORY_CONTEXT.md).
