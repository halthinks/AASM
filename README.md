<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, models, humans, and real work.**

AASM keeps machine truth outside the model. Models, compilers, and reasoning workers may propose structures; deterministic AASM validation and policy decide what may become durable.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## Current release — v0.37.0

**Reasoning Artifacts and Epistemic Admission**

| Identity | Value |
|---|---|
| Package/runtime | `aasm-runtime 0.37.0` |
| Adoption contract | `aasm.adoption.v1 / 0.13.0` |
| Semantic problem | `aasm.semantic.problem.v1 / 0.1.0` |
| Semantic compiler | `aasm.semantic.compiler.v1 / 0.1.0` |
| Reasoning artifacts | `aasm.reasoning.artifact.v1 / 0.1.0` |
| Epistemic admission | `aasm.reasoning.admission.v1 / 0.1.0` |
| Reasoning commit | `aasm.reasoning.commit.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |
| Next release | **v0.38.0 — Semantic Dependency Graph and Truth Maintenance** |

v0.37 gives AASM a durable epistemic layer without adding a second runtime, database, scheduler, or authority path.

### Typed reasoning artifacts

The public reasoning model includes:

`Claim · Hypothesis · Lemma · Invariant · Counterexample · Definition · Assumption · Observation · Derivation · Refutation · ObjectiveResult`

Each artifact has deterministic identity/fingerprint, producer authority, subject scope, premise references, evidence references, verifier requirements, confidence, and metadata.

### Epistemic lifecycle

```text
PROPOSED
  ├─ SUPPORT ───────────────→ SUPPORTED
  ├─ CONTEST ───────────────→ CONTESTED
  └─ REQUEST_VERIFICATION ─→ VERIFICATION_REQUESTED
                                  │
                                  ├─ PASS (required verifiers complete) → VERIFIED
                                  └─ FAIL → CONTESTED

VERIFIED ── POLICY/CONTROLLER AUTHORIZE ─→ AUTHORIZED
AUTHORIZED/VERIFIED/CONTESTED ── REFUTE ─→ REFUTED
nonterminal state ── STALE ─→ STALE
pre-authorization state ── POLICY/CONTROLLER REJECT ─→ REJECTED
```

Self-verification is rejected. Verification must be evidence-bearing. Authorization requires `POLICY` or `CONTROLLER` authority. A `ReasoningCommit` can contain only `AUTHORIZED` artifacts.

### One durable authority path

Reasoning proposals, transitions, and commits are ordinary AASM Evidence records. The production event/reducer/store path remains authoritative:

```text
raw problem
   ↓
semantic compiler (proposal only)
   ↓
ProblemInstance
   ↓
reasoning artifact proposal
   ↓
independent evidence + verification
   ↓
policy authorization
   ↓
ReasoningCommit
   ↓
ordinary AASM Evidence event → production reducer → Memory / SQLite / PostgreSQL
```

The durable reasoning view is reconstructed deterministically from that event-sourced evidence history. Replay and restart therefore preserve admitted knowledge without a private reasoning store.

### Python surface

```python
from aasm import AASMEngine, ProblemSpec, Claim, ReasoningProducer, VerifierRequirement

engine = AASMEngine(ProblemSpec("example"))

artifact = Claim(
    "the component is ready",
    ReasoningProducer("planner", "PROPOSER"),
    verifier_requirements=(VerifierRequirement("independent-verifier"),),
)

engine.propose_artifact(artifact)
engine.request_verification(
    artifact.artifact_id,
    verifier_ids=["independent-verifier"],
    requester_id="planner",
)
```

The remaining lifecycle methods are `support_artifact`, `contest_artifact`, `record_verification`, `authorize_artifact`, `refute_artifact`, `mark_stale`, `reject_artifact`, and `reasoning_commit`.

### CLI surfaces

```bash
aasm reasoning-contract
aasm reasoning-conformance
aasm reasoning MACHINE_ID --store runs.db
aasm reasoning-artifact MACHINE_ID ARTIFACT_ID --store runs.db
aasm reasoning-provenance MACHINE_ID ARTIFACT_ID --store runs.db
aasm reasoning-commit MACHINE_ID --store runs.db \
  --artifact-id ARTIFACT_ID \
  --authority-id policy-1 \
  --authority-class POLICY
```

## Why AASM exists

A conversational agent can forget decisions, retry disproven approaches, hide unfinished requirements, treat a model-generated claim as truth, or modify the newest symptom instead of the causal assumption. AASM turns long-running work into a replayable state machine with durable Decisions, Obligations, Evidence, reasoning artifacts, conflicts, learned constraints, causal backjumping, fairness, effects, leases, replay, provenance, and formal checks.

## Release progression

- **v0.29** Thin LangGraph Adapter
- **v0.30** Adapter Conformance Kit
- **v0.31** Hierarchical Decision Scopes
- **v0.32** Runtime/Formal Trace Conformance
- **v0.33** Signed Provenance and Verifiable Exports
- **v0.34** Distributed Recovery Certification
- **v0.35** Semantic Problem Model Foundations
- **v0.36** Semantic Compiler SDK
- **v0.37** Reasoning Artifacts and Epistemic Admission
- **v0.38 next** Semantic Dependency Graph and Truth Maintenance

## Install

```bash
pip install aasm-runtime
```

Contributor setup:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
pip install -e '.[dev]'
pytest -q
```

## Documentation

[Why AASM?](WHY_AASM.md) · [Roadmap](ROADMAP.md) · [Architecture](docs/ARCHITECTURE.md) · [Formal Assurance](docs/FORMAL_ASSURANCE.md) · [Operator Runbooks](docs/runbooks/README.md) · [Release Process](docs/RELEASE_PROCESS.md)

## Correctness boundary

The compiler guarantees deterministic structure and admission routing. The epistemic layer guarantees explicit artifact lifecycle, verifier separation, evidence references, policy authorization, append-only provenance, deterministic projection, and replay/restart consistency. Neither layer makes an unsupported scientific premise, external measurement, or model-generated statement true.

Semantic dependency propagation and automatic truth maintenance are deliberately reserved for v0.38 rather than being hidden inside v0.37.

## License

MIT — see [LICENSE](LICENSE).
