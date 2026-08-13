# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, and long-horizon work.**

## Current release — v0.41.0

**Domain-Neutral Solver Loop and Deterministic Reuse Plane**

**Next release:** v0.42.0 — Reference Domains & Reuse/Memory/Reasoning Stress Tests

AASM v0.41 adds a sound work-avoidance layer before expensive model, tool, solver, or capability execution. It does **not** create a second cache authority. Reuse candidates point to canonical AASM Evidence, Reasoning Artifacts, or Hierarchical Memory; a hit is legal only after deterministic validation and can be committed as a provenance-bearing `ReuseCertificate`.

### Release contracts

```text
aasm.adoption.v1 / 0.17.0
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
- an explicit sound relation: `EXACT`, `IDEMPOTENT`, `SUBSUMES`, or `CERTIFIED_EQUIVALENT`.

Similarity and embeddings may discover candidates but never establish reuse. `SUBSUMES` requires an explicit semantic validator. Non-idempotent effects are never discharged by a cached result.

### Cache deletion cannot change truth

The process-local `HotReuseIndex` is disposable. Clearing it can make a run slower, but cannot change the semantic result because a hit still requires durable candidate admission and the canonical source object. V36 `CompilationCache`, legacy `DPMemory`, V37 reasoning, V39 formal results, V40 Hierarchical Memory, and learned no-goods remain their existing systems; V41 coordinates them instead of copying them into a new store.

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

The V41 coordinator uses the existing AASM Decision / Obligation / Evidence calculus, V39 capability/lease boundary, V37 epistemic admission, V38 truth maintenance, and V40 context projection. It adds no second scheduler, reducer, event log, or truth store.

### Reuse telemetry

V41 exposes counters for reuse attempts, exact/subsumption hits, negative prunes, stale/privacy/freshness/environment rejections, model/tool/solver executions avoided, and avoided input/output units. V42 reference domains will use these to compare cold and warm execution.

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
- **v0.41 Domain-Neutral Solver Loop & Deterministic Reuse Plane ✅**
- **v0.42 next — Reference Domains & Reuse/Memory/Reasoning Stress Tests**

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/REUSE_AND_SOLVER_LOOP.md](docs/REUSE_AND_SOLVER_LOOP.md), and [docs/HIERARCHICAL_MEMORY_CONTEXT.md](docs/HIERARCHICAL_MEMORY_CONTEXT.md).
