# AASM — Algorithmic Agent State Machine

**Durable deterministic control for agents, tools, models, humans, and long-horizon work.**

## Current release — v0.43.0

**Semantic Conformance, Adversarial Domains, and Certification**

**Next release:** v0.44.0 — Symbiotic Intelligence Interface & Governed Intelligence Economics

AASM v0.43 adds an explicit certification layer above the existing v0.42 reference-domain stress harness. Certification reports `PASS | FAIL | INCONCLUSIVE`, treats missing evidence as non-success, and distinguishes deterministic AASM contract behavior from claims about arbitrary external truth. The active kernel remains `runtime_v41.AASMEngine`; v0.43 adds no second scheduler, reducer, event log, or truth store.

The release also stages the **Symbiotic Intelligence Interface (SII)** as an experimental v0.44 participation plane. SII lets models, agents, humans, solvers, and ensembles submit structured proposals and earn bounded compute/search/context resources from independently measured contribution—without ever earning epistemic authority. Its current certification result is deliberately `INCONCLUSIVE` until actor-authority binding and ResourceLease enforcement are completed.

### Release contracts

```text
aasm.adoption.v1 / 0.19.0
aasm.certification.v1 / 0.1.0
aasm.sii.v1 / 0.2.0              # experimental v0.44 target
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

### Certification semantics

v0.43 makes uncertainty explicit:

- **PASS** — every required observed check for the selected certification target passed.
- **FAIL** — one or more required observed checks failed.
- **INCONCLUSIVE** — no required observed check failed, but required evidence or enforcement is absent.

`INCONCLUSIVE` is a valid terminal result. Synthetic fixture success is not reinterpreted as proof that arbitrary real-world data, model output, research conclusions, software diagnoses, mathematical statements, or memories are correct.

The default certification run covers:

- **reference-domains** — all five v0.42 deterministic reference domains;
- **solver-reuse** — durable reuse, certificate-gated skipping, freshness/dependency/effect rejection, and verification-strength enforcement;
- **truth-memory** — reasoning staleness, memory privacy, revocation, and durable invalidation;
- **formal-verification** — exact proof-strength requirements and validated formal-result reuse;
- **sii-preview** — adversarial tests for identity reset, score forgery, fake reuse credit, self-measurement, outcome farming, and authority escalation.

The four core targets are expected to `PASS`. The experimental SII target is intentionally `INCONCLUSIVE` until its v0.44 graduation gates are closed.

```python
from aasm import run_certification

report = run_certification()
assert report["core_status"] == "PASS"
assert report["status"] == "INCONCLUSIVE"  # experimental SII preview not graduated yet
```

### Symbiotic Intelligence Interface

SII is governed by three laws:

1. **The reasoner proposes; AASM measures.**
2. **Utility may buy resources; utility never buys truth.**
3. **AASM returns compressed governed intelligence, not merely a reputation score.**

A proposer may supply a structured candidate, confidence, rejected alternatives, typed reasoning consequences, evidence references, and cost estimates. It may not supply its own semantic fingerprint, novelty/depth score, verification authority, resource tier, or a required raw chain-of-thought field.

AASM projects a bounded performance vector from durable outcomes and validated reuse telemetry: reliability, confidence calibration, verified utility, reuse contribution, compute efficiency, conflict-learning value, artifact durability, repair rate, and measured avoided work.

That performance may yield a `ResourceLease` for more context, more parallel candidates, solver classes, and scheduling priority. It never yields direct truth promotion, direct canonical-state mutation, self-verification, `POLICY`, or `CONTROLLER` authority.

The v0.44 graduation gates are explicit:

- bind measurement identity/authority to a durable governed AASM actor rather than a caller-supplied class;
- enforce ResourceLease budgets through the existing scheduler/resource path;
- enforce solver/privilege restrictions through the existing capability/lease boundary;
- make the SII adversarial certification profile reach `PASS`.

### Five reference domains remain active

The v0.42 harness remains the deterministic stress substrate:

- **Constraint solving:** exact subproblem-result reuse, durable recovery after deleting the process-local hot index, environment invalidation, and certificate-gated execution skipping.
- **Software repair:** freshness expiry, repository/dependency fingerprint changes, and the rule that non-idempotent effects are never discharged by reuse.
- **Research synthesis:** an authorized Reasoning Artifact is reusable until an ordinary truth-status change marks it stale; provenance remains durable while reuse is rejected.
- **Formal reasoning:** a requested verification strength is independently checked against candidate verification strength.
- **Long-horizon memory:** governed user-private memory obeys principal visibility and becomes ineligible for reuse after tombstone/revocation.

Every scenario also checks exact replay against persisted machine state.

### Reuse boundary

A reusable result must pass all applicable checks before execution can be skipped:

- exact canonical source fingerprint;
- durable policy/controller candidate admission;
- hierarchical scope visibility;
- principal privacy;
- environment compatibility;
- dependency-fingerprint compatibility;
- explicit freshness bounds when required;
- effect safety;
- requested verification-strength compatibility when specified;
- an explicit sound relation: `EXACT`, `IDEMPOTENT`, `SUBSUMES`, or `CERTIFIED_EQUIVALENT`.

Similarity and embeddings may discover candidates but never establish reuse. `SUBSUMES` requires an explicit semantic validator. Non-idempotent effects are never discharged by a cached result.

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

SII sits above this loop as a participation/economic policy surface. It does not bypass it.

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

Experimental SII preview:

```python
from aasm import AASMEngine, ProblemSpec, StructuredProposal, create_sii

engine = AASMEngine(ProblemSpec("participation preview"))
sii = create_sii(engine)
identity = sii.register(principal_id="provider:model:stable", name="reasoner")
proposal = StructuredProposal(
    proposer_id=identity["identity"]["proposer_id"],
    decision_name="choose_strategy",
    scope_id="root",
    chosen={"strategy": "reuse-first"},
    confidence=.8,
)
sii.submit(proposal)
```

## CLI

```bash
# v0.43 certification surfaces
aasm certification-contract
aasm certify
aasm certify --target solver-reuse
aasm certify --target sii-preview
aasm sii-contract

# v0.42 reference stress surfaces remain active
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
- v0.42 Reference Domains & Reuse/Memory/Reasoning Stress Tests ✅
- **v0.43 Semantic Conformance, Adversarial Domains, and Certification ✅**
- **v0.44 next — Symbiotic Intelligence Interface & Governed Intelligence Economics**
- v0.45 Cross-Run Certified Knowledge & Governed Long-Term Memory
- v0.46 Semantic Solver Release Candidate

See [ROADMAP.md](ROADMAP.md), [docs/CURRENT_RELEASE.md](docs/CURRENT_RELEASE.md), [docs/SEMANTIC_CERTIFICATION.md](docs/SEMANTIC_CERTIFICATION.md), [docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md](docs/SYMBIOTIC_INTELLIGENCE_INTERFACE.md), [docs/REFERENCE_DOMAIN_STRESS.md](docs/REFERENCE_DOMAIN_STRESS.md), and [docs/REUSE_AND_SOLVER_LOOP.md](docs/REUSE_AND_SOLVER_LOOP.md).
