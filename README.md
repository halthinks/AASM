# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, and long-horizon work.**

## Current release — v0.40.0

**Hierarchical Memory, Reasoning Frontier, and Context Projection**

AASM v0.40 adds governed long-horizon memory without creating a second truth system. Canonical memory remains on the existing AASM Decision → Obligation → Evidence path; semantic memory can reference only admitted reasoning artifacts; V38 truth changes can make memory stale; scope and principal privacy are enforced before retrieval; vector/lexical/graph indexes are derived and never become memory identity.

### Release contracts

```text
aasm.adoption.v1 / 0.16.0
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

### Memory boundary

The existing `DPMemory`/`memo_*` API remains a deterministic algorithmic memoization cache. V0.40 Hierarchical Memory is the durable governed semantic layer.

Memory kinds: `SENSORY`, `WORKING`, `EPISODIC`, `SEMANTIC`, `PROCEDURAL`.

Canonical substrates: `TEXT_RECORD`, `STRUCTURED`, `REFERENCE`, `EXECUTION_SNAPSHOT`.

**Embeddings are derived indexes**, not memory. Re-embedding a memory changes only a `MemoryIndexEntry`; it never changes the canonical `MemoryObject` fingerprint.

### Authority path

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

Workers cannot replace authorized content at commit time.

### Semantic memory and stale truth

`SEMANTIC` memory requires V37 reasoning artifacts already in `AUTHORIZED` state. If V38 later marks those artifacts stale/refuted/rejected, the memory projection becomes stale and ordinary context excludes it by default.

### Privacy and scope

Hierarchical visibility reuses AASM Decision Scopes. `AGENT` and `USER` memories additionally require `metadata.privacy_principal_id`, and context projection must present the same principal. `SHARED` and `PUBLIC` remain scope-governed.

### Retention and forgetting

Retention: `permanent`, `forgettable`, `ttl:<seconds>`. TTL is evaluated against explicit/durable time. Forgetting appends a `MemoryTombstone`; historical Evidence is never silently deleted.

### Reasoning Frontier and Context Projection

V0.40 deterministically projects bounded context from valid visible memories plus current reasoning artifacts, active decisions, and open obligations. Ranking may use lexical relevance, V38 causal/objective relevance, verification strength, and admitted derived index scores. Hard item and character budgets are enforced.

## Quick start

```bash
pip install aasm-runtime
```

```python
from aasm import AASMEngine, ProblemSpec, ContextProjectionRequest

engine = AASMEngine(ProblemSpec("long-horizon analysis"))
proposal = engine.propose_memory_operation(
    "STORE",
    scope_id="root",
    proposer_id="agent-1",
    kind="WORKING",
    substrate="STRUCTURED",
    content={"finding": "component A needs revalidation"},
    privacy_level="USER",
    metadata={"privacy_principal_id": "user-123"},
)
decision_id = proposal["decision"]["decision_id"]
engine.authorize_memory_operation(decision_id, authority_id="policy", authority_class="POLICY")
engine.commit_memory_operation(decision_id, worker_id="memory-worker")

context = engine.context_projection(ContextProjectionRequest(
    query="what needs revalidation?",
    max_chars=8000,
    metadata={"principal_id": "user-123"},
))
```

## CLI

```bash
aasm hierarchical-memory-contract
aasm hierarchical-memory-conformance
aasm memory-report MACHINE_ID --store runs.db
aasm memory-propose MACHINE_ID --store runs.db --input operation.json
aasm memory-authorize MACHINE_ID DECISION_ID --store runs.db --authority-id policy --authority-class POLICY
aasm memory-commit MACHINE_ID DECISION_ID --store runs.db --worker-id memory-worker
aasm memory-forget MACHINE_ID MEMORY_ID --store runs.db --proposer-id user --reason "privacy revocation"
aasm memory-index-add MACHINE_ID --store runs.db --input index.json --authority-id policy --authority-class POLICY
aasm reasoning-frontier MACHINE_ID --store runs.db --input context-request.json
aasm context-project MACHINE_ID --store runs.db --input context-request.json
aasm context-record MACHINE_ID --store runs.db --input context-request.json --actor-id worker-1
```

## Roadmap

- v0.35 Semantic Problem Model ✅
- v0.36 Semantic Compiler SDK ✅
- v0.37 Reasoning Artifacts & Epistemic Admission ✅
- v0.38 Dependency Graph & Truth Maintenance ✅
- v0.39 Typed Capability ABI & Formal Verification Workers ✅
- **v0.40 Hierarchical Memory, Reasoning Frontier & Context Projection ✅**
- **v0.41 next — Domain-Neutral Autonomous Solver Loop**

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), and [docs/HIERARCHICAL_MEMORY_CONTEXT.md](docs/HIERARCHICAL_MEMORY_CONTEXT.md).
