<div align="center">

# AASM
## Algorithmic Agent State Machine

**A durable, deterministic control plane for agents, tools, models, humans, and real work.**

AASM keeps machine truth outside the model. Models, compilers, and tools may propose or produce evidence; explicit authority, obligations, verification, and deterministic state transitions decide what becomes durable.

[![CI](https://github.com/halthinks/AASM/actions/workflows/ci.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/ci.yml)
[![Formal Assurance](https://github.com/halthinks/AASM/actions/workflows/formal.yml/badge.svg)](https://github.com/halthinks/AASM/actions/workflows/formal.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

## Current release — v0.39.0

**Typed Protocol, Capability ABI, and Formal Verification Workers**

| Identity | Value |
|---|---|
| Package/runtime | `aasm-runtime 0.39.0` |
| Adoption contract | `aasm.adoption.v1 / 0.15.0` |
| Typed protocol | `aasm.typed.protocol.v1 / 0.1.0` |
| Capability ABI | `aasm.capability.abi.v1 / 0.1.0` |
| Formal statement | `aasm.formal.statement.v1 / 0.1.0` |
| Formal verification | `aasm.formal.verification.v1 / 0.1.0` |
| Semantic dependencies | `aasm.semantic.dependencies.v1 / 0.1.0` |
| Reasoning admission | `aasm.reasoning.admission.v1 / 0.1.0` |
| Remote protocol | `aasm.remote.v1 / 0.19.0` |
| Next release | **v0.40.0 — Hierarchical Memory, Reasoning Frontier, and Context Projection** |

V0.39 turns typed transitions and formal verification into ordinary governed AASM capabilities instead of parallel subsystems.

```text
Typed event
   ↓ schema validation
legal transition proposal
   ↓ ordinary CausalDecisionRecord
required guards/evidence
   ↓ ordinary ObligationRecord(s)
POLICY / CONTROLLER authorization
   ↓
active scoped decision
```

A pattern cannot silently redefine machine legality. It is versioned, fingerprinted, admitted by policy, and every typed transition remains on the existing decision/obligation/event/reducer path.

## Versioned capability ABI

Capabilities are explicit contracts with typed inputs/outputs, evidence classes, supported logics/query modes, deterministic identity, and provider bindings.

```text
CapabilityContract
     ↓ policy admission
CapabilityProvider
     ↓ binds to
ResourceRecord + WorkerRecord
     ↓ scheduler sees capability/provider tokens
TaskDemand
     ↓
TaskLease
     ↓
worker result
     ↓
Evidence
```

A capability is not authority. Registering a solver, model, tool, observer, handler, or operator does not let it change the plan or durable truth by itself.

V0.39 defines the common ABI classes:

- `OPERATOR`
- `OBSERVER`
- `VERIFIER`
- `HANDLER`

The first reference capability family is formal verification.

## Formal reasoning capability family

AASM now provides first-class contracts for:

- **Vampire** — first-order/TPTP proving;
- **Z3** — SMT verification;
- **cvc5** — SMT verification;
- **Lean 4** — proof elaboration/kernel checking;
- certificate-checker capabilities.

They do **not** share identical semantics. AASM normalizes each provider into one formal result contract while preserving provider identity, logic, query mode, and raw status.

### Formalization is part of provenance

A natural-language claim is never sent to a prover and then treated as proved merely because the prover accepted some translation.

```text
ReasoningArtifact
      ↓
FormalStatement
  source artifact IDs + exact fingerprints
  logic + query mode + query encoding
  compiler ID/version
  environment fingerprint
  canonical source
      ↓
FormalVerificationRequest
```

If the source artifact fingerprint changes, that exact formalization no longer represents the new artifact.

### SMT validity is explicit

For `VALIDITY`, `INVARIANT`, and `EQUIVALENCE`, SMT statements use the declared encoding:

```text
ASSUMPTIONS_AND_NEGATED_CONJECTURE
```

Only under that contract is:

```text
UNSAT → PROVED
SAT   → COUNTERMODEL
```

`SAT` is therefore never generically interpreted as “the theorem was disproved.”

### Lean rejection is not a refutation

A successful Lean kernel check may produce `PROVED` with `TRUSTED_KERNEL` strength. A failed elaboration/check produces an inconclusive result; it does **not** establish the negation of the theorem.

```text
Lean accepts proof → PROVED
Lean rejects proof → UNKNOWN / diagnostic evidence
```

The contract records this as `NOT_A_REFUTATION`.

### Solver identity is reproducible

The default formal verification policy requires a conclusive solver result to carry:

- solver/provider ID;
- solver version;
- executable SHA-256 **or** immutable container digest;
- exact request and formal-statement fingerprints.

Raw stdout/stderr is diagnostic material and is content-hashed separately. A proof object is likewise independently hashed rather than folded ambiguously into the theorem identity.

### Agreement is not voting

A multi-solver policy may require independent results, but AASM does not turn majority vote into truth.

```text
Z3     → PROVED
cvc5   → PROVED
        ↓
MULTI_SOLVER_AGREEMENT
```

If independent solvers disagree, the aggregate is `INCONCLUSIVE`. Policy decides what additional verification is required.

## Epistemic boundary

Formal workers are deterministic evidence producers/verifiers, not epistemic authorities.

```text
Model / human proposes Claim
          ↓
FormalStatement
          ↓
ordinary formal-verification Obligation
          ↓
TaskDemand → TaskLease
          ↓
Vampire / Z3 / cvc5 / Lean 4
          ↓
FormalVerificationResult Evidence
          ↓
V37 VERIFY transition
          ↓
VERIFIED reasoning artifact
          ↓
POLICY / CONTROLLER only
          ↓
AUTHORIZED
```

A solver result can propose a `Lemma`, `Invariant`, or `Counterexample`, or satisfy a requested V37 verifier. It cannot call `authorize_artifact()` for itself.

Once policy changes the epistemic state of an upstream artifact, **V38** supplies the downstream consequence engine: affected constraints, causal decisions, and consumed obligations can be invalidated/reopened while unrelated siblings survive.

## Typed transition example

```python
from aasm import PatternMachine, ScopedLegalTransition, TypedEventSchema

ready = TypedEventSchema(
    "READY",
    {
        "type": "object",
        "required": ["ok"],
        "properties": {"ok": {"type": "boolean"}},
        "additionalProperties": False,
    },
    guards=("calibration.current",),
)

pattern = PatternMachine(
    "component-test",
    "1.0.0",
    "root",
    ("INIT", "VERIFIED"),
    "INIT",
    (ScopedLegalTransition("INIT", "READY", "VERIFIED", "accept-ready"),),
    (ready,),
)

engine.admit_typed_pattern(
    pattern,
    authority_id="policy-1",
    authority_class="POLICY",
)
```

The event validates first. The candidate transition is then represented as a causal decision plus ordinary obligations. No hidden handler or direct state mutation is introduced.

## Formal verification example

```python
engine.install_default_formal_capability_contracts(
    authority_id="policy-1",
    authority_class="POLICY",
)

formal = engine.formalize_artifact(
    artifact_id,
    logic="smtlib2",
    query_mode="VALIDITY",
    canonical_source=smt2_source,
    compiler_id="my-formalizer",
    compiler_version="1.0.0",
)

request = engine.request_formal_verification(
    formal["formal_statement"]["formal_statement_id"],
    "formal.smt",
    requester_id="agent-1",
    linked_artifact_id=artifact_id,
    required_providers=["z3", "cvc5"],
)
```

Providers are admitted separately and execute only after normal resource/worker registration and lease acquisition.

## CLI

```bash
aasm typed-protocol-contract
aasm capability-abi-contract
aasm formal-verification-contract
aasm typed-capability-conformance

aasm typed-patterns MACHINE_ID --store runs.db
aasm typed-pattern-add MACHINE_ID --store runs.db --input pattern.json \
  --authority-id policy-1 --authority-class POLICY
aasm typed-transition-propose MACHINE_ID --store runs.db \
  --pattern-id PATTERN --event READY --payload payload.json --proposer-id agent-1
aasm typed-transition-authorize MACHINE_ID DECISION_ID --store runs.db \
  --authority-id policy-1 --authority-class POLICY

aasm capabilities MACHINE_ID --store runs.db
aasm formal-blueprint MACHINE_ID --store runs.db
aasm formal-default-contracts MACHINE_ID --store runs.db \
  --authority-id policy-1 --authority-class POLICY
aasm formal-provider-runtime MACHINE_ID --store runs.db --input provider.json \
  --authority-id policy-1 --authority-class POLICY

aasm formalize MACHINE_ID ARTIFACT_ID --store runs.db \
  --logic smtlib2 --query-mode VALIDITY --source theorem.smt2
aasm formal-request MACHINE_ID FORMAL_STATEMENT_ID --store runs.db \
  --capability-id formal.smt --requester-id agent-1 --provider z3 --provider cvc5
aasm formal-report MACHINE_ID REQUEST_ID --store runs.db
aasm formal-result MACHINE_ID --store runs.db --input result.json --lease-id LEASE_ID
```

## Architecture progression

- **v0.35** Semantic Problem Model Foundations
- **v0.36** Semantic Compiler SDK
- **v0.37** Reasoning Artifacts and Epistemic Admission
- **v0.38** Semantic Dependency Graph, Causal Decisions, and Reactive Truth Maintenance
- **v0.39 current** Typed Protocol, Capability ABI, and Formal Verification Workers
- **v0.40 next** Hierarchical Memory, Reasoning Frontier, and Context Projection
- **v0.41** Domain-Neutral Autonomous Solver Loop
- **v0.42** Reference Domains and Memory/Reasoning Stress Tests — including mathematical theorem proving
- **v0.43** Semantic Conformance and Adversarial Certification
- **v0.44** Cross-Run Certified Knowledge and Governed Long-Term Memory
- **v0.45** Semantic Solver Release Candidate

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

[Why AASM?](WHY_AASM.md) · [Roadmap](ROADMAP.md) · [Architecture](docs/ARCHITECTURE.md) · [Typed Capabilities & Formal Verification](docs/TYPED_CAPABILITIES_FORMAL_VERIFICATION.md) · [Semantic Truth Maintenance](docs/SEMANTIC_TRUTH_MAINTENANCE.md) · [Formal Assurance](docs/FORMAL_ASSURANCE.md)

## Correctness boundary

V0.39 proves/tests typed event legality, policy-controlled transition activation, formalization identity, capability/provider binding, leased formal execution, normalized solver semantics, and the no-solver-authority boundary. It does not claim that arbitrary natural-language-to-formal translations are correct, that every solver produces independently checkable certificates, or that solver agreement substitutes for proof policy.

## License

MIT — see [LICENSE](LICENSE).
